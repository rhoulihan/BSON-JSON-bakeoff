"""
Data loading and validation module for benchmark reports.
"""

import json
import subprocess
from pathlib import Path


class BenchmarkDataLoader:
    """Handles loading benchmark data from local and remote sources."""

    def __init__(self):
        self.local_indexed = None
        self.local_noindex = None
        self.remote_indexed = None
        self.remote_noindex = None
        self.local_metrics = None
        self.remote_metrics = None

    @staticmethod
    def load_json(filepath):
        """Load JSON file with error handling."""
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Warning: {filepath} not found")
            return None
        except json.JSONDecodeError:
            print(f"Warning: {filepath} is not valid JSON")
            return None

    def load_local_data(self):
        """Load local benchmark results."""
        print("Loading local results...")
        # Load from article_benchmark_results.json (created by flame-graph runs)
        self.local_indexed = self.load_json('article_benchmark_results.json')
        self.local_noindex = self.load_json('/tmp/local_noindex_nostats_results.json')
        self.local_metrics = self.load_json('resource_metrics.json')

    def fetch_remote_data(self):
        """Fetch remote benchmark results via SCP."""
        print("Fetching remote results...")
        try:
            # Fetch remote indexed results from article_benchmark_results.json
            subprocess.run(
                ['scp', 'oci-opc:BSON-JSON-bakeoff/article_benchmark_results.json',
                 '/tmp/remote_article_benchmark_results.json'],
                check=True, capture_output=True
            )
            subprocess.run(
                ['scp', 'oci-opc:BSON-JSON-bakeoff/resource_metrics.json',
                 '/tmp/remote_resource_metrics.json'],
                check=True, capture_output=True
            )
            subprocess.run(
                ['scp', 'oci-opc:BSON-JSON-bakeoff/tmp/remote_noindex_nostats_results.json',
                 '/tmp/remote_noindex_nostats_results.json'],
                check=True, capture_output=True
            )

            self.remote_indexed = self.load_json('/tmp/remote_article_benchmark_results.json')
            self.remote_noindex = self.load_json('/tmp/remote_noindex_nostats_results.json')
            self.remote_metrics = self.load_json('/tmp/remote_resource_metrics.json')

        except Exception as e:
            print(f"Warning: Could not fetch remote results: {e}")
            # Try loading from local cache
            self.remote_indexed = self.load_json('/tmp/remote_article_benchmark_results.json')
            self.remote_noindex = self.load_json('/tmp/remote_noindex_nostats_results.json')
            self.remote_metrics = self.load_json('/tmp/remote_resource_metrics.json')

    def load_all(self):
        """Load all benchmark data."""
        self.load_local_data()
        self.fetch_remote_data()

        return {
            'local_indexed': self.local_indexed,
            'local_noindex': self.local_noindex,
            'remote_indexed': self.remote_indexed,
            'remote_noindex': self.remote_noindex,
            'local_metrics': self.local_metrics,
            'remote_metrics': self.remote_metrics
        }
