"""Build the Ontology backing datasets from the scored test stream — pandas
version that runs anywhere (local machine or workspace), no Spark needed at
1M rows. Mirrors the PySpark transform in build_ontology_backing.py.

    python build_backing_datasets_local.py \
        --scored  scored_test_stream.parquet \
        --history train_temporal.csv val_temporal.csv \
        --patterns HI-Small_Patterns.txt \
        --model-version ri.models.main.model-version.<...> \
        --out out_dir/

Outputs (parquet, one per Ontology object type):
  transactions.parquet            Transaction   (scored stream, 1 row / txn)
  transaction_risk_scores.parquet TransactionRiskScore (keyed by txn+model)
  accounts_summary.parquet        Account       (24h in/out volume, max risk)
  alerts.parquet                  Alert         (High + Medium band txns)
  investigation_cases.parquet     InvestigationCase (empty seed, schema only)
  laundering_patterns.parquet     ground-truth typology per laundering txn
                                  (demo "reveal" layer; hidden from triage UI)
  model_evaluation.parquet        precision/recall per band + P@K

Typology for alerts is derived from the local transaction graph (fan-in /
fan-out / scatter-gather / cycle) and is what the investigator sees; the
ground-truth pattern from the Kaggle Patterns file is joined into a
separate column `true_typology` for the demo reveal only.
"""
from __future__ import annotations

import argparse
import os
import re

import numpy as np
import pandas as pd

RAW_DTYPES = {"from_bank": str, "to_bank": str, "from_account": str, "to_account": str}
WINDOW_H = 72          # typology window around an alerted transaction
FAN_MIN = 6            # distinct counterparties to call it a fan pattern
PATTERN_RE = re.compile(r"BEGIN LAUNDERING ATTEMPT - ([A-Z\- ]+?):")


# ------------------------------------------------------------------ helpers
def account_key(bank: pd.Series, acct: pd.Series) -> pd.Series:
    return bank.astype(str) + "|" + acct.astype(str)


def parse_patterns(path: str) -> pd.DataFrame:
    """Kaggle *_Patterns.txt -> one row per laundering transaction with its
    pattern id and typology. Transactions are matched to the stream on the
    raw CSV fields (the file has no transaction ids)."""
    rows, pattern_id, typology = [], -1, None
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            m = PATTERN_RE.match(line)
            if m:
                pattern_id += 1
                typology = m.group(1).strip().title()
                continue
            if line.startswith("END LAUNDERING ATTEMPT") or not line:
                continue
            parts = line.split(",")
            if len(parts) < 11:
                continue
            rows.append((pattern_id, typology, parts[0], parts[1], parts[2],
                         parts[3], parts[4], float(parts[7]), parts[9]))
    return pd.DataFrame(rows, columns=[
        "pattern_id", "true_typology", "timestamp", "from_bank", "from_account",
        "to_bank", "to_account", "amount_paid", "payment_format",
    ])


def derive_typology(alerts: pd.DataFrame, txns: pd.DataFrame) -> pd.Series:
    """Heuristic motif label per alert from the ±WINDOW_H-hour neighbourhood
    of the alerted transaction's two endpoints."""
    ts = txns["timestamp"]
    out_by_src = txns.groupby("from_account")
    in_by_dst = txns.groupby("to_account")
    src_groups = {k: v for k, v in out_by_src}
    dst_groups = {k: v for k, v in in_by_dst}
    labels = []
    for _, a in alerts.iterrows():
        t0 = a["timestamp"]
        lo, hi = t0 - pd.Timedelta(hours=WINDOW_H), t0 + pd.Timedelta(hours=WINDOW_H)
        src, dst = a["from_account"], a["to_account"]

        def win(g):
            return g[(g["timestamp"] >= lo) & (g["timestamp"] <= hi)] if g is not None else None

        src_out = win(src_groups.get(src))
        src_in = win(dst_groups.get(src))
        dst_out = win(src_groups.get(dst))
        dst_in = win(dst_groups.get(dst))
        n_src_out = src_out["to_account"].nunique() if src_out is not None else 0
        n_src_in = src_in["from_account"].nunique() if src_in is not None else 0
        n_dst_in = dst_in["from_account"].nunique() if dst_in is not None else 0
        n_dst_out = dst_out["to_account"].nunique() if dst_out is not None else 0

        # cycle: money from dst (or dst's receivers) finds its way back to src
        cycle = False
        if dst_out is not None and len(dst_out):
            hop1 = set(dst_out["to_account"])
            if src in hop1:
                cycle = True
            else:
                for mid in list(hop1)[:50]:
                    g = win(src_groups.get(mid))
                    if g is not None and (g["to_account"] == src).any():
                        cycle = True
                        break

        if cycle:
            labels.append("Cycle")
        elif n_src_in >= FAN_MIN and n_src_out >= FAN_MIN:
            labels.append("Gather-Scatter")
        elif n_dst_in >= FAN_MIN and n_dst_out >= FAN_MIN:
            labels.append("Scatter-Gather")
        elif n_src_out >= FAN_MIN:
            labels.append("Fan-Out")
        elif n_dst_in >= FAN_MIN:
            labels.append("Fan-In")
        elif a["amount_usd"] >= 10_000 and a["payment_format"] in ("Cash", "ACH"):
            labels.append("Structuring-Suspect")
        else:
            labels.append("Unclassified")
    return pd.Series(labels, index=alerts.index)


# -------------------------------------------------------------------- build
def build(scored: pd.DataFrame, history: pd.DataFrame, patterns: pd.DataFrame | None,
          model_version: str, thresholds: dict | None) -> dict[str, pd.DataFrame]:
    s = scored.copy()
    s["timestamp"] = pd.to_datetime(s["timestamp"], format="%Y/%m/%d %H:%M")
    s["from_account_key"] = account_key(s["from_bank"], s["from_account"])
    s["to_account_key"] = account_key(s["to_bank"], s["to_account"])
    s["amount_usd"] = pd.to_numeric(s["amount_paid"], errors="coerce").fillna(0.0)
    s["transaction_id"] = s["transaction_id"].astype("int64")
    s["is_laundering"] = pd.to_numeric(s["is_laundering"], errors="coerce").fillna(0).astype(int)

    # ---- Transaction
    transactions = pd.DataFrame({
        "transaction_id": s["transaction_id"],
        "timestamp": s["timestamp"],
        "from_account": s["from_account_key"],
        "to_account": s["to_account_key"],
        "from_bank": s["from_bank"].astype(str),
        "to_bank": s["to_bank"].astype(str),
        "amount_usd": s["amount_usd"],
        "amount_received": pd.to_numeric(s["amount_received"], errors="coerce"),
        "payment_currency": s["payment_currency"],
        "receiving_currency": s["receiving_currency"],
        "payment_format": s["payment_format"],
        "laundering_probability": s["laundering_probability"].astype(float),
        "risk_band": s["risk_band"],
        "is_laundering_ground_truth": s["is_laundering"],
    })

    # ---- TransactionRiskScore (one row per txn per model version)
    scored_ts = pd.Timestamp.utcnow().tz_localize(None).floor("s")
    risk_scores = pd.DataFrame({
        "score_id": s["transaction_id"].astype(str) + "|" + model_version,
        "transaction_id": s["transaction_id"],
        "laundering_probability": s["laundering_probability"].astype(float),
        "risk_band": s["risk_band"],
        "model_version": model_version,
        "scored_ts": scored_ts,
    })

    # ---- Account (24h window as of latest activity; history included so
    #      accounts active before the stream still get a profile)
    h = history.copy()
    h["timestamp"] = pd.to_datetime(h["timestamp"], format="%Y/%m/%d %H:%M")
    h["amount_usd"] = pd.to_numeric(h["amount_paid"], errors="coerce").fillna(0.0)
    h["from_account_key"] = account_key(h["from_bank"], h["from_account"])
    h["to_account_key"] = account_key(h["to_bank"], h["to_account"])
    h["laundering_probability"] = np.nan
    cols = ["timestamp", "from_account_key", "to_account_key", "amount_usd", "laundering_probability"]
    allx = pd.concat([h[cols], s[cols]], ignore_index=True)
    out_e = allx.rename(columns={"from_account_key": "account_id"})[["account_id", "timestamp", "amount_usd", "laundering_probability"]].assign(direction="out")
    in_e = allx.rename(columns={"to_account_key": "account_id"})[["account_id", "timestamp", "amount_usd", "laundering_probability"]].assign(direction="in")
    edges = pd.concat([out_e, in_e], ignore_index=True)
    last_ts = edges.groupby("account_id")["timestamp"].max().rename("last_active_ts")
    edges = edges.join(last_ts, on="account_id")
    recent = edges[edges["timestamp"] >= edges["last_active_ts"] - pd.Timedelta(hours=24)]
    vol = recent.pivot_table(index="account_id", columns="direction", values="amount_usd", aggfunc="sum", fill_value=0.0)
    cnt = edges.groupby("account_id").agg(
        total_txn_count=("amount_usd", "size"),
        counterparty_count=("account_id", "size"),  # placeholder, replaced below
    )
    # distinct counterparties
    cp = pd.concat([
        allx[["from_account_key", "to_account_key"]].rename(columns={"from_account_key": "account_id", "to_account_key": "cp"}),
        allx[["to_account_key", "from_account_key"]].rename(columns={"to_account_key": "account_id", "from_account_key": "cp"}),
    ]).drop_duplicates().groupby("account_id")["cp"].nunique().rename("counterparty_count")
    max_risk = edges.groupby("account_id")["laundering_probability"].max().rename("max_risk_score")
    n_high = s[s["risk_band"] == "High"]
    high_cnt = pd.concat([n_high["from_account_key"], n_high["to_account_key"]]).value_counts().rename("high_risk_txn_count")
    accounts = (
        pd.DataFrame(index=edges["account_id"].unique())
        .join(vol).join(last_ts).join(cnt[["total_txn_count"]]).join(cp).join(max_risk).join(high_cnt)
        .rename(columns={"in": "volume_24h_inbound", "out": "volume_24h_outbound"})
        .fillna({"volume_24h_inbound": 0.0, "volume_24h_outbound": 0.0, "max_risk_score": 0.0, "high_risk_txn_count": 0, "counterparty_count": 0})
        .reset_index().rename(columns={"index": "account_id"})
    )
    accounts["bank_id"] = accounts["account_id"].str.split("|").str[0]
    accounts["high_risk_txn_count"] = accounts["high_risk_txn_count"].astype(int)
    accounts["counterparty_count"] = accounts["counterparty_count"].astype(int)
    accounts["total_txn_count"] = accounts["total_txn_count"].astype(int)
    accounts["risk_tier"] = pd.cut(accounts["max_risk_score"],
                                   bins=[-1, (thresholds or {}).get("medium", 0.35), (thresholds or {}).get("high", 0.62), 2],
                                   labels=["Low", "Medium", "High"]).astype(str)
    accounts = accounts[["account_id", "bank_id", "volume_24h_inbound", "volume_24h_outbound",
                         "total_txn_count", "counterparty_count", "max_risk_score", "risk_tier",
                         "high_risk_txn_count", "last_active_ts"]]

    # ---- ground-truth patterns (demo reveal layer)
    gt = None
    if patterns is not None and len(patterns):
        pt = patterns.copy()
        pt["timestamp"] = pd.to_datetime(pt["timestamp"], format="%Y/%m/%d %H:%M")
        key = ["timestamp", "from_bank", "from_account", "to_bank", "to_account", "amount_paid", "payment_format"]
        s_key = s[["transaction_id"] + key].copy()
        s_key["amount_paid"] = s_key["amount_paid"].astype(float).round(2)
        pt["amount_paid"] = pt["amount_paid"].round(2)
        for c in ("from_bank", "to_bank", "from_account", "to_account"):
            s_key[c] = s_key[c].astype(str); pt[c] = pt[c].astype(str)
        gt = s_key.merge(pt, on=key, how="inner").drop_duplicates("transaction_id")
        gt = gt[["transaction_id", "pattern_id", "true_typology"]]
        gt["pattern_id"] = "HI-Small-P" + gt["pattern_id"].astype(str).str.zfill(4)

    # ---- Alert (High + Medium band)
    a = s[s["risk_band"].isin(["High", "Medium"])].copy()
    a = a.sort_values("laundering_probability", ascending=False)
    a["alert_id"] = "ALT-" + a["transaction_id"].astype(str)
    a["from_account"] = a["from_account_key"]; a["to_account"] = a["to_account_key"]
    a["subject_account_id"] = a["from_account_key"]
    a["counterparty_account_id"] = a["to_account_key"]
    a["priority"] = np.where(a["risk_band"] == "High", "P1",
                     np.where(a["laundering_probability"] >= a["laundering_probability"].quantile(0.75), "P2", "P3"))
    txn_graph = pd.concat([h[["timestamp", "from_account_key", "to_account_key", "amount_usd"]],
                           s[["timestamp", "from_account_key", "to_account_key", "amount_usd"]]], ignore_index=True)
    txn_graph = txn_graph.rename(columns={"from_account_key": "from_account", "to_account_key": "to_account"})
    a["primary_typology"] = derive_typology(a, txn_graph)
    alerts = pd.DataFrame({
        "alert_id": a["alert_id"],
        "transaction_id": a["transaction_id"],
        "subject_account_id": a["subject_account_id"],
        "counterparty_account_id": a["counterparty_account_id"],
        "status": "Open",
        "priority": a["priority"],
        "primary_typology": a["primary_typology"].to_numpy(),
        "laundering_probability": a["laundering_probability"].astype(float),
        "risk_band": a["risk_band"],
        "amount_usd": a["amount_usd"],
        "payment_format": a["payment_format"],
        "alerted_ts": a["timestamp"],
        "model_version": model_version,
        "case_id": pd.Series([None] * len(a), index=a.index, dtype="object"),
    })
    if gt is not None:
        alerts = alerts.merge(gt, on="transaction_id", how="left")
    else:
        alerts["pattern_id"] = None; alerts["true_typology"] = None
    alerts["is_laundering_ground_truth"] = alerts["transaction_id"].map(s.set_index("transaction_id")["is_laundering"]).astype(int)

    # ---- InvestigationCase (empty, schema only — created by the escalate action)
    cases = pd.DataFrame({
        "case_id": pd.Series(dtype="object"), "title": pd.Series(dtype="object"),
        "analyst_notes": pd.Series(dtype="object"), "sar_required": pd.Series(dtype="bool"),
        "case_status": pd.Series(dtype="object"), "opened_ts": pd.Series(dtype="datetime64[ns]"),
        "sar_draft": pd.Series(dtype="object"),
    })

    # ---- evaluation summary (labeled stream makes this possible)
    y = s["is_laundering"].to_numpy(); p = s["laundering_probability"].to_numpy()
    rows = []
    for band in ("High", "Medium", "Low"):
        m = (s["risk_band"] == band).to_numpy()
        rows.append({"metric": f"band_{band}", "n": int(m.sum()),
                     "precision": float(y[m].mean()) if m.sum() else 0.0,
                     "recall": float(y[m].sum() / max(y.sum(), 1))})
    order = np.argsort(-p)
    for k in (100, 500, 1000, 5000):
        rows.append({"metric": f"precision_at_{k}", "n": k, "precision": float(y[order[:k]].mean()),
                     "recall": float(y[order[:k]].sum() / max(y.sum(), 1))})
    evaluation = pd.DataFrame(rows).assign(model_version=model_version, positives=int(y.sum()), total=len(y))

    return {
        "transactions": transactions,
        "transaction_risk_scores": risk_scores,
        "accounts_summary": accounts,
        "alerts": alerts,
        "investigation_cases": cases,
        "laundering_patterns": gt if gt is not None else pd.DataFrame(columns=["transaction_id", "pattern_id", "true_typology"]),
        "model_evaluation": evaluation,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scored", required=True)
    ap.add_argument("--history", nargs="+", required=True)
    ap.add_argument("--patterns")
    ap.add_argument("--model-version", required=True)
    ap.add_argument("--thresholds", help="json like {\"high\":0.62,\"medium\":0.35}")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    import json
    scored = pd.read_parquet(args.scored) if args.scored.endswith(".parquet") else pd.read_csv(args.scored, dtype=RAW_DTYPES)
    history = pd.concat([pd.read_csv(f, dtype=RAW_DTYPES) for f in args.history], ignore_index=True)
    patterns = parse_patterns(args.patterns) if args.patterns else None
    thresholds = json.loads(args.thresholds) if args.thresholds else None
    tables = build(scored, history, patterns, args.model_version, thresholds)
    os.makedirs(args.out, exist_ok=True)
    for name, df in tables.items():
        df.to_parquet(os.path.join(args.out, f"{name}.parquet"), index=False)
        print(f"{name:28s} {len(df):>9,} rows  cols={list(df.columns)[:6]}{'...' if len(df.columns) > 6 else ''}")
    al = tables["alerts"]
    print("\nalerts by band/priority:\n", al.groupby(["risk_band", "priority"]).size().to_string())
    print("\nderived typology vs ground truth (alerts that are true laundering):")
    tl = al[al["is_laundering_ground_truth"] == 1]
    print(pd.crosstab(tl["primary_typology"], tl["true_typology"].fillna("(unmatched)")).to_string())


if __name__ == "__main__":
    main()
