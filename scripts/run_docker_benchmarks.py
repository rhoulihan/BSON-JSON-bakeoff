#!/usr/bin/env python3
"""
Docker-based benchmark script for comparing MongoDB vs Oracle JCT.
Designed to work with Docker containers (no systemd).

Tests:
- Single attribute: 10B, 200B, 1000B, 2000B, 4000B
- Multi attribute: 10×1B, 10×20B, 50×20B, 100×20B, 200×20B
- 10,000 documents per test
- 3 runs (best time reported)

Usage:
  python3 scripts/run_docker_benchmarks.py --mongodb --oracle --queries
  python3 scripts/run_docker_benchmarks.py --mongodb --oracle --no-index
  python3 scripts/run_docker_benchmarks.py --mongodb --oracle --full-comparison
"""

import subprocess
import json
import re
from datetime import datetime
import sys
import time
import argparse
import os
from pathlib import Path

JAR_PATH = "target/insertTest-1.0-jar-with-dependencies.jar"
NUM_DOCS = 10000
NUM_RUNS = 3
BATCH_SIZE = 500
QUERY_LINKS = 10

# Test configurations matching the LinkedIn article
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

# Database configurations for Docker
# MongoDB: uses -rd for realistic data
# Oracle JCT: uses -oj -mv -rd for JSON Collection Tables with multivalue index
DATABASES = {
    "mongodb": {"name": "MongoDB (BSON)", "flags": "-rd"},
    "oracle_jct": {"name": "Oracle JCT", "flags": "-oj -mv -rd"},
}

def check_jar_exists():
    """Check if the JAR file exists, build if not."""
    if not os.path.exists(JAR_PATH):
        print(f"JAR not found at {JAR_PATH}, building...")
        result = subprocess.run("mvn clean package -DskipTests", shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"ERROR: Failed to build JAR: {result.stderr}")
            sys.exit(1)
        print("Build successful")
    return True

def check_docker_containers():
    """Check if MongoDB and Oracle containers are running."""
    result = subprocess.run("docker ps --format '{{.Names}}'", shell=True, capture_output=True, text=True)
    containers = result.stdout.strip().split('\n')

    mongodb_running = any('mongodb' in c.lower() for c in containers)
    oracle_running = any('oracle' in c.lower() for c in containers)

    return mongodb_running, oracle_running

def run_benchmark(db_flags, size, attrs, num_docs, num_runs, batch_size, query_links=None, use_index=True):
    """Run a single benchmark test."""

    # Build command
    flags = db_flags
    if use_index:
        flags += " -i"

    cmd = f"java -jar {JAR_PATH} {flags} -s {size} -n {attrs} -r {num_runs} -b {batch_size}"

    # Add query test flag if specified
    if query_links is not None and use_index:
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

        response = {
            "success": False,
            "size": size,
            "attrs": attrs,
            "num_docs": num_docs
        }

        # Parse insertion time
        # Pattern: "Best time to insert N documents with XB payload in Y attribute(s) into indexed: ZZZms"
        # Or: "Best time to insert N documents with realistic nested data (~XB) into indexed: ZZZms"
        patterns = [
            rf"(?:Best time|Time taken) to insert {num_docs} documents with {size}B payload in \d+ attributes? into \w+: (\d+)ms",
            rf"(?:Best time|Time taken) to insert {num_docs} documents with realistic nested data \(~{size}B\) into \w+: (\d+)ms",
        ]

        for pattern in patterns:
            match = re.search(pattern, result.stdout)
            if match:
                time_ms = int(match.group(1))
                throughput = round(num_docs / (time_ms / 1000), 2)
                response.update({
                    "success": True,
                    "time_ms": time_ms,
                    "throughput": throughput
                })
                break

        if not response["success"]:
            # Debug output
            if result.stdout:
                print(f"\n    DEBUG stdout: {result.stdout[:500]}")
            if result.stderr:
                print(f"\n    DEBUG stderr: {result.stderr[:500]}")
            return {"success": False, "error": "Could not parse output"}

        # Parse query results if query test was run
        if query_links is not None and use_index:
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
                })

        return response

    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Timeout"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def run_test_suite(test_configs, databases, test_type, enable_queries=False, use_index=True):
    """Run a complete test suite."""
    print(f"\n{'='*80}")
    index_str = "WITH INDEX" if use_index else "NO INDEX"
    query_str = "+ QUERIES" if enable_queries else ""
    print(f"{test_type.upper()} TESTS ({index_str} {query_str})")
    print(f"{'='*80}")

    results = {}

    for db_key, db_config in databases.items():
        print(f"\n--- {db_config['name']} ---")
        results[db_key] = []

        for test in test_configs:
            print(f"  Testing: {test['desc']}...", end=" ", flush=True)

            result = run_benchmark(
                db_config['flags'],
                test['size'],
                test['attrs'],
                NUM_DOCS,
                NUM_RUNS,
                BATCH_SIZE,
                query_links=QUERY_LINKS if enable_queries else None,
                use_index=use_index
            )

            if result['success']:
                output = f"✓ {result['time_ms']}ms ({result['throughput']:,.0f} docs/sec)"
                if enable_queries and 'query_time_ms' in result:
                    output += f" | Query: {result['query_time_ms']}ms ({result['query_throughput']:,.0f} queries/sec)"
                print(output)
            else:
                print(f"✗ {result.get('error', 'Failed')}")

            results[db_key].append(result)

    return results

def generate_summary_table(results, test_configs, test_type, databases):
    """Generate a summary table."""
    print(f"\n{'='*80}")
    print(f"SUMMARY: {test_type}")
    print(f"{'='*80}")

    # Header
    header = f"{'Config':<25}"
    for db_key in databases.keys():
        header += f" {databases[db_key]['name']:<20}"
    print(header)
    print("-" * 80)

    # Rows
    for i, test in enumerate(test_configs):
        row = f"{test['desc']:<25}"
        for db_key in databases.keys():
            if db_key in results and i < len(results[db_key]):
                result = results[db_key][i]
                if result['success']:
                    row += f" {result['time_ms']:>6}ms ({result['throughput']:>8,.0f}/s)"
                else:
                    row += f" {'FAIL':>20}"
            else:
                row += f" {'N/A':>20}"
        print(row)

def main():
    global NUM_DOCS, NUM_RUNS, BATCH_SIZE, QUERY_LINKS

    parser = argparse.ArgumentParser(description='Docker-based MongoDB vs Oracle JCT benchmarks')
    parser.add_argument('--queries', '-q', action='store_true',
                        help='Include query tests with indexes')
    parser.add_argument('--no-index', action='store_true',
                        help='Run insert-only tests without indexes')
    parser.add_argument('--full-comparison', action='store_true',
                        help='Run both indexed (with queries) and non-indexed tests')
    parser.add_argument('--mongodb', action='store_true', help='Run MongoDB tests')
    parser.add_argument('--oracle', action='store_true', help='Run Oracle JCT tests')
    parser.add_argument('--batch-size', '-b', type=int, default=BATCH_SIZE,
                        help=f'Batch size (default: {BATCH_SIZE})')
    parser.add_argument('--num-docs', '-n', type=int, default=NUM_DOCS,
                        help=f'Number of documents (default: {NUM_DOCS})')
    parser.add_argument('--num-runs', '-r', type=int, default=NUM_RUNS,
                        help=f'Number of runs (default: {NUM_RUNS})')
    args = parser.parse_args()

    NUM_DOCS = args.num_docs
    NUM_RUNS = args.num_runs
    BATCH_SIZE = args.batch_size

    # Filter databases
    databases = {}
    if args.mongodb:
        databases['mongodb'] = DATABASES['mongodb']
    if args.oracle:
        databases['oracle_jct'] = DATABASES['oracle_jct']

    if not databases:
        databases = DATABASES  # Run all if none specified

    # Check prerequisites
    check_jar_exists()

    mongodb_running, oracle_running = check_docker_containers()
    if 'mongodb' in databases and not mongodb_running:
        print("WARNING: MongoDB container does not appear to be running")
    if 'oracle_jct' in databases and not oracle_running:
        print("WARNING: Oracle container does not appear to be running")

    print(f"\n{'='*80}")
    print("DOCKER BENCHMARK: MongoDB vs Oracle JCT")
    print(f"{'='*80}")
    print(f"Document count: {NUM_DOCS:,}")
    print(f"Runs per test: {NUM_RUNS} (best time reported)")
    print(f"Batch size: {BATCH_SIZE}")
    print(f"Databases: {', '.join(d['name'] for d in databases.values())}")
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    all_results = {}

    if args.full_comparison:
        # Run both no-index and indexed tests
        print("\n" + "="*80)
        print("PART 1: INSERT-ONLY TESTS (NO INDEXES)")
        print("="*80)

        single_noindex = run_test_suite(SINGLE_ATTR_TESTS, databases, "SINGLE ATTRIBUTE",
                                         enable_queries=False, use_index=False)
        multi_noindex = run_test_suite(MULTI_ATTR_TESTS, databases, "MULTI ATTRIBUTE",
                                        enable_queries=False, use_index=False)

        print("\n" + "="*80)
        print("PART 2: INDEXED TESTS WITH QUERIES")
        print("="*80)

        single_indexed = run_test_suite(SINGLE_ATTR_TESTS, databases, "SINGLE ATTRIBUTE",
                                         enable_queries=True, use_index=True)
        multi_indexed = run_test_suite(MULTI_ATTR_TESTS, databases, "MULTI ATTRIBUTE",
                                        enable_queries=True, use_index=True)

        all_results = {
            "no_index": {
                "single_attribute": single_noindex,
                "multi_attribute": multi_noindex
            },
            "with_index": {
                "single_attribute": single_indexed,
                "multi_attribute": multi_indexed
            }
        }

        # Generate summaries
        generate_summary_table(single_noindex, SINGLE_ATTR_TESTS, "Single-Attribute (No Index)", databases)
        generate_summary_table(multi_noindex, MULTI_ATTR_TESTS, "Multi-Attribute (No Index)", databases)
        generate_summary_table(single_indexed, SINGLE_ATTR_TESTS, "Single-Attribute (Indexed + Query)", databases)
        generate_summary_table(multi_indexed, MULTI_ATTR_TESTS, "Multi-Attribute (Indexed + Query)", databases)

    elif args.no_index:
        # Insert-only tests without indexes
        single_results = run_test_suite(SINGLE_ATTR_TESTS, databases, "SINGLE ATTRIBUTE",
                                         enable_queries=False, use_index=False)
        multi_results = run_test_suite(MULTI_ATTR_TESTS, databases, "MULTI ATTRIBUTE",
                                        enable_queries=False, use_index=False)

        all_results = {
            "single_attribute": single_results,
            "multi_attribute": multi_results
        }

        generate_summary_table(single_results, SINGLE_ATTR_TESTS, "Single-Attribute (No Index)", databases)
        generate_summary_table(multi_results, MULTI_ATTR_TESTS, "Multi-Attribute (No Index)", databases)

    else:
        # Default: indexed tests with optional queries
        enable_queries = args.queries

        single_results = run_test_suite(SINGLE_ATTR_TESTS, databases, "SINGLE ATTRIBUTE",
                                         enable_queries=enable_queries, use_index=True)
        multi_results = run_test_suite(MULTI_ATTR_TESTS, databases, "MULTI ATTRIBUTE",
                                        enable_queries=enable_queries, use_index=True)

        all_results = {
            "single_attribute": single_results,
            "multi_attribute": multi_results
        }

        suffix = "(Indexed + Query)" if enable_queries else "(Indexed)"
        generate_summary_table(single_results, SINGLE_ATTR_TESTS, f"Single-Attribute {suffix}", databases)
        generate_summary_table(multi_results, MULTI_ATTR_TESTS, f"Multi-Attribute {suffix}", databases)

    # Save results
    output_data = {
        "timestamp": datetime.now().isoformat(),
        "configuration": {
            "documents": NUM_DOCS,
            "runs": NUM_RUNS,
            "batch_size": BATCH_SIZE,
            "databases": list(databases.keys()),
            "mode": "full_comparison" if args.full_comparison else ("no_index" if args.no_index else "indexed"),
            "queries_enabled": args.queries or args.full_comparison
        },
        "results": all_results
    }

    output_file = "docker_benchmark_results.json"
    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)

    print(f"\n{'='*80}")
    print(f"✓ Results saved to: {output_file}")
    print(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    main()
