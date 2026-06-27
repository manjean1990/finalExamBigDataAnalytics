"""
spark_batch_processing.py
Part 2.1 - Batch Processing with Spark.

1. Clean/normalize raw JSON data (handle missing/null fields, standardize
   timestamp types, drop malformed records).
2. Compute "users who bought X also bought Y" product affinity indicators
   from transaction data (market-basket co-occurrence).

Run:
    spark-submit spark_batch_processing.py
or, for local testing:
    python spark_batch_processing.py
"""

import os
from pyspark.sql import SparkSession, functions as F
from pyspark.sql.types import (
    StructType, StructField, StringType, DoubleType, IntegerType, ArrayType, BooleanType
)

# Fix path for Windows compatibility
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")


def get_spark():
    return (
        SparkSession.builder.appName("EcommerceBatchProcessing")
        .master("local[*]")
        .config("spark.driver.host", "localhost")
        .getOrCreate()
    )


def clean_transactions(spark):
    """Load and clean transaction data."""
    df = spark.read.json(os.path.join(DATA_DIR, "transactions.json"))

    # Standardize: cast timestamp string to actual timestamp type,
    # drop rows with null/zero total (malformed), drop rows with no items.
    df_clean = (
        df.withColumn("event_ts", F.to_timestamp("timestamp"))
        .filter(F.col("total").isNotNull() & (F.col("total") >= 0))
        .filter(F.size("items") > 0)
        .withColumn("discount", F.coalesce(F.col("discount"), F.lit(0.0)))
        .withColumn("status", F.coalesce(F.col("status"), F.lit("unknown")))
    )

    n_raw, n_clean = df.count(), df_clean.count()
    print(f"Transactions: {n_raw} raw -> {n_clean} after cleaning ({n_raw - n_clean} dropped)")
    return df_clean


def clean_sessions(spark):
    """Load and clean session data."""
    df = spark.read.json(os.path.join(DATA_DIR, "sessions_0.json"))

    df_clean = (
        df.withColumn("start_ts", F.to_timestamp("start_time"))
        .withColumn("end_ts", F.to_timestamp("end_time"))
        .filter(F.col("duration_seconds") > 0)
        .withColumn(
            "conversion_status",
            F.coalesce(F.col("conversion_status"), F.lit("browsed")),
        )
    )
    n_raw, n_clean = df.count(), df_clean.count()
    print(f"Sessions: {n_raw} raw -> {n_clean} after cleaning ({n_raw - n_clean} dropped)")
    return df_clean


def product_affinity(spark, transactions_df):
    """
    'Users who bought X also bought Y' - market basket co-occurrence.
    Explode each transaction's items into product_id, self-join transactions
    on shared transaction_id to find pairs of products bought together,
    then count pair frequency.
    """
    items_df = transactions_df.select(
        "transaction_id", F.explode("items").alias("item")
    ).select("transaction_id", F.col("item.product_id").alias("product_id"))

    # Self-join on transaction_id to get co-purchased pairs (A != B)
    a = items_df.alias("a")
    b = items_df.alias("b")
    pairs = (
        a.join(b, on="transaction_id")
        .filter(F.col("a.product_id") < F.col("b.product_id"))  # avoid duplicates/self-pairs
        .groupBy(F.col("a.product_id").alias("product_a"), F.col("b.product_id").alias("product_b"))
        .agg(F.count("*").alias("co_purchase_count"))
        .orderBy(F.desc("co_purchase_count"))
    )

    print("\nTop product affinity pairs ('bought X also bought Y'):")
    pairs.show(15, truncate=False)
    return pairs


def cohort_analysis(spark, transactions_df):
    """
    Group users by registration month (cohort), analyze their spending
    in subsequent months.
    """
    users_df = spark.read.json(os.path.join(DATA_DIR, "users.json")).withColumn(
        "reg_month", F.date_format(F.to_timestamp("registration_date"), "yyyy-MM")
    )

    txn_with_month = transactions_df.withColumn(
        "txn_month", F.date_format("event_ts", "yyyy-MM")
    )

    joined = txn_with_month.join(
        users_df.select("user_id", "reg_month"), on="user_id", how="inner"
    )

    cohort = (
        joined.groupBy("reg_month", "txn_month")
        .agg(
            F.countDistinct("user_id").alias("active_users"),
            F.sum("total").alias("cohort_revenue"),
            F.round(F.avg("total"), 2).alias("avg_order_value"),
        )
        .orderBy("reg_month", "txn_month")
    )

    print("\nCohort analysis (registration month vs. transaction month):")
    cohort.show(20, truncate=False)
    return cohort


def main():
    spark = get_spark()
    spark.sparkContext.setLogLevel("WARN")

    transactions_df = clean_transactions(spark)
    sessions_df = clean_sessions(spark)

    transactions_df.cache()

    product_affinity(spark, transactions_df)
    cohort_analysis(spark, transactions_df)

    # Save cleaned data for downstream Spark SQL / integration steps
    transactions_df.write.mode("overwrite").parquet(os.path.join(DATA_DIR, "cleaned_transactions.parquet"))
    sessions_df.write.mode("overwrite").parquet(os.path.join(DATA_DIR, "cleaned_sessions.parquet"))
    print("\nCleaned data written to parquet for downstream use.")

    spark.stop()


if __name__ == "__main__":
    main()