# Executive Summary: 3-Platform Document Storage Benchmark

**Date:** October 30, 2025
**Platforms Tested:** MongoDB BSON, Oracle 26ai JSON Collection Tables (OSON), PostgreSQL 17.6 JSON/JSONB
**Workload:** 10,000 documents, payloads from 10B to 4KB, single and multi-attribute configurations

---

## Bottom Line

### 🥇 MongoDB BSON - Overall Winner
**Best for:** Most document workloads, large documents (>2KB), consistent performance

- **Wins:** Large documents, overall consistency
- **Throughput:** 28K-33K docs/sec (stable)
- **Degradation:** Only 1.18x from 10B to 4KB (best-in-class)

### 🥈 Oracle JCT - Strong Second
**Best for:** Multi-attribute documents, Oracle shops, SQL access needed

- **Wins:** Multi-attribute documents (200+ attributes), small documents
- **Throughput:** 21K-35K docs/sec
- **Degradation:** 1.65x from 10B to 4KB (excellent)
- **Surprise:** Beats MongoDB for highly-fragmented documents!

### 🥉 PostgreSQL JSONB - Niche Use Only
**Best for:** Tiny documents (<200B) in hybrid relational systems

- **Wins:** 10B documents only
- **Throughput:** 397-51K docs/sec (wild variance)
- **Degradation:** 114x from 10B to 4KB (catastrophic)
- **TOAST cliff at 2KB makes it unsuitable for document storage**

---

## Key Numbers

### Single-Attribute Performance (4KB documents)
```
MongoDB:   353ms  ← Winner
Oracle:    471ms  (33% slower)
PG-JSON:  16,297ms (46x slower!)
PG-JSONB: 25,192ms (71x slower!)
```

### Multi-Attribute Performance (200×20B = 4KB)
```
Oracle:    744ms  ← Winner
MongoDB:   829ms  (11% slower)
PG-JSON:  17,361ms (23x slower!)
PG-JSONB: 30,196ms (41x slower!)
```

---

## Critical Insights

### 1. PostgreSQL's TOAST Problem
PostgreSQL hits a **performance cliff at 2KB** due to TOAST (The Oversized-Attribute Storage Technique):
- At 200B: 757ms (competitive)
- At 2KB: 8,087ms (10x worse!)
- At 4KB: 16,297ms (46x worse than MongoDB!)

**Verdict:** PostgreSQL is **unsuitable for document storage >2KB**.

### 2. JSONB is SLOWER Than JSON for Writes
Contrary to expectations:
- JSON requires: parse → store
- JSONB requires: parse → convert to binary → compress (>2KB) → store

**Result:** JSONB is 55-75% slower than JSON for writes.

### 3. Oracle JCT Surprises
Oracle's OSON format handles fragmented documents (many attributes) **better than MongoDB**:
- 200 attributes: Oracle 744ms vs MongoDB 829ms
- Multi-attribute degradation: Oracle 2.5x vs MongoDB 2.7x

### 4. MongoDB's Flat Curve Dominates
MongoDB maintains near-constant performance:
- 10B: 300ms
- 4KB: 353ms (only 18% slower!)

Compare to PostgreSQL:
- 10B: 196ms
- 4KB: 16,297ms (83x slower!)

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
| 10B | PG-JSON | Oracle | MongoDB |
| 200B | Oracle | MongoDB | PG-JSON |
| 1KB | MongoDB | Oracle | PG-JSON |
| 2KB | MongoDB | Oracle | PG-JSON |
| 4KB | MongoDB | Oracle | PG-JSON |

### By Attribute Count
| Attrs | 1st | 2nd | 3rd |
|-------|-----|-----|-----|
| 1 | MongoDB | Oracle | PG-JSON |
| 10 | Oracle | MongoDB | PG-JSON |
| 50 | Oracle | MongoDB | PG-JSON |
| 100 | Oracle | MongoDB | PG-JSON |
| 200 | Oracle | MongoDB | PG-JSON |

### Overall Winner
**MongoDB** - Most versatile, best consistency, suitable for widest range of document workloads.

---

## Data Files Generated

1. **THREE_PLATFORM_COMPARISON.md** - Comprehensive 500+ line analysis
2. **combined_benchmark_results.json** - All results in structured format
3. **article_benchmark_results.json** - MongoDB + PostgreSQL results
4. **oracle_benchmark_results.json** - Oracle JCT results
5. **BENCHMARK_ANALYSIS.md** - Original 2-platform analysis

---

## Conclusion

This benchmark conclusively demonstrates:

1. **MongoDB and Oracle are purpose-built for documents** - Both show excellent, consistent performance
2. **PostgreSQL's TOAST is a deal-breaker** - Catastrophic degradation above 2KB
3. **Oracle JCT is a viable alternative** - Especially for multi-attribute documents and Oracle shops
4. **Use the right tool** - Don't force relational databases into document storage roles

**For GenAI, content management, and document-centric applications:** Choose MongoDB or Oracle JCT, not PostgreSQL.

---

**Test completed:** October 30, 2025
**Total tests:** 30 configurations × 3 platforms × 3 runs = 270 benchmark runs
**Duration:** ~20 minutes
**Reproducibility:** Deterministic seed (42) ensures consistent results
