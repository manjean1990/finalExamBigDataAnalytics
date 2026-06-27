# create_hbase_schema.sh
# Run inside the HBase shell:
#   docker exec -it ecommerce-hbase hbase shell
# then paste these commands (or run: hbase shell create_hbase_schema.sh)
#
# ---------------------------------------------------------------------------
# DESIGN RATIONALE (see report for full discussion)
#
# Table: user_sessions
#   Row key:      <user_id>_<reverse_timestamp>
#     - reverse_timestamp = (9999999999999 - epoch_millis), zero-padded.
#     - This makes HBase's natural lexicographic row-key sort put a user's
#       MOST RECENT sessions first, so "get last N sessions for user X" is
#       a single short scan starting at the row prefix <user_id>_ instead
#       of a full table scan + sort.
#   Column families:
#     cf_meta  -> session_id, start_time, end_time, duration, device, referrer
#     cf_geo   -> city, state, country, ip_address
#     cf_conv  -> conversion_status, cart_item_count, cart_value
#   Why HBase here: sessions are high-volume, append-mostly, and queried by
#   "give me this user's recent activity stream" -> exactly HBase's sweet
#   spot for time-series/sparse row access, vs. MongoDB which is better for
#   reading one ENTIRE rich session document (with full page_views array).
#
# Table: product_daily_metrics
#   Row key: <product_id>_<date YYYYMMDD>
#   Column families:
#     cf_activity -> views, cart_adds, purchases (counters, incremented per event)
#     cf_revenue  -> revenue, units_sold
#   Why HBase here: this is a classic wide, sparse, time-bucketed metric
#   table -- most cells are zero/absent on most days for most products,
#   and the access pattern is always "scan product X across a date range",
#   which is a fast range scan on a row-key prefix in HBase.
# ---------------------------------------------------------------------------

create 'user_sessions', 'cf_meta', 'cf_geo', 'cf_conv'
create 'product_daily_metrics', 'cf_activity', 'cf_revenue'

list
describe 'user_sessions'
describe 'product_daily_metrics'
