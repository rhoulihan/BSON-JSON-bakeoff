# Report Generation Update - Server-Side Flame Graphs

## Overview

The benchmark report generation system has been updated to include **server-side flame graphs** alongside the existing client-side flame graphs. This provides a complete performance analysis picture showing both Java client and database server CPU usage.

## Changes Made

### 1. Updated `flamegraph_report_helper.py`

**New Functions:**
- `discover_server_flamegraphs()` - Discovers and parses server-side flame graphs from `server_flamegraphs/` directory

**Modified Functions:**
- `generate_flamegraph_list_html()` - Now generates two sections:
  - **Client-Side Flame Graphs**: HTML flame graphs from async-profiler (Java app)
  - **Server-Side Flame Graphs**: SVG flame graphs from Linux perf (database servers)

**Features:**
- Automatic discovery of `.svg` files matching pattern: `{database}_server_{timestamp}.svg`
- Displays database, timestamp, file size, and link to flame graph
- Graceful handling when server flame graphs are not available
- Sorted by timestamp (most recent first)

### 2. Updated `generate_unified_report.py`

**Modified Functions:**
- `create_distributable_archive()` - Now bundles both client and server flame graphs
  - Includes `flamegraphs/` directory (client-side HTML files)
  - Includes `server_flamegraphs/` directory (server-side SVG files)

**Updated Documentation:**
- README.txt now explains both flame graph types
- Distinguishes between client-side and server-side profiling

## Report Structure

The updated HTML report now shows flame graphs in two sections:

```
Flame Graphs
├── 📊 Client-Side Flame Graphs
│   ├── MongoDB BSON tests (HTML files)
│   └── Oracle JCT tests (HTML files)
└── 🔥 Server-Side Flame Graphs
    ├── MongoDB server (SVG files)
    └── Oracle server (SVG files)
```

### Client-Side Flame Graphs Section

**Purpose**: Profile Java client application
**Technology**: async-profiler
**Format**: HTML
**Shows**: JDBC driver, JSON serialization, networking overhead

**Table Columns:**
- Database
- Test Description
- Insert Rate (docs/sec)
- Query Rate (queries/sec)
- Flame Graph Link

### Server-Side Flame Graphs Section

**Purpose**: Profile database server processes
**Technology**: Linux perf + FlameGraph
**Format**: SVG
**Shows**: Storage engine, query execution, index operations

**Table Columns:**
- Database (MongoDB / Oracle)
- Timestamp
- File Size
- Flame Graph Link

## Zip File Contents

The distributable zip file now includes:

```
benchmark_report_package.zip
├── unified_benchmark_report.html       (Main report)
├── flamegraphs/                         (Client-side, 64 HTML files)
│   ├── mongodb_bson_insert_*.html
│   └── oracle_jct_insert_*.html
├── server_flamegraphs/                  (Server-side, 5 SVG files)
│   ├── mongodb_server_*.svg
│   └── oracle_server_*.svg
└── README.txt                           (Updated with flame graph types)
```

## Usage

### Generate Benchmarks with Server Profiling

```bash
# Run benchmarks with both client and server profiling
python3 scripts/run_article_benchmarks.py \
  --queries \
  --mongodb \
  --oracle \
  --flame-graph \
  --server-profile
```

This creates:
- `flamegraphs/` - Client-side HTML flame graphs
- `server_flamegraphs/` - Server-side SVG flame graphs

### Generate Report

```bash
# Generate unified report with both flame graph types
python3 report/generate_unified_report.py
```

**Output:**
- `unified_benchmark_report.html` - Interactive HTML report
- `benchmark_report_package.zip` - Distributable package

### View Report

```bash
# Open report in browser
firefox unified_benchmark_report.html

# Or extract and share zip file
unzip benchmark_report_package.zip -d shared_report/
```

## Test Results

Successfully tested report generation:
- ✅ Discovered 5 server-side flame graphs (MongoDB)
- ✅ Added 64 client-side flame graph files to zip
- ✅ Added 5 server-side flame graph files to zip
- ✅ Generated 1.67 MB distributable package
- ✅ HTML includes both flame graph sections
- ✅ Links properly reference `server_flamegraphs/` directory

## Verification Commands

### Check Server Flame Graphs

```bash
# List server flame graphs
ls -lh server_flamegraphs/*.svg

# Test discovery function
python3 -c "
from flamegraph_report_helper import discover_server_flamegraphs
print(f'Found {len(discover_server_flamegraphs())} server flame graphs')
"
```

### Verify Report Contents

```bash
# Check zip contents
unzip -l benchmark_report_package.zip | grep server_flamegraphs

# Check HTML includes server section
grep "Server-Side Flame Graphs" unified_benchmark_report.html

# Check flame graph links
grep -c "server_flamegraphs/.*\.svg" unified_benchmark_report.html
```

## Compatibility

### Backward Compatible
- Report generation works with or without server flame graphs
- If `server_flamegraphs/` directory doesn't exist, displays helpful message
- No breaking changes to existing functionality

### Graceful Degradation
- Client-only flame graphs still work as before
- Server-only flame graphs supported
- Combined client + server flame graphs (recommended)

## Remote System Support

All updates work on remote systems:

```bash
# Copy updated scripts to remote
scp flamegraph_report_helper.py generate_unified_report.py \
    oci-opc:BSON-JSON-bakeoff/

# Run on remote
ssh oci-opc "cd BSON-JSON-bakeoff && \
  python3 report/generate_unified_report.py"

# Copy report back
scp oci-opc:BSON-JSON-bakeoff/benchmark_report_package.zip ./remote_report.zip
```

## Benefits

### Complete Performance Picture
- **Client-side**: See JDBC, serialization, network overhead
- **Server-side**: See storage, indexing, query execution
- **Combined**: Identify whether bottleneck is client or server

### Better Diagnostics
- Pinpoint exact functions consuming CPU
- Compare client vs server overhead
- Validate optimization efforts

### Shareable Analysis
- Single zip file contains everything
- No external dependencies
- Works offline
- Professional presentation

## Example Analysis Workflow

1. **Run benchmarks with profiling**
   ```bash
   python3 scripts/run_article_benchmarks.py --queries --mongodb --oracle \
     --flame-graph --server-profile
   ```

2. **Generate report**
   ```bash
   python3 report/generate_unified_report.py
   ```

3. **Analyze results**
   - Open `unified_benchmark_report.html`
   - Navigate to "Flame Graphs" section
   - Compare client-side vs server-side CPU usage
   - Identify bottlenecks

4. **Share findings**
   - Send `benchmark_report_package.zip`
   - Recipients extract and view in browser
   - All flame graphs accessible via links

## Related Documentation

- `SERVER_PROFILING_README.md` - Server profiling setup and usage
- `CLAUDE.md` - Updated with server profiling documentation
- `MONITORING_README.md` - Resource monitoring features

## Files Modified

| File | Changes |
|------|---------|
| `flamegraph_report_helper.py` | Added server flame graph discovery and HTML generation |
| `generate_unified_report.py` | Updated zip creation to include server_flamegraphs/ |
| `CLAUDE.md` | Updated Flame Graph Profiling section |
| `SERVER_PROFILING_README.md` | New comprehensive documentation |

## Future Enhancements

Potential improvements:
- Parse server flame graph metadata from filenames (size, attrs, test type)
- Match client and server flame graphs by timestamp
- Side-by-side comparison view
- Integrated analysis combining both flame graph types
- CPU overhead comparison metrics

## Conclusion

The report generation system now provides complete visibility into performance by combining client-side and server-side flame graphs in a single, distributable package. This enhancement completes the profiling story and enables comprehensive performance analysis.
