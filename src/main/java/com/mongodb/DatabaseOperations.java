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

    /**
     * Get the average document size in bytes for the given collection.
     * For MongoDB, this returns BSON size. For Oracle, this returns OSON size.
     * @param collectionName The collection/table name
     * @return Average document size in bytes, or -1 if not supported or error
     */
    long getAverageDocumentSize(String collectionName);

    void close();
}