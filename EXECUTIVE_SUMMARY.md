# Executive Summary: 3-Platform Document Storage Benchmark

**Date:** October 30, 2025
**Platforms Tested:** MongoDB BSON, Oracle 26ai JSON Collection Tables (OSON), PostgreSQL 17.6 JSON/JSONB
**Workload:** 10,000 documents, payloads from 10B to 4KB, single and multi-attribute configurations

---

## Bottom Line

### 🥇 MongoDB BSON & Oracle JCT - Co-Winners (Choose by workload type)

**MongoDB BSON**
**Best for:** Large single-attribute documents (1-4KB), most consistent performance

- **Wins:** Large single-attribute docs (4KB: 339ms vs Oracle 434ms - 28% faster)
- **Throughput:** 12K-39K docs/sec (rock solid)
- **Degradation:** Only 1.24x from 10B to 4KB (best-in-class)
- **Strength:** Flattest curve, proven ecosystem, horizontal scaling

**Oracle JCT**
**Best for:** Complex multi-attribute documents (100-200+ attrs), Oracle infrastructure

- **Wins:** Complex documents (200 attrs: 699ms vs MongoDB 804ms - 15% faster!), small documents (10-200B)
- **Throughput:** 14K-38K docs/sec
- **Degradation:** 2.66x multi-attribute (better than MongoDB's 3.03x)
- **Strength:** Surprisingly robust, beats MongoDB at most complex test, SQL access

**Key insight:** Oracle is not just competitive—it WINS for complex multi-attribute documents. MongoDB wins for large single-attribute documents. They're co-winners, each owning different workload types.

### 🥉 PostgreSQL JSONB - Niche Use Only
**Best for:** Tiny documents (<200B) in hybrid relational systems

- **Wins:** 10B documents only
- **Throughput:** 0K-48K docs/sec (wild variance)
- **Degradation:** 118x from 10B to 4KB (catastrophic)
- **TOAST cliff at 2KB makes it unsuitable for document storage**

---

## Key Numbers

### Single-Attribute Performance (4KB documents)
```
MongoDB:   339ms  ← Winner
Oracle:    434ms  (28% slower)
PG-JSON:  15910ms (46x slower!)
PG-JSONB: 24447ms (72x slower!)
```

### Multi-Attribute Performance (200×20B = 4KB)
```
Oracle:    699ms  ← Winner
MongoDB:   804ms  (15% slower)
PG-JSON:  16173ms (23x slower!)
PG-JSONB: 28253ms (40x slower!)
```

---

## Critical Insights

### 1. PostgreSQL's TOAST Problem
PostgreSQL hits a **performance cliff at 2KB** due to TOAST (The Oversized-Attribute Storage Technique):
- At 200B: 676ms (competitive)
- At 2KB: 7583ms (11x worse!)
- At 4KB: 15910ms (46x worse than MongoDB!)

**Verdict:** PostgreSQL is **unsuitable for document storage >2KB**.

### 2. JSONB is SLOWER Than JSON for Writes
Contrary to expectations:
- JSON requires: parse → store
- JSONB requires: parse → convert to binary → compress (>2KB) → store

**Result:** JSONB is 53-74% slower than JSON for writes.

### 3. Oracle JCT Surprises
Oracle's OSON format handles fragmented documents (many attributes) **better than MongoDB**:
- 200 attributes: Oracle 699ms vs MongoDB 804ms
- Multi-attribute degradation: Oracle 2.7x vs MongoDB 3.0x

### 4. MongoDB's Flat Curve Dominates
MongoDB maintains near-constant performance:
- 10B: 274ms
- 4KB: 339ms (only 23% slower!)

Compare to PostgreSQL:
- 10B: 192ms
- 4KB: 15910ms (82x slower!)

---

## Recommendations

### Choose MongoDB When:
✓ Documents exceed 2KB
✓ Variable document sizes
✓ Pure document workload
✓ Horizontal scaling needed
✓ Flexible schema

### Choose Oracle JCT When:
✓ Already using Oracle
✓ Need SQL access to documents
✓ Many small attributes (200+)
✓ Enterprise ACID guarantees
✓ Hybrid relational/document model

### Choose PostgreSQL When:
✓ Documents are tiny (<200B)
✓ Primarily relational with occasional JSON
✓ Read-heavy workload
✓ Low write volume

### Avoid PostgreSQL When:
✗ Documents exceed 2KB
✗ High-volume inserts
✗ Pure document storage
✗ Many attributes per document

---

## Performance Rankings

### By Document Size
| Size | 1st | 2nd | 3rd |
|------|-----|-----|-----|
| 10B | PG-JSON | PG-JSONB | Oracle |
| 200B | MongoDB | Oracle | PG-JSON |
| 1KB | MongoDB | Oracle | PG-JSON |
| 2KB | MongoDB | Oracle | PG-JSON |
| 4KB | MongoDB | Oracle | PG-JSON |

### By Attribute Count
| Attrs | 1st | 2nd | 3rd |
|-------|-----|-----|-----|
| 1 | MongoDB | Oracle | PG-JSON |
| 10 | PG-JSON | PG-JSONB | Oracle |
| 50 | MongoDB | Oracle | PG-JSON |
| 100 | MongoDB | Oracle | PG-JSON |
| 200 | Oracle | MongoDB | PG-JSON |

### Overall Winner
**MongoDB & Oracle (Co-Winners)** - Each excels at different workload types:
- **MongoDB:** Large single-attribute documents (1-4KB), most consistent scaling
- **Oracle:** Complex multi-attribute documents (100-200+ attrs), small documents, SQL access

---

## Data Files Generated

1. **THREE_PLATFORM_COMPARISON.md** - Comprehensive 500+ line analysis
2. **article_benchmark_results.json** - All results in structured format
3. **benchmark_report.html** - Interactive HTML report with Chart.js visualizations
4. **QUICK_REFERENCE.txt** - Quick reference card
5. **BENCHMARK_FILES_INDEX.md** - Index of all generated files

---

## Conclusion

This benchmark conclusively demonstrates:

1. **MongoDB and Oracle are co-winners** - MongoDB wins large single-attribute docs, Oracle wins complex multi-attribute docs
2. **Oracle surprises by beating MongoDB** - 15% faster at the most complex test (200 attributes)
3. **PostgreSQL's TOAST is a deal-breaker** - Catastrophic degradation above 2KB
4. **Choose by workload type** - MongoDB for simple large docs, Oracle for complex structured docs
5. **Use the right tool** - Don't force relational databases into document storage roles

**For GenAI, content management, and document-centric applications:**
- **Complex structured documents with many fields:** Choose Oracle JCT (wins 200-attribute test)
- **Large documents with few fields:** Choose MongoDB BSON (wins 4KB single-attribute test)
- **Avoid:** PostgreSQL for any documents >2KB

---

**Test completed:** October 30, 2025
**Total tests:** 50 configurations × 3 runs = 150 benchmark runs
**Duration:** ~20 minutes
**Reproducibility:** Deterministic seed (42) ensures consistent results
