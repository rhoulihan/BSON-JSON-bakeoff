# BSON-JSON-bakeoff
A simple benchmark to insert documents of various size and complexity into either MongoDB or PostgreSQL and report time taken to complete.

Start a MongoDB or PostgreSQL server on localhost, edit connection strings in Main.java and then build/execute as follows:

mvn clean package

usage:

java -jar insertTest-1.0-jar-with-dependencies [-p -j -i -q -s [payloadSizeArray] -n [numAttributes] -b [batchSize]] [numItems]

-p      Use PostgreSQL (Default is MongoDB)<br>
-j      Use JSONB (JSON is default when -p is set)<br>
-i      Run against both indexed and unindexed tables (Default is use indexed tables only)<br>
-q      Run query test<br>
-s      Specify a comma delimited array of payload sizes in bytes to test with (Default is [100,1000])<br>
-n      Specify the number of attributes to split each payload size across (Default is 10)<br>
-b      Specify the muber of BSON/JSON/JSONB Documents to batch in each insert (Default is 100)<br>

if [numItems] is not set, the default value of 10 thousand documents will be generated.

# Test

The `test.sh` script tests the program on MongoDB, PostgreSQL and YugabyteDB (starting them in docker container)
Example:
```
sh test.sh -q -n 200 -s 4000

Using mongodb database.
Jun 16, 2024 7:43:05 PM com.mongodb.diagnostics.logging.Loggers shouldUseSLF4J
WARNING: SLF4J not found on the classpath.  Logging is disabled for the 'org.mongodb.driver' component
Time taken to insert 10000 documents with 4000B payload in 1 attribute into indexed: 2052ms
Time taken to insert 10000 documents with 4000B payload in 200 attributes into indexed: 1351ms
Total time taken to query 10000 ID's from indexedArray: 10169ms
Total items found: 99941

PostgreSQL 16.3 (Debian 16.3-1.pgdg120+1) on x86_64-pc-linux-gnu, compiled by gcc (Debian 12.2.0-14) 12.2.0, 64-bit
Time taken to insert 10000 documents with 4000B payload in 1 attribute into indexed: 16786ms
Time taken to insert 10000 documents with 4000B payload in 200 attributes into indexed: 17861ms
Total time taken to query 10000 ID's from indexedArray: 29485ms
Total items found: 99939

PostgreSQL 11.2-YB-2.21.1.0-b0 on x86_64-pc-linux-gnu, compiled by clang version 17.0.6 (https://github.com/yugabyte/llvm-project.git 9b881774e40024e901fc6f3d313607b071c08631), 64-bit
Time taken to insert 10000 documents with 4000B payload in 1 attribute into indexed: 14075ms
Time taken to insert 10000 documents with 4000B payload in 200 attributes into indexed: 14820ms
Total time taken to query 10000 ID's from indexedArray: 15900ms
Total items found: 99959

CockroachDB CCL v24.1.0 (x86_64-pc-linux-gnu, built 2024/05/15 21:28:29, go1.22.2 X:nocoverageredesign)
Time taken to insert 10000 documents with 4000B payload in 1 attribute into indexed: 37648ms
Time taken to insert 10000 documents with 4000B payload in 200 attributes into indexed: 42455ms
Total time taken to query 10000 ID's from indexedArray: 155116ms
Total items found: 99963
```

