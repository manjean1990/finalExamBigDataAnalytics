"""
spark_sql_analytics.py
Part 2.2 - Spark SQL Analytics.

Demonstrates complex SQL queries over DataFrames built from the JSON
files, simulating querying data that would notionally live in
MongoDB/HBase (we load equivalent samples into Spark DataFrames and
register them as SQL temp views).

Run:
    spark-submit spark_sql_analytics.py
"""

from pyspark.sql import SparkSession, functions as F

DATA_DIR = "/workspace/data"


def get_spark():
    return (
        SparkSession.builder.appName("EcommerceSparkSQL")
        .master("local[*]")
        .getOrCreate()
    )


def main():
    spark = get_spark()
    spark.sparkContext.setLogLevel("WARN")

    users = spark.read.json(f"{DATA_DIR}/users.json")
    products = spark.read.json(f"{DATA_DIR}/products.json")
    categories = spark.read.json(f"{DATA_DIR}/categories.json")
    transactions = spark.read.json(f"{DATA_DIR}/transactions.json")
    sessions = spark.read.json(f"{DATA_DIR}/sessions_0.json")

    users.createOrReplaceTempView("users")
    products.createOrReplaceTempView("products")
    categories.createOrReplaceTempView("categories")
    transactions.createOrReplaceTempView("transactions")
    sessions.createOrReplaceTempView("sessions")

    # Flatten transaction line items into their own view for easy SQL joins
    spark.sql(
        """
        SELECT transaction_id, user_id, timestamp, total,
               explode(items) as item
        FROM transactions
        """
    ).createOrReplaceTempView("transaction_items")

    print("=== Query 1: Revenue by category (joins transaction_items -> products -> categories) ===")
    spark.sql(
        """
        SELECT c.name AS category_name,
               ROUND(SUM(ti.item.subtotal), 2) AS total_revenue,
               SUM(ti.item.quantity) AS units_sold
        FROM transaction_items ti
        JOIN products p ON ti.item.product_id = p.product_id
        JOIN categories c ON p.category_id = c.category_id
        GROUP BY c.name
        ORDER BY total_revenue DESC
        """
    ).show(10, truncate=False)

    print("=== Query 2: Top spenders with their geo data (users join transactions) ===")
    spark.sql(
        """
        SELECT u.user_id, u.geo_data.city, u.geo_data.state,
               COUNT(t.transaction_id) AS order_count,
               ROUND(SUM(t.total), 2) AS total_spent
        FROM users u
        JOIN transactions t ON u.user_id = t.user_id
        GROUP BY u.user_id, u.geo_data.city, u.geo_data.state
        ORDER BY total_spent DESC
        LIMIT 10
        """
    ).show(truncate=False)

    print("=== Query 3: Session-to-purchase conversion rate by device type ===")
    spark.sql(
        """
        SELECT device_profile.type AS device_type,
               COUNT(*) AS total_sessions,
               SUM(CASE WHEN conversion_status = 'converted' THEN 1 ELSE 0 END) AS converted_sessions,
               ROUND(
                 100.0 * SUM(CASE WHEN conversion_status = 'converted' THEN 1 ELSE 0 END) / COUNT(*),
                 2
               ) AS conversion_rate_pct
        FROM sessions
        GROUP BY device_profile.type
        ORDER BY conversion_rate_pct DESC
        """
    ).show(truncate=False)

    print("=== Query 4: Average order value by payment method, by month ===")
    spark.sql(
        """
        SELECT date_format(to_timestamp(timestamp), 'yyyy-MM') AS month,
               payment_method,
               ROUND(AVG(total), 2) AS avg_order_value,
               COUNT(*) AS num_orders
        FROM transactions
        GROUP BY month, payment_method
        ORDER BY month, avg_order_value DESC
        """
    ).show(20, truncate=False)

    spark.stop()


if __name__ == "__main__":
    main()
