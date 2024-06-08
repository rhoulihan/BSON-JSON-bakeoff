package com.mongodb;

import org.json.JSONObject;

import java.util.List;

public interface DatabaseOperations {
    void initializeDatabase(String connectionString);
    void dropAndCreateCollections(List<String> collectionNames);
    List<Integer> generateObjectIds(int count);
    List<JSONObject> generateDocuments(List<Integer> objectIds);
    long insertDocuments(String collectionName, List<JSONObject> documents, int dataSize, boolean splitPayload);
    int queryDocumentsById(String collectionName, int id);
    void close();
}