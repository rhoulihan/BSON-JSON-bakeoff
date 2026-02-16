/**
 * API routes for benchmark results
 */

const express = require('express');
const router = express.Router();
const { ObjectId } = require('mongodb');

function getResultsRoutes(db, collectionName) {
    // GET /api/results - Query results with filters
    router.get('/', async (req, res) => {
        try {
            const collection = db.collection(collectionName);
            
            // Build query filter
            const filter = {};
            
            if (req.query.database_type) {
                filter['database.type'] = req.query.database_type;
            }
            
            if (req.query.database_version) {
                filter['database.version'] = req.query.database_version;
            }
            
            if (req.query.test_run_id) {
                filter['test_run_id'] = req.query.test_run_id;
            }
            
            if (req.query.start_date || req.query.end_date) {
                filter.timestamp = {};
                if (req.query.start_date) {
                    filter.timestamp.$gte = new Date(req.query.start_date);
                }
                if (req.query.end_date) {
                    filter.timestamp.$lte = new Date(req.query.end_date);
                }
            }
            
            // Pagination
            const limit = parseInt(req.query.limit) || 100;
            const skip = parseInt(req.query.skip) || 0;
            
            // Sort
            const sort = { timestamp: -1 }; // Most recent first
            
            const results = await collection
                .find(filter)
                .sort(sort)
                .limit(limit)
                .skip(skip)
                .toArray();
            
            const total = await collection.countDocuments(filter);
            
            res.json({
                results,
                total,
                limit,
                skip
            });
        } catch (error) {
            console.error('Error querying results:', error);
            res.status(500).json({ error: error.message });
        }
    });
    
    // GET /api/results/:id - Get single test result
    router.get('/:id', async (req, res) => {
        try {
            const collection = db.collection(collectionName);
            const result = await collection.findOne({ _id: new ObjectId(req.params.id) });
            
            if (!result) {
                return res.status(404).json({ error: 'Result not found' });
            }
            
            res.json(result);
        } catch (error) {
            console.error('Error getting result:', error);
            res.status(500).json({ error: error.message });
        }
    });
    
    // GET /api/versions - Get list of all database/client versions
    router.get('/meta/versions', async (req, res) => {
        try {
            const collection = db.collection(collectionName);
            
            const dbVersions = await collection.distinct('database.version');
            const clientVersions = await collection.distinct('client.version');
            const dbTypes = await collection.distinct('database.type');
            // Get test_run_ids with their earliest timestamp for display
            const testRunAgg = await collection.aggregate([
                { $match: { test_run_id: { $ne: null } } },
                { $group: { _id: '$test_run_id', first_timestamp: { $min: '$timestamp' } } },
                { $sort: { first_timestamp: -1 } }
            ]).toArray();

            const test_run_ids = testRunAgg.map(r => ({
                id: r._id,
                timestamp: r.first_timestamp
            }));

            // Collect DocumentDB-specific version components
            const documentdbVersions = await collection.distinct('database.documentdb_version');
            const wireProtocolVersions = await collection.distinct('database.wire_protocol_version');
            const postgresVersions = await collection.distinct('database.postgres_version');

            res.json({
                database_versions: dbVersions.sort(),
                client_versions: clientVersions.sort(),
                database_types: dbTypes.sort(),
                test_run_ids,
                documentdb_versions: documentdbVersions.filter(v => v != null).sort(),
                wire_protocol_versions: wireProtocolVersions.filter(v => v != null).sort(),
                postgres_versions: postgresVersions.filter(v => v != null).sort()
            });
        } catch (error) {
            console.error('Error getting versions:', error);
            res.status(500).json({ error: error.message });
        }
    });
    
    // GET /api/comparison - Compare performance across versions/databases
    router.get('/meta/comparison', async (req, res) => {
        try {
            const collection = db.collection(collectionName);
            
            const { database_type, database_version, test_type, payload_size } = req.query;
            
            const matchFilter = {
                'results.success': true
            };
            
            if (database_type) {
                matchFilter['database.type'] = database_type;
            }
            
            if (database_version) {
                matchFilter['database.version'] = database_version;
            }
            
            if (test_type) {
                matchFilter['test_config.test_type'] = test_type;
            }
            
            if (payload_size) {
                matchFilter['test_config.payload_size'] = parseInt(payload_size);
            }
            
            const pipeline = [
                { $match: matchFilter },
                {
                    $group: {
                        _id: {
                            database_type: '$database.type',
                            database_version: '$database.version',
                            test_type: '$test_config.test_type',
                            payload_size: '$test_config.payload_size',
                            indexed: '$test_config.indexed'
                        },
                        avg_insert_time: { $avg: '$results.insert_time_ms' },
                        avg_insert_throughput: { $avg: '$results.insert_throughput' },
                        avg_query_time: { $avg: '$results.query_time_ms' },
                        avg_query_throughput: { $avg: '$results.query_throughput' },
                        count: { $sum: 1 }
                    }
                },
                { $sort: { '_id.payload_size': 1 } }
            ];
            
            const comparison = await collection.aggregate(pipeline).toArray();
            
            res.json({ comparison });
        } catch (error) {
            console.error('Error getting comparison:', error);
            res.status(500).json({ error: error.message });
        }
    });
    
    return router;
}

module.exports = getResultsRoutes;
