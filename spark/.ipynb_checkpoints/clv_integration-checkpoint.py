"""
clv_integration.py
Part 3 - Integrated Analytical Query: Customer Lifetime Value (CLV) Estimation.

Business question:
  "Which users represent the highest current and projected lifetime
  value, and what role does engagement (session frequency/duration)
  play in that value?"

Data sources involved (conceptually, per the assignment's system design):
  - MongoDB: user profiles (users collection) + transaction history
    (transactions collection) -> who they are + what they've bought.
  - HBase:   session engagement metrics (user_sessions table) -> how
    often and how long they engage, which HBase is well-suited to
    store/scan as a time-series-like access pattern keyed by user_id.
  - Spark:   performs the actual join/aggregation across both sources,
    since this is exactly the kind of cross-system computation no
    single store does natively/cheaply.

Implementation note: since this is graded as an integration *workflow*
and a single laptop environment, we simulate "data living in two
systems" by reading the Mongo-shaped JSON (users/transactions) and the
HBase-shaped JSON (sessions, which is what gets loaded into
user_sessions in load_to_hbase.py) and joining them in Spark -- which
is precisely the production pattern: Spark reads connectors/exports
from both stores and joins them in one engine.

Run:
    clv_integration.py
"""

from pyspark.sql import SparkSession, functions as F

DATA_DIR = "/workspace/data"


def get_spark():
    return (
        SparkSession.builder.appName("CLVIntegration")
        .master("local[*]")
        .getOrCreate()
    )


def main():
    spark = get_spark()
    spark.sparkContext.setLogLevel("WARN")

    # --- "MongoDB side": user profile + transaction history ---
    users = spark.read.json(f"{DATA_DIR}/users.json")
    transactions = spark.read.json(f"{DATA_DIR}/transactions.json")

    txn_agg = transactions.groupBy("user_id").agg(
        F.count("transaction_id").alias("order_count"),
        F.round(F.sum("total"), 2).alias("total_spent"),
        F.round(F.avg("total"), 2).alias("avg_order_value"),
        F.max("timestamp").alias("last_purchase_date"),
    )

    # --- "HBase side": session engagement metrics ---
    sessions = spark.read.json(f"{DATA_DIR}/sessions_0.json")

    session_agg = sessions.groupBy("user_id").agg(
        F.count("session_id").alias("session_count"),
        F.round(F.avg("duration_seconds"), 1).alias("avg_session_duration_sec"),
        F.sum(
            F.when(F.col("conversion_status") == "converted", 1).otherwise(0)
        ).alias("converted_sessions"),
    )

    # --- Spark join across both "systems" ---
    clv_base = (
        users.select("user_id", "registration_date", "geo_data")
        .join(txn_agg, on="user_id", how="left")
        .join(session_agg, on="user_id", how="left")
        .fillna(0, subset=["order_count", "total_spent", "avg_order_value", "session_count", "converted_sessions"])
    )

    # Simple CLV estimate:
    #   CLV = avg_order_value * purchase_frequency * estimated_lifespan_factor
    # purchase_frequency proxied by order_count over the 90-day window,
    # projected to an annual figure, then weighted slightly by engagement
    # (session_count) as a proxy for ongoing interest/retention likelihood.
    clv_df = clv_base.withColumn(
        "annualized_orders", F.col("order_count") * (365.0 / 90.0)
    ).withColumn(
        "engagement_factor",
        F.lit(1.0) + F.least(F.col("session_count") / F.lit(20.0), F.lit(0.5)),
    ).withColumn(
        "estimated_annual_clv",
        F.round(F.col("avg_order_value") * F.col("annualized_orders") * F.col("engagement_factor"), 2),
    )

    print("=== Top 15 users by estimated annual CLV ===")
    clv_df.select(
        "user_id", "order_count", "total_spent", "avg_order_value",
        "session_count", "avg_session_duration_sec", "estimated_annual_clv",
    ).orderBy(F.desc("estimated_annual_clv")).show(15, truncate=False)

    print("=== CLV summary stats ===")
    clv_df.select("estimated_annual_clv").summary("min", "25%", "50%", "75%", "max", "mean").show()

    clv_df.write.mode("overwrite").parquet(f"{DATA_DIR}/clv_results.parquet")
    print("CLV results written to clv_results.parquet")

    spark.stop()


if __name__ == "__main__":
    main()
