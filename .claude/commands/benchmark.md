---
description: Run comprehensive article benchmarks with interactive configuration
---

Use the AskUserQuestion tool to interactively configure and run benchmarks.

**IMPORTANT**: Due to AskUserQuestion tool's 4-question limit, ask questions in TWO BATCHES:
- **Batch 1**: Questions 1-3 (System, Test Type, Databases)
- **Batch 2**: Questions 4-5 (Config options, Profiling options)

## Questions to Ask (Use AskUserQuestion Tool)

Ask the user these configuration questions using the AskUserQuestion tool in two separate batches:

**Question 1: Which system(s)?**
- Header: "System"
- Question: "Which system(s) should run the benchmarks?"
- Options:
  1. "Local only" - Run only on local system
  2. "Remote only" - Run only on remote system (oci-opc)
  3. "Both systems" - Run on both systems in parallel

**Question 2: Test type**
- Header: "Test Type"
- Question: "Which test type(s) to run?"
- Options:
  1. "Indexed with queries" - --queries (with indexes, includes query tests)
  2. "No-index insertion" - --no-index (insertion-only, no indexes)
  3. "Both phases" - Run both sequentially

**Question 3: Databases**
- Header: "Databases"
- Question: "Which database(s) to test?"
- Options:
  1. "MongoDB only"
  2. "Oracle only"
  3. "Both databases"

**Question 4: Test configuration** (multi-select enabled)
- Header: "Config"
- Question: "Select test configuration options:"
- Options:
  1. "Large items" - Include 10KB, 100KB, 1000KB tests (--large-items)
  2. "Disable Oracle stats" - Disable statistics gathering for fair comparison (--nostats)

**Question 5: Profiling** (multi-select enabled)
- Header: "Profiling"
- Question: "Select profiling and monitoring options:"
- Options:
  1. "Resource monitoring" - Track CPU/disk/network (--monitor)
  2. "Client profiling" - Java flame graphs with async-profiler (--flame-graph)
  3. "Server profiling" - Database flame graphs with Linux perf (--server-profile)

---

## After Collecting Answers

Based on the user's answers:

1. **Build command flags:**
   - Test type: `--queries` or `--no-index` (or both sequentially)
   - Databases: `--mongodb` and/or `--oracle`
   - Config options: `--large-items`, `--nostats` (as selected)
   - Profiling: `--monitor`, `--flame-graph`, `--server-profile` (as selected)
   - Note: Realistic data (`-rd`) is automatically enabled by run_article_benchmarks.py

2. **Generate appropriate command(s):**
   - For remote system: `ssh oci-opc "cd BSON-JSON-bakeoff && nohup bash -c 'timeout 1800 python3 run_article_benchmarks.py [FLAGS] 2>&1' > ~/remote_benchmark.log 2>&1 &"`
   - For local system: Similar command without SSH
   - For both phases: Chain with `&&` between no-index and queries phases

3. **Execute benchmarks:**
   - Start in background with 30-minute timeout per phase
   - Create monitoring command to check progress every 60 seconds

4. **Monitor and report:**
   - Check log file tail and disk space every 60 seconds
   - Report when complete with summary of tests run
   - Show flame graph file counts and locations

5. **Offer next steps:**
   - Generate unified HTML report (if profiling enabled)
   - Analyze results and compare MongoDB vs Oracle performance
   - Create summaries from logs with flame graph links

**Storage Configuration (current):**
- Remote system: Oracle data on 1TB partition `/mnt/benchmarks` (984GB free)
- Remote system: Root filesystem has 11GB free
- Flame graphs: Temp files cleaned immediately during generation

**Expected Duration:**
- Standard tests (10B-4000B): 15-25 minutes per phase
- With large items: 30-45 minutes per phase
- With profiling: +5-10 minutes per phase
- Both systems in parallel: Same as single system (runs concurrently)
- Both phases sequential: 2× duration

**Output Files:**
- Logs: `remote_benchmark.log` or `local_benchmark.log` (tail with `ssh oci-opc "tail -40 ~/remote_benchmark.log"`)
- Flame graphs (client): `flamegraphs/*.html` (~60 files for full run)
- Flame graphs (server): `server_flamegraphs/*.svg` (~60 files for full run)
- Results JSON: `/tmp/*_results.json`
- Metrics: `resource_metrics.json` (if --monitor enabled)
