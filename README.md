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

- Java 8 or higher
- Maven 3.x
- Docker (for using the automated test script)
- Access to at least one of the supported database systems

## Project Structure

```
BSON-JSON-bakeoff/
├── src/main/java/com/mongodb/
│   ├── Main.java                    # Entry point and argument parsing
│   ├── DatabaseOperations.java     # Interface for database operations
│   ├── MongoDBOperations.java      # MongoDB implementation
│   ├── PostgreSQLOperations.java   # PostgreSQL implementation
│   └── Oracle23AIOperations.java   # Oracle 23AI implementation
├── pom.xml                          # Maven project configuration
├── test.sh                          # Automated testing script with Docker
└── README.md                        # This file
```

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/rhoulihan/BSON-JSON-bakeoff.git
cd BSON-JSON-bakeoff
```

### 2. Configure Database Connection

Before building, edit the connection strings in `src/main/java/com/mongodb/Main.java`:

```java
// Lines 112-114 in Main.java
String mongoConnectionString = "mongodb://localhost:27017";
String postgresConnectionString = "jdbc:postgresql://localhost:5432/test?user=postgres&password=YOUR_PASSWORD";
String oracleConnectionString = "jdbc:oracle:thin:@localhost:1521/FREEPDB1";
```

Replace:
- `YOUR_PASSWORD` with your PostgreSQL password
- `FREEPDB1` with your Oracle pluggable database name
- Modify the entire connection string to match your database configuration

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
| `-o` | Use Oracle 23AI instead of MongoDB | MongoDB |
| `-d` | Use direct table insertion (Oracle only, bypasses Duality View bug) | Duality View |
| `-j` | Use JSONB instead of JSON (requires `-p`) | JSON |
| `-i` | Run tests on both indexed and non-indexed tables | Indexed only |
| `-q [numLinks]` | Run query test with specified number of links | No query test |
| `-l [numLinks]` | Run `$lookup` test with specified number of links | No lookup test |
| `-r [numRuns]` | Number of times to run each test (keeps best result) | 1 |
| `-c [configFile]` | Load configuration from JSON file | None |
| `-s [sizes]` | Comma-delimited array of payload sizes in bytes | 100,1000 |
| `-n [numAttrs]` | Number of attributes to split payload across | 10 |
| `-b [batchSize]` | Number of documents to batch in each insert | 100 |
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

#### Example 11: Multiple Runs for Best Performance
```bash
java -jar target/insertTest-1.0-jar-with-dependencies.jar -o -d -q 10 -r 3 1000
```
Runs each test 3 times and reports the best (lowest) time:
- Useful for consistent benchmarking
- Eliminates outliers from JVM warmup or system load
- Provides more reliable performance comparison

#### Example 12: Using Configuration File
```bash
java -jar target/insertTest-1.0-jar-with-dependencies.jar -c config.json
```
Loads all settings from a JSON configuration file (see Configuration File section below).
Command-line arguments can override config file settings.

#### Example 13: Comprehensive Test
```bash
java -jar target/insertTest-1.0-jar-with-dependencies.jar -q 20 -n 100 -s 1000,5000,10000 -b 200 25000
```
Full-featured test with:
- 25,000 documents
- Three payload sizes: 1000B, 5000B, 10000B
- 100 attributes per document
- Batch size of 200
- Query test with 20 linked documents

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
  "jsonType": "json"
}
```

#### Config File Parameters

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `database` | string | Database to use: "mongodb", "postgresql", or "oracle23ai" | "mongodb" |
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
sh test.sh [OPTIONS]
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
sh test.sh -q 10 -n 200 -s 4000
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

## Performance Insights

Based on typical benchmark results:

1. **MongoDB** generally provides faster insertion times, especially with BSON's native binary format
2. **MongoDB** typically offers faster query performance for multikey index queries
3. **Oracle 23AI** with direct table insertion (`-d` flag) produces correct results matching MongoDB
4. **Oracle 23AI JSON Duality Views** offers unique advantages:
   - Unified access to data as both relational tables and JSON documents
   - ACID transaction guarantees with document-style operations
   - Automatic normalization/denormalization during writes/reads
   - Leverages relational indexes for query performance
   - Best-of-both-worlds approach for applications requiring both document flexibility and relational integrity
5. **Multiple Runs**: Using `-r` flag provides more consistent benchmarking by eliminating outliers from JVM warmup or system load
6. **Direct Table Insertion**: Oracle's direct insertion (`-d`) bypasses Duality View overhead but loses the automatic bidirectional JSON/relational mapping

### Additional Performance Notes

- **JSONB vs JSON**: PostgreSQL's JSONB format offers better query performance but slightly slower insertion compared to plain JSON
- **Indexing**: Multikey indexes significantly improve query performance but add overhead to insertions
- **Batch Size**: Larger batch sizes generally improve throughput but consume more memory
- **Oracle Overhead**: Direct table insertion in Oracle includes overhead from two separate INSERT operations, foreign key constraints, and multiple commits per batch
- **Attribute Distribution**: Splitting payloads across multiple attributes can have different impacts depending on the database

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

## Customization

### Adding New Database Implementations

To add support for additional databases:

1. Create a new class implementing the `DatabaseOperations` interface
2. Implement all required methods: `initializeDatabase`, `dropAndCreateCollections`, `insertDocuments`, `queryDocumentsById`, `queryDocumentsByIdWithInCondition`, `queryDocumentsByIdUsingLookup`, and `close`
3. Update `Main.java` to:
   - Add a new command-line flag for your database
   - Instantiate your implementation
   - Add connection string configuration

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
**Solution**: Update the connection string in `Main.java` or configure PostgreSQL to use trust authentication for localhost

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
