"""Shared Multi-GNN training loop, used by BOTH execution surfaces:

- Code Repository batch training transforms (production: GPU profile,
  scheduled builds) -- see the aml_training transforms package.
- Jupyter Code Workspace notebook (interactive development).

Keeping the loop here means the production pipeline and the notebook train
byte-identical models; only data loading and publishing differ per surface.
"""
from __future__ import annotations

import copy
import gc
import os
import time

import numpy as np
import pandas as pd


def _rss_gb() -> float:
    try:
        with open("/proc/self/status") as fh:
            for line in fh:
                if line.startswith("VmRSS"):
                    return int(line.split()[1]) / 1e6
    except OSError:
        pass
    return -1.0
import torch
from sklearn.metrics import (average_precision_score, f1_score,
                             precision_recall_curve, roc_auc_score)


def _usable_cpus() -> int:
    """CPUs this process may actually run on: min(affinity, cgroup quota).
    Containers often report the host's core count while the cgroup grants
    far fewer; OpenMP then spins N threads on M<N cores and every CPU-side
    torch op (sampling, feature gathers) slows down by an order of magnitude."""
    n = os.cpu_count() or 1
    try:
        n = min(n, len(os.sched_getaffinity(0)))
    except AttributeError:
        pass
    quota = None
    try:  # cgroup v2
        q, period = open("/sys/fs/cgroup/cpu.max").read().split()
        if q != "max":
            quota = int(q) / int(period)
    except (OSError, ValueError):
        try:  # cgroup v1
            q = int(open("/sys/fs/cgroup/cpu/cpu.cfs_quota_us").read())
            period = int(open("/sys/fs/cgroup/cpu/cpu.cfs_period_us").read())
            if q > 0:
                quota = q / period
        except (OSError, ValueError):
            try:  # cgroup v1, combined controller mount
                q = int(open("/sys/fs/cgroup/cpu,cpuacct/cpu.cfs_quota_us").read())
                period = int(open("/sys/fs/cgroup/cpu,cpuacct/cpu.cfs_period_us").read())
                if q > 0:
                    quota = q / period
            except (OSError, ValueError):
                pass
    if quota:
        n = min(n, max(1, int(quota)))
    return max(1, n)
from torch_geometric.loader import LinkNeighborLoader

from graph_builder import EDGE_FEATURE_DIM, NODE_FEATURE_DIM, build_graph
from model import AmlEdgeGNN, focal_loss

DEFAULTS = dict(
    epochs=5,
    batch_size=4096,
    num_neighbors=[15, 10],
    hidden_dim=64,
    lr=1e-3,
    focal_alpha=0.95,
    focal_gamma=2.0,
    num_layers=2,
    reverse_mp=True,
    ego_ids=True,
    edge_updates=False,  # reference impl's edge MLPs + residuals; new checkpoints only
    num_workers=None,   # sampling THREADS (not processes); None -> auto
    amp=False,          # fp16 overflowed GIN sums pre-BatchNorm; sampling-bound
                        # anyway, so fp32 costs ~nothing in wall-clock
    grad_clip=1.0,
    patience=6,         # early stop after this many epochs without val PR-AUC gain
    lr_patience=2,      # halve lr after this many epochs without val PR-AUC gain
    lr_factor=0.5,
    checkpoint_fn=None, # callable(adapter, metrics) invoked on every new best epoch
    resume_from=None,   # (state_dict, best_val_pr_auc) to continue an interrupted run
    pin_memory=False,   # cudaHostAlloc is slow + driver-serialising on some VMs;
                        # pinned H2D saves ~3ms per 30MB batch, not worth the risk
    torch_threads=None, # CPU intra-op threads; None -> 4 on GPU (CPU-side torch
                        # work is tiny), usable CPUs when training on CPU
)


class ThreadedLoader:
    """Runs a PyG loader's sampling (collate_fn) in a thread pool.

    Why threads and not DataLoader worker processes: every torch tensor
    handed between processes goes through shm_open(), i.e. /dev/shm -- for
    BOTH sharing strategies (file_descriptor and file_system). Workspace
    containers give /dev/shm 64MB, so a spawned worker receiving the pickled
    graph (hundreds of MB) or returning a sampled batch SIGBUS-dies or hangs.
    pyg_lib's neighbor_sample and the feature gathers in filter_fn are torch
    C++ ops that release the GIL, so plain threads parallelise sampling with
    no shared memory at all. num_threads <= 0 iterates the loader as-is.
    """

    def __init__(self, loader, num_threads: int, pin: bool = False, prefetch: int = 2):
        self.loader = loader
        self.num_threads = int(num_threads)
        self.pin = pin
        self.prefetch = max(int(prefetch), 1)

    def __len__(self):
        return len(self.loader)

    def _produce(self, index):
        batch = self.loader.collate_fn(index)  # sample + filter -> Data
        if self.pin:
            batch = batch.pin_memory()
        return batch

    def __iter__(self):
        if self.num_threads <= 0:
            yield from self.loader
            return
        from collections import deque
        from concurrent.futures import ThreadPoolExecutor

        pending = deque()
        indices = iter(self.loader.batch_sampler)  # reshuffled every epoch

        def submit():
            try:
                index = next(indices)
            except StopIteration:
                return False
            pending.append(pool.submit(self._produce, index))
            return True

        with ThreadPoolExecutor(self.num_threads) as pool:
            for _ in range(self.num_threads * self.prefetch):
                if not submit():
                    break
            while pending:
                batch = pending.popleft().result()
                submit()
                yield batch


def make_loader(data, batch_size, num_neighbors, shuffle, num_workers, pin,
                seed_ids=None):
    """seed_ids restricts which edges are scored/supervised; message passing
    still samples over ALL of data's edges (history-inclusive protocol).

    num_workers = number of sampling THREADS (see ThreadedLoader); the
    underlying DataLoader always runs with num_workers=0."""
    if seed_ids is None:
        label_index, label = data.edge_index, data.y
    else:
        label_index, label = data.edge_index[:, seed_ids], data.y[seed_ids]
    threaded = num_workers > 0
    loader = LinkNeighborLoader(
        data,
        num_neighbors=num_neighbors,
        edge_label_index=label_index,
        edge_label=label,
        batch_size=batch_size,
        shuffle=shuffle,
        num_workers=0,
        pin_memory=pin and not threaded,
        filter_per_worker=True,   # collate_fn returns a finished Data object
    )
    return ThreadedLoader(loader, num_workers, pin=pin and threaded)


@torch.no_grad()
def evaluate(model, loader, edge_attr_store, device, use_amp) -> dict:
    model.eval()
    scores, labels = [], []
    for batch in loader:
        seed_attr = edge_attr_store[batch.input_id].to(device, non_blocking=True)
        batch = batch.to(device, non_blocking=True)
        with torch.autocast(device_type=device.type, enabled=use_amp):
            logits = model(
                batch.x, batch.edge_index, batch.edge_attr,
                batch.edge_label_index, seed_attr,
            )
        scores.append(torch.sigmoid(logits.float()).cpu().numpy())
        labels.append(batch.edge_label.cpu().numpy())
    y_score = np.concatenate(scores)
    y_true = np.concatenate(labels)
    prec, rec, thr = precision_recall_curve(y_true, y_score)
    f1s = 2 * prec[:-1] * rec[:-1] / np.clip(prec[:-1] + rec[:-1], 1e-12, None)
    i = int(np.argmax(f1s))
    return {
        "roc_auc": roc_auc_score(y_true, y_score),
        "pr_auc": average_precision_score(y_true, y_score),
        "minority_f1": f1_score(y_true, (y_score >= 0.5).astype(int)),
        "best_f1": float(f1s[i]),            # F1 at the best threshold on val
        "best_f1_threshold": float(thr[i]),
        "scores": y_score,
        "labels": y_true,
    }


def calibrate_thresholds(y_score: np.ndarray, y_true: np.ndarray) -> dict:
    """High band: smallest threshold reaching >=50% precision on val;
    Medium band: threshold capturing 80% recall."""
    order = np.argsort(-y_score)
    cum_tp = np.cumsum(y_true[order])
    precision_at_k = cum_tp / (np.arange(len(order)) + 1)
    high_idx = np.where(precision_at_k >= 0.5)[0]
    high_thr = float(y_score[order][high_idx[-1]]) if len(high_idx) else 0.85
    recall = cum_tp / max(y_true.sum(), 1)
    med_idx = int(np.searchsorted(recall, 0.8))
    med_thr = float(y_score[order][min(med_idx, len(order) - 1)])
    return {"high": high_thr, "medium": min(med_thr, high_thr * 0.9)}


def train_multignn(train_df, val_df=None, tier: str = "unknown", log=print,
                   **overrides):
    """Full training run: graphs -> loop -> threshold calibration.

    Returns (adapter, metrics). The caller publishes the adapter through
    whichever ModelOutput its surface provides (transforms or workspace).

    Memory: pass a LIST [train_df, val_df] as the first argument (and drop
    your own references) to hand over ownership — the frames are then freed
    as soon as the graphs are built, roughly halving peak RAM for training.
    """
    if isinstance(train_df, list):
        frames = train_df
        train_df, val_df = frames[0], frames[1]
        frames.clear()
    cfg = {**DEFAULTS, **overrides}
    on_gpu = torch.cuda.is_available()
    device = torch.device("cuda" if on_gpu else "cpu")
    n_cpu = _usable_cpus()
    n_threads = cfg["torch_threads"]
    if n_threads is None:
        # OpenMP teams spinning on more threads than the cgroup really grants
        # stall every CPU-side torch op by seconds; on GPU the CPU side only
        # does small gathers, so a handful of threads is plenty.
        n_threads = min(4, n_cpu) if on_gpu else n_cpu
    if torch.get_num_threads() != n_threads:
        log(f"intra-op threads {torch.get_num_threads()} -> {n_threads} "
            f"(cpu_count={os.cpu_count()}, usable={n_cpu})")
        torch.set_num_threads(int(n_threads))
    pin = bool(on_gpu and cfg["pin_memory"])
    num_workers = cfg["num_workers"]
    if num_workers is None:
        num_workers = min(8, n_cpu) if on_gpu else min(2, n_cpu)
    log(f"tier={tier} device={device} cfg={ {k: v for k, v in cfg.items()} }")

    train_graph = build_graph(train_df)
    # History-inclusive evaluation (paper protocol): val seeds are scored
    # with message passing over the train+val graph, so an account's full
    # history is visible; training still passes messages over train edges
    # only, so no future information leaks into the weights.
    feature_cols = [c for c in train_df.columns if c in val_df.columns]
    eval_graph = build_graph(
        pd.concat([train_df[feature_cols], val_df[feature_cols]],
                  ignore_index=True),
        account_index=dict(train_graph.account_index),
    )
    n_train_edges = train_graph.edge_index.size(1)
    val_seed_ids = torch.arange(n_train_edges, eval_graph.edge_index.size(1))
    val_seed_attr = eval_graph.edge_attr[val_seed_ids]
    del train_df, val_df   # frees the frames iff the caller handed ownership
    gc.collect()
    log(f"train graph: {train_graph.num_nodes:,} nodes, "
        f"{train_graph.edge_index.size(1):,} edges, "
        f"{int(train_graph.y.sum()):,} positives | "
        f"eval graph: {eval_graph.edge_index.size(1):,} edges, "
        f"{len(val_seed_ids):,} val seeds | rss={_rss_gb():.1f}GB")

    model = AmlEdgeGNN(
        node_dim=NODE_FEATURE_DIM,
        edge_dim=EDGE_FEATURE_DIM,
        hidden_dim=cfg["hidden_dim"],
        num_layers=cfg["num_layers"],
        reverse_mp=cfg["reverse_mp"],
        ego_ids=cfg["ego_ids"],
        edge_updates=cfg["edge_updates"],
    ).to(device)
    use_amp = bool(on_gpu and cfg["amp"])
    optimizer = torch.optim.AdamW(model.parameters(), lr=cfg["lr"])
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="max", factor=cfg["lr_factor"], patience=cfg["lr_patience"])
    scaler = torch.amp.GradScaler("cuda", enabled=use_amp)
    log(f"model params: {sum(p.numel() for p in model.parameters()):,}")

    def make_adapter(state_dict, thresholds):
        from model_adapter import AmlGnnAdapter
        return AmlGnnAdapter(
            state_dict={k: v.cpu() for k, v in state_dict.items()},
            account_index=train_graph.account_index,
            thresholds=thresholds,
            config={
                "node_dim": NODE_FEATURE_DIM,
                "edge_dim": EDGE_FEATURE_DIM,
                "hidden_dim": cfg["hidden_dim"],
                "num_layers": cfg["num_layers"],
                "reverse_mp": cfg["reverse_mp"],
                "ego_ids": cfg["ego_ids"],
                "edge_updates": cfg["edge_updates"],
                "num_neighbors": list(cfg["num_neighbors"]),  # inference must match
                "tier": tier,
            },
        )

    train_loader = make_loader(train_graph, cfg["batch_size"], cfg["num_neighbors"],
                               True, num_workers, pin)
    val_loader = make_loader(eval_graph, cfg["batch_size"], cfg["num_neighbors"],
                             False, num_workers, pin, seed_ids=val_seed_ids)

    log(f"sampling with {num_workers} thread(s) per loader, pin_memory={pin} "
        f"(no worker processes: /dev/shm is tiny in workspace containers)")
    best_pr_auc, best_state = -1.0, None
    if cfg["resume_from"] is not None:
        init_state, prev_best = cfg["resume_from"]
        model.load_state_dict(init_state)
        best_state = copy.deepcopy(model.state_dict())
        best_pr_auc = float(prev_best)
        log(f"resumed from checkpoint (previous best val_pr_auc={best_pr_auc:.4f}); "
            f"optimizer state restarts fresh")
    epochs_since_best = 0
    skipped_nan = 0
    for epoch in range(1, cfg["epochs"] + 1):
        epoch_start = time.time()
        model.train()
        total_loss, n_batches = 0.0, 0
        sample_time, step_time = 0.0, 0.0
        batch_iter = iter(train_loader)
        while True:
            t_fetch = time.time()
            try:
                batch = next(batch_iter)
            except StopIteration:
                break
            t_step = time.time()
            sample_time += t_step - t_fetch
            seed_attr = train_graph.edge_attr[batch.input_id].to(device, non_blocking=True)
            batch = batch.to(device, non_blocking=True)
            optimizer.zero_grad(set_to_none=True)
            with torch.autocast(device_type=device.type, enabled=use_amp):
                logits = model(
                    batch.x, batch.edge_index, batch.edge_attr,
                    batch.edge_label_index, seed_attr,
                )
                loss = focal_loss(logits, batch.edge_label.float(),
                                  alpha=cfg["focal_alpha"], gamma=cfg["focal_gamma"])
            if not torch.isfinite(loss):
                skipped_nan += 1
                if skipped_nan > 50:
                    raise RuntimeError(
                        "Aborting: >50 non-finite losses; training is diverging."
                    )
                continue
            scaler.scale(loss).backward()
            scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(model.parameters(), cfg["grad_clip"])
            scaler.step(optimizer)
            scaler.update()
            total_loss += float(loss.detach())   # syncs the GPU step
            step_time += time.time() - t_step
            n_batches += 1
            if n_batches == 1 and epoch == 1:
                # first batch carries CUDA kernel/cuBLAS warmup; restart clocks
                sample_time, step_time, pace_t0 = 0.0, 0.0, time.time()
            if n_batches == 11 and epoch == 1:
                rate = (time.time() - pace_t0) / 10
                log(f"  pace check: {rate:.2f}s/batch "
                    f"(sampling {sample_time / 10:.2f}s + gpu step {step_time / 10:.2f}s) "
                    f"-> ~{rate * len(train_loader) / 60:.0f} min/epoch "
                    f"({len(train_loader)} batches)")
            if n_batches % 200 == 0:
                log(f"  epoch {epoch} batch {n_batches} "
                    f"loss={total_loss / n_batches:.5f}")

        m = evaluate(model, val_loader, val_seed_attr, device, use_amp)
        log(f"epoch {epoch}: train_loss={total_loss / max(n_batches, 1):.5f} "
            f"val_roc_auc={m['roc_auc']:.4f} val_pr_auc={m['pr_auc']:.4f} "
            f"val_f1@0.5={m['minority_f1']:.4f} val_best_f1={m['best_f1']:.4f} "
            f"lr={optimizer.param_groups[0]['lr']:.2e} "
            f"({(time.time() - epoch_start) / 60:.1f} min)"
            + (f" (skipped {skipped_nan} non-finite batches)" if skipped_nan else ""))
        scheduler.step(m["pr_auc"])
        if m["pr_auc"] > best_pr_auc:
            best_pr_auc = m["pr_auc"]
            best_state = copy.deepcopy(model.state_dict())
            epochs_since_best = 0
            if cfg["checkpoint_fn"] is not None:
                try:
                    thr = calibrate_thresholds(m["scores"], m["labels"])
                    cfg["checkpoint_fn"](
                        make_adapter(best_state, thr),
                        {"tier": tier, "epoch": epoch, "best_val_pr_auc": float(best_pr_auc),
                         "val_roc_auc": float(m["roc_auc"]), "val_best_f1": m["best_f1"],
                         "thresholds": thr, "partial": True})
                    log(f"  checkpointed best epoch {epoch}")
                except Exception as exc:  # never let checkpointing kill a run
                    log(f"  checkpoint failed (continuing): {exc!r}")
        else:
            epochs_since_best += 1
            if epochs_since_best >= cfg["patience"]:
                log(f"early stop: no val PR-AUC gain in {cfg['patience']} epochs")
                break

    model.load_state_dict(best_state)
    m = evaluate(model, val_loader, val_seed_attr, device, use_amp)
    thresholds = calibrate_thresholds(m["scores"], m["labels"])
    metrics = {
        "tier": tier,
        "epochs_run": epoch,
        "best_val_pr_auc": float(best_pr_auc),
        "final_val_roc_auc": float(m["roc_auc"]),
        "final_val_minority_f1": float(m["minority_f1"]),
        "final_val_best_f1": float(m["best_f1"]),
        "best_f1_threshold": float(m["best_f1_threshold"]),
        "thresholds": thresholds,
        "config": {k: v for k, v in cfg.items() if k not in ("checkpoint_fn", "resume_from")},
    }
    log(f"final: {metrics}")
    return make_adapter(model.state_dict(), thresholds), metrics
