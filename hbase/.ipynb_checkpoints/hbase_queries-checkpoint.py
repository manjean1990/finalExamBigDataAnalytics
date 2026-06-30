"""
hbase_queries.py
Example queries demonstrating HBase's strength: fast retrieval of a single
user's session activity stream, and time-range scans on product metrics.

Run AFTER load_to_hbase.py.
    python hbase_queries.py <user_id>
Example:
    python3 hbase_queries.py user_000042
"""

import sys
import happybase

HBASE_HOST = "localhost"
HBASE_PORT = 9090


def get_user_sessions(table, user_id, limit=10):
    """
    Scan starting at the row-key prefix '<user_id>_' to retrieve that
    user's sessions, most-recent-first, without scanning the whole table.
    This is the payoff of the reverse-timestamp row key design.
    """
    row_prefix = f"{user_id}_".encode()
    rows = table.scan(row_prefix=row_prefix, limit=limit)
    results = []
    for key, data in rows:
        results.append(
            {
                "row_key": key.decode(),
                "session_id": data.get(b"cf_meta:session_id", b"").decode(),
                "start_time": data.get(b"cf_meta:start_time", b"").decode(),
                "device_type": data.get(b"cf_meta:device_type", b"").decode(),
                "conversion_status": data.get(b"cf_conv:conversion_status", b"").decode(),
            }
        )
    return results


def get_product_metrics_range(table, product_id, start_date, end_date):
    """
    Range scan on product_daily_metrics between two YYYYMMDD-suffixed
    row keys for a given product -- demonstrates HBase's efficient
    time-range scan on a sorted row key.
    """
    start_key = f"{product_id}_{start_date}".encode()
    stop_key = f"{product_id}_{end_date}".encode()
    rows = table.scan(row_start=start_key, row_stop=stop_key)
    results = []
    for key, data in rows:
        results.append(
            {
                "row_key": key.decode(),
                "views": int(data.get(b"cf_activity:views", b"0")),
                "cart_adds": int(data.get(b"cf_activity:cart_adds", b"0")),
                "purchases": int(data.get(b"cf_activity:purchases", b"0")),
                "revenue": float(data.get(b"cf_revenue:revenue", b"0")),
            }
        )
    return results


if __name__ == "__main__":
    user_id = sys.argv[1] if len(sys.argv) > 1 else "user_000001"

    connection = happybase.Connection(HBASE_HOST, port=HBASE_PORT)
    sessions_table = connection.table("user_sessions")
    metrics_table = connection.table("product_daily_metrics")

    print(f"=== Recent sessions for {user_id} (most recent first) ===")
    for row in get_user_sessions(sessions_table, user_id, limit=10):
        print(row)

    print("\n=== Product metrics range scan example (prod_00000, March 2026) ===")
    for row in get_product_metrics_range(metrics_table, "prod_00000", "20260301", "20260331"):
        print(row)

    connection.close()
