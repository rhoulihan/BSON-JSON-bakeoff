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
import oracle.jdbc.OracleType;

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

    /**
     * Convert a JSON string to Oracle's native OSON format.
     * This avoids the overhead of parsing JSON text on the database side.
     */
    private OracleJsonObject createOsonObject(String jsonString) {
        try {
            // Parse JSON string into Oracle's native binary JSON format (OSON)
            java.io.StringReader reader = new java.io.StringReader(jsonString);
            return jsonFactory.createJsonTextValue(reader).asJsonObject();
        } catch (Exception e) {
            System.err.println("Error creating OSON object: " + e.getMessage());
            e.printStackTrace();
            return null;
        }
    }

    @Override
    public void dropAndCreateCollections(List<String> collectionNames) {
        try {
            Statement stmt = connection.createStatement();

            for (String collectionName : collectionNames) {
                // Drop existing duality view first (must drop before tables)
                try {
                    stmt.execute("DROP VIEW " + collectionName + "_dv");
                    System.out.println("Dropped view " + collectionName + "_dv");
                } catch (SQLException e) {
                    // Ignore if view doesn't exist
                    System.out.println("View " + collectionName + "_dv does not exist");
                }

                // Drop tables with CASCADE to remove any dependencies
                try {
                    stmt.execute("DROP TABLE " + collectionName + "_index_array CASCADE CONSTRAINTS");
                    System.out.println("Dropped table " + collectionName + "_index_array");
                } catch (SQLException e) {
                    // Ignore if table doesn't exist
                    System.out.println("Table " + collectionName + "_index_array does not exist");
                }

                try {
                    stmt.execute("DROP TABLE " + collectionName + "_docs CASCADE CONSTRAINTS");
                    System.out.println("Dropped table " + collectionName + "_docs");
                } catch (SQLException e) {
                    // Ignore if table doesn't exist
                    System.out.println("Table " + collectionName + "_docs does not exist");
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

                // Create JSON Duality View with correct array syntax
                // Arrays require nested SELECT JSON with WHERE clause for foreign key join
                String createDualityView = String.format(
                    "CREATE OR REPLACE JSON RELATIONAL DUALITY VIEW %s_dv AS " +
                    "SELECT JSON {" +
                    "  '_id': d.doc_id, " +
                    "  'data': d.payload, " +
                    "  'indexArray': [" +
                    "    (" +
                    "      SELECT JSON {" +
                    "        'value': a.array_value" +
                    "      }" +
                    "      FROM %s_index_array a WITH INSERT UPDATE DELETE " +
                    "      WHERE a.doc_id = d.doc_id" +
                    "    )" +
                    "  ]" +
                    "} " +
                    "FROM %s_docs d WITH INSERT UPDATE DELETE",
                    collectionName, collectionName, collectionName
                );
                stmt.execute(createDualityView);
                System.out.println("Created duality view " + collectionName + "_dv with correct array syntax");
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
        if (Main.useDirectTableInsert) {
            return insertDocumentsDirectly(collectionName, documents, dataSize, splitPayload);
        }

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
            } else if (dataSize > 0) {
                payloadJson.put("data",
                    java.util.Base64.getEncoder().encodeToString(bytes)
                );
            }

            long startTime = System.currentTimeMillis();
            int batchCount = 0;

            for (JSONObject doc : documents) {
                // Build complete JSON document for duality view
                JSONObject dualityDoc = new JSONObject();
                dualityDoc.put("_id", doc.getString("_id"));
                // Only add binary data field if dataSize > 0 (not using realistic data mode)
                if (dataSize > 0) {
                    dualityDoc.put("data", payloadJson);
                }

                // Add index array - transform to array of objects
                JSONArray indexArray = doc.getJSONArray("targets");
                JSONArray transformedArray = new JSONArray();
                for (int i = 0; i < indexArray.length(); i++) {
                    JSONObject arrayItem = new JSONObject();
                    arrayItem.put("value", indexArray.getString(i));
                    transformedArray.put(arrayItem);
                }
                dualityDoc.put("indexArray", transformedArray);

                // Insert through duality view using native OSON format
                // This avoids JSON text parsing overhead on the database side
                OracleJsonObject osonDoc = createOsonObject(dualityDoc.toString());
                stmt.setObject(1, osonDoc, OracleType.JSON);
                stmt.addBatch();
                batchCount++;

                // Execute batch when reaching batch size
                if (batchCount >= Main.batchSize) {
                    stmt.executeBatch();
                    connection.commit();
                    batchCount = 0;
                }
            }

            // Execute remaining batch
            if (batchCount > 0) {
                stmt.executeBatch();
                connection.commit();
            }

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
    public long getAverageDocumentSize(String collectionName) {
        // Not implemented for Oracle23AI
        return -1;
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

    /**
     * Insert documents directly into base tables, bypassing the Duality View.
     * This avoids the array value duplication bug in Oracle 23AI Duality Views.
     */
    private long insertDocumentsDirectly(String collectionName, List<JSONObject> documents, int dataSize, boolean splitPayload) {
        try {
            // Prepare SQL statements
            String insertDocSql = "INSERT INTO " + collectionName + "_docs (doc_id, payload) VALUES (?, ?)";
            String insertArraySql = "INSERT INTO " + collectionName + "_index_array (doc_id, array_value) VALUES (?, ?)";

            PreparedStatement docStmt = connection.prepareStatement(insertDocSql);
            PreparedStatement arrayStmt = connection.prepareStatement(insertArraySql);

            byte[] bytes = new byte[dataSize];
            rand.nextBytes(bytes);

            // Prepare payload structure
            JSONObject payloadJson = new JSONObject();
            if (splitPayload) {
                int length = dataSize / Main.numAttrs;
                for (int i = 0; i < Main.numAttrs; i++) {
                    int start = i * length;
                    payloadJson.put("data" + i,
                        java.util.Base64.getEncoder().encodeToString(
                            Arrays.copyOfRange(bytes, start, start + length)
                        )
                    );
                }
            } else if (dataSize > 0) {
                payloadJson.put("data",
                    java.util.Base64.getEncoder().encodeToString(bytes)
                );
            }

            long startTime = System.currentTimeMillis();

            // First, insert all documents
            int docBatchCount = 0;
            for (JSONObject doc : documents) {
                String docId = doc.getString("_id");
                docStmt.setString(1, docId);
                // Use native OSON format for better performance (only if dataSize > 0)
                OracleJsonObject osonPayload = dataSize > 0 ? createOsonObject(payloadJson.toString()) : createOsonObject("{}");
                docStmt.setObject(2, osonPayload, OracleType.JSON);
                docStmt.addBatch();
                docBatchCount++;

                if (docBatchCount >= Main.batchSize) {
                    docStmt.executeBatch();
                    connection.commit();
                    docBatchCount = 0;
                }
            }
            if (docBatchCount > 0) {
                docStmt.executeBatch();
                connection.commit();
            }

            // Then, insert all array elements (after parent keys are committed)
            int arrayBatchCount = 0;
            for (JSONObject doc : documents) {
                String docId = doc.getString("_id");
                JSONArray indexArray = doc.getJSONArray("targets");

                for (int i = 0; i < indexArray.length(); i++) {
                    arrayStmt.setString(1, docId);
                    arrayStmt.setString(2, indexArray.getString(i));
                    arrayStmt.addBatch();
                    arrayBatchCount++;

                    if (arrayBatchCount >= Main.batchSize) {
                        arrayStmt.executeBatch();
                        connection.commit();
                        arrayBatchCount = 0;
                    }
                }
            }
            if (arrayBatchCount > 0) {
                arrayStmt.executeBatch();
                connection.commit();
            }

            docStmt.close();
            arrayStmt.close();

            long elapsed = System.currentTimeMillis() - startTime;
            System.out.println("  [Direct table insertion completed]");
            return elapsed;

        } catch (SQLException e) {
            System.err.println("Error inserting documents directly:");
            e.printStackTrace();
            try {
                connection.rollback();
            } catch (SQLException ex) {
                ex.printStackTrace();
            }
            return -1;
        }
    }
}
