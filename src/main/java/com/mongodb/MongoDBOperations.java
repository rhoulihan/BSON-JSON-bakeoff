package com.mongodb;

import com.mongodb.client.*;
import com.mongodb.client.model.ClusteredIndexOptions;
import com.mongodb.client.model.CreateCollectionOptions;
import com.mongodb.client.model.Filters;
import com.mongodb.client.model.Indexes;
import com.mongodb.client.model.InsertManyOptions;
import com.mongodb.client.model.Projections;

import org.bson.Document;
import org.json.JSONObject;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Random;

public class MongoDBOperations implements DatabaseOperations {
    private com.mongodb.client.MongoClient client;
    private MongoDatabase database;

    @Override
    public void initializeDatabase(String connectionString) {
        client = MongoClients.create(connectionString);
        database = client.getDatabase("test");
    }

    @Override
    public void dropAndCreateCollections(List<String> collectionNames) {
        for (String collectionName : collectionNames) {
            if (Main.runLookupTest) {
                database.getCollection("links").drop();
                ClusteredIndexOptions clusteredIndexOptions = new ClusteredIndexOptions(new Document("_id", 1), true);
                CreateCollectionOptions createCollectionOptions = new CreateCollectionOptions().clusteredIndexOptions(clusteredIndexOptions);
                database.createCollection("links", createCollectionOptions);
            }

            database.getCollection(collectionName).drop();
            database.createCollection(collectionName);
        }
        database.getCollection("indexed").createIndex(Indexes.ascending("targets"));
    }

    @Override
    public List<JSONObject> generateDocuments(List<String> objectIds) {
        List<JSONObject> documents = new ArrayList<>();
        Random rand = new Random();
        for (String id : objectIds) {
            JSONObject json = new JSONObject();
            List<String> targets = new ArrayList<>();
            for (int i = 0; i < Main.numLinks; i++) {
                targets.add(objectIds.get(rand.nextInt(objectIds.size())));
            }
            json.put("_id", id);
            json.put("targets", targets);
            documents.add(json);
        }
        return documents;
    }

    @Override
    public long insertDocuments(String collectionName, List<JSONObject> documents, int dataSize, boolean splitPayload) {
        MongoCollection<Document> collection = database.getCollection(collectionName);
        MongoCollection<Document> links = null;
        List<Document> insertDocs = new ArrayList<>();
        List<Document> linkDocs = null;
        Document data = new Document();
        Document link = null;

        if (Main.runLookupTest) {
            links = database.getCollection("links");
            linkDocs = new ArrayList<>();
            link = new Document();
        }

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

        int dupCount = 0;
        long startTime = System.currentTimeMillis();
        for (JSONObject json : documents) {

            insertDocs.add(Document.parse(json.toString()));
            insertDocs.get(insertDocs.size() - 1).append("data", data);

            if (Main.runLookupTest) {
                for (Object target : json.getJSONArray("targets").toList()) {
                    link.append("_id", json.getString("_id") + "#" + target.toString());
                    link.append("target", target.toString());
                    linkDocs.add(link);
                    link = new Document();
                    if (linkDocs.size() == Main.batchSize) {
                        try {
                            links.insertMany(linkDocs, new InsertManyOptions().ordered(false));
                        } catch (MongoBulkWriteException e) {
                            dupCount += e.getWriteErrors().size();
                        }

                        linkDocs.clear();
                    }
                }

               insertDocs.get(insertDocs.size() - 1).remove("targets");
            }

            if (insertDocs.size() == Main.batchSize) {
                collection.insertMany(insertDocs);
                insertDocs.clear();
            }
        }

        if (!insertDocs.isEmpty()) {
            collection.insertMany(insertDocs);
        }

        if (Main.runLookupTest) {
            System.out.println(String.format("Duplicates found: %d", dupCount));
        }
        return System.currentTimeMillis() - startTime;
    }

    @Override
    public int queryDocumentsById(String collectionName, String id) {
        MongoCollection<Document> collection = database.getCollection(collectionName);
        FindIterable<Document> documents = collection.find(Filters.eq("targets", id)).projection(Projections.fields(Projections.exclude("targets")));
        int count = 0;
        for (Document document : documents) {
            // Process the document data as needed
            document.clear();
            count++;
        }
        return count;
    }

    @Override
    public int queryDocumentsByIdUsingLookup(String collectionName, String id) {
        MongoCollection<Document> collection = database.getCollection("links");
        AggregateIterable<Document> documents = collection.aggregate(Arrays.asList(new Document("$match", 
            new Document("_id", 
            new Document("$gte", id + "#")
                        .append("$lte", id + "#~"))), 
            new Document("$group", 
            new Document("_id", "")
                    .append("links", 
            new Document("$push", "$target"))), 
            new Document("$lookup", 
            new Document("from", collectionName)
                    .append("localField", "links")
                    .append("foreignField", "_id")
                    .append("as", "result")), 
            new Document("$unwind", 
            new Document("path", "$result")), 
            new Document("$replaceRoot", 
            new Document("newRoot", "$result"))));

        int count = 0;
        for (Document document : documents) {
            // Process the document data as needed
            document.clear();
            count++;
        }
        return count;
    }

    @Override
    public void close() {
        client.close();
    }
}
