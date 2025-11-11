#!/usr/bin/env python3
"""
Helper module to generate flame graph sections for the benchmark report.
Called by generate_benchmark_report.py to embed flame graph analysis.
Supports both client-side (HTML) and server-side (SVG) flame graphs.
"""

import json
from pathlib import Path
import re


# Determine project root (parent of the report/ directory)
PROJECT_ROOT = Path(__file__).parent.parent


def load_flamegraph_summaries():
    """Load the flame graph analysis summaries (client-side)."""
    summaries_file = PROJECT_ROOT / 'flamegraph_summaries.json'
    if summaries_file.exists():
        with open(summaries_file, 'r') as f:
            return json.load(f)
    return None


def discover_server_flamegraphs():
    """
    Discover and parse server-side flame graphs from server_flamegraphs/ directory.

    Returns:
        List of dicts with server flame graph metadata, or empty list if none found.
        Format: [{
            'database': 'mongodb' or 'oracle',
            'filename': 'mongodb_server_20251106_172238.svg',
            'filepath': 'server_flamegraphs/mongodb_server_20251106_172238.svg',
            'timestamp': '20251106_172238',
            'file_size': size in bytes
        }]
    """
    server_fg_dir = PROJECT_ROOT / 'server_flamegraphs'
    if not server_fg_dir.exists():
        return []

    server_flamegraphs = []

    # Pattern: {database}_server_{timestamp}.svg
    # Examples: mongodb_server_20251106_172238.svg, oracle_server_20251106_172310.svg
    pattern = re.compile(r'^(mongodb|oracle)_server_(\d{8}_\d{6})\.svg$')

    for svg_file in server_fg_dir.glob('*.svg'):
        match = pattern.match(svg_file.name)
        if match:
            database = match.group(1)
            timestamp = match.group(2)

            server_flamegraphs.append({
                'database': database,
                'filename': svg_file.name,
                'filepath': str(svg_file),
                'timestamp': timestamp,
                'file_size': svg_file.stat().st_size
            })

    # Sort by timestamp (most recent first)
    server_flamegraphs.sort(key=lambda x: x['timestamp'], reverse=True)

    return server_flamegraphs


def generate_test_summary_html(summaries, config_key):
    """Generate HTML for test summary section."""
    if not summaries or config_key not in summaries:
        return "<p>No summary data available.</p>"

    tests = summaries[config_key]

    # Separate MongoDB and Oracle tests
    mongodb_tests = [t for t in tests if t['database'] == 'MongoDB BSON']
    oracle_tests = [t for t in tests if t['database'] == 'Oracle JCT']

    html = '<div class="summary-section">\n'

    # MongoDB summary
    if mongodb_tests:
        avg_insert = sum(t['performance']['insertion']['docs_per_sec'] for t in mongodb_tests) / len(mongodb_tests)
        html += f'''
        <h4>MongoDB BSON Performance</h4>
        <div class="stats-grid" style="grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); margin-bottom: 20px;">
            <div class="stat-card">
                <h5>Avg Insertion Rate</h5>
                <div class="value" style="font-size: 1.8em;">{avg_insert:,.0f}</div>
                <div class="label">docs/sec</div>
            </div>
            <div class="stat-card">
                <h5>Tests Completed</h5>
                <div class="value" style="font-size: 1.8em;">{len(mongodb_tests)}</div>
                <div class="label">benchmarks</div>
            </div>
        </div>
        '''

        # Add query performance if available
        mongodb_query_tests = [t for t in mongodb_tests if 'query' in t['performance']]
        if mongodb_query_tests:
            avg_query = sum(t['performance']['query']['queries_per_sec'] for t in mongodb_query_tests) / len(mongodb_query_tests)
            html += f'''
            <div class="comparison-box" style="background: rgba(102, 126, 234, 0.1); margin-bottom: 20px;">
                <strong>Query Performance:</strong> Average {avg_query:,.0f} queries/sec across {len(mongodb_query_tests)} tests
                using multikey indexes on array fields.
            </div>
            '''

    # Oracle summary
    if oracle_tests:
        avg_insert = sum(t['performance']['insertion']['docs_per_sec'] for t in oracle_tests) / len(oracle_tests)
        html += f'''
        <h4>Oracle JCT Performance</h4>
        <div class="stats-grid" style="grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); margin-bottom: 20px;">
            <div class="stat-card">
                <h5>Avg Insertion Rate</h5>
                <div class="value" style="font-size: 1.8em;">{avg_insert:,.0f}</div>
                <div class="label">docs/sec</div>
            </div>
            <div class="stat-card">
                <h5>Tests Completed</h5>
                <div class="value" style="font-size: 1.8em;">{len(oracle_tests)}</div>
                <div class="label">benchmarks</div>
            </div>
        </div>
        '''

        # Add query performance if available
        oracle_query_tests = [t for t in oracle_tests if 'query' in t['performance']]
        if oracle_query_tests:
            avg_query = sum(t['performance']['query']['queries_per_sec'] for t in oracle_query_tests) / len(oracle_query_tests)
            html += f'''
            <div class="comparison-box" style="background: rgba(231, 76, 60, 0.1); margin-bottom: 20px;">
                <strong>Query Performance:</strong> Average {avg_query:,.0f} queries/sec across {len(oracle_query_tests)} tests
                using multivalue indexes on JSON Collection Tables (<code>data.array[*].string()</code> syntax).
            </div>
            '''

    # Performance comparison
    if mongodb_tests and oracle_tests:
        mongo_avg = sum(t['performance']['insertion']['docs_per_sec'] for t in mongodb_tests) / len(mongodb_tests)
        oracle_avg = sum(t['performance']['insertion']['docs_per_sec'] for t in oracle_tests) / len(oracle_tests)
        ratio = mongo_avg / oracle_avg if oracle_avg > 0 else 0

        html += f'''
        <div class="comparison-box" style="background: rgba(46, 125, 50, 0.1); border-left: 4px solid #2e7d32;">
            <strong>Performance Ratio:</strong> MongoDB achieves {ratio:.1f}x higher insertion throughput than Oracle
            on this system ({mongo_avg:,.0f} vs {oracle_avg:,.0f} docs/sec).
        </div>
        '''

    html += '</div>\n'
    return html


def match_server_flamegraph_to_test(test, server_flamegraphs):
    """
    Match a server-side flame graph to a client-side test based on database and timestamp proximity.

    Returns the closest matching server flame graph or None.
    """
    # Extract database from test
    db_key = 'mongodb' if test['database'] == 'MongoDB BSON' else 'oracle'

    # Extract timestamp from client flame graph file
    # Format: mongodb_bson_insert_10B_1attrs_20251107_085648.html
    client_fg_file = test['flamegraph_file']
    timestamp_match = re.search(r'_(\d{8}_\d{6})\.html$', client_fg_file)

    if not timestamp_match:
        return None

    client_timestamp = timestamp_match.group(1)

    # Find server flame graphs for the same database
    matching_server_fgs = [fg for fg in server_flamegraphs if fg['database'] == db_key]

    if not matching_server_fgs:
        return None

    # Find the closest timestamp (server FG should be within 60 seconds of client FG)
    best_match = None
    best_diff = float('inf')

    for server_fg in matching_server_fgs:
        # Calculate time difference
        time_diff = abs(int(client_timestamp.replace('_', '')) - int(server_fg['timestamp'].replace('_', '')))

        if time_diff < best_diff and time_diff < 10000:  # Within ~100 seconds
            best_diff = time_diff
            best_match = server_fg

    return best_match


def generate_flamegraph_list_html(summaries, config_key):
    """Generate unified HTML table with both client-side and server-side flame graphs."""
    html = '<div class="flamegraph-list">\n'

    html += '<h3 style="color: #667eea; margin-top: 20px; margin-bottom: 15px;">🔥 Flame Graph Analysis</h3>\n'
    html += '<p style="margin-bottom: 20px; color: #666;">CPU profiling of both client (Java application) and server (database processes) using async-profiler and Linux perf.</p>\n'

    if not summaries or config_key not in summaries:
        html += "<p>No flame graph data available.</p>"
    else:
        tests = summaries[config_key]
        server_flamegraphs = discover_server_flamegraphs()

        html += '<table style="width: 100%; border-collapse: collapse; margin-bottom: 40px;">\n'
        html += '''
        <thead>
            <tr style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white;">
                <th style="padding: 12px; text-align: left; border: 1px solid #ddd;">Database</th>
                <th style="padding: 12px; text-align: left; border: 1px solid #ddd;">Test Description</th>
                <th style="padding: 12px; text-align: right; border: 1px solid #ddd;">Insert Rate</th>
                <th style="padding: 12px; text-align: right; border: 1px solid #ddd;">Query Rate</th>
                <th style="padding: 12px; text-align: center; border: 1px solid #ddd;">Client<br/>Flame Graph</th>
                <th style="padding: 12px; text-align: center; border: 1px solid #ddd;">Server<br/>Flame Graph</th>
            </tr>
        </thead>
        <tbody>
        '''

        for test in tests:
            db_color = '#667eea' if test['database'] == 'MongoDB BSON' else '#e74c3c'
            insert_rate = test['performance']['insertion']['docs_per_sec']
            query_rate = test['performance'].get('query', {}).get('queries_per_sec', '-')
            query_rate_str = f"{query_rate:,}" if query_rate != '-' else '-'

            # Client-side flame graph
            flamegraph_file = test['flamegraph_file']

            # Find matching server-side flame graph
            server_fg = match_server_flamegraph_to_test(test, server_flamegraphs)

            html += f'''
            <tr style="border-bottom: 1px solid #eee;">
                <td style="padding: 10px; border: 1px solid #ddd;">
                    <span style="color: {db_color}; font-weight: bold;">●</span> {test['database']}
                </td>
                <td style="padding: 10px; border: 1px solid #ddd;">{test['description']}</td>
                <td style="padding: 10px; text-align: right; border: 1px solid #ddd; font-family: monospace;">
                    {insert_rate:,}
                </td>
                <td style="padding: 10px; text-align: right; border: 1px solid #ddd; font-family: monospace;">
                    {query_rate_str}
                </td>
                <td style="padding: 10px; text-align: center; border: 1px solid #ddd;">
                    <a href="{flamegraph_file}" target="_blank"
                       style="background: #667eea; color: white; padding: 6px 12px;
                              border-radius: 4px; text-decoration: none; display: inline-block; font-size: 0.85em;">
                        View Client
                    </a>
                </td>
                <td style="padding: 10px; text-align: center; border: 1px solid #ddd;">'''

            if server_fg:
                server_path = f"server_flamegraphs/{server_fg['filename']}"
                html += f'''
                    <a href="{server_path}" target="_blank"
                       style="background: #764ba2; color: white; padding: 6px 12px;
                              border-radius: 4px; text-decoration: none; display: inline-block; font-size: 0.85em;">
                        View Server
                    </a>'''
            else:
                html += '<span style="color: #999; font-size: 0.85em;">N/A</span>'

            html += '''
                </td>
            </tr>
            '''

            # Add analysis notes as expandable row
            if test.get('analysis'):
                html += f'''
            <tr style="background: #f8f9fa;">
                <td colspan="6" style="padding: 10px 20px; border: 1px solid #ddd; font-size: 0.9em;">
                    <strong>Analysis:</strong>
                    <ul style="margin: 5px 0; padding-left: 20px;">
            '''
                for note in test['analysis']:
                    html += f'            <li>{note}</li>\n'
                html += '''
                    </ul>
                </td>
            </tr>
            '''

        html += '''
        </tbody>
        </table>
        '''

        # Add legend
        html += '''
        <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin-top: 20px;">
            <strong>Legend:</strong>
            <ul style="margin: 10px 0; padding-left: 20px;">
                <li><strong>Client Flame Graph:</strong> CPU profiling of the Java client application (JDBC driver, JSON serialization, networking)</li>
                <li><strong>Server Flame Graph:</strong> CPU profiling of the database server process (mongod or Oracle) using Linux perf</li>
                <li><strong>N/A:</strong> Server-side profiling not available for this test</li>
            </ul>
        </div>
        '''

    html += '</div>\n'
    return html


def generate_flamegraph_sections(config_key):
    """
    Generate both test summary and flame graph sections for a given configuration.

    Args:
        config_key: One of 'local_indexed', 'local_noindex', 'remote_indexed', 'remote_noindex'

    Returns:
        Tuple of (test_summary_html, flamegraph_list_html)
    """
    summaries = load_flamegraph_summaries()

    if not summaries:
        no_data = "<p>Flame graph analysis data not available. Run analyze_flamegraphs.py to generate summaries.</p>"
        return (no_data, no_data)

    test_summary = generate_test_summary_html(summaries, config_key)
    flamegraph_list = generate_flamegraph_list_html(summaries, config_key)

    return (test_summary, flamegraph_list)


def get_all_sections():
    """
    Get all flame graph sections for all configurations.

    Returns:
        Dictionary with keys for each configuration containing (summary, flamegraphs) tuples
    """
    configs = ['local_indexed', 'local_noindex', 'remote_indexed', 'remote_noindex']
    sections = {}

    for config in configs:
        sections[config] = generate_flamegraph_sections(config)

    return sections


if __name__ == '__main__':
    # Test the module
    print("Testing flame graph report helper...")
    sections = get_all_sections()

    for config, (summary, flamegraphs) in sections.items():
        print(f"\n=== {config} ===")
        print(f"Summary length: {len(summary)} chars")
        print(f"Flamegraphs length: {len(flamegraphs)} chars")
