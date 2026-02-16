# Quickstart Guide

Run all database benchmarks, store results to an external MongoDB, and view them in the web dashboard.

## Prerequisites

| Tool | Version | Check |
|------|---------|-------|
| Java | 11+ | `java -version` |
| Maven | 3.x | `mvn -version` |
| Docker | 20+ | `docker --version` |
| Python | 3.8+ | `python3 --version` |
| Node.js | 18+ | `node --version` |
| npm | 8+ | `npm --version` |

## Step 1: Clone and Build

```bash
git clone https://github.com/rhoulihan/BSON-JSON-bakeoff.git
cd BSON-JSON-bakeoff
mvn clean package
```

This produces `target/insertTest-1.0-jar-with-dependencies.jar`.

## Step 2: Install Python Dependencies

```bash
pip3 install pymongo psutil
```

## Step 3: Configure Results Storage

You need a MongoDB instance to store results. This can be MongoDB Atlas (free tier works) or any MongoDB 5.0+.

```bash
cp config/benchmark_config.ini.example config/benchmark_config.ini
```

Edit `config/benchmark_config.ini` and set your MongoDB connection string:

```ini
[results_storage]
mongodb_connection_string = mongodb+srv://YOUR_USER:YOUR_PASS@YOUR_CLUSTER.mongodb.net/benchmark_db
database_name = benchmark_results
collection_name = test_runs
```

> **Using MongoDB Atlas free tier:** Create a free cluster at [cloud.mongodb.com](https://cloud.mongodb.com), create a database user, whitelist your IP, and copy the connection string.
>
> **Using a local MongoDB:** If you have MongoDB running locally on the default port, use:
> ```ini
> mongodb_connection_string = mongodb://localhost:27017
> ```

## Step 4: Run All Benchmarks

### Option A: Shell Script (Simple)

Runs all 5 databases sequentially with Docker:

```bash
bash scripts/test.sh -i -q 10 -s 100,1000 -v -r 3 -b 500 10000
```

**What this does:**
- `-i` — Tests with indexes
- `-q 10` — Runs query tests (10 array links per document)
- `-s 100,1000` — Tests 100B and 1000B payloads
- `-v` — Validates data integrity after each test
- `-r 3` — 3 runs per test, keeps best time
- `-b 500` — Batch size of 500
- `10000` — 10,000 documents per test

**Databases tested (in order):** MongoDB, DocumentDB, PostgreSQL, YugabyteDB, CockroachDB

Each database container is started, benchmarked, results stored to your MongoDB, then the container is removed.

### Option B: Python Orchestration (Full Featured)

More control, per-test database isolation, resource monitoring:

```bash
python3 scripts/run_article_benchmarks_docker.py \
  --queries \
  --validate \
  --monitor \
  --num-docs 10000 \
  --num-runs 3 \
  --batch-size 500
```

To test specific databases only:
```bash
python3 scripts/run_article_benchmarks_docker.py \
  --mongodb --postgresql \
  --queries --validate
```

For the full comparison (indexed + non-indexed):
```bash
python3 scripts/run_article_benchmarks_docker.py --full-comparison --validate
```

### Option C: Quick Smoke Test (Fast, ~2 minutes)

To verify everything works before committing to a full run:

```bash
bash scripts/test.sh -i -q 10 -s 100 -v -r 1 -b 100 500
```

This runs 500 documents, 1 run, 100B payload — enough to verify each database connects and produces results.

## Step 5: Start the Web Dashboard

```bash
cd webapp
npm install
```

Create a `.env` file with the **same** MongoDB connection string:

```bash
cat > .env << 'EOF'
MONGODB_CONNECTION_STRING=mongodb+srv://YOUR_USER:YOUR_PASS@YOUR_CLUSTER.mongodb.net/benchmark_db
MONGODB_DATABASE_NAME=benchmark_results
MONGODB_COLLECTION_NAME=test_runs
EOF
```

Start the server:

```bash
npm start
```

Open **http://localhost:3000** in your browser.

### What You'll See

- **Insertion Performance chart** — Time (ms) by payload size, one line per database/test run
- **Query Performance chart** — Query time by payload size
- **Throughput chart** — Documents/sec by payload size
- **Results table** — Every individual test result with timestamp, database, version, config, and timings

### Filtering Results

Use the dropdowns to filter by:
- **Database Type** — mongodb, postgresql, documentdb, yugabytedb, cockroachdb
- **Database Version** — Specific versions from your test runs
- **Test Type** — Single attribute or multi attribute
- **Date Range** — Time window for results

Click **Export CSV** to download filtered results for further analysis.

## Step 6: Verify Results Storage

After running benchmarks, verify data reached MongoDB:

```bash
# Check via the webapp API
curl -s http://localhost:3000/api/results?limit=5 | python3 -m json.tool | head -30

# Check available database types and versions
curl -s http://localhost:3000/api/results/meta/versions | python3 -m json.tool

# Get aggregated comparison
curl -s http://localhost:3000/api/results/meta/comparison | python3 -m json.tool
```

## All-in-One Script

Copy and run this entire block to go from zero to results:

```bash
# Build
mvn clean package

# Install Python deps
pip3 install pymongo psutil

# Configure (edit the connection string!)
cp config/benchmark_config.ini.example config/benchmark_config.ini
echo ">>> Edit config/benchmark_config.ini with your MongoDB connection string, then press Enter"
read

# Run benchmarks (quick smoke test first)
bash scripts/test.sh -i -q 10 -s 100,1000 -v -r 1 -b 100 2000

# Start webapp
cd webapp && npm install
echo "MONGODB_CONNECTION_STRING=YOUR_CONNECTION_STRING_HERE" > .env
echo ">>> Edit webapp/.env with the same MongoDB connection string, then press Enter"
read
npm start &
cd ..

echo ">>> Dashboard running at http://localhost:3000"
echo ">>> Run a full benchmark with: bash scripts/test.sh -i -q 10 -s 100,1000,4000 -v -r 3 -b 500 10000"
```

## Troubleshooting

### "Could not load config.properties file"
The Docker scripts auto-generate `config.properties` if missing. If you see this running Java directly, create it:
```bash
cp config/config.properties.example config.properties
```
Edit `config.properties` and set `password` for PostgreSQL (matches Docker default).

### "pymongo not found"
```bash
pip3 install pymongo
```
If no pip3, install Python packages first: `sudo apt install python3-pip` or equivalent.

### DocumentDB fails to start
DocumentDB's local Docker image is slower to initialize. The scripts include extended wait times. If it still fails, it won't block other databases — the suite continues.

### YugabyteDB hangs
Fixed in recent commits. Make sure you're on the latest `main`. YugabyteDB needs extra startup time; the scripts now handle this with timeouts.

### Webapp shows "No results found"
- Verify the `.env` connection string matches `benchmark_config.ini`
- Check the database/collection names match
- Confirm benchmarks completed successfully (check for "Stored N test results to MongoDB" in output)
- Try: `curl http://localhost:3000/api/results/meta/versions` — if this returns empty arrays, no data has been stored yet

### Docker permission errors
```bash
sudo usermod -aG docker $USER
# Then log out and back in
```
