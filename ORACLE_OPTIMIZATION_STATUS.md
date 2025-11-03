# Oracle Database Optimization Status

This document shows the current state of Oracle Database 23ai Free Edition optimizations on this system, comparing actual settings against recommendations in ORACLE_OPTIMIZATIONS.md.

## Summary

**Database Edition**: Oracle 23ai Free Edition (2GB memory limit)
**Optimization Script**: `tune_oracle_free.sql`
**Status**: **NOT APPLIED** - Oracle is running with default configuration

All recommended optimizations are compatible with Free Edition and should be applied for optimal performance.

## Current Configuration vs Recommended

### 1. Memory Configuration

| Parameter | Current Value | Recommended (Free Edition) | Status | Impact |
|-----------|--------------|---------------------------|--------|--------|
| **memory_target** | 2147483648 (2GB) | N/A (disable for manual tuning) | DEFAULT | Using automatic memory management |
| **memory_max_target** | 2147483648 (2GB) | N/A (disable for manual tuning) | DEFAULT | Limits manual tuning |
| **sga_target** | 0 (auto) | 2000M (2GB) | NOT SET | Manual control provides better performance |
| **sga_max_size** | 0 (auto) | 2000M (2GB) | NOT SET | Required for manual SGA sizing |
| **pga_aggregate_target** | 0 (auto) | 2000M (2GB) | NOT SET | Larger PGA improves sort/hash operations |
| **db_cache_size** | 0 (auto) | 1200M (1.2GB) | NOT SET | More cache = less disk I/O |
| **shared_pool_size** | 0 (auto) | 600M | NOT SET | Larger pool = better JSON parsing |

**Free Edition Compatibility**: ✅ All memory settings compatible (respects 2GB SGA + 2GB PGA limits)

**Current Impact**: Oracle is using automatic memory management which is less optimal for JSON workloads. Manual tuning allocates more memory to buffer cache and shared pool where it's needed most.

### 2. Transaction Commit Optimizations

| Parameter | Current Value | Recommended | Status | Impact |
|-----------|--------------|-------------|--------|--------|
| **commit_logging** | (empty/default) | IMMEDIATE | NOT SET | Default has higher latency |
| **commit_wait** | (empty/default) | NOWAIT | NOT SET | Default waits for log sync |

**Free Edition Compatibility**: ✅ Compatible

**Current Impact**: Missing 30-50% improvement in commit latency. Bulk insert operations are slower than optimal.

### 3. Query Optimizer Settings

| Parameter | Current Value | Recommended | Status | Impact |
|-----------|--------------|-------------|--------|--------|
| **optimizer_index_cost_adj** | 100 (default) | 20 | NOT SET | Underutilizing indexes |
| **optimizer_index_caching** | 0 (default) | 90 | NOT SET | Not assuming cached indexes |
| **result_cache_mode** | MANUAL | MANUAL | ✅ CORRECT | Prevents benchmark skew |

**Free Edition Compatibility**: ✅ Compatible

**Current Impact**: Query optimizer is less aggressive about using indexes, leading to more full table scans and slower queries.

### 4. Parallel Operations

| Parameter | Current Value | Recommended | Status | Impact |
|-----------|--------------|-------------|--------|--------|
| **parallel_degree_policy** | MANUAL (default) | AUTO | NOT SET | Not auto-parallelizing |
| **parallel_min_time_threshold** | AUTO | 10 | NOT SET | Using default threshold |

**Free Edition Compatibility**: ✅ Compatible

**Current Impact**: Long-running operations not automatically parallelized across CPU cores.

### 5. Segment Management

| Parameter | Current Value | Recommended | Status | Impact |
|-----------|--------------|-------------|--------|--------|
| **deferred_segment_creation** | TRUE (default) | FALSE | NOT SET | Segments created on-demand |

**Free Edition Compatibility**: ✅ Compatible

**Current Impact**: Segments are created lazily on first row insert. This can cause extent allocation overhead during bulk inserts, particularly when tables grow rapidly. Setting to FALSE allocates segments immediately on CREATE TABLE, reducing fragmentation and improving bulk load performance.

## Application-Level Optimizations

These are implemented in the Java code and ARE being used:

| Optimization | Status | Notes |
|--------------|--------|-------|
| **OSON Binary Format** | ✅ ACTIVE | Implemented in OracleJCT.java |
| **Batch Processing** | ✅ ACTIVE | Configurable batch size (default 100, tested up to 1000) |
| **Multivalue Indexes** | ✅ ACTIVE | Available via `-mv` flag (7x faster than search indexes) |
| **Search Indexes** | ✅ ACTIVE | Default index type for array queries |
| **Per-Test DB Isolation** | ✅ ACTIVE | Python benchmark script restarts Oracle between tests |
| **MongoDB Parity (WriteConcern.JOURNALED)** | ✅ ACTIVE | Equivalent durability settings |

## Performance Impact of Missing Optimizations

Based on the actual benchmarks run with **DEFAULT** configuration, applying the database-level optimizations from `tune_oracle_free.sql` would likely provide:

### Expected Improvements After Applying tune_oracle_free.sql

| Workload Type | Current Performance | Expected After Tuning | Improvement |
|---------------|--------------------|-----------------------|-------------|
| **Bulk Inserts** | Baseline | +30-50% | Commit optimizations + better memory |
| **Query Performance** | Baseline | +20-40% | Better index usage + caching assumptions |
| **Buffer Cache Hit Ratio** | ~85-90% (auto) | >95% | Larger dedicated buffer cache |
| **Large Operations** | Serial | Parallel capable | Better multi-core utilization |

**Important Note**: All benchmark results in this repository were obtained with the DEFAULT Oracle configuration shown above. The performance numbers represent Oracle's out-of-box performance on Free Edition, not its optimized performance.

## How to Apply Optimizations

### Step 1: Apply Database Tuning

```bash
# Connect to the database as system user
sqlplus system/PASSWORD@localhost:1521/FREE @tune_oracle_free.sql

# Restart Oracle for SPFILE changes to take effect
sudo systemctl restart oracle-free-26ai
```

### Step 2: Verify Settings

```bash
# Start listener after Oracle starts
sudo -u oracle bash -c "
export ORACLE_HOME=/opt/oracle/product/26ai/dbhomeFree
export PATH=\$ORACLE_HOME/bin:\$PATH
lsnrctl start
"

# Check settings
sqlplus system/PASSWORD@localhost:1521/FREE <<EOF
SELECT name, value FROM v\$parameter
WHERE name IN ('sga_target', 'pga_aggregate_target', 'db_cache_size',
               'shared_pool_size', 'optimizer_index_cost_adj',
               'optimizer_index_caching', 'commit_logging', 'commit_wait')
ORDER BY name;
EXIT;
EOF
```

### Step 3: Re-run Benchmarks (Optional)

To see the performance improvement from database-level optimizations:

```bash
# Run with same settings as before but with optimized database
python3 run_article_benchmarks.py --mongodb --oracle --full-comparison --batch-size 1000
```

## Compatibility Notes

### Free Edition Limits

Oracle 23ai Free Edition has the following hard limits:
- Maximum 2GB SGA
- Maximum 2GB PGA
- Maximum 2 CPU threads for parallel operations
- Maximum 12GB user data

The `tune_oracle_free.sql` script respects all these limits:
- Sets SGA to 2000M (under 2GB limit)
- Sets PGA to 2000M (under 2GB limit)
- Parallel operations will automatically respect 2 CPU thread limit
- No storage limits affected

### Enterprise/Standard Edition

If you upgrade to Enterprise or Standard Edition (no memory limits), use `tune_oracle.sql` instead:
- 6GB SGA (vs 2GB Free)
- 2GB PGA (same as Free)
- 4GB buffer cache (vs 1.2GB Free)
- 1GB shared pool (vs 600MB Free)
- Unlimited parallel degree (vs 2 threads Free)

## Current Benchmark Results Context

**IMPORTANT**: All benchmark results documented in this repository (EXECUTIVE_SUMMARY.md, THREE_PLATFORM_COMPARISON.md, etc.) reflect Oracle's performance with the **DEFAULT** configuration shown above.

This means:
1. Oracle performed competitively with MongoDB BSON **without** database-level optimizations
2. Application-level optimizations (OSON, batching, multivalue indexes) were active
3. There is likely additional performance headroom available if tune_oracle_free.sql is applied
4. Fair comparison was maintained: both MongoDB and Oracle used out-of-box configurations

## Recommendations

### For Fair Benchmarking
If maintaining fair comparison with MongoDB defaults, keep current configuration documented.

### For Maximum Performance
Apply tune_oracle_free.sql to see Oracle's peak performance:
1. Better memory allocation for JSON workloads
2. Faster commits for bulk inserts
3. More aggressive index usage
4. Automatic parallel operations

### For Production Use
Always apply tune_oracle_free.sql (or tune_oracle.sql for paid editions):
1. 30-50% better insert performance
2. 20-40% better query performance
3. Better resource utilization
4. More predictable performance under load

## References

- Full optimization details: See ORACLE_OPTIMIZATIONS.md
- Free Edition limits: https://www.oracle.com/database/free/faq/
- Tuning guide: https://docs.oracle.com/en/database/oracle/oracle-database/23/tgdba/
