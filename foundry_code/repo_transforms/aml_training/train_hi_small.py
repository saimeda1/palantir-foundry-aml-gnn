"""Batch training transform: Multi-GNN on the HI-Small tier (pre-split
datasets). Runs on the driver with a GPU compute profile; publishes the
trained adapter as a Foundry model for the scoring pipeline.

Repo settings prerequisites:
  - Spark profiles imported & enabled: DRIVER_GPU_ENABLED,
    DRIVER_MEMORY_LARGE (training happens on the driver).
  - Library deps in conda meta.yaml: pytorch (CUDA build), pyg,
    scikit-learn, pandas, palantir_models.
"""
from transforms.api import Input, configure, transform
from palantir_models.transforms import ModelOutput

from aml_core.training_core import train_multignn

PROJECT = "/AML_Compliance_Platform"


@configure(profile=["DRIVER_GPU_ENABLED", "DRIVER_MEMORY_LARGE"])
@transform(
    model_output=ModelOutput(f"{PROJECT}/02_Models/aml_gnn_hi_small"),
    train_input=Input(f"{PROJECT}/01_Raw_Data/raw_transactions_train"),
    val_input=Input(f"{PROJECT}/01_Raw_Data/raw_transactions_val"),
)
def compute(model_output, train_input, val_input):
    train_df = train_input.dataframe().toPandas()
    val_df = val_input.dataframe().toPandas()
    adapter, metrics = train_multignn(train_df, val_df, tier="HI-Small")
    model_output.publish(model_adapter=adapter)
