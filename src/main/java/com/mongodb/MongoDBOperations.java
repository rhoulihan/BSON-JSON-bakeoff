package com.mongodb;

import com.mongodb.client.*;
import com.mongodb.client.model.ClusteredIndexOptions;
import com.mongodb.client.model.CreateCollectionOptions;
import com.mongodb.client.model.Filters;
import com.mongodb.client.model.Indexes;
import com.mongodb.client.model.InsertManyOptions;
import com.mongodb.client.model.Projections;
import com.mongodb.WriteConcern;

import org.bson.BsonBinaryWriter;
import org.bson.Document;
import org.bson.codecs.Codec;
import org.bson.codecs.EncoderContext;
import org.bson.codecs.configuration.CodecRegistry;
import org.bson.io.BasicOutputBuffer;
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

        // Only create index on 'targets' array when runIndexTest is true
        if (Main.runIndexTest && collectionNames.contains("indexed")) {
            database.getCollection("indexed").createIndex(Indexes.ascending("targets"));
            System.out.println("Created index on indexed.targets");
        }
    }

    @Override
    public long insertDocuments(String collectionName, List<JSONObject> documents, int dataSize, boolean splitPayload) {
        MongoCollection<Document> collection = database.getCollection(collectionName).withWriteConcern(WriteConcern.JOURNALED);
        MongoCollection<Document> links = null;
        List<Document> insertDocs = new ArrayList<>();
        List<Document> linkDocs = null;
        Document data = new Document();
        Document link = null;

        if (Main.runLookupTest) {
            links = database.getCollection("links").withWriteConcern(WriteConcern.JOURNALED);
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
        long dupCount = 0;
        List<Document> bsonDocuments = new ArrayList<Document>();
        for (JSONObject json : documents) {
            bsonDocuments.add(Document.parse(json.toString()));
            // Only append binary data if dataSize > 0 (not using realistic data mode)
            if (dataSize > 0) {
                bsonDocuments.get(bsonDocuments.size() - 1).append("data", data);
            }
            if (Main.runLookupTest || Main.useInCondition) {
                bsonDocuments.get(bsonDocuments.size() - 1).remove("targets");
            }
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
            }
        }
        
        long startTime = System.currentTimeMillis();
        int ct = 0;
        for (Document json : bsonDocuments) {
            byte[] bson = toBsonBytes(json);
            if (ct++ < 10)
                System.out.println("Binding: " + bson.length);
            insertDocs.add(json);
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
    
    public static byte[] toBsonBytes(Document doc) {
        CodecRegistry registry = MongoClientSettings.getDefaultCodecRegistry();
        Codec<Document> codec = registry.get(Document.class);

        BasicOutputBuffer buffer = new BasicOutputBuffer();
        try (BsonBinaryWriter writer = new BsonBinaryWriter(buffer)) {
            codec.encode(writer, doc, EncoderContext.builder()
                    // set true if this is a collectible document (e.g., it may have _id)
                    .isEncodingCollectibleDocument(true)
                    .build());
        }
        return buffer.toByteArray();
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
    public int queryDocumentsByIdWithInCondition(String collectionName, JSONObject document) {
        MongoCollection<Document> collection = database.getCollection(collectionName);
        FindIterable<Document> documents = collection.find(Filters.in("_id", document.getJSONArray("targets"))).projection(Projections.fields(Projections.exclude("targets")));
        int count = 0;
        for (Document doc : documents) {
            // Process the document data as needed
            doc.clear();
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
