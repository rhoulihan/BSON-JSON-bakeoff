#!/usr/bin/env python3
"""
Generate HTML benchmark report from article_benchmark_results.json
Simple, reliable script using string templates.
"""

import json
import os
from datetime import datetime

def load_data(filename='article_benchmark_results.json'):
    """Load benchmark results."""
    with open(filename, 'r') as f:
        return json.load(f)

def extract_data(data):
    """Extract and organize all benchmark data."""
    single = data['single_attribute']
    multi = data['multi_attribute']

    # Extract all data arrays
    extracted = {
        # Single-attribute times
        'mongo_single_time': [r['time_ms'] for r in single['mongodb']],
        'oracle_no_single_time': [r['time_ms'] for r in single['oracle_no_index']],
        'oracle_idx_single_time': [r['time_ms'] for r in single['oracle_with_index']],
        'pg_json_single_time': [r['time_ms'] for r in single['postgresql_json']],
        'pg_jsonb_single_time': [r['time_ms'] for r in single['postgresql_jsonb']],

        # Single-attribute throughput
        'mongo_single_tput': [int(r['throughput']) for r in single['mongodb']],
        'oracle_no_single_tput': [int(r['throughput']) for r in single['oracle_no_index']],
        'oracle_idx_single_tput': [int(r['throughput']) for r in single['oracle_with_index']],
        'pg_json_single_tput': [int(r['throughput']) for r in single['postgresql_json']],
        'pg_jsonb_single_tput': [int(r['throughput']) for r in single['postgresql_jsonb']],

        # Multi-attribute times
        'mongo_multi_time': [r['time_ms'] for r in multi['mongodb']],
        'oracle_no_multi_time': [r['time_ms'] for r in multi['oracle_no_index']],
        'oracle_idx_multi_time': [r['time_ms'] for r in multi['oracle_with_index']],
        'pg_json_multi_time': [r['time_ms'] for r in multi['postgresql_json']],
        'pg_jsonb_multi_time': [r['time_ms'] for r in multi['postgresql_jsonb']],

        # Multi-attribute throughput
        'mongo_multi_tput': [int(r['throughput']) for r in multi['mongodb']],
        'oracle_no_multi_tput': [int(r['throughput']) for r in multi['oracle_no_index']],
        'oracle_idx_multi_tput': [int(r['throughput']) for r in multi['oracle_with_index']],
        'pg_json_multi_tput': [int(r['throughput']) for r in multi['postgresql_json']],
        'pg_jsonb_multi_tput': [int(r['throughput']) for r in multi['postgresql_jsonb']],
    }

    # Calculate degradation
    extracted['mongo_single_deg'] = round(extracted['mongo_single_time'][-1] / extracted['mongo_single_time'][0], 2)
    extracted['oracle_idx_single_deg'] = round(extracted['oracle_idx_single_time'][-1] / extracted['oracle_idx_single_time'][0], 2)
    extracted['pg_json_single_deg'] = round(extracted['pg_json_single_time'][-1] / extracted['pg_json_single_time'][0], 2)
    extracted['pg_jsonb_single_deg'] = round(extracted['pg_jsonb_single_time'][-1] / extracted['pg_jsonb_single_time'][0], 2)

    extracted['mongo_multi_deg'] = round(extracted['mongo_multi_time'][-1] / extracted['mongo_multi_time'][0], 2)
    extracted['oracle_idx_multi_deg'] = round(extracted['oracle_idx_multi_time'][-1] / extracted['oracle_idx_multi_time'][0], 2)
    extracted['pg_json_multi_deg'] = round(extracted['pg_json_multi_time'][-1] / extracted['pg_json_multi_time'][0], 2)
    extracted['pg_jsonb_multi_deg'] = round(extracted['pg_jsonb_multi_time'][-1] / extracted['pg_jsonb_multi_time'][0], 2)

    return extracted

def build_charts_js(d):
    """Build the JavaScript charts code with actual data."""
    return '''
        // Benchmark data
        const benchmarkData = {
            singleTime: {
                mongo: ''' + str(d['mongo_single_time']) + ''',
                oracleNo: ''' + str(d['oracle_no_single_time']) + ''',
                oracleIdx: ''' + str(d['oracle_idx_single_time']) + ''',
                pgJson: ''' + str(d['pg_json_single_time']) + ''',
                pgJsonb: ''' + str(d['pg_jsonb_single_time']) + '''
            },
            singleTput: {
                mongo: ''' + str(d['mongo_single_tput']) + ''',
                oracleNo: ''' + str(d['oracle_no_single_tput']) + ''',
                oracleIdx: ''' + str(d['oracle_idx_single_tput']) + ''',
                pgJson: ''' + str(d['pg_json_single_tput']) + ''',
                pgJsonb: ''' + str(d['pg_jsonb_single_tput']) + '''
            },
            multiTime: {
                mongo: ''' + str(d['mongo_multi_time']) + ''',
                oracleNo: ''' + str(d['oracle_no_multi_time']) + ''',
                oracleIdx: ''' + str(d['oracle_idx_multi_time']) + ''',
                pgJson: ''' + str(d['pg_json_multi_time']) + ''',
                pgJsonb: ''' + str(d['pg_jsonb_multi_time']) + '''
            },
            multiTput: {
                mongo: ''' + str(d['mongo_multi_tput']) + ''',
                oracleNo: ''' + str(d['oracle_no_multi_tput']) + ''',
                oracleIdx: ''' + str(d['oracle_idx_multi_tput']) + ''',
                pgJson: ''' + str(d['pg_json_multi_tput']) + ''',
                pgJsonb: ''' + str(d['pg_jsonb_multi_tput']) + '''
            },
            degradation: {
                mongo: [''' + str(d['mongo_single_deg']) + ''', ''' + str(d['mongo_multi_deg']) + '''],
                oracleIdx: [''' + str(d['oracle_idx_single_deg']) + ''', ''' + str(d['oracle_idx_multi_deg']) + '''],
                pgJson: [''' + str(d['pg_json_single_deg']) + ''', ''' + str(d['pg_json_multi_deg']) + '''],
                pgJsonb: [''' + str(d['pg_jsonb_single_deg']) + ''', ''' + str(d['pg_jsonb_multi_deg']) + ''']
            }
        };

        // Color scheme
        const colors = {
            mongodb: { line: 'rgb(0, 237, 100)', fill: 'rgba(0, 237, 100, 0.1)' },
            oracle_no: { line: 'rgb(255, 99, 71)', fill: 'rgba(255, 99, 71, 0.1)' },
            oracle_idx: { line: 'rgb(220, 20, 60)', fill: 'rgba(220, 20, 60, 0.1)' },
            pg_json: { line: 'rgb(70, 130, 180)', fill: 'rgba(70, 130, 180, 0.1)' },
            pg_jsonb: { line: 'rgb(0, 0, 139)', fill: 'rgba(0, 0, 139, 0.1)' }
        };

        // Chart options
        const chartOptions = {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend: { display: true, position: 'top' },
                tooltip: { mode: 'index', intersect: false }
            }
        };

        // Single-Attribute Time Chart
        new Chart(document.getElementById('singleTimeChart'), {
            type: 'line',
            data: {
                labels: [10, 200, 1000, 2000, 4000],
                datasets: [
                    { label: 'MongoDB BSON', data: benchmarkData.singleTime.mongo, borderColor: colors.mongodb.line, backgroundColor: colors.mongodb.fill, borderWidth: 3, tension: 0.4, fill: true },
                    { label: 'Oracle JCT (no index)', data: benchmarkData.singleTime.oracleNo, borderColor: colors.oracle_no.line, backgroundColor: colors.oracle_no.fill, borderWidth: 3, tension: 0.4, fill: true },
                    { label: 'Oracle JCT (with index)', data: benchmarkData.singleTime.oracleIdx, borderColor: colors.oracle_idx.line, backgroundColor: colors.oracle_idx.fill, borderWidth: 3, tension: 0.4, fill: true },
                    { label: 'PostgreSQL JSON', data: benchmarkData.singleTime.pgJson, borderColor: colors.pg_json.line, backgroundColor: colors.pg_json.fill, borderWidth: 3, tension: 0.4, fill: true },
                    { label: 'PostgreSQL JSONB', data: benchmarkData.singleTime.pgJsonb, borderColor: colors.pg_jsonb.line, backgroundColor: colors.pg_jsonb.fill, borderWidth: 3, tension: 0.4, fill: true }
                ]
            },
            options: { ...chartOptions, scales: { y: { title: { display: true, text: 'Time (ms)' }, beginAtZero: true }, x: { title: { display: true, text: 'Document Size (bytes)' } } } }
        });

        // Single-Attribute Throughput Chart
        new Chart(document.getElementById('singleTputChart'), {
            type: 'line',
            data: {
                labels: [10, 200, 1000, 2000, 4000],
                datasets: [
                    { label: 'MongoDB BSON', data: benchmarkData.singleTput.mongo, borderColor: colors.mongodb.line, backgroundColor: colors.mongodb.fill, borderWidth: 3, tension: 0.4, fill: true },
                    { label: 'Oracle JCT (no index)', data: benchmarkData.singleTput.oracleNo, borderColor: colors.oracle_no.line, backgroundColor: colors.oracle_no.fill, borderWidth: 3, tension: 0.4, fill: true },
                    { label: 'Oracle JCT (with index)', data: benchmarkData.singleTput.oracleIdx, borderColor: colors.oracle_idx.line, backgroundColor: colors.oracle_idx.fill, borderWidth: 3, tension: 0.4, fill: true },
                    { label: 'PostgreSQL JSON', data: benchmarkData.singleTput.pgJson, borderColor: colors.pg_json.line, backgroundColor: colors.pg_json.fill, borderWidth: 3, tension: 0.4, fill: true },
                    { label: 'PostgreSQL JSONB', data: benchmarkData.singleTput.pgJsonb, borderColor: colors.pg_jsonb.line, backgroundColor: colors.pg_jsonb.fill, borderWidth: 3, tension: 0.4, fill: true }
                ]
            },
            options: { ...chartOptions, scales: { y: { title: { display: true, text: 'Throughput (docs/sec)' }, beginAtZero: true }, x: { title: { display: true, text: 'Document Size (bytes)' } } } }
        });

        // Multi-Attribute Time Chart
        new Chart(document.getElementById('multiTimeChart'), {
            type: 'line',
            data: {
                labels: ['10×1B', '10×20B', '50×20B', '100×20B', '200×20B'],
                datasets: [
                    { label: 'MongoDB BSON', data: benchmarkData.multiTime.mongo, borderColor: colors.mongodb.line, backgroundColor: colors.mongodb.fill, borderWidth: 3, tension: 0.4, fill: true },
                    { label: 'Oracle JCT (no index)', data: benchmarkData.multiTime.oracleNo, borderColor: colors.oracle_no.line, backgroundColor: colors.oracle_no.fill, borderWidth: 3, tension: 0.4, fill: true },
                    { label: 'Oracle JCT (with index)', data: benchmarkData.multiTime.oracleIdx, borderColor: colors.oracle_idx.line, backgroundColor: colors.oracle_idx.fill, borderWidth: 3, tension: 0.4, fill: true },
                    { label: 'PostgreSQL JSON', data: benchmarkData.multiTime.pgJson, borderColor: colors.pg_json.line, backgroundColor: colors.pg_json.fill, borderWidth: 3, tension: 0.4, fill: true },
                    { label: 'PostgreSQL JSONB', data: benchmarkData.multiTime.pgJsonb, borderColor: colors.pg_jsonb.line, backgroundColor: colors.pg_jsonb.fill, borderWidth: 3, tension: 0.4, fill: true }
                ]
            },
            options: { ...chartOptions, scales: { y: { title: { display: true, text: 'Time (ms)' }, beginAtZero: true }, x: { title: { display: true, text: 'Attribute Configuration' } } } }
        });

        // Multi-Attribute Throughput Chart
        new Chart(document.getElementById('multiTputChart'), {
            type: 'line',
            data: {
                labels: ['10×1B', '10×20B', '50×20B', '100×20B', '200×20B'],
                datasets: [
                    { label: 'MongoDB BSON', data: benchmarkData.multiTput.mongo, borderColor: colors.mongodb.line, backgroundColor: colors.mongodb.fill, borderWidth: 3, tension: 0.4, fill: true },
                    { label: 'Oracle JCT (no index)', data: benchmarkData.multiTput.oracleNo, borderColor: colors.oracle_no.line, backgroundColor: colors.oracle_no.fill, borderWidth: 3, tension: 0.4, fill: true },
                    { label: 'Oracle JCT (with index)', data: benchmarkData.multiTput.oracleIdx, borderColor: colors.oracle_idx.line, backgroundColor: colors.oracle_idx.fill, borderWidth: 3, tension: 0.4, fill: true },
                    { label: 'PostgreSQL JSON', data: benchmarkData.multiTput.pgJson, borderColor: colors.pg_json.line, backgroundColor: colors.pg_json.fill, borderWidth: 3, tension: 0.4, fill: true },
                    { label: 'PostgreSQL JSONB', data: benchmarkData.multiTput.pgJsonb, borderColor: colors.pg_jsonb.line, backgroundColor: colors.pg_jsonb.fill, borderWidth: 3, tension: 0.4, fill: true }
                ]
            },
            options: { ...chartOptions, scales: { y: { title: { display: true, text: 'Throughput (docs/sec)' }, beginAtZero: true }, x: { title: { display: true, text: 'Attribute Configuration' } } } }
        });

        // Degradation Chart
        new Chart(document.getElementById('degradationChart'), {
            type: 'bar',
            data: {
                labels: ['Single-Attribute (10B→4KB)', 'Multi-Attribute (10×1B→200×20B)'],
                datasets: [
                    { label: 'MongoDB BSON', data: benchmarkData.degradation.mongo, backgroundColor: colors.mongodb.line, borderColor: colors.mongodb.line, borderWidth: 2 },
                    { label: 'Oracle JCT (with index)', data: benchmarkData.degradation.oracleIdx, backgroundColor: colors.oracle_idx.line, borderColor: colors.oracle_idx.line, borderWidth: 2 },
                    { label: 'PostgreSQL JSON', data: benchmarkData.degradation.pgJson, backgroundColor: colors.pg_json.line, borderColor: colors.pg_json.line, borderWidth: 2 },
                    { label: 'PostgreSQL JSONB', data: benchmarkData.degradation.pgJsonb, backgroundColor: colors.pg_jsonb.line, borderColor: colors.pg_jsonb.line, borderWidth: 2 }
                ]
            },
            options: {
                ...chartOptions,
                scales: { y: { title: { display: true, text: 'Degradation Factor (lower is better)' }, beginAtZero: true } },
                plugins: { ...chartOptions.plugins, tooltip: { callbacks: { label: function(context) { return context.dataset.label + ': ' + context.parsed.y + 'x'; } } } }
            }
        });
'''

def generate_html(data_dict, output_file='benchmark_report.html'):
    """Generate HTML report."""
    
    percent_oracle_wins = int(((data_dict['mongo_multi_time'][-1] - data_dict['oracle_idx_multi_time'][-1]) / data_dict['oracle_idx_multi_time'][-1]) * 100)
    
    html = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MongoDB vs Oracle vs PostgreSQL - Benchmark Report</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; }
        .container { max-width: 1400px; margin: 0 auto; background: white; border-radius: 12px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); }
        header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 40px; text-align: center; border-radius: 12px 12px 0 0; }
        header h1 { font-size: 2.5em; margin-bottom: 10px; }
        .subtitle { font-size: 1.2em; opacity: 0.9; }
        .meta { margin-top: 20px; font-size: 0.9em; opacity: 0.8; }
        .content { padding: 40px; }
        .section { margin-bottom: 50px; }
        .section-title { font-size: 2em; color: #667eea; margin-bottom: 20px; padding-bottom: 10px; border-bottom: 3px solid #667eea; }
        .chart-container { position: relative; height: 500px; margin-bottom: 40px; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
        .chart-title { font-size: 1.3em; font-weight: 600; color: #333; margin-bottom: 15px; text-align: center; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
        th, td { padding: 15px; text-align: left; border-bottom: 1px solid #e0e0e0; }
        th { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; font-weight: 600; }
        tr:hover { background: #f5f5f5; }
        .winner { background: #d4edda; font-weight: 600; }
        footer { background: #f8f9fa; padding: 30px; text-align: center; color: #666; border-radius: 0 0 12px 12px; }
        footer a { color: #667eea; text-decoration: none; }
        footer a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Document Storage Benchmark Report</h1>
            <p class="subtitle">MongoDB BSON vs Oracle JCT vs PostgreSQL JSON/JSONB</p>
            <p class="meta">Generated: ''' + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '''</p>
        </header>

        <div class="content">
            <section class="section">
                <h2 class="section-title">Single-Attribute Performance</h2>
                <div class="chart-container">
                    <div class="chart-title">Insertion Time (Lower is Better)</div>
                    <canvas id="singleTimeChart"></canvas>
                </div>
                <div class="chart-container">
                    <div class="chart-title">Throughput (Higher is Better)</div>
                    <canvas id="singleTputChart"></canvas>
                </div>
            </section>

            <section class="section">
                <h2 class="section-title">Multi-Attribute Performance</h2>
                <div class="chart-container">
                    <div class="chart-title">Insertion Time (Lower is Better)</div>
                    <canvas id="multiTimeChart"></canvas>
                </div>
                <div class="chart-container">
                    <div class="chart-title">Throughput (Higher is Better)</div>
                    <canvas id="multiTputChart"></canvas>
                </div>
            </section>

            <section class="section">
                <h2 class="section-title">Performance Degradation</h2>
                <div class="chart-container">
                    <div class="chart-title">Scalability Comparison (Lower is Better)</div>
                    <canvas id="degradationChart"></canvas>
                </div>
            </section>

            <section class="section">
                <h2 class="section-title">Key Results</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Test</th>
                            <th>Winner</th>
                            <th>Time</th>
                            <th>Insight</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>Single-Attr 4KB</td>
                            <td class="winner">MongoDB</td>
                            <td>''' + str(data_dict['mongo_single_time'][-1]) + ''' ms</td>
                            <td>Most consistent scaling</td>
                        </tr>
                        <tr>
                            <td>Multi-Attr 200×20B</td>
                            <td class="winner">Oracle JCT</td>
                            <td>''' + str(data_dict['oracle_idx_multi_time'][-1]) + ''' ms</td>
                            <td>Beats MongoDB by ''' + str(percent_oracle_wins) + '''%!</td>
                        </tr>
                        <tr>
                            <td>Best Degradation</td>
                            <td class="winner">MongoDB</td>
                            <td>''' + str(data_dict['mongo_single_deg']) + '''x</td>
                            <td>Flattest performance curve</td>
                        </tr>
                    </tbody>
                </table>
            </section>
        </div>

        <footer>
            <p><strong>Benchmark Report</strong></p>
            <p>10,000 documents | 3 runs | Batch size: 500</p>
            <p><a href="https://github.com/rhoulihan/BSON-JSON-bakeoff">View on GitHub</a></p>
        </footer>
    </div>

    <script>
''' + build_charts_js(data_dict) + '''
    </script>
</body>
</html>'''

    with open(output_file, 'w') as f:
        f.write(html)

    print(f"✓ HTML report generated: {output_file}")
    print(f"  File size: {os.path.getsize(output_file) / 1024:.1f} KB")
    return output_file

def main():
    """Main execution."""
    print("="*70)
    print("Benchmark HTML Report Generator")
    print("="*70)

    print("\n1. Loading benchmark data...")
    data = load_data()
    print(f"   ✓ Loaded data from article_benchmark_results.json")

    print("\n2. Extracting and processing data...")
    data_dict = extract_data(data)
    print(f"   ✓ Extracted {len(data_dict)} data series")

    print("\n3. Generating HTML report...")
    output_file = generate_html(data_dict)

    print("\n" + "="*70)
    print("✓ Report generation complete!")
    print("="*70)
    print(f"\nOpen {output_file} in your browser to view the report.")

if __name__ == '__main__':
    main()
