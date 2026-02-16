package com.mongodb;

import com.mongodb.client.*;
import com.mongodb.client.model.ClusteredIndexOptions;
import com.mongodb.client.model.CreateCollectionOptions;
import com.mongodb.client.model.Filters;
import com.mongodb.client.model.Indexes;
import com.mongodb.client.model.InsertManyOptions;
import com.mongodb.client.model.Projections;
import com.mongodb.ConnectionString;
import com.mongodb.MongoClientSettings;

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
import javax.net.ssl.SSLContext;
import javax.net.ssl.TrustManager;
import javax.net.ssl.X509TrustManager;
import java.security.cert.X509Certificate;
import java.security.NoSuchAlgorithmException;
import java.security.KeyManagementException;
import java.util.concurrent.TimeUnit;

/**
 * DocumentDB implementation using MongoDB-compatible Java driver.
 * 
 * DocumentDB is a MongoDB-compatible open-source database built on PostgreSQL.
 * Since it's MongoDB-compatible, it uses the same MongoDB Java driver,
 * but may require TLS connection settings for local development.
 */
public class DocumentDBOperations implements DatabaseOperations {
    private com.mongodb.client.MongoClient client;
    private MongoDatabase database;

    @Override
    public void initializeDatabase(String connectionString) {
        // DocumentDB is MongoDB-compatible, so we can use the same MongoDB client
        // Connection string should include TLS settings: ?tls=true&tlsAllowInvalidCertificates=true
        // Parse connection string to ensure TLS settings are properly applied
        ConnectionString connString = new ConnectionString(connectionString);
        
        // Check if tlsAllowInvalidCertificates is specified in the connection string
        String connStrLower = connectionString.toLowerCase();
        boolean allowInvalidCertificates = connStrLower.contains("tlsallowinvalidcertificates=true") 
                || connStrLower.contains("sslallowinvalidcertificates=true");
        
        // Build MongoClientSettings with explicit SSL/TLS configuration
        // Use generous timeouts because DocumentDB's MongoDB wire protocol layer
        // starts after the PostgreSQL engine, causing initial connection attempts
        // to get MongoSocketReadException ("Prematurely reached end of stream").
        MongoClientSettings.Builder settingsBuilder = MongoClientSettings.builder()
                .applyConnectionString(connString)
                .applyToClusterSettings(builder ->
                    builder.serverSelectionTimeout(60, TimeUnit.SECONDS))
                .applyToSocketSettings(builder -> {
                    builder.connectTimeout(30, TimeUnit.SECONDS);
                    builder.readTimeout(60, TimeUnit.SECONDS);
                });
        
        // Explicitly configure SSL settings if TLS is enabled
        // If tlsAllowInvalidCertificates=true, create a custom SSL context that accepts all certificates
        if (connString.getSslEnabled() != null && connString.getSslEnabled() && allowInvalidCertificates) {
            try {
                // Create a TrustManager that accepts all certificates
                TrustManager[] trustAllCerts = new TrustManager[] {
                    new X509TrustManager() {
                        public X509Certificate[] getAcceptedIssuers() {
                            return new X509Certificate[0];
                        }
                        public void checkClientTrusted(X509Certificate[] certs, String authType) {
                        }
                        public void checkServerTrusted(X509Certificate[] certs, String authType) {
                        }
                    }
                };
                
                // Create SSL context that accepts all certificates
                SSLContext sslContext = SSLContext.getInstance("TLS");
                sslContext.init(null, trustAllCerts, new java.security.SecureRandom());
                
                settingsBuilder.applyToSslSettings(builder -> {
                    builder.enabled(true);
                    builder.invalidHostNameAllowed(true);
                    builder.context(sslContext);
                });
            } catch (NoSuchAlgorithmException | KeyManagementException e) {
                // If SSL context creation fails, fall back to default behavior
                // The connection string parameters should still be applied
                settingsBuilder.applyToSslSettings(builder -> {
                    builder.enabled(true);
                    builder.invalidHostNameAllowed(true);
                });
            }
        } else if (connString.getSslEnabled() != null && connString.getSslEnabled()) {
            // TLS enabled but not allowing invalid certificates - use default SSL settings
            settingsBuilder.applyToSslSettings(builder -> {
                builder.enabled(true);
            });
        }
        
        MongoClientSettings settings = settingsBuilder.build();
        client = MongoClients.create(settings);
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
        // Use JOURNALED write concern for consistency with MongoDBOperations
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
            if (Main.measureObjectSizes && ct++ < 10)
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
    public long getAverageDocumentSize(String collectionName) {
        // Not implemented for DocumentDB - size measurement happens during generation
        return -1;
    }

    @Override
    public long getDocumentCount(String collectionName) {
        try {
            return database.getCollection(collectionName).countDocuments();
        } catch (Exception e) {
            System.err.println("Error getting document count: " + e.getMessage());
            return -1;
        }
    }

    @Override
    public boolean validateDocument(String collectionName, String id, JSONObject expected) {
        try {
            MongoCollection<Document> collection = database.getCollection(collectionName);
            Document doc = collection.find(Filters.eq("_id", id)).first();
            if (doc == null) {
                return false;
            }
            // Validate key fields match
            String docId = doc.getString("_id");
            return docId != null && docId.equals(expected.getString("_id"));
        } catch (Exception e) {
            System.err.println("Error validating document: " + e.getMessage());
            return false;
        }
    }

    @Override
    public void close() {
        client.close();
    }
}

