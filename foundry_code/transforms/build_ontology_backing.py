"""PySpark transforms building the Ontology backing datasets from the
scored stream: account summaries (24h rolling volumes, max risk) and
alerts for High/Medium-band transactions.

Outputs land in /AML_Compliance_Platform/03_Scored_Data/ and back the
Account, TransactionRiskScore, and Alert object types.
"""
from pyspark.sql import Window
from pyspark.sql import functions as F
from transforms.api import Input, Output, transform_df

PROJECT = "/AML_Compliance_Platform"
SCORED = f"{PROJECT}/03_Scored_Data/scored_transactions_stream"


@transform_df(
    Output(f"{PROJECT}/03_Scored_Data/accounts_summary"),
    scored=Input(SCORED),
)
def accounts_summary(scored):
    """One row per account with 24h-window aggregates as of the account's
    latest activity, plus the max model risk score touching the account."""
    out_edges = scored.select(
        F.col("from_account").alias("account_id"),
        "timestamp",
        F.col("amount").alias("out_amount"),
        F.lit(0.0).alias("in_amount"),
        "laundering_probability",
    )
    in_edges = scored.select(
        F.col("to_account").alias("account_id"),
        "timestamp",
        F.lit(0.0).alias("out_amount"),
        F.col("amount").alias("in_amount"),
        "laundering_probability",
    )
    edges = out_edges.unionByName(in_edges)

    w24 = (
        Window.partitionBy("account_id")
        .orderBy(F.col("timestamp").cast("long"))
        .rangeBetween(-24 * 3600, 0)
    )
    enriched = (
        edges
        .withColumn("inbound_24h", F.sum("in_amount").over(w24))
        .withColumn("outbound_24h", F.sum("out_amount").over(w24))
    )
    latest = Window.partitionBy("account_id").orderBy(F.col("timestamp").desc())
    return (
        enriched
        .withColumn("rn", F.row_number().over(latest))
        .withColumn(
            "max_risk_score",
            F.max("laundering_probability").over(Window.partitionBy("account_id")),
        )
        .filter(F.col("rn") == 1)
        .select(
            "account_id",
            F.split("account_id", r"\|").getItem(0).alias("bank_id"),
            F.col("inbound_24h").alias("volume_24h_inbound"),
            F.col("outbound_24h").alias("volume_24h_outbound"),
            "max_risk_score",
            F.col("timestamp").alias("last_active_ts"),
        )
    )


@transform_df(
    Output(f"{PROJECT}/03_Scored_Data/alerts"),
    scored=Input(SCORED),
)
def alerts(scored):
    """Open one alert per High/Medium risk-band transaction."""
    flagged = scored.filter(F.col("risk_band").isin("High", "Medium"))
    return flagged.select(
        F.concat(F.lit("ALERT-"), F.col("transaction_id")).alias("alert_id"),
        "transaction_id",
        F.col("from_account").alias("subject_account_id"),
        F.lit("Open").alias("status"),
        F.when(F.col("risk_band") == "High", "P1").otherwise("P2").alias("priority"),
        F.when(F.col("laundering_probability") >= 0.97, "Structuring / layering")
         .otherwise("Anomalous counterparty flow").alias("primary_typology"),
        "laundering_probability",
        "risk_band",
        F.col("timestamp").alias("alerted_ts"),
    )


@transform_df(
    Output(f"{PROJECT}/03_Scored_Data/transaction_risk_scores"),
    scored=Input(SCORED),
)
def transaction_risk_scores(scored):
    return scored.select(
        F.concat(F.lit("SCORE-"), F.col("transaction_id")).alias("score_id"),
        "transaction_id",
        "laundering_probability",
        "risk_band",
        F.lit("aml_gnn_model@v1").alias("model_version"),
        F.col("timestamp").alias("scored_ts"),
    )
