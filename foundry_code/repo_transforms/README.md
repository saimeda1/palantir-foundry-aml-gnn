# AML Model Training — Code Repository package

Production training pipeline: batch transforms that train the Multi-GNN on
GPU compute profiles, publish Foundry models, and score the test stream.
Designed for a **Code Repositories → Model Training (Python transforms)**
template repo.

## One-time setup (UI)

1. In the `AML_Compliance_Platform` project: **+ New → Code repository →
   Model training** (Python transforms language). Name it e.g.
   `aml-gnn-training`.
2. Tell Claude the repo name — the code gets pushed into it via git, merged
   over the template scaffolding.

## Repo layout after the push

```
transforms-python/src/<template package>/
  aml_core/            # shared: graph_builder, model, model_adapter,
                       #         training_core (synced from workspace code)
  aml_training/
    train_hi_small.py  # GPU training transform -> 02_Models/aml_gnn_hi_small
    train_hi_medium.py # GPU training transform -> 02_Models/aml_gnn_hi_medium
    score_test_stream.py  # ModelInput batch scoring -> 03_Scored_Data
```

## Repo settings required before the first build

- **Spark profiles** (Settings → Spark → import profiles):
  `DRIVER_GPU_ENABLED`, `DRIVER_MEMORY_LARGE`,
  `DRIVER_MEMORY_EXTRA_LARGE` (Medium tier). Profile availability is
  enrollment-controlled; if GPU profiles are not importable yet, the
  transforms still build and train on CPU — remove/swap the
  `DRIVER_GPU_ENABLED` entry until GPU is granted.
- **Libraries** (conda meta.yaml run requirements): `pytorch`, `pyg`,
  `scikit-learn`, `pandas`, `numpy`, `palantir_models`,
  `palantir_models_serializers`.

## Operating model

- Commit → CI checks → build the training transform → model version
  published to `02_Models/`. Schedule the training transform for periodic
  retraining; schedule `score_test_stream` downstream of it.
- The Code Workspace notebook trains through the identical
  `training_core.train_multignn`, so interactive experiments and production
  builds cannot drift.
