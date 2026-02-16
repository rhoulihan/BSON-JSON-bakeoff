/**
 * Main application JavaScript
 */

const API_BASE = '/api/results';

let insertionChart = null;
let queryChart = null;
let throughputChart = null;
let latencyPercentileChart = null;
let latencyTimelineChart = null;
let resourceCpuChart = null;
let resourceIopsChart = null;

// Cloud database types that have latency metrics
const CLOUD_DB_TYPES = ['mongodb-cloud', 'documentdb-azure'];

// Store loaded results for detail view access
let currentResults = [];

// Initialize on page load
document.addEventListener('DOMContentLoaded', async () => {
    await loadVersions();
    await loadResults();
    setupEventListeners();
});

async function loadVersions() {
    try {
        const response = await fetch(`${API_BASE}/meta/versions`);
        const data = await response.json();

        // Populate database type dropdown
        const dbTypeSelect = document.getElementById('database-type');
        data.database_types.forEach(type => {
            const option = document.createElement('option');
            option.value = type;
            option.textContent = type;
            dbTypeSelect.appendChild(option);
        });

        // Populate database version dropdown
        const dbVersionSelect = document.getElementById('database-version');
        data.database_versions.forEach(version => {
            const option = document.createElement('option');
            option.value = version;
            option.textContent = version;
            dbVersionSelect.appendChild(option);
        });

        // Populate test run dropdown
        const testRunSelect = document.getElementById('test-run');
        (data.test_run_ids || []).forEach(id => {
            const option = document.createElement('option');
            option.value = id;
            // Show a truncated label for long UUIDs
            option.textContent = id.length > 24 ? id.substring(0, 8) + '...' + id.substring(id.length - 4) : id;
            option.title = id;
            testRunSelect.appendChild(option);
        });
    } catch (error) {
        console.error('Error loading versions:', error);
    }
}

async function loadResults() {
    try {
        const filters = getFilters();
        let allResults = [];

        // If no database type filter is applied, fetch results from all database types
        if (!filters.database_type) {
            // Get all available database types
            const versionsResponse = await fetch(`${API_BASE}/meta/versions`);
            const versionsData = await versionsResponse.json();
            const databaseTypes = versionsData.database_types || [];
            console.log('Found database types:', databaseTypes);

            // Fetch results for each database type
            const fetchPromises = databaseTypes.map(async (dbType) => {
                const queryParams = new URLSearchParams();
                queryParams.append('database_type', dbType);
                if (filters.database_version) queryParams.append('database_version', filters.database_version);
                if (filters.test_run_id) queryParams.append('test_run_id', filters.test_run_id);
                if (filters.start_date) queryParams.append('start_date', filters.start_date);
                if (filters.end_date) queryParams.append('end_date', filters.end_date);
                // Fetch a reasonable number of results per database type
                queryParams.append('limit', '500');

                const response = await fetch(`${API_BASE}?${queryParams}`);
                const data = await response.json();
                const results = data.results || [];
                console.log(`Fetched ${results.length} results for database type: ${dbType}`);
                return results;
            });

            const resultsArrays = await Promise.all(fetchPromises);
            allResults = resultsArrays.flat();
            console.log(`Total results fetched: ${allResults.length}`);

            // Sort by timestamp descending (most recent first)
            allResults.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
        } else {
            // If database type filter is applied, use the normal approach
            const queryParams = new URLSearchParams();
            queryParams.append('database_type', filters.database_type);
            if (filters.database_version) queryParams.append('database_version', filters.database_version);
            if (filters.test_run_id) queryParams.append('test_run_id', filters.test_run_id);
            if (filters.start_date) queryParams.append('start_date', filters.start_date);
            if (filters.end_date) queryParams.append('end_date', filters.end_date);
            queryParams.append('limit', '100');

            const response = await fetch(`${API_BASE}?${queryParams}`);
            const data = await response.json();
            allResults = data.results || [];
        }

        currentResults = allResults;
        updateTable(allResults);
        updateCharts(allResults);
        updateResourceComparison(allResults);
    } catch (error) {
        console.error('Error loading results:', error);
        showError('Failed to load results: ' + error.message);
    }
}

function getFilters() {
    return {
        database_type: document.getElementById('database-type').value,
        database_version: document.getElementById('database-version').value,
        test_type: document.getElementById('test-type').value,
        test_run_id: document.getElementById('test-run').value,
        start_date: document.getElementById('start-date').value,
        end_date: document.getElementById('end-date').value
    };
}

// Helper: format a metric value or return null for N/A
function fmtMetric(val, decimals) {
    if (val == null || val === undefined) return null;
    return typeof val === 'number' ? val.toFixed(decimals !== undefined ? decimals : 1) : val;
}

function updateTable(results) {
    const tbody = document.getElementById('results-tbody');
    tbody.innerHTML = '';

    if (results.length === 0) {
        tbody.innerHTML = '<tr><td colspan="14" class="loading">No results found</td></tr>';
        return;
    }

    results.forEach((result, index) => {
        const row = document.createElement('tr');
        row.className = 'clickable-row';
        row.dataset.resultIndex = index;
        row.addEventListener('click', () => showDetailModal(result));

        const timestamp = new Date(result.timestamp).toLocaleString();
        const testRunId = result.test_run_id || '-';
        const shortRunId = testRunId.length > 16 ? testRunId.substring(0, 8) + '...' : testRunId;
        const dbType = result.database?.type || 'unknown';
        const dbVersion = result.database?.version || 'unknown';
        // Build detailed version tooltip for DocumentDB
        let versionDisplay = dbVersion;
        let versionTooltip = dbVersion;
        if ((dbType === 'documentdb' || dbType === 'documentdb-azure') && result.database) {
            const parts = [];
            if (result.database.documentdb_version) parts.push(`DocumentDB: ${result.database.documentdb_version}`);
            if (result.database.wire_protocol_version) parts.push(`Wire Protocol: ${result.database.wire_protocol_version}`);
            if (result.database.postgres_version) parts.push(`PostgreSQL: ${result.database.postgres_version}`);
            if (parts.length > 0) {
                versionTooltip = parts.join(' | ');
                versionDisplay = result.database.documentdb_version || dbVersion;
            }
        }
        const testType = result.test_config?.test_type || 'unknown';
        const payloadSize = result.test_config?.payload_size || 0;
        const insertTime = result.results?.insert_time_ms || '-';
        const insertThroughput = result.results?.insert_throughput || '-';
        const queryTime = result.results?.query_time_ms || '-';

        // Build latency display for cloud databases
        let latencyDisplay = '-';
        const latencyMetrics = result.latency_metrics;
        if (latencyMetrics) {
            const insertLatency = latencyMetrics.insert_multi_attr || latencyMetrics.insert_single_attr;
            if (insertLatency) {
                latencyDisplay = `${insertLatency.p50_ms?.toFixed(1) || '-'}/${insertLatency.p99_ms?.toFixed(1) || '-'}`;
            }
        }

        // Resource metrics (graceful degradation for missing data)
        const rm = result.resource_metrics;
        const avgCpu = fmtMetric(rm?.avg_cpu_percent);
        const peakCpu = fmtMetric(rm?.max_cpu_percent);
        const diskIops = fmtMetric(rm?.avg_disk_iops, 0);
        const ioWait = fmtMetric(rm?.avg_iowait_percent);

        const naCell = (val) => val !== null ? `<td>${val}</td>` : '<td class="metric-na">N/A</td>';

        row.innerHTML = `
            <td>${timestamp}</td>
            <td title="${testRunId}">${shortRunId}</td>
            <td>${dbType}</td>
            <td title="${versionTooltip}">${versionDisplay}</td>
            <td>${testType}</td>
            <td>${payloadSize}B</td>
            <td>${insertTime}</td>
            <td>${insertThroughput}</td>
            <td>${queryTime}</td>
            <td>${latencyDisplay}</td>
            ${naCell(avgCpu)}
            ${naCell(peakCpu)}
            ${naCell(diskIops)}
            ${naCell(ioWait)}
        `;
        tbody.appendChild(row);
    });
}

// --- Detail Modal (drill-down view) ---

function showDetailModal(result) {
    const modal = document.getElementById('detail-modal');
    const title = document.getElementById('modal-title');
    const dbType = result.database?.type || 'unknown';
    const dbVersion = result.database?.version || '';
    title.textContent = `${dbType} ${dbVersion} - Test Result Details`;

    // Test Configuration
    populateDetailGrid('detail-test-config', [
        ['Test Type', result.test_config?.test_type],
        ['Payload Size', result.test_config?.payload_size != null ? result.test_config.payload_size + 'B' : null],
        ['Num Documents', result.test_config?.num_docs],
        ['Batch Size', result.test_config?.batch_size],
        ['Num Runs', result.test_config?.num_runs],
        ['Num Attributes', result.test_config?.num_attributes],
        ['Indexed', result.test_config?.indexed != null ? String(result.test_config.indexed) : null],
        ['Query Test', result.test_config?.query_test != null ? String(result.test_config.query_test) : null],
        ['Query Links', result.test_config?.query_links],
    ]);

    // Performance Results
    populateDetailGrid('detail-results', [
        ['Insert Time', result.results?.insert_time_ms != null ? result.results.insert_time_ms + ' ms' : null],
        ['Insert Throughput', result.results?.insert_throughput != null ? Math.round(result.results.insert_throughput) + ' docs/sec' : null],
        ['Query Time', result.results?.query_time_ms != null ? result.results.query_time_ms + ' ms' : null],
        ['Query Throughput', result.results?.query_throughput != null ? Math.round(result.results.query_throughput) + ' queries/sec' : null],
        ['Success', result.results?.success != null ? String(result.results.success) : null],
        ['Error', result.results?.error],
    ]);

    // System Information
    const si = result.system_info;
    populateDetailGrid('detail-system-info', [
        ['CPU Model', si?.cpu?.model],
        ['CPU Cores', si?.cpu?.cores],
        ['CPU Threads', si?.cpu?.threads],
        ['Memory (Total)', si?.memory?.total_gb != null ? si.memory.total_gb.toFixed(1) + ' GB' : null],
        ['Memory (Available)', si?.memory?.available_gb != null ? si.memory.available_gb.toFixed(1) + ' GB' : null],
        ['OS', si?.os?.name],
        ['OS Version', si?.os?.version],
        ['Kernel', si?.os?.kernel],
        ['Hostname', si?.hostname],
        ['Java Version', si?.java_version],
    ]);

    // Resource Metrics
    const rm = result.resource_metrics;
    populateDetailGrid('detail-resource-metrics', [
        ['Avg CPU %', fmtMetric(rm?.avg_cpu_percent)],
        ['Peak CPU %', fmtMetric(rm?.max_cpu_percent)],
        ['Avg I/O Wait %', fmtMetric(rm?.avg_iowait_percent)],
        ['Avg Disk IOPS', fmtMetric(rm?.avg_disk_iops, 0)],
        ['Max Disk IOPS', fmtMetric(rm?.max_disk_iops, 0)],
        ['Samples', rm?.samples],
    ]);

    // CI Information
    const ci = result.ci_info;
    populateDetailGrid('detail-ci-info', [
        ['CI Run', ci?.ci_run != null ? String(ci.ci_run) : null],
        ['CI Platform', ci?.ci_platform],
        ['Commit Hash', ci?.commit_hash],
        ['Branch', ci?.branch],
    ]);

    modal.style.display = 'flex';
}

function populateDetailGrid(elementId, items) {
    const container = document.getElementById(elementId);
    container.innerHTML = '';
    let hasAnyData = false;
    items.forEach(([label, value]) => {
        const div = document.createElement('div');
        div.className = 'detail-item';
        const isNA = value == null || value === undefined || value === '';
        if (!isNA) hasAnyData = true;
        div.innerHTML = `
            <span class="detail-label">${label}</span>
            <span class="detail-value${isNA ? ' na' : ''}">${isNA ? 'N/A' : value}</span>
        `;
        container.appendChild(div);
    });
    // Show notice if all values are N/A
    if (!hasAnyData) {
        container.innerHTML = '<div class="detail-item"><span class="detail-value na">No data available</span></div>';
    }
}

function closeDetailModal() {
    document.getElementById('detail-modal').style.display = 'none';
}

// --- Resource Utilization Comparison ---

function updateResourceComparison(results) {
    const section = document.getElementById('resource-comparison-section');

    // Check if any results have resource metrics
    const resultsWithMetrics = results.filter(r =>
        r.resource_metrics && (r.resource_metrics.avg_cpu_percent != null || r.resource_metrics.avg_disk_iops != null)
    );

    if (resultsWithMetrics.length === 0) {
        section.style.display = 'none';
        return;
    }

    // Group by database type, averaging resource metrics
    const byDbType = {};
    resultsWithMetrics.forEach(r => {
        const dbType = r.database?.type || 'unknown';
        if (!byDbType[dbType]) {
            byDbType[dbType] = { avgCpu: [], peakCpu: [], avgIops: [], maxIops: [], ioWait: [] };
        }
        const rm = r.resource_metrics;
        if (rm.avg_cpu_percent != null) byDbType[dbType].avgCpu.push(rm.avg_cpu_percent);
        if (rm.max_cpu_percent != null) byDbType[dbType].peakCpu.push(rm.max_cpu_percent);
        if (rm.avg_disk_iops != null) byDbType[dbType].avgIops.push(rm.avg_disk_iops);
        if (rm.max_disk_iops != null) byDbType[dbType].maxIops.push(rm.max_disk_iops);
        if (rm.avg_iowait_percent != null) byDbType[dbType].ioWait.push(rm.avg_iowait_percent);
    });

    const dbTypes = Object.keys(byDbType).sort();
    if (dbTypes.length < 1) {
        section.style.display = 'none';
        return;
    }

    section.style.display = '';

    const avg = arr => arr.length ? arr.reduce((a, b) => a + b, 0) / arr.length : 0;

    const labels = dbTypes;
    const colors = dbTypes.map(t => getColorForDatabaseType(t));

    // CPU Chart (avg + peak as grouped bar)
    const cpuCtx = document.getElementById('resource-cpu-chart').getContext('2d');
    if (resourceCpuChart) resourceCpuChart.destroy();
    resourceCpuChart = new Chart(cpuCtx, {
        type: 'bar',
        data: {
            labels,
            datasets: [
                {
                    label: 'Avg CPU %',
                    data: dbTypes.map(t => +avg(byDbType[t].avgCpu).toFixed(1)),
                    backgroundColor: colors.map(c => c + 'CC'),
                    borderColor: colors,
                    borderWidth: 1,
                },
                {
                    label: 'Peak CPU %',
                    data: dbTypes.map(t => +avg(byDbType[t].peakCpu).toFixed(1)),
                    backgroundColor: colors.map(c => c + '66'),
                    borderColor: colors,
                    borderWidth: 1,
                },
                {
                    label: 'I/O Wait %',
                    data: dbTypes.map(t => +avg(byDbType[t].ioWait).toFixed(2)),
                    backgroundColor: dbTypes.map(() => '#ff6384AA'),
                    borderColor: dbTypes.map(() => '#ff6384'),
                    borderWidth: 1,
                },
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: { title: { display: true, text: 'CPU & I/O Wait by Database' } },
            scales: {
                y: { beginAtZero: true, title: { display: true, text: 'Percentage (%)' } }
            }
        }
    });

    // IOPS Chart
    const iopsCtx = document.getElementById('resource-iops-chart').getContext('2d');
    if (resourceIopsChart) resourceIopsChart.destroy();
    resourceIopsChart = new Chart(iopsCtx, {
        type: 'bar',
        data: {
            labels,
            datasets: [
                {
                    label: 'Avg Disk IOPS',
                    data: dbTypes.map(t => +avg(byDbType[t].avgIops).toFixed(0)),
                    backgroundColor: colors.map(c => c + 'CC'),
                    borderColor: colors,
                    borderWidth: 1,
                },
                {
                    label: 'Max Disk IOPS',
                    data: dbTypes.map(t => +avg(byDbType[t].maxIops).toFixed(0)),
                    backgroundColor: colors.map(c => c + '66'),
                    borderColor: colors,
                    borderWidth: 1,
                },
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: { title: { display: true, text: 'Disk IOPS by Database' } },
            scales: {
                y: { beginAtZero: true, title: { display: true, text: 'IOPS' } }
            }
        }
    });
}

// Color mapping for database types
function getColorForDatabaseType(dbType) {
    const colorMap = {
        'mongodb': '#667eea',
        'documentdb': '#764ba2',
        'postgresql': '#f093fb',
        'yugabytedb': '#43a047',
        'cockroachdb': '#ff9800',
        'oracle': '#4facfe',
        'oracle23ai': '#00d2ff',
        'mongodb-cloud': '#2ecc71',
        'documentdb-azure': '#e67e22',
        'unknown': '#95a5a6'
    };
    return colorMap[dbType?.toLowerCase()] || colorMap['unknown'];
}

// Helper function to sort payload sizes and align data
function sortAndAlignData(groups, payloadKey, dataKey) {
    // Collect all unique payload sizes
    const allPayloadSizes = new Set();
    Object.values(groups).forEach(group => {
        (group[payloadKey] || []).forEach(size => allPayloadSizes.add(size));
    });

    // Sort payload sizes numerically
    const sortedPayloadSizes = Array.from(allPayloadSizes).sort((a, b) => a - b);

    // Create labels
    const labels = sortedPayloadSizes.map(s => `${s}B`);

    // Align data for each group
    const alignedDatasets = Object.values(groups).map((group) => {
        const payloadArray = group[payloadKey] || [];
        const dataArray = group[dataKey] || [];
        const dbType = group.dbType || 'unknown';
        const color = getColorForDatabaseType(dbType);

        // Create a map of payload size to array of data values (to handle multiple values per size)
        const dataMap = new Map();
        payloadArray.forEach((size, idx) => {
            if (!dataMap.has(size)) {
                dataMap.set(size, []);
            }
            if (dataArray[idx] != null && dataArray[idx] !== undefined) {
                dataMap.get(size).push(dataArray[idx]);
            }
        });

        // Create aligned data array - average multiple values for the same payload size
        const alignedData = sortedPayloadSizes.map(size => {
            const values = dataMap.get(size);
            if (!values || values.length === 0) {
                return null;
            }
            // Average multiple values for the same payload size
            const sum = values.reduce((a, b) => a + b, 0);
            return sum / values.length;
        });

        const dataset = {
            label: group.label,
            data: alignedData,
            backgroundColor: color,
            borderColor: color,
            borderWidth: 2
        };

        console.log(`Creating dataset for ${dataKey}:`, {
            label: dataset.label,
            dbType: dbType,
            color: color,
            dataPoints: alignedData.filter(d => d !== null).length,
            totalDataPoints: alignedData.length
        });

        return dataset;
    });

    console.log(`Created ${alignedDatasets.length} datasets for ${dataKey}`);
    return { labels, datasets: alignedDatasets };
}

function updateCharts(results) {
    // Filter successful results
    const successful = results.filter(r => r.results?.success);
    console.log(`Updating charts with ${successful.length} successful results out of ${results.length} total`);

    // Debug: Check mongodb vs documentdb results
    const mongodbResults = successful.filter(r => r.database?.type?.toLowerCase() === 'mongodb');
    const documentdbResults = successful.filter(r => r.database?.type?.toLowerCase() === 'documentdb');
    console.log(`MongoDB results: ${mongodbResults.length}, DocumentDB results: ${documentdbResults.length}`);

    // Check test_run_id for mongodb results
    if (mongodbResults.length > 0) {
        const mongodbTestRunIds = new Set(mongodbResults.map(r => r.test_run_id || 'missing'));
        console.log(`MongoDB test_run_ids:`, Array.from(mongodbTestRunIds));
        console.log(`Sample MongoDB result:`, {
            test_run_id: mongodbResults[0].test_run_id,
            hasInsertTime: !!mongodbResults[0].results?.insert_time_ms,
            hasQueryTime: !!mongodbResults[0].results?.query_time_ms,
            hasThroughput: !!mongodbResults[0].results?.insert_throughput
        });
    }

    // Group by test_run_id AND database type (since same test_run_id can have different db types)
    const grouped = {};
    const dbTypesSeen = new Set();
    const dbTypeCounts = {};
    successful.forEach(result => {
        const testRunId = result.test_run_id || 'unknown';
        const dbType = result.database?.type || 'unknown';
        // Include database type in the key to separate MongoDB and DocumentDB results with same test_run_id
        const key = `${testRunId}-${dbType}`;
        dbTypesSeen.add(dbType);

        // Count results by database type
        if (!dbTypeCounts[dbType]) {
            dbTypeCounts[dbType] = { total: 0, withInsertTime: 0, withQueryTime: 0, withThroughput: 0 };
        }
        dbTypeCounts[dbType].total++;
        if (result.results?.insert_time_ms) dbTypeCounts[dbType].withInsertTime++;
        if (result.results?.query_time_ms) dbTypeCounts[dbType].withQueryTime++;
        if (result.results?.insert_throughput) dbTypeCounts[dbType].withThroughput++;

        if (!grouped[key]) {
            // Create a descriptive label with test_run_id and database info
            const dbVersion = result.database?.version || 'unknown';
            const label = `${testRunId} (${dbType}-${dbVersion})`;
            grouped[key] = {
                label: label,
                dbType: dbType,
                insertTimes: [],
                queryTimes: [],
                throughputs: [],
                payloadSizes: [],
                queryPayloadSizes: [],
                throughputPayloadSizes: []
            };
        }

        if (result.results?.insert_time_ms) {
            grouped[key].insertTimes.push(result.results.insert_time_ms);
            grouped[key].payloadSizes.push(result.test_config?.payload_size || 0);
        }

        if (result.results?.query_time_ms) {
            grouped[key].queryTimes.push(result.results.query_time_ms);
            grouped[key].queryPayloadSizes = grouped[key].queryPayloadSizes || [];
            grouped[key].queryPayloadSizes.push(result.test_config?.payload_size || 0);
        }

        if (result.results?.insert_throughput) {
            grouped[key].throughputs.push(result.results.insert_throughput);
            // Track payload size for throughputs (use same as insert if available, otherwise track separately)
            if (!grouped[key].throughputPayloadSizes) {
                grouped[key].throughputPayloadSizes = [];
            }
            grouped[key].throughputPayloadSizes.push(result.test_config?.payload_size || 0);
        }
    });

    console.log(`Database types found in results:`, Array.from(dbTypesSeen));
    console.log('Database type counts:', dbTypeCounts);
    console.log(`Number of test runs (groups): ${Object.keys(grouped).length}`);
    console.log('Grouped data:', Object.keys(grouped).map(key => ({
        key,
        label: grouped[key].label,
        dbType: grouped[key].dbType,
        insertCount: grouped[key].insertTimes.length,
        queryCount: grouped[key].queryTimes.length
    })));

    // Check if mongodb results are being grouped
    const mongodbGroups = Object.values(grouped).filter(g => g.dbType.toLowerCase() === 'mongodb');
    const documentdbGroups = Object.values(grouped).filter(g => g.dbType.toLowerCase() === 'documentdb');
    console.log(`MongoDB groups: ${mongodbGroups.length}, DocumentDB groups: ${documentdbGroups.length}`);

    // Update insertion chart
    updateInsertionChart(grouped);

    // Update query chart
    updateQueryChart(grouped);

    // Update throughput chart
    updateThroughputChart(grouped);

    // Update latency charts (only for cloud database results)
    updateLatencyCharts(results);
}

function updateInsertionChart(grouped) {
    const ctx = document.getElementById('insertion-chart').getContext('2d');

    if (insertionChart) {
        insertionChart.destroy();
    }

    const { labels, datasets } = sortAndAlignData(grouped, 'payloadSizes', 'insertTimes');

    insertionChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Time (ms)'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Payload Size'
                    }
                }
            }
        }
    });
}

function updateQueryChart(grouped) {
    const ctx = document.getElementById('query-chart').getContext('2d');

    if (queryChart) {
        queryChart.destroy();
    }

    // Use queryPayloadSizes if available, otherwise fall back to payloadSizes
    const payloadKey = Object.values(grouped).some(g => g.queryPayloadSizes?.length > 0)
        ? 'queryPayloadSizes'
        : 'payloadSizes';

    const { labels, datasets } = sortAndAlignData(grouped, payloadKey, 'queryTimes');

    // Add fill: false to datasets for line chart styling
    datasets.forEach(dataset => {
        dataset.fill = false;
    });

    queryChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Query Time (ms)'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Payload Size'
                    }
                }
            }
        }
    });
}

function updateThroughputChart(grouped) {
    const ctx = document.getElementById('throughput-chart').getContext('2d');

    if (throughputChart) {
        throughputChart.destroy();
    }

    // Use throughputPayloadSizes if available, otherwise fall back to payloadSizes
    const payloadKey = Object.values(grouped).some(g => g.throughputPayloadSizes?.length > 0)
        ? 'throughputPayloadSizes'
        : 'payloadSizes';

    const { labels, datasets } = sortAndAlignData(grouped, payloadKey, 'throughputs');

    throughputChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Throughput (docs/sec)'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Payload Size'
                    }
                }
            }
        }
    });
}

function setupEventListeners() {
    document.getElementById('apply-filters').addEventListener('click', loadResults);
    document.getElementById('export-data').addEventListener('click', exportData);

    // Modal close handlers
    document.getElementById('modal-close').addEventListener('click', closeDetailModal);
    document.getElementById('detail-modal').addEventListener('click', (e) => {
        if (e.target === e.currentTarget) closeDetailModal();
    });
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeDetailModal();
    });
}

async function exportData() {
    try {
        const filters = getFilters();
        const queryParams = new URLSearchParams();

        if (filters.database_type) queryParams.append('database_type', filters.database_type);
        if (filters.database_version) queryParams.append('database_version', filters.database_version);
        if (filters.test_run_id) queryParams.append('test_run_id', filters.test_run_id);
        if (filters.start_date) queryParams.append('start_date', filters.start_date);
        if (filters.end_date) queryParams.append('end_date', filters.end_date);
        queryParams.append('limit', '10000'); // Get more for export

        const response = await fetch(`${API_BASE}?${queryParams}`);
        const data = await response.json();

        // Convert to CSV
        const csv = convertToCSV(data.results);
        downloadCSV(csv, 'benchmark_results.csv');
    } catch (error) {
        console.error('Error exporting data:', error);
        showError('Failed to export data: ' + error.message);
    }
}

function convertToCSV(results) {
    const headers = [
        'Timestamp', 'Test Run ID', 'Database Type', 'Database Version',
        'DocumentDB Version', 'Wire Protocol Version', 'PostgreSQL Version',
        'Test Type', 'Payload Size', 'Insert Time (ms)', 'Insert Throughput',
        'Query Time (ms)', 'Avg CPU %', 'Peak CPU %', 'Avg Disk IOPS',
        'I/O Wait %', 'CPU Model', 'CPU Cores', 'Memory (GB)', 'OS'
    ];
    const rows = results.map(r => [
        new Date(r.timestamp).toISOString(),
        r.test_run_id || '',
        r.database?.type || '',
        r.database?.version || '',
        r.database?.documentdb_version || '',
        r.database?.wire_protocol_version || '',
        r.database?.postgres_version || '',
        r.test_config?.test_type || '',
        r.test_config?.payload_size || '',
        r.results?.insert_time_ms || '',
        r.results?.insert_throughput || '',
        r.results?.query_time_ms || '',
        r.resource_metrics?.avg_cpu_percent ?? '',
        r.resource_metrics?.max_cpu_percent ?? '',
        r.resource_metrics?.avg_disk_iops ?? '',
        r.resource_metrics?.avg_iowait_percent ?? '',
        (r.system_info?.cpu?.model || '').replace(/,/g, ' '),
        r.system_info?.cpu?.cores ?? '',
        r.system_info?.memory?.total_gb ?? '',
        (r.system_info?.os?.name || '').replace(/,/g, ' ')
    ]);

    return [headers, ...rows].map(row => row.join(',')).join('\n');
}

function downloadCSV(csv, filename) {
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    window.URL.revokeObjectURL(url);
}

function isCloudDbType(dbType) {
    return CLOUD_DB_TYPES.includes(dbType?.toLowerCase());
}

function updateLatencyCharts(results) {
    // Filter to cloud database results that have latency metrics
    const cloudResults = results.filter(r =>
        r.results?.success &&
        isCloudDbType(r.database?.type) &&
        r.latency_metrics
    );

    const latencySection = document.getElementById('latency-section');
    if (cloudResults.length === 0) {
        latencySection.style.display = 'none';
        return;
    }
    latencySection.style.display = 'block';

    updateLatencyPercentileChart(cloudResults);
    updateLatencyTimelineChart(cloudResults);
}

function updateLatencyPercentileChart(cloudResults) {
    const ctx = document.getElementById('latency-percentile-chart').getContext('2d');
    if (latencyPercentileChart) {
        latencyPercentileChart.destroy();
    }

    // Group by database type
    const byDb = {};
    cloudResults.forEach(r => {
        const dbType = r.database?.type || 'unknown';
        if (!byDb[dbType]) byDb[dbType] = [];
        const insertMetrics = r.latency_metrics?.insert_multi_attr || r.latency_metrics?.insert_single_attr;
        if (insertMetrics) {
            byDb[dbType].push(insertMetrics);
        }
    });

    const labels = ['Min', 'p50', 'p95', 'p99', 'Max'];
    const datasets = Object.entries(byDb).map(([dbType, metricsList]) => {
        // Average across all test results for this db type
        const avg = (arr, key) => arr.reduce((s, m) => s + (m[key] || 0), 0) / arr.length;
        const color = getColorForDatabaseType(dbType);
        return {
            label: dbType,
            data: [
                avg(metricsList, 'min_ms'),
                avg(metricsList, 'p50_ms'),
                avg(metricsList, 'p95_ms'),
                avg(metricsList, 'p99_ms'),
                avg(metricsList, 'max_ms')
            ],
            backgroundColor: color + '80',
            borderColor: color,
            borderWidth: 2
        };
    });

    latencyPercentileChart = new Chart(ctx, {
        type: 'bar',
        data: { labels, datasets },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            scales: {
                y: {
                    beginAtZero: true,
                    title: { display: true, text: 'Latency (ms)' }
                }
            }
        }
    });
}

function updateLatencyTimelineChart(cloudResults) {
    const ctx = document.getElementById('latency-timeline-chart').getContext('2d');
    if (latencyTimelineChart) {
        latencyTimelineChart.destroy();
    }

    // Pick the most recent result per cloud db type that has samples
    const byDb = {};
    cloudResults.forEach(r => {
        const dbType = r.database?.type || 'unknown';
        const insertMetrics = r.latency_metrics?.insert_multi_attr || r.latency_metrics?.insert_single_attr;
        if (insertMetrics?.samples?.length > 0) {
            // Keep most recent (results are sorted by timestamp desc)
            if (!byDb[dbType]) {
                byDb[dbType] = insertMetrics.samples;
            }
        }
    });

    if (Object.keys(byDb).length === 0) {
        return;
    }

    // Find the max number of samples across all db types
    const maxSamples = Math.max(...Object.values(byDb).map(s => s.length));
    const labels = Array.from({ length: maxSamples }, (_, i) => `Batch ${i + 1}`);

    const datasets = Object.entries(byDb).map(([dbType, samples]) => {
        const color = getColorForDatabaseType(dbType);
        return {
            label: dbType,
            data: samples,
            borderColor: color,
            backgroundColor: color + '20',
            borderWidth: 1.5,
            pointRadius: 0,
            fill: true,
            tension: 0.1
        };
    });

    latencyTimelineChart = new Chart(ctx, {
        type: 'line',
        data: { labels, datasets },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            scales: {
                y: {
                    beginAtZero: true,
                    title: { display: true, text: 'Batch Latency (ms)' }
                },
                x: {
                    title: { display: true, text: 'Batch Number' },
                    ticks: {
                        maxTicksLimit: 20
                    }
                }
            },
            plugins: {
                tooltip: {
                    callbacks: {
                        label: (context) => `${context.dataset.label}: ${context.parsed.y?.toFixed(2)}ms`
                    }
                }
            }
        }
    });
}

function showError(message) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error';
    errorDiv.textContent = message;
    document.querySelector('.container').insertBefore(errorDiv, document.querySelector('.filters'));
    setTimeout(() => errorDiv.remove(), 5000);
}
