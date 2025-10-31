#!/usr/bin/env python3
"""
Generate a rich HTML report with interactive charts from benchmark results.
Creates line graphs similar to the LinkedIn article.
"""

import json
from datetime import datetime

def load_results(filename="article_benchmark_results.json"):
    """Load benchmark results from JSON file."""
    with open(filename, 'r') as f:
        return json.load(f)

def generate_html_report(data, output_file="benchmark_report.html"):
    """Generate comprehensive HTML report with interactive charts."""

    # Extract data for charts
    single_attr = data['single_attribute']
    multi_attr = data['multi_attribute']

    # Prepare chart data
    sizes_single = [10, 200, 1000, 2000, 4000]
    sizes_multi_labels = ['10×1B', '10×20B', '50×20B', '100×20B', '200×20B']

    # Pre-extract all data arrays
    mongo_single_time = [r['time_ms'] for r in single_attr['mongodb']]
    oracle_no_single_time = [r['time_ms'] for r in single_attr['oracle_no_index']]
    oracle_idx_single_time = [r['time_ms'] for r in single_attr['oracle_with_index']]
    pg_json_single_time = [r['time_ms'] for r in single_attr['postgresql_json']]
    pg_jsonb_single_time = [r['time_ms'] for r in single_attr['postgresql_jsonb']]

    mongo_single_throughput = [round(r['throughput']) for r in single_attr['mongodb']]
    oracle_no_single_throughput = [round(r['throughput']) for r in single_attr['oracle_no_index']]
    oracle_idx_single_throughput = [round(r['throughput']) for r in single_attr['oracle_with_index']]
    pg_json_single_throughput = [round(r['throughput']) for r in single_attr['postgresql_json']]
    pg_jsonb_single_throughput = [round(r['throughput']) for r in single_attr['postgresql_jsonb']]

    mongo_multi_time = [r['time_ms'] for r in multi_attr['mongodb']]
    oracle_no_multi_time = [r['time_ms'] for r in multi_attr['oracle_no_index']]
    oracle_idx_multi_time = [r['time_ms'] for r in multi_attr['oracle_with_index']]
    pg_json_multi_time = [r['time_ms'] for r in multi_attr['postgresql_json']]
    pg_jsonb_multi_time = [r['time_ms'] for r in multi_attr['postgresql_jsonb']]

    mongo_multi_throughput = [round(r['throughput']) for r in multi_attr['mongodb']]
    oracle_no_multi_throughput = [round(r['throughput']) for r in multi_attr['oracle_no_index']]
    oracle_idx_multi_throughput = [round(r['throughput']) for r in multi_attr['oracle_with_index']]
    pg_json_multi_throughput = [round(r['throughput']) for r in multi_attr['postgresql_json']]
    pg_jsonb_multi_throughput = [round(r['throughput']) for r in multi_attr['postgresql_jsonb']]

    # Calculate degradation
    mongo_single_deg = round(mongo_single_time[-1] / mongo_single_time[0], 2)
    oracle_idx_single_deg = round(oracle_idx_single_time[-1] / oracle_idx_single_time[0], 2)
    pg_json_single_deg = round(pg_json_single_time[-1] / pg_json_single_time[0], 2)
    pg_jsonb_single_deg = round(pg_jsonb_single_time[-1] / pg_jsonb_single_time[0], 2)

    mongo_multi_deg = round(mongo_multi_time[-1] / mongo_multi_time[0], 2)
    oracle_idx_multi_deg = round(oracle_idx_multi_time[-1] / oracle_idx_multi_time[0], 2)
    pg_json_multi_deg = round(pg_json_multi_time[-1] / pg_json_multi_time[0], 2)
    pg_jsonb_multi_deg = round(pg_jsonb_multi_time[-1] / pg_jsonb_multi_time[0], 2)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Document Storage Benchmark Report - MongoDB vs Oracle vs PostgreSQL</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            line-height: 1.6;
            color: #333;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}

        header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}

        header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        }}

        header .subtitle {{
            font-size: 1.2em;
            opacity: 0.9;
        }}

        header .meta {{
            margin-top: 20px;
            font-size: 0.9em;
            opacity: 0.8;
        }}

        .content {{
            padding: 40px;
        }}

        .section {{
            margin-bottom: 50px;
        }}

        .section-title {{
            font-size: 2em;
            color: #667eea;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 3px solid #667eea;
        }}

        .chart-container {{
            position: relative;
            height: 500px;
            margin-bottom: 40px;
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}

        .chart-title {{
            font-size: 1.3em;
            font-weight: 600;
            margin-bottom: 15px;
            color: #444;
            text-align: center;
        }}

        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}

        .summary-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 25px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }}

        .summary-card h3 {{
            font-size: 1.1em;
            margin-bottom: 10px;
            opacity: 0.9;
        }}

        .summary-card .value {{
            font-size: 2.5em;
            font-weight: bold;
            margin-bottom: 5px;
        }}

        .summary-card .label {{
            font-size: 0.9em;
            opacity: 0.8;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            background: white;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            border-radius: 8px;
            overflow: hidden;
        }}

        th, td {{
            padding: 15px;
            text-align: left;
            border-bottom: 1px solid #e0e0e0;
        }}

        th {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.85em;
            letter-spacing: 0.5px;
        }}

        tr:hover {{
            background: #f8f9fa;
        }}

        .winner {{
            background: #d4edda;
            font-weight: 600;
            color: #155724;
        }}

        .poor {{
            background: #f8d7da;
            color: #721c24;
        }}

        .findings {{
            background: #f8f9fa;
            padding: 30px;
            border-radius: 8px;
            border-left: 5px solid #667eea;
        }}

        .findings h3 {{
            color: #667eea;
            margin-bottom: 15px;
        }}

        .findings ul {{
            list-style: none;
            padding-left: 0;
        }}

        .findings li {{
            padding: 10px 0;
            padding-left: 30px;
            position: relative;
        }}

        .findings li:before {{
            content: "→";
            position: absolute;
            left: 0;
            color: #667eea;
            font-weight: bold;
            font-size: 1.2em;
        }}

        .recommendations {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 20px;
            margin-top: 30px;
        }}

        .recommendation-card {{
            background: white;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            padding: 25px;
            transition: all 0.3s;
        }}

        .recommendation-card:hover {{
            border-color: #667eea;
            box-shadow: 0 8px 16px rgba(102, 126, 234, 0.2);
            transform: translateY(-5px);
        }}

        .recommendation-card h3 {{
            color: #667eea;
            margin-bottom: 15px;
            font-size: 1.3em;
        }}

        .recommendation-card ul {{
            list-style: none;
            padding: 0;
        }}

        .recommendation-card li {{
            padding: 8px 0;
            padding-left: 25px;
            position: relative;
        }}

        .recommendation-card li:before {{
            content: "✓";
            position: absolute;
            left: 0;
            color: #28a745;
            font-weight: bold;
        }}

        .badge {{
            display: inline-block;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 600;
            margin-left: 10px;
        }}

        .badge-winner {{
            background: #28a745;
            color: white;
        }}

        .badge-second {{
            background: #ffc107;
            color: #333;
        }}

        .badge-poor {{
            background: #dc3545;
            color: white;
        }}

        footer {{
            background: #2c3e50;
            color: white;
            padding: 30px;
            text-align: center;
        }}

        footer a {{
            color: #667eea;
            text-decoration: none;
        }}

        footer a:hover {{
            text-decoration: underline;
        }}

        @media print {{
            body {{
                background: white;
                padding: 0;
            }}
            .container {{
                box-shadow: none;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📊 Document Storage Benchmark Report</h1>
            <div class="subtitle">MongoDB BSON vs Oracle JCT vs PostgreSQL JSON/JSONB</div>
            <div class="meta">
                <div>Generated: {datetime.now().strftime('%B %d, %Y at %H:%M:%S')}</div>
                <div>Test Date: {data['timestamp'][:10]} | 10,000 documents | 3 runs | Batch size: 500</div>
            </div>
        </header>

        <div class="content">
            <!-- Executive Summary -->
            <section class="section">
                <h2 class="section-title">Executive Summary</h2>

                <div class="summary-grid">
                    <div class="summary-card">
                        <h3>🥇 Best Single-Attribute</h3>
                        <div class="value">MongoDB</div>
                        <div class="label">256-339ms • 1.24x degradation</div>
                    </div>
                    <div class="summary-card">
                        <h3>🥇 Best Multi-Attribute</h3>
                        <div class="value">Oracle JCT</div>
                        <div class="label">699-700ms @ 200 attrs • 2.46x degradation</div>
                    </div>
                    <div class="summary-card">
                        <h3>❌ Worst Performer</h3>
                        <div class="value">PostgreSQL</div>
                        <div class="label">JSONB: 118.7x degradation</div>
                    </div>
                </div>

                <div class="findings">
                    <h3>🔍 Key Findings</h3>
                    <ul>
                        <li><strong>Oracle WINS Most Complex Test:</strong> 200 attributes (699-700ms vs MongoDB 804ms - 13-15% faster!)</li>
                        <li><strong>MongoDB WINS Large Single Docs:</strong> 4KB single attribute (339ms vs Oracle 434-440ms)</li>
                        <li><strong>PostgreSQL TOAST Cliff Confirmed:</strong> 82-119x degradation above 2KB</li>
                        <li><strong>Oracle Index Nearly Free:</strong> &lt;5% overhead for search index</li>
                        <li><strong>JSONB Slower Than JSON:</strong> Contrary to expectations, JSONB 43% slower for writes</li>
                    </ul>
                </div>
            </section>

            <!-- Single-Attribute Charts -->
            <section class="section">
                <h2 class="section-title">Single-Attribute Performance</h2>

                <div class="chart-container">
                    <div class="chart-title">Insertion Time by Document Size (Lower is Better)</div>
                    <canvas id="singleAttrChart"></canvas>
                </div>

                <div class="chart-container">
                    <div class="chart-title">Throughput by Document Size (Higher is Better)</div>
                    <canvas id="singleAttrThroughputChart"></canvas>
                </div>
            </section>

            <!-- Multi-Attribute Charts -->
            <section class="section">
                <h2 class="section-title">Multi-Attribute Performance</h2>

                <div class="chart-container">
                    <div class="chart-title">Insertion Time by Attribute Count (Lower is Better)</div>
                    <canvas id="multiAttrChart"></canvas>
                </div>

                <div class="chart-container">
                    <div class="chart-title">Throughput by Attribute Count (Higher is Better)</div>
                    <canvas id="multiAttrThroughputChart"></canvas>
                </div>
            </section>

            <!-- Degradation Comparison -->
            <section class="section">
                <h2 class="section-title">Performance Degradation Analysis</h2>

                <div class="chart-container">
                    <div class="chart-title">How Well Does Each Platform Scale?</div>
                    <canvas id="degradationChart"></canvas>
                </div>

                <table>
                    <thead>
                        <tr>
                            <th>Database</th>
                            <th>Single-Attr Degradation</th>
                            <th>Multi-Attr Degradation</th>
                            <th>Overall Rating</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td><strong>MongoDB BSON</strong></td>
                            <td class="winner">1.24x (256→339ms)</td>
                            <td>3.03x (265→804ms)</td>
                            <td class="winner">⭐⭐⭐⭐⭐</td>
                        </tr>
                        <tr>
                            <td><strong>Oracle JCT (no index)</strong></td>
                            <td class="winner">1.67x (264→440ms)</td>
                            <td class="winner">2.46x (284→700ms)</td>
                            <td class="winner">⭐⭐⭐⭐⭐</td>
                        </tr>
                        <tr>
                            <td><strong>Oracle JCT (with index)</strong></td>
                            <td class="winner">1.69x (257→434ms)</td>
                            <td class="winner">2.66x (263→699ms)</td>
                            <td class="winner">⭐⭐⭐⭐⭐</td>
                        </tr>
                        <tr>
                            <td><strong>PostgreSQL JSON</strong></td>
                            <td class="poor">82.9x (192→15,910ms)</td>
                            <td class="poor">74.9x (216→16,173ms)</td>
                            <td class="poor">❌</td>
                        </tr>
                        <tr>
                            <td><strong>PostgreSQL JSONB</strong></td>
                            <td class="poor">118.7x (206→24,447ms)</td>
                            <td class="poor">113.9x (248→28,253ms)</td>
                            <td class="poor">❌</td>
                        </tr>
                    </tbody>
                </table>
            </section>

            <!-- Detailed Results Tables -->
            <section class="section">
                <h2 class="section-title">Detailed Results</h2>

                <h3 style="margin-top: 30px; margin-bottom: 15px; color: #667eea;">Single-Attribute Performance (10K documents)</h3>
                <table>
                    <thead>
                        <tr>
                            <th>Payload</th>
                            <th>MongoDB</th>
                            <th>Oracle (no idx)</th>
                            <th>Oracle (idx)</th>
                            <th>PG-JSON</th>
                            <th>PG-JSONB</th>
                        </tr>
                    </thead>
                    <tbody>
"""

    # Single-attribute table rows
    for i, size in enumerate(sizes_single):
        mongo = single_attr['mongodb'][i]
        oracle_no = single_attr['oracle_no_index'][i]
        oracle_idx = single_attr['oracle_with_index'][i]
        pg_json = single_attr['postgresql_json'][i]
        pg_jsonb = single_attr['postgresql_jsonb'][i]

        # Find winner
        times = [mongo['time_ms'], oracle_no['time_ms'], oracle_idx['time_ms']]
        min_time = min(times)

        html += f"""                        <tr>
                            <td><strong>{size}B</strong></td>
                            <td{"class='winner'" if mongo['time_ms'] == min_time else ''}>{mongo['time_ms']}ms</td>
                            <td{"class='winner'" if oracle_no['time_ms'] == min_time else ''}>{oracle_no['time_ms']}ms</td>
                            <td{"class='winner'" if oracle_idx['time_ms'] == min_time else ''}>{oracle_idx['time_ms']}ms</td>
                            <td{"class='poor'" if size >= 1000 else ''}>{pg_json['time_ms']:,}ms</td>
                            <td{"class='poor'" if size >= 1000 else ''}>{pg_jsonb['time_ms']:,}ms</td>
                        </tr>
"""

    html += """                    </tbody>
                </table>

                <h3 style="margin-top: 30px; margin-bottom: 15px; color: #667eea;">Multi-Attribute Performance (10K documents)</h3>
                <table>
                    <thead>
                        <tr>
                            <th>Config</th>
                            <th>MongoDB</th>
                            <th>Oracle (no idx)</th>
                            <th>Oracle (idx)</th>
                            <th>PG-JSON</th>
                            <th>PG-JSONB</th>
                        </tr>
                    </thead>
                    <tbody>
"""

    # Multi-attribute table rows
    for i, label in enumerate(sizes_multi_labels):
        mongo = multi_attr['mongodb'][i]
        oracle_no = multi_attr['oracle_no_index'][i]
        oracle_idx = multi_attr['oracle_with_index'][i]
        pg_json = multi_attr['postgresql_json'][i]
        pg_jsonb = multi_attr['postgresql_jsonb'][i]

        # Find winner
        times = [mongo['time_ms'], oracle_no['time_ms'], oracle_idx['time_ms']]
        min_time = min(times)

        html += f"""                        <tr>
                            <td><strong>{label}</strong></td>
                            <td{"class='winner'" if mongo['time_ms'] == min_time else ''}>{mongo['time_ms']}ms</td>
                            <td{"class='winner'" if oracle_no['time_ms'] == min_time else ''}>{oracle_no['time_ms']}ms</td>
                            <td{"class='winner'" if oracle_idx['time_ms'] == min_time else ''}>{oracle_idx['time_ms']}ms</td>
                            <td{"class='poor'" if i >= 2 else ''}>{pg_json['time_ms']:,}ms</td>
                            <td{"class='poor'" if i >= 2 else ''}>{pg_jsonb['time_ms']:,}ms</td>
                        </tr>
"""

    html += """                    </tbody>
                </table>
            </section>

            <!-- Recommendations -->
            <section class="section">
                <h2 class="section-title">Recommendations</h2>

                <div class="recommendations">
                    <div class="recommendation-card">
                        <h3>🥇 Choose MongoDB BSON</h3>
                        <ul>
                            <li>Large documents with few attributes (1-4KB)</li>
                            <li>Most consistent performance (1.24x degradation)</li>
                            <li>Proven ecosystem and tooling</li>
                            <li>Horizontal scaling required</li>
                            <li>Variable document sizes</li>
                        </ul>
                    </div>

                    <div class="recommendation-card">
                        <h3>🥇 Choose Oracle JCT</h3>
                        <ul>
                            <li>Complex documents with many attributes (100-200+)</li>
                            <li>Already using Oracle infrastructure</li>
                            <li>Need SQL access to JSON documents</li>
                            <li>Enterprise ACID guarantees required</li>
                            <li>WINS the most complex test (200 attrs)</li>
                        </ul>
                    </div>

                    <div class="recommendation-card">
                        <h3>⚠️ Use PostgreSQL Only When</h3>
                        <ul>
                            <li>Documents are tiny (&lt;200B)</li>
                            <li>Primarily relational with occasional JSON</li>
                            <li>Read-heavy workload (JSONB indexes help)</li>
                            <li>Low write volume</li>
                            <li>Already deployed on PostgreSQL</li>
                        </ul>
                    </div>

                    <div class="recommendation-card">
                        <h3>❌ Avoid PostgreSQL When</h3>
                        <ul>
                            <li>Documents exceed 2KB (TOAST kills performance)</li>
                            <li>High-volume document inserts</li>
                            <li>Pure document storage use case</li>
                            <li>Many attributes per document</li>
                            <li>Write-heavy workloads</li>
                        </ul>
                    </div>
                </div>
            </section>
        </div>

        <footer>
            <p><strong>Document Storage Benchmark Report</strong></p>
            <p>Testing MongoDB BSON, Oracle 26ai JSON Collection Tables, and PostgreSQL 17.6 JSON/JSONB</p>
            <p style="margin-top: 15px;">
                <a href="https://github.com/rhoulihan/BSON-JSON-bakeoff">View on GitHub</a> |
                Generated with ❤️ by Claude Code
            </p>
        </footer>
    </div>

    <script>
        // Chart configuration
        const chartOptions = {{
            responsive: true,
            maintainAspectRatio: false,
            interaction: {{
                mode: 'index',
                intersect: false,
            }},
            plugins: {{
                legend: {{
                    display: true,
                    position: 'top',
                    labels: {{
                        usePointStyle: true,
                        padding: 15,
                        font: {{
                            size: 12,
                            weight: '600'
                        }}
                    }}
                }},
                tooltip: {{
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    padding: 12,
                    titleFont: {{
                        size: 14,
                        weight: 'bold'
                    }},
                    bodyFont: {{
                        size: 13
                    }},
                    displayColors: true
                }}
            }},
            scales: {{
                y: {{
                    beginAtZero: true,
                    grid: {{
                        color: 'rgba(0, 0, 0, 0.05)'
                    }},
                    ticks: {{
                        font: {{
                            size: 11
                        }}
                    }}
                }},
                x: {{
                    grid: {{
                        display: false
                    }},
                    ticks: {{
                        font: {{
                            size: 11,
                            weight: '600'
                        }}
                    }}
                }}
            }}
        }};

        // Colors for each database
        const colors = {{
            mongodb: {{ line: 'rgb(0, 237, 100)', fill: 'rgba(0, 237, 100, 0.1)' }},
            oracle_no: {{ line: 'rgb(255, 0, 0)', fill: 'rgba(255, 0, 0, 0.1)' }},
            oracle_idx: {{ line: 'rgb(255, 99, 132)', fill: 'rgba(255, 99, 132, 0.1)' }},
            pg_json: {{ line: 'rgb(54, 162, 235)', fill: 'rgba(54, 162, 235, 0.1)' }},
            pg_jsonb: {{ line: 'rgb(153, 102, 255)', fill: 'rgba(153, 102, 255, 0.1)' }}
        }};

        // Single-Attribute Time Chart
        new Chart(document.getElementById('singleAttrChart'), {{
            type: 'line',
            data: {{
                labels: {sizes_single},
                datasets: [
                    {{
                        label: 'MongoDB BSON',
                        data: {mongo_single_time},
                        borderColor: colors.mongodb.line,
                        backgroundColor: colors.mongodb.fill,
                        borderWidth: 3,
                        tension: 0.4,
                        fill: true,
                        pointRadius: 5,
                        pointHoverRadius: 7
                    }},
                    {{
                        label: 'Oracle JCT (no index)',
                        data: {oracle_no_single_time},
                        borderColor: colors.oracle_no.line,
                        backgroundColor: colors.oracle_no.fill,
                        borderWidth: 3,
                        tension: 0.4,
                        fill: true,
                        pointRadius: 5,
                        pointHoverRadius: 7
                    }},
                    {{
                        label: 'Oracle JCT (with index)',
                        data: {oracle_idx_single_time},
                        borderColor: colors.oracle_idx.line,
                        backgroundColor: colors.oracle_idx.fill,
                        borderWidth: 3,
                        tension: 0.4,
                        fill: true,
                        pointRadius: 5,
                        pointHoverRadius: 7
                    }},
                    {{
                        label: 'PostgreSQL JSON',
                        data: {pg_json_single_time},
                        borderColor: colors.pg_json.line,
                        backgroundColor: colors.pg_json.fill,
                        borderWidth: 3,
                        tension: 0.4,
                        fill: true,
                        pointRadius: 5,
                        pointHoverRadius: 7
                    }},
                    {{
                        label: 'PostgreSQL JSONB',
                        data: {pg_jsonb_single_time},
                        borderColor: colors.pg_jsonb.line,
                        backgroundColor: colors.pg_jsonb.fill,
                        borderWidth: 3,
                        tension: 0.4,
                        fill: true,
                        pointRadius: 5,
                        pointHoverRadius: 7
                    }}
                ]
            }},
            options: {{
                ...chartOptions,
                scales: {{
                    ...chartOptions.scales,
                    y: {{
                        ...chartOptions.scales.y,
                        title: {{
                            display: true,
                            text: 'Time (milliseconds)',
                            font: {{ size: 13, weight: 'bold' }}
                        }}
                    }},
                    x: {{
                        ...chartOptions.scales.x,
                        title: {{
                            display: true,
                            text: 'Document Size (bytes)',
                            font: {{ size: 13, weight: 'bold' }}
                        }}
                    }}
                }}
            }}
        }});

        // Single-Attribute Throughput Chart
        new Chart(document.getElementById('singleAttrThroughputChart'), {{
            type: 'line',
            data: {{
                labels: {sizes_single},
                datasets: [
                    {{
                        label: 'MongoDB BSON',
                        data: {mongo_single_throughput},
                        borderColor: colors.mongodb.line,
                        backgroundColor: colors.mongodb.fill,
                        borderWidth: 3,
                        tension: 0.4,
                        fill: true,
                        pointRadius: 5,
                        pointHoverRadius: 7
                    }},
                    {{
                        label: 'Oracle JCT (no index)',
                        data: {oracle_no_single_throughput},
                        borderColor: colors.oracle_no.line,
                        backgroundColor: colors.oracle_no.fill,
                        borderWidth: 3,
                        tension: 0.4,
                        fill: true,
                        pointRadius: 5,
                        pointHoverRadius: 7
                    }},
                    {{
                        label: 'Oracle JCT (with index)',
                        data: {oracle_idx_single_throughput},
                        borderColor: colors.oracle_idx.line,
                        backgroundColor: colors.oracle_idx.fill,
                        borderWidth: 3,
                        tension: 0.4,
                        fill: true,
                        pointRadius: 5,
                        pointHoverRadius: 7
                    }},
                    {{
                        label: 'PostgreSQL JSON',
                        data: {pg_json_single_throughput},
                        borderColor: colors.pg_json.line,
                        backgroundColor: colors.pg_json.fill,
                        borderWidth: 3,
                        tension: 0.4,
                        fill: true,
                        pointRadius: 5,
                        pointHoverRadius: 7
                    }},
                    {{
                        label: 'PostgreSQL JSONB',
                        data: {pg_jsonb_single_throughput},
                        borderColor: colors.pg_jsonb.line,
                        backgroundColor: colors.pg_jsonb.fill,
                        borderWidth: 3,
                        tension: 0.4,
                        fill: true,
                        pointRadius: 5,
                        pointHoverRadius: 7
                    }}
                ]
            }},
            options: {{
                ...chartOptions,
                scales: {{
                    ...chartOptions.scales,
                    y: {{
                        ...chartOptions.scales.y,
                        title: {{
                            display: true,
                            text: 'Throughput (docs/second)',
                            font: {{ size: 13, weight: 'bold' }}
                        }}
                    }},
                    x: {{
                        ...chartOptions.scales.x,
                        title: {{
                            display: true,
                            text: 'Document Size (bytes)',
                            font: {{ size: 13, weight: 'bold' }}
                        }}
                    }}
                }}
            }}
        }});

        // Multi-Attribute Time Chart
        new Chart(document.getElementById('multiAttrChart'), {{
            type: 'line',
            data: {{
                labels: {sizes_multi_labels},
                datasets: [
                    {{
                        label: 'MongoDB BSON',
                        data: {mongo_multi_time},
                        borderColor: colors.mongodb.line,
                        backgroundColor: colors.mongodb.fill,
                        borderWidth: 3,
                        tension: 0.4,
                        fill: true,
                        pointRadius: 5,
                        pointHoverRadius: 7
                    }},
                    {{
                        label: 'Oracle JCT (no index)',
                        data: {oracle_no_multi_time},
                        borderColor: colors.oracle_no.line,
                        backgroundColor: colors.oracle_no.fill,
                        borderWidth: 3,
                        tension: 0.4,
                        fill: true,
                        pointRadius: 5,
                        pointHoverRadius: 7
                    }},
                    {{
                        label: 'Oracle JCT (with index)',
                        data: {oracle_idx_multi_time},
                        borderColor: colors.oracle_idx.line,
                        backgroundColor: colors.oracle_idx.fill,
                        borderWidth: 3,
                        tension: 0.4,
                        fill: true,
                        pointRadius: 5,
                        pointHoverRadius: 7
                    }},
                    {{
                        label: 'PostgreSQL JSON',
                        data: {pg_json_multi_time},
                        borderColor: colors.pg_json.line,
                        backgroundColor: colors.pg_json.fill,
                        borderWidth: 3,
                        tension: 0.4,
                        fill: true,
                        pointRadius: 5,
                        pointHoverRadius: 7
                    }},
                    {{
                        label: 'PostgreSQL JSONB',
                        data: {pg_jsonb_multi_time},
                        borderColor: colors.pg_jsonb.line,
                        backgroundColor: colors.pg_jsonb.fill,
                        borderWidth: 3,
                        tension: 0.4,
                        fill: true,
                        pointRadius: 5,
                        pointHoverRadius: 7
                    }}
                ]
            }},
            options: {{
                ...chartOptions,
                scales: {{
                    ...chartOptions.scales,
                    y: {{
                        ...chartOptions.scales.y,
                        title: {{
                            display: true,
                            text: 'Time (milliseconds)',
                            font: {{ size: 13, weight: 'bold' }}
                        }}
                    }},
                    x: {{
                        ...chartOptions.scales.x,
                        title: {{
                            display: true,
                            text: 'Document Configuration',
                            font: {{ size: 13, weight: 'bold' }}
                        }}
                    }}
                }}
            }}
        }});

        // Multi-Attribute Throughput Chart
        new Chart(document.getElementById('multiAttrThroughputChart'), {{
            type: 'line',
            data: {{
                labels: {sizes_multi_labels},
                datasets: [
                    {{
                        label: 'MongoDB BSON',
                        data: {mongo_multi_throughput},
                        borderColor: colors.mongodb.line,
                        backgroundColor: colors.mongodb.fill,
                        borderWidth: 3,
                        tension: 0.4,
                        fill: true,
                        pointRadius: 5,
                        pointHoverRadius: 7
                    }},
                    {{
                        label: 'Oracle JCT (no index)',
                        data: {oracle_no_multi_throughput},
                        borderColor: colors.oracle_no.line,
                        backgroundColor: colors.oracle_no.fill,
                        borderWidth: 3,
                        tension: 0.4,
                        fill: true,
                        pointRadius: 5,
                        pointHoverRadius: 7
                    }},
                    {{
                        label: 'Oracle JCT (with index)',
                        data: {oracle_idx_multi_throughput},
                        borderColor: colors.oracle_idx.line,
                        backgroundColor: colors.oracle_idx.fill,
                        borderWidth: 3,
                        tension: 0.4,
                        fill: true,
                        pointRadius: 5,
                        pointHoverRadius: 7
                    }},
                    {{
                        label: 'PostgreSQL JSON',
                        data: {pg_json_multi_throughput},
                        borderColor: colors.pg_json.line,
                        backgroundColor: colors.pg_json.fill,
                        borderWidth: 3,
                        tension: 0.4,
                        fill: true,
                        pointRadius: 5,
                        pointHoverRadius: 7
                    }},
                    {{
                        label: 'PostgreSQL JSONB',
                        data: {pg_jsonb_multi_throughput},
                        borderColor: colors.pg_jsonb.line,
                        backgroundColor: colors.pg_jsonb.fill,
                        borderWidth: 3,
                        tension: 0.4,
                        fill: true,
                        pointRadius: 5,
                        pointHoverRadius: 7
                    }}
                ]
            }},
            options: {{
                ...chartOptions,
                scales: {{
                    ...chartOptions.scales,
                    y: {{
                        ...chartOptions.scales.y,
                        title: {{
                            display: true,
                            text: 'Throughput (docs/second)',
                            font: {{ size: 13, weight: 'bold' }}
                        }}
                    }},
                    x: {{
                        ...chartOptions.scales.x,
                        title: {{
                            display: true,
                            text: 'Document Configuration',
                            font: {{ size: 13, weight: 'bold' }}
                        }}
                    }}
                }}
            }}
        }});

        // Degradation Comparison Chart
        new Chart(document.getElementById('degradationChart'), {{
            type: 'bar',
            data: {{
                labels: ['Single-Attribute\\n(10B→4KB)', 'Multi-Attribute\\n(10×1B→200×20B)'],
                datasets: [
                    {{
                        label: 'MongoDB BSON',
                        data: [{mongo_single_deg}, {mongo_multi_deg}],
                        backgroundColor: colors.mongodb.line,
                        borderColor: colors.mongodb.line,
                        borderWidth: 2
                    }},
                    {{
                        label: 'Oracle JCT (with index)',
                        data: [{oracle_idx_single_deg}, {oracle_idx_multi_deg}],
                        backgroundColor: colors.oracle_idx.line,
                        borderColor: colors.oracle_idx.line,
                        borderWidth: 2
                    }},
                    {{
                        label: 'PostgreSQL JSON',
                        data: [{pg_json_single_deg}, {pg_json_multi_deg}],
                        backgroundColor: colors.pg_json.line,
                        borderColor: colors.pg_json.line,
                        borderWidth: 2
                    }},
                    {{
                        label: 'PostgreSQL JSONB',
                        data: [{pg_jsonb_single_deg}, {pg_jsonb_multi_deg}],
                        backgroundColor: colors.pg_jsonb.line,
                        borderColor: colors.pg_jsonb.line,
                        borderWidth: 2
                    }}
                ]
            }},
            options: {{
                ...chartOptions,
                scales: {{
                    ...chartOptions.scales,
                    y: {{
                        ...chartOptions.scales.y,
                        title: {{
                            display: true,
                            text: 'Degradation Factor (lower is better)',
                            font: {{ size: 13, weight: 'bold' }}
                        }},
                        type: 'logarithmic',
                        ticks: {{
                            callback: function(value) {{
                                return value.toFixed(1) + 'x';
                            }}
                        }}
                    }},
                    x: {{
                        ...chartOptions.scales.x,
                        title: {{
                            display: true,
                            text: 'Test Type',
                            font: {{ size: 13, weight: 'bold' }}
                        }}
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>
"""

    # Write HTML file
    with open(output_file, 'w') as f:
        f.write(html)

    print(f"✓ HTML report generated: {output_file}")
    return output_file

def main():
    """Main execution."""
    print("Generating HTML benchmark report...")
    data = load_results()
    output_file = generate_html_report(data)
    print(f"\nOpen {output_file} in your browser to view the report!")

if __name__ == "__main__":
    main()
