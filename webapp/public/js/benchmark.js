/**
 * Benchmark page - configure and launch benchmark runs
 */

(function () {
    'use strict';

    const form = document.getElementById('benchmark-form');
    const runBtn = document.getElementById('run-btn');
    const stopBtn = document.getElementById('stop-btn');
    const outputSection = document.getElementById('output-section');
    const outputConsole = document.getElementById('output-console');
    const runStatus = document.getElementById('run-status');

    // Cloud DB checkboxes
    const dbAtlas = document.getElementById('db-atlas');
    const dbAzure = document.getElementById('db-azure');
    const cloudConfig = document.getElementById('cloud-config');
    const atlasConnGroup = document.getElementById('atlas-conn-group');
    const azureConnGroup = document.getElementById('azure-conn-group');

    let currentRunId = null;
    let eventSource = null;

    // Toggle cloud connection fields when cloud DBs are checked
    function updateCloudFields() {
        const atlasChecked = dbAtlas.checked;
        const azureChecked = dbAzure.checked;
        cloudConfig.style.display = (atlasChecked || azureChecked) ? '' : 'none';
        atlasConnGroup.style.display = atlasChecked ? '' : 'none';
        azureConnGroup.style.display = azureChecked ? '' : 'none';
    }

    dbAtlas.addEventListener('change', updateCloudFields);
    dbAzure.addEventListener('change', updateCloudFields);

    // Build config object from form
    function getConfig() {
        const databases = [];
        document.querySelectorAll('input[name="databases"]:checked').forEach(cb => {
            databases.push(cb.value);
        });

        const payloadMode = document.querySelector('input[name="payload-mode"]:checked').value;

        return {
            databases,
            numDocs: parseInt(document.getElementById('num-docs').value) || 10000,
            numRuns: parseInt(document.getElementById('num-runs').value) || 3,
            batchSize: parseInt(document.getElementById('batch-size').value) || 500,
            queryLinks: parseInt(document.getElementById('query-links').value) || 10,
            queries: document.getElementById('opt-queries').checked,
            validate: document.getElementById('opt-validate').checked,
            monitor: document.getElementById('opt-monitor').checked,
            monitorInterval: parseFloat(document.getElementById('monitor-interval').value) || 0.5,
            randomizeOrder: document.getElementById('opt-randomize').checked,
            measureSizes: document.getElementById('opt-measure-sizes').checked,
            indexMode: document.getElementById('index-mode').value,
            largeItems: payloadMode === 'large',
            // Cloud connection overrides (only sent if non-empty)
            atlasConnectionString: document.getElementById('atlas-conn').value.trim() || undefined,
            azureConnectionString: document.getElementById('azure-conn').value.trim() || undefined
        };
    }

    // Validate form
    function validate() {
        const dbs = document.querySelectorAll('input[name="databases"]:checked');
        if (dbs.length === 0) {
            alert('Please select at least one database to benchmark.');
            return false;
        }
        return true;
    }

    // Append a line to the output console
    function appendLine(text, stream) {
        const line = document.createElement('div');
        line.className = 'line-' + (stream || 'stdout');
        line.textContent = text;
        outputConsole.appendChild(line);
        // Auto-scroll to bottom
        outputConsole.scrollTop = outputConsole.scrollHeight;
    }

    // Update status badge
    function setStatus(status) {
        runStatus.textContent = status;
        runStatus.className = 'run-status ' + status;
    }

    // Start SSE streaming
    function startStreaming(runId) {
        if (eventSource) {
            eventSource.close();
        }

        eventSource = new EventSource('/api/benchmark/stream/' + runId);

        eventSource.onmessage = function (e) {
            const entry = JSON.parse(e.data);
            appendLine(entry.text, entry.stream);
        };

        eventSource.addEventListener('status', function (e) {
            const data = JSON.parse(e.data);
            setStatus(data.status);
        });

        eventSource.addEventListener('done', function (e) {
            const data = JSON.parse(e.data);
            setStatus(data.status);
            eventSource.close();
            eventSource = null;
            runBtn.style.display = '';
            stopBtn.style.display = 'none';
            runBtn.disabled = false;
            runBtn.textContent = 'Run Benchmark';
        });

        eventSource.onerror = function () {
            // Connection lost - could be done or error
            if (eventSource) {
                eventSource.close();
                eventSource = null;
            }
            runBtn.style.display = '';
            stopBtn.style.display = 'none';
            runBtn.disabled = false;
            runBtn.textContent = 'Run Benchmark';
        };
    }

    // Submit handler
    form.addEventListener('submit', async function (e) {
        e.preventDefault();
        if (!validate()) return;

        const config = getConfig();

        // Show output section and clear previous output
        outputSection.style.display = '';
        outputConsole.innerHTML = '';
        setStatus('running');

        // Disable run button, show stop
        runBtn.disabled = true;
        runBtn.textContent = 'Starting...';
        stopBtn.style.display = '';

        try {
            const resp = await fetch('/api/benchmark/run', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(config)
            });

            if (!resp.ok) {
                const err = await resp.json();
                appendLine('Error: ' + (err.error || 'Failed to start benchmark'), 'system');
                setStatus('failed');
                runBtn.disabled = false;
                runBtn.textContent = 'Run Benchmark';
                runBtn.style.display = '';
                stopBtn.style.display = 'none';
                return;
            }

            const data = await resp.json();
            currentRunId = data.runId;
            appendLine('Benchmark started (run #' + currentRunId + ')', 'system');
            startStreaming(currentRunId);

        } catch (err) {
            appendLine('Network error: ' + err.message, 'system');
            setStatus('failed');
            runBtn.disabled = false;
            runBtn.textContent = 'Run Benchmark';
            stopBtn.style.display = 'none';
        }
    });

    // Stop handler
    stopBtn.addEventListener('click', async function () {
        if (!currentRunId) return;

        try {
            await fetch('/api/benchmark/stop/' + currentRunId, { method: 'POST' });
            appendLine('Stop signal sent...', 'system');
        } catch (err) {
            appendLine('Failed to stop: ' + err.message, 'system');
        }
    });
})();
