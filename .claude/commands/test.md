---
description: Benchmark MongoDB vs Oracle JSON Collection Tables
---

Run comprehensive benchmarks comparing MongoDB and Oracle JSON Collection Tables, and generate an HTML report with visualizations.

**Test Configuration:**
- Documents: 10,000
- Payload sizes: 100B and 1000B
- Attributes: 1 and 10 (single attribute vs multi-attribute split)
- Runs: 3 (keeps best result)
- Batch size: 500 (optimized)
- Databases: MongoDB and Oracle JSON Collection Tables (with and without search index)

**Steps:**
1. Ensure the project is built (mvn clean package)
2. Run all benchmarks and generate report using Python script
3. Open the generated HTML report

Please execute the following:

First, build the project:
```bash
cd /mnt/c/Users/rickh/OneDrive/Documents/GitHub/BSON-JSON-bakeoff
mvn clean package
```

Then run the report generator (this will run all benchmarks and create the HTML report):
```bash
python3 generate_report.py
```

The script will:
- Run MongoDB benchmark with parameters: `-s 100,1000 -n 10 -r 3 -b 500 10000`
- Run Oracle JCT benchmark WITHOUT search index: `-oj -s 100,1000 -n 10 -r 3 -b 500 10000`
- Run Oracle JCT benchmark WITH search index: `-oj -i -s 100,1000 -n 10 -r 3 -b 500 10000`
- Parse all results into standardized JSON format
- Generate an HTML report with interactive charts

**Output Files:**
- `benchmark_results.json` - Standardized JSON results
- `benchmark_report.html` - Interactive HTML report with graphs

After completion, open `benchmark_report.html` in a web browser to view the full report with visualizations.
