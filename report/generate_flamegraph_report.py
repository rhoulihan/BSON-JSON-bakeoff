#!/usr/bin/env python3
"""
Generate standalone HTML report for flame graph analysis.
Complements the main benchmark_report.html with detailed flame graph data.
"""

import flamegraph_report_helper
from datetime import datetime
from pathlib import Path

# Determine project root (parent of the report/ directory)
PROJECT_ROOT = Path(__file__).parent.parent


def generate_html_report():
    """Generate complete HTML report with flame graph analysis."""

    # Get all flame graph sections
    fg_sections = flamegraph_report_helper.get_all_sections()

    local_idx_summary, local_idx_flamegraphs = fg_sections['local_indexed']
    local_noidx_summary, local_noidx_flamegraphs = fg_sections['local_noindex']
    remote_idx_summary, remote_idx_flamegraphs = fg_sections['remote_indexed']
    remote_noidx_summary, remote_noidx_flamegraphs = fg_sections['remote_noindex']

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Flame Graph Analysis Report</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
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
            margin: 0;
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

        .summary-section {{
            padding: 20px;
            margin: 20px 0;
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
            max-height: 5000px;
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
    </style>
</head>
<body>
    <div class="container">
        <h1>Flame Graph Analysis Report</h1>
        <div class="metadata">
            <strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br>
            <strong>Analysis Scope:</strong> CPU profiling with async-profiler 3.0<br>
            <strong>Test Configuration:</strong> 10,000 documents, 3 runs per test, Batch size: 500<br>
            <strong>Profiling Method:</strong> Low-overhead sampling profiler with flame graph visualization
        </div>

        <div class="tabs">
            <button class="tab active" onclick="openTab(event, 'local')">Local System</button>
            <button class="tab" onclick="openTab(event, 'remote')">Remote System</button>
        </div>

        <!-- LOCAL SYSTEM TAB -->
        <div id="local" class="tab-content active">
            <div class="subtabs">
                <button class="subtab active" onclick="openSubTab(event, 'local', 'local-indexed')">Indexed (with Queries)</button>
                <button class="subtab" onclick="openSubTab(event, 'local', 'local-noindex')">No Index (Insert Only)</button>
            </div>

            <!-- LOCAL INDEXED SUBTAB -->
            <div id="local-indexed" class="subtab-content active">
                <div class="collapsible-section">
                    <div class="collapsible-header" onclick="toggleSection(this)">
                        <h2 style="margin: 0; padding: 0; border: none;">Test Summary</h2>
                        <span class="collapse-icon">▼</span>
                    </div>
                    <div class="collapsible-content">
                        {local_idx_summary}
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
                        <h2 style="margin: 0; padding: 0; border: none;">Test Summary</h2>
                        <span class="collapse-icon">▼</span>
                    </div>
                    <div class="collapsible-content">
                        {local_noidx_summary}
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
                        <h2 style="margin: 0; padding: 0; border: none;">Test Summary</h2>
                        <span class="collapse-icon">▼</span>
                    </div>
                    <div class="collapsible-content">
                        {remote_idx_summary}
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
                        <h2 style="margin: 0; padding: 0; border: none;">Test Summary</h2>
                        <span class="collapse-icon">▼</span>
                    </div>
                    <div class="collapsible-content">
                        {remote_noidx_summary}
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


def main():
    """Generate the flame graph report."""
    print("Generating flame graph report...")

    html = generate_html_report()

    output_file = PROJECT_ROOT / 'flamegraph_report.html'
    with open(str(output_file), 'w') as f:
        f.write(html)

    print(f"\n✅ Flame graph report generated: {output_file}")
    print(f"   Open in browser: file://{Path(output_file).absolute()}")


if __name__ == '__main__':
    from pathlib import Path
    main()
