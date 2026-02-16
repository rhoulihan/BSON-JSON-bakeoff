# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Java-based benchmarking tool that compares document storage and retrieval performance across multiple databases. Local databases run in Docker containers; cloud/SaaS databases (MongoDB Atlas, Azure DocumentDB) are tested remotely. All results are stored in an external MongoDB instance and visualized through a Node.js webapp dashboard.

### Key Architecture

1. **Java benchmark engine** - Core insertion/query tests with configurable payloads
2. **Docker-based test execution** - Each local database runs in its own container for isolation
3. **Cloud/SaaS database support** - MongoDB Atlas and Azure DocumentDB tested over network
4. **External MongoDB results storage** - All benchmark results posted to a central MongoDB instance
5. **Node.js/Express webapp** - Dashboard for visualizing, filtering by test run, and comparing results
6. **Data validation** - Post-test verification that data was written and read back correctly
7. **Latency tracking** - Per-operation latency metrics (p50/p95/p99) for cloud databases
8. **Test run grouping** - UUID-based test_run_id links all results from a single execution

## Supported Databases

### Local (Docker)

| Database | Docker Image | Driver | Flag |
|----------|-------------|--------|------|
| MongoDB (BSON) | `mongo` | mongodb-driver-sync 5.5.1 | (default) |
| DocumentDB | `documentdb-local` | mongodb-driver-sync 5.5.1 | `-ddb` |
| PostgreSQL (JSON/JSONB) | `postgres:latest` | postgresql 42.7.3 | `-p` |
| YugabyteDB (YSQL) | `yugabytedb/yugabyte:latest` | postgresql 42.7.3 | `-p` |
| CockroachDB (SQL) | `cockroachdb/cockroach:latest` | postgresql 42.7.3 | `-p` |

### Cloud/SaaS (Optional, config-gated)

| Database | Type Key | Config Section | Flag |
|----------|---------|---------------|------|
| MongoDB Atlas | `mongodb-cloud` | `[mongodb_atlas]` | `--mongodb-atlas` |
| Azure DocumentDB | `documentdb-azure` | `[azure_documentdb]` | `--azure-documentdb` |

### Oracle (Native install, not Dockerized)

| Database | Driver | Flag |
|----------|--------|------|
| Oracle 23AI (Duality Views) | ojdbc11 23.4.0 | `-o` |
| Oracle 23AI (JCT) | ojdbc11 23.4.0 | `-oj` |

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
2. Auto-generates `config.properties` with Docker-correct connection strings
3. Starts each database in Docker, waits for readiness, runs benchmarks (with `-Dconn` override), stops container
4. Stores results to external MongoDB (if configured in `config/benchmark_config.ini`)
5. Tests: MongoDB, DocumentDB, PostgreSQL, YugabyteDB, CockroachDB

Example:
```bash
sh scripts/test.sh -q 10 -n 200 -s 4000 -v
```

### Python Orchestration (Full Benchmark Suite)

For comprehensive benchmarks with resource monitoring, validation, and results storage:

```bash
# All Docker databases, with queries, indexes, and validation
python3 scripts/run_article_benchmarks_docker.py --queries --validate

# Specific databases only
python3 scripts/run_article_benchmarks_docker.py --mongodb --postgresql --queries

# Include cloud databases
python3 scripts/run_article_benchmarks_docker.py --queries --mongodb-atlas --azure-documentdb

# Full comparison (both indexed and non-indexed)
python3 scripts/run_article_benchmarks_docker.py --full-comparison --validate
```

Each run generates a UUID `test_run_id` that groups all database results together.

### Direct Java Execution

For single benchmark runs against a running database:
```bash
java -jar target/insertTest-1.0-jar-with-dependencies.jar [OPTIONS] [numItems]

# Override connection string (used by Docker scripts)
java -Dconn="mongodb://localhost:27017" -jar target/insertTest-1.0-jar-with-dependencies.jar [OPTIONS]
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

Cloud databases are configured in their own sections:
```ini
[mongodb_atlas]
enabled = true
connection_string = mongodb+srv://user:pass@cluster.mongodb.net/test

[azure_documentdb]
enabled = true
connection_string = mongodb://user:pass@host:10255/?ssl=true&replicaSet=globaldb&...
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
- `resource_metrics` - CPU, disk IOPS, I/O wait during test (Docker databases)
- `latency_metrics` - Per-operation p50/p95/p99 percentiles (cloud databases)
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
- Latency percentile charts for cloud database results
- Filter by database type, version, test run ID, date range
- System info and resource metrics display
- Results table with all test data
- CSV export

**API Endpoints:**
- `GET /api/results` - Query results with filters (`database_type`, `database_version`, `test_run_id`, `start_date`, `end_date`, `limit`, `skip`)
- `GET /api/results/:id` - Single result by ID
- `GET /api/results/meta/versions` - All unique database types, versions, and test run IDs
- `GET /api/results/meta/comparison` - Aggregated performance comparison

## Data Validation

The `-v` (or `--validate`) flag enables post-test data integrity verification:

**Insertion validation:**
- Verifies document count in the database matches expected count
- Samples 1% of documents (minimum 10) and verifies each exists and matches

**Query validation:**
- Verifies query result count is non-zero
- Verifies result count doesn't exceed maximum possible

**DatabaseOperations interface** validation methods:
- `long getDocumentCount(String collectionName)` - Count documents in DB
- `boolean validateDocument(String collectionName, String id, JSONObject expected)` - Verify specific document

All database implementations (MongoDB, PostgreSQL, Oracle, DocumentDB) implement these methods.

## Latency Tracking (Cloud Databases)

For cloud/SaaS databases, local resource monitoring is not meaningful. Instead, the `-latency` Java flag enables per-operation latency collection:

- `LatencyCollector.java` records per-batch insert and per-query latencies
- Calculates min, max, avg, p50, p95, p99 percentile statistics
- Outputs structured `LATENCY_STATS|<operation_type>|{json}` lines parsed by Python
- Python orchestration automatically enables `-latency` for cloud database types
- Results stored in `latency_metrics` field of MongoDB result documents
- Webapp shows dedicated latency charts for cloud database results

## Architecture

### Core Design Pattern

Strategy pattern with `DatabaseOperations` interface:
- **Interface**: `DatabaseOperations` (8 methods including validation)
- **Implementations**: `MongoDBOperations`, `PostgreSQLOperations`, `Oracle23AIOperations`, `OracleJCT`, `DocumentDBOperations`
- **Main coordinator**: `Main.java` - argument parsing, document generation, benchmarking, validation
- **Latency collector**: `LatencyCollector.java` - per-operation latency tracking

### Connection String Override

Docker test scripts pass connection strings directly via `-Dconn` JVM system property. This ensures correct credentials and ports regardless of what's in `config.properties`. The Java code applies the override at `Main.java` line ~219:
```java
connectionString = System.getProperty("conn", connectionString);
```

### DocumentDB Special Handling

DocumentDB is built on PostgreSQL with a MongoDB wire protocol gateway:
- **TLS required**: Gateway on port 10260 uses auto-generated TLS certificates. All connections must include `tls=true&tlsAllowInvalidCertificates=true`
- **Version reporting**: Three components captured — DocumentDB product version, MongoDB wire protocol compatibility version, underlying PostgreSQL version
- **Startup**: PostgreSQL engine starts first (~4s), MongoDB protocol layer starts after. Readiness checks use pymongo with TLS, then fall back to psql inside the container
- **Java TLS handling**: `DocumentDBOperations.initializeDatabase()` detects `tls=true` and `tlsAllowInvalidCertificates=true` in the connection string and builds a custom `SSLContext` that accepts self-signed certificates

### Project Structure

```
BSON-JSON-bakeoff/
├── src/main/java/com/mongodb/
│   ├── Main.java                    # Entry point, benchmark orchestration, validation
│   ├── DatabaseOperations.java      # Interface (with validation methods)
│   ├── MongoDBOperations.java       # MongoDB implementation
│   ├── PostgreSQLOperations.java    # PostgreSQL/YugabyteDB/CockroachDB
│   ├── DocumentDBOperations.java    # DocumentDB (local + Azure, requires TLS)
│   ├── LatencyCollector.java        # Per-operation latency tracking
│   ├── Oracle23AIOperations.java    # Oracle Duality Views
│   └── OracleJCT.java              # Oracle JSON Collection Tables
├── scripts/
│   ├── run_article_benchmarks_docker.py  # Docker + cloud benchmark orchestration
│   ├── test.sh                           # Shell script for Docker testing
│   ├── results_storage.py                # MongoDB results storage module (pymongo)
│   ├── store_benchmark_results.py        # CLI to parse benchmark output → MongoDB
│   ├── version_detector.py               # Database/library version detection
│   ├── system_info_collector.py          # System info collection (CPU, memory, OS)
│   └── monitor_resources.py              # Real-time resource monitoring during tests
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
│   ├── benchmark_config.ini.example # Config (DB connections, cloud DBs, results storage)
│   ├── config.properties.example    # Java DB connection strings
│   └── config.example.json          # JSON test configuration
├── pom.xml                          # Maven (Java 11, mongodb-driver-sync, postgresql, ojdbc11)
├── QUICKSTART.md                    # End-to-end setup guide
├── CLAUDE.md                        # This file
└── README.md                        # User-facing documentation
```

### Configuration Files

**`config/benchmark_config.ini`** (primary config):
- `[results_storage]` - External MongoDB for storing results
- `[mongodb_atlas]` - MongoDB Atlas connection (enabled/disabled)
- `[azure_documentdb]` - Azure DocumentDB connection (enabled/disabled)
- `[mongodb]` - MongoDB host/port for health checks
- `[postgresql]` - PostgreSQL user/host/port
- `[documentdb]` - DocumentDB credentials

**`config.properties`** (Java JDBC connection strings):
- Auto-generated by Docker scripts with correct defaults
- Overridden by `-Dconn` JVM property for Docker testing

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
| `-ddb` | Use DocumentDB |
| `-o` | Use Oracle JSON Duality Views |
| `-oj` | Use Oracle JSON Collection Tables |
| `-d` | Direct table insertion (Oracle Duality Views - bypasses bug) |
| `-j` | Use JSONB instead of JSON (PostgreSQL only) |
| `-i` | Run indexed vs non-indexed comparison |
| `-mv` | Use multivalue index (Oracle JCT, requires `-i`, 7x faster) |
| `-rd` | Use realistic nested data structures |
| `-v` | Enable data validation after each test |
| `-latency` | Enable per-operation latency collection (for cloud DBs) |
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
| `--mongodb-atlas` | Include MongoDB Atlas (requires config, enables latency) |
| `--azure-documentdb` | Include Azure DocumentDB (requires config, enables latency) |
| `--queries` / `-q` | Enable query tests |
| `--no-index` | Insert-only, no indexes |
| `--full-comparison` | Run both indexed and non-indexed |
| `--validate` | Enable data integrity validation |
| `--large-items` | Add 10KB, 100KB, 1000KB payload tests |
| `--monitor` / `--no-monitor` | Enable/disable resource monitoring (default: enabled) |
| `--monitor-interval N` | Monitoring interval in seconds |
| `--measure-sizes` | Enable BSON/OSON size measurement |
| `--randomize-order` | Randomize test execution order |
| `--num-docs N` | Documents per test (default: 10000) |
| `--num-runs N` | Runs per test (default: 3) |
| `--batch-size N` | Batch size (default: 500) |

## Development Notes

### Adding New Database Support

1. Create class implementing `DatabaseOperations` interface (8 methods including `getDocumentCount` and `validateDocument`)
2. Add command-line flag in `Main.java`
3. Add Docker container configuration in `run_article_benchmarks_docker.py` DATABASES list
4. Add container startup/readiness logic in the Docker scripts
5. Add connection config to `config/benchmark_config.ini.example`
6. Add connection string to `get_docker_connection_string()` in both scripts
7. Add version detection in `scripts/version_detector.py`

### Oracle 23AI Special Considerations

**JSON Duality Views** (`-o` flag):
- Known bug in Oracle 23AI Free: array values treated as globally unique during insertion through Duality Views, causing silent data loss
- Workaround: `-d` flag for direct table insertion

**JSON Collection Tables** (`-oj` flag):
- Two index types: search index (default) vs multivalue index (`-mv`, 7x faster)
- Multivalue index requires `[*].string()` syntax in index creation
