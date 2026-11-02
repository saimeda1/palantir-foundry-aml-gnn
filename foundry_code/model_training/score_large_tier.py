"""Chunked scoring of a Large-tier dataset with a trained AML GNN adapter.

The Large transaction datasets (~175M rows) were uploaded as ~36 headerless
CSV part files of ~5M rows each, in chronological order. This streams them
file by file: each part becomes a time-window graph, every edge in it is
scored, and only compact score/label arrays are kept, so peak memory stays
at one part (~2-3GB) regardless of total size.

Usage inside the Code Workspace (after training, or with a loaded model):

    from score_large_tier import score_large
    report = score_large(adapter, "HI-Large_Trans")

Add the dataset alias (e.g. HI-Large_Trans) in the Data panel first. Pass
`output_alias` (a registered writable dataset) to persist per-transaction
scores; otherwise only the evaluation report is produced.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

RAW_COLS = [
    "timestamp", "from_bank", "from_account", "to_bank", "to_account",
    "amount_received", "receiving_currency", "amount_paid",
    "payment_currency", "payment_format", "is_laundering",
]


def score_large(adapter, dataset_alias: str, output_alias: str | None = None,
                max_parts: int | None = None) -> dict:
    from foundry.transforms import Dataset
    from sklearn.metrics import average_precision_score, roc_auc_score

    files = Dataset.get(dataset_alias).files().download()
    parts = sorted(p for name, p in files.items() if name.endswith(".csv"))
    if max_parts:
        parts = parts[:max_parts]
    print(f"{dataset_alias}: scoring {len(parts)} part files")

    HISTORY_ROWS = 1_000_000   # trailing context carried between chunks

    all_scores, all_labels = [], []
    scored_frames = []
    history = None
    next_txn_id = 0
    for i, path in enumerate(parts, 1):
        chunk = pd.read_csv(path, names=RAW_COLS, dtype=str)
        chunk["transaction_id"] = np.arange(
            next_txn_id, next_txn_id + len(chunk), dtype=np.int64
        )
        next_txn_id += len(chunk)
        labels = pd.to_numeric(chunk["is_laundering"], errors="coerce").fillna(0).to_numpy(np.int8)

        out = adapter.predict(chunk.drop(columns=["is_laundering"]),
                              history_df=history)
        history = chunk.tail(HISTORY_ROWS)
        scores = out["laundering_probability"].to_numpy(np.float32)
        all_scores.append(scores)
        all_labels.append(labels)
        if output_alias:
            scored_frames.append(out[[
                "transaction_id", "timestamp", "laundering_probability", "risk_band",
            ]].assign(is_laundering_ground_truth=labels))
        print(f"  part {i}/{len(parts)}: {len(chunk):,} rows, "
              f"{int(labels.sum()):,} positives, "
              f"mean score {scores.mean():.4f}")
        del chunk, out

    y_score = np.concatenate(all_scores)
    y_true = np.concatenate(all_labels)
    order = np.argsort(-y_score)
    report = {
        "rows": int(len(y_score)),
        "positives": int(y_true.sum()),
        "roc_auc": float(roc_auc_score(y_true, y_score)),
        "pr_auc": float(average_precision_score(y_true, y_score)),
        "precision_at_100": float(y_true[order][:100].mean()),
        "precision_at_500": float(y_true[order][:500].mean()),
        "precision_at_5000": float(y_true[order][:5000].mean()),
    }
    print("evaluation:", report)

    if output_alias and scored_frames:
        result = pd.concat(scored_frames, ignore_index=True)
        Dataset.get(output_alias).write_table(result)
        print(f"wrote {len(result):,} scored rows to {output_alias}")
    return report
