# System Resource Monitoring for Benchmarks

## Overview

The benchmark suite now includes integrated system resource monitoring that collects CPU, disk, and network utilization data during test execution. This helps understand system bottlenecks and resource consumption patterns.

## Features

### Metrics Collected (every 5 seconds by default)

**CPU Metrics:**
- Total CPU utilization (%)
- User CPU time (%)
- System CPU time (%)
- I/O wait time (%)

**Disk Metrics (per device):**
- Read throughput (MB/s)
- Write throughput (MB/s)
- Read IOPS
- Write IOPS
- Total IOPS

**Network Metrics (per active interface):**
- Receive throughput (MB/s)
- Transmit throughput (MB/s)
- Receive packets/second
- Transmit packets/second

## Usage

### Enable Monitoring in Benchmarks

Add the `--monitor` flag to any benchmark command:

```bash
# Basic benchmark with monitoring
python3 scripts/run_article_benchmarks.py --mongodb --oracle --queries --monitor

# Custom monitoring interval (default: 5 seconds)
python3 scripts/run_article_benchmarks.py --mongodb --queries --monitor --monitor-interval 3

# Full comparison with monitoring
python3 scripts/run_article_benchmarks.py --full-comparison --monitor
```

### Standalone Monitoring

Run the monitor independently for custom scenarios:

```bash
# Monitor for 60 seconds with 5-second intervals
timeout 60 python3 scripts/monitor_resources.py --interval 5 --output my_metrics.json

# Monitor indefinitely (Ctrl+C to stop)
python3 scripts/monitor_resources.py --interval 10 --output system_metrics.json
```

## Output Format

### Monitoring Data Structure

```json
{
  "monitoring_config": {
    "interval_seconds": 5,
    "start_time": "2025-11-05T08:45:26.778416",
    "end_time": "2025-11-05T08:45:51.803744",
    "samples_collected": 6
  },
  "metrics": [
    {
      "timestamp": "2025-11-05T08:45:26.778416",
      "cpu": {
        "total": 19.54,
        "user": 14.79,
        "system": 2.67,
        "iowait": 0.02
      },
      "disk": {
        "sda": {
          "read_mb_s": 0.0,
          "write_mb_s": 0.33,
          "read_iops": 0.4,
          "write_iops": 67.4,
          "total_iops": 67.8
        }
      },
      "network": {}
    }
  ],
  "summary": {
    "cpu": {
      "avg": 29.25,
      "max": 39.64,
      "min": 19.54,
      "avg_iowait": 0.05,
      "max_iowait": 0.08
    },
    "disk": {
      "avg_iops": 97.87,
      "max_iops": 139.8,
      "min_iops": 61.6
    }
  }
}
```

### Merged Benchmark Results

When `--monitor` is enabled, resource data is automatically merged into the benchmark results file:

```json
{
  "timestamp": "2025-11-05T08:45:56.123456",
  "configuration": {
    "documents": 1000,
    "runs": 3,
    "batch_size": 500,
    "query_tests_enabled": true,
    "monitoring_enabled": true
  },
  "single_attribute": { ... },
  "multi_attribute": { ... },
  "resource_monitoring": {
    "monitoring_config": { ... },
    "metrics": [ ... ],
    "summary": { ... }
  }
}
```

## Analyzing Results

### Quick Summary

```bash
# View monitoring summary
jq '.resource_monitoring.summary' article_benchmark_results.json

# View CPU metrics over time
jq '.resource_monitoring.metrics[].cpu.total' article_benchmark_results.json

# View disk IOPS over time
jq '.resource_monitoring.metrics[].disk.sda.total_iops' article_benchmark_results.json
```

### Key Metrics to Watch

**CPU Bottleneck Indicators:**
- `cpu.total > 90%` - System is CPU-bound
- `cpu.iowait > 10%` - I/O bottleneck (waiting for disk)
- `cpu.user` vs `cpu.system` - Application vs kernel overhead

**Disk Bottleneck Indicators:**
- High IOPS (>10,000 for SATA, >50,000 for NVMe) may indicate I/O saturation
- `cpu.iowait > 10%` combined with low throughput indicates disk bottleneck
- Consistent `write_mb_s` near physical limits (~500 MB/s SATA, ~3000 MB/s NVMe)

**Network Bottleneck Indicators:**
- Throughput approaching link speed (1000 MB/s for 10Gbit, 125 MB/s for 1Gbit)
- High packet rates (>100k pps) may cause CPU overhead

## Example: Comparing MongoDB vs Oracle

```bash
# Run benchmark with monitoring
python3 scripts/run_article_benchmarks.py --mongodb --oracle --queries --monitor

# Extract CPU utilization for each database test
jq '.resource_monitoring.metrics[] | {timestamp, cpu: .cpu.total}' article_benchmark_results.json

# Compare average CPU usage
echo "MongoDB CPU avg:" $(jq -r '.resource_monitoring.summary.cpu.avg' article_benchmark_results.json)

# Check I/O wait during Oracle tests
jq '.resource_monitoring.metrics[] | select(.cpu.iowait > 1) | {timestamp, iowait: .cpu.iowait}' article_benchmark_results.json
```

## Technical Details

### Data Sources

- **CPU**: `/proc/stat` (system-wide aggregated stats)
- **Disk**: `/proc/diskstats` (per-device I/O statistics)
- **Network**: `/proc/net/dev` (per-interface traffic counters)

### Calculation Methods

**CPU Usage:**
```
total_time = sum(user, nice, system, idle, iowait, irq, softirq, steal)
idle_time = idle + iowait
cpu_usage = ((total_time - idle_time) / total_time) * 100
```

**Disk Rates:**
```
read_mb_s = (sectors_read_delta * 512) / (1024 * 1024 * interval)
iops = operations_delta / interval
```

**Network Rates:**
```
rx_mb_s = bytes_received_delta / (1024 * 1024 * interval)
pps = packets_delta / interval
```

### Limitations

- First sample is skipped (requires two measurements to calculate rates)
- Monitoring adds minimal overhead (~0.1% CPU per sample)
- Network metrics only show active interfaces (with traffic during interval)
- Disk metrics aggregate all partitions into parent device
- No per-process breakdown (system-wide metrics only)

## Troubleshooting

### Monitoring Script Not Found

Ensure `monitor_resources.py` is in the same directory as `run_article_benchmarks.py`:

```bash
ls -l monitor_resources.py
chmod +x monitor_resources.py
```

### Permission Denied Errors

The monitor reads `/proc` files which are world-readable. No special permissions needed.

### High CPU from Monitoring

If monitoring impacts benchmarks:
- Increase interval: `--monitor-interval 10`
- Run monitoring on separate machine (not recommended for accuracy)

### Missing Metrics

- **No network data**: Normal if no network traffic during interval
- **No disk data**: System may be using memory cache
- **Zero iowait**: CPU not waiting for I/O (either no I/O or not bottlenecked)

## Best Practices

1. **Use consistent intervals**: 5 seconds balances resolution and overhead
2. **Long-running tests**: Monitoring overhead is negligible for tests >60 seconds
3. **Short tests**: For <10 second tests, use longer intervals (--monitor-interval 10)
4. **Baseline comparison**: Run tests with and without monitoring to measure overhead
5. **System isolation**: Stop background services for cleaner data

## Integration with CLAUDE.md

The monitoring feature has been documented in the main project CLAUDE.md. To use monitoring with the article benchmark command:

```bash
# Standard article benchmark with monitoring
python3 scripts/run_article_benchmarks.py --queries --mongodb --oracle --monitor

# With custom interval
python3 scripts/run_article_benchmarks.py --queries --mongodb --oracle --monitor --monitor-interval 3
```

## Files

- `monitor_resources.py` - Standalone monitoring script
- `resource_metrics.json` - Default monitoring output (standalone)
- `resource_metrics_full.json` - Full comparison mode monitoring output
- `article_benchmark_results.json` - Benchmark results with merged monitoring data
