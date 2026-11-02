#!/bin/bash
# Idempotent pipeline: download each IBM AML Kaggle file, upload to a Foundry
# dataset in 01_Raw_Data/kaggle_full, apply schema (CSVs), delete local copy.
# Safe to re-run: finished files are skipped via .done markers; downloads resume.
# Must run from the project root (foundry.yml context for run-with-auth).
set -u
cd "$(dirname "$0")/.."

KAGGLE_BASE="https://www.kaggle.com/api/v1/datasets/download/ealtman2019/ibm-transactions-for-anti-money-laundering-aml"
FOLDER_RID="ri.compass.main.folder.d7dcb934-e5e1-4300-bc26-05566fb42b92"
WORK="data/kaggle"
STATE="$WORK/.state"
CHUNK_LINES=5000000   # ~500MB per chunk (gateway 500s on ~2GB uploads)
mkdir -p "$WORK" "$STATE"

# Ordered small -> large so useful data lands first
FILES=(
  "HI-Small_Patterns.txt"
  "LI-Small_Patterns.txt"
  "LI-Medium_Patterns.txt"
  "HI-Medium_Patterns.txt"
  "HI-Large_Patterns.txt"
  "LI-Large_Patterns.txt"
  "LI-Small_Trans.csv"
  "HI-Medium_Trans.csv"
  "LI-Medium_Trans.csv"
  "HI-Large_Trans.csv"
  "LI-Large_Trans.csv"
)

log() { echo "[$(date '+%H:%M:%S')] $*"; }

fapi() {  # fapi <output-file> <curl args...> ; echoes HTTP code
  local out=$1; shift
  local args="$*"
  foundry run-with-auth "curl -s -H \"Authorization: Bearer \${FOUNDRY_TOKEN}\" $args -o $out -w '%{http_code}'" 2>/dev/null | tail -1
}

write_schema_json() {  # headerless CSV schema (skipLines=0)
  cat > "$WORK/.schema.json" <<'EOF'
{
  "fieldSchemaList": [
    {"name": "timestamp", "type": "STRING", "nullable": true, "customMetadata": {}},
    {"name": "from_bank", "type": "STRING", "nullable": true, "customMetadata": {}},
    {"name": "from_account", "type": "STRING", "nullable": true, "customMetadata": {}},
    {"name": "to_bank", "type": "STRING", "nullable": true, "customMetadata": {}},
    {"name": "to_account", "type": "STRING", "nullable": true, "customMetadata": {}},
    {"name": "amount_received", "type": "DOUBLE", "nullable": true, "customMetadata": {}},
    {"name": "receiving_currency", "type": "STRING", "nullable": true, "customMetadata": {}},
    {"name": "amount_paid", "type": "DOUBLE", "nullable": true, "customMetadata": {}},
    {"name": "payment_currency", "type": "STRING", "nullable": true, "customMetadata": {}},
    {"name": "payment_format", "type": "STRING", "nullable": true, "customMetadata": {}},
    {"name": "is_laundering", "type": "INTEGER", "nullable": true, "customMetadata": {}}
  ],
  "dataFrameReaderClass": "com.palantir.foundry.spark.input.TextDataFrameReader",
  "customMetadata": {
    "textParserParams": {
      "parser": "CSV_PARSER", "charsetName": "UTF-8", "fieldDelimiter": ",",
      "recordDelimiter": "\n", "quoteCharacter": "\"", "dateFormat": {},
      "skipLines": 0, "jaggedRowBehavior": "THROW_EXCEPTION",
      "parseErrorBehavior": "THROW_EXCEPTION", "addFilePath": false,
      "addFilePathInsteadOfUri": false, "addByteOffset": false, "addImportedAt": false
    }
  }
}
EOF
}

json_field() { .venv/bin/python -c "import json,sys; print(json.load(open('$1')).get('$2',''))"; }

process_file() {
  local fname=$1
  local stem="${fname%.*}"
  local marker="$STATE/done_$stem"
  [ -f "$marker" ] && { log "SKIP $fname (already uploaded)"; return 0; }

  local local_path="$WORK/$fname"
  # ---- download with resume, up to 5 attempts ----
  local attempt=0 code=1
  while [ $attempt -lt 5 ]; do
    attempt=$((attempt + 1))
    log "download $fname (attempt $attempt)"
    curl -sL -C - -o "$local_path" "$KAGGLE_BASE/$fname" && code=0 && break
    sleep 10
  done
  [ $code -ne 0 ] && { log "FAILED download $fname"; return 1; }
  log "downloaded $fname ($(du -h "$local_path" | cut -f1))"

  # ---- create dataset (reuse an existing one with the same name) ----
  local http rid
  http=$(fapi "$WORK/.children.json" "\"https://\${FOUNDRY_HOSTNAME}/api/v2/filesystem/folders/$FOLDER_RID/children?preview=true&pageSize=100\"")
  rid=$(.venv/bin/python -c "
import json
for r in json.load(open('$WORK/.children.json')).get('data', []):
    if r.get('displayName') == '$stem':
        print(r['rid']); break")
  if [ -n "$rid" ]; then
    log "dataset $stem exists -> $rid (reusing)"
  else
    printf '{"name":"%s","parentFolderRid":"%s"}' "$stem" "$FOLDER_RID" > "$WORK/.req.json"
    http=$(fapi "$WORK/.ds.json" -X POST -H '"Content-Type: application/json"' -d @"$WORK/.req.json" "\"https://\${FOUNDRY_HOSTNAME}/api/v2/datasets\"")
    rid=$(json_field "$WORK/.ds.json" rid)
    if [ -z "$rid" ]; then log "FAILED dataset create $stem (HTTP $http)"; return 1; fi
    log "dataset $stem -> $rid"
  fi

  # ---- open transaction (abort any dangling OPEN transaction on 409) ----
  printf '{"transactionType":"SNAPSHOT"}' > "$WORK/.req.json"
  http=$(fapi "$WORK/.txn.json" -X POST -H '"Content-Type: application/json"' -d @"$WORK/.req.json" "\"https://\${FOUNDRY_HOSTNAME}/api/v2/datasets/$rid/transactions\"")
  local txn; txn=$(json_field "$WORK/.txn.json" rid)
  if [ -z "$txn" ] && [ "$http" = "409" ]; then
    log "409 on $stem: aborting dangling open transaction"
    fapi "$WORK/.rev.json" "\"https://\${FOUNDRY_HOSTNAME}/foundry-catalog/api/catalog/datasets/$rid/reverse-transactions2/master?pageSize=5&includeOpenExclusiveTransaction=true\"" >/dev/null
    local dangling
    dangling=$(.venv/bin/python -c "
import json
for v in json.load(open('$WORK/.rev.json')).get('values', []):
    if v['transaction']['status'] == 'OPEN':
        print(v['rid']); break")
    [ -n "$dangling" ] && fapi /dev/null -X POST "\"https://\${FOUNDRY_HOSTNAME}/api/v2/datasets/$rid/transactions/$dangling/abort\"" >/dev/null
    http=$(fapi "$WORK/.txn.json" -X POST -H '"Content-Type: application/json"' -d @"$WORK/.req.json" "\"https://\${FOUNDRY_HOSTNAME}/api/v2/datasets/$rid/transactions\"")
    txn=$(json_field "$WORK/.txn.json" rid)
  fi
  [ -z "$txn" ] && { log "FAILED transaction open $stem (HTTP $http)"; return 1; }

  # ---- prepare upload parts ----
  local parts_dir="$WORK/parts_$stem"
  rm -rf "$parts_dir"; mkdir -p "$parts_dir"
  case "$fname" in
    *.csv)  tail -n +2 "$local_path" | split -l $CHUNK_LINES - "$parts_dir/part_" ;;
    *)      cp "$local_path" "$parts_dir/part_aa" ;;
  esac

  # ---- upload each part with retries ----
  local ok=1 i=0
  for part in "$parts_dir"/part_*; do
    i=$((i + 1))
    local target
    case "$fname" in
      *.csv) target=$(printf "part-%04d.csv" $i) ;;
      *)     target="$fname" ;;
    esac
    local pa=0 pcode=""
    while [ $pa -lt 3 ]; do
      pa=$((pa + 1))
      # -T streams from disk (no in-memory buffering, required for 2GB chunks)
      pcode=$(fapi /dev/null -X POST -H '"Content-Type: application/octet-stream"' -T "$part" "\"https://\${FOUNDRY_HOSTNAME}/api/v2/datasets/$rid/files/$target/upload?transactionRid=$txn\"")
      [ "$pcode" = "200" ] && break
      log "retry upload $target (HTTP $pcode)"
      sleep 15
    done
    if [ "$pcode" != "200" ]; then ok=0; break; fi
    log "uploaded $target ($(du -h "$part" | cut -f1))"
  done
  rm -rf "$parts_dir"
  [ $ok -ne 1 ] && { log "FAILED upload $stem; aborting transaction"; fapi /dev/null -X POST "\"https://\${FOUNDRY_HOSTNAME}/api/v2/datasets/$rid/transactions/$txn/abort\"" >/dev/null; return 1; }

  # ---- commit ----
  http=$(fapi /dev/null -X POST "\"https://\${FOUNDRY_HOSTNAME}/api/v2/datasets/$rid/transactions/$txn/commit\"")
  [ "$http" != "200" ] && { log "FAILED commit $stem (HTTP $http)"; return 1; }

  # ---- schema for CSVs ----
  case "$fname" in
    *.csv)
      write_schema_json
      http=$(fapi /dev/null -X POST -H '"Content-Type: application/json"' -d @"$WORK/.schema.json" "\"https://\${FOUNDRY_HOSTNAME}/foundry-metadata/api/schemas/datasets/$rid/branches/master\"")
      log "schema $stem HTTP $http"
      ;;
  esac

  echo "$rid" > "$marker"
  rm -f "$local_path"
  log "DONE $fname -> $stem ($rid)"
}

log "=== pipeline start ==="
FAILED=0
for f in "${FILES[@]}"; do
  process_file "$f" || FAILED=$((FAILED + 1))
done
log "=== pipeline finished; failures: $FAILED ==="
