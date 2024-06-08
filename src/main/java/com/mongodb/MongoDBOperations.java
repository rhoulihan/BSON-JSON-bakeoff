package com.mongodb;

import com.mongodb.client.*;
import com.mongodb.client.model.Filters;
import com.mongodb.client.model.Indexes;
import org.bson.Document;
import org.json.JSONObject;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Random;

public class MongoDBOperations implements DatabaseOperations {
    private MongoClient client;
    private MongoDatabase database;

    @Override
    public void initializeDatabase(String connectionString) {
        client = MongoClients.create(connectionString);
        database = client.getDatabase("test");
    }

    @Override
    public void dropAndCreateCollections(List<String> collectionNames) {
        for (String collectionName : collectionNames) {
            database.getCollection(collectionName).drop();
            database.createCollection(collectionName);
        }
        database.getCollection("indexed").createIndex(Indexes.ascending("indexAttrs"));
    }

    @Override
    public List<Integer> generateObjectIds(int count) {
        List<Integer> ids = new ArrayList<>();
        for (int i = 0; i < count; i++) {
            ids.add(i); // Use simple integers as IDs
        }
        return ids;
    }

    @Override
    public List<JSONObject> generateDocuments(List<Integer> objectIds) {
        List<JSONObject> documents = new ArrayList<>();
        Random rand = new Random();
        for (Integer id : objectIds) {
            JSONObject json = new JSONObject();
            List<Integer> indexAttrs = new ArrayList<>();
            for (int i = 0; i < 10; i++) {
                indexAttrs.add(objectIds.get(rand.nextInt(objectIds.size())));
            }
            json.put("_id", id);
            json.put("indexAttrs", indexAttrs);
            documents.add(json);
        }
        return documents;
    }

    @Override
    public long insertDocuments(String collectionName, List<JSONObject> documents, int dataSize, boolean splitPayload) {
        MongoCollection<Document> collection = database.getCollection(collectionName);
        List<Document> insertDocs = new ArrayList<>();
        Document data = new Document();
        byte[] bytes = new byte[dataSize];
        new Random().nextBytes(bytes);

        if (splitPayload) {
            int length = dataSize / Main.numAttrs;
            int start;
            for (int i = 0; i < Main.numAttrs; i++) {
                start = i * length;
                data.append(String.format("data%d", i), Arrays.copyOfRange(bytes, start, start + length));
            }
        } else {
            data.append("data", bytes);
        }

        long startTime = System.currentTimeMillis();
        for (JSONObject json : documents) {
            insertDocs.add(Document.parse(json.toString()));
            insertDocs.get(insertDocs.size() - 1).append("data", data);

            if (insertDocs.size() == Main.batchSize) {
                collection.insertMany(insertDocs);
                insertDocs.clear();
            }
        }

        if (!insertDocs.isEmpty()) {
            collection.insertMany(insertDocs);
        }

        return System.currentTimeMillis() - startTime;
    }

    @Override
    public int queryDocumentsById(String collectionName, int id) {
        MongoCollection<Document> collection = database.getCollection(collectionName);
        FindIterable<Document> documents = collection.find(Filters.eq("indexAttrs", id));
        int count = 0;
        for (Document document : documents) {
            // Process the document data as needed
            count++;
        }
        return count;
    }

    @Override
    public void close() {
        client.close();
    }
}
