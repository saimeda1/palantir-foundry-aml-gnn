# AML detection on Palantir Foundry with a graph neural network

End-to-end proof of concept: a Multi-GNN anti-money-laundering model trained on the IBM AML
HI-Small dataset inside Palantir Foundry, published as a Foundry model, used to score a held-out
transaction stream, and surfaced to investigators through a Foundry Ontology with an alert
network visualization.

`HANDOFF.md` is the authoritative, detailed project log (architecture, every blocker hit and how
it was resolved, RIDs, run configs). This README is the short version.

## Results

Champion model `aml_gnn_hi_small` v1 (GINE backbone, reverse message passing, ego IDs, port
numbering; 2 layers × 96 hidden, fanout 50/30, best of 39 epochs on a single T4).

| Split | PR-AUC | ROC-AUC | Notes |
|---|---|---|---|
| Validation | 0.564 | 0.987 | best-F1 0.584, thresholds High ≥ 0.623 / Medium ≥ 0.351 |
| Test stream (1,015,670 txns, 1,797 laundering) | 0.191 | 0.949 | precision@100 = 0.91, High band 181 / 269 = 0.67 |

## What is in here

| Path | What |
|---|---|
| `foundry_code/model_training/` | Training code that runs in a Foundry Code Workspace: `graph_builder.py` (features, ports, ego IDs), `model.py` (Multi-GNN), `training_core.py` (threaded neighbour sampler, training loop, calibration), `train_gnn_foundry.py` (entry point, env knobs), `model_adapter.py` + generated `aml_gnn_adapter.py` (Foundry model adapter), publish scripts |
| `foundry_code/transforms/` | Scoring and ontology-backing dataset builders (Foundry transforms and a local pandas version) |
| `foundry_code/repo_transforms/` | Same pipeline packaged for a Foundry Code Repository |
| `foundry_code/workshop_aip/` | Ontology build guide, AIP Assist prompt, Workshop layout, SAR prompt, and the standalone investigator-console prototype (`prototype/`) |
| `ontology/` | Ontology-as-code (`@osdk/maker`): 7 object types, 8 links, 5 actions; `aml_ontology.yml` is the human-readable spec |
| `foundry.yml`, `env.yml`, `package.json` | Foundry CLI SuperRepo config and input mappings for the Marketplace bundle |
| `gnn_workspace_repo/` | Snapshot of the Foundry Code Workspace repository (training notebook, publish transform spec, adapter bundle) |
| `scripts/` | Dataset upload, temporal split, Kaggle download helpers |

## Pipeline

1. **Data.** IBM AML HI-Small (Kaggle) → temporal split into train / validation / test stream →
   Foundry datasets.
2. **Training.** Code Workspace with a T4. `/dev/shm` is 64 MB there, so PyG DataLoader workers
   cannot be used; `ThreadedLoader` in `training_core.py` samples neighbourhoods on a thread pool.
3. **Publishing.** Interactive publishing from the workspace is denied by the sidecar token; the
   working route is **Publish as transform output** (`publish_model.ipynb`, spec in
   `gnn_workspace_repo/.transforms/`).
4. **Scoring.** The published adapter replays the training protocol (sampled fanout, per-batch ego
   IDs) over the test stream and emits probability + risk band.
5. **Ontology.** Seven backing tables (transactions, risk scores, account summaries, alerts with a
   graph-heuristic typology, cases, ground-truth patterns, evaluation) → object types and links in
   Ontology Manager (built by hand; the code version is blocked on an enrollment-level Marketplace
   signing setting, see HANDOFF §5b).
6. **Investigator surface.** Alert inbox → network graph → evidence → actions. A standalone D3
   prototype of this console lives in `foundry_code/workshop_aip/prototype/`; the Foundry build
   (Vertex, Workshop, AIP Logic) follows `ontology_build_guide.md`.

## Stack

Palantir Foundry (Code Workspaces, Datasets, Models, Ontology, Marketplace, Foundry CLI) ·
PyTorch 2.3 · PyTorch Geometric 2.6 · CUDA · pandas · PyArrow · scikit-learn · D3.js ·
TypeScript (`@osdk/maker`) · Python 3.12

## Reproducing locally

```bash
uv venv && uv pip install --python .venv/bin/python pandas pyarrow scikit-learn torch torch_geometric
bash scripts/kaggle_to_foundry.sh            # fetch HI-Small into data/raw (Kaggle credentials needed)
.venv/bin/python scripts/temporal_split.py   # data/processed
.venv/bin/python foundry_code/transforms/build_backing_datasets_local.py   # data/scored tables
```

The `data/` folder is not committed (about 1 GB).

## Reference

Egressy et al., *Provably Powerful Graph Neural Networks for Directed Multigraphs*, AAAI 2024
(the Multi-GNN paper this implementation follows; differences are documented in HANDOFF §7).
