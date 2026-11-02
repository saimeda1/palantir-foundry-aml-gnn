"""Create/refresh Foundry datasets from local parquet files and register a
parquet schema, so they are immediately usable as Ontology backing datasets.

    foundry run-with-auth 'python scripts/upload_parquet_datasets.py \
        --folder ri.compass.main.folder.<03_Scored_Data> \
        --map scored_transactions_stream=data/scored/transactions.parquet ...'

Uses FOUNDRY_TOKEN / FOUNDRY_HOSTNAME injected by `foundry run-with-auth`.
Existing datasets with the same name in the folder are refreshed with a new
SNAPSHOT transaction (idempotent re-runs). Timestamps are coerced to
milliseconds (Spark cannot read nanosecond parquet timestamps).
"""
import argparse
import json
import os
import sys
import tempfile

import pyarrow as pa
import pyarrow.parquet as pq
import requests

HOST = "https://" + os.environ["FOUNDRY_HOSTNAME"]
H = {"Authorization": f"Bearer {os.environ['FOUNDRY_TOKEN']}"}

CAMEL = False


def snake_to_camel(name: str) -> str:
    """transaction_id -> transactionId; volume_24h_inbound -> volume24hInbound.
    Needed because ontology-as-code (@osdk/maker) maps each property to the
    column of the same name and property API names are camelCase."""
    parts = name.split("_")
    return parts[0] + "".join(w[:1].upper() + w[1:] for w in parts[1:])


PA_TO_FOUNDRY = {
    "int64": "LONG", "int32": "INTEGER", "int16": "INTEGER", "int8": "INTEGER",
    "double": "DOUBLE", "float": "FLOAT", "bool": "BOOLEAN", "string": "STRING",
    "large_string": "STRING", "timestamp[ms]": "TIMESTAMP", "timestamp[us]": "TIMESTAMP",
    "timestamp[ns]": "TIMESTAMP", "date32[day]": "DATE",
}


def existing(folder: str) -> dict[str, str]:
    r = requests.get(f"{HOST}/api/v2/filesystem/folders/{folder}/children", params={"preview": "true"}, headers=H)
    r.raise_for_status()
    return {c["displayName"]: c["rid"] for c in r.json()["data"] if c["type"] == "FOUNDRY_DATASET"}


def foundry_schema(table: pa.Table) -> dict:
    fields = []
    for f in table.schema:
        t = str(f.type)
        if t.startswith("timestamp"):
            t = "timestamp[ms]"
        if t.startswith("dictionary"):
            t = "string"
        ft = PA_TO_FOUNDRY.get(t)
        if ft is None:
            raise SystemExit(f"unsupported arrow type {f.type} for column {f.name}")
        fields.append({"name": f.name, "type": ft, "nullable": True, "customMetadata": {}})
    return {"fieldSchemaList": fields,
            "dataFrameReaderClass": "com.palantir.foundry.spark.input.ParquetDataFrameReader",
            "customMetadata": {"format": "parquet"}}


def upload(name: str, path: str, folder: str, rids: dict[str, str]) -> str:
    table = pq.read_table(path)
    # normalise: ns timestamps -> ms, null-typed empty columns -> string
    cols = []
    for f in table.schema:
        col = table[f.name]
        if pa.types.is_timestamp(f.type):
            col = col.cast(pa.timestamp("ms"))
        elif pa.types.is_null(f.type):
            col = col.cast(pa.string())
        elif pa.types.is_dictionary(f.type):
            col = col.cast(pa.string())
        cols.append(col)
    names = table.column_names
    if CAMEL:
        names = [snake_to_camel(n) for n in names]
    table = pa.table(cols, names=names)

    rid = rids.get(name)
    if rid is None:
        r = requests.post(f"{HOST}/api/v2/datasets", headers=H, json={"name": name, "parentFolderRid": folder})
        r.raise_for_status(); rid = r.json()["rid"]; print(f"  created {name} {rid}")
    else:
        print(f"  refreshing {name} {rid}")
    r = requests.post(f"{HOST}/api/v2/datasets/{rid}/transactions", headers=H, json={"transactionType": "SNAPSHOT"})
    r.raise_for_status(); txn = r.json()["rid"]
    with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp:
        pq.write_table(table, tmp.name, coerce_timestamps="ms", allow_truncated_timestamps=True, compression="snappy")
        size = os.path.getsize(tmp.name)
        with open(tmp.name, "rb") as fh:
            r = requests.post(f"{HOST}/api/v2/datasets/{rid}/files/{name}.parquet/upload",
                              params={"transactionRid": txn}, headers={**H, "Content-Type": "application/octet-stream"}, data=fh)
        r.raise_for_status()
    os.unlink(tmp.name)
    r = requests.post(f"{HOST}/api/v2/datasets/{rid}/transactions/{txn}/commit", headers=H); r.raise_for_status()
    r = requests.post(f"{HOST}/foundry-metadata/api/schemas/datasets/{rid}/branches/master",
                      headers={**H, "Content-Type": "application/json"}, data=json.dumps(foundry_schema(table)))
    print(f"  {name}: {table.num_rows:,} rows, {size/1e6:.1f} MB uploaded, schema HTTP {r.status_code}")
    return rid


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--folder", required=True)
    ap.add_argument("--map", nargs="+", required=True, help="name=path.parquet ...")
    ap.add_argument("--camel", action="store_true", help="rename snake_case columns to camelCase")
    args = ap.parse_args()
    global CAMEL
    CAMEL = args.camel
    rids = existing(args.folder)
    out = {}
    for item in args.map:
        name, path = item.split("=", 1)
        out[name] = upload(name, path, args.folder, rids)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
