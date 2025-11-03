-- Oracle Performance Tuning for Benchmark Workload
-- Optimized for bulk inserts and JSON queries

-- ============================================================
-- 1. MEMORY SETTINGS (Increase from 2GB to 8GB total)
-- ============================================================
-- SGA: Shared Global Area for caching data/SQL
-- PGA: Program Global Area for sorting/hashing
ALTER SYSTEM SET sga_target=6G SCOPE=SPFILE;
ALTER SYSTEM SET sga_max_size=6G SCOPE=SPFILE;
ALTER SYSTEM SET pga_aggregate_target=2G SCOPE=SPFILE;

-- ============================================================
-- 2. BUFFER CACHE (More memory for data blocks)
-- ============================================================
-- Increase buffer cache for better data caching
ALTER SYSTEM SET db_cache_size=4G SCOPE=SPFILE;

-- ============================================================
-- 3. REDO LOG OPTIMIZATION (Faster commits)
-- ============================================================
-- Use immediate commit logging for better performance
ALTER SYSTEM SET commit_logging=IMMEDIATE SCOPE=BOTH;
-- Don't wait for log writes to complete
ALTER SYSTEM SET commit_wait=NOWAIT SCOPE=BOTH;

-- ============================================================
-- 4. OPTIMIZER SETTINGS (Better for indexes)
-- ============================================================
-- Favor index usage
ALTER SYSTEM SET optimizer_index_cost_adj=20 SCOPE=BOTH;
-- Assume 90% index caching
ALTER SYSTEM SET optimizer_index_caching=90 SCOPE=BOTH;

-- ============================================================
-- 5. I/O SETTINGS (Parallel operations)
-- ============================================================
-- Enable parallel DML
ALTER SESSION ENABLE PARALLEL DML;
-- Set default parallel degree
ALTER SYSTEM SET parallel_degree_policy=AUTO SCOPE=BOTH;
ALTER SYSTEM SET parallel_min_time_threshold=10 SCOPE=BOTH;

-- ============================================================
-- 6. JSON-SPECIFIC OPTIMIZATIONS
-- ============================================================
-- Increase shared pool for JSON operations
ALTER SYSTEM SET shared_pool_size=1G SCOPE=SPFILE;

-- ============================================================
-- 7. SESSION SETTINGS (Apply to current session)
-- ============================================================
-- Disable query result cache for benchmark accuracy
ALTER SYSTEM SET result_cache_mode=MANUAL SCOPE=BOTH;

-- Show current settings
SELECT 'Current Memory Settings:' as info FROM dual;
SELECT name, value FROM v$parameter 
WHERE name IN ('sga_target', 'pga_aggregate_target', 'db_cache_size', 'shared_pool_size')
ORDER BY name;

SELECT 'Current Optimizer Settings:' as info FROM dual;
SELECT name, value FROM v$parameter 
WHERE name IN ('optimizer_index_cost_adj', 'optimizer_index_caching', 'commit_logging', 'commit_wait')
ORDER BY name;

PROMPT
PROMPT ============================================================
PROMPT Tuning complete! Restart Oracle for SPFILE changes to take effect:
PROMPT   sudo systemctl restart oracle-free-26ai
PROMPT ============================================================
