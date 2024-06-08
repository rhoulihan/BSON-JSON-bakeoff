package com.mongodb;

import java.util.List;
import java.util.Arrays;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.Map;
import org.json.JSONObject;

public class Main {
    private static DatabaseOperations dbOperations;
    private static int numDocs = 10000;
    public static int numAttrs = 10;
    private static List<Integer> sizes = new ArrayList<>(Arrays.asList(new Integer[]{100,1000}));

    private static Map<Integer, List<Long>> results = new HashMap<Integer, List<Long>>();
    private static boolean runQueryTest = false;
    private static boolean runIndexTest = false;
    public static String jsonType = "json";
    public static Integer batchSize = 100;

    public static void main(String[] args) {
        String dbType = "mongodb"; // default to MongoDB
        String flag = "";
        for (String arg : args) {
            switch (arg) {
                case "-j":
                    jsonType = "jsonb";
                    break;
                    
                case "-i":
                    System.out.println("Including index test...");
                    runIndexTest = true;
                    break;
                    
                case "-p":
                    dbType = "postgresql";
                    break;
                    
                case "-q":
                    System.out.println("Including query test...");
                    runQueryTest = true;
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

        String mongoConnectionString = "mongodb://localhost:27017";
        String postgresConnectionString = "jdbc:postgresql://localhost:5432/test?user=postgres&password=G0_4w4y!";

        initializeDatabase(dbType, dbType.equals("postgresql") ? postgresConnectionString : mongoConnectionString);

        for (Integer size : sizes){
            handleDataInsertions(size);
        }
        
        System.out.println();
        System.out.println(results.toString());
        System.out.println("Done.");
        dbOperations.close(); // Ensure resources are properly closed
    }

    private static void initializeDatabase(String dbType, String connectionString) {
        if (dbType.equals("postgresql")) {
            dbOperations = new PostgreSQLOperations();
        } else {
            dbOperations = new MongoDBOperations();
        }

        dbOperations.initializeDatabase(connectionString);
    }

    private static void handleDataInsertions(Integer dataSize) {
        List<String> collectionNames = new ArrayList<>();
        
        if (runIndexTest)
            collectionNames.add("noindex");
        
        collectionNames.add("indexed");

        dbOperations.dropAndCreateCollections(collectionNames);

        List<Integer> objectIds = dbOperations.generateObjectIds(numDocs);
        List<JSONObject> documents = dbOperations.generateDocuments(objectIds);

        List<Long> insertionTimes = new ArrayList<>();
        for (String collectionName : collectionNames) {
            long timeTaken = dbOperations.insertDocuments(collectionName, documents, dataSize, false);
            System.out.println(String.format("Time taken to insert %d documents with %dB payload in 1 attribute into %s: %dms", numDocs, dataSize, collectionName, timeTaken));
            insertionTimes.add(timeTaken);
        }

        dbOperations.dropAndCreateCollections(collectionNames);

        for (String collectionName : collectionNames) {
            long timeTaken = dbOperations.insertDocuments(collectionName, documents, dataSize, true);
            System.out.println(String.format("Time taken to insert %d documents with %dB payload in %d attributes into %s: %dms", numDocs, dataSize, numAttrs, collectionName, timeTaken));
            insertionTimes.add(timeTaken);
        }

        results.put(dataSize, insertionTimes);

        // Query documents by ID for "indexed" collection
        if (runQueryTest) {
            long startTime = System.currentTimeMillis();
            int totalItemsFound = 0;
            for (Integer id : objectIds) {
                totalItemsFound += dbOperations.queryDocumentsById("indexed", id);
            }
            long totalQueryTime = System.currentTimeMillis() - startTime;
            System.out.println(String.format("Total time taken to query %d ID's from indexedArray: %dms", objectIds.size(), totalQueryTime));
            System.out.println(String.format("Total items found: %d", totalItemsFound));
            System.out.println();
        }
    }
}

