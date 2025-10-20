---
description: Benchmark MongoDB vs Oracle JSON Collection Tables
---

Run comprehensive benchmarks comparing MongoDB and Oracle JSON Collection Tables.

**Test Configuration:**
- Documents: 10,000
- Payload sizes: 100B and 1000B
- Attributes: 1 and 10 (single attribute vs multi-attribute split)
- Runs: 3 (keeps best result)
- Databases: MongoDB and Oracle JSON Collection Tables

**Steps:**
1. Ensure the project is built (mvn clean package)
2. Run MongoDB benchmark with specified parameters
3. Run Oracle JSON Collection Tables benchmark with same parameters
4. Compare results

Please execute the following:

First, build the project:
```bash
cd /mnt/c/Users/rickh/OneDrive/Documents/GitHub/BSON-JSON-bakeoff
mvn clean package
```

Then run MongoDB benchmark:
```bash
java -jar target/insertTest-1.0-jar-with-dependencies.jar -s 100,1000 -n 10 -r 3 10000
```

Then run Oracle JSON Collection Tables benchmark:
```bash
java -jar target/insertTest-1.0-jar-with-dependencies.jar -oj -s 100,1000 -n 10 -r 3 10000
```

**Parameters:**
- `-s 100,1000`: Payload sizes to test
- `-n 10`: Number of attributes (tests both 1 and 10 attributes)
- `-r 3`: Number of runs (keeps best result)
- `10000`: Number of documents to insert
