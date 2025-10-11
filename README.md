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
│   └── PostgreSQLOperations.java   # PostgreSQL implementation
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
// Line 108-109 in Main.java
String mongoConnectionString = "mongodb://localhost:27017";
String postgresConnectionString = "jdbc:postgresql://localhost:5432/test?user=postgres&password=YOUR_PASSWORD";
```

Replace `YOUR_PASSWORD` with your PostgreSQL password, or modify the entire connection string to match your database configuration.

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
| `-j` | Use JSONB instead of JSON (requires `-p`) | JSON |
| `-i` | Run tests on both indexed and non-indexed tables | Indexed only |
| `-q [numLinks]` | Run query test with specified number of links | No query test |
| `-l [numLinks]` | Run `$lookup` test with specified number of links | No lookup test |
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

#### Example 8: Comprehensive Test
```bash
java -jar target/insertTest-1.0-jar-with-dependencies.jar -q 20 -n 100 -s 1000,5000,10000 -b 200 25000
```
Full-featured test with:
- 25,000 documents
- Three payload sizes: 1000B, 5000B, 10000B
- 100 attributes per document
- Batch size of 200
- Query test with 20 linked documents

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
2. **Attribute Distribution**: Splitting payloads across multiple attributes can improve performance in MongoDB but may have minimal impact or slightly reduce performance in PostgreSQL
3. **JSONB vs JSON**: PostgreSQL's JSONB format offers better query performance but slightly slower insertion compared to plain JSON
4. **Indexing**: Multikey indexes significantly improve query performance but add overhead to insertions
5. **Batch Size**: Larger batch sizes generally improve throughput but consume more memory

## Customization

### Adding New Database Implementations

To add support for additional databases:

1. Create a new class implementing the `DatabaseOperations` interface
2. Implement all required methods: `initializeDatabase`, `dropAndCreateCollections`, `generateDocuments`, `insertDocuments`, `queryDocumentsById`, etc.
3. Update `Main.java` to recognize a new command-line flag and instantiate your implementation

### Modifying Test Data

Document generation occurs in the `generateDocuments` method of each implementation. Customize this method to:
- Add additional fields
- Change document structure
- Include specific data patterns
- Implement different linking strategies

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
- Configuration file support (instead of hardcoded connection strings)

## License

This project is licensed under the Apache License 2.0. See the `LICENSE` file for details.

## Authors

Rick Houlihan - Initial development

## Acknowledgments

This benchmark tool was created to provide objective performance comparisons between document-oriented and relational databases when handling semi-structured data.
