/**
 * API routes for launching and monitoring benchmark runs
 */

const express = require('express');
const { spawn } = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');

const router = express.Router();

// Track active benchmark runs: id -> { process, output[], status }
const activeRuns = new Map();
let nextRunId = 1;

// Path to the Python orchestration script (relative to project root)
const SCRIPT_PATH = path.resolve(__dirname, '..', '..', 'scripts', 'run_article_benchmarks_docker.py');
const PROJECT_ROOT = path.resolve(__dirname, '..', '..');
const BASE_CONFIG_PATH = path.join(PROJECT_ROOT, 'config', 'benchmark_config.ini');

/**
 * Create a temporary config file with cloud connection string overrides.
 * Reads the base config, merges overrides, writes to a temp file.
 * Returns the temp file path, or null if no overrides needed.
 */
function createTempConfig(config) {
    const hasAtlasOverride = config.atlasConnectionString;
    const hasAzureOverride = config.azureConnectionString;

    if (!hasAtlasOverride && !hasAzureOverride) return null;
    if (!fs.existsSync(BASE_CONFIG_PATH)) return null;

    let iniContent = fs.readFileSync(BASE_CONFIG_PATH, 'utf-8');

    // Helper to set a value in an INI section
    function setIniValue(content, section, key, value) {
        const sectionRegex = new RegExp(`(\\[${section}\\][^\\[]*?)${key}\\s*=\\s*[^\\n]*`, 's');
        if (sectionRegex.test(content)) {
            return content.replace(sectionRegex, `$1${key} = ${value}`);
        }
        // Section exists but key doesn't - add it
        const sectionHeaderRegex = new RegExp(`(\\[${section}\\]\\n)`);
        if (sectionHeaderRegex.test(content)) {
            return content.replace(sectionHeaderRegex, `$1${key} = ${value}\n`);
        }
        // Section doesn't exist - add it
        return content + `\n[${section}]\nenabled = true\n${key} = ${value}\n`;
    }

    if (hasAtlasOverride) {
        iniContent = setIniValue(iniContent, 'mongodb_atlas', 'enabled', 'true');
        iniContent = setIniValue(iniContent, 'mongodb_atlas', 'connection_string', config.atlasConnectionString);
    }
    if (hasAzureOverride) {
        iniContent = setIniValue(iniContent, 'azure_documentdb', 'enabled', 'true');
        iniContent = setIniValue(iniContent, 'azure_documentdb', 'connection_string', config.azureConnectionString);
    }

    // IMPORTANT: Strip results_storage section credentials - they must come from the base config only.
    // This is a defense-in-depth measure; the frontend never sends these values.

    const tmpFile = path.join(os.tmpdir(), `benchmark_config_${Date.now()}.ini`);
    fs.writeFileSync(tmpFile, iniContent, 'utf-8');
    return tmpFile;
}

/**
 * POST /api/benchmark/run
 * Launch a new benchmark run with the given configuration.
 * Returns { runId } which can be used to stream output.
 */
router.post('/run', (req, res) => {
    // Only allow one benchmark at a time
    for (const [, run] of activeRuns) {
        if (run.status === 'running') {
            return res.status(409).json({ error: 'A benchmark is already running. Wait for it to finish or stop it first.' });
        }
    }

    const config = req.body;
    const args = buildArgs(config);

    const runId = String(nextRunId++);
    const output = [];
    let status = 'running';

    // Create temp config if cloud connection overrides were provided
    const tmpConfigPath = createTempConfig(config);
    const env = { ...process.env };
    if (tmpConfigPath) {
        env.BENCHMARK_CONFIG_PATH = tmpConfigPath;
    }

    // Spawn the Python script from the project root directory
    const proc = spawn('python3', [SCRIPT_PATH, ...args], {
        cwd: PROJECT_ROOT,
        env,
        stdio: ['ignore', 'pipe', 'pipe']
    });

    proc.stdout.on('data', (data) => {
        const lines = data.toString().split('\n');
        for (const line of lines) {
            if (line) output.push({ ts: Date.now(), stream: 'stdout', text: line });
        }
    });

    proc.stderr.on('data', (data) => {
        const lines = data.toString().split('\n');
        for (const line of lines) {
            if (line) output.push({ ts: Date.now(), stream: 'stderr', text: line });
        }
    });

    proc.on('close', (code) => {
        status = code === 0 ? 'completed' : 'failed';
        output.push({ ts: Date.now(), stream: 'system', text: `Process exited with code ${code}` });
        const run = activeRuns.get(runId);
        if (run) run.status = status;
        // Clean up temp config file
        if (tmpConfigPath) {
            try { fs.unlinkSync(tmpConfigPath); } catch (_) { /* ignore */ }
        }
    });

    proc.on('error', (err) => {
        status = 'failed';
        output.push({ ts: Date.now(), stream: 'system', text: `Failed to start: ${err.message}` });
        const run = activeRuns.get(runId);
        if (run) run.status = status;
    });

    activeRuns.set(runId, { process: proc, output, status });

    // Clean up old finished runs (keep at most 10)
    const finished = [...activeRuns.entries()].filter(([, r]) => r.status !== 'running');
    while (finished.length > 10) {
        const [oldId] = finished.shift();
        activeRuns.delete(oldId);
    }

    res.json({ runId });
});

/**
 * GET /api/benchmark/stream/:runId
 * SSE endpoint that streams benchmark output in real time.
 */
router.get('/stream/:runId', (req, res) => {
    const run = activeRuns.get(req.params.runId);
    if (!run) {
        return res.status(404).json({ error: 'Run not found' });
    }

    res.writeHead(200, {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive'
    });

    let cursor = 0;

    const sendPending = () => {
        while (cursor < run.output.length) {
            const entry = run.output[cursor++];
            res.write(`data: ${JSON.stringify(entry)}\n\n`);
        }
        // Send status event
        res.write(`event: status\ndata: ${JSON.stringify({ status: run.status })}\n\n`);
    };

    // Send all buffered output immediately
    sendPending();

    // Poll for new output every 500ms
    const interval = setInterval(() => {
        sendPending();
        if (run.status !== 'running') {
            clearInterval(interval);
            res.write(`event: done\ndata: ${JSON.stringify({ status: run.status })}\n\n`);
            res.end();
        }
    }, 500);

    req.on('close', () => {
        clearInterval(interval);
    });
});

/**
 * POST /api/benchmark/stop/:runId
 * Stop a running benchmark.
 */
router.post('/stop/:runId', (req, res) => {
    const run = activeRuns.get(req.params.runId);
    if (!run) {
        return res.status(404).json({ error: 'Run not found' });
    }
    if (run.status !== 'running') {
        return res.status(400).json({ error: 'Run is not active' });
    }

    run.process.kill('SIGTERM');
    // Give it a moment, then force kill
    setTimeout(() => {
        try { run.process.kill('SIGKILL'); } catch (_) { /* already dead */ }
    }, 5000);

    run.status = 'stopped';
    res.json({ status: 'stopped' });
});

/**
 * GET /api/benchmark/status
 * Get status of all runs.
 */
router.get('/status', (req, res) => {
    const runs = [];
    for (const [id, run] of activeRuns) {
        runs.push({ id, status: run.status, lines: run.output.length });
    }
    res.json({ runs });
});

/**
 * Build command-line arguments for run_article_benchmarks_docker.py
 * from the frontend configuration object.
 */
function buildArgs(config) {
    const args = [];

    // Database selection flags
    const databases = config.databases || [];
    if (databases.includes('mongodb')) args.push('--mongodb');
    if (databases.includes('documentdb')) args.push('--documentdb');
    if (databases.includes('postgresql')) args.push('--postgresql');
    if (databases.includes('yugabytedb')) args.push('--yugabytedb');
    if (databases.includes('cockroachdb')) args.push('--cockroachdb');
    if (databases.includes('mongodb-atlas')) args.push('--mongodb-atlas');
    if (databases.includes('azure-documentdb')) args.push('--azure-documentdb');

    // Test parameters
    if (config.numDocs) args.push('--num-docs', String(config.numDocs));
    if (config.numRuns) args.push('--num-runs', String(config.numRuns));
    if (config.batchSize) args.push('--batch-size', String(config.batchSize));

    // Query options
    if (config.queries) args.push('--queries');
    if (config.queryLinks) args.push('--query-links', String(config.queryLinks));

    // Indexing mode
    if (config.indexMode === 'no-index') args.push('--no-index');
    if (config.indexMode === 'full-comparison') args.push('--full-comparison');

    // Payload sizes
    if (config.largeItems) args.push('--large-items');

    // Other options
    if (config.validate) args.push('--validate');
    if (config.measureSizes) args.push('--measure-sizes');
    if (config.randomizeOrder) args.push('--randomize-order');

    // Resource monitoring
    if (config.monitor === false) args.push('--no-monitor');
    if (config.monitorInterval) args.push('--monitor-interval', String(config.monitorInterval));

    return args;
}

module.exports = router;
