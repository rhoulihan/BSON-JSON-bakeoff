# Flame Graph Profiling Feature

## Overview

Added flame graph generation capability to the benchmark suite using async-profiler. This feature allows detailed CPU profiling and performance analysis of JVM-based benchmarks.

## Files Created/Modified

### New Files:
1. **setup_async_profiler.sh** - Installation script for async-profiler
   - Downloads async-profiler 3.0
   - Installs to /opt/async-profiler
   - Configures perf_event_paranoid for profiling
   - Creates symlink to /usr/local/bin/asprof

### Modified Files:
1. **run_article_benchmarks.py**:
   - Added `--flame-graph` command-line argument
   - Added `ASYNC_PROFILER_PATH` and `FLAMEGRAPH_OUTPUT_DIR` constants
   - Added `check_async_profiler()` function to validate installation
   - Added `get_flamegraph_filename()` to generate unique flame graph names
   - Modified `run_benchmark()` to use async-profiler when flame_graph=True
   - Modified `run_test_suite()` to accept and pass flame_graph parameter
   - Added validation check at script startup

2. **CLAUDE.md**:
   - Added "Flame Graph Profiling" section with usage examples
   - Documented system requirements and setup process
   - Added example output filenames

3. **.gitignore**:
   - Added `flamegraphs/` directory to ignore flame graph output files

## Usage

### Initial Setup (one-time):
```bash
chmod +x setup_async_profiler.sh
./scripts/setup_async_profiler.sh
```

### Running Benchmarks with Flame Graphs:
```bash
# Basic usage - MongoDB and Oracle with queries
python3 scripts/run_article_benchmarks.py --queries --mongodb --oracle --flame-graph

# Combined with other options
python3 scripts/run_article_benchmarks.py --queries --mongodb --oracle --flame-graph --monitor --nostats
```

### Output Location:
Flame graphs are saved in `flamegraphs/` directory with format:
```
{database}_{test_type}_{size}B_{attrs}attrs_{timestamp}.html
```

Example:
```
flamegraphs/mongodb_bson_insert_200B_10attrs_20250106_143022.html
flamegraphs/oracle_jct_query_1000B_50attrs_20250106_143145.html
```

## Technical Details

### How It Works:
1. When `--flame-graph` is specified, the script checks if async-profiler is installed
2. For each benchmark test, if flame graphs are enabled:
   - A unique filename is generated based on database, test type, size, and attributes
   - Java is started with the async-profiler agent: `-agentpath:/opt/async-profiler/lib/libasyncProfiler.so=start,event=cpu,file=output.html`
   - The profiler captures CPU samples during the entire benchmark run
   - On JVM exit, the flame graph HTML file is automatically generated

### Profiler Configuration:
- **Event**: CPU sampling (event=cpu)
- **Output Format**: HTML (interactive flame graphs)
- **Sampling**: Continuous during benchmark execution
- **Overhead**: < 5% typical

### Flame Graph Interpretation:
- **X-axis**: Percentage of CPU samples (not time)
- **Y-axis**: Stack depth
- **Color**: Helps distinguish different code paths (no semantic meaning)
- **Width**: Relative time spent in that method
- **Interactive**: Click to zoom, hover for details

## System Requirements

- **OS**: Linux (perf_event support required)
- **Kernel**: perf_event_paranoid <= 1 (configured by setup script)
- **async-profiler**: Version 3.0 (automatically downloaded)
- **Java**: Any recent JVM (tested with Java 11+)

## Error Handling

The implementation gracefully handles missing async-profiler:
1. If `--flame-graph` is specified but async-profiler is not installed:
   - Prints warning message with installation instructions
   - Continues running benchmarks WITHOUT flame graphs
   - Does not fail or abort the benchmark run

2. If async-profiler is installed:
   - Prints confirmation message with output directory
   - Generates one flame graph per benchmark test
   - Shows flame graph file path during execution

## Benefits

1. **Performance Analysis**: Identify CPU hotspots in insertion and query operations
2. **Method-Level Visibility**: See exactly which methods consume CPU time
3. **Database Comparison**: Compare flame graphs between MongoDB BSON and Oracle JCT
4. **Optimization**: Guide performance tuning efforts based on actual CPU usage
5. **Zero Code Changes**: Enable/disable with command-line flag only

## Example Workflow

```bash
# 1. Install async-profiler (one-time)
./scripts/setup_async_profiler.sh

# 2. Run benchmarks with profiling
python3 scripts/run_article_benchmarks.py --queries --mongodb --oracle --flame-graph --num-docs 10000

# 3. Open flame graphs in browser
firefox flamegraphs/mongodb_bson_insert_200B_10attrs_*.html
firefox flamegraphs/oracle_jct_insert_200B_10attrs_*.html

# 4. Analyze and compare CPU usage patterns
```

## Integration with Existing Features

Flame graph profiling works seamlessly with other features:
- ✅ Resource monitoring (`--monitor`)
- ✅ Statistics control (`--nostats`)
- ✅ Database selection (`--mongodb`, `--oracle`)
- ✅ Query tests (`--queries`)
- ✅ No-index tests (`--no-index`)
- ✅ Custom document counts (`--num-docs`)
- ✅ Custom run counts (`--num-runs`)

## Future Enhancements (Optional)

Possible future improvements:
1. Add allocation profiling (event=alloc)
2. Add lock contention profiling (event=lock)
3. Generate differential flame graphs (compare two runs)
4. Integrate flame graph links into HTML benchmark reports
5. Support for profiling specific test categories only

## Notes

- Flame graphs are generated only for JVM-based tests (MongoDB Java driver, Oracle JDBC)
- PostgreSQL benchmarks also generate flame graphs (Java-based)
- Minimal performance overhead (< 5%)
- Flame graphs can be large (1-5 MB) for long-running tests
- HTML files are self-contained and can be shared/archived
