package com.mongodb;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Random;

import org.json.JSONArray;
import org.json.JSONObject;

import oracle.sql.json.OracleJsonFactory;
import oracle.sql.json.OracleJsonObject;

/**
 * Oracle 23AI implementation using JSON Duality Views.
 *
 * JSON Duality Views in Oracle 23AI provide a unified way to work with data
 * both as relational tables and as JSON documents. This implementation leverages
 * this feature to provide document-style access while maintaining ACID properties
 * and relational integrity.
 */
public class Oracle23AIOperations implements DatabaseOperations {
    private Connection connection;
    private Random rand = new Random();
    private PreparedStatement stmt;
    private OracleJsonFactory jsonFactory;

    @Override
    public void initializeDatabase(String connectionString) {
        try {
            // Load Oracle JDBC driver
            Class.forName("oracle.jdbc.driver.OracleDriver");
            connection = DriverManager.getConnection(connectionString);

            // Initialize Oracle JSON factory for JSON operations
            jsonFactory = new OracleJsonFactory();

            // Get database version
            Statement versionStmt = connection.createStatement();
            ResultSet rs = versionStmt.executeQuery("SELECT banner FROM v$version WHERE banner LIKE 'Oracle%'");
            if (rs.next()) {
                System.out.println(rs.getString(1));
            }
            rs.close();
            versionStmt.close();

            // Disable auto-commit for better batch performance
            connection.setAutoCommit(false);

        } catch (ClassNotFoundException e) {
            System.err.println("Oracle JDBC Driver not found. Add ojdbc11.jar to classpath.");
            e.printStackTrace();
        } catch (SQLException e) {
            System.err.println("Database connection failed.");
            e.printStackTrace();
        }
    }

    @Override
    public void dropAndCreateCollections(List<String> collectionNames) {
        try {
            Statement stmt = connection.createStatement();

            for (String collectionName : collectionNames) {
                // Drop existing duality view and tables
                try {
                    stmt.execute("DROP VIEW " + collectionName + "_dv");
                } catch (SQLException e) {
                    // Ignore if view doesn't exist
                }

                try {
                    stmt.execute("DROP TABLE " + collectionName + "_docs CASCADE CONSTRAINTS");
                } catch (SQLException e) {
                    // Ignore if table doesn't exist
                }

                try {
                    stmt.execute("DROP TABLE " + collectionName + "_index_array CASCADE CONSTRAINTS");
                } catch (SQLException e) {
                    // Ignore if table doesn't exist
                }

                // Create base document table
                // Using JSON type for payload and proper normalization for index array
                String createDocsTable = String.format(
                    "CREATE TABLE %s_docs (" +
                    "  doc_id VARCHAR2(100) PRIMARY KEY, " +
                    "  payload JSON, " +
                    "  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP" +
                    ") TABLESPACE USERS",
                    collectionName
                );
                stmt.execute(createDocsTable);

                // Create index array table (normalized for better performance)
                String createIndexArrayTable = String.format(
                    "CREATE TABLE %s_index_array (" +
                    "  doc_id VARCHAR2(100), " +
                    "  array_value VARCHAR2(100), " +
                    "  CONSTRAINT pk_%s_array PRIMARY KEY (doc_id, array_value), " +
                    "  CONSTRAINT fk_%s_doc FOREIGN KEY (doc_id) REFERENCES %s_docs(doc_id) ON DELETE CASCADE" +
                    ") TABLESPACE USERS",
                    collectionName, collectionName, collectionName, collectionName
                );
                stmt.execute(createIndexArrayTable);

                // Create index on array values for query performance
                if (collectionName.equals("indexed")) {
                    String createArrayIndex = String.format(
                        "CREATE INDEX idx_%s_array_value ON %s_index_array(array_value)",
                        collectionName, collectionName
                    );
                    stmt.execute(createArrayIndex);
                }

                // Create JSON Duality View
                // This view presents the relational data as JSON documents
                String createDualityView = String.format(
                    "CREATE OR REPLACE JSON RELATIONAL DUALITY VIEW %s_dv AS " +
                    "%s_docs @INSERT @UPDATE @DELETE {" +
                    "  _id: doc_id, " +
                    "  data: payload, " +
                    "  indexArray: %s_index_array @INSERT @UPDATE @DELETE [ {value: array_value} ]" +
                    "}",
                    collectionName, collectionName, collectionName
                );
                stmt.execute(createDualityView);
            }

            connection.commit();
            stmt.close();

        } catch (SQLException e) {
            System.err.println("Error creating tables and duality views:");
            e.printStackTrace();
            try {
                connection.rollback();
            } catch (SQLException ex) {
                ex.printStackTrace();
            }
        }
    }

    @Override
    public long insertDocuments(String collectionName, List<JSONObject> documents, int dataSize, boolean splitPayload) {
        // Using INSERT into duality view - Oracle automatically handles the relational mapping
        String insertSql = "INSERT INTO " + collectionName + "_dv VALUES (?)";

        try {
            stmt = connection.prepareStatement(insertSql);

            byte[] bytes = new byte[dataSize];
            rand.nextBytes(bytes);

            // Prepare payload structure
            JSONObject payloadJson = new JSONObject();
            if (splitPayload) {
                int length = dataSize / Main.numAttrs;
                for (int i = 0; i < Main.numAttrs; i++) {
                    int start = i * length;
                    // Convert byte array to base64 for JSON storage
                    payloadJson.put("data" + i,
                        java.util.Base64.getEncoder().encodeToString(
                            Arrays.copyOfRange(bytes, start, start + length)
                        )
                    );
                }
            } else {
                payloadJson.put("data",
                    java.util.Base64.getEncoder().encodeToString(bytes)
                );
            }

            long startTime = System.currentTimeMillis();
            int batchCount = 0;
            int docCount = 0;

            for (JSONObject doc : documents) {
                docCount++;
                // Build complete JSON document for duality view
                JSONObject dualityDoc = new JSONObject();
                dualityDoc.put("_id", doc.getString("_id"));
                dualityDoc.put("data", payloadJson);

                // Add index array - transform to array of objects
                JSONArray indexArray = doc.getJSONArray("targets");
                JSONArray transformedArray = new JSONArray();
                for (int i = 0; i < indexArray.length(); i++) {
                    JSONObject arrayItem = new JSONObject();
                    arrayItem.put("value", indexArray.getString(i));
                    transformedArray.put(arrayItem);
                }
                dualityDoc.put("indexArray", transformedArray);

                // Debug: Print first document to verify structure
                if (docCount == 1) {
                    System.out.println("DEBUG: First document JSON structure:");
                    System.out.println(dualityDoc.toString(2));
                }

                // Insert through duality view
                stmt.setString(1, dualityDoc.toString());

                // DEBUG: Try inserting one at a time instead of batching
                if (docCount <= 5 || (docCount % 100) == 0) {
                    System.out.println("DEBUG: Inserting document " + docCount + " individually");
                    try {
                        stmt.executeUpdate();
                        connection.commit();
                        System.out.println("  SUCCESS");
                    } catch (SQLException e) {
                        System.err.println("  FAILED: " + e.getMessage() + " (ErrorCode: " + e.getErrorCode() + ")");
                        connection.rollback();
                    }
                } else {
                    stmt.addBatch();
                    batchCount++;
                }

                // Execute batch when reaching batch size
                if (batchCount >= Main.batchSize) {
                    try {
                        int[] results = stmt.executeBatch();
                        connection.commit();
                        int successCount = 0;
                        for (int result : results) {
                            if (result > 0 || result == Statement.SUCCESS_NO_INFO) {
                                successCount++;
                            }
                        }
                        System.out.println("Batch " + (docCount / Main.batchSize) + ": Successfully inserted " + successCount + " out of " + results.length + " documents");
                    } catch (SQLException e) {
                        System.err.println("Batch insert error at document " + docCount + ": " + e.getMessage());
                        System.err.println("SQL State: " + e.getSQLState());
                        System.err.println("Error Code: " + e.getErrorCode());
                        if (e.getNextException() != null) {
                            System.err.println("Next exception: " + e.getNextException().getMessage());
                        }
                        connection.rollback();
                        // Try to continue with next batch
                    }
                    batchCount = 0;
                }
            }

            // Execute remaining batch
            if (batchCount > 0) {
                try {
                    int[] results = stmt.executeBatch();
                    connection.commit();
                    int successCount = 0;
                    for (int result : results) {
                        if (result > 0 || result == Statement.SUCCESS_NO_INFO) {
                            successCount++;
                        }
                    }
                    System.out.println("Final batch: Successfully inserted " + successCount + " out of " + results.length + " documents");
                } catch (SQLException e) {
                    System.err.println("Final batch insert error: " + e.getMessage());
                    System.err.println("SQL State: " + e.getSQLState());
                    System.err.println("Error Code: " + e.getErrorCode());
                    if (e.getNextException() != null) {
                        System.err.println("Next exception: " + e.getNextException().getMessage());
                    }
                    connection.rollback();
                }
            }

            System.out.println("Total documents processed: " + docCount);

            stmt.close();
            return System.currentTimeMillis() - startTime;

        } catch (SQLException e) {
            System.err.println("Error inserting documents:");
            e.printStackTrace();
            try {
                connection.rollback();
            } catch (SQLException ex) {
                ex.printStackTrace();
            }
            return -1;
        }
    }

    @Override
    public int queryDocumentsById(String collectionName, String id) {
        // Query using the normalized index array table for optimal performance
        String sql = String.format(
            "SELECT d.payload FROM %s_docs d " +
            "WHERE d.doc_id IN (" +
            "  SELECT doc_id FROM %s_index_array WHERE array_value = ?" +
            ")",
            collectionName, collectionName
        );

        try {
            stmt = connection.prepareStatement(sql);
            stmt.setString(1, id);
            ResultSet rs = stmt.executeQuery();

            int count = 0;
            while (rs.next()) {
                // Fetch the JSON data (simulating real-world usage)
                rs.getString(1);
                count++;
            }

            rs.close();
            stmt.close();
            return count;

        } catch (SQLException e) {
            System.err.println("Error querying documents:");
            e.printStackTrace();
            return 0;
        }
    }

    @Override
    public int queryDocumentsByIdWithInCondition(String collectionName, JSONObject document) {
        // Query documents using IN condition on index array
        JSONArray targets = document.getJSONArray("targets");

        if (targets.length() == 0) {
            return 0;
        }

        // Build IN clause
        StringBuilder sql = new StringBuilder();
        sql.append("SELECT DISTINCT d.payload FROM ")
           .append(collectionName).append("_docs d ")
           .append("WHERE d.doc_id IN (")
           .append("  SELECT doc_id FROM ").append(collectionName).append("_index_array ")
           .append("  WHERE array_value IN (");

        for (int i = 0; i < targets.length(); i++) {
            if (i > 0) sql.append(", ");
            sql.append("?");
        }
        sql.append("))");

        try {
            stmt = connection.prepareStatement(sql.toString());

            // Set parameters
            for (int i = 0; i < targets.length(); i++) {
                stmt.setString(i + 1, targets.getString(i));
            }

            ResultSet rs = stmt.executeQuery();

            int count = 0;
            while (rs.next()) {
                rs.getString(1);
                count++;
            }

            rs.close();
            stmt.close();
            return count;

        } catch (SQLException e) {
            System.err.println("Error querying documents with IN condition:");
            e.printStackTrace();
            return 0;
        }
    }

    @Override
    public int queryDocumentsByIdUsingLookup(String collectionName, String id) {
        // Oracle doesn't have MongoDB's $lookup, but we can simulate with JOIN
        // This would require a links table similar to MongoDB implementation
        // For now, implementing a basic version

        String sql = String.format(
            "SELECT d.payload FROM %s_docs d " +
            "JOIN %s_index_array ia ON d.doc_id = ia.doc_id " +
            "WHERE ia.array_value = ?",
            collectionName, collectionName
        );

        try {
            stmt = connection.prepareStatement(sql);
            stmt.setString(1, id);
            ResultSet rs = stmt.executeQuery();

            int count = 0;
            while (rs.next()) {
                rs.getString(1);
                count++;
            }

            rs.close();
            stmt.close();
            return count;

        } catch (SQLException e) {
            System.err.println("Error querying documents using lookup:");
            e.printStackTrace();
            return 0;
        }
    }

    @Override
    public void close() {
        try {
            if (stmt != null && !stmt.isClosed()) {
                stmt.close();
            }
            if (connection != null && !connection.isClosed()) {
                connection.commit();
                connection.close();
            }
        } catch (SQLException e) {
            System.err.println("Error closing connection:");
            e.printStackTrace();
        }
    }
}
