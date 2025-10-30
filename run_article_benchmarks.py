#!/usr/bin/env python3
"""
Benchmark script to replicate tests from LinkedIn article:
"Comparing Document Data Options for Generative AI"

Tests:
- Single attribute: 10B, 200B, 1000B, 2000B, 4000B
- Multi attribute: 10×1B, 10×20B, 50×20B, 100×20B, 200×20B
- 10,000 documents per test
- 3 runs (best time reported)
"""

import subprocess
import json
import re
from datetime import datetime
import sys
import time

JAR_PATH = "target/insertTest-1.0-jar-with-dependencies.jar"
NUM_DOCS = 10000
NUM_RUNS = 3
BATCH_SIZE = 500

# Test configurations matching the article
SINGLE_ATTR_TESTS = [
    {"size": 10, "attrs": 1, "desc": "10B single attribute"},
    {"size": 200, "attrs": 1, "desc": "200B single attribute"},
    {"size": 1000, "attrs": 1, "desc": "1000B single attribute"},
    {"size": 2000, "attrs": 1, "desc": "2000B single attribute"},
    {"size": 4000, "attrs": 1, "desc": "4000B single attribute"},
]

MULTI_ATTR_TESTS = [
    {"size": 10, "attrs": 10, "desc": "10 attributes × 1B = 10B"},
    {"size": 200, "attrs": 10, "desc": "10 attributes × 20B = 200B"},
    {"size": 1000, "attrs": 50, "desc": "50 attributes × 20B = 1000B"},
    {"size": 2000, "attrs": 100, "desc": "100 attributes × 20B = 2000B"},
    {"size": 4000, "attrs": 200, "desc": "200 attributes × 20B = 4000B"},
]

# Databases to test - with service management info
DATABASES = [
    {"name": "MongoDB (BSON)", "key": "mongodb", "flags": "", "service": "mongod", "db_type": "mongodb"},
    {"name": "PostgreSQL (JSON)", "key": "postgresql_json", "flags": "-p", "service": "postgresql-17", "db_type": "postgresql"},
    {"name": "PostgreSQL (JSONB)", "key": "postgresql_jsonb", "flags": "-p -j", "service": "postgresql-17", "db_type": "postgresql"},
    {"name": "Oracle JCT (no index)", "key": "oracle_no_index", "flags": "-oj", "service": "oracle-free-26ai", "db_type": "oracle"},
    {"name": "Oracle JCT (with index)", "key": "oracle_with_index", "flags": "-oj -i", "service": "oracle-free-26ai", "db_type": "oracle"},
]

def stop_all_databases():
    """Stop all databases before starting."""
    print("Stopping all databases...")
    for service in ["mongod", "postgresql-17", "oracle-free-26ai"]:
        subprocess.run(f"sudo systemctl stop {service}", shell=True, capture_output=True)
    time.sleep(2)
    print("✓ All databases stopped\n")

def start_database(service_name, db_type):
    """Start a database service and wait for it to be ready."""
    print(f"  Starting {service_name}...", end=" ", flush=True)
    result = subprocess.run(f"sudo systemctl start {service_name}", shell=True, capture_output=True)

    if result.returncode != 0:
        print(f"✗ Failed to start")
        return False

    # Wait for database to be ready
    max_wait = 30
    wait_interval = 2

    for i in range(max_wait // wait_interval):
        time.sleep(wait_interval)

        if db_type == "mongodb":
            check = subprocess.run("mongosh --quiet --eval 'db.adminCommand(\"ping\").ok' 2>&1",
                                   shell=True, capture_output=True, text=True)
            if "1" in check.stdout:
                print(f"✓ Ready (took {(i+1)*wait_interval}s)")
                return True

        elif db_type == "postgresql":
            check = subprocess.run("sudo -u postgres psql -c 'SELECT 1;' 2>&1",
                                   shell=True, capture_output=True, text=True)
            if check.returncode == 0:
                print(f"✓ Ready (took {(i+1)*wait_interval}s)")
                return True

        elif db_type == "oracle":
            # Check for ora_pmon process indicating database is running
            check = subprocess.run("ps aux | grep ora_pmon | grep -v grep",
                                   shell=True, capture_output=True, text=True)
            if check.stdout.strip():
                print(f"✓ Ready (took {(i+1)*wait_interval}s)")
                return True

    print(f"✗ Timeout waiting for database")
    return False

def stop_database(service_name):
    """Stop a database service."""
    print(f"  Stopping {service_name}...", end=" ", flush=True)
    subprocess.run(f"sudo systemctl stop {service_name}", shell=True, capture_output=True)
    time.sleep(2)
    print("✓ Stopped")

def run_benchmark(db_flags, size, attrs, num_docs, num_runs, batch_size):
    """Run a single benchmark test."""
    cmd = f"java -jar {JAR_PATH} {db_flags} -s {size} -n {attrs} -r {num_runs} -b {batch_size} {num_docs}"

    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=300
        )

        # Parse result for "Best time to insert"
        pattern = rf"Best time to insert {num_docs} documents with {size}B payload in {attrs} attributes? into indexed: (\d+)ms"
        match = re.search(pattern, result.stdout)

        if match:
            time_ms = int(match.group(1))
            throughput = round(num_docs / (time_ms / 1000), 2)
            return {
                "success": True,
                "time_ms": time_ms,
                "throughput": throughput,
                "size": size,
                "attrs": attrs,
                "num_docs": num_docs
            }
        else:
            # Try alternative pattern with "attribute" singular/plural
            alt_pattern = rf"Best time to insert {num_docs} documents with {size}B payload in \d+ attributes? into indexed: (\d+)ms"
            alt_match = re.search(alt_pattern, result.stdout)
            if alt_match:
                time_ms = int(alt_match.group(1))
                throughput = round(num_docs / (time_ms / 1000), 2)
                return {
                    "success": True,
                    "time_ms": time_ms,
                    "throughput": throughput,
                    "size": size,
                    "attrs": attrs,
                    "num_docs": num_docs
                }

            print(f"    Warning: Could not parse output")
            return {"success": False, "error": "Could not parse output"}

    except subprocess.TimeoutExpired:
        print(f"    ERROR: Timeout after 300 seconds")
        return {"success": False, "error": "Timeout"}
    except Exception as e:
        print(f"    ERROR: {str(e)}")
        return {"success": False, "error": str(e)}

def run_test_suite(test_configs, test_type):
    """Run a complete test suite (single or multi attribute)."""
    print(f"\n{'='*80}")
    print(f"{test_type.upper()} ATTRIBUTE TESTS")
    print(f"{'='*80}")

    results = {}
    current_service = None

    for db in DATABASES:
        print(f"\n--- {db['name']} ---")

        # Start database if different from current
        if db['service'] != current_service:
            # Stop previous database if any
            if current_service:
                stop_database(current_service)

            # Start new database
            if not start_database(db['service'], db['db_type']):
                print(f"  ERROR: Failed to start {db['service']}, skipping tests")
                results[db['key']] = [{"success": False, "error": "Database failed to start"} for _ in test_configs]
                continue

            current_service = db['service']

        results[db['key']] = []

        for test in test_configs:
            print(f"  Testing: {test['desc']}...", end=" ", flush=True)

            result = run_benchmark(
                db['flags'],
                test['size'],
                test['attrs'],
                NUM_DOCS,
                NUM_RUNS,
                BATCH_SIZE
            )

            if result['success']:
                results[db['key']].append(result)
                print(f"✓ {result['time_ms']}ms ({result['throughput']:,.0f} docs/sec)")
            else:
                results[db['key']].append(result)
                print(f"✗ {result.get('error', 'Failed')}")

    # Stop the last database
    if current_service:
        stop_database(current_service)

    return results

def generate_summary_table(single_results, multi_results):
    """Generate a summary comparison table."""
    print(f"\n{'='*80}")
    print("SUMMARY: Single-Attribute Results (10K documents)")
    print(f"{'='*80}")
    print(f"{'Payload':<12} {'MongoDB':<12} {'PG-JSON':<12} {'PG-JSONB':<12} {'Oracle':<12} {'Oracle+Idx':<12}")
    print("-" * 80)

    for i, test in enumerate(SINGLE_ATTR_TESTS):
        row = f"{test['size']}B"
        for db_key in ['mongodb', 'postgresql_json', 'postgresql_jsonb', 'oracle_no_index', 'oracle_with_index']:
            if db_key in single_results and i < len(single_results[db_key]):
                result = single_results[db_key][i]
                if result['success']:
                    row += f"  {result['time_ms']:>8}ms"
                else:
                    row += f"  {'FAIL':>8}  "
            else:
                row += f"  {'N/A':>8}  "
        print(row)

    print(f"\n{'='*80}")
    print("SUMMARY: Multi-Attribute Results (10K documents)")
    print(f"{'='*80}")
    print(f"{'Config':<20} {'MongoDB':<12} {'PG-JSON':<12} {'PG-JSONB':<12} {'Oracle':<12} {'Oracle+Idx':<12}")
    print("-" * 80)

    for i, test in enumerate(MULTI_ATTR_TESTS):
        row = f"{test['attrs']}×{test['size']//test['attrs']}B"
        for db_key in ['mongodb', 'postgresql_json', 'postgresql_jsonb', 'oracle_no_index', 'oracle_with_index']:
            if db_key in multi_results and i < len(multi_results[db_key]):
                result = multi_results[db_key][i]
                if result['success']:
                    row += f"  {result['time_ms']:>8}ms"
                else:
                    row += f"  {'FAIL':>8}  "
            else:
                row += f"  {'N/A':>8}  "
        print(row)

def main():
    """Main execution."""
    print(f"\n{'='*80}")
    print("BENCHMARK: Replicating LinkedIn Article Tests")
    print(f"{'='*80}")
    print(f"Document count: {NUM_DOCS:,}")
    print(f"Runs per test: {NUM_RUNS} (best time reported)")
    print(f"Batch size: {BATCH_SIZE}")
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Stop all databases first to ensure clean start
    stop_all_databases()

    # Run single-attribute tests
    single_results = run_test_suite(SINGLE_ATTR_TESTS, "SINGLE")

    # Run multi-attribute tests
    multi_results = run_test_suite(MULTI_ATTR_TESTS, "MULTI")

    # Generate summary
    generate_summary_table(single_results, multi_results)

    # Save results to JSON
    output_data = {
        "timestamp": datetime.now().isoformat(),
        "configuration": {
            "documents": NUM_DOCS,
            "runs": NUM_RUNS,
            "batch_size": BATCH_SIZE
        },
        "single_attribute": single_results,
        "multi_attribute": multi_results
    }

    output_file = "article_benchmark_results.json"
    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)

    print(f"\n{'='*80}")
    print(f"✓ Results saved to: {output_file}")
    print(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    main()
