#!/usr/bin/env python3
"""
Run ONLY Oracle JCT benchmarks to complete the comparison.
Reuses existing MongoDB and PostgreSQL results.
"""

import subprocess
import json
import re
from datetime import datetime

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
            # Try alternative pattern
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
            print(f"    Last 200 chars: {result.stdout[-200:]}")
            return {"success": False, "error": "Could not parse output"}

    except subprocess.TimeoutExpired:
        print(f"    ERROR: Timeout after 300 seconds")
        return {"success": False, "error": "Timeout"}
    except Exception as e:
        print(f"    ERROR: {str(e)}")
        return {"success": False, "error": str(e)}

def main():
    """Main execution - Oracle only."""
    print(f"\n{'='*80}")
    print("ORACLE JCT BENCHMARKS")
    print(f"{'='*80}")
    print(f"Document count: {NUM_DOCS:,}")
    print(f"Runs per test: {NUM_RUNS} (best time reported)")
    print(f"Batch size: {BATCH_SIZE}")
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    results = {
        "single_attribute": [],
        "multi_attribute": []
    }

    # Run single-attribute tests
    print(f"\n{'='*80}")
    print("SINGLE ATTRIBUTE TESTS - Oracle JCT")
    print(f"{'='*80}\n")

    for test in SINGLE_ATTR_TESTS:
        print(f"  Testing: {test['desc']}...", end=" ", flush=True)
        result = run_benchmark("-oj", test['size'], test['attrs'], NUM_DOCS, NUM_RUNS, BATCH_SIZE)

        if result['success']:
            results['single_attribute'].append(result)
            print(f"✓ {result['time_ms']}ms ({result['throughput']:,.0f} docs/sec)")
        else:
            results['single_attribute'].append(result)
            print(f"✗ {result.get('error', 'Failed')}")

    # Run multi-attribute tests
    print(f"\n{'='*80}")
    print("MULTI ATTRIBUTE TESTS - Oracle JCT")
    print(f"{'='*80}\n")

    for test in MULTI_ATTR_TESTS:
        print(f"  Testing: {test['desc']}...", end=" ", flush=True)
        result = run_benchmark("-oj", test['size'], test['attrs'], NUM_DOCS, NUM_RUNS, BATCH_SIZE)

        if result['success']:
            results['multi_attribute'].append(result)
            print(f"✓ {result['time_ms']}ms ({result['throughput']:,.0f} docs/sec)")
        else:
            results['multi_attribute'].append(result)
            print(f"✗ {result.get('error', 'Failed')}")

    # Save results
    output_data = {
        "timestamp": datetime.now().isoformat(),
        "configuration": {
            "documents": NUM_DOCS,
            "runs": NUM_RUNS,
            "batch_size": BATCH_SIZE
        },
        "oracle_jct": results
    }

    output_file = "oracle_benchmark_results.json"
    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)

    # Print summary
    print(f"\n{'='*80}")
    print("ORACLE JCT SUMMARY")
    print(f"{'='*80}")
    print(f"{'Payload':<12} {'Single-Attr':<15} {'Multi-Attr':<15}")
    print("-" * 80)

    for i, test in enumerate(SINGLE_ATTR_TESTS):
        single_result = results['single_attribute'][i]
        multi_result = results['multi_attribute'][i]

        single_str = f"{single_result['time_ms']}ms" if single_result['success'] else "FAIL"
        multi_str = f"{multi_result['time_ms']}ms" if multi_result['success'] else "FAIL"

        print(f"{test['size']}B{' '*7} {single_str:<15} {multi_str:<15}")

    print(f"\n✓ Results saved to: {output_file}")
    print(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    main()
