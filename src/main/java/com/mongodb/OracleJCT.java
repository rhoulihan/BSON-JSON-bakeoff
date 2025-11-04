package com.mongodb;

import java.io.ByteArrayOutputStream;
import java.io.StringReader;
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

import oracle.jdbc.OracleConnection;
import oracle.jdbc.internal.OracleTypes;
import oracle.sql.json.OracleJsonFactory;
import oracle.sql.json.OracleJsonGenerator;
import oracle.sql.json.OracleJsonObject;

/**
 * Oracle implementation using JSON Collection Tables with direct JDBC operations.
 *
 * This implementation uses Oracle's JSON collection table feature which provides
 * a simple JSON document store interface while maintaining Oracle's ACID properties.
 */
public class OracleJCT implements DatabaseOperations {

    OracleJsonFactory jsonFactory;
    OracleConnection connection;

    @Override
    public void initializeDatabase(String connectionString) {
        try {
            Class.forName("oracle.jdbc.driver.OracleDriver");
            connection = (OracleConnection) DriverManager.getConnection(connectionString);
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

            // Apply session optimizations for better performance
            Statement optStmt = connection.createStatement();

            // Session parse optimization - cache parsed SQL statements
            optStmt.execute("ALTER SESSION SET SESSION_CACHED_CURSORS = 200");

            // Optional async commit mode (only if enabled via -acb flag)
            if (Main.useAsyncCommit) {
                optStmt.execute("ALTER SESSION SET COMMIT_LOGGING = BATCH");
                optStmt.execute("ALTER SESSION SET COMMIT_WAIT = NOWAIT");
                System.out.println("⚠ ASYNC COMMIT ENABLED: COMMIT_LOGGING=BATCH, COMMIT_WAIT=NOWAIT");
                System.out.println("⚠ WARNING: This mode is NOT ACID compliant - data may be lost on crash!");
            }

            optStmt.close();
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }

    @Override
    public void dropAndCreateCollections(List<String> collectionNames) {
        try {
            Statement stmt = connection.createStatement();
            if (Main.runLookupTest) {
                throw new UnsupportedOperationException("Lookup test not yet implemented for OracleJCT");
            }
            for (String name : collectionNames) {
                // Drop index if it exists (must be done before dropping table)
                if (name.equals("indexed")) {
                    try {
                        if (Main.useMultivalueIndex) {
                            stmt.execute("DROP INDEX idx_targets");
                            System.out.println("Dropped multivalue index idx_targets");
                        } else {
                            stmt.execute("DROP SEARCH INDEX idx_targets");
                            System.out.println("Dropped search index idx_targets");
                        }
                    } catch (SQLException e) {
                        // Ignore if index doesn't exist
                    }
                }

                // Drop table if exists
                try {
                    stmt.execute("DROP TABLE " + name + " CASCADE CONSTRAINTS PURGE");
                    System.out.println("Dropped table " + name);
                } catch (SQLException e) {
                    // Ignore if table doesn't exist
                    System.out.println("Table " + name + " does not exist");
                }

                // Create JSON collection table in USERS tablespace (required for automatic segment space management)
                stmt.execute("CREATE JSON COLLECTION TABLE " + name + " TABLESPACE USERS");
                System.out.println("Created JSON collection table " + name);
            }

            // Create index on 'targets' array for the indexed collection (only when runIndexTest is true)
            if (Main.runIndexTest && collectionNames.contains("indexed")) {
                try {
                    if (Main.useMultivalueIndex) {
                        System.out.println("Creating multivalue index on indexed collection...");
                        stmt.execute("CREATE MULTIVALUE INDEX idx_targets ON indexed (data.targets[*].string())");
                        System.out.println("✓ Successfully created multivalue index idx_targets");

                        // Verify index was created and check its type
                        ResultSet idxRs = stmt.executeQuery(
                            "SELECT index_name, index_type, status FROM user_indexes WHERE index_name = 'IDX_TARGETS'"
                        );
                        if (idxRs.next()) {
                            String idxType = idxRs.getString(2);
                            System.out.println("✓ Verified: Index " + idxRs.getString(1) +
                                             " (Type: " + idxType + ") with status: " + idxRs.getString(3));
                            if (!idxType.contains("MVI") && !idxType.contains("FUNCTION-BASED")) {
                                System.out.println("⚠ WARNING: Expected FUNCTION-BASED MVI but got: " + idxType);
                            }
                        } else {
                            System.out.println("⚠ Warning: Index not found in user_indexes");
                        }
                        idxRs.close();
                    } else {
                        System.out.println("Creating JSON search index on indexed collection...");
                        stmt.execute("CREATE SEARCH INDEX idx_targets ON indexed (data) FOR JSON");
                        System.out.println("✓ Successfully created search index idx_targets");

                        // Verify index was created
                        ResultSet idxRs = stmt.executeQuery(
                            "SELECT idx_name, idx_status FROM user_indexes WHERE idx_name = 'IDX_TARGETS'"
                        );
                        if (idxRs.next()) {
                            System.out.println("✓ Verified: Index " + idxRs.getString(1) + " exists with status: " + idxRs.getString(2));
                        } else {
                            System.out.println("⚠ Warning: Index not found in user_indexes");
                        }
                        idxRs.close();
                    }
                } catch (SQLException e) {
                    String indexType = Main.useMultivalueIndex ? "multivalue index" : "search index";
                    System.err.println("✗ ERROR: Could not create " + indexType + ": " + e.getMessage());
                    e.printStackTrace();
                }
            } else if (collectionNames.contains("indexed")) {
                String indexType = Main.useMultivalueIndex ? "multivalue index" : "search index";
                System.out.println("Note: Running WITHOUT " + indexType + " (use -i flag to enable index)");
            }

            connection.commit();
            stmt.close();
        } catch (SQLException e) {
            throw new RuntimeException(e);
        }
    }

    @Override
    public long insertDocuments(String collectionName, List<JSONObject> documents, int dataSize, boolean splitPayload) {
        if (Main.runLookupTest) {
            throw new UnsupportedOperationException("Lookup test not yet implemented for OracleJCT");
        }

        OracleJsonObject data = jsonFactory.createObject();
        byte[] bytes = new byte[dataSize];
        new Random().nextBytes(bytes);
        if (splitPayload) {
            int length = dataSize / Main.numAttrs;
            int start;
            for (int i = 0; i < Main.numAttrs; i++) {
                start = i * length;
                data.put(String.format("data%d", i), Arrays.copyOfRange(bytes, start, start + length));
            }
        } else if (dataSize > 0) {
            data.put("data", bytes);
        }

        List<OracleJsonObject> objects = new ArrayList<OracleJsonObject>();
        for (JSONObject json : documents) {
            OracleJsonObject obj = jsonFactory.createJsonTextValue(new StringReader(json.toString())).asJsonObject();
            // Only add binary data field if dataSize > 0 (not using realistic data mode)
            if (dataSize > 0) {
                obj.put("data", data);
            }
            if (Main.useInCondition) {
                obj.remove("targets");
            }
            objects.add(obj);
        }

        try {
            PreparedStatement insert = connection.prepareStatement("INSERT INTO \"" + collectionName + "\" VALUES (:1)");
            long start = System.currentTimeMillis();
            int added = 0;
            for (OracleJsonObject obj : objects) {
                // Use explicit OSON binary conversion for better performance
                byte[] oson = getOson(obj);
                insert.setObject(1, oson, OracleTypes.JSON);
                insert.addBatch();
                added++;
                if (added == Main.batchSize) {
                    insert.executeBatch();
                    connection.commit();
                    added = 0;
                }
            }
            if (added > 0) {
                insert.executeBatch();
                connection.commit();
            }

            // Gather statistics for indexed collections to improve query performance
            if (Main.runIndexTest && collectionName.equals("indexed")) {
                Statement statsStmt = connection.createStatement();
                statsStmt.execute("BEGIN DBMS_STATS.GATHER_TABLE_STATS(USER, '" +
                                  collectionName.toUpperCase() +
                                  "', estimate_percent => DBMS_STATS.AUTO_SAMPLE_SIZE); END;");
                statsStmt.close();
                System.out.println("✓ Gathered table statistics for indexed collection");
            }

            insert.close();
            return System.currentTimeMillis() - start;
        } catch (SQLException e) {
            throw new RuntimeException(e);
        }
    }

    /**
     * Convert OracleJsonObject to OSON (Oracle Binary JSON) format.
     * This explicit conversion improves insertion performance compared to implicit conversion.
     */
    private byte[] getOson(OracleJsonObject obj) {
        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        OracleJsonGenerator gen = jsonFactory.createJsonBinaryGenerator(baos);
        gen.write(obj);
        gen.close();
        return baos.toByteArray();
    }

    @Override
    public int queryDocumentsById(String collectionName, String id) {
        // Query documents where 'targets' array contains the specified id
        // Use different query syntax depending on index type
        String sql;

        if (Main.useMultivalueIndex) {
            // For multivalue index: use JSON_EXISTS with filter expression
            // Index must be created with: CREATE MULTIVALUE INDEX idx_targets ON indexed (data.targets[*].string())
            // This query results in: INDEX RANGE SCAN (MULTI VALUE) on IDX_TARGETS
            sql = "SELECT data FROM \"" + collectionName + "\" WHERE JSON_EXISTS(data, '$.targets?(@ == $val)' PASSING ? AS \"val\")";
        } else {
            // For search index: use JSON_EXISTS with filter expression (optimized for search indexes)
            sql = "SELECT data FROM \"" + collectionName + "\" WHERE JSON_EXISTS(data, '$?(@.targets[*] == $id)' PASSING ? AS \"id\")";
        }

        try {
            PreparedStatement stmt = connection.prepareStatement(sql);
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
            System.err.println("Error querying documents by ID:");
            e.printStackTrace();
            return 0;
        }
    }

    @Override
    public int queryDocumentsByIdWithInCondition(String collectionName, JSONObject document) {
        // Query documents using IN condition on the targets array
        JSONArray targets = document.getJSONArray("targets");

        if (targets.length() == 0) {
            return 0;
        }

        // For Oracle JSON, we need to query documents where _id is in the targets array
        // Build the SQL with IN clause
        StringBuilder sql = new StringBuilder();
        sql.append("SELECT data FROM \"").append(collectionName).append("\" WHERE JSON_VALUE(data, '$._id') IN (");

        for (int i = 0; i < targets.length(); i++) {
            if (i > 0) sql.append(", ");
            sql.append("?");
        }
        sql.append(")");

        try {
            PreparedStatement stmt = connection.prepareStatement(sql.toString());

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
        throw new UnsupportedOperationException("Lookup test not yet implemented for OracleJCT");
    }

    @Override
    public long getAverageDocumentSize(String collectionName) {
        try {
            String sql = "SELECT AVG(LENGTH(data)) as avg_size FROM " + collectionName;
            try (PreparedStatement pstmt = connection.prepareStatement(sql);
                 ResultSet rs = pstmt.executeQuery()) {
                if (rs.next()) {
                    return rs.getLong("avg_size");
                }
                return -1;
            }
        } catch (SQLException e) {
            System.err.println("Error getting average document size: " + e.getMessage());
            return -1;
        }
    }

    @Override
    public void close() {
        try {
            if (connection != null && !connection.isClosed()) {
                connection.commit();
                connection.close();
            }
        } catch (SQLException e) {
            throw new RuntimeException(e);
        }
    }

}
