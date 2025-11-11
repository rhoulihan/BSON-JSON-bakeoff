#!/usr/bin/env python3
"""
Unified modular benchmark report generator.
Combines performance benchmarks with flame graph analysis and CPU overhead insights.
"""

import sys
from pathlib import Path
from datetime import datetime
import zipfile
import shutil

# Determine paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent

# Add report_modules to path
sys.path.insert(0, str(SCRIPT_DIR))

from report_modules.benchmark_formatter import format_benchmark_table
from report_modules.executive_summary import generate_executive_summary_html, load_flamegraph_summaries
from report_modules.flamegraph_to_benchmark_converter import convert_all_configurations
from report_modules.chart_generator import generate_query_performance_chart, generate_insertion_performance_chart
import flamegraph_report_helper
import json


def generate_report_html(data, fg_sections, fg_summaries):
    """Generate unified HTML report with benchmarks and flame graphs."""

    # Extract data
    local_idx = data['local_indexed']
    local_noidx = data['local_noindex']
    remote_idx = data['remote_indexed']
    remote_noidx = data['remote_noindex']

    # Check if we have data for each system
    has_local_data = bool(local_idx or local_noidx)
    has_remote_data = bool(remote_idx or remote_noidx)

    # Extract flame graph sections
    local_idx_summary, local_idx_flamegraphs = fg_sections['local_indexed']
    local_noidx_summary, local_noidx_flamegraphs = fg_sections['local_noindex']
    remote_idx_summary, remote_idx_flamegraphs = fg_sections['remote_indexed']
    remote_noidx_summary, remote_noidx_flamegraphs = fg_sections['remote_noindex']

    # Generate executive summary
    exec_summary = generate_executive_summary_html({
        'local_indexed': local_idx,
        'local_noindex': local_noidx,
        'remote_indexed': remote_idx,
        'remote_noindex': remote_noidx
    }, fg_summaries)

    # Build tab buttons
    tab_buttons = '''<button class="tab active" onclick="openTab(event, 'overview')">Executive Summary</button>'''
    if has_local_data:
        tab_buttons += '''<button class="tab" onclick="openTab(event, 'local')">Local System</button>'''
    if has_remote_data:
        tab_buttons += '''<button class="tab" onclick="openTab(event, 'remote')">Remote System</button>'''

    # Build local system tab content
    local_tab_content = ""
    if has_local_data:
        local_tab_content = f'''
        <!-- LOCAL SYSTEM TAB -->
        <div id="local" class="tab-content">
            <div class="subtabs">
                <button class="subtab active" onclick="openSubTab(event, 'local', 'local-indexed')">Indexed (with Queries)</button>
                <button class="subtab" onclick="openSubTab(event, 'local', 'local-noindex')">No Index (Insert Only)</button>
            </div>

            <!-- LOCAL INDEXED SUBTAB -->
            <div id="local-indexed" class="subtab-content active">
                <div class="collapsible-section">
                    <div class="collapsible-header" onclick="toggleSection(this)">
                        <h2 style="margin: 0; padding: 0; border: none;">Test Results</h2>
                        <span class="collapse-icon">▼</span>
                    </div>
                    <div class="collapsible-content">
                        {generate_query_performance_chart(local_idx, "Query Performance - Local System (Indexed)")}
                        {generate_insertion_performance_chart(local_idx, "Insertion Performance - Local System (Indexed)")}
                    </div>
                </div>

                <div class="collapsible-section">
                    <div class="collapsible-header" onclick="toggleSection(this)">
                        <h2 style="margin: 0; padding: 0; border: none;">Raw Data</h2>
                        <span class="collapse-icon">▼</span>
                    </div>
                    <div class="collapsible-content">
                        {format_benchmark_table(local_idx, 'indexed')}
                    </div>
                </div>

                <div class="collapsible-section">
                    <div class="collapsible-header" onclick="toggleSection(this)">
                        <h2 style="margin: 0; padding: 0; border: none;">Flame Graphs</h2>
                        <span class="collapse-icon">▼</span>
                    </div>
                    <div class="collapsible-content">
                        {local_idx_flamegraphs}
                    </div>
                </div>
            </div>

            <!-- LOCAL NO INDEX SUBTAB -->
            <div id="local-noindex" class="subtab-content">
                <div class="collapsible-section">
                    <div class="collapsible-header" onclick="toggleSection(this)">
                        <h2 style="margin: 0; padding: 0; border: none;">Test Results</h2>
                        <span class="collapse-icon">▼</span>
                    </div>
                    <div class="collapsible-content">
                        {generate_insertion_performance_chart(local_noidx, "Insertion Performance - Local System (No Index)")}
                    </div>
                </div>

                <div class="collapsible-section">
                    <div class="collapsible-header" onclick="toggleSection(this)">
                        <h2 style="margin: 0; padding: 0; border: none;">Raw Data</h2>
                        <span class="collapse-icon">▼</span>
                    </div>
                    <div class="collapsible-content">
                        {format_benchmark_table(local_noidx, 'noindex')}
                    </div>
                </div>

                <div class="collapsible-section">
                    <div class="collapsible-header" onclick="toggleSection(this)">
                        <h2 style="margin: 0; padding: 0; border: none;">Flame Graphs</h2>
                        <span class="collapse-icon">▼</span>
                    </div>
                    <div class="collapsible-content">
                        {local_noidx_flamegraphs}
                    </div>
                </div>
            </div>
        </div>
        '''

    # Build remote system tab content
    remote_tab_content = ""
    if has_remote_data:
        remote_tab_content = f'''
        <!-- REMOTE SYSTEM TAB -->
        <div id="remote" class="tab-content">
            <div class="subtabs">
                <button class="subtab active" onclick="openSubTab(event, 'remote', 'remote-indexed')">Indexed (with Queries)</button>
                <button class="subtab" onclick="openSubTab(event, 'remote', 'remote-noindex')">No Index (Insert Only)</button>
            </div>

            <!-- REMOTE INDEXED SUBTAB -->
            <div id="remote-indexed" class="subtab-content active">
                <div class="collapsible-section">
                    <div class="collapsible-header" onclick="toggleSection(this)">
                        <h2 style="margin: 0; padding: 0; border: none;">Test Results</h2>
                        <span class="collapse-icon">▼</span>
                    </div>
                    <div class="collapsible-content">
                        {generate_query_performance_chart(remote_idx, "Query Performance - Remote System (Indexed)")}
                        {generate_insertion_performance_chart(remote_idx, "Insertion Performance - Remote System (Indexed)")}
                    </div>
                </div>

                <div class="collapsible-section">
                    <div class="collapsible-header" onclick="toggleSection(this)">
                        <h2 style="margin: 0; padding: 0; border: none;">Raw Data</h2>
                        <span class="collapse-icon">▼</span>
                    </div>
                    <div class="collapsible-content">
                        {format_benchmark_table(remote_idx, 'indexed')}
                    </div>
                </div>

                <div class="collapsible-section">
                    <div class="collapsible-header" onclick="toggleSection(this)">
                        <h2 style="margin: 0; padding: 0; border: none;">Flame Graphs</h2>
                        <span class="collapse-icon">▼</span>
                    </div>
                    <div class="collapsible-content">
                        {remote_idx_flamegraphs}
                    </div>
                </div>
            </div>

            <!-- REMOTE NO INDEX SUBTAB -->
            <div id="remote-noindex" class="subtab-content">
                <div class="collapsible-section">
                    <div class="collapsible-header" onclick="toggleSection(this)">
                        <h2 style="margin: 0; padding: 0; border: none;">Test Results</h2>
                        <span class="collapse-icon">▼</span>
                    </div>
                    <div class="collapsible-content">
                        {generate_insertion_performance_chart(remote_noidx, "Insertion Performance - Remote System (No Index)")}
                    </div>
                </div>

                <div class="collapsible-section">
                    <div class="collapsible-header" onclick="toggleSection(this)">
                        <h2 style="margin: 0; padding: 0; border: none;">Raw Data</h2>
                        <span class="collapse-icon">▼</span>
                    </div>
                    <div class="collapsible-content">
                        {format_benchmark_table(remote_noidx, 'noindex')}
                    </div>
                </div>

                <div class="collapsible-section">
                    <div class="collapsible-header" onclick="toggleSection(this)">
                        <h2 style="margin: 0; padding: 0; border: none;">Flame Graphs</h2>
                        <span class="collapse-icon">▼</span>
                    </div>
                    <div class="collapsible-content">
                        {remote_noidx_flamegraphs}
                    </div>
                </div>
            </div>
        </div>
        '''

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Unified Benchmark Report - MongoDB vs Oracle 23ai</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            border-radius: 10px;
            overflow: hidden;
        }}

        h1 {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
            font-size: 2.5em;
        }}

        h2 {{
            color: #667eea;
            padding: 20px 30px 10px;
            border-bottom: 3px solid #667eea;
            margin: 30px 30px 20px;
        }}

        h3 {{
            color: #764ba2;
            padding: 15px 30px 10px;
            margin: 20px 0 10px;
        }}

        h4 {{
            color: #555;
            margin: 15px 0 10px;
        }}

        h5 {{
            color: #777;
            margin: 10px 0 5px;
            font-size: 0.9em;
        }}

        .metadata {{
            background: #f8f9fa;
            padding: 20px 30px;
            border-left: 4px solid #667eea;
            margin: 20px 30px;
            font-size: 0.95em;
            line-height: 1.8;
        }}

        .tabs {{
            display: flex;
            background: #f1f3f5;
            border-bottom: 2px solid #dee2e6;
            padding: 0 30px;
        }}

        .tab {{
            padding: 15px 30px;
            background: transparent;
            border: none;
            cursor: pointer;
            font-size: 1.1em;
            font-weight: 500;
            color: #555;
            transition: all 0.3s;
            border-bottom: 3px solid transparent;
        }}

        .tab:hover {{
            background: rgba(102, 126, 234, 0.1);
        }}

        .tab.active {{
            background: white;
            color: #667eea;
            border-bottom: 3px solid #667eea;
        }}

        .tab-content {{
            display: none;
            padding: 30px;
        }}

        .tab-content.active {{
            display: block;
        }}

        .subtabs {{
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            padding: 10px 0;
            border-bottom: 2px solid #e0e0e0;
        }}

        .subtab {{
            padding: 10px 20px;
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 5px;
            cursor: pointer;
            font-size: 1em;
            font-weight: 500;
            color: #555;
            transition: all 0.3s;
        }}

        .subtab:hover {{
            background: rgba(102, 126, 234, 0.1);
        }}

        .subtab.active {{
            background: #667eea;
            color: white;
            border-color: #667eea;
        }}

        .subtab-content {{
            display: none;
        }}

        .subtab-content.active {{
            display: block;
        }}

        .collapsible-section {{
            margin: 30px 0;
        }}

        .collapsible-header {{
            background: #f8f9fa;
            padding: 15px 20px;
            cursor: pointer;
            border-left: 4px solid #667eea;
            display: flex;
            justify-content: space-between;
            align-items: center;
            transition: background 0.3s;
        }}

        .collapsible-header:hover {{
            background: #e9ecef;
        }}

        .collapsible-content {{
            max-height: 10000px;
            overflow: hidden;
            transition: max-height 0.5s ease, opacity 0.5s ease, padding 0.5s ease;
            opacity: 1;
            padding-top: 20px;
        }}

        .collapsible-content.collapsed {{
            max-height: 0;
            opacity: 0;
            padding-top: 0;
        }}

        .collapse-icon {{
            transition: transform 0.3s;
        }}

        .collapsible-header.collapsed .collapse-icon {{
            transform: rotate(-90deg);
        }}

        a {{
            color: #667eea;
            text-decoration: none;
        }}

        a:hover {{
            text-decoration: underline;
        }}

        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}

        .stat-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
        }}

        .stat-card .value {{
            font-size: 2.5em;
            font-weight: bold;
            margin: 10px 0;
        }}

        .stat-card .label {{
            font-size: 0.9em;
            opacity: 0.9;
        }}

        .comparison-box {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #667eea;
            margin: 15px 0;
        }}

        .flamegraph-list table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}

        .flamegraph-list th {{
            background: #667eea;
            color: white;
            padding: 12px;
            text-align: left;
            border: 1px solid #ddd;
        }}

        .flamegraph-list td {{
            padding: 10px;
            border: 1px solid #ddd;
        }}

        .flamegraph-list tr:hover {{
            background: #f8f9fa;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>MongoDB vs Oracle 23ai Benchmark Report</h1>
        <div class="metadata">
            <strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br>
            <strong>Test Configuration:</strong> 10,000 documents, 3 runs per test, Batch size: 500<br>
            <strong>CPU Profiling:</strong> async-profiler 3.0 with flame graph generation<br>
            <strong>Monitoring:</strong> CPU, disk I/O, and network activity tracking
        </div>

        <div class="tabs">
            {tab_buttons}
        </div>

        <!-- OVERVIEW TAB -->
        <div id="overview" class="tab-content active">
            {exec_summary}
        </div>

        {local_tab_content}

        {remote_tab_content}

    </div>

    <script>
        function openTab(evt, tabName) {{
            var i, tabcontent, tabs;

            tabcontent = document.getElementsByClassName("tab-content");
            for (i = 0; i < tabcontent.length; i++) {{
                tabcontent[i].classList.remove("active");
            }}

            tabs = document.getElementsByClassName("tab");
            for (i = 0; i < tabs.length; i++) {{
                tabs[i].classList.remove("active");
            }}

            document.getElementById(tabName).classList.add("active");
            evt.currentTarget.classList.add("active");
        }}

        function openSubTab(evt, parentTab, subtabId) {{
            var parentContainer = document.getElementById(parentTab);

            var subtabContents = parentContainer.getElementsByClassName('subtab-content');
            for (var i = 0; i < subtabContents.length; i++) {{
                subtabContents[i].classList.remove('active');
            }}

            var subtabs = parentContainer.getElementsByClassName('subtab');
            for (var i = 0; i < subtabs.length; i++) {{
                subtabs[i].classList.remove('active');
            }}

            document.getElementById(subtabId).classList.add("active");
            evt.currentTarget.classList.add("active");
        }}

        function toggleSection(element) {{
            var content = element.nextElementSibling;
            content.classList.toggle('collapsed');
            element.classList.toggle('collapsed');
        }}
    </script>
</body>
</html>
'''

    return html


def create_distributable_archive(report_file, flamegraphs_dir, server_flamegraphs_dir='server_flamegraphs', archive_name='benchmark_report_package.zip'):
    """
    Create a distributable zip archive containing the report and all dependencies.

    Args:
        report_file: Path to the HTML report file
        flamegraphs_dir: Path to the client-side flamegraphs directory
        server_flamegraphs_dir: Path to the server-side flamegraphs directory
        archive_name: Name of the output zip file

    Returns:
        Path to the created zip file
    """
    print(f"\nStep 5: Creating distributable archive...")

    # Create README content
    readme_content = """MongoDB vs Oracle 23ai Benchmark Report Package
================================================

This package contains a comprehensive benchmark report comparing MongoDB BSON
and Oracle 23ai JSON Collection Tables performance.

Contents:
---------
- unified_benchmark_report.html : Main report (open this file in your browser)
- flamegraphs/                  : Client-side CPU profiling (Java app - HTML files)
- server_flamegraphs/           : Server-side CPU profiling (DB servers - SVG files)
- README.txt                    : This file

How to View:
------------
1. Extract this zip file to a folder on your computer
2. Open 'unified_benchmark_report.html' in your web browser
   - You can double-click the file, or
   - Right-click and select "Open with" your preferred browser
3. Navigate through the report using the tabs
4. Click "View Flame Graph" buttons to see detailed CPU profiling data
   (flame graphs will open in new browser tabs)

Flame Graph Types:
-----------------
- Client-Side Flame Graphs: Profile Java client application (JDBC, JSON serialization)
  These are HTML files generated by async-profiler
- Server-Side Flame Graphs: Profile database server processes (mongod, Oracle)
  These are SVG files generated by Linux perf + FlameGraph tools

System Requirements:
-------------------
- Any modern web browser (Chrome, Firefox, Safari, Edge)
- JavaScript enabled (required for interactive charts and tabs)
- No internet connection required (all resources are self-contained)

Report Sections:
---------------
- Executive Summary: Key findings and performance comparisons
- Local System: Benchmark results from the local test environment
- Remote System: Benchmark results from the remote OCI cloud environment
- Test Results: Interactive charts showing throughput and response times
- Raw Data: Detailed benchmark data tables
- Flame Graphs: CPU profiling visualizations for both client and server

For questions or issues, please contact the report generator.

Generated: """ + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + "\n"

    # Create the zip file
    archive_path = Path(archive_name)

    with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Add the main report (use just the filename, not full path)
        report_filename = Path(report_file).name
        print(f"  Adding {report_filename}...")
        zipf.write(report_file, arcname=report_filename)

        # Add all client-side flamegraph HTML files
        flamegraphs_path = Path(flamegraphs_dir)
        if flamegraphs_path.exists():
            flamegraph_files = list(flamegraphs_path.glob('*.html'))
            print(f"  Adding {len(flamegraph_files)} client-side flame graph files...")
            for fg_file in flamegraph_files:
                zipf.write(fg_file, arcname=f'flamegraphs/{fg_file.name}')
        else:
            print(f"  Warning: Client flamegraphs directory '{flamegraphs_dir}' not found")

        # Add all server-side flamegraph SVG files
        server_fg_path = Path(server_flamegraphs_dir)
        if server_fg_path.exists():
            server_fg_files = list(server_fg_path.glob('*.svg'))
            print(f"  Adding {len(server_fg_files)} server-side flame graph files...")
            for fg_file in server_fg_files:
                zipf.write(fg_file, arcname=f'server_flamegraphs/{fg_file.name}')
        else:
            print(f"  Note: Server flamegraphs directory '{server_flamegraphs_dir}' not found (run with --server-profile to generate)")

        # Add README
        print("  Adding README.txt...")
        zipf.writestr('README.txt', readme_content)

    # Get file size
    size_mb = archive_path.stat().st_size / (1024 * 1024)
    print(f"  Archive created: {archive_path} ({size_mb:.2f} MB)")

    return archive_path


def main():
    """Generate the unified benchmark report."""
    print("=== Unified Benchmark Report Generator ===\n")

    print("Step 1: Loading flame graph summaries...")
    fg_summaries = load_flamegraph_summaries()

    if not fg_summaries:
        print("Error: No flame graph summaries found. Run benchmarks with --flame-graph first.")
        return

    print("Step 2: Converting flame graph data to benchmark format...")
    data = convert_all_configurations(fg_summaries)

    print("Step 3: Loading flame graph HTML sections...")
    fg_sections = flamegraph_report_helper.get_all_sections()

    print("Step 4: Generating unified HTML report...")
    html = generate_report_html(data, fg_sections, fg_summaries)

    output_file = PROJECT_ROOT / 'unified_benchmark_report.html'
    with open(output_file, 'w') as f:
        f.write(html)

    print(f"\n✅ Unified report generated: {output_file}")
    print(f"   Open in browser: file://{output_file.absolute()}")

    # Create distributable archive
    archive_path = create_distributable_archive(
        report_file=str(output_file),
        flamegraphs_dir=str(PROJECT_ROOT / 'flamegraphs'),
        server_flamegraphs_dir=str(PROJECT_ROOT / 'server_flamegraphs'),
        archive_name=str(PROJECT_ROOT / 'benchmark_report_package.zip')
    )

    print()
    print("=" * 70)
    print("✅ Report Generation Complete!")
    print("=" * 70)
    print()
    print("📊 Standalone Report:")
    print(f"   {output_file}")
    print(f"   Open in browser: file://{Path(output_file).absolute()}")
    print()
    print("📦 Distributable Package:")
    print(f"   {archive_path}")
    print(f"   Share this zip file - extract and open {output_file} in any browser")
    print()
    print("This report combines:")
    print("  - Performance benchmark results with interactive charts")
    print("  - Flame graph analysis with detailed CPU profiling")
    print("  - Executive summary with key findings")
    print("  - Side-by-side system comparisons")
    print()


if __name__ == '__main__':
    main()
