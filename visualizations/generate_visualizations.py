"""
generate_visualizations.py
Part 4 - Visualization and Insights.
Produces 4 static charts from the actual generated dataset:
  1. Revenue by category (bar chart)
  2. Revenue over time / monthly trend (line chart)
  3. Customer segmentation: spend distribution by tier (bar chart)
  4. Conversion funnel by device type (bar chart)

Run:
    pip install matplotlib --break-system-packages
    python3 generate_visualizations.py
Output goes to ../visualizations/*.png
"""

import json
from collections import defaultdict
import matplotlib.pyplot as plt

DATA_DIR = "/workspace/data"
OUT_DIR = "../visualizations"


def load_json(path):
    with open(path) as f:
        return json.load(f)


def chart_revenue_by_category():
    transactions = load_json(f"{DATA_DIR}/transactions.json")
    products = {p["product_id"]: p for p in load_json(f"{DATA_DIR}/products.json")}
    categories = {c["category_id"]: c["name"] for c in load_json(f"{DATA_DIR}/categories.json")}

    revenue = defaultdict(float)
    for t in transactions:
        for item in t["items"]:
            cat_id = products[item["product_id"]]["category_id"]
            revenue[categories[cat_id]] += item["subtotal"]

    sorted_items = sorted(revenue.items(), key=lambda x: -x[1])[:10]
    names = [n for n, _ in sorted_items]
    values = [v for _, v in sorted_items]

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.barh(names[::-1], values[::-1], color="#4C72B0")
    ax.set_xlabel("Revenue ($)")
    ax.set_title("Top 10 Categories by Revenue")
    plt.tight_layout()
    plt.savefig(f"{OUT_DIR}/01_revenue_by_category.png", dpi=150)
    plt.close()
    print("Saved 01_revenue_by_category.png")


def chart_monthly_revenue_trend():
    transactions = load_json(f"{DATA_DIR}/transactions.json")
    monthly = defaultdict(float)
    for t in transactions:
        ym = t["timestamp"][:7]
        monthly[ym] += t["total"]

    months = sorted(monthly.keys())
    values = [monthly[m] for m in months]

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(months, values, marker="o", color="#DD8452", linewidth=2)
    ax.set_xlabel("Month")
    ax.set_ylabel("Total Revenue ($)")
    ax.set_title("Monthly Revenue Trend")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(f"{OUT_DIR}/02_monthly_revenue_trend.png", dpi=150)
    plt.close()
    print("Saved 02_monthly_revenue_trend.png")


def chart_customer_segmentation():
    transactions = load_json(f"{DATA_DIR}/transactions.json")
    spend = defaultdict(float)
    for t in transactions:
        spend[t["user_id"]] += t["total"]

    tiers = {"$0-50": 0, "$50-150": 0, "$150-300": 0, "$300-1000": 0, "$1000+": 0}
    for v in spend.values():
        if v < 50:
            tiers["$0-50"] += 1
        elif v < 150:
            tiers["$50-150"] += 1
        elif v < 300:
            tiers["$150-300"] += 1
        elif v < 1000:
            tiers["$300-1000"] += 1
        else:
            tiers["$1000+"] += 1

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.bar(tiers.keys(), tiers.values(), color="#55A868")
    ax.set_ylabel("Number of Customers")
    ax.set_title("Customer Segmentation by Total Spend")
    plt.tight_layout()
    plt.savefig(f"{OUT_DIR}/03_customer_segmentation.png", dpi=150)
    plt.close()
    print("Saved 03_customer_segmentation.png")


def chart_conversion_by_device():
    sessions = load_json(f"{DATA_DIR}/sessions_0.json")
    device_totals = defaultdict(int)
    device_converted = defaultdict(int)
    for s in sessions:
        d = s["device_profile"]["type"]
        device_totals[d] += 1
        if s["conversion_status"] == "converted":
            device_converted[d] += 1

    devices = list(device_totals.keys())
    rates = [100 * device_converted[d] / device_totals[d] for d in devices]

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.bar(devices, rates, color="#C44E52")
    ax.set_ylabel("Conversion Rate (%)")
    ax.set_title("Session-to-Purchase Conversion Rate by Device Type")
    for i, r in enumerate(rates):
        ax.text(i, r + 0.3, f"{r:.1f}%", ha="center")
    plt.tight_layout()
    plt.savefig(f"{OUT_DIR}/04_conversion_by_device.png", dpi=150)
    plt.close()
    print("Saved 04_conversion_by_device.png")


if __name__ == "__main__":
    chart_revenue_by_category()
    chart_monthly_revenue_trend()
    chart_customer_segmentation()
    chart_conversion_by_device()
    print("\nAll visualizations generated in", OUT_DIR)
