# AML GNN on Palantir Foundry — Project Handoff

**Last updated:** 2026-10-29 (model published; see §3 for the publish path) · **Owner:** Vinay Meda (`meda@purdue.edu`, Multipass user id `d71afdaa-5829-449e-90b1-bb925db2e086`)
**Enrollment:** https://saisplayground.usw-17.palantirfoundry.com

---

## 1. What this project is

A proof of concept for banks/regulators: a state-of-the-art AML (anti-money-laundering)
GNN trained and run **entirely on Palantir Foundry**, scoring transactions so flagged
activity can be investigated through the Foundry Ontology, Workshop, Vertex graph
views, and an AIP SAR-drafting assistant. Model quality target: "solid to good" —
credibility comes from using the published state-of-the-art architecture, not from
beating the paper's numbers.

**Division of labor:** Claude owns data/GNN/training/scoring; the user owns the
ontology application, Workshop UI, and AIP configuration (specs are drafted, see §6).

## 2. Papers & external resources

| Resource | Link |
|---|---|
| Method paper: Egressy et al., *Provably Powerful GNNs for Directed Multigraphs* (AAAI 2024) | https://arxiv.org/abs/2306.11586 |
| Dataset paper: Altman et al., *Realistic Synthetic Financial Transactions for AML Models* (NeurIPS 2023, "AMLworld") | https://arxiv.org/abs/2306.16424 |
| IBM reference implementation | https://github.com/IBM/Multi-GNN |
| Kaggle dataset (source of all raw data) | https://www.kaggle.com/datasets/ealtman2019/ibm-transactions-for-anti-money-laundering-aml |
| PyTorch Geometric docs | https://pytorch-geometric.readthedocs.io |

**Model = the paper's three adaptations on a GINE backbone:** reverse message passing
(per-direction conv weights), port numbering (chronological in/out edge ranks as edge
features — global variant, not per-subgraph), ego IDs (seed endpoints flagged per batch
— batched variant), plus BatchNorm everywhere (its absence caused NaN divergence),
focal loss (α=.95, γ=2) for the ~0.1% positive rate, and **history-inclusive
evaluation** (val/test seeds scored over a graph that includes earlier edges — the
paper's protocol; training message-passes over train edges only).

## 3. Foundry state (what exists on the enrollment)

### Project `/Sai's Playground-509041/AML_Compliance_Platform`
(rid `ri.compass.main.folder.2c7fe3fd-cdc3-4040-b4a1-f3e6a755c93a`)

**`01_Raw_Data/`** — HI-Small split chronologically 70/10/20 (no future leakage):
| Dataset | Rows | RID |
|---|---|---|
| `raw_transactions_train` | 3,554,841 (Sep 1–7, pos 0.080%) | `ri.foundry.main.dataset.f659e2b2-41cc-4aad-9111-e31a0edb1e6a` |
| `raw_transactions_val` | 507,834 (Sep 7–8, pos 0.103%) | `ri.foundry.main.dataset.4a742420-545e-4995-b354-658b3c968c1e` |
| `raw_transactions_test_stream` | 1,015,670 (Sep 8–18, pos 0.177%) | `ri.foundry.main.dataset.b479a5c3-59cc-4075-8da0-52b8d9f4d24d` |

Columns (snake_case; raw Kaggle file has duplicate "Account" headers — renamed):
`transaction_id, timestamp, from_bank, from_account, to_bank, to_account,
amount_received, receiving_currency, amount_paid, payment_currency, payment_format,
is_laundering`.

**`01_Raw_Data/kaggle_full/`** — all 11 Kaggle files (~22GB), full-file datasets:
`HI/LI-{Small,Medium,Large}_Trans` (Large ≈ 175M rows each, stored as ~36 headerless
500MB CSV chunks per dataset) + six `*_Patterns` ground-truth text files.
Notable RIDs: `HI-Medium_Trans` = `...710cd14e-f183-4ba7-a929-72f533f93025`,
`HI-Large_Trans` = `...7245f3b8-349a-4a46-bb29-d899f39d05c3`.

**`02_Models/`** — `gnn_training_code` dataset
(`ri.foundry.main.dataset.ec53b956-0779-405f-9d15-9ed61ada4617`): the synced Python
modules, PLUS binary repair bundles (`abseil_2407_libs.tar.gz`, `libtorch_part_aa/ab/ac`
+ `pytorch_cuda120.tar.gz` — a complete coherent torch build, kept as env insurance).
**PUBLISHED 2026-10-29:** model `aml_gnn_hi_small` =
`ri.models.main.model.6f8e161b-348d-402f-a57b-3a8c59ed3981` (lives in the WORKSPACE project
"Sai's demo playground", sidebar-created), version 1 =
`ri.models.main.model-version.5f131650-5723-40a5-9d29-aa58b7960f3b` (39-epoch run, best epoch 33,
val PR-AUC 0.564 / best-F1 0.584, fanout 50,30, hidden 96, no edge updates). Checkpoint copies:
dataset `aml_model_checkpoints` (`ri.foundry.main.dataset.72743b94-797c-4a94-89b8-e9d5ebb8952e`,
in-project, alias registered) and `gnn_training_code/aml_gnn_hi_small_epoch33.pt`.

**HOW PUBLISHING WORKS HERE (cost 2 days — read):** the interactive workspace session CANNOT
publish: its sidecar deployment token is denied artifact writes
(`Artifacts:WriteArtifactPermissionDenied`) on every model, in-project or not, fresh session or
not; overriding the token is rejected (`InvalidDeploymentToken`). Models created via the public
API get an immutable `container` source and are useless to the workspace. The working path:
Models sidebar → *Create new model* (in the workspace's own project; cross-project resources
need a project reference) → model card → **Publish as transform output** → notebook
`publish_model.ipynb` (downloads checkpoint from `aml_model_checkpoints`, loads into the
self-contained `aml_gnn_adapter.py` bundle, `ModelOutput(alias).publish`) → *Sync and run*.
The panel writes `.transforms/<uuid>.yml`; its resources copy the workspace profile and must be
edited down (build cap 8 cpu; set 4 cpu/16G, no gpu). Re-publishing a new checkpoint = upload
`.pt` to `aml_model_checkpoints` (SNAPSHOT txn) → *Rebuild* that transform. Publishing needs
`aml_gnn_adapter.py` (generated by `build_adapter_bundle.py` from graph_builder+model+
model_adapter) because Foundry packages only the adapter's own file.
Model resource for it exists (created via `POST /api/v2/models?preview=true`, lives in the
workspace project folder, not 02_Models): `ri.models.main.model.81e1f9f3-6db3-49a1-8d53-172661721b50`,
registered in the workspace repo as `.foundry/model-assets.yml` (alias → rid).
2026-10-25: a 5-epoch run (val PR-AUC 0.37, ROC-AUC 0.986) was LOST because the alias
was missing at publish time; `train_gnn_foundry.py` now resolves the alias before training,
checkpoints the adapter to `~/repo/checkpoints/<alias>.pt` (gitignored) before publishing,
and `publish_checkpoint.py <alias>` publishes a checkpoint without retraining.
`AML_SKIP_PUBLISH=1` trains + checkpoints only.

**`03_Scored_Data/`** — POPULATED 2026-10-29 (parquet, schemas applied, built locally by
`foundry_code/transforms/build_backing_datasets_local.py` from the champion's scores and uploaded
with `scripts/upload_parquet_datasets.py`; re-run both to refresh):
| Dataset | Rows | RID |
|---|---|---|
| `scored_transactions_stream` (Transaction) | 1,015,670 | `...77edf771-f067-48bf-947f-43f5189fa776` |
| `transaction_risk_scores` | 1,015,670 | `...b83aab09-9d6c-45c0-a679-05f198e8106c` |
| `accounts_summary` (Account) | 515,088 | `...c808a42f-96b0-432a-a584-d0bfe44b3cc5` |
| `alerts` (High+Medium band; 269 P1 / 334 P2 / 1808 P3) | 2,411 | `...6e29110d-b2b8-4033-8aef-2c98f10f047f` |
| `investigation_cases` (empty seed) | 0 | `...15163afd-d20d-4bf2-995f-05abc44d3e98` |
| `laundering_patterns` (ground-truth typology, demo reveal) | 1,339 | `...744f4737-a16a-49e2-bc15-cf8789621e64` |
| `model_evaluation` | 7 | `...2144c316-fef1-4435-85b6-6c78a59f7818` |

**Champion test-stream metrics** (history-inclusive, sampled-protocol inference, 1,797 positives /
0.177%): PR-AUC 0.191, ROC-AUC 0.949, best-F1 0.266; High band (p≥0.623) n=269 precision 0.67;
Medium band n=2,142 precision 0.18; precision@100 0.91, @500 0.48, @1000 0.34, @5000 0.13.
Lower than val (0.56) mostly because `elapsed_days` is an absolute feature (train saw days 0–6,
test is days 7–17) — candidate fix for the challenger: drop it or make it cyclical/relative.
Local copies of everything: `data/scored/`. Ontology spec aligned to these columns:
`ontology/aml_ontology.yml` (v2).

### Workspace project "Sai's demo playground"
(rid `ri.compass.main.folder.e6cc3c24-5e1e-4639-9748-64d3f6795d67`)

- **"GNN workspace"** Jupyter Code Workspace, backed by git repo
  `ri.stemma.main.repository.40e1c1c0-43c1-4638-b616-f9e1f11d87f9`
  (clone/push: `https://<host>/stemma/git/<that rid>` with `Authorization: Bearer` header).
- **In-project dataset copies** (made because cross-project reads 403 without a
  panel-created project import; in-project needs none):
  `raw_transactions_train` = `...34f4564c-b748-4cf7-b99d-e9c9e00ea0df`,
  `raw_transactions_val` = `...85c349d7-792e-4d18-8e8b-cc1655d6c156`,
  `raw_transactions_test_stream` = `...dae9c876-cd96-442f-b63f-fa74992cfbff`.
- Compute: was 2× Tesla T4 + 16 vCPU + 186GB RAM; user moving to **2× H100 + 32 vCPU +
  256GB** on 2026-10-25. Profile change = env rebuild (pins + startup.sh self-heal make it
  safe). torch 2.3.1 cuda120 should carry sm_90 kernels; verify with `gpu_diag.py`
  (`arch_list` must list sm_90, else kernels PTX-JIT). Code trains on ONE GPU by design:
  the model is tiny and per-step overhead dominates, so a second GPU buys nothing.
  `/dev/shm` is only 64MB (matters — §7). Container reports 48 CPUs, cgroup grants fewer.

## 4. Local layout — `~/Desktop/Palantir_foundry_aml/`

- `foundry_code/model_training/` — **source of truth** for the model code:
  - `graph_builder.py` — accounts→nodes, 30-dim edge features (log amounts, time,
    payment/currency one-hots, 4 port features), `temporal_split()`
  - `model.py` — `AmlEdgeGNN` (bidirectional GINEConv + ego flags + BatchNorm), `focal_loss`
  - `training_core.py` — shared training loop (AMP off by default, grad clip, NaN guard,
    early stopping patience=4, history-inclusive eval, dataframe-ownership memory trick,
    worker spawn-context + file_system sharing)
  - `train_gnn_foundry.py` — workspace entry; env knobs `AML_TIER / AML_EPOCHS /
    AML_BATCH_SIZE / AML_NUM_WORKERS / AML_FANOUT / AML_MODEL_ALIAS`; publishes via
    `palantir_models.code_workspaces.ModelOutput`
  - `model_adapter.py` — `AmlGnnAdapter` (save/load/api/predict with optional
    `history_df`, GPU inference, risk bands from val-calibrated thresholds)
  - `score_large_tier.py` — chunked scorer for the 175M-row Large tiers
- `foundry_code/transforms/` + `foundry_code/repo_transforms/` — batch scoring &
  ontology-backing PySpark transforms; production Code-Repository package (parked —
  user chose the workspace path; revive if CI/CD or scheduled retraining is wanted)
- `ontology/aml_ontology.yml` — object/link/action spec (Account, Transaction,
  TransactionRiskScore, Alert, InvestigationCase; triageAlert / escalateToCase /
  closeFalsePositive)
- `foundry_code/workshop_aip/` — Workshop 4-page layout plan + AIP SAR-draft prompt
- `foundry_code/README.md` — deployment order & RIDs
- `gnn_workspace_repo/` — local clone of the workspace git (notebook + modules +
  `.envs/maestro/meta.yaml` + `.hooks/startup.sh` + `.foundry/aliases.yml`)
- `scripts/` — `temporal_split.py`, `kaggle_to_foundry.sh` (idempotent download→upload
  pipeline, resumable, 500MB chunking; rerun for new Kaggle files)
- `data/` — local HI-Small raw + split CSVs (source of the uploads)
- `.venv/` — local Python 3.12 (torch 2.13 + PyG 2.8) used for smoke tests & JSON tooling

## 5. The notebook (`train_aml_gnn.ipynb`, 6 cells)

**Presentable-run config (cell 4, set 2026-10-25):** `AML_EPOCHS=40` (upper bound,
`AML_PATIENCE=6` early stop), `AML_BATCH_SIZE=8192`, `AML_FANOUT=50,30` (reference impl
uses 100/hop; 15,10 was a T4 budget), `AML_HIDDEN=96`, `AML_LAYERS=2` (= len(fanout)),
`AML_LR=1e-3` with ReduceLROnPlateau(max, ×0.5, patience 2). Per-epoch log now shows
`val_best_f1` (F1 at best val threshold — the paper-comparable number; `f1@0.5` is not)
and lr. Every improving epoch overwrites `~/repo/checkpoints/<alias>.pt`.

1. Intro/prereqs · 2. Env+runtime diagnostics (cuda, sampling backend, /dev/shm) ·
3. Sync modules from `gnn_training_code` dataset into the workspace ·
4. Config via env vars · 5. Train→calibrate→publish (wraps errors to `last_error.txt`
since commits strip notebook outputs) · 6. Score the test stream with history context →
ROC/PR-AUC, Precision@K, risk bands, `scored_test_stream.parquet`.

**Module update flow:** edit locally → upload to `gnn_training_code` dataset (cell 3
pulls from there) → also commit/push to the workspace git for persistence. Cell 5
reloads the module chain, so cell 3 + rerun cell 5 picks up changes without kernel restart.

## 5b. Ontology-as-code (SuperRepo) — built, blocked only on bundle signing (2026-10-29)

The ontology is fully defined in code and packaged; only the final Marketplace install is pending.
- `ontology/src/ontology.mts` (@osdk/maker 0.83): 7 object types (`aml.amlTransaction`,
  `amlTransactionRiskScore`, `amlAccount`, `amlAlert`, `amlInvestigationCase`,
  `amlLaunderingPattern`, `amlModelEvaluation`), 8 one-to-many links, 5 actions
  (`aml-triage-alert`, `aml-close-false-positive`, `aml-assign-alert-to-case`, `aml-open-case`,
  `aml-update-case`). Property API names == dataset column names (camelCase; the 03_Scored_Data
  datasets were re-uploaded with camelCase columns via `scripts/upload_parquet_datasets.py --camel`).
- Toolchain: Foundry CLI **0.371.0** (self-updated from 0.253 — templates need ≥0.354), pnpm 12,
  `ontology/node_modules` (@osdk/maker, @osdk/maker-experimental). Build: `foundry build ontology`
  → `ontology/build/ontology_block_generator_result.json`; `foundry bundle --project-version 0.1.0`
  → `build/store.zip` (49KB); `foundry validate` passes with `env.yml` (71 input mappings:
  7 datasets + 64 columns, generated from the block inputs; `ontology_rid` =
  `ri.ontology.main.ontology.7e5cff5d-44c7-4469-8c18-00889446161a`).
- Deploy target created: Marketplace store `aml-investigator-ontology store`
  (`ri.marketplace.main.local.fcfb889c-96b7-47be-9f35-db7a14eb12af`) in the AML project.
- **BLOCKER:** `foundry deploy` requires a signed bundle; `foundry register` (generated key at
  `~/Library/Application Support/foundry-cli/keys/default.pem`) fails with
  `Marketplace:ContainingNamespaceMissingMavenGroupPrefix` — the enrollment's Marketplace namespace
  has no Maven group prefix configured (admin/Control Panel setting; mavenCoordinate is
  `com.saisplayground:aml-investigator-ontology`). Options: (a) admin sets the namespace's Maven
  group prefix, then `foundry register && foundry bundle --project-version 0.1.0 && foundry deploy
  --creator-role Owner`; (b) **tried and dead (2026-10-29):** Marketplace UI "New product ▾ →
  Upload to store" rejects `build/store.zip` with `malformedFile` (that screen only accepts signed
  store exports); (c) build by hand in Ontology Manager using
  `foundry_code/workshop_aip/ontology_build_guide.md` (45 min) — **the route to take**.
- Also tried: a second store in Sai's demo playground
  (`ri.marketplace.main.local.8f96b610-6ec9-449e-8582-91dc96f46362`, env file in the session
  scratchpad) → `foundry register` fails with the same error, so the missing prefix is
  enrollment-wide, not per space. That store is empty and can be deleted.

## 5c. Investigator console prototype (web page, 2026-10-31)

Vertex/Workshop/Quiver have no API, so the "alert network + evaluation" visual was built as a
standalone page from the local scored tables: https://claude.ai/artifact/LR3mHKyiETWkbcv9B1tqp8
(private artifact). Inbox of 41 alerts (top-36 by probability + one per typology + 4 Medium),
±72h two-hop neighbourhood per alert (hop1 cap 100 txns/account, hop2 40 accounts × 6),
ground-truth reveal (pattern siblings as dashed violet edges), rule-based network summary
(fan-out/fan-in/pass-through/cycle), and an evaluation tab (precision@k, band precision,
score histogram, typology confusion, model_evaluation table). It is the visual spec for the
Workshop build in `ontology_build_guide.md` §4–5.
Rebuild: `.venv/bin/python foundry_code/workshop_aip/prototype/build_alert_network_data.py`
(writes data.json to the session scratchpad; edit the output path), then inject into
`foundry_code/workshop_aip/prototype/aml_alert_network.template.html` at `__DATA__`.
Ontology status 2026-10-31: user built all 7 object types + 8 links by hand in Ontology Manager
(verified: alert → concerns/subject/counterparty, transaction → hasScore, account → sent).
Actions and Vertex/Workshop not yet built.

## 5d. Source control (2026-11-02)

The whole project folder is now a git repo (root `.gitignore` excludes `data/`, `.venv/`,
`node_modules/`, build outputs, checkpoints). The Foundry Code Workspace clone keeps its own git
metadata at `gnn_workspace_repo/.git_foundry` (renamed from `.git` so it nests as plain files);
to push code to the Foundry workspace repo use
`git --git-dir=gnn_workspace_repo/.git_foundry --work-tree=gnn_workspace_repo <cmd>`.

## 6. User-owned next phase (specs ready)

Ontology backing transforms exist (`build_ontology_backing.py`: accounts_summary with
24h volumes, alerts, transaction_risk_scores). Multi-model design: one scoring transform
per model, union keyed by `(transaction_id, model_version)`; Transaction→RiskScore is
one-to-many; one **champion** model drives Alerts, others are challengers (standard
model-risk-management framing for regulators).

## 7. Environment: history, the fix, and standing rules  ⚠️ READ BEFORE TOUCHING

The workspace conda channel's repodata produces **incoherent solves when packages
float** — this burned ~2 weeks (broken pyarrow↔azure ABI, wrong abseil, dropped
cudnn/libtorch, chimera torch builds). Resolution:

- **`meta.yaml` is exact-pinned** (do not unpin, do not add packages):
  `pytorch 2.3.1 cuda120_py312h26b3cf7_300`, `libtorch 2.3.1 cuda120_h2b0da52_300`,
  `pyg 2.6.1 py312_torch_2.3.0_cpu`, `pyg-lib 0.4.0 cuda120py312hc073071_1`
  (+ ipykernel, pip, foundry-transforms-lib-python, pandas, scikit-learn, palantir,
  palantir_models, containers-external-systems-python). This solve was verified clean:
  torch on T4, pyg_lib, pyarrow, foundry.transforms all import.
- **`.hooks/startup.sh` self-heals** on every session start: broken conda pyarrow →
  pip-wheel overwrite (`pip install --force-reinstall --no-deps pyarrow==17.0.0`);
  missing abseil-2407 → untar from dataset; missing `torch/version.py` → stub.
- Repair bundles live in the `gnn_training_code` dataset (see §3) if a rebuild ever
  goes wrong again; cuDNN/CUDA/MKL pieces are also obtainable via
  `python -m pip install --no-deps nvidia-*-cu12 ...` + copying libs into
  `~/envs/default/lib/`.
- **Rules:** changing `AML_*` settings never requires an env reset (they're just env
  vars). Interrupt-cell/kernel-restart are always safe. Env reset / workspace restart /
  profile change / package install each trigger a rebuild — safe now thanks to pins,
  but pointless churn; don't.

**Known runtime facts:**
- `/dev/shm` = 64MB → **DataLoader worker processes cannot work here, period.** Every
  torch tensor passed between processes goes through `shm_open()` = `/dev/shm`, for BOTH
  sharing strategies (`file_system` does NOT avoid it — earlier belief was wrong). The
  spawned worker receiving the pickled graph, or returning a batch, SIGBUS-dies/hangs.
  Resolved 2026-10-24: `training_core.ThreadedLoader` samples in a **thread pool**
  (pyg_lib ops release the GIL; zero shared memory). `AML_NUM_WORKERS` now means
  sampling *threads* (0 = serial, unset = auto 8 on GPU). Loader always has
  `num_workers=0` underneath.
- **The 2.2s/batch (16 min/epoch) seen at workers=0 is NOT a sampling-capacity
  problem**: locally the same graph samples at ~0.06s/batch @ 8192 (434 batches ≈
  0.5 min/epoch of sampling). Top suspect: OpenMP oversubscription (container reports
  host core count, cgroup grants fewer) — `training_core` now caps intra-op threads to
  `_usable_cpus()` (affinity ∩ cgroup quota). `diag_loader.py` (in repo + dataset)
  measures topology, sampling serial/threaded, and GPU step time separately. The pace
  check now prints `sampling Xs + gpu step Ys` so the bottleneck is visible.
- NaN divergence is fixed (BatchNorm + fp32 + grad clip + NaN-skip guard); AMP stays off.
- numpy floated to 2.5 in the pinned solve — watch for "compiled using NumPy 1.x"
  errors; fix would be pinning `numpy <2` in meta.yaml.

## 8. CLI / auth setup (new machine or expired token)

- Foundry CLI (`foundry`, v0.253+) at `~/.local/bin/foundry`; auth profile
  `saisplayground`. **Tokens expire (~2–4 weeks)** — the one from Sep 28 expired
  2026-10-06, so a fresh login is needed:
  user generates a token in Foundry → Account → Settings → Tokens, then:
  ```
  FOUNDRY_TOKEN='<token>' foundry login --foundry-url https://saisplayground.usw-17.palantirfoundry.com
  ```
- All API work runs through `foundry run-with-auth 'curl ... ${FOUNDRY_TOKEN} ... ${FOUNDRY_HOSTNAME} ...'`
  — requires a `foundry.yml` in cwd (one exists at repo root). **Gotcha:** it injects
  `FOUNDRY_HOSTNAME` *without* scheme — always write `https://${FOUNDRY_HOSTNAME}/...`.
- Verify access: `/multipass/api/me` (identity), `/api/v2/filesystem/spaces?preview=true`
  (platform API), `/stemma/git/<workspace rid>/info/refs?service=git-upload-pack` (git).
- Useful API endpoints proven to work: dataset create `POST /api/v2/datasets`;
  transactions `POST /api/v2/datasets/{rid}/transactions` (body
  `{"transactionType":"SNAPSHOT"|"UPDATE"}`) + file upload
  `POST .../files/{name}/upload?transactionRid=...` (use curl `-T` streaming, **≤~500MB
  per request** — gateway 500s above that) + `/commit`; schema
  `POST /foundry-metadata/api/schemas/datasets/{rid}/branches/master`; folder listing
  `GET /api/v2/filesystem/folders/{rid}/children?preview=true`; dangling-transaction
  cleanup via `GET /foundry-catalog/api/catalog/datasets/{rid}/reverse-transactions2/master`
  then `POST .../transactions/{txn}/abort`.
- Workspace git: clone/fetch/push with
  `git -c http.extraHeader="Authorization: Bearer ${FOUNDRY_TOKEN}" ...` inside
  `run-with-auth`. Workspace auto-commits strip notebook outputs — errors reach git only
  via `last_error.txt` (cell 5 writes it; user runs "commit local changes").

## 9. Current status & exact next steps

**Status (as of Oct 24):** pipeline fully built and verified; environment finally
stable and pinned; **the 15-epoch showcase training run has never completed — no model
published.** Everything downstream (scoring, ontology, Workshop) is blocked only on that.

1. Open the GNN workspace; cell 2 must show `cuda: True` + `sampling backend: pyg_lib`.
2. Diagnose the slow pace in a workspace **terminal** (~3-4 min; user tried the old
   process-worker ladder on Oct 24 and it failed at workers>0, as now expected):
   ```
   cd ~/repo && python diag_loader.py
   ```
   Read: topology (cpu_count vs affinity vs cgroup quota vs torch threads), sampling
   s/batch serial vs 4/8 threads, and the GPU step time. If serial sampling is >>0.1s
   and threads don't help, the box is CPU-starved/oversubscribed → the intra-op cap in
   training_core is the fix (verify by comparing the two sampling sections). Nothing
   here needs an env reset.
3. Real run in the notebook: cell 3 → cell 4 (`AML_EPOCHS="15"`, `AML_BATCH_SIZE="8192"`,
   `AML_FANOUT="15,10"`, leave `AML_NUM_WORKERS` unset for auto threads) → cell 5.
   The alias check runs first; if it fails, Models sidebar → import existing model
   (rid above) with alias `aml_gnn_hi_small`. GPU step is a fixed ~1s/step stall
   (down from 2.2s after pin_memory off + 4 intra-op threads); `gpu_diag.py` +
   an `AML_NUM_WORKERS=0` pace test are the pending diagnostics (§7). Prereq: Models panel has a model
   output with alias exactly `aml_gnn_hi_small`. Publish happens only at run end.
4. Cell 6 → Precision@100/500/1000/5000 + `scored_test_stream.parquet` (the handoff
   artifact for ontology ingestion).
5. Then: HI-Medium challenger (`AML_TIER="HI-Medium"`, alias `aml_gnn_hi_medium`,
   dataset alias `HI-Medium_Trans` needs panel-add or in-project copy — cross-project
   403 applies, see §3), the `score_large_tier` demo, and the user's ontology build.

**Expected metrics context:** at 0.1% positives, PR-AUC of 0.2–0.4 is strong; minority-F1
~0.3 = vanilla-GNN territory, 0.5–0.65 = paper territory; the demo-relevant number is
Precision@K on the test stream.

## 10. Debug loop that works

Error in the workspace → user commits (`last_error.txt` survives; notebook outputs
don't) → fetch workspace git and read it. Or user pastes the traceback — faster.
Silent kernel death → rerun the same thing in the workspace terminal to see the signal
(`Killed`=OOM, `Bus error`=shm, `Segmentation fault`=native). `groups: cannot find name
for group ID 110` in terminals is cosmetic noise.
