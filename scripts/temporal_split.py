"""Strict chronological 70/10/20 split of the IBM AML HI-Small transactions.

Reads data/raw/HI-Small_Trans.csv, renames headers to unique snake_case
(the raw file has two columns literally named "Account", which breaks
Foundry schema inference), assigns a stable transaction_id, sorts by
timestamp (stable sort preserves file order within the same minute), and
writes:
  data/processed/train_temporal.csv  (earliest 70%)
  data/processed/val_temporal.csv    (next 10%)
  data/processed/test_stream.csv     (latest 20%)
"""
import pandas as pd

RAW = "data/raw/HI-Small_Trans.csv"
OUT = "data/processed"

COLS = [
    "timestamp", "from_bank", "from_account", "to_bank", "to_account",
    "amount_received", "receiving_currency", "amount_paid",
    "payment_currency", "payment_format", "is_laundering",
]

df = pd.read_csv(RAW, dtype=str)
df.columns = COLS
df["transaction_id"] = df.index.astype("int64")

ts = pd.to_datetime(df["timestamp"], format="%Y/%m/%d %H:%M")
order = ts.argsort(kind="stable")
df = df.iloc[order].reset_index(drop=True)

n = len(df)
n_train = int(n * 0.70)
n_val = int(n * 0.10)

splits = {
    "train_temporal.csv": df.iloc[:n_train],
    "val_temporal.csv": df.iloc[n_train:n_train + n_val],
    "test_stream.csv": df.iloc[n_train + n_val:],
}
front = ["transaction_id"] + COLS
for name, part in splits.items():
    part[front].to_csv(f"{OUT}/{name}", index=False)
    pos = part["is_laundering"].astype(int).mean()
    print(f"{name}: rows={len(part)} span=[{part['timestamp'].iloc[0]} .. "
          f"{part['timestamp'].iloc[-1]}] positive_rate={pos:.5f}")
print(f"total={n}")
