#!/usr/bin/env python3
"""
System resource monitoring script for benchmark instrumentation.
Collects CPU, disk, and network utilization every 5 seconds.
"""

import time
import json
import os
import signal
import sys
from datetime import datetime
from pathlib import Path

class ResourceMonitor:
    def __init__(self, interval=5, output_file="resource_metrics.json"):
        self.interval = interval
        self.output_file = output_file
        self.running = True
        self.metrics = []

        # Track previous values for delta calculations
        self.prev_cpu_stats = None
        self.prev_disk_stats = {}
        self.prev_net_stats = {}

        # Set up signal handler for graceful shutdown
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        print(f"\nReceived signal {signum}, shutting down...")
        self.running = False

    def _read_cpu_stats(self):
        """Read CPU statistics from /proc/stat."""
        with open('/proc/stat', 'r') as f:
            line = f.readline()
            # cpu  user nice system idle iowait irq softirq steal guest guest_nice
            fields = line.split()
            if fields[0] == 'cpu':
                return {
                    'user': int(fields[1]),
                    'nice': int(fields[2]),
                    'system': int(fields[3]),
                    'idle': int(fields[4]),
                    'iowait': int(fields[5]),
                    'irq': int(fields[6]),
                    'softirq': int(fields[7]),
                    'steal': int(fields[8]) if len(fields) > 8 else 0
                }
        return None

    def _calculate_cpu_usage(self, prev, curr):
        """Calculate CPU usage percentage between two snapshots."""
        if prev is None or curr is None:
            return None

        # Calculate total time
        prev_total = sum(prev.values())
        curr_total = sum(curr.values())
        total_delta = curr_total - prev_total

        if total_delta == 0:
            return None

        # Calculate idle time
        prev_idle = prev['idle'] + prev['iowait']
        curr_idle = curr['idle'] + curr['iowait']
        idle_delta = curr_idle - prev_idle

        # Calculate usage
        usage = 100.0 * (total_delta - idle_delta) / total_delta

        # Calculate individual components
        iowait_pct = 100.0 * (curr['iowait'] - prev['iowait']) / total_delta
        system_pct = 100.0 * (curr['system'] - prev['system']) / total_delta
        user_pct = 100.0 * (curr['user'] - prev['user']) / total_delta

        return {
            'total': round(usage, 2),
            'user': round(user_pct, 2),
            'system': round(system_pct, 2),
            'iowait': round(iowait_pct, 2)
        }

    def _read_disk_stats(self):
        """Read disk I/O statistics from /proc/diskstats."""
        stats = {}
        with open('/proc/diskstats', 'r') as f:
            for line in f:
                fields = line.split()
                # We want major block devices (8 = SCSI, 259 = NVMe)
                major = int(fields[0])
                minor = int(fields[1])
                device = fields[2]

                # Skip partitions (only track whole disks)
                if major in [8, 259] and (minor % 16 == 0 or device.startswith('nvme')):
                    stats[device] = {
                        'reads_completed': int(fields[3]),
                        'sectors_read': int(fields[5]),
                        'writes_completed': int(fields[7]),
                        'sectors_written': int(fields[9]),
                        'io_time_ms': int(fields[12])
                    }
        return stats

    def _calculate_disk_usage(self, prev, curr):
        """Calculate disk I/O rates between two snapshots."""
        if not prev or not curr:
            return None

        results = {}
        for device in curr:
            if device in prev:
                p = prev[device]
                c = curr[device]

                # Calculate deltas (sectors are 512 bytes)
                read_bytes = (c['sectors_read'] - p['sectors_read']) * 512
                write_bytes = (c['sectors_written'] - p['sectors_written']) * 512
                reads = c['reads_completed'] - p['reads_completed']
                writes = c['writes_completed'] - p['writes_completed']

                # Convert to rates (per second)
                read_mb_s = read_bytes / (1024 * 1024 * self.interval)
                write_mb_s = write_bytes / (1024 * 1024 * self.interval)
                read_iops = reads / self.interval
                write_iops = writes / self.interval

                results[device] = {
                    'read_mb_s': round(read_mb_s, 2),
                    'write_mb_s': round(write_mb_s, 2),
                    'read_iops': round(read_iops, 2),
                    'write_iops': round(write_iops, 2),
                    'total_iops': round((reads + writes) / self.interval, 2)
                }

        return results

    def _read_network_stats(self):
        """Read network statistics from /proc/net/dev."""
        stats = {}
        with open('/proc/net/dev', 'r') as f:
            # Skip header lines
            next(f)
            next(f)
            for line in f:
                fields = line.split()
                interface = fields[0].rstrip(':')

                # Skip loopback
                if interface == 'lo':
                    continue

                stats[interface] = {
                    'rx_bytes': int(fields[1]),
                    'rx_packets': int(fields[2]),
                    'tx_bytes': int(fields[9]),
                    'tx_packets': int(fields[10])
                }
        return stats

    def _calculate_network_usage(self, prev, curr):
        """Calculate network transfer rates between two snapshots."""
        if not prev or not curr:
            return None

        results = {}
        for interface in curr:
            if interface in prev:
                p = prev[interface]
                c = curr[interface]

                # Calculate deltas
                rx_bytes = c['rx_bytes'] - p['rx_bytes']
                tx_bytes = c['tx_bytes'] - p['tx_bytes']
                rx_packets = c['rx_packets'] - p['rx_packets']
                tx_packets = c['tx_packets'] - p['tx_packets']

                # Convert to rates (per second)
                rx_mb_s = rx_bytes / (1024 * 1024 * self.interval)
                tx_mb_s = tx_bytes / (1024 * 1024 * self.interval)
                rx_pps = rx_packets / self.interval
                tx_pps = tx_packets / self.interval

                # Only include active interfaces
                if rx_bytes > 0 or tx_bytes > 0:
                    results[interface] = {
                        'rx_mb_s': round(rx_mb_s, 3),
                        'tx_mb_s': round(tx_mb_s, 3),
                        'rx_pps': round(rx_pps, 2),
                        'tx_pps': round(tx_pps, 2)
                    }

        return results

    def collect_snapshot(self):
        """Collect a single snapshot of all metrics."""
        timestamp = datetime.now().isoformat()

        # Read current stats
        cpu_stats = self._read_cpu_stats()
        disk_stats = self._read_disk_stats()
        net_stats = self._read_network_stats()

        # Calculate usage rates
        cpu_usage = self._calculate_cpu_usage(self.prev_cpu_stats, cpu_stats)
        disk_usage = self._calculate_disk_usage(self.prev_disk_stats, disk_stats)
        net_usage = self._calculate_network_usage(self.prev_net_stats, net_stats)

        # Store current as previous for next iteration
        self.prev_cpu_stats = cpu_stats
        self.prev_disk_stats = disk_stats
        self.prev_net_stats = net_stats

        # Only record if we have calculated values (skip first iteration)
        if cpu_usage is not None:
            snapshot = {
                'timestamp': timestamp,
                'cpu': cpu_usage,
                'disk': disk_usage or {},
                'network': net_usage or {}
            }
            self.metrics.append(snapshot)

            # Print summary to stdout
            print(f"[{timestamp}] CPU: {cpu_usage['total']:5.1f}% | "
                  f"IO-Wait: {cpu_usage['iowait']:5.1f}% | "
                  f"Disk IOPS: {sum(d.get('total_iops', 0) for d in disk_usage.values()) if disk_usage else 0:6.0f}")

    def run(self):
        """Main monitoring loop."""
        print(f"Resource monitoring started (interval: {self.interval}s)")
        print(f"Output file: {self.output_file}")
        print(f"Metrics: CPU, Disk I/O, Network")
        print("-" * 80)

        try:
            while self.running:
                self.collect_snapshot()
                time.sleep(self.interval)

        except KeyboardInterrupt:
            print("\nMonitoring interrupted by user")

        finally:
            self.save_results()

    def save_results(self):
        """Save collected metrics to JSON file."""
        output_data = {
            'monitoring_config': {
                'interval_seconds': self.interval,
                'start_time': self.metrics[0]['timestamp'] if self.metrics else None,
                'end_time': self.metrics[-1]['timestamp'] if self.metrics else None,
                'samples_collected': len(self.metrics)
            },
            'metrics': self.metrics,
            'summary': self._calculate_summary()
        }

        with open(self.output_file, 'w') as f:
            json.dump(output_data, f, indent=2)

        print(f"\n{'='*80}")
        print(f"Monitoring stopped. {len(self.metrics)} samples collected.")
        print(f"Results saved to: {self.output_file}")
        print(f"{'='*80}")

    def _calculate_summary(self):
        """Calculate summary statistics from collected metrics."""
        if not self.metrics:
            return {}

        cpu_totals = [m['cpu']['total'] for m in self.metrics]
        cpu_iowaits = [m['cpu']['iowait'] for m in self.metrics]

        # Aggregate disk IOPS across all devices
        disk_iops = []
        for m in self.metrics:
            total_iops = sum(d.get('total_iops', 0) for d in m['disk'].values())
            disk_iops.append(total_iops)

        return {
            'cpu': {
                'avg': round(sum(cpu_totals) / len(cpu_totals), 2),
                'max': round(max(cpu_totals), 2),
                'min': round(min(cpu_totals), 2),
                'avg_iowait': round(sum(cpu_iowaits) / len(cpu_iowaits), 2),
                'max_iowait': round(max(cpu_iowaits), 2)
            },
            'disk': {
                'avg_iops': round(sum(disk_iops) / len(disk_iops), 2),
                'max_iops': round(max(disk_iops), 2),
                'min_iops': round(min(disk_iops), 2)
            }
        }

def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Monitor system resources during benchmarks')
    parser.add_argument('--interval', '-i', type=int, default=5,
                        help='Sampling interval in seconds (default: 5)')
    parser.add_argument('--output', '-o', type=str, default='resource_metrics.json',
                        help='Output JSON file (default: resource_metrics.json)')
    args = parser.parse_args()

    monitor = ResourceMonitor(interval=args.interval, output_file=args.output)
    monitor.run()

if __name__ == '__main__':
    main()
