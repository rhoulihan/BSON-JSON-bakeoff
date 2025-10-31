# Benchmark Files Index

All files generated from the 3-platform document storage benchmark comparing MongoDB BSON, Oracle JSON Collection Tables, and PostgreSQL JSON/JSONB.

---

## 📊 Analysis Reports

### **THREE_PLATFORM_COMPARISON.md** (RECOMMENDED - START HERE)
**Size:** ~50KB | **Lines:** 500+

Comprehensive analysis comparing all three platforms:
- Complete results tables (single & multi-attribute)
- Performance degradation analysis
- Throughput comparisons
- Technical deep dives
- Platform-specific recommendations
- Cost-benefit analysis
- Use case recommendations

### **EXECUTIVE_SUMMARY.md**
**Size:** ~15KB | **Lines:** 200+

High-level summary document with:
- Bottom line recommendations
- Key performance numbers
- Critical insights
- Quick decision matrix
- Performance rankings

### **QUICK_REFERENCE.txt**
**Size:** ~6KB | **Lines:** 150

ASCII-art formatted quick reference card:
- Results tables with box drawing
- Performance degradation scores
- Critical findings highlighted
- Recommendations checklist
- Easy to print/share

### **benchmark_report.html**
**Type:** Interactive HTML Report

Rich HTML report with Chart.js visualizations:
- Interactive line graphs for all test configurations
- Single-attribute and multi-attribute performance charts
- Throughput comparison visualizations
- Degradation analysis charts
- Detailed results tables with color-coded winners
- Responsive design with gradient styling

---

## 📁 Raw Data Files

### **article_benchmark_results.json**
**Format:** JSON

Unified results from all platforms:
```json
{
  "timestamp": "2025-10-30T17:52:12.254763",
  "configuration": {
    "documents": 10000,
    "runs": 3,
    "batch_size": 500
  },
  "single_attribute": {
    "mongodb": [...],
    "oracle_no_index": [...],
    "oracle_with_index": [...],
    "postgresql_json": [...],
    "postgresql_jsonb": [...]
  },
  "multi_attribute": {...}
}
```

---

## 🔧 Test Scripts

### **run_article_benchmarks.py**
**Language:** Python 3

Main benchmark script that runs:
- MongoDB BSON tests
- PostgreSQL JSON tests
- PostgreSQL JSONB tests
- Oracle JCT tests (with and without index)
- Database lifecycle management (start/stop databases automatically)
- All single & multi-attribute configurations

Usage:
```bash
python3 run_article_benchmarks.py
```

### **generate_html_report.py**
**Language:** Python 3

Generates interactive HTML report with Chart.js visualizations:
- Reads article_benchmark_results.json
- Creates 5 interactive line charts
- Generates detailed results tables
- Outputs benchmark_report.html

Usage:
```bash
python3 generate_html_report.py
```

### **update_all_documents.py**
**Language:** Python 3

Updates all analysis documents with exact benchmark results:
- Updates EXECUTIVE_SUMMARY.md
- Updates QUICK_REFERENCE.txt
- Updates BENCHMARK_FILES_INDEX.md
- Ensures all numbers match article_benchmark_results.json

Usage:
```bash
python3 update_all_documents.py
```

---

## 📈 Visual Results

### Console Output Summary
```
SINGLE-ATTRIBUTE RESULTS (10K docs)
Payload      MongoDB      Oracle JCT   PG-JSON      PG-JSONB
10B              274ms        257ms        192ms        206ms
200B             256ms        281ms        676ms       1616ms
1KB              268ms        320ms       3590ms       6531ms
2KB              325ms        352ms       7583ms      12502ms
4KB              339ms        434ms      15910ms      24447ms

MULTI-ATTRIBUTE RESULTS (10K docs)
Config          MongoDB      Oracle JCT   PG-JSON      PG-JSONB
10×1B                265ms        263ms        216ms        248ms
10×20B               271ms        275ms        726ms       1624ms
50×20B               375ms        363ms       4080ms       7296ms
100×20B              597ms        527ms       8135ms      14629ms
200×20B              804ms        699ms      16173ms      28253ms
```

---

## 🎯 Key Findings Summary

### Platform Rankings

1. **MongoDB BSON & Oracle JCT** - Co-winners (each excels at different workloads)

   **MongoDB BSON:**
   - Best for large single-attribute documents (1-4KB)
   - Best consistency (1.24x degradation)
   - Proven ecosystem and horizontal scaling

   **Oracle JCT:**
   - Best for complex multi-attribute documents (100-200+ attrs)
   - Wins most complex test: 200 attributes (699ms vs MongoDB 804ms - 13% faster!)
   - Wins small documents (10B)
   - Surprisingly robust, SQL access

2. **PostgreSQL JSONB** - Niche use only
   - Only wins tiny docs when not indexed
   - 119x degradation (catastrophic)
   - TOAST cliff at 2KB

### Critical Numbers

**Single-Attribute 4KB (Large single-attribute docs):**
- MongoDB: 339ms ✓ (Winner)
- Oracle: 434ms (28% slower)
- PG-JSONB: 24447ms (72x slower!)

**Multi-Attribute 200×20B (Complex multi-attribute docs):**
- Oracle: 699ms ✓ (Winner - 15% FASTER than MongoDB!)
- MongoDB: 804ms
- PG-JSONB: 28253ms (40x slower!)

---

## 🔬 Test Specifications

**Workload:**
- 10,000 documents per test
- 3 runs per configuration (best time reported)
- Batch size: 500
- Deterministic seed: 42 (reproducible)

**Configurations Tested:**
- Single-attribute: 5 sizes (10B, 200B, 1KB, 2KB, 4KB)
- Multi-attribute: 5 configs (10×1B, 10×20B, 50×20B, 100×20B, 200×20B)
- Total: 50 test configurations (5 databases × 10 configs)
- Per platform: 30 benchmark runs
- All platforms: 150 total runs

**Environment:**
- OS: Oracle Linux 9.6
- PostgreSQL: 17.6
- Oracle: 26ai Free
- MongoDB: Latest

**Duration:** ~20 minutes total

---

## 📚 How to Use These Files

### For Executive Decision-Making
1. Read **EXECUTIVE_SUMMARY.md**
2. Review **QUICK_REFERENCE.txt**
3. Check specific concerns in **THREE_PLATFORM_COMPARISON.md**
4. View interactive charts in **benchmark_report.html**

### For Technical Analysis
1. Start with **THREE_PLATFORM_COMPARISON.md**
2. Review raw data in **article_benchmark_results.json**
3. Explore interactive visualizations in **benchmark_report.html**

### For Reproducing Tests
1. Review test script: `run_article_benchmarks.py`
2. Check configurations in source code
3. Run tests with: `python3 run_article_benchmarks.py`
4. Compare results with JSON files
5. Generate new report with: `python3 generate_html_report.py`

---

## 🎓 Bottom Line

**All files support the same conclusion:**

Use **MongoDB or Oracle JCT** for document workloads. They are co-winners, each excelling at different workload types. PostgreSQL's TOAST mechanism makes it unsuitable for documents >2KB despite excellent relational capabilities.

- **MongoDB:** Best for large single-attribute documents (1-4KB), proven ecosystem
- **Oracle JCT:** Surprisingly robust, WINS for complex multi-attribute documents (100-200+ attrs)
- **PostgreSQL:** Only for tiny docs (<200B) in hybrid systems

**Key finding:** Oracle beats MongoDB by 13% at the most complex test (200 attributes)

---

**Generated:** October 30, 2025
**Repository:** /home/rhoulihan/claude/BSON-JSON-bakeoff/
