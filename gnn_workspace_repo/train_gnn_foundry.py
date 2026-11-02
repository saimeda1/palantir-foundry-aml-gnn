"""Interactive (Code Workspace) entry point for Multi-GNN training.

Thin wrapper over training_core so the notebook trains the exact same model
as the production Code Repository transforms. Tier selection via env:

  AML_TIER=HI-Small (default) -> pre-split datasets raw_transactions_train/val
  AML_TIER=HI-Medium | LI-Small | LI-Medium
        -> loads the raw kaggle_full dataset (e.g. "HI-Medium_Trans") and
           performs the 70/10/20 temporal split in memory.
  AML_EPOCHS, AML_BATCH_SIZE, AML_FANOUT, AML_MODEL_ALIAS override defaults;
  AML_NUM_WORKERS = sampling threads (0 = serial, unset = auto).
  AML_PIN_MEMORY=1 re-enables pinned host memory; AML_TORCH_THREADS caps
  CPU intra-op threads (default 4 on GPU).
  AML_HIDDEN (64), AML_LAYERS (2), AML_LR (1e-3), AML_PATIENCE (6) shape the
  model/optimisation; AML_SKIP_PUBLISH=1 trains + checkpoints only;
  AML_RESUME=1 continues from the alias checkpoint (same HIDDEN/LAYERS/EDGE_UPDATES!).
  AML_EDGE_UPDATES=1 adds the reference impl's per-layer edge MLPs + residuals.
"""
from __future__ import annotations

import os

import numpy as np

from graph_builder import temporal_split
from training_core import train_multignn

TIER = os.environ.get("AML_TIER", "HI-Small")
MODEL_ALIAS = os.environ.get(
    "AML_MODEL_ALIAS", f"aml_gnn_{TIER.lower().replace('-', '_')}"
)

RAW_COLS = [
    "timestamp", "from_bank", "from_account", "to_bank", "to_account",
    "amount_received", "receiving_currency", "amount_paid",
    "payment_currency", "payment_format", "is_laundering",
]


def load_tier(tier: str):
    from foundry.transforms import Dataset

    if tier == "HI-Small":
        train_df = Dataset.get("raw_transactions_train").read_table(format="pandas")
        val_df = Dataset.get("raw_transactions_val").read_table(format="pandas")
        return train_df, val_df

    full = Dataset.get(f"{tier}_Trans").read_table(format="pandas")
    full.columns = RAW_COLS[: len(full.columns)]
    full["transaction_id"] = np.arange(len(full), dtype=np.int64)
    train_df, val_df, _test_df = temporal_split(full)
    del full
    return train_df.copy(), val_df.copy()


CKPT_DIR = os.environ.get("AML_CKPT_DIR", os.path.expanduser("~/repo/checkpoints"))
SKIP_PUBLISH = os.environ.get("AML_SKIP_PUBLISH", "0") == "1"


def apply_publish_token() -> None:
    """AML_PUBLISH_TOKEN: publish with a personal Foundry token instead of the
    workspace's scoped one. palantir_models (code_workspaces runtime) sends
    `Bearer $FOUNDRY_TOKEN` to the sidecar, which forwards it; the workspace
    token only has write access to models registered through the Models
    sidebar, so publishing to a model created any other way 403s
    (Artifacts:WriteArtifactPermissionDenied). A user token that owns the
    model does not."""
    tok = os.environ.get("AML_PUBLISH_TOKEN")
    if tok:
        os.environ["FOUNDRY_TOKEN"] = tok.strip()
        print("publishing with AML_PUBLISH_TOKEN (personal token) instead of the workspace token")


def resolve_model_output(alias: str):
    """Resolve the Models-sidebar alias BEFORE training so a missing alias
    fails in 1 second instead of after an hour of GPU time."""
    apply_publish_token()
    from palantir_models.code_workspaces import ModelOutput
    try:
        return ModelOutput(alias)
    except KeyError as exc:
        raise SystemExit(
            f"\nModel alias '{alias}' is not defined in this workspace.\n"
            f"Fix: Models sidebar (left panel) -> add/create a model output "
            f"with alias exactly '{alias}' (this writes .foundry/model-assets.yml), "
            f"then rerun. Or set AML_SKIP_PUBLISH=1 to train and checkpoint only; "
            f"publish later with: python publish_checkpoint.py {alias}\n"
            f"({exc})"
        ) from exc


def save_checkpoint(adapter, metrics, alias: str) -> str:
    """Persist everything needed to rebuild + publish the adapter later.
    Lives under ~/repo (persistent volume) but *.pt is gitignored."""
    import torch
    os.makedirs(CKPT_DIR, exist_ok=True)
    path = os.path.join(CKPT_DIR, f"{alias}.pt")
    torch.save(
        {
            "state_dict": adapter.model.state_dict(),
            "account_index": adapter.account_index,
            "thresholds": adapter.thresholds,
            "config": adapter.config,
            "metrics": metrics,
        },
        path,
    )
    return path


def load_checkpoint(path: str):
    """Rebuild the adapter from a checkpoint using the SELF-CONTAINED bundle
    class (aml_gnn_adapter.py), which is what must be published: Foundry
    packages only the adapter's own file, not graph_builder/model."""
    import torch
    try:
        from aml_gnn_adapter import AmlGnnAdapter
    except ImportError:  # bundle not built; fall back to the multi-file adapter
        print("WARNING: aml_gnn_adapter.py missing - run build_adapter_bundle.py; "
              "publishing the multi-file adapter will break at inference time")
        from model_adapter import AmlGnnAdapter
    ckpt = torch.load(path, map_location="cpu", weights_only=False)
    adapter = AmlGnnAdapter(
        state_dict=ckpt["state_dict"], account_index=ckpt["account_index"],
        thresholds=ckpt["thresholds"], config=ckpt["config"],
    )
    return adapter, ckpt.get("metrics", {})


def resume_state():
    """AML_RESUME=1: continue from ~/repo/checkpoints/<alias>.pt if present."""
    if os.environ.get("AML_RESUME", "0") != "1":
        return None
    import torch
    path = os.path.join(CKPT_DIR, f"{MODEL_ALIAS}.pt")
    if not os.path.exists(path):
        print(f"AML_RESUME=1 but no checkpoint at {path}; starting fresh")
        return None
    ckpt = torch.load(path, map_location="cpu", weights_only=False)
    m = ckpt.get("metrics", {})
    print(f"resuming from {path}: epoch {m.get('epoch')} val_pr_auc {m.get('best_val_pr_auc')}")
    return ckpt["state_dict"], m.get("best_val_pr_auc", -1.0)


LOG_PATH = os.environ.get(
    "AML_LOG_PATH", os.path.expanduser(f"~/repo/train_{MODEL_ALIAS}.log"))


def log(msg: str) -> None:
    """Print AND append to LOG_PATH (gitignored *.log), so progress is readable
    from any terminal even when the notebook front end has lost its output
    stream (happens on tab reload / reconnect)."""
    import datetime
    print(msg, flush=True)
    try:
        with open(LOG_PATH, "a") as fh:
            fh.write(f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S} {msg}\n")
    except OSError:
        pass


def main():
    output = None if SKIP_PUBLISH else resolve_model_output(MODEL_ALIAS)
    resume = resume_state()
    log(f"=== run start: tier={TIER} alias={MODEL_ALIAS} "
        f"env={ {k: v for k, v in os.environ.items() if k.startswith('AML_')} } "
        f"| log file: {LOG_PATH}")
    frames = list(load_tier(TIER))
    log(f"train rows: {len(frames[0]):,}  val rows: {len(frames[1]):,}")
    # hand ownership of the dataframes to the trainer so they are freed as
    # soon as the graphs are built (halves peak memory during training)
    adapter, metrics = train_multignn(
        frames, tier=TIER, log=log,
        epochs=int(os.environ.get("AML_EPOCHS", 5)),
        batch_size=int(os.environ.get("AML_BATCH_SIZE", 4096)),
        # sampling THREADS, not processes (worker processes need /dev/shm,
        # which is 64MB in workspace containers). Unset -> auto (8 on GPU).
        num_workers=(int(os.environ["AML_NUM_WORKERS"])
                     if os.environ.get("AML_NUM_WORKERS") else None),
        num_neighbors=[int(x) for x in os.environ.get("AML_FANOUT", "15,10").split(",")],
        # both default off/small: suspects for the fixed ~2s/step GPU stall
        pin_memory=os.environ.get("AML_PIN_MEMORY", "0") == "1",
        torch_threads=(int(os.environ["AML_TORCH_THREADS"])
                       if os.environ.get("AML_TORCH_THREADS") else None),
        hidden_dim=int(os.environ.get("AML_HIDDEN", 64)),
        edge_updates=os.environ.get("AML_EDGE_UPDATES", "0") == "1",
        num_layers=int(os.environ.get("AML_LAYERS", 2)),
        lr=float(os.environ.get("AML_LR", 1e-3)),
        patience=int(os.environ.get("AML_PATIENCE", 6)),
        # every improving epoch overwrites ~/repo/checkpoints/<alias>.pt, so a
        # crash or kernel death mid-run never loses the best model so far
        checkpoint_fn=lambda a, m: save_checkpoint(a, m, MODEL_ALIAS),
        resume_from=resume,
    )

    ckpt = save_checkpoint(adapter, metrics, MODEL_ALIAS)
    log(f"checkpoint saved: {ckpt}")
    if output is None:
        print(f"AML_SKIP_PUBLISH=1 -> not published. Later: "
              f"python publish_checkpoint.py {MODEL_ALIAS}")
        return adapter
    adapter, _ = load_checkpoint(ckpt)   # bundle adapter class, see load_checkpoint
    try:
        output.publish(adapter)
    except Exception:
        log(f"\nPUBLISH FAILED but the trained model is safe in {ckpt}. "
              f"Fix the cause, then: python publish_checkpoint.py {MODEL_ALIAS}\n")
        raise
    log(f"published model alias '{MODEL_ALIAS}' | {metrics}")
    return adapter


if __name__ == "__main__":
    main()
