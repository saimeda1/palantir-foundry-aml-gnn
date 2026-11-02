"""Batch scoring transform: score the held-out HI-Small test stream with the
model trained by train_hi_small.py. Downstream of this dataset sit the
ontology backing transforms (risk scores, accounts, alerts).

To add challenger models, copy this transform with a different ModelInput
and output path; the union into transaction_risk_scores keys rows by
(transaction_id, model_version).
"""
import pandas as pd
from pyspark.sql import functions as F
from transforms.api import Input, Output, configure, transform
from palantir_models.transforms import ModelInput

PROJECT = "/AML_Compliance_Platform"
CHUNK_ROWS = 250_000


@configure(profile=["DRIVER_MEMORY_LARGE"])
@transform(
    out=Output(f"{PROJECT}/03_Scored_Data/scored_transactions_stream"),
    raw=Input(f"{PROJECT}/01_Raw_Data/raw_transactions_test_stream"),
    model=ModelInput(f"{PROJECT}/02_Models/aml_gnn_hi_small"),
)
def score_stream(out, raw, model, ctx):
    pdf = (
        raw.dataframe()
        .orderBy("timestamp", "transaction_id")
        .toPandas()
    )

    scored_chunks = []
    for start in range(0, len(pdf), CHUNK_ROWS):
        chunk = pdf.iloc[start:start + CHUNK_ROWS]
        scored_chunks.append(
            model.transform(df_in=chunk.drop(columns=["is_laundering"])).df_out
        )
    scored = pd.concat(scored_chunks, ignore_index=True)
    scored["is_laundering_ground_truth"] = pdf["is_laundering"].to_numpy()

    result = (
        ctx.spark_session.createDataFrame(scored)
        .withColumn("timestamp", F.to_timestamp("timestamp", "yyyy/MM/dd HH:mm"))
        .select(
            "transaction_id",
            "timestamp",
            F.concat_ws("|", "from_bank", "from_account").alias("from_account"),
            F.concat_ws("|", "to_bank", "to_account").alias("to_account"),
            F.col("amount_paid").cast("double").alias("amount"),
            "laundering_probability",
            "risk_band",
            F.col("is_laundering_ground_truth").cast("int"),
        )
    )
    out.write_dataframe(result)
