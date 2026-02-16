/**
 * Main application JavaScript
 */

const API_BASE = '/api/results';

let insertionChart = null;
let queryChart = null;
let throughputChart = null;

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
        
        updateTable(allResults);
        updateCharts(allResults);
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

function updateTable(results) {
    const tbody = document.getElementById('results-tbody');
    tbody.innerHTML = '';
    
    if (results.length === 0) {
        tbody.innerHTML = '<tr><td colspan="9" class="loading">No results found</td></tr>';
        return;
    }

    results.forEach(result => {
        const row = document.createElement('tr');
        const timestamp = new Date(result.timestamp).toLocaleString();
        const testRunId = result.test_run_id || '-';
        const shortRunId = testRunId.length > 16 ? testRunId.substring(0, 8) + '...' : testRunId;
        const dbType = result.database?.type || 'unknown';
        const dbVersion = result.database?.version || 'unknown';
        const testType = result.test_config?.test_type || 'unknown';
        const payloadSize = result.test_config?.payload_size || 0;
        const insertTime = result.results?.insert_time_ms || '-';
        const insertThroughput = result.results?.insert_throughput || '-';
        const queryTime = result.results?.query_time_ms || '-';

        row.innerHTML = `
            <td>${timestamp}</td>
            <td title="${testRunId}">${shortRunId}</td>
            <td>${dbType}</td>
            <td>${dbVersion}</td>
            <td>${testType}</td>
            <td>${payloadSize}B</td>
            <td>${insertTime}</td>
            <td>${insertThroughput}</td>
            <td>${queryTime}</td>
        `;
        tbody.appendChild(row);
    });
}

// Color mapping for database types
function getColorForDatabaseType(dbType) {
    const colorMap = {
        'mongodb': '#667eea',
        'documentdb': '#764ba2',
        'postgresql': '#f093fb',
        'oracle': '#4facfe',
        'oracle23ai': '#00d2ff',
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
    const headers = ['Timestamp', 'Test Run ID', 'Database Type', 'Database Version', 'Test Type', 'Payload Size', 'Insert Time (ms)', 'Insert Throughput', 'Query Time (ms)'];
    const rows = results.map(r => [
        new Date(r.timestamp).toISOString(),
        r.test_run_id || '',
        r.database?.type || '',
        r.database?.version || '',
        r.test_config?.test_type || '',
        r.test_config?.payload_size || '',
        r.results?.insert_time_ms || '',
        r.results?.insert_throughput || '',
        r.results?.query_time_ms || ''
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

function showError(message) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error';
    errorDiv.textContent = message;
    document.querySelector('.container').insertBefore(errorDiv, document.querySelector('.filters'));
    setTimeout(() => errorDiv.remove(), 5000);
}
