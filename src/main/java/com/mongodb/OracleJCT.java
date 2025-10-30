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
                // Drop search index if it exists (must be done before dropping table)
                if (name.equals("indexed")) {
                    try {
                        stmt.execute("DROP SEARCH INDEX idx_targets");
                        System.out.println("Dropped search index idx_targets");
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
                    stmt.execute("CREATE SEARCH INDEX idx_targets ON indexed (data) FOR JSON");
                    System.out.println("Created search index on indexed collection");
                } catch (SQLException e) {
                    System.err.println("Warning: Could not create search index: " + e.getMessage());
                }
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
        } else {
            data.put("data", bytes);
        }

        List<OracleJsonObject> objects = new ArrayList<OracleJsonObject>();
        for (JSONObject json : documents) {
            OracleJsonObject obj = jsonFactory.createJsonTextValue(new StringReader(json.toString())).asJsonObject();
            obj.put("data", data);
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
        String sql = "SELECT data FROM \"" + collectionName + "\" WHERE JSON_EXISTS(data, '$?(@.targets[*] == $id)' PASSING ? AS \"id\")";

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
