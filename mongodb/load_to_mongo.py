"""
load_to_mongo.py
Loads categories, products, users, transactions, and sessions into MongoDB.

Schema design notes (see report for full justification):
- categories: embed subcategories directly (small, always read together)
- products: embed price_history (small array, read with the product)
- users: embed a small purchase_summary computed at load time
  (total_spent, order_count, last_purchase_date) so user-level analytics
  don't need a join/lookup at query time
- transactions: embed line items (always read/written together, never
  queried independently of their parent transaction)
- sessions: embedded as-is (page_views + cart_contents are natural nested
  documents representing one user journey)

Run:
    pip install pymongo --break-system-packages
    python3 load_to_mongo.py
"""

import json
import glob
from collections import defaultdict
from pymongo import MongoClient, ASCENDING

MONGO_URI = "mongodb://localhost:27017"
DB_NAME = "ecommerce"

client = MongoClient(MONGO_URI)
db = client[DB_NAME]


def load_json(path):
    with open(path) as f:
        return json.load(f)


def main():
    # ---- Categories ----
    categories = load_json("../data/categories.json")
    db.categories.drop()
    db.categories.insert_many(categories)
    print(f"Loaded {len(categories)} categories")

    # ---- Products ----
    products = load_json("../data/products.json")
    db.products.drop()
    db.products.insert_many(products)
    print(f"Loaded {len(products)} products")

    # ---- Transactions ----
    transactions = load_json("../data/transactions.json")
    db.transactions.drop()
    if transactions:
        db.transactions.insert_many(transactions)
    print(f"Loaded {len(transactions)} transactions")

    # ---- Users (with embedded purchase_summary) ----
    users = load_json("../data/users.json")

    # Pre-compute per-user purchase summary from transactions
    summary = defaultdict(lambda: {"total_spent": 0.0, "order_count": 0, "last_purchase_date": None})
    for t in transactions:
        s = summary[t["user_id"]]
        s["total_spent"] += t["total"]
        s["order_count"] += 1
        if s["last_purchase_date"] is None or t["timestamp"] > s["last_purchase_date"]:
            s["last_purchase_date"] = t["timestamp"]

    for u in users:
        s = summary.get(u["user_id"], {"total_spent": 0.0, "order_count": 0, "last_purchase_date": None})
        u["purchase_summary"] = {
            "total_spent": round(s["total_spent"], 2),
            "order_count": s["order_count"],
            "last_purchase_date": s["last_purchase_date"],
        }

    db.users.drop()
    db.users.insert_many(users)
    print(f"Loaded {len(users)} users (with embedded purchase_summary)")

    # ---- Sessions (loaded from all sessions_*.json chunk files) ----
    db.sessions.drop()
    session_files = sorted(glob.glob("../data/sessions_*.json"))
    total_sessions = 0
    for sf in session_files:
        sessions = load_json(sf)
        if sessions:
            db.sessions.insert_many(sessions)
        total_sessions += len(sessions)
    print(f"Loaded {total_sessions} sessions from {len(session_files)} file(s)")

    # ---- Indexes to support the analytical queries we'll run ----
    db.transactions.create_index([("user_id", ASCENDING)])
    db.transactions.create_index([("timestamp", ASCENDING)])
    db.transactions.create_index([("items.product_id", ASCENDING)])
    db.sessions.create_index([("user_id", ASCENDING)])
    db.sessions.create_index([("viewed_products", ASCENDING)])
    db.products.create_index([("category_id", ASCENDING)])
    db.users.create_index([("user_id", ASCENDING)], unique=True)
    print("Indexes created.")

    print("\nMongoDB load complete.")
    print(f"  categories:   {db.categories.count_documents({})}")
    print(f"  products:     {db.products.count_documents({})}")
    print(f"  users:        {db.users.count_documents({})}")
    print(f"  transactions: {db.transactions.count_documents({})}")
    print(f"  sessions:     {db.sessions.count_documents({})}")


if __name__ == "__main__":
    main()
