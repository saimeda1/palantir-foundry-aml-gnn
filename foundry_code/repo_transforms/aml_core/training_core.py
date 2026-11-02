"""Shared Multi-GNN training loop, used by BOTH execution surfaces:

- Code Repository batch training transforms (production: GPU profile,
  scheduled builds) -- see the aml_training transforms package.
- Jupyter Code Workspace notebook (interactive development).

Keeping the loop here means the production pipeline and the notebook train
byte-identical models; only data loading and publishing differ per surface.
"""
from __future__ import annotations

import copy
import os

import numpy as np
import torch
from sklearn.metrics import average_precision_score, f1_score, roc_auc_score
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
    num_workers=None,   # None -> auto (4 on GPU, 2 on CPU)
)


def make_loader(data, batch_size, num_neighbors, shuffle, num_workers, pin):
    return LinkNeighborLoader(
        data,
        num_neighbors=num_neighbors,
        edge_label_index=data.edge_index,
        edge_label=data.y,
        batch_size=batch_size,
        shuffle=shuffle,
        num_workers=num_workers,
        pin_memory=pin,
    )


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
    return {
        "roc_auc": roc_auc_score(y_true, y_score),
        "pr_auc": average_precision_score(y_true, y_score),
        "minority_f1": f1_score(y_true, (y_score >= 0.5).astype(int)),
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


def train_multignn(train_df, val_df, tier: str = "unknown", log=print, **overrides):
    """Full training run: graphs -> loop -> threshold calibration.

    Returns (adapter, metrics). The caller publishes the adapter through
    whichever ModelOutput its surface provides (transforms or workspace).
    """
    cfg = {**DEFAULTS, **overrides}
    on_gpu = torch.cuda.is_available()
    device = torch.device("cuda" if on_gpu else "cpu")
    if not on_gpu:
        torch.set_num_threads(os.cpu_count() or 4)
    num_workers = cfg["num_workers"]
    if num_workers is None:
        num_workers = 4 if on_gpu else 2
    log(f"tier={tier} device={device} cfg={ {k: v for k, v in cfg.items()} }")

    train_graph = build_graph(train_df)
    val_graph = build_graph(val_df, account_index=dict(train_graph.account_index))
    log(f"train graph: {train_graph.num_nodes:,} nodes, "
        f"{train_graph.edge_index.size(1):,} edges, "
        f"{int(train_graph.y.sum()):,} positives")

    model = AmlEdgeGNN(
        node_dim=NODE_FEATURE_DIM,
        edge_dim=EDGE_FEATURE_DIM,
        hidden_dim=cfg["hidden_dim"],
        num_layers=cfg["num_layers"],
        reverse_mp=cfg["reverse_mp"],
        ego_ids=cfg["ego_ids"],
    ).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=cfg["lr"])
    scaler = torch.amp.GradScaler("cuda", enabled=on_gpu)

    train_loader = make_loader(train_graph, cfg["batch_size"], cfg["num_neighbors"],
                               True, num_workers, on_gpu)
    val_loader = make_loader(val_graph, cfg["batch_size"], cfg["num_neighbors"],
                             False, num_workers, on_gpu)

    best_pr_auc, best_state = -1.0, None
    for epoch in range(1, cfg["epochs"] + 1):
        model.train()
        total_loss, n_batches = 0.0, 0
        for batch in train_loader:
            seed_attr = train_graph.edge_attr[batch.input_id].to(device, non_blocking=True)
            batch = batch.to(device, non_blocking=True)
            optimizer.zero_grad(set_to_none=True)
            with torch.autocast(device_type=device.type, enabled=on_gpu):
                logits = model(
                    batch.x, batch.edge_index, batch.edge_attr,
                    batch.edge_label_index, seed_attr,
                )
                loss = focal_loss(logits, batch.edge_label.float(),
                                  alpha=cfg["focal_alpha"], gamma=cfg["focal_gamma"])
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()
            total_loss += float(loss.detach())
            n_batches += 1
            if n_batches % 200 == 0:
                log(f"  epoch {epoch} batch {n_batches} "
                    f"loss={total_loss / n_batches:.5f}")

        m = evaluate(model, val_loader, val_graph.edge_attr, device, on_gpu)
        log(f"epoch {epoch}: train_loss={total_loss / max(n_batches, 1):.5f} "
            f"val_roc_auc={m['roc_auc']:.4f} val_pr_auc={m['pr_auc']:.4f} "
            f"val_minority_f1={m['minority_f1']:.4f}")
        if m["pr_auc"] > best_pr_auc:
            best_pr_auc = m["pr_auc"]
            best_state = copy.deepcopy(model.state_dict())

    model.load_state_dict(best_state)
    m = evaluate(model, val_loader, val_graph.edge_attr, device, on_gpu)
    thresholds = calibrate_thresholds(m["scores"], m["labels"])
    metrics = {
        "tier": tier,
        "best_val_pr_auc": float(best_pr_auc),
        "final_val_roc_auc": float(m["roc_auc"]),
        "final_val_minority_f1": float(m["minority_f1"]),
        "thresholds": thresholds,
    }
    log(f"final: {metrics}")

    from model_adapter import AmlGnnAdapter
    adapter = AmlGnnAdapter(
        state_dict={k: v.cpu() for k, v in model.state_dict().items()},
        account_index=train_graph.account_index,
        thresholds=thresholds,
        config={
            "node_dim": NODE_FEATURE_DIM,
            "edge_dim": EDGE_FEATURE_DIM,
            "hidden_dim": cfg["hidden_dim"],
            "num_layers": cfg["num_layers"],
            "reverse_mp": cfg["reverse_mp"],
            "ego_ids": cfg["ego_ids"],
            "tier": tier,
        },
    )
    return adapter, metrics
