#!/bin/bash
# Docker-based multi-database benchmark testing script
# Runs benchmarks against MongoDB, PostgreSQL, YugabyteDB, and CockroachDB
# Results are automatically stored to MongoDB if configured

# Get the project root (parent of scripts directory)
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPTS_DIR="$PROJECT_ROOT/scripts"
cd "$PROJECT_ROOT"

# Auto-generate config.properties with Docker-appropriate defaults if missing
if [ ! -f "$PROJECT_ROOT/config.properties" ]; then
    echo "config.properties not found - generating with Docker defaults..."
    cat > "$PROJECT_ROOT/config.properties" <<'CONFIGEOF'
# Auto-generated config.properties for Docker-based testing
# See config/config.properties.example for full documentation

# MongoDB Connection
mongodb.connection.string=mongodb://localhost:27017

# PostgreSQL Connection
postgresql.connection.string=jdbc:postgresql://localhost:5432/test?user=postgres&password=password

# DocumentDB Connection (MongoDB-compatible)
documentdb.connection.string=mongodb://testuser:testpass@localhost:10260/?directConnection=true&authMechanism=SCRAM-SHA-256&serverSelectionTimeoutMS=60000&connectTimeoutMS=30000&socketTimeoutMS=60000
CONFIGEOF
    echo "✓ Generated config.properties with Docker defaults"
fi

# Configuration
STORE_RESULTS=${STORE_RESULTS:-true}  # Set to false to disable MongoDB storage
TEST_RUN_ID=${TEST_RUN_ID:-"test.sh-$(date +%Y%m%d-%H%M%S)-$$"}
LOG_DIR="$PROJECT_ROOT/tmp/test_logs"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Create log directory
mkdir -p "$LOG_DIR"

# Check Python dependencies needed for results storage
check_python_deps() {
    if [ "$STORE_RESULTS" != "true" ]; then
        return 0
    fi

    log_info "Checking Python dependencies for results storage..."

    if python3 -c 'import pymongo' 2>/dev/null; then
        log_success "pymongo is available"
    else
        log_warning "pymongo not found, installing..."
        if pip3 install pymongo 2>/dev/null || pip install pymongo 2>/dev/null || python3 -m pip install pymongo 2>/dev/null; then
            log_success "pymongo installed successfully"
        else
            log_warning "Failed to install pymongo - results storage will be unavailable"
            STORE_RESULTS=false
        fi
    fi

    # Install any other dependencies from requirements.txt if present
    local req_file="$PROJECT_ROOT/requirements.txt"
    if [ -f "$req_file" ]; then
        pip3 install -r "$req_file" --quiet 2>/dev/null || pip install -r "$req_file" --quiet 2>/dev/null || python3 -m pip install -r "$req_file" --quiet 2>/dev/null || true
    fi
}

check_python_deps

# Build the project if needed
[ -f ./target/insertTest-1.0-jar-with-dependencies.jar ] || {
    log_info "Building project..."
    mvn clean package -q
}

# Map db_type to docker image name
get_docker_image() {
    case "$1" in
        mongodb)       echo "mongo" ;;
        documentdb)    echo "documentdb-local" ;;
        postgresql)    echo "postgres" ;;
        yugabytedb)    echo "yugabytedb/yugabyte" ;;
        cockroachdb)   echo "cockroachdb/cockroach" ;;
        *)             echo "unknown" ;;
    esac
}

# Map db_type to docker container name
get_container_name() {
    case "$1" in
        documentdb)    echo "documentdb" ;;
        *)             echo "db" ;;
    esac
}

# Function to store results in MongoDB
store_results() {
    local db_type="$1"
    local output_file="$2"

    if [ "$STORE_RESULTS" != "true" ]; then
        return 0
    fi

    if [ ! -f "$output_file" ]; then
        log_warning "No output file to store for $db_type"
        return 1
    fi

    local docker_image
    docker_image=$(get_docker_image "$db_type")
    local container_name
    container_name=$(get_container_name "$db_type")

    log_info "Storing $db_type results to MongoDB..."
    python3 "$SCRIPTS_DIR/store_benchmark_results.py" \
        --db-type "$db_type" \
        --test-run-id "$TEST_RUN_ID" \
        --input-file "$output_file" \
        --docker-image "$docker_image" \
        --container-name "$container_name"

    local exit_code=$?
    if [ $exit_code -eq 0 ]; then
        log_success "Results stored for $db_type"
    else
        log_warning "Failed to store results for $db_type (exit code: $exit_code)"
    fi
    return $exit_code
}

# Get connection string for a database type (used to override config.properties via -Dconn)
get_connection_string() {
    case "$1" in
        mongodb)       echo "mongodb://localhost:27017" ;;
        documentdb)    echo "mongodb://testuser:testpass@localhost:10260/?directConnection=true&authMechanism=SCRAM-SHA-256&serverSelectionTimeoutMS=60000&connectTimeoutMS=30000&socketTimeoutMS=60000" ;;
        postgresql)    echo "jdbc:postgresql://localhost:5432/test?user=postgres&password=password" ;;
        yugabytedb)    echo "jdbc:postgresql://localhost:5432/test?user=postgres&password=password" ;;
        cockroachdb)   echo "jdbc:postgresql://localhost:5432/test?user=postgres&password=password" ;;
        *)             echo "" ;;
    esac
}

# Function to run benchmark and capture output
run_benchmark() {
    local db_type="$1"
    local extra_flags="$2"
    shift 2  # Remove db_type and extra_flags so "$@" only contains user args
    local output_file="$LOG_DIR/${db_type}_$(date +%Y%m%d_%H%M%S).log"
    local conn_string
    conn_string=$(get_connection_string "$db_type")

    log_info "Running $db_type benchmark..."
    echo "========================================" | tee "$output_file"
    echo "Database: $db_type" | tee -a "$output_file"
    echo "Timestamp: $(date)" | tee -a "$output_file"
    echo "Test Run ID: $TEST_RUN_ID" | tee -a "$output_file"
    echo "Extra flags: $extra_flags $*" | tee -a "$output_file"
    echo "========================================" | tee -a "$output_file"

    # Run the benchmark with explicit connection string override (-Dconn)
    # This ensures Docker-correct credentials/ports regardless of config.properties
    java -Dconn="$conn_string" -jar ./target/insertTest-1.0-jar-with-dependencies.jar $extra_flags "$@" 2>&1 | tee -a "$output_file"
    local exit_code=${PIPESTATUS[0]}

    if [ $exit_code -eq 0 ]; then
        log_success "$db_type benchmark completed"
        # Store results to MongoDB
        store_results "$db_type" "$output_file"
    else
        log_error "$db_type benchmark failed (exit code: $exit_code)"
    fi

    return $exit_code
}

# Function to cleanup Docker container
cleanup_container() {
    local container_name="$1"
    docker rm -f "$container_name" 2>/dev/null || true
}

# Function to wait for database to be ready
wait_for_db() {
    local container_name="$1"
    local check_cmd="$2"
    local max_attempts="${3:-30}"
    local attempt=1

    log_info "Waiting for $container_name to be ready..."
    while [ $attempt -le $max_attempts ]; do
        if eval "$check_cmd" >/dev/null 2>&1; then
            log_success "$container_name is ready"
            return 0
        fi
        sleep 2
        attempt=$((attempt + 1))
    done

    log_error "$container_name failed to start after $max_attempts attempts"
    return 1
}

# Print test run header
echo ""
echo "========================================"
echo "  Docker-Based Database Benchmark"
echo "========================================"
echo "Test Run ID: $TEST_RUN_ID"
echo "Store Results: $STORE_RESULTS"
echo "Log Directory: $LOG_DIR"
echo "Arguments: $*"
echo "========================================"
echo ""

# Track overall success
overall_success=true

# ============================================
# MongoDB
# ============================================
log_info "Starting MongoDB container..."
cleanup_container "db"
docker run --name db --rm -d -p 27017:27017 mongo

if wait_for_db "db" "docker exec db mongosh --eval 'db.runCommand({ping:1})'" 30; then
    run_benchmark "mongodb" "" "$@" || overall_success=false
else
    log_error "MongoDB failed to start"
    overall_success=false
fi
cleanup_container "db"

echo ""

# ============================================
# DocumentDB (MongoDB-compatible, open-source)
# ============================================
log_info "Starting DocumentDB container..."
cleanup_container "documentdb"

# Pull and tag DocumentDB image if needed
documentdb_image_ready=true
if ! docker images -q documentdb-local:latest | grep -q .; then
    log_info "Pulling DocumentDB image..."
    if docker pull ghcr.io/documentdb/documentdb/documentdb-local:latest; then
        docker tag ghcr.io/documentdb/documentdb/documentdb-local:latest documentdb-local:latest
        log_success "DocumentDB image ready"
    else
        log_error "Failed to pull DocumentDB image"
        overall_success=false
        documentdb_image_ready=false
    fi
fi

if [ "$documentdb_image_ready" = true ]; then
    # Start DocumentDB container (uses port 10260 internally)
    docker run --name documentdb --rm -d -p 10260:10260 documentdb-local:latest --username testuser --password testpass

    # DocumentDB is slower to initialize than MongoDB - use a longer timeout (90 attempts × 2s = 180s)
    # and verify with an actual authenticated MongoDB ping, not just a port check
    # Readiness check: try pymongo ping, then mongosh from host, then psql inside container
    # (DocumentDB is PostgreSQL-based, so psql on internal port 9712 verifies the engine is ready)
    if wait_for_db "documentdb" "python3 -c \"from pymongo import MongoClient; c=MongoClient('mongodb://testuser:testpass@localhost:10260/?directConnection=true', serverSelectionTimeoutMS=3000); c.admin.command('ping')\" 2>/dev/null || mongosh --host localhost --port 10260 --username testuser --password testpass --authenticationDatabase admin --quiet --eval 'db.runCommand({ping:1})' 2>/dev/null || docker exec documentdb psql -h localhost -p 9712 -U testuser -d postgres -c 'SELECT 1' 2>/dev/null" 90; then
        # Verify DocumentDB can actually perform operations (not just accept connections)
        # Try pymongo for full MongoDB protocol check, fall back to psql inside container
        log_info "Verifying DocumentDB is fully operational..."
        documentdb_operational=false
        for verify_attempt in $(seq 1 10); do
            # Try pymongo first (full MongoDB wire protocol verification)
            if python3 -c "
from pymongo import MongoClient
c = MongoClient('mongodb://testuser:testpass@localhost:10260/?directConnection=true', serverSelectionTimeoutMS=5000)
db = c['_readiness_check']
db['_test'].insert_one({'check': 1})
db['_test'].find_one({'check': 1})
c.drop_database('_readiness_check')
print('ok')
" 2>/dev/null | grep -q "ok"; then
                log_success "DocumentDB is fully operational (pymongo)"
                documentdb_operational=true
                break
            fi
            # Fall back to psql inside container (verifies PostgreSQL engine processes queries)
            if docker exec documentdb psql -h localhost -p 9712 -U testuser -d postgres -c 'SELECT 1' 2>/dev/null | grep -q "1"; then
                log_success "DocumentDB is fully operational (psql)"
                documentdb_operational=true
                break
            fi
            sleep 2
        done
        if [ "$documentdb_operational" = true ]; then
            # Allow the MongoDB wire protocol to fully stabilize after verification.
            # DocumentDB's protocol layer can briefly become unresponsive after initial connections.
            log_info "Waiting for DocumentDB wire protocol to stabilize..."
            sleep 10
            run_benchmark "documentdb" "-ddb" "$@" || overall_success=false
        else
            log_error "DocumentDB accepted connections but failed operational verification"
            overall_success=false
        fi
    else
        log_error "DocumentDB failed to start"
        overall_success=false
    fi
    cleanup_container "documentdb"
fi

echo ""

# ============================================
# PostgreSQL
# ============================================
log_info "Starting PostgreSQL container..."
cleanup_container "db"
docker run --name db --rm -d -p 5432:5432 -e POSTGRES_PASSWORD=password postgres

if wait_for_db "db" "docker exec db pg_isready -U postgres" 30; then
    # Create test database (with timeout to prevent infinite hang)
    attempts=0
    max_attempts=30
    until echo "CREATE DATABASE test;" | docker exec -i db psql -U postgres 2>/dev/null || [ $attempts -ge $max_attempts ]; do
        sleep 2
        attempts=$((attempts + 1))
    done
    if [ $attempts -ge $max_attempts ]; then
        log_error "PostgreSQL CREATE DATABASE timed out after $max_attempts attempts"
        overall_success=false
    else
        run_benchmark "postgresql" "-p" "$@" || overall_success=false
    fi
else
    log_error "PostgreSQL failed to start"
    overall_success=false
fi
cleanup_container "db"

echo ""

# ============================================
# YugabyteDB
# ============================================
log_info "Starting YugabyteDB container..."
cleanup_container "db"
docker run --name db -d -p 5432:5433 yugabytedb/yugabyte yugabyted start --background=false

if wait_for_db "db" "docker exec db yugabyted status" 60; then
    # Wait for YSQL to be ready and create test database
    # Note: YugabyteDB binds YSQL to the container hostname, not localhost,
    # so we must pass -h $(hostname) to ysqlsh
    sleep 10
    attempts=0
    max_attempts=30
    until docker exec db ysqlsh -h $(docker exec db hostname) -U yugabyte -c "CREATE DATABASE test;" 2>/dev/null || [ $attempts -ge $max_attempts ]; do
        sleep 5
        attempts=$((attempts + 1))
    done
    if [ $attempts -ge $max_attempts ]; then
        log_error "YugabyteDB CREATE DATABASE timed out after $max_attempts attempts"
        overall_success=false
    else
        run_benchmark "yugabytedb" "-p" "$@" || overall_success=false
    fi
else
    log_error "YugabyteDB failed to start"
    overall_success=false
fi
cleanup_container "db"

echo ""

# ============================================
# CockroachDB
# ============================================
log_info "Starting CockroachDB container..."
cleanup_container "db"
docker run --name db -d -p 5432:26257 cockroachdb/cockroach start-single-node --insecure

if wait_for_db "db" "docker exec db cockroach sql --insecure -e 'SELECT 1'" 30; then
    # Create test database and postgres user
    echo "CREATE DATABASE test;" | docker exec -i db cockroach sql --insecure
    echo "CREATE USER IF NOT EXISTS postgres;" | docker exec -i db cockroach sql --insecure
    echo "GRANT ALL ON DATABASE test TO postgres;" | docker exec -i db cockroach sql --insecure
    run_benchmark "cockroachdb" "-p" "$@" || overall_success=false
else
    log_error "CockroachDB failed to start"
    overall_success=false
fi
cleanup_container "db"

echo ""

# ============================================
# Summary
# ============================================
echo "========================================"
echo "  Benchmark Summary"
echo "========================================"
echo "Test Run ID: $TEST_RUN_ID"
echo "Log files saved to: $LOG_DIR"

if [ "$STORE_RESULTS" = "true" ]; then
    echo ""
    echo "Results stored to MongoDB."
    echo "View results at: http://localhost:3000 (if webapp is running)"
fi

echo ""
if [ "$overall_success" = true ]; then
    log_success "All benchmarks completed successfully"
    exit 0
else
    log_warning "Some benchmarks failed - check logs for details"
    exit 1
fi
