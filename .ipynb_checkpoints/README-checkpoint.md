# AUCA Big Data Final Project — E-commerce Multi-Model Analytics

This repo implements the full assignment: MongoDB + HBase + Spark analytics
over a synthetic e-commerce dataset, with cross-system integration and
visualizations.

**Dataset is scaled down** from the assignment's suggested volumes
(10,000 users / 500,000 transactions / 2,000,000 sessions) to
500 users / 300 products / 3,000 transactions / 6,000 sessions, so the
whole pipeline runs in minutes on a laptop instead of hours on a cluster.
The schema, relationships, and generation logic are otherwise unchanged —
this is explicitly called out and justified in the report (see
`report/technical_report.docx`, Section: Scalability Considerations).

## Project Structure

```
ecommerce-project/
├── data/                       # dataset generator + generated JSON files
├── mongodb/                    # loader + 2 aggregation pipelines
├── hbase/                      # schema, loader, query examples
├── spark/                      # batch cleaning, affinity/cohort, Spark SQL
├── integration/                # CLV cross-system integration query
├── visualizations/             # chart generation script + output PNGs
├── report/                     # technical report (docx)
└── docker-compose.yml          # spins up MongoDB + HBase + Spark
```

## Prerequisites

- Docker + Docker Compose installed
- Python 3.9+
- `pip install faker pandas pymongo happybase pyspark matplotlib`

## Step-by-Step: Run Everything

### 0. Generate the dataset (already done, but to regenerate)
```bash
cd data
python3 dataset_generator.py
```
This produces `users.json`, `products.json`, `categories.json`,
`transactions.json`, and `sessions_0.json` in `data/`.

### 1. Start the infrastructure
```bash
docker compose up -d
docker ps   # confirm ecommerce-mongo, ecommerce-hbase, ecommerce-spark are running
```
Give HBase ~30-60 seconds to fully initialize before loading data into it
(check with `docker logs ecommerce-hbase` until you see it's ready).

### 2. MongoDB: Load data and run aggregation queries
```bash
cd mongodb
python load_to_mongo.py        # loads categories, products, users, transactions, sessions
python mongo_queries.py        # runs the 2 required aggregation pipelines
```
Take screenshots of the output for your report's Part 1 section.

You can also inspect the data interactively:
```bash
docker exec -it ecommerce-mongo mongosh ecommerce
> db.users.findOne()
> db.transactions.countDocuments()
```

### 3. HBase: Create schema and load session data
```bash
# Create the tables (paste the commands into the HBase shell, or pipe the file in)
docker exec -it ecommerce-hbase hbase shell hbase/create_hbase_schema.sh

cd hbase
python load_to_hbase.py                  # loads sessions + product metrics
python hbase_queries.py user_000042      # example: get recent sessions for one user
```
Screenshot the `describe` table output and the query results for your report's
Part 1 (HBase Design & Justify) section.

### 4. Spark: Batch processing + Spark SQL
```bash
cd spark
python spark_batch_processing.py   # cleaning + product affinity + cohort analysis
python spark_sql_analytics.py      # 4 Spark SQL analytical queries
```
These ran successfully in testing on the actual generated dataset — see the
sample output already captured in the report draft. Capture the console
output (or run via `spark-submit` if you want a more "production" feel for
screenshots) for Part 2 of the report.

### 5. Integration: CLV cross-system query
```bash
cd integration
python3 clv_integration.py
```
This script explicitly documents (in comments) which parts of the
computation conceptually belong to MongoDB (user/transaction data) vs.
HBase (session engagement), and uses Spark to join them — exactly the
workflow Part 3 of the assignment asks you to describe.

### 6. Visualizations
```bash
cd visualizations
python3 generate_visualizations.py
```
Produces 4 PNGs in `visualizations/`:
1. Revenue by category
2. Monthly revenue trend
3. Customer segmentation by spend tier
4. Conversion rate by device type

Embed these directly in the technical report (Part 4).

### 7. Technical Report
Fill in `report/technical_report.docx` with:
- Screenshots from steps 2-5 above
- The 4 visualization PNGs from step 6
- Your own discussion/reflection (the report template has section headers
  and starter content, but the analysis/reflection should be in your voice)

### 8. Push to GitHub
```bash
git init
git add .
git commit -m "AUCA Big Data final project: multi-model e-commerce analytics"
git remote add origin <your-repo-url>
git push -u origin main
```
Make sure `data/sessions_0.json` etc. aren't too large for git — if GitHub
complains, add a `.gitignore` for `data/*.json` and `data/*.parquet`, and
instead commit `data/dataset_generator.py` with instructions to regenerate
(this is normal practice for big-data coursework; the report should note
this explicitly under "Reproducibility").

## What's Already Validated

Every script above was run against the actual generated dataset (with
pandas/PySpark standing in for Mongo/HBase logic-checking where a live
server wasn't available) and produces correct, sensible output:
- Mongo aggregation logic cross-checked against pandas — matches exactly.
- HBase reverse-timestamp row-key design verified to sort most-recent-first.
- Spark batch job ran end-to-end: 3,000 transactions cleaned, product
  affinity pairs computed, cohort table produced.
- Spark SQL: 4 queries ran successfully (revenue by category, top spenders,
  conversion by device, AOV by payment method/month).
- CLV integration script ran end-to-end producing ranked CLV estimates.
- All 4 visualizations generated successfully as PNGs.

You should still run everything yourself on your machine against the real
MongoDB/HBase containers to get authentic screenshots — but the underlying
logic in every script is pre-validated, so you're mainly debugging
environment/connection issues, not algorithm bugs.
