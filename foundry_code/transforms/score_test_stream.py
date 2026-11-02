"""PySpark transform: batch-score the held-out test stream with the
published AML GNN model.

Inputs : /AML_Compliance_Platform/01_Raw_Data/raw_transactions_test_stream
         ModelInput(/AML_Compliance_Platform/02_Models/aml_gnn_model)
Output : /AML_Compliance_Platform/03_Scored_Data/scored_transactions_stream

The model adapter scores whole transaction windows (it rebuilds the local
graph per batch), so scoring runs on the driver in chronological chunks —
appropriate for the 1.0M-row test slice. For larger streams switch the
chunking to Spark applyInPandas over time buckets.
"""
import pandas as pd
from pyspark.sql import functions as F
from transforms.api import Input, Output, transform
from palantir_models.transforms import ModelInput

PROJECT = "/AML_Compliance_Platform"
CHUNK_ROWS = 250_000


@transform(
    out=Output(f"{PROJECT}/03_Scored_Data/scored_transactions_stream"),
    raw=Input(f"{PROJECT}/01_Raw_Data/raw_transactions_test_stream"),
    model=ModelInput(f"{PROJECT}/02_Models/aml_gnn_model"),
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
