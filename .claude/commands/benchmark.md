---
description: Run comprehensive article benchmarks with query tests and generate reports
---

Run the full article benchmark suite with query tests across all databases (MongoDB, PostgreSQL JSON/JSONB, Oracle JCT), monitor progress every 3 minutes, generate HTML report, and update summary markdown files.

**Test Configuration:**
- Documents: 10,000 per test
- Payload sizes: 10B, 200B, 1000B, 2000B, 4000B
- Attribute configurations: Single-attribute and multi-attribute (10×, 50×, 100×, 200×)
- Runs: 3 (best time reported)
- Batch size: 500
- Query tests: ENABLED (10 links per document)
- All databases: WITH INDEXES

**What this command does:**
1. Runs article benchmarks with query tests (60-minute timeout)
2. Monitors and reports progress every 3 minutes
3. Generates HTML report when complete
4. Updates summary markdown files with findings

**Expected Duration:** 45-60 minutes

---

## Step 1: Make the benchmark script executable and run it

```bash
chmod +x run_full_benchmark.sh
./run_full_benchmark.sh
```

This script will:
- Run all benchmarks in the background with progress monitoring
- Show updates every 3 minutes
- Generate the HTML report automatically when complete
- Display final results and next steps

## Step 2: After benchmarks complete, update summary files

Once the benchmarks finish successfully, analyze the results from `article_benchmark_results.json` and `benchmark_report.html` and update these summary markdown files:

### Files to update:
1. **EXECUTIVE_SUMMARY.md** - Overall benchmark findings and key insights
2. **THREE_PLATFORM_COMPARISON.md** - Three-way comparison between MongoDB, PostgreSQL, and Oracle

### What to include in updates:
- Latest benchmark results with BOTH insertion AND query performance
- Key findings for each test category (single-attribute, multi-attribute)
- Winner for each metric:
  - Insertion time (single-attribute and multi-attribute)
  - Query time (single-attribute and multi-attribute)
  - Throughput (insertion and query)
  - Performance degradation (scalability)
- Comparison insights between databases
- Updated recommendations based on indexed performance with query tests

### Important notes:
- All databases now use indexes, so update any previous comparisons accordingly
- Query performance data is NEW - ensure it's prominently featured
- Focus on practical insights for different use cases (writes vs reads, attribute patterns, etc.)

**Output Files:**
- `benchmark_run.log` - Full execution log with all test results
- `article_benchmark_results.json` - JSON results with insertion and query data
- `benchmark_report.html` - Interactive HTML report with charts and visualizations
