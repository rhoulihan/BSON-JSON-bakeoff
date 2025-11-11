#!/usr/bin/env python3
"""
Server-side profiling for MongoDB and Oracle using Linux perf and FlameGraph.
Profiles database server processes during benchmark execution.
"""

import subprocess
import sys
import time
import os
import signal
import argparse
from datetime import datetime

class ServerProfiler:
    def __init__(self, database, output_dir="server_flamegraphs", flamegraph_dir=None):
        """
        Initialize server profiler.

        Args:
            database: "mongodb" or "oracle"
            output_dir: Directory to save flame graphs
            flamegraph_dir: Path to FlameGraph tools (auto-detected if None)
        """
        self.database = database.lower()
        self.output_dir = output_dir
        self.perf_pid = None
        self.perf_data_file = None

        # Auto-detect FlameGraph directory
        if flamegraph_dir is None:
            possible_locations = [
                "./FlameGraph",
                "/opt/FlameGraph",
                os.path.expanduser("~/FlameGraph"),
            ]
            for loc in possible_locations:
                if os.path.exists(os.path.join(loc, "flamegraph.pl")):
                    flamegraph_dir = loc
                    break

        if flamegraph_dir is None or not os.path.exists(flamegraph_dir):
            raise RuntimeError(
                "FlameGraph tools not found. Please run: "
                "git clone https://github.com/brendangregg/FlameGraph"
            )

        self.flamegraph_dir = flamegraph_dir
        os.makedirs(output_dir, exist_ok=True)

    def find_mongodb_pid(self):
        """Find the MongoDB mongod process ID."""
        try:
            result = subprocess.run(
                ["pgrep", "-x", "mongod"],
                capture_output=True,
                text=True,
                check=True
            )
            pids = result.stdout.strip().split('\n')
            if len(pids) > 1:
                print(f"Warning: Multiple mongod processes found: {pids}")
                print(f"Using first one: {pids[0]}")
            return int(pids[0])
        except subprocess.CalledProcessError:
            print("Error: No mongod process found")
            return None
        except (ValueError, IndexError):
            print("Error: Failed to parse mongod PID")
            return None

    def find_oracle_pids(self):
        """
        Find ALL Oracle dedicated server process IDs that handle queries.
        Returns a list of PIDs instead of a single PID for comprehensive profiling.

        Oracle uses dedicated server processes (oracleFREE) to handle client connections
        and execute SQL. PMON is just a monitoring process and doesn't show query activity.
        """
        # Find all oracleFREE dedicated server processes (these execute the actual queries)
        try:
            result = subprocess.run(
                ["pgrep", "-f", "oracleFREE"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0 and result.stdout.strip():
                pids = [int(pid.strip()) for pid in result.stdout.strip().split('\n') if pid.strip().isdigit()]
                if pids:
                    print(f"Found {len(pids)} Oracle dedicated server process(es): {pids}")
                    return pids
        except Exception as e:
            print(f"Error finding oracleFREE processes: {e}")

        # Fallback: try to find any Oracle processes for FREE database
        print("Warning: No dedicated server processes found, trying alternate methods...")

        # Try finding by LOCAL=YES (indicates local dedicated server)
        try:
            result = subprocess.run(
                ["bash", "-c", "ps -ef | grep -i 'LOCAL=YES' | grep -v grep | awk '{print $2}'"],
                capture_output=True,
                text=True,
                timeout=10
            )
            pids_str = result.stdout.strip().split('\n')
            pids = [int(pid) for pid in pids_str if pid.strip().isdigit()]
            if pids:
                print(f"Found Oracle processes via LOCAL=YES: {pids}")
                return pids
        except Exception as e:
            pass

        print("Error: No Oracle dedicated server processes found")
        print("Make sure Oracle is running and handling connections")
        return []

    def get_oracle_user(self):
        """Get the Oracle database user (usually 'oracle')."""
        # Try to find oracle user from running processes
        try:
            result = subprocess.run(
                ["bash", "-c", "ps -eo user,comm | grep -E '(db_pmon_FREE|ora_pmon_FREE)' | head -1 | awk '{print $1}'"],
                capture_output=True,
                text=True,
                timeout=5
            )
            user = result.stdout.strip()
            if user:
                print(f"Detected Oracle user: {user}")
                return user
        except:
            pass

        # Default to 'oracle'
        return "oracle"

    def find_oracle_pid(self):
        """
        For Oracle, return special marker to indicate we should profile by user.
        Since dedicated server processes spawn after client connection,
        we need to profile all Oracle processes dynamically.
        """
        # Return special marker that signals start_profiling to use user-based profiling
        return "PROFILE_BY_USER"

    def find_server_pid(self):
        """Find the appropriate server process ID based on database type."""
        if self.database == "mongodb":
            return self.find_mongodb_pid()
        elif self.database == "oracle":
            return self.find_oracle_pid()
        else:
            raise ValueError(f"Unknown database: {self.database}")

    def start_profiling(self, duration_hint=None):
        """
        Start perf profiling on the server process.

        Args:
            duration_hint: Optional hint for expected duration (for display only)

        Returns:
            True if profiling started successfully, False otherwise
        """
        pid = self.find_server_pid()
        if pid is None:
            print(f"Failed to find {self.database} server process")
            return False

        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.perf_data_file = os.path.join(
            self.output_dir,
            f"{self.database}_server_{timestamp}.perf.data"
        )

        # Build perf command based on profiling mode
        # -F 99: Sample at 99 Hz
        # -g: Capture call graphs
        cmd = ["sudo", "perf", "record", "-F", "99", "-g"]

        if pid == "PROFILE_BY_USER":
            # For Oracle: profile all processes owned by oracle user
            # This catches background processes + dedicated servers as they spawn
            oracle_user = self.get_oracle_user()
            cmd.extend(["-u", oracle_user])
            print(f"Profiling all processes for user: {oracle_user}")
            print(f"  (This will capture Oracle background + dedicated server processes)")
        else:
            # For MongoDB: profile specific PID
            cmd.extend(["-p", str(pid)])
            print(f"Found {self.database} server process: PID {pid}")

        cmd.extend(["-o", self.perf_data_file])

        print(f"Starting perf recording: {' '.join(cmd)}")
        if duration_hint:
            print(f"Expected duration: ~{duration_hint} seconds")

        try:
            self.perf_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            self.perf_pid = self.perf_process.pid

            # Give perf a moment to attach
            time.sleep(2)

            # Check if process is still running
            if self.perf_process.poll() is not None:
                stdout, stderr = self.perf_process.communicate()
                print(f"Error: perf process exited immediately")
                print(f"stdout: {stdout.decode()}")
                print(f"stderr: {stderr.decode()}")
                return False

            print(f"Perf recording started (PID: {self.perf_pid})")
            return True

        except Exception as e:
            print(f"Error starting perf: {e}")
            return False

    def stop_profiling(self):
        """Stop perf profiling and generate flame graph."""
        if self.perf_process is None:
            print("No profiling session active")
            return None

        print("Stopping perf recording...")

        # Find the actual perf process (child of sudo)
        try:
            # Get child processes of sudo
            result = subprocess.run(
                ["pgrep", "-P", str(self.perf_pid)],
                capture_output=True,
                text=True
            )
            child_pids = result.stdout.strip().split('\n')

            # Send SIGINT to all child processes (the actual perf command)
            for child_pid in child_pids:
                if child_pid.strip():
                    subprocess.run(["sudo", "kill", "-INT", child_pid.strip()], timeout=2)

            # Also send to parent sudo process
            subprocess.run(["sudo", "kill", "-INT", str(self.perf_pid)], timeout=2)

            # Wait for process to finish
            self.perf_process.wait(timeout=10)
            print("Perf recording stopped")
        except subprocess.TimeoutExpired:
            print("Timeout waiting for perf to stop, forcing...")
            # Force kill the entire process group
            try:
                subprocess.run(["sudo", "pkill", "-KILL", "-P", str(self.perf_pid)], timeout=2)
                subprocess.run(["sudo", "kill", "-KILL", str(self.perf_pid)], timeout=2)
            except:
                pass
            try:
                self.perf_process.wait(timeout=5)
            except:
                pass
        except Exception as e:
            print(f"Error stopping perf: {e}")
            return None

        # Generate flame graph
        return self.generate_flamegraph()

    def generate_flamegraph(self):
        """Generate flame graph from perf.data file."""
        if self.perf_data_file is None or not os.path.exists(self.perf_data_file):
            print(f"Error: perf data file not found: {self.perf_data_file}")
            return None

        print(f"Generating flame graph from {self.perf_data_file}...")

        base_name = self.perf_data_file.replace('.perf.data', '')
        out_perf = f"{base_name}.out.perf"
        out_folded = f"{base_name}.out.folded"
        out_svg = f"{base_name}.svg"

        try:
            # Step 1: perf script > out.perf
            print("Running perf script...")
            with open(out_perf, 'w') as f:
                subprocess.run(
                    ["sudo", "perf", "script", "-i", self.perf_data_file],
                    stdout=f,
                    stderr=subprocess.PIPE,
                    check=True
                )

            # Step 2: stackcollapse-perf.pl out.perf > out.folded
            print("Collapsing stacks...")
            stackcollapse_script = os.path.join(self.flamegraph_dir, "stackcollapse-perf.pl")
            with open(out_folded, 'w') as f:
                subprocess.run(
                    [stackcollapse_script, out_perf],
                    stdout=f,
                    stderr=subprocess.PIPE,
                    check=True
                )

            # Step 3: flamegraph.pl out.folded > db.svg
            print("Generating flame graph SVG...")
            flamegraph_script = os.path.join(self.flamegraph_dir, "flamegraph.pl")
            with open(out_svg, 'w') as f:
                subprocess.run(
                    [flamegraph_script, out_folded],
                    stdout=f,
                    stderr=subprocess.PIPE,
                    check=True
                )

            print(f"Flame graph generated: {out_svg}")

            # Clean up intermediate files
            for f in [out_perf, out_folded]:
                try:
                    os.remove(f)
                except:
                    pass

            return out_svg

        except subprocess.CalledProcessError as e:
            print(f"Error generating flame graph: {e}")
            if e.stderr:
                print(f"stderr: {e.stderr.decode()}")
            return None
        except Exception as e:
            print(f"Unexpected error: {e}")
            return None


def main():
    parser = argparse.ArgumentParser(
        description="Profile database server processes using perf and FlameGraph"
    )
    parser.add_argument(
        "database",
        choices=["mongodb", "oracle"],
        help="Database to profile"
    )
    parser.add_argument(
        "--duration",
        type=int,
        help="Duration to profile in seconds (for testing)"
    )
    parser.add_argument(
        "--output-dir",
        default="server_flamegraphs",
        help="Output directory for flame graphs"
    )
    parser.add_argument(
        "--flamegraph-dir",
        help="Path to FlameGraph tools directory"
    )

    args = parser.parse_args()

    try:
        profiler = ServerProfiler(
            args.database,
            output_dir=args.output_dir,
            flamegraph_dir=args.flamegraph_dir
        )

        if not profiler.start_profiling(duration_hint=args.duration):
            sys.exit(1)

        if args.duration:
            print(f"Profiling for {args.duration} seconds...")
            time.sleep(args.duration)
            svg_path = profiler.stop_profiling()
            if svg_path:
                print(f"\nFlame graph saved to: {svg_path}")
                print(f"View with: firefox {svg_path}")
            else:
                print("Failed to generate flame graph")
                sys.exit(1)
        else:
            print("\nProfiling started. Press Ctrl+C to stop and generate flame graph...")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n")
                svg_path = profiler.stop_profiling()
                if svg_path:
                    print(f"\nFlame graph saved to: {svg_path}")
                    print(f"View with: firefox {svg_path}")
                else:
                    print("Failed to generate flame graph")
                    sys.exit(1)

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
