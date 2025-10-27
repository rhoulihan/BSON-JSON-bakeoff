package com.mongodb;

import java.io.ByteArrayOutputStream;
import java.io.StringReader;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Random;

import org.json.JSONObject;

import oracle.jdbc.OracleConnection;
import oracle.jdbc.internal.OracleTypes;
import oracle.sql.json.OracleJsonFactory;
import oracle.sql.json.OracleJsonGenerator;
import oracle.sql.json.OracleJsonObject;

public class OracleJCT2 implements DatabaseOperations {

    OracleJsonFactory jsonFactory;
    OracleConnection connection;
    ByteArrayOutputStream baos = new ByteArrayOutputStream();
    
    @Override
    public void initializeDatabase(String connectionString) {
        try {
            Class.forName("oracle.jdbc.driver.OracleDriver");
            connection = (OracleConnection) DriverManager.getConnection(connectionString);
            jsonFactory = new OracleJsonFactory();
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }

    @Override
    public void dropAndCreateCollections(List<String> collectionNames) {
        try {
            Statement stmt = connection.createStatement();
            if (Main.runLookupTest) {
                throw new UnsupportedOperationException("todo");
            }
            for (String name : collectionNames) {
                stmt.execute("drop table if exists " + name);
                stmt.execute("create json collection table " + name + " tablespace users");
            }
        } catch (SQLException e) {
            throw new RuntimeException(e);
        }
    }

    @Override
    public long insertDocuments(String collectionName, List<JSONObject> documents, int dataSize, boolean splitPayload) {
        if (Main.runLookupTest || Main.useInCondition) {
            throw new UnsupportedOperationException("todo");
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
            if (Main.runLookupTest || Main.useInCondition) {
                obj.remove("targets");
            }
            objects.add(obj);
        }
        
        try {
            PreparedStatement insert = connection.prepareStatement("insert into \"" + collectionName + "\" values (:1)");
            long start = System.currentTimeMillis();
            int added = 0;
            for (OracleJsonObject obj : objects) {
                byte[] oson = getOson(obj);
                insert.setObject(1, oson, OracleTypes.JSON);
                insert.addBatch();
                added++;
                if (added == Main.batchSize) {
                    insert.executeBatch();
                    added = 0;
                }
            }
            if (added > 0) {
                insert.executeBatch();
            }
            return System.currentTimeMillis() - start;
        } catch (SQLException e) {
            throw new RuntimeException(e);
        }
    }
    
    public byte[] getOson(OracleJsonObject obj) {
        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        OracleJsonGenerator gen = jsonFactory.createJsonBinaryGenerator(baos);
        gen.write(obj);
        gen.close();
        return baos.toByteArray();
    }

    @Override
    public int queryDocumentsById(String collectionName, String id) {
        throw new UnsupportedOperationException("todo");   
    }

    @Override
    public int queryDocumentsByIdWithInCondition(String collectionName, JSONObject document) {
        throw new UnsupportedOperationException("todo");   
    }

    @Override
    public int queryDocumentsByIdUsingLookup(String collectionName, String id) {
        throw new UnsupportedOperationException("todo");   
    }

    @Override
    public void close() {
        try {
            connection.close();
        } catch (SQLException e) {
            throw new RuntimeException(e);
        }
    }

}
