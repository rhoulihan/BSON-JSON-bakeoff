package com.mongodb;

import org.json.JSONObject;

import java.util.List;

public interface DatabaseOperations {
    void initializeDatabase(String connectionString);
    void dropAndCreateCollections(List<String> collectionNames);
    long insertDocuments(String collectionName, List<JSONObject> documents, int dataSize, boolean splitPayload);
    int queryDocumentsById(String collectionName, String id);
    int queryDocumentsByIdWithInCondition(String collectionName, JSONObject document);
    int queryDocumentsByIdUsingLookup(String collectionName, String id);
    void close();
}