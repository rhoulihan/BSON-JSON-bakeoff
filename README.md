# BSON-JSON Bakeoff

A comprehensive benchmarking tool that compares document storage and retrieval performance across multiple database systems using Docker containers. Results are stored in an external MongoDB database and visualized through a web dashboard.

## Overview

This project provides a Java-based benchmark engine that generates synthetic documents with configurable payloads and tests how efficiently various databases can insert and query these documents. Databases run in Docker containers for repeatable, isolated testing. Results are automatically posted to an external MongoDB instance for historical tracking and comparison.

**Key capabilities:**
- Dockerized testing across 5+ database systems with automated container lifecycle
- Centralized results storage in MongoDB with full metadata (versions, system info, resource metrics)
- Web dashboard for interactive visualization and comparison of results
- Data validation to verify correctness of writes and reads
- Configurable payloads, indexing strategies, and query patterns

## Supported Databases

| Database | Type | Docker Image | Notes |
|----------|------|-------------|-------|
| **MongoDB** | Native BSON | `mongo` | Reference implementation |
| **DocumentDB** | MongoDB-compatible | `documentdb-local` | Open-source local version |
| **PostgreSQL** | JSON/JSONB | `postgres:latest` | GIN indexes, array containment |
| **YugabyteDB** | Distributed SQL | `yugabytedb/yugabyte:latest` | PostgreSQL-compatible |
| **CockroachDB** | Distributed SQL | `cockroachdb/cockroach:latest` | PostgreSQL-compatible |
| **Oracle 23AI** | JSON Duality Views / JCT | Native install | Not yet Dockerized |

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

### 2. Configure Results Storage (Optional)

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
2. Starts each database container, waits for readiness
3. Runs the benchmark, captures output to log files
4. Stores results to MongoDB (if configured)
5. Cleans up containers

### Python Orchestration (`scripts/run_article_benchmarks_docker.py`)

Full-featured benchmark runner with per-test isolation, monitoring, and results storage:

```bash
# All databases with queries and validation
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
```

**Test configurations:**
- Single attribute tests: 10B, 200B, 1000B, 2000B, 4000B
- Multi attribute tests: 10x1B, 10x20B, 50x20B, 100x20B, 200x20B
- Large item tests (with `--large-items`): 10KB, 100KB, 1000KB
- Default: 10,000 documents, 3 runs (best time), batch size 500

### Direct Java Execution

For running against a database that's already running:

```bash
# MongoDB with defaults
java -jar target/insertTest-1.0-jar-with-dependencies.jar

# PostgreSQL with JSONB, 20K docs
java -jar target/insertTest-1.0-jar-with-dependencies.jar -p -j 20000

# Oracle JCT with multivalue index, realistic data, queries, validation
java -jar target/insertTest-1.0-jar-with-dependencies.jar -oj -i -mv -rd -v -q 10 -r 3 -b 1000 10000

# DocumentDB
java -jar target/insertTest-1.0-jar-with-dependencies.jar -ddb -q 10 5000
```

## Data Validation

The `-v` flag enables post-test data integrity verification:

```bash
# Via Java directly
java -jar target/insertTest-1.0-jar-with-dependencies.jar -v -q 10 10000

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

Benchmark results are automatically stored in an external MongoDB instance with comprehensive metadata:

- Database type, version, and Docker image info
- Client library versions (Java driver)
- System information (CPU, memory, OS)
- Resource metrics (CPU usage, disk IOPS, I/O wait)
- CI environment metadata (platform, commit hash, branch)
- Test configuration and performance results

**Two storage paths:**
1. `run_article_benchmarks_docker.py` builds full result documents in Python and stores them directly
2. `test.sh` calls `store_benchmark_results.py` to parse Java output and store it

## Webapp Dashboard

The visualization webapp provides an interactive dashboard for exploring benchmark results.

```bash
cd webapp
npm install
npm start
```

**Features:**
- Interactive charts (insertion time, query time, throughput) using Chart.js
- Filter by database type, database version, date range
- Results table showing all test metadata
- CSV export for further analysis
- REST API for programmatic access

**API Endpoints:**
| Endpoint | Description |
|----------|-------------|
| `GET /api/results` | Query results with filters |
| `GET /api/results/:id` | Get single result |
| `GET /api/results/meta/versions` | List all database types and versions |
| `GET /api/results/meta/comparison` | Aggregated performance comparison |

**Configuration:**
Set `MONGODB_CONNECTION_STRING` as an environment variable or in a `.env` file in the webapp directory.

## Command-Line Reference

### Java Flags

| Flag | Description | Default |
|------|-------------|---------|
| `-p` | Use PostgreSQL (also YugabyteDB, CockroachDB) | MongoDB |
| `-o` | Use Oracle JSON Duality Views | MongoDB |
| `-oj` | Use Oracle JSON Collection Tables | MongoDB |
| `-ddb` | Use DocumentDB | MongoDB |
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
| `-c FILE` | Load config from JSON file | None |
| `[numItems]` | Total documents to generate | 10000 |

### Python Orchestration Flags

| Flag | Description | Default |
|------|-------------|---------|
| `--mongodb` | Include MongoDB | All if none specified |
| `--documentdb` | Include DocumentDB | All if none specified |
| `--postgresql` | Include PostgreSQL | All if none specified |
| `--yugabytedb` | Include YugabyteDB | All if none specified |
| `--cockroachdb` | Include CockroachDB | All if none specified |
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
│   ├── Oracle23AIOperations.java    # Oracle Duality Views
│   ├── OracleJCT.java              # Oracle JSON Collection Tables
│   └── DocumentDBOperations.java    # AWS DocumentDB
├── scripts/
│   ├── run_article_benchmarks_docker.py  # Docker benchmark orchestration
│   ├── run_article_benchmarks.py         # Native benchmark orchestration
│   ├── test.sh                           # Shell-based Docker testing
│   ├── results_storage.py                # MongoDB results storage (pymongo)
│   ├── store_benchmark_results.py        # CLI for parsing output → MongoDB
│   ├── version_detector.py               # DB/library version detection
│   ├── system_info_collector.py          # System info collection
│   ├── monitor_resources.py              # Resource monitoring
│   └── profile_server.py                 # Server-side profiling
├── webapp/
│   ├── server.js                    # Express server
│   ├── routes/results.js            # REST API
│   ├── config/mongodb.js            # MongoDB connection
│   └── public/                      # Frontend (HTML/CSS/JS + Chart.js)
├── config/
│   ├── benchmark_config.ini.example # Primary config template
│   ├── config.properties.example    # Java JDBC connections
│   └── config.example.json          # JSON test configuration
├── docs/                            # Feature documentation
├── pom.xml                          # Maven build (Java 11)
├── CLAUDE.md                        # AI assistant guidance
└── README.md                        # This file
```

## Configuration

### `config/benchmark_config.ini` (Primary - for Docker testing)

```ini
[oracle]
system_password = YourOraclePasswordHere
host = localhost
port = 1521

[mongodb]
host = localhost
port = 27017

[postgresql]
user = postgres
host = localhost
port = 5432

[results_storage]
mongodb_connection_string = mongodb+srv://user:pass@cluster.mongodb.net/benchmark_db
database_name = benchmark_results
collection_name = test_runs
```

### `config.properties` (For direct Java execution)

```properties
mongodb.connection.string=mongodb://localhost:27017
postgresql.connection.string=jdbc:postgresql://localhost:5432/test?user=postgres&password=PASSWORD
oracle.connection.string=jdbc:oracle:thin:system/PASSWORD@localhost:1521/FREEPDB1
```

### JSON Config File (Alternative to CLI flags)

```json
{
  "database": "mongodb",
  "numDocs": 10000,
  "numAttrs": 10,
  "batchSize": 100,
  "numLinks": 10,
  "numRuns": 3,
  "sizes": [100, 1000],
  "runQueryTest": true,
  "runIndexTest": false,
  "useRealisticData": false,
  "useMultivalueIndex": false
}
```

## Known Issues

### Oracle 23AI Duality View Array Bug

Oracle 23AI Free (23.0.0.0.0) incorrectly treats array values as globally unique during insertion through Duality Views, causing silent data loss. Use `-d` flag for direct table insertion as a workaround. See `src/test/java/com/mongodb/TestDualityView.java` for reproduction.

### Oracle Not Dockerized

Oracle databases require native installation and are not managed by the Docker test scripts. The Docker testing covers MongoDB, DocumentDB, PostgreSQL, YugabyteDB, and CockroachDB.

## Features Status

| Feature | Status | Notes |
|---------|--------|-------|
| Docker-based testing | **Complete** | MongoDB, DocumentDB, PostgreSQL, YugabyteDB, CockroachDB |
| Results storage to MongoDB | **Complete** | Full metadata, auto-indexed, two storage paths |
| Webapp visualization | **Functional** | Charts, filtering, export work; UI is basic, could use polish |
| Data validation | **Recently added** | Count + sample verification works; results not yet stored in DB |
| Resource monitoring | **Complete** | CPU, disk IOPS, I/O wait per test |
| Flame graph profiling | **Complete** | Client-side (async-profiler) and server-side (perf) |

### Areas for Improvement

- **Webapp**: Needs comparison views between test runs, historical trends, drill-down detail views, and better chart labeling
- **Validation**: Results should be stored structurally in the MongoDB results database, not just printed to stdout. Could verify full payload content, not just document existence.
- **Results schema**: `test.sh` and `run_article_benchmarks_docker.py` produce slightly different document schemas - should be unified
- **Oracle Docker**: Oracle databases are not yet containerized like the other databases
- **No Docker Compose**: Container management is done through imperative `docker run` commands rather than a declarative compose file

## License

Apache License 2.0. See `LICENSE` for details.

## Author

Rick Houlihan
