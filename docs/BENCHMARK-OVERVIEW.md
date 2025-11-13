# Benchmark Overview

This document provides a comprehensive guide to running benchmarks and understanding environment dependencies for `scripts/run_article_benchmarks.py`.

## Table of Contents

- [System Requirements](#system-requirements)
- [Database Dependencies](#database-dependencies)
- [File System Dependencies](#file-system-dependencies)
- [Configuration Files](#configuration-files)
- [Profiling Dependencies (Optional)](#profiling-dependencies-optional)
- [Python Dependencies](#python-dependencies)
- [Network/Port Requirements](#networkport-requirements)
- [Sudo/Permission Requirements](#sudopermission-requirements)
- [Environment Variables](#environment-variables)
- [Differences Between Local and Remote Systems](#differences-between-local-and-remote-systems)
- [Troubleshooting Common Issues](#troubleshooting-common-issues)
- [Summary Checklist](#summary-checklist)
- [Quick Setup Commands](#quick-setup-commands)
- [Running the Benchmark](#running-the-benchmark)
  - [Basic Example](#basic-example)
  - [Complete Example (Full Profiling)](#complete-example-full-profiling)
  - [Generating HTML Report](#generating-html-report)
  - [Expected Duration](#expected-duration)

---

## System Requirements

### Operating System
- **Linux** (tested on Oracle Linux 9.6, kernel 5.14.0)
- **systemd** for service management
- **sudo** privileges required for:
  - systemctl (start/stop databases)
  - Page cache clearing (`/proc/sys/vm/drop_caches`)
  - perf profiling (server-side flame graphs)

### Required System Commands
```bash
# Core utilities (must be in PATH)
java          # OpenJDK/Oracle JDK for running JAR file
mvn           # Maven for building (if JAR not present)
sudo          # For systemctl, cache clearing, perf
systemctl     # For database service management
mongosh       # MongoDB shell (for readiness checks)
psql          # PostgreSQL client (for readiness checks)
sqlplus       # Oracle SQL*Plus (for readiness checks)
pgrep         # Process grep (for finding database PIDs)
ps            # Process list (for Oracle PMON checks)
```

## Database Dependencies

### MongoDB
- **Service name**: `mongod` (systemd)
- **Version**: MongoDB 6.0+ recommended
- **Default port**: 27017 (not explicitly checked, assumed)
- **Readiness check**: `mongosh --quiet --eval 'db.adminCommand("ping").ok'`
- **Data directory**: `/mnt/benchmarks/mongodb_data` (commented reference)
  - Configured in `/etc/mongod.conf`
  - Ownership: `mongod:mongod`
- **Startup time**: Max 30 seconds
- **Connection**: Configured via `config.properties`

### PostgreSQL
- **Service name**: `postgresql-17` (systemd)
- **Version**: PostgreSQL 17
- **Default port**: 5432 (assumed)
- **Readiness check**: `sudo -u postgres psql -c 'SELECT 1;'`
- **User**: `postgres` (requires sudo access)
- **Startup time**: Max 30 seconds
- **Connection**: Configured via `config.properties`

### Oracle Database
- **Service name**: `oracle-free-26ai` (systemd)
- **Version**: Oracle 23ai Free Edition
- **Database name**: `FREE` (CDB)
- **PDB name**: `FREEPDB1` (pluggable database)
- **Ports**:
  - 1521 (listener)
- **Credentials** (hardcoded in script):
  - System password: `G0_4w4y!`
  - Connection: `system/G0_4w4y!@localhost:1521/FREE`
  - PDB connection: `system/G0_4w4y!@localhost:1521/FREEPDB1`
- **Readiness checks**:
  1. PMON process: `ps -ef | grep db_pmon_FREE`
  2. PDB status: `SELECT open_mode FROM v$pdbs WHERE name='FREEPDB1'` (must be `READ WRITE`)
  3. JDBC connectivity: `SELECT 1 FROM DUAL` via sqlplus
- **Data directory**: `/mnt/benchmarks/oracle_data` (commented reference)
  - Symlinked from `/opt/oracle/oradata/FREE`
  - Ownership: `oracle:oinstall`
- **Startup time**: Max 120 seconds (can take 60-90s)
- **Size limit**: 12GB maximum (Oracle Free Edition)
- **Environment**:
  - `ORACLE_HOME=/opt/oracle/product/26ai/dbhomeFree` (implied)
  - Oracle user: `oracle`

## File System Dependencies

### Required Files
```
project_root/
├── target/
│   └── insertTest-1.0-jar-with-dependencies.jar  # Built from mvn package
├── config.properties                              # Database connection strings (gitignored)
├── scripts/
│   ├── run_article_benchmarks.py                 # Main benchmark script
│   ├── profile_server.py                         # Server-side profiling (optional)
│   └── monitor_resources.py                      # Resource monitoring (optional)
└── flamegraphs/                                   # Created automatically
    └── *.html                                     # Client-side flame graphs
```

### Required Directories (created automatically)
- `flamegraphs/` - Client-side flame graph output
- `server_flamegraphs/` - Server-side flame graph output (if profiling enabled)

### Optional Data Directories
- `/mnt/benchmarks/mongodb_data` - MongoDB data (referenced but cleanup disabled)
- `/mnt/benchmarks/oracle_data` - Oracle data (referenced but cleanup disabled)

## Configuration Files

### config.properties (Required)
Location: `project_root/config.properties`

```properties
# Example content (actual file is gitignored)
mongodb.connection.string=mongodb://localhost:27017
postgresql.connection.string=jdbc:postgresql://localhost:5432/test?user=postgres&password=PASSWORD
oracle.connection.string=jdbc:oracle:thin:system/G0_4w4y!@localhost:1521/FREEPDB1
```

Created from: `config/config.properties.example`

### Database Configuration
- **MongoDB**: `/etc/mongod.conf` (for data directory configuration)
- **Oracle**: Environment variables, listener.ora, tnsnames.ora (standard Oracle setup)

## Profiling Dependencies (Optional)

### Client-Side Profiling (--flame-graph)
- **async-profiler**: `/opt/async-profiler/lib/libasyncProfiler.so`
  - Version: 3.0
  - Install: `./scripts/setup_async_profiler.sh`
  - Requires: `perf_event_paranoid <= 1` (`/proc/sys/kernel/perf_event_paranoid`)
- **Output**: HTML flame graphs in `flamegraphs/`

### Server-Side Profiling (--server-profile)
- **Linux perf**: `perf record`, `perf script`
  - Package: `perf` (yum/dnf)
- **FlameGraph tools**: Perl scripts for flame graph generation
  - Location (auto-detected):
    - `./FlameGraph/`
    - `/opt/FlameGraph/`
    - `~/FlameGraph/`
  - Install: `git clone https://github.com/brendangregg/FlameGraph`
  - Required scripts:
    - `stackcollapse-perf.pl`
    - `flamegraph.pl`
- **Perl modules**: `perl-open` (yum/dnf)
- **Sudo access**: Required for `perf record` on system processes
- **Output**: SVG flame graphs in `server_flamegraphs/`

### Resource Monitoring (--monitor)
- **Python 3** with standard library modules
- **System tools**:
  - `ps` - Process info
  - `iostat` - Disk I/O stats (optional)
  - `/proc/` filesystem - Memory, CPU stats
- **Output**: `resource_metrics.json`

## Python Dependencies

### Required Python Modules (Standard Library)
```python
import subprocess  # System command execution
import json        # JSON parsing
import re          # Regular expressions
import datetime    # Timestamps
import sys         # System utilities
import time        # Sleep/timing
import argparse    # Command-line parsing
import random      # Test randomization
import os          # File/path operations
import signal      # Process signals
```

### Optional Python Modules
- `profile_server.ServerProfiler` - Server-side profiling (same directory)
- `monitor_resources` - Resource monitoring script (same directory)

## Network/Port Requirements

### Localhost Services
- **MongoDB**: localhost:27017
- **PostgreSQL**: localhost:5432
- **Oracle**:
  - localhost:1521 (listener)
  - Connection to FREEPDB1 PDB

### No External Network Required
All connections are localhost-only. No internet access needed for benchmarks (only for initial setup/package installation).

## Sudo/Permission Requirements

### Commands Requiring Sudo
```bash
# Database service management
sudo systemctl start mongod
sudo systemctl stop mongod
sudo systemctl start postgresql-17
sudo systemctl stop postgresql-17
sudo systemctl start oracle-free-26ai
sudo systemctl stop oracle-free-26ai

# Page cache clearing (for cache-clear restarts)
sudo sync
echo 3 | sudo tee /proc/sys/vm/drop_caches

# PostgreSQL readiness check
sudo -u postgres psql -c 'SELECT 1;'

# Server-side profiling
sudo perf record -F 99 -g -p <pid>
sudo perf script -i <file>
sudo kill -INT <pid>

# Oracle operations (if needed)
sudo -u oracle <command>
```

### User Requirements
- User must be in `sudoers` with permission for above commands
- No password prompt for systemctl commands (recommended for automation)
- Oracle user must exist on system (for Oracle profiling)

## Environment Variables

### Not Required
The script does not require any environment variables to be set. All configuration is via:
- Command-line arguments
- `config.properties` file
- Hardcoded defaults in script

### Oracle Environment (for manual operations)
If manually running Oracle commands outside the script:
```bash
export ORACLE_HOME=/opt/oracle/product/26ai/dbhomeFree
export ORACLE_SID=FREE
export PATH=$ORACLE_HOME/bin:$PATH
export LD_LIBRARY_PATH=$ORACLE_HOME/lib:$LD_LIBRARY_PATH
```

## Differences Between Local and Remote Systems

### Potential Environment Differences

| Aspect | Local System | Remote System (oci-opc) |
|--------|-------------|-------------------------|
| **OS** | May vary | Oracle Linux 9.6 |
| **Data location** | May vary | `/mnt/benchmarks/` (1TB partition) |
| **Oracle version** | May vary | Oracle 23ai Free Edition |
| **PostgreSQL version** | May vary | PostgreSQL 17 |
| **MongoDB version** | May vary | MongoDB 6.0+ |
| **Profiling tools** | May not be installed | async-profiler + FlameGraph installed |
| **Disk space** | May vary | 984GB free on `/mnt/benchmarks` |

### System-Specific Configuration Needed

**Before running on a new system, verify:**
1. All databases installed and services configured
2. `config.properties` created with correct connection strings
3. Database credentials match (especially Oracle password)
4. Sudo permissions configured
5. If profiling: async-profiler and FlameGraph tools installed
6. Sufficient disk space (especially for Oracle 12GB limit)
7. JAR file built: `mvn clean package`

## Troubleshooting Common Issues

### Oracle Won't Start
- Check PDB size: `df -h /mnt/benchmarks/oracle_data`
- If > 12GB: Recreate PDB (see error message in script output)
- Check ORACLE_HOME and paths
- Verify listener is running: `lsnrctl status`

### MongoDB Connection Failed
- Check service: `systemctl status mongod`
- Check port: `ss -tlnp | grep 27017`
- Verify config.properties connection string

### Sudo Permission Denied
- Add user to sudoers for systemctl commands
- For profiling: Add `perf` and `kill` commands to sudoers

### Profiling Not Working
- Client-side: Run `./scripts/setup_async_profiler.sh`
- Server-side: Install FlameGraph tools and Perl modules
- Check `perf_event_paranoid` setting: `cat /proc/sys/kernel/perf_event_paranoid`

### Disk Space Issues
- Oracle: Max 12GB for Free Edition
- Flame graphs: ~1-5MB per test (can accumulate)
- Temporary files in `/tmp` during profiling
- Check: `df -h`

## Summary Checklist

Before running benchmarks on any system:

- [ ] Linux OS with systemd
- [ ] sudo access configured
- [ ] Java installed (OpenJDK or Oracle JDK)
- [ ] Maven installed (for building JAR)
- [ ] MongoDB installed and configured
- [ ] PostgreSQL 17 installed and configured
- [ ] Oracle 23ai Free Edition installed and configured
- [ ] `mongosh` installed
- [ ] `sqlplus` installed
- [ ] `config.properties` created from example
- [ ] Oracle password matches `G0_4w4y!` OR script modified
- [ ] PDB `FREEPDB1` created and open
- [ ] JAR file built: `target/insertTest-1.0-jar-with-dependencies.jar`
- [ ] (Optional) async-profiler installed at `/opt/async-profiler/`
- [ ] (Optional) FlameGraph tools installed
- [ ] (Optional) `perf` and `perl-open` packages installed
- [ ] Sufficient disk space (>15GB recommended)

## Quick Setup Commands

```bash
# Build JAR file
mvn clean package

# Create config file
cp config/config.properties.example config.properties
vi config.properties  # Add your connection strings

# Install profiling tools (optional)
./scripts/setup_async_profiler.sh
git clone https://github.com/brendangregg/FlameGraph
sudo yum install -y perf perl-open

# Verify databases are running
sudo systemctl status mongod postgresql-17 oracle-free-26ai

# Run basic benchmark (no profiling)
python3 scripts/run_article_benchmarks.py --queries --mongodb --oracle

# Run with full profiling
python3 scripts/run_article_benchmarks.py --queries --mongodb --oracle \
  --monitor --flame-graph --server-profile
```

## Running the Benchmark

### Basic Example

Run both test phases (no-index insertion + indexed with queries) on MongoDB and Oracle with statistics disabled for fair comparison:

```bash
# Phase 1: No-index insertion tests (pure insertion performance)
python3 scripts/run_article_benchmarks.py --no-index --nostats --mongodb --oracle

# Phase 2: Indexed with queries (insertion + query performance)
python3 scripts/run_article_benchmarks.py --queries --nostats --mongodb --oracle

# Or run both phases sequentially in background with timeout
nohup bash -c 'timeout 1800 python3 scripts/run_article_benchmarks.py --no-index --nostats --mongodb --oracle > noindex.log 2>&1 && \
               timeout 1800 python3 scripts/run_article_benchmarks.py --queries --nostats --mongodb --oracle > indexed.log 2>&1' &
```

**Basic Output:**
- Console: Real-time test progress with timing results
- `article_benchmark_results.json`: Performance data for all tests
- Summary table showing insertion times and query performance

### Complete Example (Full Profiling)

Run comprehensive benchmarks with all profiling options and large items enabled:

```bash
# Single command with all options
nohup bash -c '\
  timeout 3600 python3 scripts/run_article_benchmarks.py \
    --no-index --nostats --mongodb --oracle \
    --large-items --monitor --flame-graph --server-profile \
    > noindex_full.log 2>&1 && \
  timeout 3600 python3 scripts/run_article_benchmarks.py \
    --queries --nostats --mongodb --oracle \
    --large-items --monitor --flame-graph --server-profile \
    > indexed_full.log 2>&1' > /dev/null 2>&1 &

# Monitor progress
tail -f noindex_full.log
```

**Command Breakdown:**
- `--no-index`: Run insertion-only tests without indexes
- `--queries`: Run tests with indexes and query performance tests
- `--nostats`: Disable Oracle statistics gathering for fair comparison
- `--mongodb`: Test MongoDB BSON storage
- `--oracle`: Test Oracle JSON Collection Tables
- `--large-items`: Include 10KB, 100KB, 1000KB payload tests
- `--monitor`: Track CPU, disk, network usage during tests
- `--flame-graph`: Generate client-side Java flame graphs (async-profiler)
- `--server-profile`: Generate server-side database flame graphs (Linux perf)
- `timeout 3600`: 60-minute timeout per phase (required for large items)

**Complete Output Files:**

```
project_root/
├── noindex_full.log                          # Phase 1 benchmark log
├── indexed_full.log                          # Phase 2 benchmark log
├── article_benchmark_results.json            # Performance metrics (JSON)
├── resource_metrics.json                     # System resource usage data
├── flamegraphs/                              # Client-side profiling
│   ├── mongodb_bson_insert_10B_1attrs_*.html
│   ├── mongodb_bson_query_200B_10attrs_*.html
│   ├── oracle_jct_insert_1000B_50attrs_*.html
│   └── ... (~60 HTML files for full run)
└── server_flamegraphs/                       # Server-side profiling
    ├── mongodb_server_*.svg
    ├── oracle_server_*.svg
    └── ... (~60 SVG files for full run)
```

**Output File Details:**

1. **Log Files** (`noindex_full.log`, `indexed_full.log`)
   - Real-time benchmark progress
   - Timing results for each test
   - Summary tables at end
   - Location: Project root

2. **Performance Data** (`article_benchmark_results.json`)
   - Structured JSON with all test results
   - Insertion times, query times, throughput rates
   - Used for generating HTML reports
   - Location: Project root

3. **Resource Metrics** (`resource_metrics.json`)
   - CPU usage per core
   - Disk I/O statistics
   - Network traffic
   - Memory usage
   - Timestamps for correlation with tests
   - Location: Project root

4. **Client Flame Graphs** (`flamegraphs/*.html`)
   - Interactive HTML flame graphs
   - Profile Java client application (JDBC, JSON serialization)
   - ~1-2MB per file
   - Naming: `{database}_{operation}_{size}B_{attrs}attrs_{timestamp}.html`
   - Location: `flamegraphs/` directory

5. **Server Flame Graphs** (`server_flamegraphs/*.svg`)
   - Interactive SVG flame graphs
   - Profile database server processes (storage engine, query execution)
   - ~500KB-2MB per file
   - Naming: `{database}_server_{timestamp}.svg`
   - Location: `server_flamegraphs/` directory

### Generating HTML Report

After benchmarks complete, generate a comprehensive HTML report with charts and flame graph links:

```bash
# Step 1: Parse log files to extract performance data
python3 scripts/create_summaries_from_logs.py

# Step 2: Generate unified HTML report with all flame graphs
cp flamegraph_summaries.json report/
cd report && python3 generate_unified_report.py

# Output files:
#   - unified_benchmark_report.html (standalone HTML report)
#   - benchmark_report_package.zip  (distributable archive with all flame graphs)
```

**HTML Report Contents:**
- Interactive performance charts (insertion, query)
- Side-by-side MongoDB vs Oracle comparison
- Flame graph links for deep-dive analysis
- Executive summary with key findings
- System configuration details

**Distributable Package** (`benchmark_report_package.zip`):
```
extracted_folder/
├── unified_benchmark_report.html    # Open this in browser
├── flamegraphs/                     # 60+ client-side flame graphs
└── server_flamegraphs/              # 60+ server-side flame graphs
```

The package is fully self-contained and can be shared with others for analysis on any system with a modern web browser.

### Expected Duration

| Configuration | Phase 1 (No-Index) | Phase 2 (Indexed) | Total |
|--------------|-------------------|-------------------|-------|
| **Basic** (no profiling) | 10-15 min | 15-20 min | 25-35 min |
| **Standard tests** + profiling | 15-20 min | 20-25 min | 35-45 min |
| **Large items** + profiling | 45-60 min | 45-60 min | 90-120 min |

**Note:** Use 30-minute timeout for standard tests, 60-minute timeout for tests with `--large-items`.
