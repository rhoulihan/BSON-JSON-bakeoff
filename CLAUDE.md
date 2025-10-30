# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Java-based benchmarking tool that compares document storage and retrieval performance across MongoDB (BSON), PostgreSQL (JSON/JSONB), and Oracle 23AI (JSON Duality Views and JSON Collection Tables). Tests insertion speeds, query performance, and different payload/indexing strategies.

## Build and Run Commands

### Building
```bash
mvn clean package
```
Produces: `target/insertTest-1.0-jar-with-dependencies.jar`

### Running Benchmarks

Basic syntax:
```bash
java -jar target/insertTest-1.0-jar-with-dependencies.jar [OPTIONS] [numItems]
```

Common commands:
```bash
# MongoDB with default settings (10k docs, 100B and 1000B payloads)
java -jar target/insertTest-1.0-jar-with-dependencies.jar

# PostgreSQL with JSONB
java -jar target/insertTest-1.0-jar-with-dependencies.jar -p -j 20000

# Oracle JSON Collection Tables with query test
java -jar target/insertTest-1.0-jar-with-dependencies.jar -oj -q 10 -s 4000 -n 200

# Multiple runs for consistent benchmarking
java -jar target/insertTest-1.0-jar-with-dependencies.jar -r 3 -b 500 10000

# Using configuration file
java -jar target/insertTest-1.0-jar-with-dependencies.jar -c config.json
```

### Automated Report Generation

Generate comprehensive HTML report with benchmarks:
```bash
python3 generate_report.py
```
This runs MongoDB and Oracle JCT benchmarks (with/without search index) and creates `benchmark_report.html`.

### Docker-based Testing

Test multiple databases automatically:
```bash
sh test.sh [OPTIONS]
```
Sequentially tests MongoDB, PostgreSQL, YugabyteDB, and CockroachDB using Docker containers.

## Architecture

### Core Design Pattern

The codebase uses the **Strategy pattern** with `DatabaseOperations` interface defining common operations, allowing easy addition of new database backends:

- **Interface**: `DatabaseOperations` (6 methods)
- **Implementations**: `MongoDBOperations`, `PostgreSQLOperations`, `Oracle23AIOperations`, `OracleJCT`, `OracleJCT2`
- **Main coordinator**: `Main.java` handles argument parsing, document generation, and orchestration

### Key Components

**Main.java**:
- Entry point with command-line argument parsing
- Document generation with configurable payloads (split across N attributes or single attribute)
- Benchmark orchestration (insertion, querying with multikey indexes, $lookup operations)
- Configuration file support (JSON)

**DatabaseOperations interface**:
```java
void initializeDatabase(String connectionString);
void dropAndCreateCollections(List<String> collectionNames);
long insertDocuments(String collectionName, List<JSONObject> documents, int dataSize, boolean splitPayload);
int queryDocumentsById(String collectionName, String id);
int queryDocumentsByIdWithInCondition(String collectionName, JSONObject document);
int queryDocumentsByIdUsingLookup(String collectionName, String id);
void close();
```

**Database-specific implementations**:
- **MongoDBOperations**: Uses native BSON, multikey indexes, $in queries, $lookup aggregations
- **PostgreSQLOperations**: JSON/JSONB columns, GIN indexes, array containment operators
- **Oracle23AIOperations**: JSON Duality Views with bidirectional relational/document mapping (⚠️ has array insertion bug in Oracle 23AI Free, use `-d` flag for direct table insertion workaround)
- **OracleJCT/OracleJCT2**: Native JSON Collection Tables with OSON binary format, JSON path queries, search indexes

### Configuration Management

**Database connections**: `config.properties` (git-ignored, copy from `config.properties.example`)
```properties
mongodb.connection.string=mongodb://localhost:27017
postgresql.connection.string=jdbc:postgresql://localhost:5432/test?user=postgres&password=PASSWORD
oracle.connection.string=jdbc:oracle:thin:system/PASSWORD@localhost:1521/FREEPDB1
```

**Test configurations**: JSON files (e.g., `config.example.json`) with parameters like database type, numDocs, payload sizes, batch size, etc.

### Document Generation Strategy

Documents are generated in `Main.java` with:
- Deterministic random seed (42) for reproducible results
- Configurable payload sizes (default: 100B, 1000B)
- Payload distribution: single large attribute OR split across N attributes
- Array fields (`indexArray`) with configurable number of links for query testing
- All implementations use identical document generation for fair comparison

### Oracle 23AI Special Considerations

**JSON Duality Views** (`-o` flag):
- Creates normalized relational tables + JSON views providing unified access
- ⚠️ **Known bug in Oracle 23AI Free (23.0.0.0.0)**: Array values are incorrectly treated as globally unique during insertion through Duality Views, causing silent data loss
- **Workaround**: Use `-d` flag for direct table insertion (bypasses Duality View)
- Uses OSON (Oracle Binary JSON) format via `OracleJsonFactory` for efficient binary JSON creation

**JSON Collection Tables** (`-oj` flag):
- Simpler approach: direct JSON document storage (no relational mapping)
- Uses OSON binary format for storage efficiency
- JSON search indexes for array queries (`CREATE SEARCH INDEX`)
- JSON path expressions for queries (`JSON_EXISTS`, `JSON_VALUE`)
- More MongoDB-like semantics in Oracle

## Test Patterns

### Insertion Tests
- Single attribute vs multi-attribute payload distribution
- Batch insertion with configurable batch sizes
- Indexed vs non-indexed collections (`-i` flag)
- Multiple runs (`-r N`) to eliminate outliers and report best time

### Query Tests
- **Multikey index queries** (`-q N`): Query documents by array element values, with N links per document
- **$in condition queries** (`-i` with `-q`): Use $in operator for bulk queries
- **$lookup tests** (`-l N`): MongoDB aggregation pipeline joins

## Important Command-Line Flags

- `-p`: Use PostgreSQL instead of MongoDB
- `-o`: Use Oracle JSON Duality Views
- `-oj`: Use Oracle JSON Collection Tables (simpler than Duality Views)
- `-oj2`: Use OracleJCT2 implementation (alternative with different optimizations)
- `-d`: Direct table insertion for Oracle (bypasses Duality View bug)
- `-j`: Use JSONB instead of JSON (PostgreSQL only)
- `-i`: Run indexed vs non-indexed comparison, OR enable $in condition for queries
- `-q N`: Run query test with N array elements per document
- `-l N`: Run $lookup test with N links
- `-r N`: Run each test N times, report best result
- `-c FILE`: Load configuration from JSON file
- `-s SIZES`: Comma-delimited payload sizes (e.g., `-s 100,1000,5000`)
- `-n N`: Number of attributes to split payload across
- `-b N`: Batch size for bulk insertions

## Development Notes

### Adding New Database Support

1. Create class implementing `DatabaseOperations` interface
2. Add command-line flag in `Main.java` (around line 46-89)
3. Add connection string to `config.properties.example`
4. Implement all interface methods matching the semantics of existing implementations
5. See `Oracle23AIOperations.java` for a complete reference implementation

### Performance Optimization Context

- **Batch size**: Larger batches improve throughput but consume more memory (default: 100)
- **OSON format**: Oracle implementations use binary JSON (`OracleJsonFactory`) to eliminate text parsing overhead
- **Indexing**: B-tree indexes on normalized columns (Oracle Duality Views) or search indexes (Oracle JCT)
- **Multiple runs**: JVM warmup and system load can affect results; `-r 3` provides more consistent measurements

### Testing and Validation

- Test case for Oracle Duality View bug: `src/test/java/com/mongodb/TestDualityView.java`
- Automated cross-database testing: `test.sh` script with Docker
- Report generation: `generate_report.py` for HTML visualization with charts
