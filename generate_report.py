#!/usr/bin/env python3
"""
Benchmark Report Generator
Runs MongoDB and Oracle benchmarks and generates an HTML report with visualizations.
"""

import subprocess
import re
import json
from datetime import datetime
import sys

def run_benchmark(command, description):
    """Run a benchmark command and return the output."""
    print(f"\n{'='*80}")
    print(f"Running: {description}")
    print(f"Command: {command}")
    print(f"{'='*80}\n")

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=600
        )
        return result.stdout, result.returncode
    except subprocess.TimeoutExpired:
        print(f"ERROR: {description} timed out after 600 seconds")
        return "", -1
    except Exception as e:
        print(f"ERROR running {description}: {e}")
        return "", -1

def parse_results(output):
    """Parse benchmark output and extract structured results."""
    results = []

    # Pattern to match: "Best time to insert 10000 documents with 100B payload in 1 attribute into indexed: 209ms"
    pattern = r"Best time to insert (\d+) documents with (\d+)B payload in (\d+) attributes? into indexed: (\d+)ms"

    for match in re.finditer(pattern, output):
        num_docs = int(match.group(1))
        payload_size = int(match.group(2))
        num_attrs = int(match.group(3))
        time_ms = int(match.group(4))

        results.append({
            "num_docs": num_docs,
            "payload_size": payload_size,
            "num_attributes": num_attrs,
            "time_ms": time_ms,
            "throughput": round(num_docs / (time_ms / 1000), 2)
        })

    return results

def generate_report_data():
    """Generate benchmark data by running all tests."""

    # Test configuration
    jar_path = "target/insertTest-1.0-jar-with-dependencies.jar"
    test_params = "-s 100,1000 -n 10 -r 3 -b 500 100000"

    report_data = {
        "timestamp": datetime.now().isoformat(),
        "configuration": {
            "documents": 100000,
            "payload_sizes": [100, 1000],
            "attributes": [1, 10],
            "runs": 3,
            "batch_size": 500
        },
        "results": {}
    }

    # Run MongoDB benchmark
    mongodb_output, return_code = run_benchmark(
        f"java -jar {jar_path} {test_params}",
        "MongoDB Benchmark"
    )
    if return_code == 0:
        report_data["results"]["mongodb"] = parse_results(mongodb_output)
    else:
        print(f"MongoDB benchmark failed with return code {return_code}")
        report_data["results"]["mongodb"] = []

    # Run Oracle without search index
    oracle_no_index_output, return_code = run_benchmark(
        f"java -jar {jar_path} -oj {test_params}",
        "Oracle JCT WITHOUT Search Index"
    )
    if return_code == 0:
        report_data["results"]["oracle_no_index"] = parse_results(oracle_no_index_output)
    else:
        print(f"Oracle (no index) benchmark failed with return code {return_code}")
        report_data["results"]["oracle_no_index"] = []

    # Run Oracle with search index
    oracle_with_index_output, return_code = run_benchmark(
        f"java -jar {jar_path} -oj -i {test_params}",
        "Oracle JCT WITH Search Index"
    )
    if return_code == 0:
        report_data["results"]["oracle_with_index"] = parse_results(oracle_with_index_output)
    else:
        print(f"Oracle (with index) benchmark failed with return code {return_code}")
        report_data["results"]["oracle_with_index"] = []

    # Run PostgreSQL with JSON
    postgresql_json_output, return_code = run_benchmark(
        f"java -jar {jar_path} -p {test_params}",
        "PostgreSQL with JSON"
    )
    if return_code == 0:
        report_data["results"]["postgresql_json"] = parse_results(postgresql_json_output)
    else:
        print(f"PostgreSQL (JSON) benchmark failed with return code {return_code}")
        report_data["results"]["postgresql_json"] = []

    # Run PostgreSQL with JSONB
    postgresql_jsonb_output, return_code = run_benchmark(
        f"java -jar {jar_path} -p -j {test_params}",
        "PostgreSQL with JSONB"
    )
    if return_code == 0:
        report_data["results"]["postgresql_jsonb"] = parse_results(postgresql_jsonb_output)
    else:
        print(f"PostgreSQL (JSONB) benchmark failed with return code {return_code}")
        report_data["results"]["postgresql_jsonb"] = []

    return report_data

def save_json_report(data, filename="benchmark_results.json"):
    """Save report data to JSON file."""
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"\n✓ JSON results saved to: {filename}")

def generate_html_report(data, template_file="report_template.html", output_file="benchmark_report.html"):
    """Generate HTML report from template and data."""

    try:
        with open(template_file, 'r') as f:
            template = f.read()

        # Embed the JSON data into the HTML template
        html = template.replace('{{BENCHMARK_DATA}}', json.dumps(data, indent=2))

        with open(output_file, 'w') as f:
            f.write(html)

        print(f"✓ HTML report generated: {output_file}")
        return True
    except FileNotFoundError:
        print(f"ERROR: Template file '{template_file}' not found")
        return False
    except Exception as e:
        print(f"ERROR generating HTML report: {e}")
        return False

def main():
    """Main execution function."""
    print("\n" + "="*80)
    print("BSON/JSON Benchmark Report Generator")
    print("="*80)

    # Generate benchmark data
    print("\nRunning benchmarks...")
    data = generate_report_data()

    # Save JSON results
    save_json_report(data)

    # Generate HTML report
    if generate_html_report(data):
        print(f"\n✓ Report generation complete!")
        print(f"  - JSON: benchmark_results.json")
        print(f"  - HTML: benchmark_report.html")
    else:
        print(f"\n⚠ HTML report generation failed, but JSON results are available")

    print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    main()
