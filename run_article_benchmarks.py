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
import argparse
import random

JAR_PATH = "target/insertTest-1.0-jar-with-dependencies.jar"
NUM_DOCS = 10000
NUM_RUNS = 3
BATCH_SIZE = 500
QUERY_LINKS = 10  # Number of array elements for query tests

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

# Databases to test - with service management info (all using indexes + realistic data)
DATABASES = [
    {"name": "MongoDB (BSON)", "key": "mongodb", "flags": "-i -rd", "service": "mongod", "db_type": "mongodb"},
    {"name": "PostgreSQL (JSON)", "key": "postgresql_json", "flags": "-p -i -rd", "service": "postgresql-17", "db_type": "postgresql"},
    {"name": "PostgreSQL (JSONB)", "key": "postgresql_jsonb", "flags": "-p -j -i -rd", "service": "postgresql-17", "db_type": "postgresql"},
    {"name": "Oracle JCT", "key": "oracle_jct", "flags": "-oj -i -mv -rd", "service": "oracle-free-26ai", "db_type": "oracle"},
]

def stop_all_databases():
    """Stop all databases before starting."""
    print("Stopping all databases...")
    for service in ["mongod", "postgresql-17", "oracle-free-26ai"]:
        subprocess.run(f"sudo systemctl stop {service}", shell=True, capture_output=True)
    time.sleep(2)
    print("✓ All databases stopped\n")

def restart_database_with_cache_clear(service_name, db_type):
    """Restart a database and clear OS caches to eliminate warmup effects."""
    print(f"  Restarting {service_name} with cache clear...", end=" ", flush=True)

    # Stop the database
    subprocess.run(f"sudo systemctl stop {service_name}", shell=True, capture_output=True)
    time.sleep(2)

    # Clear OS page cache, dentries and inodes (requires sudo)
    # This is critical to eliminate cache warmup effects
    subprocess.run("sudo sync", shell=True, capture_output=True)
    subprocess.run("echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null", shell=True, capture_output=True)
    time.sleep(1)

    # Start the database
    result = subprocess.run(f"sudo systemctl start {service_name}", shell=True, capture_output=True)

    if result.returncode != 0:
        print(f"✗ Failed to restart")
        return False

    # Wait for database to be ready
    max_wait = 120 if db_type == "oracle" else 30
    wait_interval = 3 if db_type == "oracle" else 2

    for i in range(max_wait // wait_interval):
        time.sleep(wait_interval)

        if db_type == "mongodb":
            check = subprocess.run("mongosh --quiet --eval 'db.adminCommand(\"ping\").ok' 2>&1",
                                   shell=True, capture_output=True, text=True)
            if "1" in check.stdout:
                print(f"✓ Ready (took {(i+1)*wait_interval}s)")
                return True

        elif db_type == "oracle":
            pmon_check = subprocess.run("ps -ef | grep db_pmon_FREE | grep -v grep",
                                       shell=True, capture_output=True, text=True)
            if pmon_check.stdout.strip():
                print(f"✓ Ready (took {(i+1)*wait_interval}s)")
                return True

    print(f"✗ Timeout waiting for database (waited {max_wait}s)")
    return False

def start_database(service_name, db_type):
    """Start a database service and wait for it to be ready."""
    print(f"  Starting {service_name}...", end=" ", flush=True)
    result = subprocess.run(f"sudo systemctl start {service_name}", shell=True, capture_output=True)

    if result.returncode != 0:
        print(f"✗ Failed to start")
        return False

    # Wait for database to be ready - Oracle needs more time
    max_wait = 120 if db_type == "oracle" else 30  # Oracle can take 60-90 seconds
    wait_interval = 3 if db_type == "oracle" else 2

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
            # Check db_pmon process (Oracle 23ai uses db_ prefix instead of ora_)
            # If pmon is running, the database is ready for connections
            pmon_check = subprocess.run("ps -ef | grep db_pmon_FREE | grep -v grep",
                                       shell=True, capture_output=True, text=True)

            if pmon_check.stdout.strip():
                print(f"✓ Ready (took {(i+1)*wait_interval}s)")
                return True

    print(f"✗ Timeout waiting for database (waited {max_wait}s)")
    return False

def stop_database(service_name):
    """Stop a database service."""
    print(f"  Stopping {service_name}...", end=" ", flush=True)
    subprocess.run(f"sudo systemctl stop {service_name}", shell=True, capture_output=True)
    time.sleep(2)
    print("✓ Stopped")

def run_benchmark(db_flags, size, attrs, num_docs, num_runs, batch_size, query_links=None):
    """Run a single benchmark test, optionally with query tests."""
    cmd = f"java -jar {JAR_PATH} {db_flags} -s {size} -n {attrs} -r {num_runs} -b {batch_size}"

    # Add query test flag if specified
    if query_links is not None:
        cmd += f" -q {query_links}"

    cmd += f" {num_docs}"

    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=900  # 15 minutes per test
        )

        # Parse result for "Best time to insert"
        pattern = rf"Best time to insert {num_docs} documents with {size}B payload in {attrs} attributes? into indexed: (\d+)ms"
        match = re.search(pattern, result.stdout)

        response = {
            "success": False,
            "size": size,
            "attrs": attrs,
            "num_docs": num_docs
        }

        if match:
            time_ms = int(match.group(1))
            throughput = round(num_docs / (time_ms / 1000), 2)
            response.update({
                "success": True,
                "time_ms": time_ms,
                "throughput": throughput
            })
        else:
            # Try alternative pattern with "attribute" singular/plural
            alt_pattern = rf"Best time to insert {num_docs} documents with {size}B payload in \d+ attributes? into indexed: (\d+)ms"
            alt_match = re.search(alt_pattern, result.stdout)
            if alt_match:
                time_ms = int(alt_match.group(1))
                throughput = round(num_docs / (time_ms / 1000), 2)
                response.update({
                    "success": True,
                    "time_ms": time_ms,
                    "throughput": throughput
                })
            else:
                print(f"    Warning: Could not parse output")
                return {"success": False, "error": "Could not parse output"}

        # If query tests were requested, parse query results
        if query_links is not None:
            # Parse query time: "Best query time for N ID's with M element link arrays...: XXXms"
            query_pattern = rf"Best query time for (\d+) ID's with {query_links} element link arrays.*?: (\d+)ms"
            query_match = re.search(query_pattern, result.stdout)

            if query_match:
                queries_executed = int(query_match.group(1))
                query_time_ms = int(query_match.group(2))
                query_throughput = round(queries_executed / (query_time_ms / 1000), 2)
                response.update({
                    "query_time_ms": query_time_ms,
                    "query_throughput": query_throughput,
                    "queries_executed": queries_executed,
                    "query_links": query_links
                })
            else:
                # Query test may have failed or not been executed
                response["query_time_ms"] = None
                response["query_error"] = "Could not parse query results"

        return response

    except subprocess.TimeoutExpired:
        print(f"    ERROR: Timeout after 900 seconds")
        return {"success": False, "error": "Timeout"}
    except Exception as e:
        print(f"    ERROR: {str(e)}")
        return {"success": False, "error": str(e)}

def run_test_suite(test_configs, test_type, enable_queries=False, restart_per_test=False):
    """Run a complete test suite (single or multi attribute).

    Args:
        test_configs: List of test configurations
        test_type: Description of test type
        enable_queries: Whether to run query tests
        restart_per_test: If True, restart database before EACH test for maximum isolation
    """
    print(f"\n{'='*80}")
    print(f"{test_type.upper()} ATTRIBUTE TESTS" + (" WITH QUERIES" if enable_queries else ""))
    print(f"{'='*80}")

    results = {}

    if restart_per_test:
        # MAXIMUM ISOLATION MODE: Restart database before each individual test
        # Initialize results dict
        for db in DATABASES:
            results[db['key']] = []

        # Outer loop: iterate through tests
        for test_idx, test in enumerate(test_configs):
            # Inner loop: run this test on each database
            for db in DATABASES:
                if test_idx == 0:
                    # Print database header only for first test
                    print(f"\n--- {db['name']} ---")

                # Start database for this specific test
                if not start_database(db['service'], db['db_type']):
                    print(f"  Testing: {test['desc']}... ✗ Database failed to start")
                    results[db['key']].append({"success": False, "error": "Database failed to start"})
                    continue

                # Run the test
                print(f"  Testing: {test['desc']}...", end=" ", flush=True)

                result = run_benchmark(
                    db['flags'],
                    test['size'],
                    test['attrs'],
                    NUM_DOCS,
                    NUM_RUNS,
                    BATCH_SIZE,
                    query_links=QUERY_LINKS if enable_queries else None
                )

                if result['success']:
                    output = f"✓ {result['time_ms']}ms ({result['throughput']:,.0f} docs/sec)"
                    if enable_queries and 'query_time_ms' in result and result['query_time_ms']:
                        output += f" | Query: {result['query_time_ms']}ms ({result['query_throughput']:,.0f} queries/sec)"
                    results[db['key']].append(result)
                    print(output)
                else:
                    results[db['key']].append(result)
                    print(f"✗ {result.get('error', 'Failed')}")

                # Stop database immediately after test completes
                stop_database(db['service'])

    else:
        # ORIGINAL MODE: Start database once, run all tests, then stop
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
                    BATCH_SIZE,
                    query_links=QUERY_LINKS if enable_queries else None
                )

                if result['success']:
                    output = f"✓ {result['time_ms']}ms ({result['throughput']:,.0f} docs/sec)"
                    if enable_queries and 'query_time_ms' in result and result['query_time_ms']:
                        output += f" | Query: {result['query_time_ms']}ms ({result['query_throughput']:,.0f} queries/sec)"
                    results[db['key']].append(result)
                    print(output)
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
    print("SUMMARY: Single-Attribute Results (10K documents) - All with indexes")
    print(f"{'='*80}")
    print(f"{'Payload':<12} {'MongoDB':<12} {'PG-JSON':<12} {'PG-JSONB':<12} {'Oracle JCT':<12}")
    print("-" * 80)

    for i, test in enumerate(SINGLE_ATTR_TESTS):
        row = f"{test['size']}B"
        for db_key in ['mongodb', 'postgresql_json', 'postgresql_jsonb', 'oracle_jct']:
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
    print("SUMMARY: Multi-Attribute Results (10K documents) - All with indexes")
    print(f"{'='*80}")
    print(f"{'Config':<20} {'MongoDB':<12} {'PG-JSON':<12} {'PG-JSONB':<12} {'Oracle JCT':<12}")
    print("-" * 80)

    for i, test in enumerate(MULTI_ATTR_TESTS):
        row = f"{test['attrs']}×{test['size']//test['attrs']}B"
        for db_key in ['mongodb', 'postgresql_json', 'postgresql_jsonb', 'oracle_jct']:
            if db_key in multi_results and i < len(multi_results[db_key]):
                result = multi_results[db_key][i]
                if result['success']:
                    row += f"  {result['time_ms']:>8}ms"
                else:
                    row += f"  {'FAIL':>8}  "
            else:
                row += f"  {'N/A':>8}  "
        print(row)

def run_full_comparison_suite(args):
    """
    Run complete benchmark suite: first without indexes (insert-only),
    then with indexes and queries for comprehensive comparison.
    """
    global NUM_DOCS, NUM_RUNS, BATCH_SIZE, QUERY_LINKS, DATABASES
    import copy

    # Save original database configurations
    original_databases = copy.deepcopy(DATABASES)

    # Determine test order (randomize if requested)
    run_index_first = False
    if args.randomize_order:
        run_index_first = random.choice([True, False])
        print(f"NOTE: Test order randomized - running {'WITH INDEX' if run_index_first else 'NO INDEX'} tests first\n")

    print(f"\n{'='*80}")
    print("FULL COMPARISON BENCHMARK: Insert-Only + Indexed with Queries")
    print(f"{'='*80}")
    print(f"Document count: {NUM_DOCS:,}")
    print(f"Runs per test: {NUM_RUNS} (best time reported)")
    print(f"Batch size: {BATCH_SIZE}")
    print(f"Query tests: {QUERY_LINKS} links per document (indexed tests only)")
    print(f"Randomized order: {args.randomize_order}")
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Stop all databases first
    stop_all_databases()

    # ========== PART 1: NO-INDEX TESTS ==========
    print(f"\n{'='*80}")
    print("PART 1: INSERT-ONLY TESTS (NO INDEXES)")
    print(f"{'='*80}\n")

    # Remove index flags from all databases
    for db in DATABASES:
        db['flags'] = db['flags'].replace(' -i', '').replace('-i ', '').replace(' -mv', '').replace('-mv ', '')

    # Run tests without indexes - restart database before each test for maximum isolation
    single_results_noindex = run_test_suite(SINGLE_ATTR_TESTS, "SINGLE ATTRIBUTE (NO INDEX)", enable_queries=False, restart_per_test=True)
    multi_results_noindex = run_test_suite(MULTI_ATTR_TESTS, "MULTI ATTRIBUTE (NO INDEX)", enable_queries=False, restart_per_test=True)

    # ========== PART 2: WITH-INDEX TESTS ==========
    print(f"\n{'='*80}")
    print("PART 2: INDEXED TESTS WITH QUERIES")
    print(f"{'='*80}\n")

    # Restore original database configurations (with indexes)
    DATABASES = copy.deepcopy(original_databases)

    # Stop all databases and restart MongoDB/Oracle with cache clear to eliminate warmup effects
    print("Restarting databases with cache clear to eliminate warmup effects...")
    stop_all_databases()

    # Restart MongoDB with cache clear for fair comparison
    for db in DATABASES:
        if db['db_type'] == 'mongodb':
            if not restart_database_with_cache_clear(db['service'], db['db_type']):
                print(f"  ERROR: Failed to restart {db['service']}")
            subprocess.run(f"sudo systemctl stop {db['service']}", shell=True, capture_output=True)
            time.sleep(1)
            break

    # Restart Oracle with cache clear for fair comparison
    for db in DATABASES:
        if db['db_type'] == 'oracle':
            if not restart_database_with_cache_clear(db['service'], db['db_type']):
                print(f"  ERROR: Failed to restart {db['service']}")
            subprocess.run(f"sudo systemctl stop {db['service']}", shell=True, capture_output=True)
            time.sleep(1)
            break

    print()

    # Run tests with indexes and queries - restart database before each test for maximum isolation
    single_results_indexed = run_test_suite(SINGLE_ATTR_TESTS, "SINGLE ATTRIBUTE (WITH INDEX)", enable_queries=True, restart_per_test=True)
    multi_results_indexed = run_test_suite(MULTI_ATTR_TESTS, "MULTI ATTRIBUTE (WITH INDEX)", enable_queries=True, restart_per_test=True)

    # ========== GENERATE COMPARISON SUMMARY ==========
    print(f"\n{'='*80}")
    print("COMPARISON SUMMARY")
    print(f"{'='*80}\n")

    generate_comparison_summary(single_results_noindex, single_results_indexed,
                               multi_results_noindex, multi_results_indexed)

    # Save comprehensive results
    output_data = {
        "timestamp": datetime.now().isoformat(),
        "configuration": {
            "documents": NUM_DOCS,
            "runs": NUM_RUNS,
            "batch_size": BATCH_SIZE,
            "query_links": QUERY_LINKS
        },
        "no_index": {
            "single_attribute": single_results_noindex,
            "multi_attribute": multi_results_noindex
        },
        "with_index": {
            "single_attribute": single_results_indexed,
            "multi_attribute": multi_results_indexed
        }
    }

    with open("full_comparison_results.json", "w") as f:
        json.dump(output_data, f, indent=2)

    print(f"\n{'='*80}")
    print(f"✓ Full comparison results saved to: full_comparison_results.json")
    print(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}\n")

def generate_comparison_summary(single_noindex, single_indexed, multi_noindex, multi_indexed):
    """Generate side-by-side comparison tables."""
    print("Single-Attribute Comparison (Insert Times):")
    print(f"{'Payload':<10} {'No Index':<15} {'With Index':<15} {'Difference'}")
    print("-" * 60)

    for db_key in single_noindex.keys():
        if single_noindex[db_key] and single_indexed.get(db_key):
            print(f"\n{db_key}:")
            for i, result in enumerate(single_noindex[db_key]):
                if result['success'] and i < len(single_indexed[db_key]) and single_indexed[db_key][i]['success']:
                    noindex_time = result['time_ms']
                    indexed_time = single_indexed[db_key][i]['time_ms']
                    diff = ((indexed_time - noindex_time) / noindex_time) * 100
                    payload = SINGLE_ATTR_TESTS[i]['desc']
                    print(f"  {payload:<10} {noindex_time:>6}ms       {indexed_time:>6}ms       {diff:+6.1f}%")

def main():
    """Main execution."""
    global NUM_DOCS, NUM_RUNS, BATCH_SIZE, QUERY_LINKS, DATABASES

    parser = argparse.ArgumentParser(description='Run benchmark tests replicating LinkedIn article')
    parser.add_argument('--queries', '-q', action='store_true',
                        help=f'Include query tests with {QUERY_LINKS} links per document')
    parser.add_argument('--no-index', action='store_true',
                        help='Run insert-only tests without indexes (disables --queries)')
    parser.add_argument('--full-comparison', action='store_true',
                        help='Run both no-index and with-index tests in sequence for complete comparison')
    parser.add_argument('--randomize-order', action='store_true',
                        help='Randomize test execution order (with-index first or no-index first) to eliminate execution order bias')
    parser.add_argument('--mongodb', action='store_true', help='Run MongoDB tests')
    parser.add_argument('--oracle', action='store_true', help='Run Oracle JCT tests')
    parser.add_argument('--postgresql', action='store_true', help='Run PostgreSQL tests (JSON and JSONB)')
    parser.add_argument('--batch-size', '-b', type=int, default=BATCH_SIZE,
                        help=f'Batch size for insertions (default: {BATCH_SIZE})')
    parser.add_argument('--num-docs', '-n', type=int, default=NUM_DOCS,
                        help=f'Number of documents per test (default: {NUM_DOCS})')
    parser.add_argument('--num-runs', '-r', type=int, default=NUM_RUNS,
                        help=f'Number of runs per test (default: {NUM_RUNS})')
    parser.add_argument('--query-links', type=int, default=QUERY_LINKS,
                        help=f'Number of array elements for query tests (default: {QUERY_LINKS})')
    args = parser.parse_args()

    # Use command-line values
    NUM_DOCS = args.num_docs
    NUM_RUNS = args.num_runs
    BATCH_SIZE = args.batch_size
    QUERY_LINKS = args.query_links

    # Filter databases based on arguments (if no args, run all)
    if args.mongodb or args.oracle or args.postgresql:
        enabled_databases = []
        for db in DATABASES:
            if (args.mongodb and db['db_type'] == 'mongodb') or \
               (args.oracle and db['db_type'] == 'oracle') or \
               (args.postgresql and db['db_type'] == 'postgresql'):
                enabled_databases.append(db)
        DATABASES = enabled_databases

    # Handle full comparison mode (run both no-index and with-index tests)
    if args.full_comparison:
        run_full_comparison_suite(args)
        return

    # Determine if queries should be enabled
    enable_queries = args.queries and not args.no_index

    # Remove index flags if --no-index is specified
    if args.no_index:
        for db in DATABASES:
            # Remove -i and -mv flags from all databases
            db['flags'] = db['flags'].replace(' -i', '').replace('-i ', '').replace(' -mv', '').replace('-mv ', '')

    print(f"\n{'='*80}")
    print("BENCHMARK: Replicating LinkedIn Article Tests")
    print(f"{'='*80}")
    print(f"Document count: {NUM_DOCS:,}")
    print(f"Runs per test: {NUM_RUNS} (best time reported)")
    print(f"Batch size: {BATCH_SIZE}")
    if args.no_index:
        print(f"Index tests: DISABLED (insert-only mode)")
        print(f"Query tests: DISABLED (insert-only mode)")
    elif enable_queries:
        print(f"Query tests: ENABLED ({QUERY_LINKS} links per document)")
    else:
        print(f"Query tests: DISABLED (use --queries to enable)")
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Stop all databases first to ensure clean start
    stop_all_databases()

    # Run single-attribute tests
    single_results = run_test_suite(SINGLE_ATTR_TESTS, "SINGLE", enable_queries=enable_queries)

    # Run multi-attribute tests
    multi_results = run_test_suite(MULTI_ATTR_TESTS, "MULTI", enable_queries=enable_queries)

    # Generate summary
    generate_summary_table(single_results, multi_results)

    # Save results to JSON
    output_data = {
        "timestamp": datetime.now().isoformat(),
        "configuration": {
            "documents": NUM_DOCS,
            "runs": NUM_RUNS,
            "batch_size": BATCH_SIZE,
            "query_tests_enabled": enable_queries,
            "query_links": QUERY_LINKS if enable_queries else None
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
