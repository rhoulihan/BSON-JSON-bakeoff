#!/bin/bash

# Full benchmark automation script with progress monitoring
# This script runs article benchmarks with query tests, monitors progress,
# generates HTML report, and updates summary markdown files

set -e

BENCHMARK_LOG="benchmark_run.log"
RESULTS_FILE="article_benchmark_results.json"
HTML_REPORT="benchmark_report.html"
TIMEOUT_SECONDS=7200  # 120 minutes
PROGRESS_INTERVAL=180  # 3 minutes

echo "=========================================================================="
echo "FULL BENCHMARK SUITE WITH QUERY TESTS"
echo "=========================================================================="
echo "Start time: $(date)"
echo "Timeout: ${TIMEOUT_SECONDS}s (120 minutes)"
echo "Progress updates: Every ${PROGRESS_INTERVAL}s (3 minutes)"
echo "Per-test timeout: 900s (15 minutes)"
echo ""

# Clean up old benchmark run log
rm -f "$BENCHMARK_LOG"

# Start the benchmark in background
echo "Starting benchmarks in background..."
# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
timeout $TIMEOUT_SECONDS python3 "$SCRIPT_DIR/run_article_benchmarks.py" --queries > "$BENCHMARK_LOG" 2>&1 &
BENCHMARK_PID=$!
echo "Benchmark started with PID: $BENCHMARK_PID"
echo "Log file: $BENCHMARK_LOG"
echo ""

# Function to show progress
show_progress() {
    echo "=== Progress Update ($(date '+%H:%M:%S')) ==="
    if [ -f "$BENCHMARK_LOG" ]; then
        # Show last 40 lines with relevant info
        tail -40 "$BENCHMARK_LOG" | grep -E "(Testing:|✓|✗|SUMMARY|---|MongoDB|PostgreSQL|Oracle|Start time|End time)" || echo "Benchmarks in progress..."
    else
        echo "Waiting for benchmark to start..."
    fi
    echo ""
}

# Monitor progress every 3 minutes
ELAPSED=0
while kill -0 $BENCHMARK_PID 2>/dev/null; do
    sleep $PROGRESS_INTERVAL
    ELAPSED=$((ELAPSED + PROGRESS_INTERVAL))
    echo ""
    echo "=========================================================================="
    echo "Elapsed time: $((ELAPSED / 60)) minutes"
    show_progress
    echo "=========================================================================="
done

# Wait for the process to fully complete
wait $BENCHMARK_PID 2>/dev/null
EXIT_CODE=$?

echo ""
echo "=========================================================================="
echo "BENCHMARKS COMPLETE!"
echo "=========================================================================="
echo "End time: $(date)"
echo "Exit code: $EXIT_CODE"
echo ""

# Show final results
if [ $EXIT_CODE -eq 0 ]; then
    echo "✓ Benchmarks completed successfully"
    echo ""
    echo "=== Final Summary ==="
    tail -80 "$BENCHMARK_LOG" | grep -A 100 "SUMMARY:"
else
    echo "✗ Benchmarks exited with error code: $EXIT_CODE"
    echo ""
    echo "=== Last 100 lines of log ==="
    tail -100 "$BENCHMARK_LOG"
    exit $EXIT_CODE
fi

# Check if results file was created
if [ ! -f "$RESULTS_FILE" ]; then
    echo ""
    echo "✗ Error: Results file not found: $RESULTS_FILE"
    exit 1
fi

echo ""
echo "✓ Results file created: $RESULTS_FILE"
FILE_SIZE=$(du -h "$RESULTS_FILE" | cut -f1)
echo "  Size: $FILE_SIZE"

# Generate HTML report
echo ""
echo "=========================================================================="
echo "GENERATING HTML REPORT"
echo "=========================================================================="
python3 generate_report.py

if [ -f "$HTML_REPORT" ]; then
    echo "✓ HTML report generated: $HTML_REPORT"
    HTML_SIZE=$(du -h "$HTML_REPORT" | cut -f1)
    echo "  Size: $HTML_SIZE"
else
    echo "✗ Error: HTML report not generated"
    exit 1
fi

echo ""
echo "=========================================================================="
echo "BENCHMARK SUITE COMPLETE"
echo "=========================================================================="
echo ""
echo "Output files:"
echo "  - $BENCHMARK_LOG (execution log)"
echo "  - $RESULTS_FILE (JSON results)"
echo "  - $HTML_REPORT (interactive report)"
echo ""
echo "Next steps:"
echo "  1. Review the HTML report: open $HTML_REPORT"
echo "  2. Update summary markdown files with findings"
echo ""
echo "Completion time: $(date)"
echo "=========================================================================="
