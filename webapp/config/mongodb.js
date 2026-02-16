/**
 * MongoDB connection configuration
 */

const { MongoClient } = require('mongodb');
require('dotenv').config();

let client = null;
let db = null;

async function connectToMongoDB() {
    if (client) {
        return { client, db };
    }

    const connectionString = process.env.MONGODB_CONNECTION_STRING || 
                           'mongodb://localhost:27017';
    const databaseName = process.env.MONGODB_DATABASE_NAME || 'benchmark_results';
    const collectionName = process.env.MONGODB_COLLECTION_NAME || 'test_runs';

    try {
        client = new MongoClient(connectionString, { serverSelectionTimeoutMS: 5000 });
        await client.connect();
        db = client.db(databaseName);
        console.log(`Connected to MongoDB: ${databaseName}`);
        return { client, db, collectionName };
    } catch (error) {
        console.error('Failed to connect to MongoDB:', error);
        throw error;
    }
}

async function closeConnection() {
    if (client) {
        await client.close();
        client = null;
        db = null;
        console.log('MongoDB connection closed');
    }
}

module.exports = {
    connectToMongoDB,
    closeConnection
};
