#!/usr/bin/env python3
"""
Create flamegraph_summaries.json from benchmark logs and flame graph files.
"""
import json
import re
from pathlib import Path
from collections import defaultdict

def parse_log_file(log_path):
    """Parse benchmark log file to extract performance data, tracking database sections."""
    mongodb_results = {}
    oracle_results = {}
    current_db = None

    with open(log_path, 'r') as f:
        lines = f.readlines()

    # Extract test results - tracking which database section we're in
    # Sections: "--- MongoDB (BSON) ---" and "--- Oracle JCT ---"
    # Results: "✓ {time}ms ({rate} docs/sec)" or "✓ {time}ms ({rate} docs/sec) | Query: {time}ms ({rate} queries/sec)"
    for i in range(len(lines)):
        line = lines[i]

        # Detect database section headers
        if '--- MongoDB' in line:
            current_db = 'mongodb'
            continue
        elif '--- Oracle' in line:
            current_db = 'oracle'
            continue

        # Look for test start
        testing_match = re.search(r'Testing:\s+(.+?)\.\.\.\s*', line)
        if testing_match and current_db:
            description = testing_match.group(1).strip()

            # Check next 30 lines for the result (server profiling adds many lines)
            for j in range(1, min(30, len(lines) - i)):
                result_line = lines[i + j]

                # Try to match result with query data
                query_match = re.search(
                    r'✓\s+(\d+)ms\s+\(([0-9,]+)\s+docs/sec\)\s+\|\s+Query:\s+(\d+)ms\s+\(([0-9,]+)\s+queries/sec\)',
                    result_line
                )

                if query_match:
                    time_ms = int(query_match.group(1))
                    docs_per_sec = int(query_match.group(2).replace(',', ''))
                    query_time_ms = int(query_match.group(3))
                    queries_per_sec = int(query_match.group(4).replace(',', ''))

                    result = {
                        'time_ms': time_ms,
                        'docs_per_sec': docs_per_sec,
                        'query_time_ms': query_time_ms,
                        'queries_per_sec': queries_per_sec
                    }

                    if current_db == 'mongodb':
                        mongodb_results[description] = result
                    else:
                        oracle_results[description] = result
                    break

                # Try to match result without query data
                insert_match = re.search(r'✓\s+(\d+)ms\s+\(([0-9,]+)\s+docs/sec\)', result_line)

                if insert_match:
                    time_ms = int(insert_match.group(1))
                    docs_per_sec = int(insert_match.group(2).replace(',', ''))

                    result = {
                        'time_ms': time_ms,
                        'docs_per_sec': docs_per_sec
                    }

                    if current_db == 'mongodb':
                        mongodb_results[description] = result
                    else:
                        oracle_results[description] = result
                    break

    return {'mongodb': mongodb_results, 'oracle': oracle_results}

def map_log_results_to_flamegraphs(log_results, flamegraph_dir, database, test_type, system):
    """Map log results to corresponding flame graph files.

    Args:
        log_results: Dict with performance data for this database
        flamegraph_dir: Directory containing flame graph files
        database: 'mongodb_bson' or 'oracle_jct'
        test_type: 'insert' or 'query'
        system: System description string
    """
    tests = []
    flamegraph_path = Path(flamegraph_dir)

    if not flamegraph_path.exists():
        return tests

    # Get all flame graphs for this database and test type
    pattern = f"{database}_{test_type}_*.html"
    fg_files = sorted(flamegraph_path.glob(pattern))

    for description, perf_data in log_results.items():
        # Find corresponding flame graph file
        # Description format: "10B single attribute", "200B 10 attributes", etc.

        # Extract size and attr count from description
        # Match formats like: 10B, 200B, 10KB, 100KB, 1000KB
        size_match = re.search(r'(\d+)([KM]?B)', description)
        attr_match = re.search(r'(\d+)\s+attributes?|single attribute', description)

        if not size_match:
            continue

        # Convert size to bytes for flame graph matching
        size_val = int(size_match.group(1))
        size_unit = size_match.group(2)

        if size_unit == 'KB':
            size = str(size_val * 1000)  # Convert KB to bytes
        elif size_unit == 'MB':
            size = str(size_val * 1000000)  # Convert MB to bytes
        else:
            size = str(size_val)  # Already in bytes

        if 'single attribute' in description:
            attrs = '1'
        elif attr_match:
            attrs = attr_match.group(1) if attr_match.group(1) else '1'
        else:
            attrs = '1'

        # Find matching flame graph (optional)
        fg_match_pattern = f"{database}_{test_type}_{size}B_{attrs}attrs_"
        matching_fg = [fg for fg in fg_files if fg_match_pattern in fg.name]

        fg_file = matching_fg[0] if matching_fg else None

        # Build performance section
        performance = {
            'insertion': {
                'time_ms': perf_data['time_ms'],
                'docs_per_sec': perf_data['docs_per_sec']
            }
        }

        # Add query data if present
        if 'query_time_ms' in perf_data and 'queries_per_sec' in perf_data:
            performance['query'] = {
                'time_ms': perf_data['query_time_ms'],
                'queries_per_sec': perf_data['queries_per_sec']
            }

        test_entry = {
            'system': system,
            'database': 'MongoDB BSON' if database == 'mongodb_bson' else 'Oracle JCT',
            'test_type': 'No Index' if test_type == 'insert' else 'Indexed with Queries',
            'description': description,
            'flamegraph_file': str(fg_file) if fg_file else None,
            'performance': performance,
            'analysis': [
                f"{'MongoDB' if database == 'mongodb_bson' else 'Oracle'} insertion achieved {perf_data['docs_per_sec']:,} docs/sec ({perf_data['time_ms']}ms for 10K documents)."
            ]
        }

        tests.append(test_entry)

    return tests

def main():
    """Generate flamegraph_summaries.json from logs."""
    project_root = Path(__file__).parent

    summaries = {
        'local_noindex': [],
        'local_indexed': [],
        'remote_noindex': [],
        'remote_indexed': []
    }

    # Parse local no-index
    local_noindex_log = project_root / 'local_noindex.log'
    if local_noindex_log.exists():
        print("Parsing local no-index log...")
        results = parse_log_file(local_noindex_log)

        # results is now {'mongodb': {...}, 'oracle': {...}}
        summaries['local_noindex'].extend(
            map_log_results_to_flamegraphs(results['mongodb'], 'flamegraphs', 'mongodb_bson', 'insert', 'Local System (Dev Machine)')
        )
        summaries['local_noindex'].extend(
            map_log_results_to_flamegraphs(results['oracle'], 'flamegraphs', 'oracle_jct', 'insert', 'Local System (Dev Machine)')
        )

    # Parse local indexed
    local_indexed_log = project_root / 'local_indexed.log'
    if local_indexed_log.exists():
        print("Parsing local indexed log...")
        results = parse_log_file(local_indexed_log)

        summaries['local_indexed'].extend(
            map_log_results_to_flamegraphs(results['mongodb'], 'flamegraphs', 'mongodb_bson', 'query', 'Local System (Dev Machine)')
        )
        summaries['local_indexed'].extend(
            map_log_results_to_flamegraphs(results['oracle'], 'flamegraphs', 'oracle_jct', 'query', 'Local System (Dev Machine)')
        )

    # Parse remote logs (if they exist locally)
    remote_noindex_log = project_root / 'remote_noindex.log'
    remote_indexed_log = project_root / 'remote_indexed.log'

    if remote_noindex_log.exists():
        print("Parsing remote no-index log...")
        results = parse_log_file(remote_noindex_log)

        summaries['remote_noindex'].extend(
            map_log_results_to_flamegraphs(results['mongodb'], 'flamegraphs', 'mongodb_bson', 'insert', 'Remote System (OCI Cloud)')
        )
        summaries['remote_noindex'].extend(
            map_log_results_to_flamegraphs(results['oracle'], 'flamegraphs', 'oracle_jct', 'insert', 'Remote System (OCI Cloud)')
        )

    if remote_indexed_log.exists():
        print("Parsing remote indexed log...")
        results = parse_log_file(remote_indexed_log)

        summaries['remote_indexed'].extend(
            map_log_results_to_flamegraphs(results['mongodb'], 'flamegraphs', 'mongodb_bson', 'query', 'Remote System (OCI Cloud)')
        )
        summaries['remote_indexed'].extend(
            map_log_results_to_flamegraphs(results['oracle'], 'flamegraphs', 'oracle_jct', 'query', 'Remote System (OCI Cloud)')
        )

    # Output summary
    print(f"\nGenerated summaries:")
    print(f"  local_noindex: {len(summaries['local_noindex'])} tests")
    print(f"  local_indexed: {len(summaries['local_indexed'])} tests")
    print(f"  remote_noindex: {len(summaries['remote_noindex'])} tests")
    print(f"  remote_indexed: {len(summaries['remote_indexed'])} tests")

    # Save to JSON
    output_file = project_root / 'flamegraph_summaries.json'
    with open(output_file, 'w') as f:
        json.dump(summaries, f, indent=2)

    print(f"\n✅ Saved flamegraph_summaries.json")
    print(f"   Total tests: {sum(len(v) for v in summaries.values())}")

if __name__ == '__main__':
    main()
