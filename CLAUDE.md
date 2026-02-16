# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Java-based benchmarking tool that compares document storage and retrieval performance across multiple databases using Docker containers. Tests insertion speeds, query performance, and different payload/indexing strategies. Results are stored in an external MongoDB instance and visualized through a Node.js webapp dashboard.

### Key Architecture

1. **Java benchmark engine** - Core insertion/query tests with configurable payloads
2. **Docker-based test execution** - Each database runs in its own container for isolation
3. **External MongoDB results storage** - All benchmark results are posted to a central MongoDB instance
4. **Node.js/Express webapp** - Dashboard for visualizing and comparing results
5. **Data validation** - Post-test verification that data was written and read back correctly

## Supported Databases

| Database | Docker Image | Driver | Flag |
|----------|-------------|--------|------|
| MongoDB (BSON) | `mongo` | mongodb-driver-sync 5.5.1 | (default) |
| DocumentDB | `documentdb-local` | mongodb-driver-sync 5.5.1 | `-ddb` |
| PostgreSQL (JSON/JSONB) | `postgres:latest` | postgresql 42.7.3 | `-p` |
| YugabyteDB (YSQL) | `yugabytedb/yugabyte:latest` | postgresql 42.7.3 | `-p` |
| CockroachDB (SQL) | `cockroachdb/cockroach:latest` | postgresql 42.7.3 | `-p` |
| Oracle 23AI (Duality Views) | N/A (native install) | ojdbc11 23.4.0 | `-o` |
| Oracle 23AI (JCT) | N/A (native install) | ojdbc11 23.4.0 | `-oj` |

## Build and Run Commands

### Building
```bash
mvn clean package
```
Produces: `target/insertTest-1.0-jar-with-dependencies.jar`

### Quick Start: Docker-based Testing (Recommended)

Run the shell script to test all Docker-based databases sequentially:
```bash
sh scripts/test.sh [JAVA_FLAGS]
```

This script:
1. Builds the JAR if it doesn't exist
2. Starts each database in Docker, waits for readiness, runs benchmarks, stops container
3. Stores results to external MongoDB (if configured in `config/benchmark_config.ini`)
4. Tests: MongoDB, DocumentDB, PostgreSQL, YugabyteDB, CockroachDB

Example:
```bash
sh scripts/test.sh -q 10 -n 200 -s 4000 -v
```

### Python Orchestration (Full Benchmark Suite)

For comprehensive benchmarks with resource monitoring, validation, and results storage:

```bash
# All databases, with queries, indexes, and validation
python3 scripts/run_article_benchmarks_docker.py --queries --validate

# Specific databases only
python3 scripts/run_article_benchmarks_docker.py --mongodb --postgresql --queries

# Insert-only (no indexes)
python3 scripts/run_article_benchmarks_docker.py --no-index --validate

# Full comparison (both indexed and non-indexed)
python3 scripts/run_article_benchmarks_docker.py --full-comparison --validate

# With large items (10KB, 100KB, 1000KB payloads)
python3 scripts/run_article_benchmarks_docker.py --queries --large-items
```

### Direct Java Execution

For single benchmark runs against a running database:
```bash
java -jar target/insertTest-1.0-jar-with-dependencies.jar [OPTIONS] [numItems]
```

## Results Storage and Webapp

### Architecture

```
Benchmark Runner → External MongoDB (benchmark_results.test_runs) → Webapp Dashboard
```

### Configuration

Create `config/benchmark_config.ini` from the example:
```bash
cp config/benchmark_config.ini.example config/benchmark_config.ini
```

The `[results_storage]` section configures the external MongoDB:
```ini
[results_storage]
mongodb_connection_string = mongodb+srv://user:pass@cluster.mongodb.net/benchmark_db
database_name = benchmark_results
collection_name = test_runs
```

### Result Document Schema

Each test result stored in MongoDB includes:
- `timestamp` - When the test ran
- `test_run_id` - UUID grouping results from a single benchmark session
- `database.type`, `database.version`, `database.docker_image` - What was tested
- `client.library`, `client.version` - Java driver info
- `test_config.test_type`, `test_config.payload_size`, `test_config.indexed`, etc.
- `results.insert_time_ms`, `results.insert_throughput`, `results.query_time_ms`, `results.query_throughput`
- `system_info` - CPU, memory, OS details
- `resource_metrics` - CPU, disk IOPS, I/O wait during test
- `ci_info` - CI platform, commit hash, branch (if in CI)

### Webapp

```bash
cd webapp
npm install
# Set MONGODB_CONNECTION_STRING in .env (or environment)
npm start
```

Open http://localhost:3000 for the dashboard with:
- Interactive Chart.js charts (insertion time, query time, throughput)
- Filter by database type, version, date range
- Results table with all test data
- CSV export

**API Endpoints:**
- `GET /api/results` - Query results with filters (database_type, database_version, start_date, end_date, limit, skip)
- `GET /api/results/:id` - Single result by ID
- `GET /api/results/meta/versions` - All unique database types, versions
- `GET /api/results/meta/comparison` - Aggregated performance comparison

## Data Validation

The `-v` (or `-validate`) flag enables post-test data integrity verification:

**Insertion validation:**
- Verifies document count in the database matches expected count
- Samples 1% of documents (minimum 10) and verifies each exists and matches

**Query validation:**
- Verifies query result count is non-zero
- Verifies result count doesn't exceed maximum possible

**Usage:**
```bash
# Direct Java
java -jar target/insertTest-1.0-jar-with-dependencies.jar -v -q 10 10000

# Python orchestration
python3 scripts/run_article_benchmarks_docker.py --queries --validate

# Shell script
sh scripts/test.sh -v -q 10
```

**Output:**
```
  ✓ Document count verified: 10000
  ✓ Sample validation: 100/100 documents verified
  ✓ Query count verified: 99941 items found (max possible: 100000)
```

**DatabaseOperations interface** validation methods:
- `long getDocumentCount(String collectionName)` - Count documents in DB
- `boolean validateDocument(String collectionName, String id, JSONObject expected)` - Verify specific document

All database implementations (MongoDB, PostgreSQL, Oracle, DocumentDB) implement these methods.

## Architecture

### Core Design Pattern

Strategy pattern with `DatabaseOperations` interface:
- **Interface**: `DatabaseOperations` (8 methods including validation)
- **Implementations**: `MongoDBOperations`, `PostgreSQLOperations`, `Oracle23AIOperations`, `OracleJCT`, `DocumentDBOperations`
- **Main coordinator**: `Main.java` - argument parsing, document generation, benchmarking, validation

### Project Structure

```
BSON-JSON-bakeoff/
├── src/main/java/com/mongodb/
│   ├── Main.java                    # Entry point, benchmark orchestration, validation
│   ├── DatabaseOperations.java      # Interface (with validation methods)
│   ├── MongoDBOperations.java       # MongoDB implementation
│   ├── PostgreSQLOperations.java    # PostgreSQL/YugabyteDB/CockroachDB implementation
│   ├── Oracle23AIOperations.java    # Oracle Duality Views
│   ├── OracleJCT.java              # Oracle JSON Collection Tables
│   └── DocumentDBOperations.java    # AWS DocumentDB (MongoDB-compatible)
├── scripts/
│   ├── run_article_benchmarks_docker.py  # Docker-based benchmark orchestration
│   ├── run_article_benchmarks.py         # Native (non-Docker) benchmark orchestration
│   ├── test.sh                           # Shell script for Docker testing
│   ├── results_storage.py                # MongoDB results storage module (pymongo)
│   ├── store_benchmark_results.py        # CLI to parse benchmark output and store in MongoDB
│   ├── version_detector.py               # Database/library version detection
│   ├── system_info_collector.py          # System info collection (CPU, memory, OS)
│   ├── monitor_resources.py              # Real-time resource monitoring during tests
│   └── profile_server.py                 # Server-side flame graph profiling
├── webapp/
│   ├── server.js                    # Express server (port 3000)
│   ├── package.json                 # Node.js dependencies
│   ├── config/mongodb.js            # MongoDB connection (uses env vars)
│   ├── routes/results.js            # REST API routes
│   └── public/                      # Frontend (HTML, CSS, JS with Chart.js)
│       ├── index.html               # Dashboard page
│       ├── css/style.css            # Styles
│       └── js/app.js                # Chart rendering, filtering, CSV export
├── config/
│   ├── benchmark_config.ini.example # Config template (DB connections + results storage)
│   ├── config.properties.example    # Java DB connection strings
│   └── config.example.json          # JSON test configuration
├── docs/                            # Feature documentation
├── pom.xml                          # Maven (Java 11, mongodb-driver-sync, postgresql, ojdbc11)
├── CLAUDE.md                        # This file
└── README.md                        # User-facing documentation
```

### Configuration

**`config/benchmark_config.ini`** (primary config for Docker testing):
- `[oracle]` - Oracle credentials and connection
- `[mongodb]` - MongoDB host/port for health checks
- `[postgresql]` - PostgreSQL user/host/port
- `[documentdb]` - DocumentDB credentials
- `[results_storage]` - External MongoDB for storing results

**`config.properties`** (JDBC connection strings for direct Java execution):
- `mongodb.connection.string`
- `postgresql.connection.string`
- `oracle.connection.string`

### Document Generation

Documents are generated in `Main.java` with:
- Deterministic random seed (42) for reproducibility
- Configurable payload sizes (default: 100B, 1000B; large: 10KB, 100KB, 1000KB)
- Single attribute (binary blob) or multi-attribute (split across N fields)
- Realistic nested data (`-rd` flag): subdocuments up to 5 levels deep with mixed types
- Array fields (`indexArray`/`targets`) with configurable link count for query testing

## Command-Line Flags (Java)

| Flag | Description |
|------|-------------|
| `-p` | Use PostgreSQL (also used for YugabyteDB, CockroachDB) |
| `-o` | Use Oracle JSON Duality Views |
| `-oj` | Use Oracle JSON Collection Tables |
| `-ddb` | Use DocumentDB |
| `-d` | Direct table insertion (Oracle Duality Views - bypasses bug) |
| `-j` | Use JSONB instead of JSON (PostgreSQL only) |
| `-i` | Run indexed vs non-indexed comparison |
| `-mv` | Use multivalue index (Oracle JCT, requires `-i`, 7x faster) |
| `-rd` | Use realistic nested data structures |
| `-v` | Enable data validation after each test |
| `-q N` | Run query test with N array elements per document |
| `-l N` | Run $lookup test with N links |
| `-r N` | Run each test N times, report best |
| `-s SIZES` | Comma-delimited payload sizes (e.g., `-s 100,1000,5000`) |
| `-n N` | Number of attributes to split payload across |
| `-b N` | Batch size for bulk insertions |
| `-size` | Measure and report BSON/OSON document sizes |
| `-c FILE` | Load configuration from JSON file |

## Python Orchestration Flags (run_article_benchmarks_docker.py)

| Flag | Description |
|------|-------------|
| `--mongodb` | Include MongoDB tests |
| `--documentdb` | Include DocumentDB tests |
| `--postgresql` | Include PostgreSQL tests |
| `--yugabytedb` | Include YugabyteDB tests |
| `--cockroachdb` | Include CockroachDB tests |
| `--queries` / `-q` | Enable query tests |
| `--no-index` | Insert-only, no indexes |
| `--full-comparison` | Run both indexed and non-indexed |
| `--validate` | Enable data integrity validation |
| `--large-items` | Add 10KB, 100KB, 1000KB payload tests |
| `--monitor` / `--no-monitor` | Enable/disable resource monitoring (default: enabled) |
| `--monitor-interval N` | Monitoring interval in seconds (default: 5) |
| `--measure-sizes` | Enable BSON/OSON size measurement |
| `--randomize-order` | Randomize test execution order |
| `--num-docs N` | Documents per test (default: 10000) |
| `--num-runs N` | Runs per test (default: 3) |
| `--batch-size N` | Batch size (default: 500) |

## Features Needing Further Work

### 1. Webapp Visualization (Partially Complete)
- **Done**: Basic dashboard with Chart.js charts, filtering, CSV export, REST API
- **Needs work**: The webapp UI is functional but basic. Could benefit from:
  - Comparison views between test runs (side-by-side)
  - Historical trend charts showing performance over time
  - Drill-down into individual test run details
  - Better handling of realistic data test types in charts
  - Authentication/access control if deployed publicly

### 2. Data Validation (Recently Added - Needs Testing)
- **Done**: `getDocumentCount()` and `validateDocument()` implemented in all DB backends. Insertion count verification and sample document validation in Main.java. Query result reasonableness checks.
- **Needs work**:
  - Validation only checks document existence and ID match; could verify full payload content
  - No validation summary report at end of benchmark run
  - Validation results are not stored in the MongoDB results database
  - No automated regression testing that uses validation to catch correctness issues
  - The `-v` flag passes through Python scripts but validation output is only in Java stdout - not parsed or stored structurally

### 3. Results Storage (Functional but Could Be More Robust)
- **Done**: `ResultsStorage` class, `store_benchmark_results.py` CLI, automatic storage in both Python scripts and test.sh
- **Needs work**:
  - `store_benchmark_results.py` (used by test.sh) builds a simpler document schema than `run_article_benchmarks_docker.py` - schemas should be unified
  - No deduplication or idempotency - rerunning stores duplicate results
  - No cleanup/retention policy for old results
  - Connection failures during storage are warnings, not errors - results can be silently lost

### 4. Docker-based Testing
- **Done**: Full Docker lifecycle management for MongoDB, DocumentDB, PostgreSQL, YugabyteDB, CockroachDB. Per-test container restart for isolation.
- **Needs work**:
  - Oracle databases are not Dockerized (require native install)
  - No Docker Compose file - everything is imperative `docker run` commands
  - DocumentDB image requires manual pull from GitHub Container Registry on first use
  - No health check timeout configuration (hardcoded to 60s)

## Oracle 23AI Special Considerations

**JSON Duality Views** (`-o` flag):
- Known bug in Oracle 23AI Free: array values treated as globally unique during insertion through Duality Views, causing silent data loss
- Workaround: `-d` flag for direct table insertion

**JSON Collection Tables** (`-oj` flag):
- Two index types: search index (default) vs multivalue index (`-mv`, 7x faster)
- Multivalue index requires `[*].string()` syntax in index creation
- Query syntax differs between index types

## Development Notes

### Adding New Database Support

1. Create class implementing `DatabaseOperations` interface (8 methods including `getDocumentCount` and `validateDocument`)
2. Add command-line flag in `Main.java`
3. Add Docker container configuration in `run_article_benchmarks_docker.py` DATABASES list
4. Add container startup/readiness logic in the Docker scripts
5. Add connection config to `config/benchmark_config.ini.example`
