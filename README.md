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
sh test.sh -j -q -n 10 -s 10
```

