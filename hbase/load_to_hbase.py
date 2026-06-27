"""
load_to_hbase.py
Loads session data into HBase using the row-key design described in
create_hbase_schema.sh.

Requires: pip install happybase --break-system-packages
(happybase talks to HBase's Thrift interface, exposed on port 9090 in
docker-compose.yml)

Run AFTER create_hbase_schema.sh has been executed in the HBase shell.

    python3 load_to_hbase.py
"""

import json
import glob
import datetime
import happybase

HBASE_HOST = "localhost"
HBASE_PORT = 9090

REVERSE_EPOCH_MAX = 9999999999999  # 13-digit ceiling for epoch millis


def to_epoch_millis(iso_str):
    dt = datetime.datetime.fromisoformat(iso_str)
    return int(dt.timestamp() * 1000)


def reverse_timestamp(iso_str):
    """Zero-padded reverse timestamp so recent sessions sort first."""
    millis = to_epoch_millis(iso_str)
    return f"{REVERSE_EPOCH_MAX - millis:013d}"


def load_json(path):
    with open(path) as f:
        return json.load(f)


def main():
    connection = happybase.Connection(HBASE_HOST, port=HBASE_PORT)
    sessions_table = connection.table("user_sessions")
    metrics_table = connection.table("product_daily_metrics")

    session_files = sorted(glob.glob("../data/sessions_*.json"))
    total_loaded = 0

    # In-memory aggregation for product_daily_metrics, built while we scan
    # sessions (views/cart_adds) -- purchases/revenue added from transactions below.
    daily_activity = {}  # (product_id, yyyymmdd) -> {"views": n, "cart_adds": n}

    for sf in session_files:
        sessions = load_json(sf)
        with sessions_table.batch(batch_size=500) as batch:
            for s in sessions:
                row_key = f"{s['user_id']}_{reverse_timestamp(s['start_time'])}"
                row_data = {
                    b"cf_meta:session_id": s["session_id"],
                    b"cf_meta:start_time": s["start_time"],
                    b"cf_meta:end_time": s["end_time"],
                    b"cf_meta:duration_seconds": str(s["duration_seconds"]),
                    b"cf_meta:device_type": s["device_profile"]["type"],
                    b"cf_meta:referrer": s["referrer"],
                    b"cf_geo:city": s["geo_data"]["city"],
                    b"cf_geo:state": s["geo_data"]["state"],
                    b"cf_geo:country": s["geo_data"]["country"],
                    b"cf_geo:ip_address": s["geo_data"]["ip_address"],
                    b"cf_conv:conversion_status": s["conversion_status"],
                    b"cf_conv:cart_item_count": str(len(s["cart_contents"])),
                }
                batch.put(row_key.encode(), {k: v.encode() for k, v in row_data.items()})

                # Tally views and cart adds for the product metrics table
                date_key = s["start_time"][:10].replace("-", "")
                for pid in s["viewed_products"]:
                    key = (pid, date_key)
                    daily_activity.setdefault(key, {"views": 0, "cart_adds": 0})
                    daily_activity[key]["views"] += 1
                for pid in s["cart_contents"]:
                    key = (pid, date_key)
                    daily_activity.setdefault(key, {"views": 0, "cart_adds": 0})
                    daily_activity[key]["cart_adds"] += 1

                total_loaded += 1
        print(f"  Loaded {len(sessions)} sessions from {sf}")

    print(f"Total sessions loaded into HBase: {total_loaded}")

    # Add purchase/revenue tallies from transactions
    transactions = load_json("../data/transactions.json")
    for t in transactions:
        date_key = t["timestamp"][:10].replace("-", "")
        for item in t["items"]:
            key = (item["product_id"], date_key)
            daily_activity.setdefault(key, {"views": 0, "cart_adds": 0})
            daily_activity[key]["purchases"] = daily_activity[key].get("purchases", 0) + item["quantity"]
            daily_activity[key]["revenue"] = daily_activity[key].get("revenue", 0.0) + item["subtotal"]

    with metrics_table.batch(batch_size=500) as batch:
        for (pid, date_key), metrics in daily_activity.items():
            row_key = f"{pid}_{date_key}"
            row_data = {
                b"cf_activity:views": str(metrics.get("views", 0)).encode(),
                b"cf_activity:cart_adds": str(metrics.get("cart_adds", 0)).encode(),
                b"cf_activity:purchases": str(metrics.get("purchases", 0)).encode(),
                b"cf_revenue:revenue": str(round(metrics.get("revenue", 0.0), 2)).encode(),
            }
            batch.put(row_key.encode(), row_data)

    print(f"Loaded {len(daily_activity)} product_daily_metrics rows into HBase")
    connection.close()


if __name__ == "__main__":
    main()
