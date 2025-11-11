# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Java-based benchmarking tool that compares document storage and retrieval performance across MongoDB (BSON), PostgreSQL (JSON/JSONB), and Oracle 23AI (JSON Duality Views and JSON Collection Tables). Tests insertion speeds, query performance, and different payload/indexing strategies.

## Build and Run Commands

### Building
```bash
mvn clean package
```
Produces: `target/insertTest-1.0-jar-with-dependencies.jar`

### Running Benchmarks

Basic syntax:
```bash
java -jar target/insertTest-1.0-jar-with-dependencies.jar [OPTIONS] [numItems]
```

Common commands:
```bash
# MongoDB with default settings (10k docs, 100B and 1000B payloads)
java -jar target/insertTest-1.0-jar-with-dependencies.jar

# PostgreSQL with JSONB
java -jar target/insertTest-1.0-jar-with-dependencies.jar -p -j 20000

# Oracle JSON Collection Tables with query test
java -jar target/insertTest-1.0-jar-with-dependencies.jar -oj -q 10 -s 4000 -n 200

# Multiple runs for consistent benchmarking
java -jar target/insertTest-1.0-jar-with-dependencies.jar -r 3 -b 500 10000

# Using configuration file
java -jar target/insertTest-1.0-jar-with-dependencies.jar -c config.json
```

### Automated Report Generation

Generate comprehensive HTML report with benchmarks:
```bash
python3 generate_report.py
```
This runs MongoDB and Oracle JCT benchmarks (with/without search index) and creates `benchmark_report.html`.

### Unified Report Generation from Benchmark Logs

After running benchmarks with `--flame-graph` and `--server-profile` flags, you need to collate the test data and generate a unified HTML report.

**Overview:** This process converts benchmark logs into a comprehensive HTML report with interactive charts, flame graph visualizations (both client-side Java profiling and server-side database profiling), and performance comparisons. The report is packaged with all flame graphs into a self-contained zip file that can be shared and viewed on any system with a modern browser.

**Two-step process:**

#### Step 1: Parse Benchmark Logs into flamegraph_summaries.json

The `create_summaries_from_logs.py` script parses benchmark log files and creates `flamegraph_summaries.json`, which contains performance data for all tests.

```bash
python3 create_summaries_from_logs.py
```

**What it does:**
- Parses log files: `local_noindex.log`, `local_indexed.log`, `remote_noindex.log`, `remote_indexed.log`
- Detects database sections by finding `--- MongoDB (BSON) ---` and `--- Oracle JCT ---` headers
- Extracts both insertion and query performance data:
  - Insertion: `✓ {time}ms ({rate} docs/sec)`
  - Query: `✓ {time}ms ({rate} docs/sec) | Query: {time}ms ({rate} queries/sec)`
- Maps performance data to corresponding flame graph files in `flamegraphs/` directory
- Outputs: `flamegraph_summaries.json` in project root

**Expected output:**
```
Parsing local no-index log...
Parsing local indexed log...
Parsing remote no-index log...
Parsing remote indexed log...

Generated summaries:
  local_noindex: 10 tests
  local_indexed: 10 tests
  remote_noindex: 10 tests
  remote_indexed: 10 tests

✅ Saved flamegraph_summaries.json
   Total tests: 40 tests
```

**Important notes:**
- The script saves `flamegraph_summaries.json` to the project root (where `create_summaries_from_logs.py` is located)
- It automatically matches flame graph files using pattern: `{database}_{test_type}_{size}B_{attrs}attrs_{timestamp}.html`
- Database sections in logs must be properly formatted with `--- MongoDB (BSON) ---` and `--- Oracle JCT ---` headers

#### Step 2: Generate Unified HTML Report

The `generate_unified_report.py` script (located in `report/` directory) creates a comprehensive HTML report with interactive charts, flame graph links, and executive summary.

```bash
# Copy flamegraph_summaries.json to report/ directory
cp flamegraph_summaries.json report/

# Generate the report
cd report && python3 generate_unified_report.py
```

**What it does:**
- Loads `flamegraph_summaries.json` from the current directory
- Converts flame graph data to benchmark format for charts
- Generates query performance and insertion performance charts
- Creates unified flame graph table with both client-side and server-side columns
- Matches server flame graphs to client tests based on timestamp proximity
- Outputs:
  - `unified_benchmark_report.html` (standalone HTML report)
  - `benchmark_report_package.zip` (distributable archive with all flame graphs)

**Expected output:**
```
=== Unified Benchmark Report Generator ===

Step 1: Loading flame graph summaries...
Step 2: Converting flame graph data to benchmark format...
Step 3: Loading flame graph HTML sections...
Step 4: Generating unified HTML report...

✅ Unified report generated: unified_benchmark_report.html
   Open in browser: file:///path/to/unified_benchmark_report.html

Step 5: Creating distributable archive...
  Adding unified_benchmark_report.html...
  Adding 60 client-side flame graph files...
  Adding 55 server-side flame graph files...
  Adding README.txt...
  Archive created: benchmark_report_package.zip (2.47 MB)
```

#### Complete Workflow Example

```bash
# 1. Run benchmarks (both systems, with flame graphs and server profiling)
timeout 1800 python3 run_article_benchmarks.py --no-index --nostats --mongodb --oracle \
  --flame-graph --server-profile --monitor > local_noindex.log 2>&1 &

timeout 1800 python3 run_article_benchmarks.py --queries --nostats --mongodb --oracle \
  --flame-graph --server-profile --monitor > local_indexed.log 2>&1 &

ssh oci-opc "cd BSON-JSON-bakeoff && timeout 1800 python3 run_article_benchmarks.py \
  --no-index --nostats --mongodb --oracle --flame-graph --server-profile --monitor \
  > remote_noindex.log 2>&1 &"

ssh oci-opc "cd BSON-JSON-bakeoff && timeout 1800 python3 run_article_benchmarks.py \
  --queries --nostats --mongodb --oracle --flame-graph --server-profile --monitor \
  > remote_indexed.log 2>&1 &"

# 2. Wait for completion, then copy remote logs to local system
scp oci-opc:BSON-JSON-bakeoff/remote_noindex.log ./
scp oci-opc:BSON-JSON-bakeoff/remote_indexed.log ./

# 3. Parse logs to create flamegraph_summaries.json
python3 create_summaries_from_logs.py

# 4. Generate unified report
cp flamegraph_summaries.json report/
cd report && python3 generate_unified_report.py

# 5. View the report
cd .. && firefox unified_benchmark_report.html
```

#### Troubleshooting

**Problem:** MongoDB and Oracle showing identical data in tables/charts

**Cause:** The log parser uses test descriptions as dictionary keys, but both databases have the same descriptions (e.g., "10B single attribute"). The parser must track which database section it's in.

**Solution:** The current `create_summaries_from_logs.py` correctly tracks database sections by detecting headers. If you modify the parser, ensure it:
1. Detects `--- MongoDB (BSON) ---` and `--- Oracle JCT ---` section headers
2. Returns separate dictionaries: `{'mongodb': {...}, 'oracle': {...}}`
3. Passes the correct database data when mapping to flame graphs

**Problem:** No query performance data in charts

**Cause:** The parser only matches insertion results, not query results.

**Solution:** The parser must try to match both patterns:
1. First: `✓ {time}ms ({rate} docs/sec) | Query: {time}ms ({rate} queries/sec)`
2. Fallback: `✓ {time}ms ({rate} docs/sec)`

**Problem:** Report generator can't find flamegraph_summaries.json

**Cause:** The file is in project root, but `generate_unified_report.py` expects it in `report/` directory.

**Solution:** Copy the file: `cp flamegraph_summaries.json report/`

**Problem:** Flame graph links broken in distributable package (benchmark_report_package.zip)

**Cause:** The HTML report was added to the zip with its full absolute path instead of just the filename, breaking relative paths to flame graph files.

**Solution:** The fix is already in `report/generate_unified_report.py` (line 572-575). The report generator now uses `Path(report_file).name` to extract just the filename before adding to the zip. If you see this issue, regenerate the report package:
```bash
cd report && python3 generate_unified_report.py
```

**Verify the fix:** Extract the zip and check structure:
```bash
unzip -l benchmark_report_package.zip | head -10
# Should show: unified_benchmark_report.html at zip root (not nested in directories)
#              flamegraphs/ directory with HTML files
#              server_flamegraphs/ directory with SVG files
```

#### Distributable Package Structure

When you extract `benchmark_report_package.zip`, you get a self-contained package:

```
extracted_folder/
├── unified_benchmark_report.html    # Main report (open this in browser)
├── flamegraphs/                     # 60+ client-side flame graphs (HTML)
│   ├── mongodb_bson_query_10B_1attrs_20251107_090420.html
│   └── ...
├── server_flamegraphs/              # 55+ server-side flame graphs (SVG)
│   ├── mongodb_server_20251107_090418.svg
│   └── ...
└── README.txt                       # Instructions for viewing
```

All flame graph links use relative paths (`flamegraphs/...` and `server_flamegraphs/...`), so the package works on any system with a modern browser.

#### File Locations Reference

```
BSON-JSON-bakeoff/
├── create_summaries_from_logs.py       # Parser script (project root)
├── flamegraph_summaries.json           # Generated by parser (project root)
├── local_noindex.log                   # Benchmark log
├── local_indexed.log                   # Benchmark log
├── remote_noindex.log                  # Benchmark log (copied from remote)
├── remote_indexed.log                  # Benchmark log (copied from remote)
├── unified_benchmark_report.html       # Generated report (project root)
├── benchmark_report_package.zip        # Distributable archive
├── flamegraphs/                        # Client-side flame graphs (HTML)
│   ├── mongodb_bson_insert_10B_1attrs_20251107_085520.html
│   ├── oracle_jct_query_200B_1attrs_20251107_090541.html
│   └── ...
├── server_flamegraphs/                 # Server-side flame graphs (SVG)
│   ├── mongodb_server_20251107_085646.svg
│   ├── oracle_server_20251107_085736.svg
│   └── ...
└── report/
    ├── generate_unified_report.py      # Report generator
    ├── flamegraph_summaries.json       # Copy of summaries (needed here)
    ├── flamegraph_report_helper.py     # Helper for flame graph sections
    └── report_modules/
        ├── benchmark_formatter.py      # Table formatting
        ├── chart_generator.py          # SVG chart generation
        ├── executive_summary.py        # Summary generation
        └── flamegraph_to_benchmark_converter.py  # Data conversion
```

### System Resource Monitoring

Enable system resource monitoring during benchmarks:
```bash
# Run with resource monitoring (CPU, disk, network every 5 seconds)
python3 run_article_benchmarks.py --queries --mongodb --oracle --monitor

# Custom monitoring interval
python3 run_article_benchmarks.py --queries --mongodb --oracle --monitor --monitor-interval 3

# Standalone monitoring (for custom scenarios)
python3 monitor_resources.py --interval 5 --output metrics.json
```

See `MONITORING_README.md` for detailed documentation on resource monitoring features, output format, and analysis examples.

### Flame Graph Profiling

Generate flame graphs to visualize CPU usage and identify performance bottlenecks. The suite supports both **client-side** and **server-side** profiling:

#### Client-Side Profiling (Java Application)

```bash
# Setup async-profiler (one-time setup)
./setup_async_profiler.sh

# Run benchmarks with client-side flame graph profiling
python3 run_article_benchmarks.py --queries --mongodb --oracle --flame-graph

# Flame graphs saved in flamegraphs/ directory
# Files: {database}_{test_type}_{size}B_{attrs}attrs_{timestamp}.html
```

**Client-Side Features:**
- Profiles Java client application (JDBC, JSON serialization, networking)
- Uses async-profiler for low-overhead CPU profiling (~1% overhead)
- Generates interactive HTML flame graphs
- Output: `flamegraphs/mongodb_bson_insert_200B_10attrs_20250106_143022.html`

**Requirements:**
- async-profiler 3.0 (installed via setup_async_profiler.sh)
- Linux with perf_event support

#### Server-Side Profiling (Database Processes)

```bash
# One-time setup: Install perf and Perl modules
sudo yum install -y perf perl-open

# Clone FlameGraph tools (if not already done)
git clone https://github.com/brendangregg/FlameGraph

# Run benchmarks with server-side profiling
python3 run_article_benchmarks.py --queries --mongodb --oracle --server-profile

# Or profile both client and server simultaneously
python3 run_article_benchmarks.py --queries --mongodb --oracle \
  --flame-graph --server-profile

# Standalone server profiling (10 seconds)
python3 profile_server.py mongodb --duration 10
python3 profile_server.py oracle --duration 10
```

**Server-Side Features:**
- Profiles database server processes (mongod, Oracle)
- Uses Linux perf for sampling-based profiling (~1-2% overhead)
- Generates interactive SVG flame graphs
- Output: `server_flamegraphs/mongodb_server_20251106_171925.svg`

**Requirements:**
- Linux perf tool (`sudo yum install perf`)
- Perl modules (`sudo yum install perl-open`)
- FlameGraph tools (https://github.com/brendangregg/FlameGraph)
- Sudo privileges (perf requires root to attach to processes)

**When to Use Each:**
- **Client-side**: Analyze JDBC driver, JSON serialization, network I/O overhead
- **Server-side**: Analyze storage engine, query execution, index operations
- **Both**: Get complete end-to-end performance picture

See `SERVER_PROFILING_README.md` for detailed server profiling documentation, troubleshooting, and analysis techniques.

### Docker-based Testing

Test multiple databases automatically:
```bash
sh test.sh [OPTIONS]
```
Sequentially tests MongoDB, PostgreSQL, YugabyteDB, and CockroachDB using Docker containers.

## Architecture

### Core Design Pattern

The codebase uses the **Strategy pattern** with `DatabaseOperations` interface defining common operations, allowing easy addition of new database backends:

- **Interface**: `DatabaseOperations` (6 methods)
- **Implementations**: `MongoDBOperations`, `PostgreSQLOperations`, `Oracle23AIOperations`, `OracleJCT`
- **Main coordinator**: `Main.java` handles argument parsing, document generation, and orchestration

### Key Components

**Main.java**:
- Entry point with command-line argument parsing
- Document generation with configurable payloads (split across N attributes or single attribute)
- Benchmark orchestration (insertion, querying with multikey indexes, $lookup operations)
- Configuration file support (JSON)

**DatabaseOperations interface**:
```java
void initializeDatabase(String connectionString);
void dropAndCreateCollections(List<String> collectionNames);
long insertDocuments(String collectionName, List<JSONObject> documents, int dataSize, boolean splitPayload);
int queryDocumentsById(String collectionName, String id);
int queryDocumentsByIdWithInCondition(String collectionName, JSONObject document);
int queryDocumentsByIdUsingLookup(String collectionName, String id);
void close();
```

**Database-specific implementations**:
- **MongoDBOperations**: Uses native BSON, multikey indexes, $in queries, $lookup aggregations
- **PostgreSQLOperations**: JSON/JSONB columns, GIN indexes, array containment operators
- **Oracle23AIOperations**: JSON Duality Views with bidirectional relational/document mapping (⚠️ has array insertion bug in Oracle 23AI Free, use `-d` flag for direct table insertion workaround)
- **OracleJCT**: Native JSON Collection Tables with OSON binary format, JSON path queries, search indexes, multivalue indexes

### Configuration Management

**Database connections**: `config.properties` (git-ignored, copy from `config.properties.example`)
```properties
mongodb.connection.string=mongodb://localhost:27017
postgresql.connection.string=jdbc:postgresql://localhost:5432/test?user=postgres&password=PASSWORD
oracle.connection.string=jdbc:oracle:thin:system/PASSWORD@localhost:1521/FREEPDB1
```

**Test configurations**: JSON files (e.g., `config.example.json`) with parameters like database type, numDocs, payload sizes, batch size, etc.

### Document Generation Strategy

Documents are generated in `Main.java` with:
- Deterministic random seed (42) for reproducible results
- Configurable payload sizes (default: 100B, 1000B)
- Payload distribution: single large attribute OR split across N attributes
- Array fields (`indexArray`) with configurable number of links for query testing
- All implementations use identical document generation for fair comparison

### Oracle 23AI Special Considerations

**JSON Duality Views** (`-o` flag):
- Creates normalized relational tables + JSON views providing unified access
- ⚠️ **Known bug in Oracle 23AI Free (23.0.0.0.0)**: Array values are incorrectly treated as globally unique during insertion through Duality Views, causing silent data loss
- **Workaround**: Use `-d` flag for direct table insertion (bypasses Duality View)
- Uses OSON (Oracle Binary JSON) format via `OracleJsonFactory` for efficient binary JSON creation

**JSON Collection Tables** (`-oj` flag):
- Simpler approach: direct JSON document storage (no relational mapping)
- Uses OSON binary format for storage efficiency
- **Two index types available for array queries:**
  - **Search index** (default): `CREATE SEARCH INDEX` - Full-text index for JSON documents
  - **Multivalue index** (with `-mv` flag): `CREATE MULTIVALUE INDEX idx ON table (data.array[*].string())` - Direct array element indexing (7x FASTER than search index)
- JSON path expressions for queries (`JSON_EXISTS`, `JSON_VALUE`)
- More MongoDB-like semantics in Oracle
- **Performance note**: Multivalue indexes with explicit `[*].string()` syntax significantly outperform search indexes for array containment queries (4,110 vs 572 queries/sec)
- **Syntax requirements**: Multivalue index requires `[*].string()` in index creation and `JSON_EXISTS(data, '$.array?(@ == $val)' PASSING ? AS "val")` for queries

## Test Patterns

### Insertion Tests
- Single attribute vs multi-attribute payload distribution
- Batch insertion with configurable batch sizes
- Indexed vs non-indexed collections (`-i` flag)
- Multiple runs (`-r N`) to eliminate outliers and report best time

### Query Tests
- **Multikey index queries** (`-q N`): Query documents by array element values, with N links per document
- **$in condition queries** (`-i` with `-q`): Use $in operator for bulk queries
- **$lookup tests** (`-l N`): MongoDB aggregation pipeline joins

## Important Command-Line Flags

- `-p`: Use PostgreSQL instead of MongoDB
- `-o`: Use Oracle JSON Duality Views
- `-oj`: Use Oracle JSON Collection Tables (simpler than Duality Views)
- `-d`: Direct table insertion for Oracle (bypasses Duality View bug)
- `-j`: Use JSONB instead of JSON (PostgreSQL only)
- `-i`: Run indexed vs non-indexed comparison, OR enable $in condition for queries
- `-mv`: Use multivalue index instead of search index (Oracle JCT only, requires `-i` flag, 7x faster than search index for array queries)
- `-rd`: Use realistic nested data structures for multi-attribute tests instead of flat binary payloads
  * Generates nested subdocuments up to 5 levels deep
  * Random mix of strings, integers, decimals, binary data (up to 50 bytes), 3-4 item arrays, booleans
  * Document sizes approximate target size specified by `-s` parameter
  * Only affects multi-attribute tests; single-attribute tests remain unchanged (binary blob)
- `-q N`: Run query test with N array elements per document
- `-l N`: Run $lookup test with N links
- `-r N`: Run each test N times, report best result
- `-c FILE`: Load configuration from JSON file
- `-s SIZES`: Comma-delimited payload sizes (e.g., `-s 100,1000,5000`)
- `-n N`: Number of attributes to split payload across (affects realistic data structure complexity when using `-rd`)
- `-b N`: Batch size for bulk insertions

## Common Test Procedures

### Remote System Access

The project uses a remote OCI cloud system for comparison testing:
- **Remote hostname**: `oci-opc` (configured in SSH config)
- **Remote project path**: `BSON-JSON-bakeoff`
- **SSH command**: `ssh oci-opc`

### Running Benchmarks on Both Systems

The standard procedure for comprehensive benchmarks involves running tests in parallel on both local and remote systems:

#### Article Benchmark (Standard Test Suite)

Run indexed benchmarks with queries on both systems:

```bash
# Local system (background process with 30-minute timeout)
timeout 1800 python3 run_article_benchmarks.py --queries --mongodb --oracle --monitor > local_benchmark.log 2>&1 &

# Remote system (background process with 30-minute timeout)
ssh oci-opc "cd BSON-JSON-bakeoff && timeout 1800 python3 run_article_benchmarks.py --queries --mongodb --oracle --monitor > remote_benchmark.log 2>&1 &"
```

#### No-Index Benchmarks (Insertion-Only Performance)

Test pure insertion performance without indexes:

```bash
# Local system
timeout 1800 python3 run_article_benchmarks.py --no-index --nostats --mongodb --oracle --monitor > local_noindex_nostats.log 2>&1 &

# Remote system
ssh oci-opc "cd BSON-JSON-bakeoff && timeout 1800 python3 run_article_benchmarks.py --no-index --nostats --mongodb --oracle --monitor > remote_noindex_nostats.log 2>&1 &"
```

#### Indexed Benchmarks with Statistics Analysis

Test with Oracle statistics gathering enabled/disabled:

```bash
# WITH --nostats flag (statistics disabled)
timeout 1800 python3 run_article_benchmarks.py --queries --mongodb --oracle --nostats --monitor > local_indexed_nostats.log 2>&1 &
ssh oci-opc "cd BSON-JSON-bakeoff && timeout 1800 python3 run_article_benchmarks.py --queries --mongodb --oracle --nostats --monitor > remote_indexed_nostats.log 2>&1 &"

# WITHOUT --nostats flag (statistics enabled, Oracle default behavior)
timeout 1800 python3 run_article_benchmarks.py --queries --oracle --monitor > local_oracle_with_stats.log 2>&1 &
ssh oci-opc "cd BSON-JSON-bakeoff && timeout 1800 python3 run_article_benchmarks.py --queries --oracle --monitor > remote_oracle_with_stats.log 2>&1 &"
```

### Monitoring Running Benchmarks

Check progress of background benchmarks:

```bash
# Local system - tail the log file
tail -f local_benchmark.log

# Remote system - SSH and tail the log file
ssh oci-opc "tail -f BSON-JSON-bakeoff/remote_benchmark.log"

# Check if processes are still running
ps aux | grep run_article_benchmarks
ssh oci-opc "ps aux | grep run_article_benchmarks"
```

### Collecting Results from Remote System

After benchmarks complete, copy JSON results and logs from remote system:

```bash
# Copy result JSON files
scp oci-opc:BSON-JSON-bakeoff/tmp/remote_indexed_nostats_results.json /tmp/
scp oci-opc:BSON-JSON-bakeoff/tmp/remote_noindex_nostats_results.json /tmp/

# Copy log files
scp oci-opc:BSON-JSON-bakeoff/remote_benchmark.log ./
scp oci-opc:BSON-JSON-bakeoff/remote_indexed_nostats.log ./
scp oci-opc:BSON-JSON-bakeoff/remote_noindex_nostats.log ./

# Verify files copied successfully
ls -lh /tmp/*_results.json
ls -lh *remote*.log
```

### Generating Reports from Benchmark Data

Generate comprehensive HTML reports with charts:

```bash
# Generate report from collected data

# View the report
firefox benchmark_report.html
# or
open benchmark_report.html
```

The report generation script automatically:
1. Loads local results from `/tmp/local_*_results.json`
2. Fetches remote results via SCP from `oci-opc:BSON-JSON-bakeoff/tmp/remote_*_results.json`
3. Generates `benchmark_report.html` with nested tabs:
   - Cover Page (executive summary)
   - Local System → Indexed / No Index subtabs
   - Remote System → Indexed / No Index subtabs

### Common Result File Locations

**Local System:**
- Results: `/tmp/local_indexed_nostats_results.json`, `/tmp/local_noindex_nostats_results.json`
- Logs: `local_benchmark.log`, `local_indexed_nostats.log`, `local_noindex_nostats.log`
- System info: `/tmp/local_system_info.json`

**Remote System:**
- Results: `oci-opc:BSON-JSON-bakeoff/tmp/remote_indexed_nostats_results.json`, `remote_noindex_nostats_results.json`
- Logs: `oci-opc:BSON-JSON-bakeoff/remote_benchmark.log`, `remote_indexed_nostats.log`, `remote_noindex_nostats.log`
- System info: `oci-opc:BSON-JSON-bakeoff/tmp/remote_system_info.json`

### Standard Benchmark Configurations

Common flag combinations for different test scenarios:

| Scenario | Flags | Purpose |
|----------|-------|---------|
| **Full comparison** | `--queries --mongodb --oracle --monitor` | Indexed insertion + queries with monitoring |
| **Insertion only** | `--no-index --mongodb --oracle --monitor` | Pure insertion without indexes |
| **Without stats** | `--queries --mongodb --oracle --nostats --monitor` | Test Oracle performance without statistics gathering overhead |
| **MongoDB only** | `--queries --mongodb --monitor` | Test only MongoDB (useful for baselines) |
| **Oracle only** | `--queries --oracle --monitor --nostats` | Test only Oracle JCT |
| **Custom docs/runs** | `--queries --mongodb --oracle --num-docs 5000 --num-runs 5` | Customize document count and run count |

### Automated Test Execution Pattern

The standard workflow for comprehensive testing:

1. **Start benchmarks in parallel** (both local and remote, background mode)
2. **Monitor progress every 60 seconds** until completion (check log files)
3. **Collect results** (SCP from remote system)
5. **Analyze results** (compare MongoDB vs Oracle performance across systems)

**Note**: Whenever I say "Run the article benchmark", execute the article benchmark scripts on both the local and the remote system with a 30-minute timeout, monitor and report progress on both systems every 60 seconds until complete, then analyze the results and generate a detailed summary of the data comparing MongoDB to Oracle performance on both systems.

## Development Notes

### Adding New Database Support

1. Create class implementing `DatabaseOperations` interface
2. Add command-line flag in `Main.java` (around line 46-89)
3. Add connection string to `config.properties.example`
4. Implement all interface methods matching the semantics of existing implementations
5. See `Oracle23AIOperations.java` for a complete reference implementation

### Performance Optimization Context

- **Batch size**: Larger batches improve throughput but consume more memory (default: 100)
- **OSON format**: Oracle implementations use binary JSON (`OracleJsonFactory`) to eliminate text parsing overhead
- **Indexing**: B-tree indexes on normalized columns (Oracle Duality Views) or search indexes (Oracle JCT)
- **Multiple runs**: JVM warmup and system load can affect results; `-r 3` provides more consistent measurements

### Testing and Validation

- Test case for Oracle Duality View bug: `src/test/java/com/mongodb/TestDualityView.java`
- Automated cross-database testing: `test.sh` script with Docker
- For comprehensive benchmark testing procedures, see the **Common Test Procedures** section above