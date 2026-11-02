# AML Compliance Platform — Foundry Code

Enrollment: `https://saisplayground.usw-17.palantirfoundry.com`
Project: `/Sai's Playground-509041/AML_Compliance_Platform`
(rid `ri.compass.main.folder.2c7fe3fd-cdc3-4040-b4a1-f3e6a755c93a`)

## Staged datasets (uploaded, schema applied, verified readable)

| Dataset | Rows | Time span | RID |
|---|---|---|---|
| `01_Raw_Data/raw_transactions_train` | 3,554,841 | 2022-09-01 → 09-07 | `ri.foundry.main.dataset.f659e2b2-41cc-4aad-9111-e31a0edb1e6a` |
| `01_Raw_Data/raw_transactions_val` | 507,834 | 09-07 → 09-08 | `ri.foundry.main.dataset.4a742420-545e-4995-b354-658b3c968c1e` |
| `01_Raw_Data/raw_transactions_test_stream` | 1,015,670 | 09-08 → 09-18 | `ri.foundry.main.dataset.b479a5c3-59cc-4075-8da0-52b8d9f4d24d` |

Strict chronological 70/10/20 split — no future edges leak into training.
Positive rates: 0.080% / 0.103% / 0.177%.

## Layout

- `model_training/` — run inside a **Jupyter Code Workspace with a GPU
  compute profile** attached to the three raw datasets:
  - `graph_builder.py` — shared featurization (accounts→nodes, txns→edges)
  - `model.py` — GINEConv edge classifier + focal loss
  - `train_gnn_foundry.py` — LinkNeighborLoader training, val ROC/PR-AUC,
    risk-band threshold calibration, publishes via `ModelOutput` to
    `02_Models/aml_gnn_model`
  - `model_adapter.py` — `palantir_models.ModelAdapter` (save/load/api/
    predict → `laundering_probability`, `risk_band`)
- `transforms/` — Python transforms repository code:
  - `preprocess_graph.py` — typed/cleaned training table
  - `score_test_stream.py` — batch scoring with `ModelInput` →
    `03_Scored_Data/scored_transactions_stream`
  - `build_ontology_backing.py` — `accounts_summary` (24h in/out volume,
    max risk), `alerts`, `transaction_risk_scores`
- `../ontology/aml_ontology.yml` — object/link/action type spec
- `workshop_aip/` — Workshop layout plan + AIP SAR-draft prompt

## Deployment order

1. Code Workspace (GPU profile, e.g. `GPU_NVIDIA_T4` or larger): import
   `model_training/`, env with `torch` (CUDA), `torch-geometric`,
   `palantir-models`; run `train_gnn_foundry.py` (5 epochs default,
   `AML_EPOCHS`/`AML_BATCH_SIZE` env overrides).
2. Code Repository (transforms-python): add `transforms/`, build
   `preprocess_graph`, then `score_test_stream` (needs the published model),
   then `build_ontology_backing`.
3. Ontology Manager: apply `aml_ontology.yml` object/link/action types over
   the `03_Scored_Data` backing datasets.
4. Workshop + AIP Logic per `workshop_aip/`.
