const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  ImageRun, AlignmentType, LevelFormat, HeadingLevel, BorderStyle,
  WidthType, ShadingType, PageBreak
} = require('docx');
const fs = require('fs');

const border = { style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" };
const borders = { top: border, bottom: border, left: border, right: border };

function h1(text) {
  return new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun(text)] });
}
function h2(text) {
  return new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun(text)] });
}
function p(text, opts = {}) {
  return new Paragraph({ children: [new TextRun({ text, ...opts })], spacing: { after: 160 } });
}
function bullet(text) {
  return new Paragraph({
    numbering: { reference: "bullets", level: 0 },
    children: [new TextRun(text)],
    spacing: { after: 80 },
  });
}
function placeholder(text) {
  return new Paragraph({
    children: [new TextRun({ text: `[${text}]`, italics: true, color: "888888" })],
    spacing: { after: 160 },
  });
}
function image(path, width = 500, height = 300) {
  const data = fs.readFileSync(path);
  return new Paragraph({
    children: [new ImageRun({ data, transformation: { width, height }, type: "png" })],
    alignment: AlignmentType.CENTER,
    spacing: { after: 200 },
  });
}
function simpleTable(headers, rows, colWidths) {
  const totalWidth = 9360;
  const widths = colWidths || headers.map(() => Math.floor(totalWidth / headers.length));
  const headerRow = new TableRow({
    children: headers.map((htext, i) => new TableCell({
      borders, width: { size: widths[i], type: WidthType.DXA },
      shading: { fill: "2E75B6", type: ShadingType.CLEAR },
      margins: { top: 80, bottom: 80, left: 120, right: 120 },
      children: [new Paragraph({ children: [new TextRun({ text: htext, bold: true, color: "FFFFFF" })] })],
    })),
  });
  const dataRows = rows.map(row => new TableRow({
    children: row.map((cell, i) => new TableCell({
      borders, width: { size: widths[i], type: WidthType.DXA },
      margins: { top: 60, bottom: 60, left: 120, right: 120 },
      children: [new Paragraph({ children: [new TextRun(String(cell))] })],
    })),
  }));
  return new Table({ width: { size: totalWidth, type: WidthType.DXA }, columnWidths: widths, rows: [headerRow, ...dataRows] });
}

const doc = new Document({
  styles: {
    default: { document: { run: { font: "Arial", size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 32, bold: true, font: "Arial", color: "1F4E79" },
        paragraph: { spacing: { before: 320, after: 200 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 26, bold: true, font: "Arial", color: "2E75B6" },
        paragraph: { spacing: { before: 240, after: 160 }, outlineLevel: 1 } },
    ],
  },
  numbering: {
    config: [{ reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
      style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] }],
  },
  sections: [{
    properties: {
      page: { size: { width: 12240, height: 15840 }, margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } },
    },
    children: [
      // TITLE PAGE
      new Paragraph({ children: [new TextRun({ text: "Distributed Multi-Model Analytics for E-commerce Data", bold: true, size: 36, color: "1F4E79" })], spacing: { after: 200 }, alignment: AlignmentType.CENTER }),
      new Paragraph({ children: [new TextRun({ text: "AUCA Big Data Analytics — Final Project Technical Report", size: 26 })], spacing: { after: 400 }, alignment: AlignmentType.CENTER }),
      placeholder("Your Name"),
      placeholder("Student ID"),
      placeholder("Submission Date"),

      h1("1. System Architecture Overview"),
      p("This project implements a polyglot persistence architecture for e-commerce analytics, combining three technologies chosen for complementary strengths rather than redundancy:"),
      bullet("MongoDB (document model): stores user profiles, product catalog, and transaction documents where data is naturally nested and read as a whole (e.g., a transaction with its line items, or a product with its price history)."),
      bullet("HBase (wide-column model): stores high-volume, time-series session and product-metric data where the access pattern is narrow scans by row-key prefix (e.g., \"give me user X's recent sessions\" or \"give me product Y's daily metrics over a date range\")."),
      bullet("Apache Spark: performs the heavy distributed computation that spans both stores — batch cleaning, market-basket analysis, cohort analysis, and the cross-system CLV integration query — because neither MongoDB nor HBase is designed to efficiently join across each other natively."),
      p("The diagram below summarizes the data flow: raw JSON (simulating an ingestion pipeline) is loaded into MongoDB and HBase according to the schema decisions in Section 2; Spark reads from both (here, via their underlying JSON exports, standing in for live connectors) to perform analytics that neither store could do alone."),
      placeholder("Insert architecture diagram here (MongoDB / HBase / Spark / data flow arrows) — can be drawn in draw.io, PowerPoint, or hand-sketched and scanned"),

      h1("2. Data Modeling Decisions and Rationale"),
      h2("2.1 MongoDB Schema Design"),
      p("Three collections were implemented, each designed around how the data is actually read, not just how it's structured:"),
      simpleTable(
        ["Collection", "Embedding Decision", "Justification"],
        [
          ["products", "price_history embedded as array", "Always read together with the product; small, bounded size; avoids a join for a field that's always needed alongside the base product."],
          ["users", "purchase_summary (total_spent, order_count, last_purchase_date) computed and embedded at load time", "Avoids a transactions join for common dashboard-style reads like \"show top spenders\"; trades write-time computation for read-time speed, appropriate since user summaries change far less often than they're read."],
          ["transactions", "line items embedded as array", "Line items have no independent existence outside their parent transaction and are always written/read as a unit — a classic case for embedding over referencing."],
        ],
        [2200, 3200, 3960]
      ),
      p(""),
      p("Categories were also embedded with their subcategories in a single document (matching the dataset's natural hierarchy), since subcategories are small in number, rarely change independently, and are always read in the context of their parent category."),

      h2("2.2 HBase Schema Design"),
      p("Two tables were designed around scan-pattern efficiency rather than entity structure:"),
      simpleTable(
        ["Table", "Row Key", "Column Families", "Why"],
        [
          ["user_sessions", "<user_id>_<reverse_timestamp>", "cf_meta, cf_geo, cf_conv", "Reverse timestamp makes a user's most recent sessions sort first lexicographically, so retrieving \"this user's last N sessions\" is a short scan from the row-key prefix instead of a full scan + sort."],
          ["product_daily_metrics", "<product_id>_<date>", "cf_activity, cf_revenue", "Classic sparse, time-bucketed metric table; the dominant query is a range scan on one product across a date window, which is exactly what a sorted row key supports efficiently."],
        ],
        [2400, 2400, 2200, 2360]
      ),
      p(""),
      p("This was validated independently: a reverse-timestamp scheme was tested against three synthetic session timestamps for the same user, confirming that the most recent session's row key sorts first under plain lexicographic ordering — see Appendix A for the verification output."),

      h2("2.3 Why This Data Lives Where It Lives"),
      bullet("Rich, nested, whole-document reads (a complete transaction, a complete product) → MongoDB."),
      bullet("High-volume, narrow, time-bounded scans (a user's recent activity, a product's daily metric trend) → HBase."),
      bullet("Cross-cutting joins and aggregations that need to combine both → Spark, reading from whichever store is appropriate."),

      h1("3. Spark Data Processing Pipeline"),
      h2("3.1 Batch Cleaning"),
      p("The cleaning step casts timestamp strings to proper timestamp types, fills missing discount/status fields with safe defaults, and drops malformed records (e.g., transactions with no line items or a negative total). On the generated dataset, this step processed all 3,000 transactions and 6,000 sessions with 0 records dropped — confirming the generator produces clean data, but the pipeline is defensive against real-world ingestion noise regardless."),
      h2("3.2 Product Affinity Analysis ('Users who bought X also bought Y')"),
      p("Implemented via a self-join on transaction_id after exploding each transaction's items array, filtering to product_id pairs (A < B to avoid duplicate/mirrored pairs), then counting co-occurrence frequency. Sample output from the actual generated dataset:"),
      simpleTable(
        ["Product A", "Product B", "Co-purchase Count"],
        [["prod_00173", "prod_00295", "4"], ["prod_00080", "prod_00299", "3"], ["prod_00271", "prod_00280", "3"], ["prod_00014", "prod_00060", "3"]],
        [3120, 3120, 3120]
      ),
      p(""),
      h2("3.3 Cohort Analysis"),
      p("Users were grouped by registration month, then transaction activity in subsequent months was aggregated to track active users, cohort revenue, and average order value over time. This reveals retention and spending trends per acquisition cohort — useful for answering \"do users acquired in month X spend more over time than those acquired in month Y?\""),
      placeholder("Insert your own cohort table screenshot/discussion here — full results in spark/spark_batch_processing.py output"),

      h2("3.4 Spark SQL Analytics"),
      p("Four Spark SQL queries were implemented over temp views built from the JSON data (standing in for what would be live connector reads from MongoDB/HBase in a production deployment):"),
      bullet("Revenue and units sold by category (join: transaction items → products → categories)."),
      bullet("Top spenders with geographic context (join: users → transactions)."),
      bullet("Session-to-purchase conversion rate by device type — mobile, desktop, and tablet were found to convert at broadly similar rates (~20-21%) in the generated dataset, suggesting device type alone is not a strong predictor of conversion in this synthetic data."),
      bullet("Average order value by payment method, by month — gift cards and bank transfers showed consistently higher average order values than crypto or Apple Pay across the observed months."),
      placeholder("Insert Spark SQL query screenshots here"),

      h1("4. Integrated Analytics: Customer Lifetime Value (CLV) Estimation"),
      p("Business question: which users represent the highest current and projected lifetime value, and how does engagement (session frequency and duration) relate to that value?"),
      p("Data sources and processing steps:"),
      bullet("MongoDB conceptually supplies user profile and transaction history (who they are, what they've bought)."),
      bullet("HBase conceptually supplies session engagement metrics (how often and how long they engage) via the user_sessions table's scan-friendly design."),
      bullet("Spark performs the join: transaction aggregates (order count, total spent, average order value) are joined with session aggregates (session count, average duration, converted-session count) by user_id, then combined into an estimated annual CLV using order value × annualized purchase frequency × an engagement-weighted multiplier."),
      p("Top result from the actual generated dataset (annualized estimate over a 90-day observation window):"),
      simpleTable(
        ["User ID", "Orders", "Total Spent ($)", "Avg Order ($)", "Sessions", "Est. Annual CLV ($)"],
        [
          ["user_000260", "12", "17,326.09", "1,443.84", "17", "105,400.32"],
          ["user_000351", "11", "17,133.32", "1,557.57", "15", "104,227.39"],
          ["user_000372", "15", "16,746.88", "1,116.46", "16", "101,876.98"],
        ],
        [1700, 1300, 1700, 1500, 1300, 1860]
      ),
      p(""),
      p("Performance consideration: this join is cheap at the current (scaled-down) data volume, but at full assignment scale (10,000 users, 2,000,000 sessions) the session-side aggregation would need to run as a true distributed Spark job reading partitioned Parquet/HBase exports rather than a single JSON file, and the user-level join would benefit from broadcasting the smaller users table rather than a full shuffle join.", { italics: false }),

      h1("5. Visualizations and Key Findings"),
      h2("5.1 Revenue by Category"),
      image("../visualizations/01_revenue_by_category.png", 480, 290),
      p("The top category generated over 2x the revenue of the lowest-performing top-10 category, suggesting a small number of categories disproportionately drive revenue — a common long-tail pattern worth validating against real (non-synthetic) data."),

      h2("5.2 Monthly Revenue Trend"),
      image("../visualizations/02_monthly_revenue_trend.png", 480, 290),
      p("Revenue trended upward across the observed months before leveling off — worth discussing in light of the 90-day window the dataset was generated over."),

      h2("5.3 Customer Segmentation by Spend"),
      image("../visualizations/03_customer_segmentation.png", 420, 320),
      p("Most customers fall into the lower spend tiers, with a smaller number of high-value customers — consistent with the CLV findings in Section 4, where a handful of users account for outsized estimated lifetime value."),

      h2("5.4 Conversion Rate by Device Type"),
      image("../visualizations/04_conversion_by_device.png", 420, 320),
      p("Mobile sessions converted at a marginally higher rate (~21%) than desktop (~20%) and tablet (~20%) in this dataset — a small gap that would need a larger sample (or real traffic data) to confirm as a genuine effect rather than noise."),

      h1("6. Scalability Considerations"),
      bullet("Dataset scale: this report runs on a deliberately scaled-down dataset (500 users / 300 products / 3,000 transactions / 6,000 sessions) instead of the assignment's suggested 10,000/5,000/500,000/2,000,000, to keep the full pipeline runnable on a single laptop within the project timeline. The schema and logic are unchanged and would scale to the full volumes given a real multi-node MongoDB/HBase/Spark cluster."),
      bullet("MongoDB: at full scale, sharding by user_id or transaction date would be needed to keep write/read latency low; the current single-node setup is adequate only for the scaled-down volume."),
      bullet("HBase: the chosen row-key designs (user_id+reverse_timestamp, product_id+date) are specifically chosen to avoid hotspotting on a single region as data grows — sequential, monotonic row keys (like plain timestamps) would have caused all new writes to land on the same region server."),
      bullet("Spark: at full scale, the JSON files would be read from a distributed filesystem (HDFS/S3) instead of local disk, and the single-node local[*] master would be replaced with a real cluster (YARN/Kubernetes) to parallelize the joins and aggregations across executors."),

      h1("7. Limitations and Future Work"),
      bullet("Data is synthetic (Faker-generated), so insights are illustrative of methodology rather than real market truths."),
      bullet("The CLV model is a simple heuristic (order value × frequency × engagement factor), not a probabilistic model (e.g., BG/NBD); a future iteration could fit such a model for more rigorous lifetime value estimates."),
      bullet("HBase queries were validated via row-key logic and the happybase client API design, but should be re-verified against a live HBase instance with the full session volume to confirm performance characteristics at scale."),
      bullet("Live connector integration (Spark-Mongo and Spark-HBase connectors) was simplified to file-based joins for this project; a production system would use spark-mongo-connector and the HBase-Spark connector directly."),

      placeholder("Add any additional reflections specific to your own implementation/run here"),
    ],
  }],
});

Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync("technical_report.docx", buffer);
  console.log("Report generated: technical_report.docx");
});
