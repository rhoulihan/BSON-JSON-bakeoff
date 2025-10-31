package com.mongodb;

import java.util.List;
import java.util.Arrays;
import java.util.ArrayList;
import java.util.Properties;
import java.io.IOException;
import java.io.FileInputStream;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Paths;
import org.json.JSONObject;
import org.json.JSONArray;

public class Main {
    private static DatabaseOperations dbOperations;
    private static int numDocs = 10000;
    public static int numAttrs = 10;
    private static List<Integer> sizes = new ArrayList<>(Arrays.asList(new Integer[]{100,1000}));

    private static boolean runQueryTest = false;
    static boolean runIndexTest = false;
    static boolean runLookupTest = false;
    static boolean useInCondition = false;
    public static String jsonType = "json";
    public static Integer batchSize = 100;
    public static Integer numLinks = 10;
    public static boolean runSingleAttrTest = true;
    public static boolean useDirectTableInsert = false;
    public static Integer numRuns = 1;
    public static boolean useMultivalueIndex = false;
    public static boolean useRealisticData = false;

    public static void main(String[] args) {
        String dbType = "mongodb"; // default to MongoDB
        String flag = "";

        // Check for config file first
        for (int i = 0; i < args.length; i++) {
            if (args[i].equals("-c") && i + 1 < args.length) {
                String configFile = args[i + 1];
                System.out.println("Loading configuration from: " + configFile);
                dbType = loadConfigFile(configFile, dbType);
            }
        }

        // Then process command-line arguments (which can override config file)
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

                case "-oj":
                    dbType = "oraclejct";
                    break;

                case "-d":
                    System.out.println("Using direct table insertion (Oracle only)...");
                    useDirectTableInsert = true;
                    break;

                case "-mv":
                    System.out.println("Using multivalue index instead of search index (Oracle only)...");
                    useMultivalueIndex = true;
                    break;

                case "-rd":
                    System.out.println("Using realistic nested data structures for multi-attribute tests...");
                    useRealisticData = true;
                    break;

                case "-r":
                    flag = arg;
                    break;

                case "-c":
                    // Config file already processed, skip the filename
                    flag = arg;
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

                            case "-r":
                                numRuns = Integer.parseInt(arg);
                                System.out.println(String.format("Running each test %d times, keeping best result", numRuns));
                                break;

                            case "-c":
                                // Skip config filename (already processed)
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

        // Load database connection strings from config.properties
        Properties dbConfig = loadDatabaseConfig();
        String connectionString;
        if (dbType.equals("postgresql")) {
            connectionString = dbConfig.getProperty("postgresql.connection.string");
        } else if (dbType.equals("oracle23ai") || dbType.equals("oraclejct")) {
            connectionString = dbConfig.getProperty("oracle.connection.string");
        } else {
            connectionString = dbConfig.getProperty("mongodb.connection.string");
        }

        connectionString = System.getProperty("conn", connectionString);
        if (connectionString == null || connectionString.isEmpty()) {
            System.err.println("ERROR: Connection string not found in config.properties for database: " + dbType);
            System.err.println("Please create config.properties from config.properties.example");
            return;
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
        } else if (dbType.equals("oraclejct")) {
            dbOperations = new OracleJCT();
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

    /**
     * Generate realistic nested document data with varied types
     * Creates nested subdocuments up to maxDepth levels with random attributes
     *
     * @param targetSize Approximate target size in bytes for the generated data
     * @param rand Random number generator for reproducibility
     * @param currentDepth Current nesting level
     * @param maxDepth Maximum nesting depth (default 5)
     * @return JSONObject with nested realistic data
     */
    private static JSONObject generateRealisticData(int targetSize, java.util.Random rand, int currentDepth, int maxDepth) {
        JSONObject data = new JSONObject();
        int currentSize = 0;
        int attributeCount = 0;

        // Calculate attributes needed based on target size and current depth
        // Deeper levels get fewer attributes
        int maxAttrsAtLevel = Math.max(3, numAttrs / (currentDepth + 1));

        while (currentSize < targetSize * 0.9 && attributeCount < maxAttrsAtLevel) {
            String fieldName = "field_" + currentDepth + "_" + attributeCount;
            int typeChoice = rand.nextInt(100);

            if (typeChoice < 20 && currentDepth < maxDepth) {
                // 20% chance: Nested subdocument (up to maxDepth levels)
                int nestedSize = (targetSize - currentSize) / (maxAttrsAtLevel - attributeCount);
                JSONObject nested = generateRealisticData(nestedSize, rand, currentDepth + 1, maxDepth);
                data.put(fieldName, nested);
                currentSize += nested.toString().length();

            } else if (typeChoice < 35) {
                // 15% chance: Array with 3-4 items
                JSONArray array = new JSONArray();
                int arraySize = 3 + rand.nextInt(2); // 3-4 items
                for (int i = 0; i < arraySize; i++) {
                    int arrayItemType = rand.nextInt(4);
                    switch (arrayItemType) {
                        case 0:
                            array.put(rand.nextInt(10000));
                            break;
                        case 1:
                            array.put(rand.nextDouble() * 1000);
                            break;
                        case 2:
                            array.put(generateRandomString(rand, 10 + rand.nextInt(20)));
                            break;
                        case 3:
                            array.put(rand.nextBoolean());
                            break;
                    }
                }
                data.put(fieldName, array);
                currentSize += array.toString().length();

            } else if (typeChoice < 50) {
                // 15% chance: String (varying lengths)
                int strLen = 10 + rand.nextInt(50);
                String value = generateRandomString(rand, strLen);
                data.put(fieldName, value);
                currentSize += value.length() + fieldName.length() + 4;

            } else if (typeChoice < 65) {
                // 15% chance: Integer
                data.put(fieldName, rand.nextInt(1000000));
                currentSize += fieldName.length() + 10;

            } else if (typeChoice < 80) {
                // 15% chance: Double/Decimal
                data.put(fieldName, rand.nextDouble() * 10000);
                currentSize += fieldName.length() + 12;

            } else {
                // 20% chance: Binary data (up to 50 bytes)
                int binSize = 10 + rand.nextInt(41); // 10-50 bytes
                byte[] bytes = new byte[binSize];
                rand.nextBytes(bytes);
                // Convert to base64 string for JSON compatibility
                data.put(fieldName, java.util.Base64.getEncoder().encodeToString(bytes));
                currentSize += binSize * 4/3 + fieldName.length() + 4; // base64 expansion
            }

            attributeCount++;
        }

        return data;
    }

    /**
     * Generate random alphanumeric string of specified length
     */
    private static String generateRandomString(java.util.Random rand, int length) {
        String chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
        StringBuilder sb = new StringBuilder(length);
        for (int i = 0; i < length; i++) {
            sb.append(chars.charAt(rand.nextInt(chars.length())));
        }
        return sb.toString();
    }

    /**
     * Add realistic data to documents for multi-attribute tests
     * This replaces the flat binary payload approach with nested realistic structures
     */
    private static List<JSONObject> addRealisticDataToDocuments(List<JSONObject> documents, int targetSize) {
        List<JSONObject> result = new ArrayList<>();
        java.util.Random rand = new java.util.Random(42); // Fixed seed for reproducibility

        for (JSONObject doc : documents) {
            JSONObject newDoc = new JSONObject();
            // Copy existing fields (_id, targets)
            newDoc.put("_id", doc.get("_id"));
            if (doc.has("targets") && !useInCondition) {
                newDoc.put("targets", doc.get("targets"));
            }

            // Add realistic nested data structure
            JSONObject realisticData = generateRealisticData(targetSize, rand, 0, 5);
            newDoc.put("data", realisticData);

            result.add(newDoc);
        }

        return result;
    }

    private static void handleDataInsertions(Integer dataSize) {
        List<String> collectionNames = new ArrayList<>();

        if (runIndexTest)
            collectionNames.add("noindex");

        collectionNames.add("indexed");

        List<String> objectIds = generateObjectIds(numDocs);
        List<JSONObject> documents = generateDocuments(objectIds);

        // Track best times across all runs
        long bestSingleAttrTime = Long.MAX_VALUE;
        long bestMultiAttrTime = Long.MAX_VALUE;
        long bestQueryTime = Long.MAX_VALUE;
        int itemsFound = 0;

        if (numRuns > 1) {
            System.out.println(String.format("\n=== Running %d iterations for %dB payload (keeping best times) ===", numRuns, dataSize));
        }

        for (int run = 1; run <= numRuns; run++) {
            if (numRuns > 1) {
                System.out.println(String.format("\n--- Run %d/%d ---", run, numRuns));
            }

            dbOperations.dropAndCreateCollections(collectionNames);

            if (runSingleAttrTest) {
                for (String collectionName : collectionNames) {
                    long timeTaken = dbOperations.insertDocuments(collectionName, documents, dataSize, false);
                    if (numRuns == 1) {
                        System.out.println(String.format("Time taken to insert %d documents with %dB payload in 1 attribute into %s: %dms", numDocs, dataSize, collectionName, timeTaken));
                    }
                    if (timeTaken < bestSingleAttrTime && timeTaken > 0) {
                        bestSingleAttrTime = timeTaken;
                    }
                }

                dbOperations.dropAndCreateCollections(collectionNames);
            }

            // Multi-attribute test - use realistic data if flag is enabled
            List<JSONObject> docsToInsert = documents;
            if (useRealisticData) {
                docsToInsert = addRealisticDataToDocuments(documents, dataSize);
                if (run == 1 && numRuns > 1) {
                    System.out.println("  Using realistic nested data structures (up to 5 levels deep)");
                } else if (numRuns == 1) {
                    System.out.println("Using realistic nested data structures (up to 5 levels deep)");
                }
            }

            for (String collectionName : collectionNames) {
                // When using realistic data, set dataSize to 0 so insertDocuments doesn't add binary payload
                int insertDataSize = useRealisticData ? 0 : dataSize;
                long timeTaken = dbOperations.insertDocuments(collectionName, docsToInsert, insertDataSize, !useRealisticData);
                if (numRuns == 1) {
                    String dataType = useRealisticData ? "realistic nested data" : String.format("%dB payload in %d attributes", dataSize, numAttrs);
                    System.out.println(String.format("Time taken to insert %d documents with %s into %s: %dms", numDocs, dataType, collectionName, timeTaken));
                }
                if (timeTaken < bestMultiAttrTime && timeTaken > 0) {
                    bestMultiAttrTime = timeTaken;
                }
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
                if (numRuns == 1) {
                    System.out.println(String.format("Total time taken to query related documents for %d ID's with %d element link arrays %s: %dms", objectIds.size(),numLinks, type, totalQueryTime));
                    System.out.println(String.format("Total items found: %d", totalItemsFound));
                    System.out.println();
                }
                if (totalQueryTime < bestQueryTime) {
                    bestQueryTime = totalQueryTime;
                    itemsFound = totalItemsFound;
                }
            }
        }

        // Print best results if running multiple times
        if (numRuns > 1) {
            System.out.println(String.format("\n=== BEST RESULTS (%dB target size) ===", dataSize));
            if (runSingleAttrTest && bestSingleAttrTime != Long.MAX_VALUE) {
                System.out.println(String.format("Best time to insert %d documents with %dB payload in 1 attribute into indexed: %dms", numDocs, dataSize, bestSingleAttrTime));
            }
            if (bestMultiAttrTime != Long.MAX_VALUE) {
                if (useRealisticData) {
                    System.out.println(String.format("Best time to insert %d documents with realistic nested data (~%dB) into indexed: %dms", numDocs, dataSize, bestMultiAttrTime));
                } else {
                    System.out.println(String.format("Best time to insert %d documents with %dB payload in %d attributes into indexed: %dms", numDocs, dataSize, numAttrs, bestMultiAttrTime));
                }
            }
            if (runQueryTest && bestQueryTime != Long.MAX_VALUE) {
                String type = runLookupTest ? "using $lookup" : useInCondition ? "using $in condition" : "using multikey index";
                System.out.println(String.format("Best query time for %d ID's with %d element link arrays %s: %dms", objectIds.size(), numLinks, type, bestQueryTime));
                System.out.println(String.format("Total items found: %d", itemsFound));
            }
            System.out.println();
        }
    }

    /**
     * Load configuration from JSON file.
     * Command-line arguments can override config file settings.
     */
    private static String loadConfigFile(String configPath, String defaultDbType) {
        String dbType = defaultDbType;
        try {
            String content = new String(Files.readAllBytes(Paths.get(configPath)));
            JSONObject config = new JSONObject(content);

            // Database configuration
            if (config.has("database")) {
                dbType = config.getString("database");
            }

            // Test parameters
            if (config.has("numDocs")) {
                numDocs = config.getInt("numDocs");
            }
            if (config.has("numAttrs")) {
                numAttrs = config.getInt("numAttrs");
            }
            if (config.has("batchSize")) {
                batchSize = config.getInt("batchSize");
            }
            if (config.has("numLinks")) {
                numLinks = config.getInt("numLinks");
            }
            if (config.has("numRuns")) {
                numRuns = config.getInt("numRuns");
            }

            // Payload sizes
            if (config.has("sizes")) {
                sizes.clear();
                JSONArray sizesArray = config.getJSONArray("sizes");
                for (int i = 0; i < sizesArray.length(); i++) {
                    sizes.add(sizesArray.getInt(i));
                }
            }

            // Test flags
            if (config.has("runQueryTest")) {
                runQueryTest = config.getBoolean("runQueryTest");
            }
            if (config.has("runIndexTest")) {
                runIndexTest = config.getBoolean("runIndexTest");
            }
            if (config.has("runLookupTest")) {
                runLookupTest = config.getBoolean("runLookupTest");
            }
            if (config.has("useInCondition")) {
                useInCondition = config.getBoolean("useInCondition");
            }
            if (config.has("useDirectTableInsert")) {
                useDirectTableInsert = config.getBoolean("useDirectTableInsert");
            }
            if (config.has("runSingleAttrTest")) {
                runSingleAttrTest = config.getBoolean("runSingleAttrTest");
            }

            // PostgreSQL-specific
            if (config.has("jsonType")) {
                jsonType = config.getString("jsonType");
            }

            System.out.println("Configuration loaded successfully");
            return dbType;

        } catch (IOException e) {
            System.err.println("Error reading config file: " + e.getMessage());
            return defaultDbType;
        } catch (Exception e) {
            System.err.println("Error parsing config file: " + e.getMessage());
            return defaultDbType;
        }
    }

    /**
     * Load database connection configuration from config.properties file.
     * Returns a Properties object with connection strings for MongoDB, PostgreSQL, and Oracle.
     */
    private static Properties loadDatabaseConfig() {
        Properties properties = new Properties();
        String configPath = "config.properties";

        try (InputStream input = new FileInputStream(configPath)) {
            properties.load(input);
        } catch (IOException e) {
            System.err.println("ERROR: Could not load config.properties file.");
            System.err.println("Please create config.properties from config.properties.example");
            System.err.println("Error: " + e.getMessage());
            System.exit(1);
        }

        return properties;
    }
}

