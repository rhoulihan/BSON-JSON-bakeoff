# BSON-JSON Bakeoff

A comprehensive benchmarking tool designed to compare the performance of document storage and retrieval across different database systems. This tool specifically measures insertion speeds and query performance between MongoDB (using BSON) and PostgreSQL-compatible databases (using JSON/JSONB).

## Overview

This project provides a Java-based benchmark utility that generates synthetic documents with configurable payloads and tests how efficiently various databases can insert and query these documents. The tool is particularly useful for:

- Comparing BSON vs JSON/JSONB storage formats
- Evaluating database performance with different document sizes and attribute distributions
- Testing indexed vs non-indexed collection performance
- Benchmarking query patterns including multikey indexes, `$in` conditions, and `$lookup` operations
- Assessing batch insertion strategies

## Supported Databases

- **MongoDB** - Native BSON document storage
- **PostgreSQL** - JSON and JSONB column types
- **YugabyteDB** - PostgreSQL-compatible distributed SQL
- **CockroachDB** - PostgreSQL-compatible distributed SQL
- **Oracle 23AI** - JSON Duality Views (unified relational and document access)
- **Oracle 23AI (JCT)** - JSON Collection Tables (native JSON document storage)

## Features

- **Configurable Payload Sizes**: Test with documents of varying sizes (default: 100B, 1000B)
- **Attribute Distribution**: Split payloads across multiple attributes or use a single large attribute
- **Batch Operations**: Configurable batch sizes for optimized bulk insertions
- **Index Comparison**: Test performance with and without indexes
- **Query Benchmarks**: Multiple query patterns including:
  - Multikey index queries
  - `$in` condition queries (MongoDB)
  - `$lookup` aggregation queries (MongoDB)
  - Array containment queries (PostgreSQL)

## Prerequisites

- **Operating System**: Oracle Linux 9.6 (or compatible RHEL-based distribution)
- **Java**: Java 8 or higher
- **Maven**: Maven 3.x
- **Docker**: For using the automated test script (optional)
- **Database Access**: At least one of the supported database systems

## Project Structure

```
BSON-JSON-bakeoff/
├── src/main/java/com/mongodb/
│   ├── Main.java                    # Entry point and argument parsing
│   ├── DatabaseOperations.java     # Interface for database operations
│   ├── MongoDBOperations.java      # MongoDB implementation (with WriteConcern.JOURNALED)
│   ├── PostgreSQLOperations.java   # PostgreSQL implementation
│   ├── Oracle23AIOperations.java   # Oracle 23AI Duality Views implementation
│   ├── OracleJCT.java               # Oracle JSON Collection Tables implementation
│   └── OracleJCT2.java              # Alternative Oracle JCT implementation
├── pom.xml                          # Maven project configuration
├── test.sh                          # Automated testing script with Docker
├── run_article_benchmarks.py       # Python benchmark orchestration with per-test restart
├── generate_html_report.py         # HTML report generation from benchmark results
├── CLAUDE.md                        # AI assistant guidance and project documentation
├── SAMPLE_DOCUMENTS.md             # Sample realistic document structures
├── README.md                        # This file (you are here)
└── document_cache/                  # Cached generated documents (git-ignored)
```

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/rhoulihan/BSON-JSON-bakeoff.git
cd BSON-JSON-bakeoff
```

### 2. Configure Database Connections

Create a `config.properties` file with your database connection strings:

```bash
cp config/config.properties.example config.properties
```

Then edit `config.properties` with your actual credentials:

```properties
# MongoDB Connection
mongodb.connection.string=mongodb://localhost:27017

# PostgreSQL Connection
postgresql.connection.string=jdbc:postgresql://localhost:5432/test?user=postgres&password=YOUR_PASSWORD

# Oracle Connection
oracle.connection.string=jdbc:oracle:thin:system/YOUR_PASSWORD@localhost:1521/FREEPDB1
```

Replace:
- `YOUR_PASSWORD` with your actual database passwords
- Host addresses and ports to match your database configuration
- `FREEPDB1` with your Oracle pluggable database name

**Note**: The `config.properties` file is excluded from git to keep your credentials secure. Never commit this file to version control.

### 3. Build the Project

```bash
mvn clean package
```

This creates an executable JAR file at:
```
target/insertTest-1.0-jar-with-dependencies.jar
```

## Usage

### Basic Command Structure

```bash
java -jar target/insertTest-1.0-jar-with-dependencies.jar [OPTIONS] [numItems]
```

### Command-Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `-p` | Use PostgreSQL instead of MongoDB | MongoDB |
| `-o` | Use Oracle 23AI Duality Views instead of MongoDB | MongoDB |
| `-oj` | Use Oracle JSON Collection Tables instead of MongoDB | MongoDB |
| `-d` | Use direct table insertion (Oracle Duality Views only, bypasses bug) | Duality View |
| `-j` | Use JSONB instead of JSON (requires `-p`) | JSON |
| `-i` | Run tests on both indexed and non-indexed tables | Indexed only |
| `-q [numLinks]` | Run query test with specified number of links | No query test |
| `-l [numLinks]` | Run `$lookup` test with specified number of links | No lookup test |
| `-r [numRuns]` | Number of times to run each test (keeps best result) | 1 |
| `-c [configFile]` | Load configuration from JSON file | None |
| `-s [sizes]` | Comma-delimited array of payload sizes in bytes | 100,1000 |
| `-n [numAttrs]` | Number of attributes to split payload across | 10 |
| `-b [batchSize]` | Number of documents to batch in each insert | 100 |
| `-rd` | Use realistic nested data structures (vs flat binary payloads) | Flat binary |
| `-mv` | Use multivalue indexes for Oracle JCT (requires `-i`, 7x faster than search indexes) | Search index |
| `[numItems]` | Total number of documents to generate | 10000 |

### Usage Examples

#### Example 1: Basic MongoDB Test
```bash
java -jar target/insertTest-1.0-jar-with-dependencies.jar
```
Inserts 10,000 documents into MongoDB with default payload sizes (100B and 1000B).

#### Example 2: PostgreSQL with JSONB
```bash
java -jar target/insertTest-1.0-jar-with-dependencies.jar -p -j 20000
```
Inserts 20,000 documents into PostgreSQL using JSONB format.

#### Example 3: Custom Payload Sizes
```bash
java -jar target/insertTest-1.0-jar-with-dependencies.jar -s 500,2000,5000
```
Tests MongoDB with three different payload sizes: 500B, 2000B, and 5000B.

#### Example 4: Multiple Attributes Test
```bash
java -jar target/insertTest-1.0-jar-with-dependencies.jar -n 50 -s 4000
```
Creates documents with 4000B payload split across 50 attributes.

#### Example 5: Query Performance Test
```bash
java -jar target/insertTest-1.0-jar-with-dependencies.jar -q 10 -s 4000 -n 200
```
Inserts documents with 4000B payload across 200 attributes, then runs query tests on 10 linked documents per query.

#### Example 6: Indexed vs Non-Indexed Comparison
```bash
java -jar target/insertTest-1.0-jar-with-dependencies.jar -p -i -s 2000
```
Tests PostgreSQL insertion into both indexed and non-indexed tables with 2000B payloads.

#### Example 7: Large Batch Size
```bash
java -jar target/insertTest-1.0-jar-with-dependencies.jar -b 500 50000
```
Inserts 50,000 documents using batch size of 500 documents per operation.

#### Example 8: Oracle 23AI with JSON Duality Views
```bash
java -jar target/insertTest-1.0-jar-with-dependencies.jar -o 20000
```
Tests Oracle 23AI using JSON Duality Views, inserting 20,000 documents with automatic bidirectional mapping between relational and document models.

#### Example 9: Oracle 23AI Query Performance Test
```bash
java -jar target/insertTest-1.0-jar-with-dependencies.jar -o -q 10 -s 4000 -n 200
```
Tests Oracle 23AI query performance with JSON Duality Views:
- 4000B payload across 200 attributes
- Query tests with 10 linked documents
- Leverages Oracle's JSON capabilities

#### Example 10: Oracle 23AI with Direct Table Insertion
```bash
java -jar target/insertTest-1.0-jar-with-dependencies.jar -o -d -q 10 1000
```
Tests Oracle 23AI using direct table insertion to bypass the Duality View array bug:
- Inserts 1000 documents
- Runs query tests with 10 linked documents
- Produces accurate results matching MongoDB

#### Example 11: Oracle JSON Collection Tables
```bash
java -jar target/insertTest-1.0-jar-with-dependencies.jar -oj 20000
```
Tests Oracle 23AI using native JSON Collection Tables:
- 20,000 documents
- Direct JSON document storage
- Simpler schema than Duality Views

#### Example 12: Oracle JSON Collection Tables with Query Test
```bash
java -jar target/insertTest-1.0-jar-with-dependencies.jar -oj -q 10 -s 4000 -n 200
```
Tests Oracle JSON Collection Tables with query performance:
- 4000B payload across 200 attributes
- Query tests with 10 linked documents
- Uses Oracle JSON path expressions for queries

#### Example 13: Multiple Runs for Best Performance
```bash
java -jar target/insertTest-1.0-jar-with-dependencies.jar -o -d -q 10 -r 3 1000
```
Runs each test 3 times and reports the best (lowest) time:
- Useful for consistent benchmarking
- Eliminates outliers from JVM warmup or system load
- Provides more reliable performance comparison

#### Example 14: Using Configuration File
```bash
java -jar target/insertTest-1.0-jar-with-dependencies.jar -c config.json
```
Loads all settings from a JSON configuration file (see Configuration File section below).
Command-line arguments can override config file settings.

#### Example 15: Comprehensive Test
```bash
java -jar target/insertTest-1.0-jar-with-dependencies.jar -q 20 -n 100 -s 1000,5000,10000 -b 200 25000
```
Full-featured test with:
- 25,000 documents
- Three payload sizes: 1000B, 5000B, 10000B
- 100 attributes per document
- Batch size of 200
- Query test with 20 linked documents

#### Example 16: Realistic Nested Data Structures
```bash
java -jar target/insertTest-1.0-jar-with-dependencies.jar -oj -i -mv -rd -q 10 -s 1000 -n 50 -r 3 -b 1000 10000
```
Tests Oracle JCT with realistic data structures:
- 10,000 documents with realistic nested data
- 1000B payload split across 50 attributes
- Nested subdocuments up to 5 levels deep
- Mixed data types: strings, integers, decimals, binary, arrays, booleans
- Multivalue indexes for optimal query performance (7x faster)
- 3 runs to ensure consistent results
- Query tests with 10 linked documents

**Note on realistic data**: The `-rd` flag generates documents with nested structures resembling real-world data, rather than flat binary blobs. This provides more accurate performance metrics for production workloads. See [SAMPLE_DOCUMENTS.md](SAMPLE_DOCUMENTS.md) for examples of the generated structures.

### Configuration File

You can use a JSON configuration file to specify all options instead of command-line arguments. This is especially useful for complex test scenarios or repeated benchmarking.

#### Config File Format

Create a JSON file (e.g., `config.json`) with the following structure:

```json
{
  "database": "mongodb",
  "numDocs": 10000,
  "numAttrs": 10,
  "batchSize": 100,
  "numLinks": 10,
  "numRuns": 3,
  "sizes": [100, 1000],
  "runQueryTest": true,
  "runIndexTest": false,
  "runLookupTest": false,
  "useInCondition": false,
  "useDirectTableInsert": false,
  "runSingleAttrTest": true,
  "jsonType": "json",
  "useMultivalueIndex": false,
  "useAsyncCommit": false,
  "useRealisticData": false
}
```

#### Config File Parameters

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `database` | string | Database to use: "mongodb", "postgresql", "oracle23ai", or "oraclejct" | "mongodb" |
| `numDocs` | integer | Number of documents to insert | 10000 |
| `numAttrs` | integer | Number of attributes to split payload across | 10 |
| `batchSize` | integer | Batch size for inserts | 100 |
| `numLinks` | integer | Number of array elements per document | 10 |
| `numRuns` | integer | Number of times to run each test | 1 |
| `sizes` | array | Payload sizes in bytes | [100, 1000] |
| `runQueryTest` | boolean | Run query performance tests | false |
| `runIndexTest` | boolean | Test both indexed and non-indexed tables | false |
| `runLookupTest` | boolean | Run $lookup tests (MongoDB) | false |
| `useInCondition` | boolean | Use $in condition for queries | false |
| `useDirectTableInsert` | boolean | Use direct table insertion (Oracle only) | false |
| `runSingleAttrTest` | boolean | Test single attribute payloads | true |
| `jsonType` | string | "json" or "jsonb" (PostgreSQL only) | "json" |
| `useMultivalueIndex` | boolean | Use multivalue indexes instead of search indexes (Oracle JCT only, 7x faster) | false |
| `useAsyncCommit` | boolean | Enable async commit mode (Oracle only, not ACID compliant) | false |
| `useRealisticData` | boolean | Use realistic nested data structures for multi-attribute tests | false |

#### Using Configuration Files

```bash
# Use config file only
java -jar target/insertTest-1.0-jar-with-dependencies.jar -c my-config.json

# Config file with command-line overrides
java -jar target/insertTest-1.0-jar-with-dependencies.jar -c my-config.json -r 5 -d

# The -d and -r flags override the config file settings
```

**Note:** Command-line arguments take precedence over configuration file settings, allowing you to easily override specific parameters without editing the config file.

## Automated Testing with Docker

The included `test.sh` script automates testing across multiple databases using Docker containers.

### Running the Test Script

```bash
sh scripts/test.sh [OPTIONS]
```

The script will:
1. Build the JAR if it doesn't exist
2. Start MongoDB in Docker and run tests
3. Start PostgreSQL in Docker and run tests
4. Start YugabyteDB in Docker and run tests
5. Start CockroachDB in Docker and run tests
6. Clean up Docker containers after each test

### Example Test Script Usage

```bash
sh scripts/test.sh -q 10 -n 200 -s 4000
```

This runs query tests with 200 attributes and 4000B payloads across all four database systems.

## Understanding the Output

### Insertion Metrics

```
Time taken to insert 10000 documents with 4000B payload in 1 attribute into indexed: 2052ms
Time taken to insert 10000 documents with 4000B payload in 200 attributes into indexed: 1351ms
```

Each line reports:
- Number of documents inserted
- Payload size in bytes
- Number of attributes (1 = single large attribute, N = split across N attributes)
- Collection/table type (indexed or noindex)
- Time in milliseconds

### Query Metrics

```
Total time taken to query 10000 ID's from indexedArray: 10169ms
Total items found: 99941
```

Query results show:
- Number of queries executed
- Query pattern used (multikey index, `$in`, `$lookup`, array containment)
- Total time in milliseconds
- Total number of matching documents found

## Sample Output

```
Using mongodb database.
Time taken to insert 10000 documents with 4000B payload in 1 attribute into indexed: 2052ms
Time taken to insert 10000 documents with 4000B payload in 200 attributes into indexed: 1351ms
Total time taken to query 10000 ID's with 10 element link arrays using multikey index: 10169ms
Total items found: 99941

PostgreSQL 16.3 (Debian 16.3-1.pgdg120+1) on x86_64-pc-linux-gnu
Time taken to insert 10000 documents with 4000B payload in 1 attribute into indexed: 16786ms
Time taken to insert 10000 documents with 4000B payload in 200 attributes into indexed: 17861ms
Total time taken to query 10000 ID's with 10 element link arrays using multikey index: 29485ms
Total items found: 99939
```

## Python Benchmarking Script

For automated, comprehensive benchmarking with per-test database isolation, use the Python orchestration script:

```bash
python3 scripts/run_article_benchmarks.py --mongodb --oracle --queries --batch-size 1000
```

### Key Features

- **Per-Test Database Restart**: Eliminates cache warmup effects by restarting the database before each test
- **Automated Test Orchestration**: Runs multiple test configurations sequentially
- **JSON Results Output**: Saves structured results for analysis (`full_comparison_results.json`)
- **Progress Logging**: Real-time output with detailed test progress
- **Configurable Test Suites**: Support for single/multi-attribute tests with various payload sizes

### Script Options

```bash
python3 scripts/run_article_benchmarks.py [OPTIONS]

Options:
  --mongodb          Include MongoDB tests
  --oracle           Include Oracle JCT tests
  --postgresql       Include PostgreSQL tests
  --queries          Run query tests with indexes (vs insert-only)
  --full-comparison  Run both indexed and non-indexed tests
  --batch-size N     Set batch size for inserts (default: 1000)
  --no-index         Run insert-only tests without indexes
```

### Example Workflows

```bash
# Full comparison: MongoDB vs Oracle with and without indexes
python3 scripts/run_article_benchmarks.py --mongodb --oracle --full-comparison --batch-size 1000

# Query-focused test: Compare query performance
python3 scripts/run_article_benchmarks.py --mongodb --oracle --queries --batch-size 1000

# Insert-only test: Pure insertion performance
python3 scripts/run_article_benchmarks.py --mongodb --oracle --no-index --batch-size 1000
```

The script automatically:
1. Stops all databases before starting
2. Starts the appropriate database for each test
3. Runs 3 iterations and keeps the best time
4. Stops the database after each test completes
5. Saves results to JSON for further analysis

## Performance Analysis and Benchmarking Methodology

This tool has been used to conduct comprehensive performance comparisons between MongoDB BSON and Oracle 23AI JSON Collection Tables. Recent updates include:

### Recent Bug Fixes and Improvements

1. **Collection Selection Fix** (Critical): Fixed a bug in `Main.java` where both indexed and non-indexed collections were tested when the `-i` flag was present, causing the loop to keep the fastest time from warmed caches. This was causing MongoDB to appear faster with indexes (impossible). Now correctly uses mutually exclusive selection.

2. **Per-Test Database Isolation**: Added `restart_per_test` feature in `run_article_benchmarks.py` to restart databases before each individual test, eliminating cache warmup effects and ensuring fair comparisons.

3. **WriteConcern.JOURNALED**: Added to MongoDB operations to force journal sync before acknowledging writes, providing more consistent timing measurements.

4. **Multivalue Index Optimization**: Oracle JCT now supports multivalue indexes (`-mv` flag) which are 7x faster than search indexes for array containment queries.

### Test Data

- **Standard Mode**: Flat binary payloads for basic performance testing
- **Realistic Mode** (`-rd` flag): Nested document structures with mixed data types
  - Subdocuments up to 5 levels deep
  - Mixed types: strings, integers, decimals, binary data, arrays, booleans
  - See [SAMPLE_DOCUMENTS.md](SAMPLE_DOCUMENTS.md) for examples

### Benchmark Methodology

- **Deterministic Generation**: Random seed of 42 ensures reproducible results
- **Multiple Runs**: 3 runs per test, best time reported
- **Batch Operations**: Configurable batch sizes (default: 1000)
- **Per-Test Isolation**: Database restart between tests eliminates cache effects
- **Identical Documents**: All databases test with the same generated documents
- **Document Caching**: Generated documents cached in `document_cache/` for consistency

For detailed guidance on running benchmarks and interpreting results, see [CLAUDE.md](CLAUDE.md).

## Oracle 23AI JSON Duality Views

Oracle 23AI introduces JSON Duality Views, a revolutionary feature that provides unified access to data through both relational and document paradigms simultaneously.

### What are JSON Duality Views?

JSON Duality Views provide:
- **Bidirectional Mapping**: Access the same data as relational tables or JSON documents
- **Automatic Normalization**: Write JSON documents, Oracle automatically normalizes to relational tables
- **Automatic Denormalization**: Read through views, Oracle automatically assembles JSON documents
- **ACID Guarantees**: Full transactional integrity for document operations
- **Performance**: Leverages relational indexes for fast queries

### Implementation Details

The Oracle implementation (`Oracle23AIOperations.java`) creates:
1. **Base Tables**: Normalized relational tables for document storage
2. **Duality Views**: JSON views that expose the relational data as documents
3. **Indexes**: Traditional B-tree indexes on normalized columns

Example structure:
```sql
-- Base document table
CREATE TABLE indexed_docs (
  doc_id VARCHAR2(100) PRIMARY KEY,
  payload JSON,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) TABLESPACE USERS;

-- Normalized array table with composite primary key
CREATE TABLE indexed_index_array (
  doc_id VARCHAR2(100),
  array_value VARCHAR2(100),
  CONSTRAINT pk_indexed_array PRIMARY KEY (doc_id, array_value),
  CONSTRAINT fk_indexed_doc FOREIGN KEY (doc_id)
    REFERENCES indexed_docs(doc_id) ON DELETE CASCADE
) TABLESPACE USERS;

-- Index for query performance
CREATE INDEX idx_indexed_array_value ON indexed_index_array(array_value);

-- JSON Duality View with correct array syntax
CREATE OR REPLACE JSON RELATIONAL DUALITY VIEW indexed_dv AS
SELECT JSON {
  '_id': d.doc_id,
  'data': d.payload,
  'indexArray': [
    (
      SELECT JSON {
        'value': a.array_value
      }
      FROM indexed_index_array a WITH INSERT UPDATE DELETE
      WHERE a.doc_id = d.doc_id
    )
  ]
}
FROM indexed_docs d WITH INSERT UPDATE DELETE;
```

**Important Note on Array Syntax:**
Arrays in Duality Views require a nested `SELECT JSON` subquery with an explicit `WHERE` clause that joins on the foreign key. This is documented in Oracle's JSON Duality Views specification. The simplified syntax (`table [ {field} ]`) does not work correctly for arrays.

### Connection Requirements

- Oracle 23AI Free or Enterprise Edition
- JDBC connection string format: `jdbc:oracle:thin:@host:port/service_name`
- Default: `jdbc:oracle:thin:@localhost:1521/FREEPDB1`

### Known Issues with Oracle 23AI Free (23.0.0.0.0)

⚠️ **Critical Bug: Array Value Insertion in Duality Views**

We have identified a significant bug in Oracle 23AI Free Release 23.0.0.0.0 that affects JSON Duality Views when inserting documents with array elements that contain duplicate values across different parent documents.

**Problem Description:**

When inserting JSON documents through a Duality View, Oracle incorrectly treats array values as globally unique, despite the underlying table having a composite PRIMARY KEY `(doc_id, array_value)`. This causes array elements to be silently dropped during insertion if the same value already exists in any other document.

**Expected Behavior:**
```sql
-- Insert 3 documents with overlapping array values
doc1: {_id: "test1", indexArray: [{value: "1"}, {value: "2"}, {value: "3"}]}
doc2: {_id: "test2", indexArray: [{value: "2"}, {value: "3"}, {value: "4"}]}
doc3: {_id: "test3", indexArray: [{value: "3"}, {value: "4"}, {value: "5"}]}

-- Should result in 9 rows in indexed_index_array table:
test1 -> 1, 2, 3
test2 -> 2, 3, 4  (values 2 and 3 reused)
test3 -> 3, 4, 5  (values 3 and 4 reused)
```

**Actual Behavior:**
```sql
-- Only 5 rows inserted, with values silently dropped:
test1 -> 1, 2, 3  ✓ (first document works correctly)
test2 -> 4        ✗ (values 2 and 3 silently dropped)
test3 -> 5        ✗ (values 3 and 4 silently dropped)
```

**Impact on Benchmarks:**
- With 1,000 documents × 10 array elements = expected 10,000 rows
- Actual result: ~1,000 rows (only ~10% inserted correctly)
- Only ~30% of documents receive any array data
- First documents get complete arrays; later documents get partial/no arrays
- Query results: Oracle returns ~1,000 items vs MongoDB's correct ~10,000

**Reproduction:**

A test case demonstrating this bug is included in `src/test/java/com/mongodb/TestDualityView.java`. Run it with:

```bash
javac -cp target/insertTest-1.0-jar-with-dependencies.jar src/test/java/com/mongodb/TestDualityView.java
java -cp "src/test/java:target/insertTest-1.0-jar-with-dependencies.jar" com.mongodb.TestDualityView
```

**Status:**

This bug has been confirmed using the correct Duality View syntax as documented in Oracle's JSON Relational Duality Views specification. The issue appears to be in Oracle's implementation of array handling within Duality Views, not in our code or schema design.

**Workaround:**

Use the `-d` flag to enable direct table insertion, which bypasses the Duality View and produces accurate results:

```bash
java -jar target/insertTest-1.0-jar-with-dependencies.jar -o -d -q 10 1000
```

This inserts data directly into the underlying relational tables (`indexed_docs` and `indexed_index_array`) instead of using the Duality View, avoiding the array duplication bug entirely. With `-d` enabled, Oracle 23AI correctly stores all 10,000 array elements and produces query results matching MongoDB.

Alternatively, use Oracle 23AI Enterprise Edition if available (bug status unknown on Enterprise Edition).

**Reference:**
- Commit: `389b353` - "Fix Duality View syntax and confirm Oracle 23AI array insertion bug"
- Test case: `src/test/java/com/mongodb/TestDualityView.java`

## Oracle JSON Collection Tables

Oracle 23AI also provides JSON Collection Tables (accessible via the `-oj` flag), which offer a simpler, more direct approach to JSON document storage compared to Duality Views.

### What are JSON Collection Tables?

JSON Collection Tables provide:
- **Native JSON Storage**: Store and retrieve JSON documents directly without relational mapping
- **Simpler Schema**: No need to design normalized relational tables
- **Direct JDBC Access**: Insert and query JSON documents using standard JDBC operations
- **Oracle JSON Support**: Leverage Oracle's native JSON data type and query capabilities
- **ACID Guarantees**: Full transactional integrity like all Oracle tables

### Key Differences from Duality Views

| Feature | JSON Collection Tables (`-oj`) | Duality Views (`-o`) |
|---------|-------------------------------|----------------------|
| **Schema Design** | Automatic - just create the collection | Manual - design relational tables + views |
| **Insertion** | Direct JSON document insert | Insert through view, Oracle normalizes |
| **Storage** | JSON documents in single table | Normalized across multiple relational tables |
| **Queries** | JSON path expressions | SQL joins on relational tables |
| **Complexity** | Simple, document-focused | Complex, hybrid relational/document |
| **Use Case** | Pure document workloads | Unified relational + document access |

### Implementation Details

The Oracle JCT implementation (`OracleJCT.java`) uses:
1. **JSON Collection Tables**: Created with `CREATE JSON COLLECTION TABLE` statement
2. **Native OSON Format**: Binary JSON format for efficient storage and querying
3. **Flexible Indexing**: Supports both search indexes and multivalue indexes
4. **JSON Path Queries**: Uses `JSON_EXISTS` and `JSON_VALUE` for document queries

#### Index Types

Oracle JCT supports two types of indexes for array queries:

**Search Indexes** (default):
```sql
CREATE SEARCH INDEX idx_targets ON indexed (data) FOR JSON;
```
- General-purpose full-text index for JSON documents
- Works with complex JSON path expressions
- Moderate performance for array containment queries

**Multivalue Indexes** (`-mv` flag, 7x faster):
```sql
CREATE MULTIVALUE INDEX idx_targets ON indexed (data.targets[*].string());
```
- Specialized index for array elements with explicit `[*].string()` syntax
- Significantly faster for array containment queries (4,110 vs 572 queries/sec)
- Requires specific query syntax: `JSON_EXISTS(data, '$.targets?(@ == $val)' PASSING ? AS "val")`
- **Recommended for production use** when querying array fields

Example queries:
```sql
-- Query with search index
SELECT data FROM indexed
WHERE JSON_EXISTS(data, '$?(@.targets[*] == $id)' PASSING '123' AS "id");

-- Query with multivalue index (7x faster)
SELECT data FROM indexed
WHERE JSON_EXISTS(data, '$.targets?(@ == $val)' PASSING '123' AS "val");
```

To use multivalue indexes in benchmarks, add the `-mv` flag:
```bash
java -jar target/insertTest-1.0-jar-with-dependencies.jar -oj -i -mv -q 10 10000
```

### When to Use JSON Collection Tables vs Duality Views

**Use JSON Collection Tables (`-oj`) when:**
- You have pure document-oriented workloads
- You want MongoDB-like simplicity in Oracle
- You don't need relational access to the data
- You want to avoid the Duality View array insertion bug

**Use Duality Views (`-o` with `-d`) when:**
- You need both relational and document access to the same data
- You want to leverage existing relational tools and queries
- You need complex joins across normalized tables
- You're willing to manage a more complex schema

### Connection Requirements

Same as Oracle 23AI Duality Views:
- Oracle 23AI Free or Enterprise Edition
- JDBC connection string format: `jdbc:oracle:thin:@host:port/service_name`
- Default: `jdbc:oracle:thin:@localhost:1521/FREEPDB1`

## Customization

### Adding New Database Implementations

To add support for additional databases:

1. Create a new class implementing the `DatabaseOperations` interface
2. Implement all required methods: `initializeDatabase`, `dropAndCreateCollections`, `insertDocuments`, `queryDocumentsById`, `queryDocumentsByIdWithInCondition`, `queryDocumentsByIdUsingLookup`, and `close`
3. Update `Main.java` to:
   - Add a new command-line flag for your database
   - Instantiate your implementation
   - Add logic to read the connection string from `config.properties`
4. Add your database connection string to `config/config.properties.example` and `config.properties`

The `Oracle23AIOperations.java` class provides a complete example of implementing support for a new database system.

### Modifying Test Data

Document generation occurs in the `generateDocuments` method in `Main.java`. All database implementations use the same document generation logic to ensure fair comparisons. Customize this method to:
- Add additional fields
- Change document structure
- Include specific data patterns
- Implement different linking strategies
- Modify the random seed for reproducibility (currently set to 42)

## Troubleshooting

### Connection Issues

**Problem**: `Connection refused` errors
**Solution**: Ensure the database is running on localhost and the port matches your connection string

### Memory Issues

**Problem**: `OutOfMemoryError` during large batch operations
**Solution**:
- Reduce batch size using `-b` option
- Reduce total document count
- Increase JVM heap size: `java -Xmx4g -jar ...`

### Build Failures

**Problem**: Maven dependency resolution errors
**Solution**:
```bash
mvn clean install -U
```

### PostgreSQL Password Authentication

**Problem**: Password authentication fails
**Solution**: Update the connection string in `config.properties` or configure PostgreSQL to use trust authentication for localhost

### Configuration File Not Found

**Problem**: `ERROR: Could not load config.properties file`
**Solution**: Create `config.properties` from the template:
```bash
cp config/config.properties.example config.properties
```
Then edit it with your actual database credentials

## Contributing

Contributions are welcome! Areas for improvement:
- Additional database support (e.g., Couchbase, DynamoDB)
- More query patterns
- Statistical analysis of results
- Graphical result visualization
- Web-based UI for running tests and viewing results

## License

This project is licensed under the Apache License 2.0. See the `LICENSE` file for details.

## Authors

Rick Houlihan - Initial development

## Acknowledgments

This benchmark tool was created to provide objective performance comparisons between document-oriented and relational databases when handling semi-structured data.
