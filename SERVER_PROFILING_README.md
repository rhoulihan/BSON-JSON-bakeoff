# Server-Side Profiling with Flame Graphs

This document explains how to use server-side profiling to analyze database server performance using Linux `perf` and FlameGraph visualization.

## Overview

The benchmark suite now supports **two types of flame graph profiling**:

1. **Client-side profiling** (existing): Profiles the Java client application using async-profiler
2. **Server-side profiling** (new): Profiles the database server processes using Linux perf

Server-side profiling helps identify performance bottlenecks in:
- MongoDB mongod process
- Oracle database processes
- PostgreSQL server (future support)

## Prerequisites

### System Requirements

Both local and remote systems need:

1. **Linux perf tool**
   ```bash
   sudo yum install -y perf
   ```

2. **Perl modules** (for FlameGraph scripts)
   ```bash
   sudo yum install -y perl-open
   ```

3. **FlameGraph tools** (already installed if you followed setup)
   ```bash
   git clone https://github.com/brendangregg/FlameGraph
   ```

4. **Sudo privileges** (perf requires root/sudo to attach to processes)

### Verification

Check that everything is installed:
```bash
# Check perf
perf --version

# Check FlameGraph
ls FlameGraph/flamegraph.pl

# Check profile_server.py
ls profile_server.py
```

## Usage

### Standalone Server Profiling

Use `profile_server.py` to profile a database server directly:

```bash
# Profile MongoDB for 10 seconds
python3 profile_server.py mongodb --duration 10

# Profile Oracle for 30 seconds
python3 profile_server.py oracle --duration 30

# Custom output directory
python3 profile_server.py mongodb --duration 15 --output-dir my_profiles/

# Interactive mode (Ctrl+C to stop)
python3 profile_server.py oracle
```

**Output:**
- Creates `server_flamegraphs/` directory (or custom output dir)
- Generates SVG flame graph: `{database}_server_{timestamp}.svg`
- Example: `server_flamegraphs/mongodb_server_20251106_171925.svg`

### Integrated Benchmark Profiling

Add `--server-profile` flag to `run_article_benchmarks.py`:

```bash
# Profile both client and server during benchmarks
python3 run_article_benchmarks.py --queries --mongodb --oracle \
  --flame-graph --server-profile

# Profile only server side (no client profiling)
python3 run_article_benchmarks.py --queries --mongodb --server-profile

# Profile on remote system
ssh oci-opc "cd BSON-JSON-bakeoff && \
  python3 run_article_benchmarks.py --queries --mongodb --oracle \
  --server-profile > remote_benchmark.log 2>&1 &"
```

**What happens:**
1. Benchmark starts database service
2. Server profiler attaches to database process with `perf`
3. Benchmark runs (insertion/queries)
4. Server profiler stops and generates flame graph
5. Results saved to `server_flamegraphs/` directory

**Output files:**
```
server_flamegraphs/
├── mongodb_server_20251106_171925.svg
├── mongodb_server_20251106_171925.perf.data
├── oracle_server_20251106_172105.svg
└── oracle_server_20251106_172105.perf.data
```

## Understanding Flame Graphs

### Reading Flame Graphs

Flame graphs show CPU time distribution across function call stacks:

- **X-axis (width)**: Percentage of samples (wider = more CPU time)
- **Y-axis (height)**: Call stack depth (bottom = entry point, top = leaf functions)
- **Colors**: Random (for visual distinction only, no meaning)

### Key Features

- **Interactive**: Click on functions to zoom in
- **Search**: Use browser's find (Ctrl+F) to search function names
- **Hover**: Shows function name and percentage of samples

### What to Look For

1. **Wide blocks at the top**: Functions consuming significant CPU time
2. **Tall stacks**: Deep call chains (potential optimization targets)
3. **Unexpected functions**: I/O waits, lock contention, unnecessary work

### Example Interpretation

```
MongoDB Flame Graph Analysis:
├─ 40% mongod::WiredTiger          ← Storage engine
│  └─ 25% WT_SESSION::insert       ← Document insertion
├─ 30% mongod::QueryExecution      ← Query processing
└─ 20% mongod::NetworkInterface    ← Client communication
```

## How It Works

### Technical Details

1. **Process Discovery**
   - MongoDB: `pgrep mongod`
   - Oracle: `pgrep ora_pmon_FREE` (process monitor)

2. **Profiling with perf**
   ```bash
   perf record -F 99 -g -p <PID>
   ```
   - `-F 99`: Sample at 99 Hz (99 times per second)
   - `-g`: Capture call graphs (stack traces)
   - `-p <PID>`: Attach to specific process

3. **Flame Graph Generation**
   ```bash
   perf script > out.perf                           # Extract stack traces
   FlameGraph/stackcollapse-perf.pl out.perf > out.folded  # Collapse stacks
   FlameGraph/flamegraph.pl out.folded > flamegraph.svg    # Generate SVG
   ```

### Performance Impact

- **Overhead**: ~1-2% CPU (99 Hz sampling is very lightweight)
- **Safe for production**: Sampling-based, minimal impact
- **No code changes**: Works with any running process

## Troubleshooting

### "perf: command not found"

Install perf:
```bash
sudo yum install -y perf
```

### "Can't locate open.pm"

Install Perl modules:
```bash
sudo yum install -y perl-open
```

### "perf.data file's data size field is 0"

This means perf was not terminated properly. The script handles this automatically by:
1. Finding child perf processes
2. Sending SIGINT to gracefully stop
3. Waiting for data to flush

If you see this error, the profiling may have been interrupted. Try again with a longer duration.

### "No mongod/oracle process found"

Make sure the database is running:
```bash
# MongoDB
sudo systemctl status mongod

# Oracle
ps -ef | grep ora_pmon_FREE
```

### Permission Denied

Perf requires sudo privileges:
```bash
# Run with sudo (script handles this internally)
python3 profile_server.py mongodb --duration 10
```

Alternatively, adjust perf_event_paranoid:
```bash
sudo sysctl kernel.perf_event_paranoid=1
```

## Comparing Client vs Server Flame Graphs

### Client-Side Flame Graphs
- Shows **client application** (Java) CPU usage
- Located in: `flamegraphs/` directory
- Useful for: JDBC driver, JSON serialization, network I/O
- Generated by: async-profiler (Java agent)

### Server-Side Flame Graphs
- Shows **database server** (mongod/oracle) CPU usage
- Located in: `server_flamegraphs/` directory
- Useful for: Storage engine, query execution, index management
- Generated by: Linux perf + FlameGraph

### Example Analysis Workflow

1. **Identify bottleneck location**
   - Slow overall? Check both client and server
   - Slow queries? Focus on server flame graph
   - High CPU in client? Check JDBC/serialization

2. **Server flame graph analysis**
   ```
   MongoDB BSON insert:
   - 60% WiredTiger insert → Storage layer
   - 25% Index updates → Index overhead
   - 10% Document validation
   - 5% Networking
   ```

3. **Compare scenarios**
   - Run with/without indexes
   - Compare different document sizes
   - Analyze query patterns

## Example: Profiling During Benchmark

```bash
# Run comprehensive benchmark with server profiling
python3 run_article_benchmarks.py \
  --queries \
  --mongodb \
  --oracle \
  --server-profile \
  --monitor \
  --num-docs 5000 \
  --num-runs 3

# Wait for completion, then analyze results
ls -lh server_flamegraphs/
ls -lh flamegraphs/
```

**Expected Output:**
```
server_flamegraphs/
├── mongodb_bson_insert_200B_10attrs_20251106_172530.svg
├── mongodb_bson_query_1000B_50attrs_20251106_172545.svg
├── oracle_jct_insert_200B_10attrs_20251106_172610.svg
└── oracle_jct_query_1000B_50attrs_20251106_172625.svg

flamegraphs/  (client-side)
├── mongodb_bson_insert_200B_10attrs_20251106_172530.html
├── mongodb_bson_query_1000B_50attrs_20251106_172545.html
├── oracle_jct_insert_200B_10attrs_20251106_172610.html
└── oracle_jct_query_1000B_50attrs_20251106_172625.html
```

## Remote System Profiling

Server profiling works seamlessly on remote systems via SSH:

```bash
# Install dependencies on remote (one-time setup)
ssh oci-opc "sudo yum install -y perf perl-open"

# Copy scripts to remote
scp profile_server.py run_article_benchmarks.py oci-opc:BSON-JSON-bakeoff/

# Run benchmarks with server profiling
ssh oci-opc "cd BSON-JSON-bakeoff && \
  timeout 1800 python3 run_article_benchmarks.py \
    --queries --mongodb --oracle --server-profile \
    > remote_benchmark_with_profiling.log 2>&1 &"

# Monitor progress
ssh oci-opc "tail -f BSON-JSON-bakeoff/remote_benchmark_with_profiling.log"

# Collect flame graphs after completion
scp -r oci-opc:BSON-JSON-bakeoff/server_flamegraphs/ ./remote_server_flamegraphs/
```

## Advanced Usage

### Custom Sampling Frequency

Edit `profile_server.py` to change sampling rate:
```python
# Default: 99 Hz (line ~168)
cmd = ["sudo", "perf", "record", "-F", "99", ...]

# Higher resolution (more overhead): 999 Hz
cmd = ["sudo", "perf", "record", "-F", "999", ...]

# Lower overhead: 49 Hz
cmd = ["sudo", "perf", "record", "-F", "49", ...]
```

### Profile Specific Oracle Process

The script automatically finds the main Oracle process (ora_pmon_FREE). To profile a specific session:

```python
# Modify find_oracle_pid() in profile_server.py
# Example: profile a specific oracle session
def find_oracle_pid(self):
    result = subprocess.run(
        ["pgrep", "-f", "oracleXYZ"],  # Replace XYZ with your session
        capture_output=True, text=True
    )
    return int(result.stdout.strip())
```

### Compare Multiple Runs

```bash
# Run 1: No indexes
python3 run_article_benchmarks.py --no-index --mongodb --server-profile
mv server_flamegraphs server_flamegraphs_noindex

# Run 2: With indexes
python3 run_article_benchmarks.py --queries --mongodb --server-profile
mv server_flamegraphs server_flamegraphs_indexed

# Compare flame graphs side-by-side
firefox server_flamegraphs_noindex/mongodb*.svg &
firefox server_flamegraphs_indexed/mongodb*.svg &
```

## Reference

### Command-Line Flags

| Flag | Description |
|------|-------------|
| `--server-profile` | Enable server-side flame graph profiling |
| `--flame-graph` | Enable client-side flame graph profiling |
| `--monitor` | Enable system resource monitoring |
| `--queries` | Run query tests (needed for meaningful server load) |

### File Locations

| Path | Description |
|------|-------------|
| `profile_server.py` | Standalone server profiling script |
| `server_flamegraphs/` | Server-side flame graph output directory |
| `flamegraphs/` | Client-side flame graph output directory |
| `FlameGraph/` | Brendan Gregg's FlameGraph tools |

### Related Documents

- `MONITORING_README.md` - System resource monitoring documentation
- `CLAUDE.md` - Project overview and build instructions
- `README.md` - Main project documentation

## References

- [Linux perf documentation](https://perf.wiki.kernel.org/)
- [Brendan Gregg's FlameGraph](https://github.com/brendangregg/FlameGraph)
- [Flame Graphs visualization](http://www.brendangregg.com/flamegraphs.html)
- [Oracle profiling with perf](https://www.oracle.com/technical-resources/)
