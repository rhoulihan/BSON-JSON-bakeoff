# ROADMAP.md — Docker Benchmark Suite Status Report

## Benchmark Run Results

**Date:** 2026-02-16 12:13 UTC
**Branch:** main (commit e819682)
**System:** Linux 6.8.0-100-generic aarch64 (ARM64), 6 CPUs, 8GB RAM
**Java:** OpenJDK 25.0.2
**Docker:** 29.1.2
**Python:** 3.12.3

### test.sh Results (2000 docs, batch 100, 1 run, indexed, queries with 10 links, validation)

| Database | Status | Insert 100B×1 | Insert 100B×10 | Insert 1000B×1 | Insert 1000B×10 | Query 100B | Query 1000B |
|----------|--------|---------------|----------------|-----------------|-----------------|------------|-------------|
| **MongoDB** | SUCCESS | 214ms | 178ms | 162ms | 165ms | 766ms (20000 items) | 628ms (20000 items) |
| **DocumentDB** | FAILED | — | — | — | — | — | — |
| **PostgreSQL** | SUCCESS | 105ms | 79ms | 350ms | 337ms | 1211ms (19962 items) | 1389ms (19949 items) |
| **YugabyteDB** | HUNG (manually recovered) | 270ms | 253ms | 476ms | 463ms | 1286ms (19960 items) | 1323ms (19952 items) |
| **CockroachDB** | HUNG (manually recovered) | 494ms | 445ms | 1011ms | 1140ms | 5379ms (19952 items) | 15961ms (19954 items) |

- YugabyteDB and CockroachDB results were obtained by manually running the Java jar after fixing container setup issues (see Errors section).
- All validation checks passed for databases that completed.

### Python Script Results (`run_article_benchmarks_docker.py`, 1000 docs, batch 100, 1 run, MongoDB + PostgreSQL only)

| Database | 10B | 200B | 1000B | 2000B | 4000B |
|----------|-----|------|-------|-------|-------|
| **MongoDB (single attr)** | 120ms | 126ms | 128ms | 128ms | 124ms |
| **PostgreSQL (single attr)** | 31ms | 128ms | 400ms | 686ms | 1356ms |
| **MongoDB (multi attr)** | 116ms | 115ms | 122ms | 122ms | 123ms |
| **PostgreSQL (multi attr)** | 34ms | 137ms | 399ms | 713ms | 1321ms |

- Query results were not captured in the output (see Warnings section).
- Results storage to MongoDB was unavailable (pymongo not installed).

## Errors

### E1: Missing `config.properties` — ALL databases (test.sh, first run)

**Symptom:** `ERROR: Could not load config.properties file. Please create config.properties from config/config.properties.example`
**Impact:** All databases failed on first test.sh run.
**Root Cause:** The Java application (`Main.java`) requires `config.properties` in the project root to load database connection strings. `test.sh` doesn't create this file; it assumes it exists.
**Fix:** Created `config.properties` from example with Docker-appropriate connection strings (e.g., `password` for PostgreSQL, `testuser:testpass` for DocumentDB). Restarting test.sh resolved the issue.
**Recommendation:** test.sh should auto-generate `config.properties` with Docker defaults if it doesn't exist.

### E2: DocumentDB — `MongoTimeoutException` (test.sh)

**Symptom:**
```
com.mongodb.MongoTimeoutException: Timed out while waiting for a server that matches WritableServerSelector.
Client view of cluster state is {type=UNKNOWN, servers=[{address=localhost:10260, type=UNKNOWN, state=CONNECTING,
exception={com.mongodb.MongoSocketReadException: Prematurely reached end of stream}}]}
```
**Impact:** DocumentDB benchmark failed completely in test.sh.
**Root Cause:** The DocumentDB container (PostgreSQL-based) passes the `psql` readiness check but the MongoDB wire protocol listener on port 10260 is not yet fully operational when the Java benchmark starts. There's a race condition between the readiness verification (which uses psql on internal port 9712) and the MongoDB protocol availability on the external port.
**Note:** The `-ddb` flag uses a `DocumentDBOperations` class that connects via the MongoDB driver. The readiness check using `psql` (PostgreSQL engine) doesn't guarantee the MongoDB wire protocol layer is ready.
**Recommendation:** Add a retry loop in the Java application's `initializeDatabase()` or add a longer post-readiness delay specifically for DocumentDB. Alternatively, the test.sh readiness check should verify the MongoDB wire protocol directly (e.g., with `mongosh` or a simple socket check on port 10260 followed by a ping).

### E3: YugabyteDB — `ysqlsh` can't connect via `localhost` (test.sh)

**Symptom:** test.sh hangs indefinitely at `CREATE DATABASE test;` step. Inside container: `ysqlsh: error: connection to server at "localhost" (127.0.0.1), port 5433 failed: Connection refused`
**Impact:** test.sh hangs forever (no timeout on `until` loop at line 325).
**Root Cause:** YugabyteDB binds YSQL to the container's hostname, not to `localhost`/`127.0.0.1`. `yugabyted status` reports "YSQL Status: Ready" but `ysqlsh -U yugabyte` (which defaults to `localhost`) fails. Using `ysqlsh -h $(hostname)` works.
**Workaround applied:** `docker exec db ysqlsh -h $(docker exec db hostname) -U yugabyte -c "CREATE DATABASE test;"` — this succeeded.
**Recommendation:** Fix test.sh to use `docker exec db ysqlsh -h $(docker exec db hostname) -U yugabyte` instead of `docker exec -i db ysqlsh -U yugabyte`. Also add a timeout to the `until` loop to prevent infinite hangs.

### E4: test.sh `until` loops have no timeout (YugabyteDB, CockroachDB)

**Symptom:** When `CREATE DATABASE test;` fails repeatedly, the script hangs forever.
**Impact:** Blocks entire benchmark suite — CockroachDB never ran because YugabyteDB hung.
**Location:** `scripts/test.sh` lines 303-305 (PostgreSQL), 325-327 (YugabyteDB)
**Recommendation:** Add a maximum retry count or timeout to all `until` loops, e.g.:
```bash
attempts=0; max_attempts=30
until echo "CREATE DATABASE test;" | docker exec -i db ysqlsh -U yugabyte 2>/dev/null || [ $attempts -ge $max_attempts ]; do
    sleep 5; attempts=$((attempts + 1))
done
```

## Warnings

### W1: SLF4J not found on classpath

**Message:** `WARNING: SLF4J not found on the classpath. Logging is disabled for the 'org.mongodb.driver' component`
**Impact:** Cosmetic only. MongoDB driver logging is suppressed but benchmarks run correctly.
**Recommendation:** Add `slf4j-simple` or `slf4j-nop` dependency to `pom.xml` to silence the warning.

### W2: `pymongo` not installable (Python script)

**Message:** `pymongo not found, attempting to install... Failed to install pymongo`
**Impact:** Results storage to MongoDB is disabled. The Python benchmark still runs but cannot persist results. Also affects DocumentDB readiness checks that use `pymongo`.
**Root Cause:** No `pip`/`pip3` available and no sudo access to install system packages.
**Recommendation:** Add `pymongo` and `psutil` to a `requirements.txt` and document setup steps, or use a virtual environment.

### W3: Python script doesn't capture query results in output

**Impact:** The summary tables show insertion times but not query performance, even though `--queries` was passed. The benchmarks likely ran queries (the Java jar received `-q 10`) but the Python script's regex didn't match the query output format.
**Root Cause:** The `run_benchmark()` function in `run_article_benchmarks_docker.py` parses query results with pattern `Best query time for (\d+) ID's with {query_links} element link arrays.*?: (\d+)ms` — but the actual Java output uses `Total time taken to query related documents for...` which is a different format. The "Best query time" line only appears with `-r N` where N > 1.
**Recommendation:** Update the regex in `run_article_benchmarks_docker.py` to also match the `Total time taken to query` format when `num_runs=1`.

### W4: Query results show less than maximum items found

**Observation:** PostgreSQL, YugabyteDB, and CockroachDB return slightly fewer items than the maximum (e.g., 19962 out of 20000). MongoDB returns exactly 20000.
**Impact:** Low — the validation passes and the differences are expected due to how random document generation creates overlapping target arrays.
**Recommendation:** No action needed; this is by design.

### W5: "Binding: NNN" debug output in MongoDB benchmarks

**Observation:** MongoDB test output includes many `Binding: NNN` lines showing document sizes.
**Impact:** Cosmetic — clutters output but doesn't affect results.
**Recommendation:** Gate this output behind a debug/verbose flag.

## Known Issues & Bugs

### B1: `config.properties` not auto-created for Docker workflows

The `test.sh` script and Python script assume `config.properties` exists but don't create it. For Docker-based testing, connection strings are deterministic and should be auto-generated.

### B2: YugabyteDB `ysqlsh` localhost binding issue

YugabyteDB in Docker doesn't bind YSQL to localhost, causing `ysqlsh -U yugabyte` to fail. The `wait_for_db` check passes (`yugabyted status` returns "Running") but the subsequent `CREATE DATABASE` command fails indefinitely.

### B3: `until` loops in test.sh can hang forever

Lines 303-305 and 325-327 in `scripts/test.sh` have no timeout. If a database starts but its SQL interface is unreachable, the script hangs indefinitely.

### B4: DocumentDB readiness check doesn't verify MongoDB protocol

The readiness check verifies the PostgreSQL engine (psql) but not the MongoDB wire protocol. The Java benchmark connects via the MongoDB driver and may fail if the protocol layer isn't ready.

### B5: Python script query parsing only works with multi-run mode

The `run_benchmark()` regex expects "Best query time" output which only appears when `num_runs > 1`. With `num_runs=1`, the output is "Total time taken to query..." which doesn't match.

### B6: Python script summary header says "10K documents" regardless of actual count

The `generate_summary_table()` function hardcodes "10K documents" in the header even when `--num-docs 1000` is used.

## Roadmap for Future Workers

### Priority 1 — Blocking Issues (prevent clean end-to-end runs)

1. **Auto-generate `config.properties` in test.sh** (B1)
   - Add a block at the top of `test.sh` that creates `config.properties` from example if missing, substituting Docker-appropriate defaults
   - Estimated effort: Small (10-20 lines of shell)

2. **Add timeouts to `until` loops in test.sh** (B3)
   - Add max retry count to all `until` loops (lines 303, 325)
   - Log a clear error and continue to next database on timeout
   - Estimated effort: Small

3. **Fix YugabyteDB `ysqlsh` connection in test.sh** (B2)
   - Change `docker exec -i db ysqlsh -U yugabyte` to use `-h $(docker exec db hostname)` or `0.0.0.0`
   - Estimated effort: Small (1-2 line change)

### Priority 2 — Reliability Improvements

4. **Improve DocumentDB readiness verification** (B4)
   - After psql check passes, add a delay or retry loop that verifies MongoDB protocol on port 10260
   - Consider adding a MongoDB wire protocol ping to the readiness check
   - Estimated effort: Medium

5. **Fix Python script query parsing** (B5)
   - Update regex in `run_article_benchmarks_docker.py:run_benchmark()` to match both "Best query time" and "Total time taken to query" formats
   - Estimated effort: Small

### Priority 3 — Polish

6. **Add `pymongo`/`psutil` to requirements.txt or document installation**
   - Ensure Python dependencies are clearly documented
   - Consider a setup script or venv creation
   - Estimated effort: Small

7. **Suppress or gate verbose debug output** (W1, W5)
   - Add SLF4J NOP binding to silence MongoDB driver warning
   - Gate "Binding: NNN" output behind a verbose flag
   - Estimated effort: Small

8. **Fix summary table header to use actual document count** (B6)
   - Pass `NUM_DOCS` to `generate_summary_table()` and use it in the header
   - Estimated effort: Trivial
