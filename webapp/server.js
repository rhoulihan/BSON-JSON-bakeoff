/**
 * Express server for benchmark results visualization
 */

const express = require('express');
const cors = require('cors');
const path = require('path');
const { connectToMongoDB, closeConnection } = require('./config/mongodb');
const getResultsRoutes = require('./routes/results');

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

// MongoDB connection and routes
let db = null;
let collectionName = 'test_runs';
let resultsRouter = null;
let dbError = null;

// Health check (always available)
app.get('/api/health', (req, res) => {
    res.json({ status: db ? 'ok' : 'degraded', database: db ? 'connected' : 'disconnected' });
});

// API results proxy — delegates to the real router once MongoDB connects
app.use('/api/results', (req, res, next) => {
    if (resultsRouter) {
        return resultsRouter(req, res, next);
    }
    if (dbError) {
        return res.status(503).json({ error: 'Database unavailable', message: dbError });
    }
    res.status(503).json({ error: 'Database connecting', message: 'Server is starting up, try again shortly' });
});

// Start server unconditionally so static assets are always served
app.listen(PORT, () => {
    console.log(`Benchmark Results Webapp running on http://localhost:${PORT}`);
    console.log(`API available at http://localhost:${PORT}/api/results`);
});

// Connect to MongoDB asynchronously — server stays up even if this fails
(async () => {
    try {
        const { db: connectedDb, collectionName: collName } = await connectToMongoDB();
        db = connectedDb;
        collectionName = collName || 'test_runs';
        resultsRouter = getResultsRoutes(db, collectionName);
        console.log('API routes ready (MongoDB connected)');
    } catch (error) {
        dbError = error.message;
        console.error('MongoDB connection failed — API routes unavailable:', error.message);
    }
})();

// Graceful shutdown
process.on('SIGINT', async () => {
    console.log('\nShutting down...');
    await closeConnection();
    process.exit(0);
});

process.on('SIGTERM', async () => {
    console.log('\nShutting down...');
    await closeConnection();
    process.exit(0);
});
