"""
mongo_queries.py
Two non-trivial aggregation pipelines required by Part 1 of the assignment:

  1. Product Popularity Analysis
     - "Most purchased" (from transactions.items) and
       "most viewed" (from sessions.viewed_products), side by side.

  2. Revenue Analytics by Category and Month
     - Joins transactions -> products -> categories to get revenue
       broken down by category and by month, using $lookup + $unwind.

Run:
    python mongo_queries.py
"""

from pymongo import MongoClient
import pprint

client = MongoClient("mongodb://localhost:27017")
db = client["ecommerce"]


def product_popularity_pipeline():
    print("\n=== 1. PRODUCT POPULARITY: Most Purchased ===")
    pipeline_purchased = [
        {"$unwind": "$items"},
        {
            "$group": {
                "_id": "$items.product_id",
                "total_quantity_sold": {"$sum": "$items.quantity"},
                "total_revenue": {"$sum": "$items.subtotal"},
                "times_purchased": {"$sum": 1},
            }
        },
        {"$sort": {"total_quantity_sold": -1}},
        {"$limit": 10},
        {
            "$lookup": {
                "from": "products",
                "localField": "_id",
                "foreignField": "product_id",
                "as": "product_info",
            }
        },
        {"$unwind": "$product_info"},
        {
            "$project": {
                "product_id": "$_id",
                "product_name": "$product_info.name",
                "total_quantity_sold": 1,
                "total_revenue": {"$round": ["$total_revenue", 2]},
                "times_purchased": 1,
                "_id": 0,
            }
        },
    ]
    results = list(db.transactions.aggregate(pipeline_purchased))
    pprint.pprint(results)

    print("\n=== 1b. PRODUCT POPULARITY: Most Viewed ===")
    pipeline_viewed = [
        {"$unwind": "$viewed_products"},
        {"$group": {"_id": "$viewed_products", "view_count": {"$sum": 1}}},
        {"$sort": {"view_count": -1}},
        {"$limit": 10},
        {
            "$lookup": {
                "from": "products",
                "localField": "_id",
                "foreignField": "product_id",
                "as": "product_info",
            }
        },
        {"$unwind": "$product_info"},
        {
            "$project": {
                "product_id": "$_id",
                "product_name": "$product_info.name",
                "view_count": 1,
                "_id": 0,
            }
        },
    ]
    results = list(db.sessions.aggregate(pipeline_viewed))
    pprint.pprint(results)


def revenue_by_category_and_month_pipeline():
    print("\n=== 2. REVENUE ANALYTICS: By Category and Month ===")
    pipeline = [
        {"$unwind": "$items"},
        {
            "$lookup": {
                "from": "products",
                "localField": "items.product_id",
                "foreignField": "product_id",
                "as": "product_info",
            }
        },
        {"$unwind": "$product_info"},
        {
            "$lookup": {
                "from": "categories",
                "localField": "product_info.category_id",
                "foreignField": "category_id",
                "as": "category_info",
            }
        },
        {"$unwind": "$category_info"},
        {
            "$addFields": {
                "year_month": {"$substrCP": ["$timestamp", 0, 7]}  # "YYYY-MM"
            }
        },
        {
            "$group": {
                "_id": {
                    "category_name": "$category_info.name",
                    "year_month": "$year_month",
                },
                "revenue": {"$sum": "$items.subtotal"},
                "units_sold": {"$sum": "$items.quantity"},
            }
        },
        {
            "$project": {
                "_id": 0,
                "category_name": "$_id.category_name",
                "year_month": "$_id.year_month",
                "revenue": {"$round": ["$revenue", 2]},
                "units_sold": 1,
            }
        },
        {"$sort": {"year_month": 1, "revenue": -1}},
    ]
    results = list(db.transactions.aggregate(pipeline))
    pprint.pprint(results[:20])
    print(f"... ({len(results)} total category/month rows)")


def basic_user_segmentation_pipeline():
    print("\n=== Bonus: User Segmentation by Spend Tier ===")
    pipeline = [
        {
            "$bucket": {
                "groupBy": "$purchase_summary.total_spent",
                "boundaries": [0, 50, 150, 300, 1000, 100000],
                "default": "100000+",
                "output": {
                    "user_count": {"$sum": 1},
                    "avg_orders": {"$avg": "$purchase_summary.order_count"},
                },
            }
        }
    ]
    results = list(db.users.aggregate(pipeline))
    pprint.pprint(results)


if __name__ == "__main__":
    product_popularity_pipeline()
    revenue_by_category_and_month_pipeline()
    basic_user_segmentation_pipeline()
