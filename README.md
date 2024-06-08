# BSON-JSON-bakeoff
A simple benchmark to insert documents of various size and complexity into either MongoDB or PostgreSQL and report time taken to complete.

Start a MongoDB or PostgreSQL server on localhost and then build and execute as follows:

mvn clean package

usage:

java -jar insertTest-1.0-jar-with-dependencies [-p -j -i -q -s [payloadSizeArray] -n [numAttributes] -b [batchSize]] [numItems]

-p      Use PostgreSQL (Default is MongoDB)
-j      Use JSONB (JSON is default when -p is set)
-i      Run against both indexed and unindexed tables (Default is use indexed tables only)
-q      Run query test
-s      Specify a comma delimited array of payload sizes in bytes to test with (Default is [100,1000])
-n      Specify the number of attributes to split each payload size across (Default is 10)
-b      Specify the muber of BSON/JSON/JSONB Documents to batch in each insert (Default is 100)

if [numItems] is not set, the default value of 10 thousand documents will be generated.
