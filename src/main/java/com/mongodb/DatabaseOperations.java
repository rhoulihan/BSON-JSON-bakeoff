package com.mongodb;

import org.json.JSONObject;

import java.util.List;

public interface DatabaseOperations {
    void initializeDatabase(String connectionString);
    void dropAndCreateCollections(List<String> collectionNames);
    List<JSONObject> generateDocuments(List<String> objectIds);
    long insertDocuments(String collectionName, List<JSONObject> documents, int dataSize, boolean splitPayload);
    int queryDocumentsById(String collectionName, String id);
    int queryDocumentsByIdUsingLookup(String collectionName, String id);
    void close();
}