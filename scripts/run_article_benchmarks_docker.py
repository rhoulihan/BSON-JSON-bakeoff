#!/usr/bin/env python3
"""
Benchmark script to replicate tests from LinkedIn article:
"Comparing Document Data Options for Generative AI" (Docker version)

Tests:
- Single attribute: 10B, 200B, 1000B, 2000B, 4000B
- Multi attribute: 10×1B, 10×20B, 50×20B, 100×20B, 200×20B
- 10,000 documents per test
- 3 runs (best time reported)

This version uses Docker containers for MongoDB and DocumentDB.
"""

import subprocess
import json
import re
from datetime import datetime
import sys
import time
import argparse
import random
import os
import signal
import configparser
from pathlib import Path

# Import results storage and metadata collection modules
def _ensure_pymongo_installed():
    """Check if pymongo is importable; if not, attempt to install it."""
    try:
        import pymongo  # noqa: F401
        return True
    except ImportError:
        print("⚠️  pymongo not found, attempting to install...")
        install_cmds = [
            ["pip3", "install", "pymongo"],
            ["pip", "install", "pymongo"],
            [sys.executable, "-m", "pip", "install", "pymongo"],
        ]
        for cmd in install_cmds:
            try:
                subprocess.check_call(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                print("✅ pymongo installed successfully")
                return True
            except (subprocess.CalledProcessError, FileNotFoundError):
                continue
        print("❌ Failed to install pymongo")
        return False

try:
    from results_storage import ResultsStorage, connect_to_mongodb
    from version_detector import get_all_versions
    from system_info_collector import get_system_info, get_ci_info
    import uuid
    RESULTS_STORAGE_AVAILABLE = True
except ImportError as e:
    # Attempt to install missing dependency and retry
    if _ensure_pymongo_installed():
        try:
            from results_storage import ResultsStorage, connect_to_mongodb
            from version_detector import get_all_versions
            from system_info_collector import get_system_info, get_ci_info
            import uuid
            RESULTS_STORAGE_AVAILABLE = True
        except ImportError as e2:
            print(f"⚠️  Warning: Results storage modules not available after install attempt: {e2}")
            RESULTS_STORAGE_AVAILABLE = False
            uuid = None
    else:
        print(f"⚠️  Warning: Results storage modules not available: {e}")
        RESULTS_STORAGE_AVAILABLE = False
        uuid = None

JAR_PATH = "target/insertTest-1.0-jar-with-dependencies.jar"
NUM_DOCS = 10000
NUM_RUNS = 3
BATCH_SIZE = 500
QUERY_LINKS = 10  # Number of array elements for query tests

# Test configurations matching the article
SINGLE_ATTR_TESTS = [
    {"size": 10, "attrs": 1, "desc": "10B single attribute"},
    {"size": 200, "attrs": 1, "desc": "200B single attribute"},
    {"size": 1000, "attrs": 1, "desc": "1000B single attribute"},
    {"size": 2000, "attrs": 1, "desc": "2000B single attribute"},
    {"size": 4000, "attrs": 1, "desc": "4000B single attribute"},
]

# Large item test configurations (enabled with --large-items flag)
LARGE_SINGLE_ATTR_TESTS = [
    {"size": 10000, "attrs": 1, "desc": "10KB single attribute"},
    {"size": 100000, "attrs": 1, "desc": "100KB single attribute"},
    {"size": 1000000, "attrs": 1, "desc": "1000KB single attribute"},
]

MULTI_ATTR_TESTS = [
    {"size": 10, "attrs": 10, "desc": "10 attributes × 1B = 10B"},
    {"size": 200, "attrs": 10, "desc": "10 attributes × 20B = 200B"},
    {"size": 1000, "attrs": 50, "desc": "50 attributes × 20B = 1000B"},
    {"size": 2000, "attrs": 100, "desc": "100 attributes × 20B = 2000B"},
    {"size": 4000, "attrs": 200, "desc": "200 attributes × 20B = 4000B"},
]

# Large multi-attribute test configurations (enabled with --large-items flag)
LARGE_MULTI_ATTR_TESTS = [
    {"size": 10000, "attrs": 200, "desc": "200 attributes × 50B = 10KB"},
    {"size": 100000, "attrs": 500, "desc": "500 attributes × 200B = 100KB"},
    {"size": 1000000, "attrs": 1000, "desc": "1000 attributes × 1000B = 1000KB"},
]

# Databases to test - Docker container versions (all using indexes + realistic data)
DATABASES = [
    {"name": "MongoDB (BSON)", "key": "mongodb", "flags": "-i -rd", "container": "mongodb-benchmark", "db_type": "mongodb", "port": 27017, "image": "mongo"},
    {"name": "DocumentDB", "key": "documentdb", "flags": "-ddb -i -rd", "container": "documentdb-benchmark", "db_type": "documentdb", "port": 10260, "image": "documentdb-local"},
    {"name": "PostgreSQL (JSONB)", "key": "postgresql", "flags": "-p -j -i -rd", "container": "postgres-benchmark", "db_type": "postgresql", "port": 5432, "image": "postgres:latest"},
    {"name": "YugabyteDB (YSQL)", "key": "yugabytedb", "flags": "-p -i -rd", "container": "yugabyte-benchmark", "db_type": "yugabytedb", "port": 5433, "image": "yugabytedb/yugabyte:latest"},
    {"name": "CockroachDB (SQL)", "key": "cockroachdb", "flags": "-p -i -rd", "container": "cockroach-benchmark", "db_type": "cockroachdb", "port": 26257, "image": "cockroachdb/cockroach:latest"},
]

# Cloud/SaaS databases - no Docker containers, connection string from config
# These are added to DATABASES conditionally based on config + CLI flags
CLOUD_DATABASES = [
    {"name": "MongoDB Atlas (Cloud)", "key": "mongodb-cloud", "flags": "-i -rd", "container": None, "db_type": "mongodb-cloud", "port": None, "image": None, "cloud": True, "config_section": "mongodb_atlas"},
    {"name": "Azure DocumentDB (Cloud)", "key": "documentdb-azure", "flags": "-ddb -i -rd", "container": None, "db_type": "documentdb-azure", "port": None, "image": None, "cloud": True, "config_section": "azure_documentdb"},
]

def get_enabled_cloud_databases(config):
    """Return list of cloud database entries that are enabled in config.

    Each cloud database must have enabled=true in its config section AND
    a valid connection_string. Returns copies with 'connection_string' populated.
    """
    enabled = []
    for cloud_db in CLOUD_DATABASES:
        section = cloud_db['config_section']
        if config.has_section(section):
            if config.getboolean(section, 'enabled', fallback=False):
                conn_str = config.get(section, 'connection_string', fallback=None)
                if conn_str:
                    entry = dict(cloud_db)
                    entry['connection_string'] = conn_str
                    enabled.append(entry)
                else:
                    print(f"  WARNING: {cloud_db['name']} is enabled but has no connection_string configured")
    return enabled


def check_cloud_database_ready(db_info):
    """Verify a cloud/SaaS database is reachable.

    Args:
        db_info: Database info dict with 'connection_string' and 'db_type'

    Returns:
        True if the database responds to a ping, False otherwise
    """
    conn_str = db_info.get('connection_string', '')
    db_type = db_info.get('db_type', '')

    try:
        from pymongo import MongoClient
        # Both mongodb-cloud and documentdb-azure use the MongoDB wire protocol
        client = MongoClient(conn_str, serverSelectionTimeoutMS=10000)
        client.admin.command('ping')
        client.close()
        return True
    except Exception as e:
        print(f"    WARNING: Could not connect to {db_info['name']}: {e}")
        return False


def get_cloud_database_version(db_info):
    """Query a cloud database for its version string.

    Args:
        db_info: Database info dict with 'connection_string' and 'db_type'

    Returns:
        Version string or None
    """
    conn_str = db_info.get('connection_string', '')
    try:
        from pymongo import MongoClient
        client = MongoClient(conn_str, serverSelectionTimeoutMS=10000)
        try:
            build_info = client.admin.command('buildInfo')
            version = build_info.get('version')
            client.close()
            return version
        except Exception:
            pass
        try:
            server_info = client.server_info()
            version = server_info.get('version')
            client.close()
            return version
        except Exception:
            pass
        client.close()
    except Exception as e:
        print(f"    WARNING: Could not detect version for {db_info['name']}: {e}")
    return None


def load_benchmark_config():
    """Load benchmark configuration from config/benchmark_config.ini"""
    # Find config file relative to project root (parent of scripts directory)
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    config_file = project_root / "config" / "benchmark_config.ini"

    if not config_file.exists():
        print(f"❌ ERROR: Benchmark config not found: {config_file}")
        print(f"   Please create it from: config/benchmark_config.ini.example")
        sys.exit(1)

    config = configparser.ConfigParser()
    config.read(config_file)
    return config

def detect_ci_environment():
    """Detect CI environment and return metadata."""
    ci_info = {
        'ci_run': False,
        'ci_platform': None,
        'commit_hash': None,
        'branch': None
    }
    
    # Check for generic CI flag
    if os.environ.get('CI'):
        ci_info['ci_run'] = True
        
        # GitHub Actions
        if os.environ.get('GITHUB_ACTIONS'):
            ci_info['ci_platform'] = 'github'
            ci_info['commit_hash'] = os.environ.get('GITHUB_SHA')
            ci_info['branch'] = os.environ.get('GITHUB_REF', '').replace('refs/heads/', '')
        
        # GitLab CI
        elif os.environ.get('GITLAB_CI'):
            ci_info['ci_platform'] = 'gitlab'
            ci_info['commit_hash'] = os.environ.get('CI_COMMIT_SHA')
            ci_info['branch'] = os.environ.get('CI_COMMIT_REF_NAME')
        
        # Jenkins
        elif os.environ.get('JENKINS_URL'):
            ci_info['ci_platform'] = 'jenkins'
            ci_info['commit_hash'] = os.environ.get('GIT_COMMIT')
            ci_info['branch'] = os.environ.get('GIT_BRANCH', '').replace('origin/', '')
        
        # Generic CI
        else:
            ci_info['ci_platform'] = 'unknown'
            # Try to get git info if available
            try:
                result = subprocess.run(
                    ['git', 'rev-parse', 'HEAD'],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                if result.returncode == 0:
                    ci_info['commit_hash'] = result.stdout.strip()
                
                result = subprocess.run(
                    ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                if result.returncode == 0:
                    ci_info['branch'] = result.stdout.strip()
            except Exception:
                pass
    
    return ci_info

def start_monitoring(output_file="resource_metrics.json", interval=5):
    """Start resource monitoring in the background."""
    monitor_script = os.path.join(os.path.dirname(__file__), "monitor_resources.py")

    if not os.path.exists(monitor_script):
        print(f"Warning: Monitoring script not found: {monitor_script}")
        return None

    print(f"Starting resource monitoring (interval: {interval}s)...")

    # Start monitoring process in background
    proc = subprocess.Popen(
        [sys.executable, monitor_script, '--interval', str(interval), '--output', output_file],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        preexec_fn=os.setsid  # Create new process group
    )

    time.sleep(1)  # Give monitor time to start

    if proc.poll() is None:
        print(f"✓ Resource monitoring started (PID: {proc.pid})")
        return proc
    else:
        print("✗ Failed to start resource monitoring")
        return None

def stop_monitoring(monitor_proc):
    """Stop resource monitoring gracefully."""
    if monitor_proc is None:
        return

    print("\nStopping resource monitoring...")

    try:
        # Send SIGTERM to process group to stop monitor gracefully
        os.killpg(os.getpgid(monitor_proc.pid), signal.SIGTERM)

        # Wait up to 10 seconds for process to finish
        monitor_proc.wait(timeout=10)
        print("✓ Resource monitoring stopped")

    except subprocess.TimeoutExpired:
        print("Warning: Monitor didn't stop gracefully, forcing...")
        os.killpg(os.getpgid(monitor_proc.pid), signal.SIGKILL)
        monitor_proc.wait()
    except Exception as e:
        print(f"Warning: Error stopping monitor: {e}")

def generate_resource_metrics_filename(db_type, test_type, size, attrs):
    """Generate a unique filename for resource metrics per test.
    
    Args:
        db_type: Database type (e.g., 'mongodb', 'documentdb')
        test_type: Test type (e.g., 'single_attr', 'multi_attr')
        size: Payload size in bytes
        attrs: Number of attributes
    
    Returns:
        Unique filename string
    """
    timestamp = int(time.time())
    test_type_short = 'single' if test_type == 'single_attr' or attrs == 1 else 'multi'
    filename = f"resource_metrics_{db_type}_{test_type_short}_{size}B_{timestamp}.json"
    return filename

def get_resource_summary_from_file(filepath):
    """Extract resource summary from monitoring output file.
    
    Args:
        filepath: Path to the resource metrics JSON file
    
    Returns:
        Dictionary with resource summary, or None if file doesn't exist or is invalid
    """
    if not filepath or not os.path.exists(filepath):
        return None
    
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
            return data.get('summary', {})
    except Exception as e:
        print(f"    ⚠️  Warning: Could not read resource summary from {filepath}: {e}")
        return None

def print_resource_summary(resource_summary, test_desc=None):
    """Print resource monitoring summary to debug console.
    
    Args:
        resource_summary: Dictionary with resource metrics summary
        test_desc: Optional test description for context
    """
    if not resource_summary:
        return
    
    print(f"    📊 Resource Monitoring Summary" + (f" ({test_desc})" if test_desc else ""))
    print(f"      CPU: avg={resource_summary.get('avg_cpu_percent', 0):.1f}%, max={resource_summary.get('max_cpu_percent', 0):.1f}%")
    print(f"      I/O Wait: avg={resource_summary.get('avg_iowait_percent', 0):.1f}%")
    print(f"      Disk IOPS: avg={resource_summary.get('avg_disk_iops', 0):.0f}, max={resource_summary.get('max_disk_iops', 0):.0f}")
    print(f"      Samples: {resource_summary.get('samples', 0)}")

def stop_all_databases():
    """Stop all Docker containers before starting (skips cloud databases)."""
    print("Stopping all Docker containers...")
    for db in DATABASES:
        if db.get('cloud'):
            continue  # Cloud databases have no containers to stop
        container_name = db['container']
        # Stop and remove container if it exists
        subprocess.run(f"docker rm -f {container_name} 2>/dev/null", shell=True, capture_output=True)
    time.sleep(2)
    print("✓ All Docker containers stopped")
    print()

def start_docker_container(db_info):
    """Start a Docker container for a database and return version info."""
    container_name = db_info['container']
    db_type = db_info['db_type']
    port = db_info['port']
    image = db_info['image']

    # Check if container already exists and remove it
    subprocess.run(f"docker rm -f {container_name} 2>/dev/null", shell=True, capture_output=True)

    if db_type == "mongodb":
        # Start MongoDB container
        cmd = f"docker run --name {container_name} --rm -d -p {port}:27017 {image}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            return False, None

    elif db_type == "documentdb":
        # Ensure DocumentDB image is available
        # First check if image exists, if not pull and tag it
        check_image = subprocess.run(f"docker images -q {image}", shell=True, capture_output=True, text=True)
        if not check_image.stdout.strip():
            print(f"    Pulling DocumentDB image...", end=" ", flush=True)
            pull_result = subprocess.run(
                "docker pull ghcr.io/documentdb/documentdb/documentdb-local:latest",
                shell=True, capture_output=True, text=True
            )
            if pull_result.returncode != 0:
                print("✗ Failed to pull DocumentDB image")
                return False, None
            # Tag the image
            subprocess.run(
                "docker tag ghcr.io/documentdb/documentdb/documentdb-local:latest documentdb-local:latest",
                shell=True, capture_output=True
            )
            print("✓", end="", flush=True)

        # Start DocumentDB container
        cmd = f"docker run --name {container_name} --rm -d -p {port}:10260 {image} --username testuser --password testpass"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            return False, None

    elif db_type == "postgresql":
        # Start PostgreSQL container
        cmd = f"docker run --name {container_name} --rm -d -p {port}:5432 -e POSTGRES_PASSWORD=password {image}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            return False, None

    elif db_type == "yugabytedb":
        # Start YugabyteDB container
        cmd = f"docker run --name {container_name} -d -p {port}:5433 {image} yugabyted start --background=false"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            return False, None

    elif db_type == "cockroachdb":
        # Start CockroachDB container
        cmd = f"docker run --name {container_name} -d -p {port}:26257 {image} start-single-node --insecure"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            return False, None

    # Get Docker image version info
    version_info = {}
    if RESULTS_STORAGE_AVAILABLE:
        try:
            from version_detector import get_docker_image_version
            version_info = get_docker_image_version(image, container_name)
        except Exception:
            pass

    return True, version_info

def check_ready(container_name, db_type):
    """Check if a Docker container is ready to accept connections."""
    # First check if container is running
    check_running = subprocess.run(
        f"docker ps --filter name={container_name} --format '{{{{.Names}}}}'",
        shell=True, capture_output=True, text=True
    )
    if container_name not in check_running.stdout:
        return False

    if db_type == "mongodb":
        # MongoDB has mongosh in the container
        check = subprocess.run(
            f"docker exec {container_name} mongosh --quiet --eval 'db.adminCommand(\"ping\").ok' 2>&1",
            shell=True, capture_output=True, text=True
        )
        if "1" in check.stdout:
            return True
    
    elif db_type == "documentdb":
        # DocumentDB doesn't have mongosh in container - must check from host
        # Use an actual authenticated MongoDB ping, not just a port check
        db_info = None
        for db in DATABASES:
            if db['container'] == container_name:
                db_info = db
                break

        if db_info:
            port = db_info['port']
            # Try pymongo ping first (most reliable), then mongosh from host
            # DocumentDB gateway requires TLS with self-signed certificates
            try:
                from pymongo import MongoClient
                client = MongoClient(
                    f'mongodb://testuser:testpass@localhost:{port}/?directConnection=true&tls=true&tlsAllowInvalidCertificates=true',
                    serverSelectionTimeoutMS=3000
                )
                client.admin.command('ping')
                client.close()
                return True
            except Exception:
                pass

            # Fallback: try mongosh from host with authentication and TLS
            try:
                check = subprocess.run(
                    f"mongosh --quiet --host localhost --port {port} "
                    f"--username testuser --password testpass --authenticationDatabase admin "
                    f"--tls --tlsAllowInvalidCertificates "
                    f"--eval 'db.runCommand({{ping:1}})' 2>&1",
                    shell=True, capture_output=True, text=True, timeout=5
                )
                if "ok" in check.stdout and "1" in check.stdout:
                    return True
            except (subprocess.TimeoutExpired, Exception):
                pass

            # Final fallback: use psql inside the container to check if the
            # PostgreSQL engine (which DocumentDB is built on) is accepting connections.
            # This is more reliable than nc -z because it verifies the DB engine, not just the port.
            try:
                check = subprocess.run(
                    f"docker exec {container_name} psql -h localhost -p 9712 -U testuser -d postgres -c 'SELECT 1'",
                    shell=True, capture_output=True, text=True, timeout=5
                )
                if check.returncode == 0 and "1" in check.stdout:
                    return True
            except (subprocess.TimeoutExpired, Exception):
                pass

    elif db_type == "postgresql":
        # PostgreSQL readiness check
        try:
            check = subprocess.run(
                f"docker exec {container_name} pg_isready -U postgres",
                shell=True, capture_output=True, text=True, timeout=5
            )
            if check.returncode == 0:
                return True
        except subprocess.TimeoutExpired:
            pass

    elif db_type == "yugabytedb":
        # YugabyteDB readiness check
        try:
            check = subprocess.run(
                f"docker exec {container_name} yugabyted status",
                shell=True, capture_output=True, text=True, timeout=10
            )
            if check.returncode == 0 and "Running" in check.stdout:
                return True
        except subprocess.TimeoutExpired:
            pass

    elif db_type == "cockroachdb":
        # CockroachDB readiness check
        try:
            check = subprocess.run(
                f"docker exec {container_name} cockroach sql --insecure -e 'SELECT 1'",
                shell=True, capture_output=True, text=True, timeout=5
            )
            if check.returncode == 0:
                return True
        except subprocess.TimeoutExpired:
            pass

    return False

def initialize_database(container_name: str, db_type: str) -> bool:
    """Initialize database after container is ready (create test db, users, etc.)

    Args:
        container_name: Name of the Docker container
        db_type: Type of database

    Returns:
        True if initialization succeeded, False otherwise
    """
    try:
        if db_type == "postgresql":
            # Create test database
            subprocess.run(
                f'docker exec {container_name} psql -U postgres -c "CREATE DATABASE test;"',
                shell=True, capture_output=True, timeout=30
            )
            return True

        elif db_type == "yugabytedb":
            # YugabyteDB needs extra time for YSQL
            time.sleep(10)
            # YugabyteDB binds YSQL to the container hostname, not localhost,
            # so we must resolve the hostname and pass it via -h
            hostname_result = subprocess.run(
                f'docker exec {container_name} hostname',
                shell=True, capture_output=True, text=True, timeout=10
            )
            yb_host = hostname_result.stdout.strip() if hostname_result.returncode == 0 else "$(hostname)"
            subprocess.run(
                f'docker exec {container_name} ysqlsh -h {yb_host} -U yugabyte -c "CREATE DATABASE test;"',
                shell=True, capture_output=True, timeout=30
            )
            return True

        elif db_type == "cockroachdb":
            # Create test database and postgres user
            subprocess.run(
                f'docker exec {container_name} cockroach sql --insecure -e "CREATE DATABASE test;"',
                shell=True, capture_output=True, timeout=30
            )
            subprocess.run(
                f'docker exec {container_name} cockroach sql --insecure -e "CREATE USER IF NOT EXISTS postgres;"',
                shell=True, capture_output=True, timeout=30
            )
            subprocess.run(
                f'docker exec {container_name} cockroach sql --insecure -e "GRANT ALL ON DATABASE test TO postgres;"',
                shell=True, capture_output=True, timeout=30
            )
            return True

        # MongoDB and DocumentDB don't need initialization
        return True
    except Exception as e:
        print(f"    ⚠️  Database initialization failed: {e}")
        return False

def _verify_documentdb_operational(port, container_name="documentdb-benchmark", max_attempts=15, retry_interval=3):
    """Verify DocumentDB can perform actual read/write operations, not just accept connections.

    Tries pymongo first for a full MongoDB wire protocol check (with TLS, since
    DocumentDB gateway uses auto-generated certificates), then falls back to
    psql inside the container to verify the PostgreSQL engine is operational.

    Args:
        port: Port number DocumentDB is listening on
        container_name: Docker container name for psql fallback
        max_attempts: Maximum number of verification attempts
        retry_interval: Seconds between retry attempts

    Returns:
        True if DocumentDB is fully operational, False otherwise
    """
    pymongo_available = True
    try:
        from pymongo import MongoClient
    except ImportError:
        pymongo_available = False

    for attempt in range(1, max_attempts + 1):
        if pymongo_available:
            try:
                client = MongoClient(
                    f'mongodb://testuser:testpass@localhost:{port}/?directConnection=true&tls=true&tlsAllowInvalidCertificates=true',
                    serverSelectionTimeoutMS=5000
                )
                db = client['_readiness_check']
                db['_test'].insert_one({'check': 1})
                result = db['_test'].find_one({'check': 1})
                client.drop_database('_readiness_check')
                client.close()
                if result:
                    print(f"    ✓ DocumentDB operational verification passed (pymongo)")
                    return True
            except Exception as e:
                if attempt == max_attempts:
                    print(f"    ✗ DocumentDB pymongo verification failed after {max_attempts} attempts: {e}")
        else:
            # Fallback: use psql inside container to verify PostgreSQL engine can process queries
            try:
                check = subprocess.run(
                    f"docker exec {container_name} psql -h localhost -p 9712 -U testuser -d postgres "
                    f"-c 'SELECT 1'",
                    shell=True, capture_output=True, text=True, timeout=10
                )
                if check.returncode == 0 and "1" in check.stdout:
                    print(f"    ✓ DocumentDB operational verification passed (psql)")
                    return True
            except Exception as e:
                if attempt == max_attempts:
                    print(f"    ✗ DocumentDB psql verification failed after {max_attempts} attempts: {e}")

        time.sleep(retry_interval)

    print(f"    ✗ DocumentDB operational verification failed after {max_attempts} attempts")
    return False

def start_cloud_database(db_info):
    """Verify a cloud/SaaS database is reachable and collect version info.

    No Docker containers are started. This only checks connectivity.

    Args:
        db_info: Database info dict with cloud=True and connection_string

    Returns:
        Tuple of (success: bool, version_info: dict)
    """
    print(f"  Connecting to {db_info['name']} (cloud/SaaS)...", end=" ", flush=True)

    if not check_cloud_database_ready(db_info):
        print("FAILED - could not reach cloud database")
        return False, None

    print("CONNECTED", flush=True)

    # Collect version info
    version_info = {}
    db_version = get_cloud_database_version(db_info)
    if db_version:
        version_info['database_version'] = db_version
        print(f"    Server version: {db_version}")

    return True, version_info


def start_database(container_name, db_type, config=None):
    """Start a Docker container and wait for it to be ready.

    Args:
        container_name: Name of the Docker container
        db_type: Type of database
        config: ConfigParser object (not used for Docker, kept for compatibility)

    Returns:
        Tuple of (success: bool, version_info: dict)
    """
    print(f"  Starting {container_name}...", end=" ", flush=True)

    # Find database info
    db_info = None
    for db in DATABASES:
        if db['container'] == container_name:
            db_info = db
            break

    if not db_info:
        print(f"✗ Failed to find database info")
        return False, None

    success, docker_version_info = start_docker_container(db_info)
    if not success:
        print(f"✗ Failed to start")
        return False, None

    # Wait for database to be ready
    # DocumentDB is slower to initialize than MongoDB - give it more time
    max_wait = 180 if db_type == "documentdb" else 60
    wait_interval = 2

    for i in range(max_wait // wait_interval):
        time.sleep(wait_interval)

        if check_ready(container_name, db_type):
            print(f"✓ Ready (took {(i+1)*wait_interval}s)")

            # For DocumentDB, verify it's fully operational with a real operation
            if db_type == "documentdb":
                if not _verify_documentdb_operational(db_info['port'], container_name):
                    print(f"    ⚠️  Warning: DocumentDB accepted connections but operational verification failed")
                    # Continue anyway - the benchmark will fail with a clear error if it's not ready

            # Initialize database (create test db, users, etc.)
            if not initialize_database(container_name, db_type):
                print(f"    ⚠️  Warning: Database initialization may have failed")

            # Get database version
            db_version = None
            if RESULTS_STORAGE_AVAILABLE:
                try:
                    from version_detector import get_database_version
                    connection_info = {
                        'host': 'localhost',
                        'port': db_info['port'],
                        'container': container_name
                    }
                    # Add db-specific connection parameters
                    if db_type == 'documentdb':
                        connection_info['user'] = 'testuser'
                        connection_info['password'] = 'testpass'
                        connection_info['database'] = 'test'
                        connection_info['tls'] = True
                    elif db_type == 'postgresql':
                        connection_info['user'] = 'postgres'
                        connection_info['password'] = 'password'
                    elif db_type == 'yugabytedb':
                        connection_info['user'] = 'yugabyte'
                    elif db_type == 'cockroachdb':
                        connection_info['user'] = 'root'
                    db_version = get_database_version(db_type, connection_info)
                except Exception:
                    pass

            version_info = docker_version_info or {}
            if db_version:
                version_info['database_version'] = db_version

            return True, version_info

        # Show progress on first few attempts
        if i < 3:
            print(".", end="", flush=True)

    print(f"✗ Timeout waiting for database (waited {max_wait}s)")
    return False, None

def stop_database(container_name):
    """Stop a Docker container."""
    print(f"  Stopping {container_name}...", end=" ", flush=True)
    subprocess.run(f"docker rm -f {container_name} 2>/dev/null", shell=True, capture_output=True)
    time.sleep(2)
    print("✓ Stopped")

def cleanup_database_files(db_type):
    """Clean up database data files (not needed for Docker with --rm flag)."""
    print(f"  Skipping file cleanup for {db_type} (Docker containers use --rm flag)", flush=True)
    return

def get_connection_string_for_db(db_info):
    """Get the connection string for a database.

    For Docker databases, builds a localhost connection string from db_type and port.
    For cloud databases, returns the configured connection string directly.
    """
    # Cloud databases use their configured connection string
    if db_info.get('cloud') and db_info.get('connection_string'):
        return db_info['connection_string']

    # Docker databases use localhost connections
    db_type = db_info['db_type']
    port = db_info['port']
    if db_type == "mongodb":
        return f"mongodb://localhost:{port}"
    elif db_type == "documentdb":
        return f"mongodb://testuser:testpass@localhost:{port}/?directConnection=true&tls=true&tlsAllowInvalidCertificates=true&serverSelectionTimeoutMS=60000&connectTimeoutMS=30000&socketTimeoutMS=60000"
    elif db_type in ("postgresql", "yugabytedb", "cockroachdb"):
        return f"jdbc:postgresql://localhost:{port}/test?user=postgres&password=password"
    return None


def get_docker_connection_string(db_type, port):
    """Get the Docker-appropriate connection string for a database type and port.

    This overrides config.properties via -Dconn to ensure correct credentials
    and ports regardless of what's in the config file.
    """
    if db_type == "mongodb":
        return f"mongodb://localhost:{port}"
    elif db_type == "documentdb":
        return f"mongodb://testuser:testpass@localhost:{port}/?directConnection=true&tls=true&tlsAllowInvalidCertificates=true&serverSelectionTimeoutMS=60000&connectTimeoutMS=30000&socketTimeoutMS=60000"
    elif db_type in ("postgresql", "yugabytedb", "cockroachdb"):
        return f"jdbc:postgresql://localhost:{port}/test?user=postgres&password=password"
    return None


def run_benchmark(db_flags, size, attrs, num_docs, num_runs, batch_size, query_links=None, measure_sizes=True, db_name="unknown", db_type=None, results_storage=None, test_run_id=None, database_info=None, system_info=None, ci_info=None, resource_summary=None, validate=False, conn_string=None, collect_latency=False):
    """Run a single benchmark test, optionally with query tests."""

    # Build Java command with explicit connection string override if provided
    conn_flag = f'-Dconn="{conn_string}" ' if conn_string else ''
    cmd = f"java {conn_flag}-jar {JAR_PATH} {db_flags} -s {size} -n {attrs} -r {num_runs} -b {batch_size}"

    # Add size measurement flag if specified
    if measure_sizes:
        cmd += " -size"

    # Add validation flag if specified
    if validate:
        cmd += " -v"

    # Add latency collection flag for cloud/SaaS databases
    if collect_latency:
        cmd += " -latency"

    # Add query test flag if specified
    if query_links is not None:
        cmd += f" -q {query_links}"

    cmd += f" {num_docs}"

    try:
        # Check if JAR file exists
        if not os.path.exists(JAR_PATH):
            print(f"    ERROR: JAR file not found: {JAR_PATH}")
            return {"success": False, "error": f"JAR file not found: {JAR_PATH}"}
        
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=900  # 15 minutes per test
        )

        # Parse result for "Best time to insert" or "Time taken to insert"
        # Standard format: "Best time to insert 10000 documents with 100B payload in 1 attribute into indexed: 123ms"
        pattern = rf"(?:Best time|Time taken) to insert {num_docs} documents with {size}B payload in {attrs} attributes? into \w+: (\d+)ms"
        match = re.search(pattern, result.stdout)

        response = {
            "success": False,
            "size": size,
            "attrs": attrs,
            "num_docs": num_docs
        }

        if match:
            time_ms = int(match.group(1))
            throughput = round(num_docs / (time_ms / 1000), 2)
            response.update({
                "success": True,
                "time_ms": time_ms,
                "throughput": throughput
            })
        else:
            # Try alternative pattern with "attribute" singular/plural
            alt_pattern = rf"(?:Best time|Time taken) to insert {num_docs} documents with {size}B payload in \d+ attributes? into \w+: (\d+)ms"
            alt_match = re.search(alt_pattern, result.stdout)
            if alt_match:
                time_ms = int(alt_match.group(1))
                throughput = round(num_docs / (time_ms / 1000), 2)
                response.update({
                    "success": True,
                    "time_ms": time_ms,
                    "throughput": throughput
                })
            else:
                # Try realistic data pattern: "Best time to insert 10000 documents with realistic nested data (~100B) into indexed: 123ms"
                realistic_pattern = rf"(?:Best time|Time taken) to insert {num_docs} documents with realistic nested data \(~{size}B\) into \w+: (\d+)ms"
                realistic_match = re.search(realistic_pattern, result.stdout)
                if realistic_match:
                    time_ms = int(realistic_match.group(1))
                    throughput = round(num_docs / (time_ms / 1000), 2)
                    response.update({
                        "success": True,
                        "time_ms": time_ms,
                        "throughput": throughput
                    })
                else:
                    # Enhanced error reporting
                    print(f"    Warning: Could not parse output")
                    print(f"    Command: {cmd}")
                    if result.returncode != 0:
                        print(f"    Java process exited with code: {result.returncode}")
                    if result.stderr:
                        stderr_preview = result.stderr.strip()
                        if len(stderr_preview) > 500:
                            stderr_preview = stderr_preview[:500] + "..."
                        print(f"    stderr: {stderr_preview}")
                    if result.stdout:
                        # Show last few lines of stdout for debugging
                        stdout_lines = result.stdout.strip().split('\n')
                        print(f"    stdout (last 10 lines):")
                        for line in stdout_lines[-10:]:
                            print(f"      {line}")
                    else:
                        print(f"    No output captured from Java process")
                    return {"success": False, "error": "Could not parse output"}

        # If query tests were requested, parse query results
        if query_links is not None:
            # Parse query time: "Best query time for N ID's with M element link arrays...: XXXms"
            # This format appears when num_runs > 1 (the Java -r flag)
            query_pattern = rf"Best query time for (\d+) ID's with {query_links} element link arrays.*?: (\d+)ms"
            query_match = re.search(query_pattern, result.stdout)

            if not query_match:
                # Fallback: single-run format (num_runs == 1)
                # "Total time taken to query related documents for N ID's with M element link arrays...: XXXms"
                query_pattern_single = rf"Total time taken to query related documents for (\d+) ID's with {query_links} element link arrays.*?: (\d+)ms"
                query_match = re.search(query_pattern_single, result.stdout)

            if query_match:
                queries_executed = int(query_match.group(1))
                query_time_ms = int(query_match.group(2))
                query_throughput = round(queries_executed / (query_time_ms / 1000), 2)
                response.update({
                    "query_time_ms": query_time_ms,
                    "query_throughput": query_throughput,
                    "queries_executed": queries_executed,
                    "query_links": query_links
                })
            else:
                # Query test may have failed or not been executed
                response["query_time_ms"] = None
                response["query_error"] = "Could not parse query results"
        
        # Parse latency statistics if latency collection was enabled
        if collect_latency:
            latency_metrics = {}
            for line in result.stdout.split('\n'):
                if line.startswith('LATENCY_STATS|'):
                    parts = line.split('|', 2)
                    if len(parts) == 3:
                        op_type = parts[1]
                        try:
                            stats = json.loads(parts[2])
                            # Simplify samples to just ms values for storage (drop timestamps for size)
                            simplified_samples = [s['ms'] for s in stats.get('samples', [])]
                            latency_metrics[op_type] = {
                                'min_ms': stats.get('min_ms'),
                                'max_ms': stats.get('max_ms'),
                                'avg_ms': stats.get('avg_ms'),
                                'p50_ms': stats.get('p50_ms'),
                                'p95_ms': stats.get('p95_ms'),
                                'p99_ms': stats.get('p99_ms'),
                                'sample_count': stats.get('sample_count'),
                                'samples': simplified_samples
                            }
                        except (json.JSONDecodeError, KeyError) as e:
                            print(f"    Warning: Could not parse latency stats for {op_type}: {e}")
            if latency_metrics:
                response['latency_metrics'] = latency_metrics

        # Build full result document structure for MongoDB storage (to be stored later)
        # Include all metadata needed for storage
        if response.get('success'):
            try:
                # Determine client library based on db_type
                client_library = None
                client_version = None
                java_version = None
                if RESULTS_STORAGE_AVAILABLE:
                    from version_detector import get_client_library_version, get_java_version
                    if db_type in ['mongodb', 'documentdb', 'mongodb-cloud', 'documentdb-azure']:
                        client_library = 'mongodb-driver-sync'
                        client_version = get_client_library_version('mongodb-driver-sync')
                    elif db_type in ['postgresql', 'yugabytedb', 'cockroachdb']:
                        client_library = 'postgresql-jdbc'
                        client_version = get_client_library_version('postgresql')
                    elif db_type == 'oracle':
                        client_library = 'ojdbc11'
                        client_version = get_client_library_version('ojdbc11')
                    java_version = get_java_version()
                
                # Extract database info
                db_image = None
                db_image_tag = None
                db_image_id = None
                db_version = None
                if database_info:
                    db_version = database_info.get('database_version')
                    db_image = database_info.get('image')
                    db_image_tag = database_info.get('tag')
                    db_image_id = database_info.get('image_id')
                
                # Build result document matching schema (will be stored to MongoDB later)
                result_doc = {
                    'timestamp': datetime.now().isoformat(),
                    'test_run_id': test_run_id or 'unknown',
                    'database': {
                        'type': db_type or 'unknown',
                        'version': db_version,
                        'docker_image': db_image or 'unknown',
                        'docker_image_tag': db_image_tag,
                        'docker_image_id': db_image_id
                    },
                    'client': {
                        'library': client_library,
                        'version': client_version
                    },
                    'test_config': {
                        'num_docs': num_docs,
                        'num_runs': num_runs,
                        'batch_size': batch_size,
                        'test_type': 'single_attr' if attrs == 1 else 'multi_attr',
                        'payload_size': size,
                        'num_attributes': attrs,
                        'indexed': '-i' in db_flags or '-mv' in db_flags,
                        'query_test': query_links is not None,
                        'query_links': query_links if query_links else None
                    },
                    'results': {
                        'insert_time_ms': response.get('time_ms'),
                        'insert_throughput': response.get('throughput'),
                        'query_time_ms': response.get('query_time_ms'),
                        'query_throughput': response.get('query_throughput'),
                        'success': response.get('success', False),
                        'error': response.get('error')
                    },
                    'system_info': system_info or {},
                    'resource_metrics': resource_summary or {},
                    'latency_metrics': response.get('latency_metrics', {}),
                    'ci_info': ci_info or {}
                }
                
                # Add Java version to system_info if available
                if java_version and result_doc.get('system_info'):
                    result_doc['system_info']['java_version'] = java_version
                
                # Attach the full document structure to response for later storage
                response['mongodb_document'] = result_doc
            except Exception as e:
                print(f"    ⚠️  Warning: Could not build MongoDB document structure: {e}")

        return response

    except subprocess.TimeoutExpired:
        print(f"    ERROR: Timeout after 900 seconds")
        return {"success": False, "error": "Timeout"}
    except Exception as e:
        print(f"    ERROR: {str(e)}")
        return {"success": False, "error": str(e)}

def run_test_suite(test_configs, test_type, enable_queries=False, restart_per_test=False, measure_sizes=False, track_activity=False, activity_log=None, config=None, results_storage=None, test_run_id=None, system_info=None, ci_info=None, enable_monitoring=False, monitor_interval=5, validate=False):
    """Run a complete test suite (single or multi attribute).

    Args:
        test_configs: List of test configurations
        config: ConfigParser object (kept for compatibility, not used for Docker)
        test_type: Description of test type
        enable_queries: Whether to run query tests
        restart_per_test: If True, restart database before EACH test for maximum isolation
        measure_sizes: Whether to enable BSON/OSON object size measurement
        track_activity: If True, record database start/stop timestamps
        activity_log: List to append activity events to (format: {db_name, event, timestamp})
        enable_monitoring: If True, start/stop resource monitoring for each test
        monitor_interval: Resource monitoring interval in seconds
        validate: If True, enable data integrity validation
    """
    print(f"\n{'='*80}")
    print(f"{test_type.upper()} ATTRIBUTE TESTS" + (" WITH QUERIES" if enable_queries else ""))
    print(f"{'='*80}")

    results = {}

    if activity_log is None:
        activity_log = []

    if restart_per_test:
        # MAXIMUM ISOLATION MODE: Restart database before each individual test
        # Initialize results dict
        for db in DATABASES:
            results[db['key']] = []

        # Outer loop: iterate through tests
        for test_idx, test in enumerate(test_configs):
            # Inner loop: run this test on each database
            for db in DATABASES:
                is_cloud = db.get('cloud', False)

                if test_idx == 0:
                    # Print database header only for first test
                    cloud_label = " [Cloud/SaaS]" if is_cloud else ""
                    print(f"\n--- {db['name']}{cloud_label} ---")

                # Start database for this specific test
                if is_cloud:
                    db_started, version_info = start_cloud_database(db)
                else:
                    db_started, version_info = start_database(db['container'], db['db_type'], config)
                if not db_started:
                    print(f"  Testing: {test['desc']}... ✗ Database failed to start")
                    results[db['key']].append({"success": False, "error": "Database failed to start"})
                    continue

                # Build database info for MongoDB storage
                database_info = version_info or {}
                database_info['image'] = db.get('image')
                if version_info:
                    database_info.update(version_info)

                # Start resource monitoring for this test if enabled
                # Skip resource monitoring for cloud DBs (not meaningful) - use latency collection instead
                monitor_proc = None
                resource_metrics_file = None
                if enable_monitoring and not is_cloud:
                    test_type_short = 'single_attr' if test['attrs'] == 1 else 'multi_attr'
                    resource_metrics_file = generate_resource_metrics_filename(
                        db['db_type'], test_type_short, test['size'], test['attrs']
                    )
                    monitor_proc = start_monitoring(resource_metrics_file, monitor_interval)

                # Enable latency collection for cloud/SaaS databases
                use_latency = is_cloud

                # Run the test
                print(f"  Testing: {test['desc']}...", end=" ", flush=True)

                conn_string = get_connection_string_for_db(db)

                result = run_benchmark(
                    db['flags'],
                    test['size'],
                    test['attrs'],
                    NUM_DOCS,
                    NUM_RUNS,
                    BATCH_SIZE,
                    query_links=QUERY_LINKS if enable_queries else None,
                    measure_sizes=measure_sizes,
                    db_name=db['name'],
                    db_type=db['db_type'],
                    results_storage=None,  # Don't store during run, collect for later
                    test_run_id=test_run_id,
                    database_info=database_info,
                    system_info=system_info,
                    ci_info=ci_info,
                    resource_summary=None,  # Will be populated after monitoring stops
                    validate=validate,
                    conn_string=conn_string,
                    collect_latency=use_latency
                )

                # Stop resource monitoring and extract summary (only for non-cloud DBs)
                resource_summary = None
                if enable_monitoring and not is_cloud and monitor_proc:
                    stop_monitoring(monitor_proc)
                    resource_summary = get_resource_summary_from_file(resource_metrics_file)
                    # Output resource summary to debug console
                    if resource_summary:
                        print_resource_summary(resource_summary, test['desc'])
                    # Update the MongoDB document with resource summary if it exists
                    if result.get('mongodb_document') and resource_summary:
                        result['mongodb_document']['resource_metrics'] = resource_summary

                if result['success']:
                    output = f"✓ {result['time_ms']}ms ({result['throughput']:,.0f} docs/sec)"
                    if enable_queries and 'query_time_ms' in result and result['query_time_ms']:
                        output += f" | Query: {result['query_time_ms']}ms ({result['query_throughput']:,.0f} queries/sec)"
                    # Show latency summary for cloud DBs
                    if use_latency and result.get('latency_metrics'):
                        for op, metrics in result['latency_metrics'].items():
                            output += f" | {op} p50={metrics['p50_ms']:.1f}ms p99={metrics['p99_ms']:.1f}ms"
                    results[db['key']].append(result)
                    print(output)
                else:
                    results[db['key']].append(result)
                    print(f"✗ {result.get('error', 'Failed')}")

                # Stop database immediately after test completes (skip for cloud)
                if not is_cloud:
                    stop_database(db['container'])
                    cleanup_database_files(db['db_type'])

    else:
        # ORIGINAL MODE: Start database once, run all tests, then stop
        current_container = None
        current_db_name = None

        for db in DATABASES:
            is_cloud = db.get('cloud', False)
            cloud_label = " [Cloud/SaaS]" if is_cloud else ""
            print(f"\n--- {db['name']}{cloud_label} ---")

            # Cloud databases don't use containers - always "start" (verify connectivity)
            if is_cloud:
                db_started, version_info = start_cloud_database(db)
                if not db_started:
                    print(f"  ERROR: Failed to connect to {db['name']}, skipping tests")
                    results[db['key']] = [{"success": False, "error": "Cloud database unreachable"} for _ in test_configs]
                    continue
                database_info = version_info or {}
                database_info['image'] = None  # No Docker image for cloud
            else:
                # Start database if different from current
                if db['container'] != current_container:
                    # Stop previous database if any
                    if current_container:
                        stop_database(current_container)
                        # Clean up previous database files
                        if current_db_name:
                            prev_db_type = None
                            for prev_db in DATABASES:
                                if prev_db['name'] == current_db_name:
                                    prev_db_type = prev_db['db_type']
                                    break
                            if prev_db_type:
                                cleanup_database_files(prev_db_type)
                        if track_activity and current_db_name:
                            activity_log.append({
                                "database": current_db_name,
                                "event": "stopped",
                                "timestamp": datetime.now().isoformat()
                            })

                    # Start new database
                    db_started, version_info = start_database(db['container'], db['db_type'], config)
                    if not db_started:
                        print(f"  ERROR: Failed to start {db['container']}, skipping tests")
                        results[db['key']] = [{"success": False, "error": "Database failed to start"} for _ in test_configs]
                        continue

                    current_container = db['container']
                    current_db_name = db['name']

                    # Build database info for MongoDB storage
                    database_info = version_info or {}
                    database_info['image'] = db.get('image')
                    if version_info:
                        database_info.update(version_info)

                    if track_activity:
                        activity_log.append({
                            "database": db['name'],
                            "event": "started",
                            "timestamp": datetime.now().isoformat()
                        })

            results[db['key']] = []

            for test in test_configs:
                # Start resource monitoring for this test if enabled
                # Skip resource monitoring for cloud DBs (not meaningful) - use latency collection instead
                monitor_proc = None
                resource_metrics_file = None
                if enable_monitoring and not is_cloud:
                    test_type_short = 'single_attr' if test['attrs'] == 1 else 'multi_attr'
                    resource_metrics_file = generate_resource_metrics_filename(
                        db['db_type'], test_type_short, test['size'], test['attrs']
                    )
                    monitor_proc = start_monitoring(resource_metrics_file, monitor_interval)

                # Enable latency collection for cloud/SaaS databases
                use_latency = is_cloud

                print(f"  Testing: {test['desc']}...", end=" ", flush=True)

                conn_string = get_connection_string_for_db(db)

                result = run_benchmark(
                    db['flags'],
                    test['size'],
                    test['attrs'],
                    NUM_DOCS,
                    NUM_RUNS,
                    BATCH_SIZE,
                    query_links=QUERY_LINKS if enable_queries else None,
                    measure_sizes=measure_sizes,
                    db_name=db['name'],
                    db_type=db['db_type'],
                    results_storage=None,  # Don't store during run, collect for later
                    test_run_id=test_run_id,
                    database_info=database_info,
                    system_info=system_info,
                    ci_info=ci_info,
                    resource_summary=None,  # Will be populated after monitoring stops
                    validate=validate,
                    conn_string=conn_string,
                    collect_latency=use_latency
                )

                # Stop resource monitoring and extract summary (only for non-cloud DBs)
                resource_summary = None
                if enable_monitoring and not is_cloud and monitor_proc:
                    stop_monitoring(monitor_proc)
                    resource_summary = get_resource_summary_from_file(resource_metrics_file)
                    # Output resource summary to debug console
                    if resource_summary:
                        print_resource_summary(resource_summary, test['desc'])
                    # Update the MongoDB document with resource summary if it exists
                    if result.get('mongodb_document') and resource_summary:
                        result['mongodb_document']['resource_metrics'] = resource_summary

                if result['success']:
                    output = f"✓ {result['time_ms']}ms ({result['throughput']:,.0f} docs/sec)"
                    if enable_queries and 'query_time_ms' in result and result['query_time_ms']:
                        output += f" | Query: {result['query_time_ms']}ms ({result['query_throughput']:,.0f} queries/sec)"
                    # Show latency summary for cloud DBs
                    if use_latency and result.get('latency_metrics'):
                        for op, metrics in result['latency_metrics'].items():
                            output += f" | {op} p50={metrics['p50_ms']:.1f}ms p99={metrics['p99_ms']:.1f}ms"
                    results[db['key']].append(result)
                    print(output)
                else:
                    results[db['key']].append(result)
                    print(f"✗ {result.get('error', 'Failed')}")

        # Stop the last database (if it was a Docker container)
        if current_container:
            stop_database(current_container)
            # Clean up final database files
            if current_db_name:
                final_db_type = None
                for final_db in DATABASES:
                    if final_db['name'] == current_db_name:
                        final_db_type = final_db['db_type']
                        break
                if final_db_type:
                    cleanup_database_files(final_db_type)
            if track_activity and current_db_name:
                activity_log.append({
                    "database": current_db_name,
                    "event": "stopped",
                    "timestamp": datetime.now().isoformat()
                })

    return results

def store_results_to_mongodb(results_dict, results_storage):
    """Store all collected test results to MongoDB.
    
    Args:
        results_dict: Dictionary with database keys and lists of result dictionaries
        results_storage: ResultsStorage instance (or None if not available)
    
    Returns:
        Number of results successfully stored
    """
    if not results_storage or results_storage.collection is None:
        return 0
    
    stored_count = 0
    for db_key, result_list in results_dict.items():
        for result in result_list:
            if result.get('success') and result.get('mongodb_document'):
                try:
                    stored_id = results_storage.store_test_result(result['mongodb_document'])
                    if stored_id:
                        stored_count += 1
                except Exception as e:
                    print(f"    ⚠️  Warning: Could not store result to MongoDB: {e}")
    
    return stored_count

def generate_summary_table(single_results, multi_results):
    """Generate a summary comparison table."""
    # Get list of database keys that have results
    all_db_keys = ['mongodb', 'documentdb', 'postgresql', 'yugabytedb', 'cockroachdb', 'mongodb-cloud', 'documentdb-azure']
    active_db_keys = [k for k in all_db_keys if k in single_results or k in multi_results]

    # Column width for each database
    col_width = 14

    print(f"\n{'='*100}")
    print(f"SUMMARY: Single-Attribute Results ({NUM_DOCS:,} documents) - All with indexes")
    print(f"{'='*100}")
    header = f"{'Payload':<12}"
    for db_key in active_db_keys:
        header += f" {db_key:<{col_width}}"
    print(header)
    print("-" * 100)

    for i, test in enumerate(SINGLE_ATTR_TESTS):
        row = f"{test['size']}B"
        for db_key in active_db_keys:
            if db_key in single_results and i < len(single_results[db_key]):
                result = single_results[db_key][i]
                if result['success']:
                    row += f"  {result['time_ms']:>{col_width-2}}ms"
                else:
                    row += f"  {'FAIL':>{col_width-2}}  "
            else:
                row += f"  {'N/A':>{col_width-2}}  "
        print(row)

    print(f"\n{'='*100}")
    print(f"SUMMARY: Multi-Attribute Results ({NUM_DOCS:,} documents) - All with indexes")
    print(f"{'='*100}")
    header = f"{'Config':<20}"
    for db_key in active_db_keys:
        header += f" {db_key:<{col_width}}"
    print(header)
    print("-" * 100)

    for i, test in enumerate(MULTI_ATTR_TESTS):
        row = f"{test['attrs']}×{test['size']//test['attrs']}B"
        for db_key in active_db_keys:
            if db_key in multi_results and i < len(multi_results[db_key]):
                result = multi_results[db_key][i]
                if result['success']:
                    row += f"  {result['time_ms']:>{col_width-2}}ms"
                else:
                    row += f"  {'FAIL':>{col_width-2}}  "
            else:
                row += f"  {'N/A':>{col_width-2}}  "
        print(row)

def run_full_comparison_suite(args):
    """
    Run complete benchmark suite: first without indexes (insert-only),
    then with indexes and queries for comprehensive comparison.
    """
    global NUM_DOCS, NUM_RUNS, BATCH_SIZE, QUERY_LINKS, DATABASES, SINGLE_ATTR_TESTS, MULTI_ATTR_TESTS
    import copy

    # Load benchmark configuration
    config = load_benchmark_config()
    
    # Initialize MongoDB results storage
    results_storage = None
    test_run_id = None
    system_info = None
    ci_info = None
    
    if RESULTS_STORAGE_AVAILABLE:
        try:
            # Get MongoDB connection string from config
            mongodb_conn = config.get('results_storage', 'mongodb_connection_string', fallback=None)
            db_name = config.get('results_storage', 'database_name', fallback='benchmark_results')
            coll_name = config.get('results_storage', 'collection_name', fallback='test_runs')
            
            if mongodb_conn:
                results_storage = connect_to_mongodb(mongodb_conn, db_name, coll_name)
                if results_storage:
                    print(f"✓ Connected to MongoDB results storage")
                else:
                    print(f"⚠️  Warning: Could not connect to MongoDB, results will not be stored")
            else:
                print(f"⚠️  Warning: MongoDB connection string not configured, results will not be stored")
        except Exception as e:
            print(f"⚠️  Warning: Could not initialize MongoDB storage: {e}")
        
        # Generate test run ID
        if uuid:
            test_run_id = str(uuid.uuid4())
            print(f"Test Run ID: {test_run_id}")
        
        # Collect system info once at start
        try:
            system_info = get_system_info()
        except Exception as e:
            print(f"⚠️  Warning: Could not collect system info: {e}")
        
        # Collect CI info
        try:
            ci_info = get_ci_info()
            if ci_info.get('ci_run'):
                print(f"✓ CI environment detected: {ci_info.get('ci_platform')}")
        except Exception as e:
            print(f"⚠️  Warning: Could not collect CI info: {e}")

    # Add large item tests if requested
    if args.large_items:
        SINGLE_ATTR_TESTS = SINGLE_ATTR_TESTS + LARGE_SINGLE_ATTR_TESTS
        MULTI_ATTR_TESTS = MULTI_ATTR_TESTS + LARGE_MULTI_ATTR_TESTS

    # Save original database configurations
    original_databases = copy.deepcopy(DATABASES)

    # Determine test order (randomize if requested)
    run_index_first = False
    if args.randomize_order:
        run_index_first = random.choice([True, False])
        print(f"NOTE: Test order randomized - running {'WITH INDEX' if run_index_first else 'NO INDEX'} tests first\n")

    print(f"\n{'='*80}")
    print("FULL COMPARISON BENCHMARK: Insert-Only + Indexed with Queries")
    print(f"{'='*80}")
    print(f"Document count: {NUM_DOCS:,}")
    print(f"Runs per test: {NUM_RUNS} (best time reported)")
    print(f"Batch size: {BATCH_SIZE}")
    print(f"Query tests: {QUERY_LINKS} links per document (indexed tests only)")
    print(f"Randomized order: {args.randomize_order}")
    print(f"Monitoring enabled: {args.monitor}")
    print(f"Large items: {'ENABLED (10KB, 100KB, 1000KB)' if args.large_items else 'DISABLED'}")
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Stop all databases first
    stop_all_databases()

    # ========== PART 1: NO-INDEX TESTS ==========
    print(f"\n{'='*80}")
    print("PART 1: INSERT-ONLY TESTS (NO INDEXES)")
    print(f"{'='*80}\n")

    # Remove index flags from all databases
    for db in DATABASES:
        db['flags'] = db['flags'].replace(' -i', '').replace('-i ', '').replace(' -mv', '').replace('-mv ', '')

    # Run tests without indexes - restart database before each test for maximum isolation
    single_results_noindex = run_test_suite(SINGLE_ATTR_TESTS, "SINGLE ATTRIBUTE (NO INDEX)", enable_queries=False, restart_per_test=True, measure_sizes=args.measure_sizes, config=config,
                                           results_storage=results_storage, test_run_id=test_run_id, system_info=system_info, ci_info=ci_info,
                                           enable_monitoring=args.monitor, monitor_interval=args.monitor_interval, validate=args.validate)
    multi_results_noindex = run_test_suite(MULTI_ATTR_TESTS, "MULTI ATTRIBUTE (NO INDEX)", enable_queries=False, restart_per_test=True, measure_sizes=args.measure_sizes, config=config,
                                          results_storage=results_storage, test_run_id=test_run_id, system_info=system_info, ci_info=ci_info,
                                          enable_monitoring=args.monitor, monitor_interval=args.monitor_interval, validate=args.validate)

    # ========== PART 2: WITH-INDEX TESTS ==========
    print(f"\n{'='*80}")
    print("PART 2: INDEXED TESTS WITH QUERIES")
    print(f"{'='*80}\n")

    # Restore original database configurations (with indexes)
    DATABASES = copy.deepcopy(original_databases)

    # Stop all databases before starting indexed tests
    stop_all_databases()
    print()

    # Run tests with indexes and queries - restart database before each test for maximum isolation
    single_results_indexed = run_test_suite(SINGLE_ATTR_TESTS, "SINGLE ATTRIBUTE (WITH INDEX)", enable_queries=True, restart_per_test=True, measure_sizes=args.measure_sizes, config=config,
                                           results_storage=results_storage, test_run_id=test_run_id, system_info=system_info, ci_info=ci_info,
                                           enable_monitoring=args.monitor, monitor_interval=args.monitor_interval, validate=args.validate)
    multi_results_indexed = run_test_suite(MULTI_ATTR_TESTS, "MULTI ATTRIBUTE (WITH INDEX)", enable_queries=True, restart_per_test=True, measure_sizes=args.measure_sizes, config=config,
                                          results_storage=results_storage, test_run_id=test_run_id, system_info=system_info, ci_info=ci_info,
                                          enable_monitoring=args.monitor, monitor_interval=args.monitor_interval, validate=args.validate)

    # ========== GENERATE COMPARISON SUMMARY ==========
    print(f"\n{'='*80}")
    print("COMPARISON SUMMARY")
    print(f"{'='*80}\n")

    generate_comparison_summary(single_results_noindex, single_results_indexed,
                               multi_results_noindex, multi_results_indexed)

    # Store all results to MongoDB at the end
    if results_storage:
        print(f"\n{'='*80}")
        print("STORING RESULTS TO MONGODB")
        print(f"{'='*80}")
        stored_count = 0
        stored_count += store_results_to_mongodb(single_results_noindex, results_storage)
        stored_count += store_results_to_mongodb(multi_results_noindex, results_storage)
        stored_count += store_results_to_mongodb(single_results_indexed, results_storage)
        stored_count += store_results_to_mongodb(multi_results_indexed, results_storage)
        print(f"✓ Stored {stored_count} test results to MongoDB")
    
    # Close MongoDB connection
    if results_storage:
        results_storage.close()

    # Save comprehensive results to JSON (local backup)
    output_data = {
        "timestamp": datetime.now().isoformat(),
        "configuration": {
            "documents": NUM_DOCS,
            "runs": NUM_RUNS,
            "batch_size": BATCH_SIZE,
            "query_links": QUERY_LINKS,
            "monitoring_enabled": args.monitor
        },
        "no_index": {
            "single_attribute": single_results_noindex,
            "multi_attribute": multi_results_noindex
        },
        "with_index": {
            "single_attribute": single_results_indexed,
            "multi_attribute": multi_results_indexed
        }
    }

    with open("full_comparison_results.json", "w") as f:
        json.dump(output_data, f, indent=2)

    print(f"\n{'='*80}")
    print(f"✓ Full comparison results saved to: full_comparison_results.json")
    if args.monitor:
        print(f"✓ Resource monitoring enabled (per-test metrics stored with each result)")
    print(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}\n")

def generate_comparison_summary(single_noindex, single_indexed, multi_noindex, multi_indexed):
    """Generate side-by-side comparison tables."""
    print("Single-Attribute Comparison (Insert Times):")
    print(f"{'Payload':<10} {'No Index':<15} {'With Index':<15} {'Difference'}")
    print("-" * 60)

    for db_key in single_noindex.keys():
        if single_noindex[db_key] and single_indexed.get(db_key):
            print(f"\n{db_key}:")
            for i, result in enumerate(single_noindex[db_key]):
                if result['success'] and i < len(single_indexed[db_key]) and single_indexed[db_key][i]['success']:
                    noindex_time = result['time_ms']
                    indexed_time = single_indexed[db_key][i]['time_ms']
                    diff = ((indexed_time - noindex_time) / noindex_time) * 100
                    payload = SINGLE_ATTR_TESTS[i]['desc']
                    print(f"  {payload:<10} {noindex_time:>6}ms       {indexed_time:>6}ms       {diff:+6.1f}%")

def ensure_config_properties():
    """Auto-generate config.properties with Docker-appropriate defaults if missing."""
    project_root = Path(__file__).parent.parent
    config_file = project_root / "config.properties"
    if not config_file.exists():
        print("config.properties not found - generating with Docker defaults...")
        config_file.write_text(
            "# Auto-generated config.properties for Docker-based testing\n"
            "# See config/config.properties.example for full documentation\n"
            "\n"
            "# MongoDB Connection\n"
            "mongodb.connection.string=mongodb://localhost:27017\n"
            "\n"
            "# PostgreSQL Connection\n"
            "postgresql.connection.string=jdbc:postgresql://localhost:5432/test?user=postgres&password=password\n"
            "\n"
            "# DocumentDB Connection (MongoDB-compatible)\n"
            "documentdb.connection.string=mongodb://testuser:testpass@localhost:10260/?directConnection=true&tls=true&tlsAllowInvalidCertificates=true\n"
        )
        print(f"✓ Generated {config_file}")


def main():
    """Main execution."""
    global NUM_DOCS, NUM_RUNS, BATCH_SIZE, QUERY_LINKS, DATABASES

    # Auto-generate config.properties if missing
    ensure_config_properties()

    parser = argparse.ArgumentParser(description='Run benchmark tests replicating LinkedIn article (Docker version)')
    parser.add_argument('--queries', '-q', action='store_true',
                        help=f'Include query tests with {QUERY_LINKS} links per document')
    parser.add_argument('--no-index', action='store_true',
                        help='Run tests without indexes (can be combined with --queries)')
    parser.add_argument('--full-comparison', action='store_true',
                        help='Run both no-index and with-index tests in sequence for complete comparison')
    parser.add_argument('--randomize-order', action='store_true',
                        help='Randomize test execution order (with-index first or no-index first) to eliminate execution order bias')
    parser.add_argument('--mongodb', action='store_true', help='Run MongoDB tests')
    parser.add_argument('--documentdb', action='store_true', help='Run DocumentDB tests')
    parser.add_argument('--postgresql', action='store_true', help='Run PostgreSQL tests')
    parser.add_argument('--yugabytedb', action='store_true', help='Run YugabyteDB tests')
    parser.add_argument('--cockroachdb', action='store_true', help='Run CockroachDB tests')
    parser.add_argument('--mongodb-atlas', action='store_true',
                        help='Run MongoDB Atlas (cloud/SaaS) tests (requires [mongodb_atlas] enabled=true in config)')
    parser.add_argument('--azure-documentdb', action='store_true',
                        help='Run Azure DocumentDB (cloud/SaaS) tests (requires [azure_documentdb] enabled=true in config)')
    parser.add_argument('--batch-size', '-b', type=int, default=BATCH_SIZE,
                        help=f'Batch size for insertions (default: {BATCH_SIZE})')
    parser.add_argument('--num-docs', '-n', type=int, default=NUM_DOCS,
                        help=f'Number of documents per test (default: {NUM_DOCS})')
    parser.add_argument('--num-runs', '-r', type=int, default=NUM_RUNS,
                        help=f'Number of runs per test (default: {NUM_RUNS})')
    parser.add_argument('--query-links', type=int, default=QUERY_LINKS,
                        help=f'Number of array elements for query tests (default: {QUERY_LINKS})')
    parser.add_argument('--measure-sizes', action='store_true',
                        help='Enable BSON/OSON object size measurement and comparison')
    parser.add_argument('--monitor', action='store_true', default=True,
                        help='Enable system resource monitoring (CPU, disk, network) every 5 seconds (default: enabled)')
    parser.add_argument('--no-monitor', dest='monitor', action='store_false',
                        help='Disable system resource monitoring')
    parser.add_argument('--monitor-interval', type=int, default=5,
                        help='Resource monitoring interval in seconds (default: 5)')
    parser.add_argument('--large-items', action='store_true',
                        help='Include large item tests (10KB, 100KB, 1000KB) in addition to standard tests')
    parser.add_argument('--validate', action='store_true',
                        help='Enable data integrity validation mode')
    args = parser.parse_args()

    # Load benchmark configuration
    config = load_benchmark_config()

    # Use command-line values
    NUM_DOCS = args.num_docs
    NUM_RUNS = args.num_runs
    BATCH_SIZE = args.batch_size
    QUERY_LINKS = args.query_links

    # Add large item tests if requested
    global SINGLE_ATTR_TESTS, MULTI_ATTR_TESTS
    if args.large_items:
        SINGLE_ATTR_TESTS = SINGLE_ATTR_TESTS + LARGE_SINGLE_ATTR_TESTS
        MULTI_ATTR_TESTS = MULTI_ATTR_TESTS + LARGE_MULTI_ATTR_TESTS
        print("\n✓ Large item tests enabled (10KB, 100KB, 1000KB)")

    # Add cloud databases if enabled in config AND requested via CLI (or no specific DB flags)
    cloud_dbs = get_enabled_cloud_databases(config)
    any_db_flag = (args.mongodb or args.documentdb or args.postgresql or
                   args.yugabytedb or args.cockroachdb or
                   args.mongodb_atlas or args.azure_documentdb)

    for cloud_db in cloud_dbs:
        # Include cloud DB if its specific flag is passed, or if no DB flags are passed at all
        if not any_db_flag:
            DATABASES.append(cloud_db)
        elif (args.mongodb_atlas and cloud_db['db_type'] == 'mongodb-cloud') or \
             (args.azure_documentdb and cloud_db['db_type'] == 'documentdb-azure'):
            DATABASES.append(cloud_db)

    # Filter databases based on arguments (if no args, run all)
    if any_db_flag:
        enabled_databases = []
        for db in DATABASES:
            if (args.mongodb and db['db_type'] == 'mongodb') or \
               (args.documentdb and db['db_type'] == 'documentdb') or \
               (args.postgresql and db['db_type'] == 'postgresql') or \
               (args.yugabytedb and db['db_type'] == 'yugabytedb') or \
               (args.cockroachdb and db['db_type'] == 'cockroachdb') or \
               (args.mongodb_atlas and db['db_type'] == 'mongodb-cloud') or \
               (args.azure_documentdb and db['db_type'] == 'documentdb-azure'):
                enabled_databases.append(db)
        DATABASES = enabled_databases

    # Handle full comparison mode (run both no-index and with-index tests)
    if args.full_comparison:
        run_full_comparison_suite(args)
        return

    # Determine if queries should be enabled (queries work with or without indexes)
    enable_queries = args.queries

    # Remove index flags if --no-index is specified
    if args.no_index:
        for db in DATABASES:
            # Remove -i and -mv flags from all databases
            db['flags'] = db['flags'].replace(' -i', '').replace('-i ', '').replace(' -mv', '').replace('-mv ', '')

    print(f"\n{'='*80}")
    print("BENCHMARK: Replicating LinkedIn Article Tests (Docker Version)")
    print(f"{'='*80}")
    print(f"Document count: {NUM_DOCS:,}")
    print(f"Runs per test: {NUM_RUNS} (best time reported)")
    print(f"Batch size: {BATCH_SIZE}")
    if args.no_index:
        print(f"Index tests: DISABLED (insert-only mode)")
        if enable_queries:
            print(f"Query tests: ENABLED ({QUERY_LINKS} links per document, no indexes)")
        else:
            print(f"Query tests: DISABLED (use --queries to enable)")
    elif enable_queries:
        print(f"Query tests: ENABLED ({QUERY_LINKS} links per document)")
    else:
        print(f"Query tests: DISABLED (use --queries to enable)")
    print(f"Large items: {'ENABLED (10KB, 100KB, 1000KB)' if args.large_items else 'DISABLED'}")
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Initialize MongoDB results storage
    results_storage = None
    test_run_id = None
    system_info = None
    ci_info = None
    
    if RESULTS_STORAGE_AVAILABLE:
        try:
            # Get MongoDB connection string from config
            mongodb_conn = config.get('results_storage', 'mongodb_connection_string', fallback=None)
            db_name = config.get('results_storage', 'database_name', fallback='benchmark_results')
            coll_name = config.get('results_storage', 'collection_name', fallback='test_runs')
            
            if mongodb_conn:
                results_storage = connect_to_mongodb(mongodb_conn, db_name, coll_name)
                if results_storage:
                    print(f"✓ Connected to MongoDB results storage")
                else:
                    print(f"⚠️  Warning: Could not connect to MongoDB, results will not be stored")
            else:
                print(f"⚠️  Warning: MongoDB connection string not configured, results will not be stored")
        except Exception as e:
            print(f"⚠️  Warning: Could not initialize MongoDB storage: {e}")
        
        # Generate test run ID
        if uuid:
            test_run_id = str(uuid.uuid4())
            print(f"Test Run ID: {test_run_id}")
        
        # Collect system info once at start
        try:
            system_info = get_system_info()
        except Exception as e:
            print(f"⚠️  Warning: Could not collect system info: {e}")
        
        # Collect CI info
        try:
            ci_info = get_ci_info()
            if ci_info.get('ci_run'):
                print(f"✓ CI environment detected: {ci_info.get('ci_platform')}")
        except Exception as e:
            print(f"⚠️  Warning: Could not collect CI info: {e}")
    
    # Stop all databases first to ensure clean start
    stop_all_databases()

    # Track database activity for visualization
    activity_log = []
    
    try:
        # Run single-attribute tests (with per-test monitoring if enabled)
        single_results = run_test_suite(SINGLE_ATTR_TESTS, "SINGLE", enable_queries=enable_queries,
                                       measure_sizes=args.measure_sizes, track_activity=True,
                                       activity_log=activity_log, config=config,
                                       results_storage=results_storage, test_run_id=test_run_id,
                                       system_info=system_info, ci_info=ci_info,
                                       enable_monitoring=args.monitor, monitor_interval=args.monitor_interval,
                                       validate=args.validate)

        # Run multi-attribute tests (with per-test monitoring if enabled)
        multi_results = run_test_suite(MULTI_ATTR_TESTS, "MULTI", enable_queries=enable_queries,
                                      measure_sizes=args.measure_sizes, track_activity=True,
                                      activity_log=activity_log, config=config,
                                      results_storage=results_storage, test_run_id=test_run_id,
                                      system_info=system_info, ci_info=ci_info,
                                      enable_monitoring=args.monitor, monitor_interval=args.monitor_interval,
                                      validate=args.validate)

        # Generate summary
        generate_summary_table(single_results, multi_results)

        # Store all results to MongoDB at the end
        if results_storage:
            print(f"\n{'='*80}")
            print("STORING RESULTS TO MONGODB")
            print(f"{'='*80}")
            stored_count = 0
            stored_count += store_results_to_mongodb(single_results, results_storage)
            stored_count += store_results_to_mongodb(multi_results, results_storage)
            print(f"✓ Stored {stored_count} test results to MongoDB")
        
    finally:
        # Close MongoDB connection
        if results_storage:
            results_storage.close()

    # Save results to JSON
    output_data = {
        "timestamp": datetime.now().isoformat(),
        "configuration": {
            "documents": NUM_DOCS,
            "runs": NUM_RUNS,
            "batch_size": BATCH_SIZE,
            "query_tests_enabled": enable_queries,
            "query_links": QUERY_LINKS if enable_queries else None,
            "monitoring_enabled": args.monitor
        },
        "single_attribute": single_results,
        "multi_attribute": multi_results,
        "database_activity": activity_log
    }

    # Save results to JSON (optional, for debugging)
    # Results are now primarily stored in MongoDB
    output_file = "article_benchmark_results.json"
    try:
        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2)
        print(f"\n{'='*80}")
        print(f"✓ Results saved to: {output_file} (local backup)")
    except Exception as e:
        print(f"\n⚠️  Warning: Could not save local JSON file: {e}")
    
    if args.monitor:
        print(f"✓ Resource monitoring enabled (per-test metrics stored with each result)")
    
    print(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    main()

