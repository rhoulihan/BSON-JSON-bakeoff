# BSON-JSON Bakeoff

A comprehensive benchmarking tool that compares document storage and retrieval performance across multiple database systems. Local databases run in Docker containers; cloud/SaaS databases are tested remotely. All results are stored in an external MongoDB instance and visualized through a web dashboard.

## Overview

This project provides a Java-based benchmark engine that generates synthetic documents with configurable payloads and tests how efficiently various databases can insert and query these documents. Results are automatically posted to an external MongoDB instance for historical tracking and comparison, then visualized through an interactive web dashboard.

**Key capabilities:**
- Dockerized testing across 5 local database systems with automated container lifecycle
- Cloud/SaaS database testing against MongoDB Atlas and Azure DocumentDB
- Centralized results storage in MongoDB with full metadata (versions, system info, resource metrics)
- Test run grouping via UUID — all databases in a single run share the same test_run_id
- Web dashboard for interactive visualization, filtering by test run, and comparison
- Per-operation latency metrics for cloud databases (p50, p95, p99 percentiles)
- Data validation to verify correctness of writes and reads

## Supported Databases

### Local (Docker-based)

| Database | Type | Docker Image | Notes |
|----------|------|-------------|-------|
| **MongoDB** | Native BSON | `mongo` | Reference implementation |
| **DocumentDB** | MongoDB-compatible | `documentdb-local` | Open-source, requires TLS |
| **PostgreSQL** | JSON/JSONB | `postgres:latest` | GIN indexes, array containment |
| **YugabyteDB** | Distributed SQL | `yugabytedb/yugabyte:latest` | PostgreSQL-compatible |
| **CockroachDB** | Distributed SQL | `cockroachdb/cockroach:latest` | PostgreSQL-compatible |

### Cloud/SaaS (Optional)

| Database | Type | Config Section | Notes |
|----------|------|---------------|-------|
| **MongoDB Atlas** | `mongodb-cloud` | `[mongodb_atlas]` | Requires Atlas connection string |
| **Azure DocumentDB** | `documentdb-azure` | `[azure_documentdb]` | Requires Azure Cosmos DB connection string |

Cloud databases must be explicitly enabled in `config/benchmark_config.ini` and require valid connection credentials.

## Quick Start

**For the complete end-to-end walkthrough** (build, run all tests, store results, view dashboard), see **[QUICKSTART.md](QUICKSTART.md)**.

### Prerequisites

- Java 11+
- Maven 3.x
- Docker
- Python 3.x with `pymongo` (for orchestration and results storage)
- Node.js 18+ (for webapp)

### 1. Clone and Build

```bash
git clone https://github.com/rhoulihan/BSON-JSON-bakeoff.git
cd BSON-JSON-bakeoff
mvn clean package
```

### 2. Configure Results Storage

```bash
cp config/benchmark_config.ini.example config/benchmark_config.ini
```

Edit `config/benchmark_config.ini` and set your MongoDB connection string in `[results_storage]`:
```ini
[results_storage]
mongodb_connection_string = mongodb+srv://user:pass@cluster.mongodb.net/benchmark_db
database_name = benchmark_results
collection_name = test_runs
```

### 3. Run Benchmarks

**Quick test across all Docker databases:**
```bash
sh scripts/test.sh -q 10 -s 1000
```

**Full benchmark suite with Python orchestration:**
```bash
python3 scripts/run_article_benchmarks_docker.py --queries --validate
```

**Include cloud databases (if configured):**
```bash
python3 scripts/run_article_benchmarks_docker.py --queries --validate --mongodb-atlas --azure-documentdb
```

### 4. View Results

```bash
cd webapp
npm install
# Set MONGODB_CONNECTION_STRING environment variable or .env file
npm start
```

Open http://localhost:3000 to view the dashboard.

## Testing Modes

### Shell Script (`scripts/test.sh`)

Sequentially tests all Docker databases with the same Java flags:

```bash
# Basic insertion test
sh scripts/test.sh

# With query tests, 200 attributes, 4000B payloads, validation
sh scripts/test.sh -q 10 -n 200 -s 4000 -v

# Specific flags are passed through to the Java benchmark
sh scripts/test.sh -i -rd -q 10 -r 3 -b 500 10000
```

The script automatically:
1. Builds the JAR if needed
2. Auto-generates `config.properties` with Docker-correct connection strings
3. Starts each database container, waits for readiness
4. Runs the benchmark with explicit connection string override (`-Dconn`)
5. Stores results to MongoDB (if configured)
6. Cleans up containers

### Python Orchestration (`scripts/run_article_benchmarks_docker.py`)

Full-featured benchmark runner with per-test isolation, monitoring, and results storage:

```bash
# All Docker databases with queries and validation
python3 scripts/run_article_benchmarks_docker.py --queries --validate

# Specific databases
python3 scripts/run_article_benchmarks_docker.py --mongodb --postgresql --queries

# Insert-only (no indexes)
python3 scripts/run_article_benchmarks_docker.py --no-index --validate

# Full comparison (indexed + non-indexed)
python3 scripts/run_article_benchmarks_docker.py --full-comparison --validate

# Include large payloads (10KB, 100KB, 1000KB)
python3 scripts/run_article_benchmarks_docker.py --queries --large-items

# Customize document count and runs
python3 scripts/run_article_benchmarks_docker.py --queries --num-docs 5000 --num-runs 5

# Include cloud databases
python3 scripts/run_article_benchmarks_docker.py --queries --mongodb-atlas --azure-documentdb
```

Each run generates a unique `test_run_id` (UUID) that groups all database results together for filtering in the webapp.

**Test configurations:**
- Single attribute tests: 10B, 200B, 1000B, 2000B, 4000B
- Multi attribute tests: 10x1B, 10x20B, 50x20B, 100x20B, 200x20B
- Large item tests (with `--large-items`): 10KB, 100KB, 1000KB
- Default: 10,000 documents, 3 runs (best time), batch size 500

## Cloud/SaaS Database Testing

Cloud databases are tested over the network against remote SaaS instances. They use the same Java benchmark engine but skip Docker container management and replace local resource monitoring with per-operation latency tracking.

### Configuration

Add credentials to `config/benchmark_config.ini`:

```ini
[mongodb_atlas]
enabled = true
connection_string = mongodb+srv://user:pass@cluster.mongodb.net/test

[azure_documentdb]
enabled = true
connection_string = mongodb://user:pass@host:10255/?ssl=true&replicaSet=globaldb&...
```

### Running

```bash
# Cloud databases only
python3 scripts/run_article_benchmarks_docker.py --queries --mongodb-atlas --azure-documentdb

# Mix of local and cloud
python3 scripts/run_article_benchmarks_docker.py --queries --mongodb --mongodb-atlas
```

### Latency Metrics

For cloud databases, the benchmark collects per-operation latency measurements instead of host resource monitoring:
- Per-batch insert latencies and per-query latencies
- Min, max, avg, p50, p95, p99 percentile statistics
- Latency over time (to detect spikes or degradation)

These are stored in result documents and visualized in the webapp with dedicated latency charts.

## Data Validation

The `-v` flag enables post-test data integrity verification:

```bash
# Via Python orchestration
python3 scripts/run_article_benchmarks_docker.py --queries --validate

# Via shell script
sh scripts/test.sh -v -q 10
```

**What gets validated:**
- **Insertion**: Document count matches expected; 1% sample (min 10 docs) verified by reading back from DB
- **Queries**: Result count is non-zero and within expected bounds

**Example output:**
```
  ✓ Document count verified: 10000
  ✓ Sample validation: 100/100 documents verified
  ✓ Query count verified: 99941 items found (max possible: 100000)
```

## Results Storage

Benchmark results are stored in an external MongoDB instance with comprehensive metadata:

- `test_run_id` — UUID grouping all results from a single benchmark execution
- Database type, version, and Docker image info
- Client library versions (Java driver)
- System information (CPU, memory, OS)
- Resource metrics (CPU usage, disk IOPS, I/O wait) for Docker databases
- Latency metrics (p50, p95, p99 percentiles) for cloud databases
- CI environment metadata (platform, commit hash, branch)
- Test configuration and performance results

## Webapp Dashboard

The visualization webapp provides an interactive dashboard for exploring benchmark results.

```bash
cd webapp
npm install
npm start
```

**Features:**
- Interactive charts (insertion time, query time, throughput) using Chart.js
- Latency percentile charts for cloud database results
- Filter by database type, database version, test run ID, date range
- System info and resource metrics display per result
- Results table showing all test metadata
- CSV export for further analysis
- REST API for programmatic access

**API Endpoints:**
| Endpoint | Description |
|----------|-------------|
| `GET /api/results` | Query results with filters (`database_type`, `database_version`, `test_run_id`, `start_date`, `end_date`) |
| `GET /api/results/:id` | Get single result |
| `GET /api/results/meta/versions` | List all database types, versions, and test run IDs |
| `GET /api/results/meta/comparison` | Aggregated performance comparison |

**Configuration:**
Set `MONGODB_CONNECTION_STRING` as an environment variable or in a `.env` file in the webapp directory.

## Command-Line Reference

### Java Flags

| Flag | Description | Default |
|------|-------------|---------|
| `-p` | Use PostgreSQL (also YugabyteDB, CockroachDB) | MongoDB |
| `-ddb` | Use DocumentDB | MongoDB |
| `-o` | Use Oracle JSON Duality Views | MongoDB |
| `-oj` | Use Oracle JSON Collection Tables | MongoDB |
| `-d` | Direct table insertion (Oracle Duality Views, bypasses bug) | Via view |
| `-j` | Use JSONB instead of JSON (PostgreSQL only) | JSON |
| `-i` | Run indexed vs non-indexed comparison | Indexed only |
| `-mv` | Use multivalue index (Oracle JCT, requires `-i`) | Search index |
| `-rd` | Use realistic nested data structures | Flat binary |
| `-v` | Enable data validation | Disabled |
| `-q N` | Query test with N array links per document | No queries |
| `-l N` | $lookup test with N links | No lookup |
| `-r N` | Run each test N times, keep best | 1 |
| `-s SIZES` | Comma-delimited payload sizes in bytes | 100,1000 |
| `-n N` | Number of attributes for payload | 10 |
| `-b N` | Batch size | 100 |
| `-size` | Measure BSON/OSON document sizes | Disabled |
| `-latency` | Enable per-operation latency collection | Disabled |
| `-c FILE` | Load config from JSON file | None |
| `[numItems]` | Total documents to generate | 10000 |

### Python Orchestration Flags

| Flag | Description | Default |
|------|-------------|---------|
| `--mongodb` | Include MongoDB | All Docker DBs if none specified |
| `--documentdb` | Include DocumentDB | All Docker DBs if none specified |
| `--postgresql` | Include PostgreSQL | All Docker DBs if none specified |
| `--yugabytedb` | Include YugabyteDB | All Docker DBs if none specified |
| `--cockroachdb` | Include CockroachDB | All Docker DBs if none specified |
| `--mongodb-atlas` | Include MongoDB Atlas (requires config) | Disabled |
| `--azure-documentdb` | Include Azure DocumentDB (requires config) | Disabled |
| `--queries` / `-q` | Enable query tests | Disabled |
| `--no-index` | Insert-only, no indexes | With indexes |
| `--full-comparison` | Run both indexed and non-indexed | Single mode |
| `--validate` | Enable data integrity validation | Disabled |
| `--large-items` | Add 10KB, 100KB, 1000KB tests | Standard only |
| `--monitor` / `--no-monitor` | Resource monitoring | Enabled |
| `--num-docs N` | Documents per test | 10000 |
| `--num-runs N` | Runs per test | 3 |
| `--batch-size N` | Batch size | 500 |

## Project Structure

```
BSON-JSON-bakeoff/
├── src/main/java/com/mongodb/
│   ├── Main.java                    # Entry point, orchestration, validation
│   ├── DatabaseOperations.java      # Interface (8 methods incl. validation)
│   ├── MongoDBOperations.java       # MongoDB implementation
│   ├── PostgreSQLOperations.java    # PostgreSQL/Yugabyte/CockroachDB
│   ├── DocumentDBOperations.java    # DocumentDB (local + Azure, requires TLS)
│   ├── LatencyCollector.java        # Per-operation latency tracking for cloud DBs
│   ├── Oracle23AIOperations.java    # Oracle Duality Views
│   └── OracleJCT.java              # Oracle JSON Collection Tables
├── scripts/
│   ├── run_article_benchmarks_docker.py  # Docker + cloud benchmark orchestration
│   ├── test.sh                           # Shell-based Docker testing
│   ├── results_storage.py                # MongoDB results storage (pymongo)
│   ├── store_benchmark_results.py        # CLI for parsing output → MongoDB
│   ├── version_detector.py               # DB/library version detection
│   ├── system_info_collector.py          # System info collection
│   └── monitor_resources.py              # Resource monitoring
├── webapp/
│   ├── server.js                    # Express server
│   ├── routes/results.js            # REST API
│   ├── config/mongodb.js            # MongoDB connection
│   └── public/                      # Frontend (HTML/CSS/JS + Chart.js)
├── config/
│   ├── benchmark_config.ini.example # Primary config (DB connections, cloud DBs, results storage)
│   ├── config.properties.example    # Java JDBC connections (auto-generated for Docker)
│   └── config.example.json          # JSON test configuration
├── pom.xml                          # Maven build (Java 11)
├── QUICKSTART.md                    # End-to-end setup guide
├── CLAUDE.md                        # AI assistant guidance
└── README.md                        # This file
```

## Configuration

### `config/benchmark_config.ini` (Primary)

```ini
[results_storage]
mongodb_connection_string = mongodb+srv://user:pass@cluster.mongodb.net/benchmark_db
database_name = benchmark_results
collection_name = test_runs

[mongodb_atlas]
enabled = false
connection_string = mongodb+srv://user:pass@cluster.mongodb.net/test

[azure_documentdb]
enabled = false
connection_string = mongodb://user:pass@host:10255/?ssl=true&replicaSet=globaldb&...
```

### `config.properties` (Java connections — auto-generated for Docker testing)

Auto-generated by `test.sh` and `run_article_benchmarks_docker.py` with Docker-correct defaults. For Docker testing, connection strings are also passed directly via `-Dconn` JVM property, so this file is mainly a fallback.

## DocumentDB Notes

DocumentDB is built on PostgreSQL with a MongoDB wire protocol gateway. Key considerations:

- **TLS required**: All connections to the gateway (port 10260) must use `tls=true&tlsAllowInvalidCertificates=true`
- **Version reporting**: Captures three version components — DocumentDB product version, MongoDB wire protocol compatibility version, and underlying PostgreSQL version
- **Startup time**: The MongoDB wire protocol layer starts after PostgreSQL, so readiness checks include extended timeouts

## Known Issues

### Oracle 23AI Duality View Array Bug

Oracle 23AI Free (23.0.0.0.0) incorrectly treats array values as globally unique during insertion through Duality Views, causing silent data loss. Use `-d` flag for direct table insertion as a workaround.

### Oracle Not Dockerized

Oracle databases require native installation and are not managed by the Docker test scripts.

## License

Apache License 2.0. See `LICENSE` for details.

## Author

Rick Houlihan
