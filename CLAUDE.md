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

Generate flame graphs to visualize CPU usage and identify performance bottlenecks:

```bash
# Setup async-profiler (one-time setup)
./setup_async_profiler.sh

# Run benchmarks with flame graph profiling
python3 run_article_benchmarks.py --queries --mongodb --oracle --flame-graph

# Flame graphs will be saved in flamegraphs/ directory
# Files are named: {database}_{test_type}_{size}B_{attrs}attrs_{timestamp}.html
```

**Flame Graph Features:**
- Uses async-profiler for low-overhead CPU profiling
- Generates interactive HTML flame graphs
- One flame graph per benchmark test
- Flame graphs show CPU time distribution across methods
- Hover over stack frames to see method names and percentages

**Output Examples:**
- `flamegraphs/mongodb_bson_insert_200B_10attrs_20250106_143022.html`
- `flamegraphs/oracle_jct_query_1000B_50attrs_20250106_143145.html`

**System Requirements:**
- async-profiler 3.0 (installed via setup_async_profiler.sh)
- Linux with perf_event support
- Root or perf_event_paranoid <= 1

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
python3 generate_benchmark_report.py

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
4. **Generate report** (`generate_benchmark_report.py`)
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
- Report generation: `generate_benchmark_report.py` for HTML visualization with charts
- For comprehensive benchmark testing procedures, see the **Common Test Procedures** section above