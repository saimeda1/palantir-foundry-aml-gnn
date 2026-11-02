"""PySpark transform: clean the raw training stream into typed, USD-normalized
transactions with graph-ready ids, feeding the GNN training workspace.

Input : /AML_Compliance_Platform/01_Raw_Data/raw_transactions_train
Output: /AML_Compliance_Platform/01_Raw_Data/prepared_transactions_train
"""
from pyspark.sql import functions as F
from transforms.api import Input, Output, transform_df

PROJECT = "/AML_Compliance_Platform"


@transform_df(
    Output(f"{PROJECT}/01_Raw_Data/prepared_transactions_train"),
    raw=Input(f"{PROJECT}/01_Raw_Data/raw_transactions_train"),
)
def prepare_transactions(raw):
    df = (
        raw
        .withColumn("event_ts", F.to_timestamp("timestamp", "yyyy/MM/dd HH:mm"))
        .withColumn("from_account_id", F.concat_ws("|", "from_bank", "from_account"))
        .withColumn("to_account_id", F.concat_ws("|", "to_bank", "to_account"))
        .withColumn("amount_usd", F.col("amount_paid").cast("double"))
        .withColumn("is_laundering", F.col("is_laundering").cast("int"))
    )
    return df.select(
        "transaction_id", "event_ts", "from_account_id", "to_account_id",
        "amount_usd", "amount_received", "receiving_currency",
        "payment_currency", "payment_format", "is_laundering",
    ).orderBy("event_ts")
