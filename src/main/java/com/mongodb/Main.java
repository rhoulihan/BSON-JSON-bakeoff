package com.mongodb;

import java.util.List;
import java.util.Arrays;
import java.util.ArrayList;
import org.json.JSONObject;

public class Main {
    private static DatabaseOperations dbOperations;
    private static int numDocs = 10000;
    public static int numAttrs = 10;
    private static List<Integer> sizes = new ArrayList<>(Arrays.asList(new Integer[]{100,1000}));

    private static boolean runQueryTest = false;
    private static boolean runIndexTest = false;
    static boolean runLookupTest = false;
    static boolean useInCondition = false;
    public static String jsonType = "json";
    public static Integer batchSize = 100;
    public static Integer numLinks = 10;
    public static boolean runSingleAttrTest = true;

    public static void main(String[] args) {
        String dbType = "mongodb"; // default to MongoDB
        String flag = "";
        for (String arg : args) {
            switch (arg) {
                case "-j":
                    jsonType = "jsonb";
                    break;

                case "-l":
                    System.out.println("Including $lookup test...");
                    runLookupTest = true;
                    runSingleAttrTest = false;
                    flag = arg;
                    break;

                case "-i":
                    if (Arrays.asList(args).contains("-l")) {
                        System.out.println("Including $in condition for query test...");
                        useInCondition = true;
                    } else {
                        System.out.println("Including index test...");
                        runIndexTest = true;
                    }
                    break;

                case "-p":
                    dbType = "postgresql";
                    break;

                case "-o":
                    dbType = "oracle23ai";
                    break;
                    
                case "-q":
                    System.out.println("Including query test...");
                    flag = arg;
                    break;
                    
                case "-s":
                case "-n":
                case "-b":
                    flag = arg;
                    break;
                    
                    
                default:
                    try {
                        switch(flag) {
                            case "-s":
                                sizes.clear();
                                for (String size : arg.split(",")) {
                                    sizes.add(Integer.parseInt(size));
                                }
                                break;
                                
                            case "-n":
                                numAttrs = Integer.parseInt(arg);
                                break;
                                
                            case "-b":
                                batchSize = Integer.parseInt(arg);
                                break;

                            case "-l":
                            case "-q":
                                runQueryTest = true;
                                numLinks = Integer.parseInt(arg);
                                break;
                                
                            default:
                                numDocs = Integer.parseInt(arg);
                                break;
                        }
                    }
                    catch (Exception e) {
                        System.err.println("ERROR: Unknown argument.");
                        return;
                    } finally {
                        flag = "";
                    }
                    break;
            }
        }
        
        System.out.println(String.format("Using %s database.", dbType));
        if (dbType.equals("postgresql"))
            System.out.println(String.format("Using %s attribute type for data.", jsonType));

        String mongoConnectionString = "mongodb://172.19.16.1:27017";
        String postgresConnectionString = "jdbc:postgresql://localhost:5432/test?user=postgres&password=G0_4w4y!";
        String oracleConnectionString = "jdbc:oracle:thin:system/G0_4w4y!@172.19.16.1:1521/FREEPDB1";

        String connectionString;
        if (dbType.equals("postgresql")) {
            connectionString = postgresConnectionString;
        } else if (dbType.equals("oracle23ai")) {
            connectionString = oracleConnectionString;
        } else {
            connectionString = mongoConnectionString;
        }

        initializeDatabase(dbType, connectionString);

        for (Integer size : sizes){

            if (Main.runLookupTest) {
                if (Main.useInCondition) {
                    Main.runLookupTest = false;
                    handleDataInsertions(size);
                    Main.useInCondition = false;
                } else {
                    handleDataInsertions(size);
                    Main.runLookupTest = false;
                }
            }
            handleDataInsertions(size);
        }
        
        System.out.println();
        System.out.println("Done.");
        dbOperations.close(); // Ensure resources are properly closed
    }

    private static void initializeDatabase(String dbType, String connectionString) {
        if (dbType.equals("postgresql")) {
            dbOperations = new PostgreSQLOperations();
        } else if (dbType.equals("oracle23ai")) {
            dbOperations = new Oracle23AIOperations();
        } else {
            dbOperations = new MongoDBOperations();
        }

        dbOperations.initializeDatabase(connectionString);
    }
    
    private static List<String> generateObjectIds(int count) {
        List<String> ids = new ArrayList<>();
        for (int i = 0; i < count; i++) {
            ids.add(Integer.toString(i));
        }
        return ids;
    }

    private static List<JSONObject> generateDocuments(List<String> objectIds) {
        List<JSONObject> documents = new ArrayList<>();
        java.util.Random rand = new java.util.Random(42); // Fixed seed for reproducibility

        for (String id : objectIds) {
            JSONObject json = new JSONObject();
            json.put("_id", id);

            // Generate unique values for array
            java.util.Set<String> uniqueTargets = new java.util.HashSet<>();
            while (uniqueTargets.size() < numLinks && uniqueTargets.size() < objectIds.size()) {
                uniqueTargets.add(objectIds.get(rand.nextInt(objectIds.size())));
            }

            // Convert to list and add to document
            List<String> targets = new ArrayList<>(uniqueTargets);
            json.put("targets", targets);
            documents.add(json);
        }

        return documents;
    }

    private static void handleDataInsertions(Integer dataSize) {
        List<String> collectionNames = new ArrayList<>();
        
        if (runIndexTest) 
            collectionNames.add("noindex");
        
        collectionNames.add("indexed");

        dbOperations.dropAndCreateCollections(collectionNames);

        List<String> objectIds = generateObjectIds(numDocs);
        List<JSONObject> documents = generateDocuments(objectIds);

        if (runSingleAttrTest) {
            for (String collectionName : collectionNames) {
                long timeTaken = dbOperations.insertDocuments(collectionName, documents, dataSize, false);
                System.out.println(String.format("Time taken to insert %d documents with %dB payload in 1 attribute into %s: %dms", numDocs, dataSize, collectionName, timeTaken));
            }

            dbOperations.dropAndCreateCollections(collectionNames);
        }

        for (String collectionName : collectionNames) {
            long timeTaken = dbOperations.insertDocuments(collectionName, documents, dataSize, true);
            System.out.println(String.format("Time taken to insert %d documents with %dB payload in %d attributes into %s: %dms", numDocs, dataSize, numAttrs, collectionName, timeTaken));
        }

        // Query documents by ID for "indexed" collection
        if (runQueryTest) {
            int totalItemsFound = 0;
            String type = runLookupTest ? "using $lookup" : useInCondition ? "using $in condition" : "using multikey index";
            long startTime = System.currentTimeMillis();

            if (!runLookupTest) {
                if (useInCondition) {
                    for (JSONObject document : documents) {
                        totalItemsFound += dbOperations.queryDocumentsByIdWithInCondition("indexed", document);
                    }
                } else {
                    for (String id : objectIds) {
                        totalItemsFound += dbOperations.queryDocumentsById("indexed", id);
                    }
                }
            } else {
                for (String id : objectIds)
                    totalItemsFound += dbOperations.queryDocumentsByIdUsingLookup("indexed", id);
            }
            
            long totalQueryTime = System.currentTimeMillis() - startTime;
            System.out.println(String.format("Total time taken to query related documents for %d ID's with %d element link arrays %s: %dms", objectIds.size(),numLinks, type, totalQueryTime));
            System.out.println(String.format("Total items found: %d", totalItemsFound));
            System.out.println();
        }
    }
}

