"""Batch training transform: Multi-GNN on the HI-Medium tier.

The Medium tiers ship as one raw dataset, so the 70/10/20 temporal split
happens here on the driver before training; the newest 20% is never seen
by the model (reserved for the scoring/evaluation pipeline).
"""
import numpy as np
from transforms.api import Input, configure, transform
from palantir_models.transforms import ModelOutput

from aml_core.graph_builder import temporal_split
from aml_core.training_core import train_multignn

PROJECT = "/AML_Compliance_Platform"

RAW_COLS = [
    "timestamp", "from_bank", "from_account", "to_bank", "to_account",
    "amount_received", "receiving_currency", "amount_paid",
    "payment_currency", "payment_format", "is_laundering",
]


@configure(profile=["DRIVER_GPU_ENABLED", "DRIVER_MEMORY_EXTRA_LARGE"])
@transform(
    model_output=ModelOutput(f"{PROJECT}/02_Models/aml_gnn_hi_medium"),
    raw_input=Input(f"{PROJECT}/01_Raw_Data/kaggle_full/HI-Medium_Trans"),
)
def compute(model_output, raw_input):
    full = raw_input.dataframe().toPandas()
    full.columns = RAW_COLS[: len(full.columns)]
    full["transaction_id"] = np.arange(len(full), dtype=np.int64)
    train_df, val_df, _test_df = temporal_split(full)
    train_df, val_df = train_df.copy(), val_df.copy()
    del full, _test_df

    adapter, metrics = train_multignn(train_df, val_df, tier="HI-Medium")
    model_output.publish(model_adapter=adapter)
