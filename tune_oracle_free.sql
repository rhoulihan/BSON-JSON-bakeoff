-- Oracle FREE EDITION Performance Tuning
-- Respects Free Edition limits: SGA max 2GB, PGA max 2GB

-- ============================================================
-- 1. MEMORY SETTINGS (Oracle Free Edition Limits)
-- ============================================================
-- Maximum SGA for Free Edition = 2GB
ALTER SYSTEM SET sga_target=2000M SCOPE=SPFILE;
ALTER SYSTEM SET sga_max_size=2000M SCOPE=SPFILE;
-- Maximum PGA for Free Edition = 2GB 
ALTER SYSTEM SET pga_aggregate_target=2000M SCOPE=SPFILE;

-- ============================================================
-- 2. BUFFER CACHE  (within 2GB SGA limit)
-- ============================================================
ALTER SYSTEM SET db_cache_size=1200M SCOPE=SPFILE;
ALTER SYSTEM SET shared_pool_size=600M SCOPE=SPFILE;

-- ============================================================
-- 3. REDO LOG OPTIMIZATION (Faster commits)
-- ============================================================
ALTER SYSTEM SET commit_logging=IMMEDIATE SCOPE=BOTH;
ALTER SYSTEM SET commit_wait=NOWAIT SCOPE=BOTH;

-- ============================================================
-- 4. OPTIMIZER SETTINGS (Better for indexes)
-- ============================================================
ALTER SYSTEM SET optimizer_index_cost_adj=20 SCOPE=BOTH;
ALTER SYSTEM SET optimizer_index_caching=90 SCOPE=BOTH;

-- ============================================================
-- 5. PARALLEL OPERATIONS
-- ============================================================
ALTER SYSTEM SET parallel_degree_policy=AUTO SCOPE=BOTH;
ALTER SYSTEM SET parallel_min_time_threshold=10 SCOPE=BOTH;

-- ============================================================
-- 6. SESSION SETTINGS
-- ============================================================
ALTER SYSTEM SET result_cache_mode=MANUAL SCOPE=BOTH;

-- ============================================================
-- 7. SEGMENT MANAGEMENT (Better for growing tables)
-- ============================================================
-- Disable deferred segment creation for immediate space allocation
-- Benefits: Allocates space upfront, reduces extent allocation overhead during inserts
ALTER SYSTEM SET deferred_segment_creation=FALSE SCOPE=BOTH;

PROMPT ============================================================
PROMPT Oracle Free Edition Tuning Applied
PROMPT ============================================================
PROMPT Memory: SGA=2GB (max for Free), PGA=2GB (max for Free)
PROMPT Commits: IMMEDIATE/NOWAIT (faster for bulk operations)
PROMPT Indexes: Optimized (cost_adj=20, caching=90)
PROMPT Segments: Immediate creation (better for bulk loads)
PROMPT
PROMPT Restart required: sudo systemctl restart oracle-free-26ai
PROMPT ============================================================
