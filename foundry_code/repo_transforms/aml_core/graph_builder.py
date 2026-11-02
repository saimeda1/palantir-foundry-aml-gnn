"""Build a PyTorch Geometric graph from raw AML transaction dataframes.

Shared by training and the model adapter so both sides featurize identically.

Nodes are accounts (bank + account composite key). Edges are directed
transactions. Implements the input-side adaptation from Egressy et al.
(AAAI 2024, "Provably Powerful GNNs for Directed Multigraphs"):
multigraph port numbering — each edge carries its chronological rank among
its source node's outgoing edges and its target node's incoming edges,
which lets the network distinguish parallel edges and count fan-in/out.
(Ego IDs and reverse message passing live in model.py.)
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import torch
from torch_geometric.data import Data

PAYMENT_FORMATS = [
    "Cheque", "Credit Card", "Reinvestment", "Cash", "ACH", "Wire", "Bitcoin",
]
CURRENCIES = [
    "US Dollar", "Euro", "Yuan", "Shekel", "Yen", "UK Pound", "Ruble",
    "Australian Dollar", "Swiss Franc", "Rupee", "Mexican Peso", "Brazil Real",
    "Canadian Dollar", "Saudi Riyal", "Bitcoin",
]

# 4 numeric + payment-format one-hot + currency one-hot + 4 port features
EDGE_FEATURE_DIM = 4 + len(PAYMENT_FORMATS) + len(CURRENCIES) + 4
NODE_FEATURE_DIM = 5


def _codes(series: pd.Series, vocab: list[str]) -> np.ndarray:
    cat = pd.Categorical(series, categories=vocab)
    return np.asarray(cat.codes)  # -1 for unseen values -> all-zero one-hot


def _one_hot(codes: np.ndarray, size: int) -> np.ndarray:
    out = np.zeros((len(codes), size), dtype=np.float32)
    mask = codes >= 0
    out[mask, codes[mask]] = 1.0
    return out


def _port_features(src: np.ndarray, dst: np.ndarray, ts_sec: np.ndarray) -> np.ndarray:
    """Chronological port numbers: for each edge, its rank among the source's
    outgoing edges and the target's incoming edges, both normalized, plus the
    log totals. Ports are computed on the full graph passed in (a pragmatic
    global variant of the paper's per-subgraph numbering)."""
    def ranks(nodes):
        frame = pd.DataFrame({"n": nodes, "t": ts_sec})
        grp = frame.groupby("n", sort=False)["t"]
        rank = grp.rank(method="first").to_numpy(np.float32)
        count = grp.transform("count").to_numpy(np.float32)
        return rank / count, np.log1p(count)

    out_port, out_total = ranks(src)
    in_port, in_total = ranks(dst)
    return np.stack([out_port, in_port, out_total, in_total], axis=1)


def build_graph(df: pd.DataFrame, account_index: dict[str, int] | None = None) -> Data:
    """df needs columns: timestamp, from_bank, from_account, to_bank,
    to_account, amount_received, receiving_currency, amount_paid,
    payment_currency, payment_format, and optionally is_laundering /
    transaction_id.

    account_index maps composite account keys to node ids; pass the training
    mapping at inference to keep ids stable, unseen accounts are appended.
    """
    df = df.reset_index(drop=True)
    src_key = df["from_bank"].astype(str) + "|" + df["from_account"].astype(str)
    dst_key = df["to_bank"].astype(str) + "|" + df["to_account"].astype(str)

    if account_index is None:
        account_index = {}
    for key in pd.concat([src_key, dst_key]).unique():
        if key not in account_index:
            account_index[key] = len(account_index)

    src = src_key.map(account_index).to_numpy(dtype=np.int64)
    dst = dst_key.map(account_index).to_numpy(dtype=np.int64)
    del src_key, dst_key
    edge_index = torch.from_numpy(np.stack([src, dst]))

    ts = pd.to_datetime(df["timestamp"], format="%Y/%m/%d %H:%M", errors="coerce")
    ts_sec = ts.astype("int64").to_numpy() // 10**9
    t0 = ts_sec.min()
    day_frac = ((ts_sec - t0) % 86400) / 86400.0
    elapsed_days = (ts_sec - t0) / 86400.0

    amount_paid = pd.to_numeric(df["amount_paid"], errors="coerce").fillna(0.0).to_numpy()
    amount_recv = pd.to_numeric(df["amount_received"], errors="coerce").fillna(0.0).to_numpy()

    edge_attr = np.concatenate(
        [
            np.log1p(np.abs(amount_paid)).reshape(-1, 1).astype(np.float32),
            np.log1p(np.abs(amount_recv)).reshape(-1, 1).astype(np.float32),
            day_frac.reshape(-1, 1).astype(np.float32),
            elapsed_days.reshape(-1, 1).astype(np.float32),
            _one_hot(_codes(df["payment_format"], PAYMENT_FORMATS), len(PAYMENT_FORMATS)),
            _one_hot(_codes(df["payment_currency"], CURRENCIES), len(CURRENCIES)),
            _port_features(src, dst, ts_sec),
        ],
        axis=1,
    )

    num_nodes = len(account_index)
    x = np.zeros((num_nodes, NODE_FEATURE_DIM), dtype=np.float32)
    out_deg = np.bincount(src, minlength=num_nodes)
    in_deg = np.bincount(dst, minlength=num_nodes)
    out_vol = np.bincount(src, weights=amount_paid, minlength=num_nodes)
    in_vol = np.bincount(dst, weights=amount_recv, minlength=num_nodes)
    x[:, 0] = np.log1p(out_deg)
    x[:, 1] = np.log1p(in_deg)
    x[:, 2] = np.log1p(out_vol)
    x[:, 3] = np.log1p(in_vol)
    x[:, 4] = (out_deg + in_deg > 0).astype(np.float32)

    data = Data(
        x=torch.from_numpy(x),
        edge_index=edge_index,
        edge_attr=torch.from_numpy(edge_attr),
    )
    if "is_laundering" in df.columns:
        data.y = torch.from_numpy(
            pd.to_numeric(df["is_laundering"], errors="coerce").fillna(0).to_numpy(np.float32)
        )
    if "transaction_id" in df.columns:
        data.transaction_id = torch.from_numpy(df["transaction_id"].to_numpy(np.int64))
    data.account_index = account_index
    return data


def temporal_split(df: pd.DataFrame, train_frac: float = 0.70, val_frac: float = 0.10):
    """Chronological split for tiers that ship as a single raw dataset
    (Medium/Large). Returns (train_df, val_df, test_df)."""
    ts = pd.to_datetime(df["timestamp"], format="%Y/%m/%d %H:%M", errors="coerce")
    df = df.iloc[ts.argsort(kind="stable")].reset_index(drop=True)
    n = len(df)
    n_train = int(n * train_frac)
    n_val = int(n * val_frac)
    return (
        df.iloc[:n_train],
        df.iloc[n_train:n_train + n_val],
        df.iloc[n_train + n_val:],
    )
