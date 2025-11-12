"""
Chart generation module for benchmark visualizations using inline SVG.
Enhanced with modern styling, smooth curves, gradients, and professional design.
Includes separate charts for single/multi-attribute and throughput/time metrics.
"""


def create_smooth_path(points, scale_x, scale_y, tension=0.3):
    """
    Create a smooth cubic bezier curve through points.

    Args:
        points: List of (x, y) tuples
        scale_x: Function to scale x coordinates
        scale_y: Function to scale y coordinates
        tension: Curve tension (0 = straight lines, 1 = very smooth)

    Returns:
        SVG path string with smooth curves
    """
    if len(points) < 2:
        return ""

    # Convert to scaled coordinates
    scaled_points = [(scale_x(p[0]), scale_y(p[1])) for p in points]

    if len(scaled_points) == 2:
        # Just a straight line for 2 points
        return f"M {scaled_points[0][0]},{scaled_points[0][1]} L {scaled_points[1][0]},{scaled_points[1][1]}"

    # Start path
    path = f"M {scaled_points[0][0]},{scaled_points[0][1]}"

    # Create smooth curves through points using cubic bezier
    for i in range(len(scaled_points) - 1):
        p0 = scaled_points[max(0, i - 1)]
        p1 = scaled_points[i]
        p2 = scaled_points[i + 1]
        p3 = scaled_points[min(len(scaled_points) - 1, i + 2)]

        # Calculate control points for smooth curve
        cp1x = p1[0] + (p2[0] - p0[0]) * tension
        cp1y = p1[1] + (p2[1] - p0[1]) * tension
        cp2x = p2[0] - (p3[0] - p1[0]) * tension
        cp2y = p2[1] - (p3[1] - p1[1]) * tension

        path += f" C {cp1x},{cp1y} {cp2x},{cp2y} {p2[0]},{p2[1]}"

    return path


def generate_chart(mongo_points, oracle_points, title, y_axis_label, value_formatter=lambda x: f"{int(x):,}"):
    """
    Generate a modern SVG chart with given data points.

    Args:
        mongo_points: List of tuples (x_label, y_value, x_position) for MongoDB
        oracle_points: List of tuples (x_label, y_value, x_position) for Oracle
        title: Chart title
        y_axis_label: Label for Y-axis
        value_formatter: Function to format Y-axis values

    Returns:
        HTML string with inline SVG chart
    """
    if not mongo_points and not oracle_points:
        return f"<p>No data available for {title}.</p>"

    # Calculate chart dimensions (sized for side-by-side display)
    width, height = 550, 400
    padding_left, padding_right = 70, 30
    padding_top, padding_bottom = 50, 80
    chart_width = width - padding_left - padding_right
    chart_height = height - padding_top - padding_bottom

    # Extract values for scaling
    all_x_positions = [p[2] for p in mongo_points + oracle_points]
    all_y_values = [p[1] for p in mongo_points + oracle_points]

    if not all_x_positions or not all_y_values:
        return f"<p>Insufficient data for {title}.</p>"

    min_x, max_x = min(all_x_positions), max(all_x_positions)
    min_y, max_y = 0, max(all_y_values) * 1.15

    # Scale functions (logarithmic for x-axis to spread out data points)
    import math

    def scale_x(x_pos):
        if max_x == min_x:
            return padding_left + chart_width / 2
        # Use logarithmic scale for better visualization of exponential data
        # Add 1 to avoid log(0)
        log_min = math.log10(min_x + 1)
        log_max = math.log10(max_x + 1)
        log_pos = math.log10(x_pos + 1)
        return padding_left + (log_pos - log_min) / (log_max - log_min) * chart_width

    def scale_y(y_val):
        if max_y == 0:
            return height - padding_bottom
        return height - padding_bottom - (y_val / max_y) * chart_height

    # Get unique x-axis labels and positions
    all_points = mongo_points + oracle_points
    x_labels = {}
    for label, _, pos in all_points:
        if pos not in x_labels:
            x_labels[pos] = label
    x_labels = sorted(x_labels.items())

    # Generate SVG
    svg = f'''
    <div style="margin: 20px 0;">
        <div style="background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); padding: 20px; border-radius: 12px; box-shadow: 0 10px 30px rgba(0,0,0,0.15);">
            <h4 style="text-align: center; color: #2c3e50; margin: 0 0 15px 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-size: 16px; font-weight: 600;">{title}</h4>
            <svg width="{width}" height="{height}" style="background: white; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">

                <defs>
                    <linearGradient id="mongoGrad_{id(mongo_points)}" x1="0%" y1="0%" x2="0%" y2="100%">
                        <stop offset="0%" style="stop-color:#667eea;stop-opacity:0.3" />
                        <stop offset="100%" style="stop-color:#667eea;stop-opacity:0.05" />
                    </linearGradient>
                    <linearGradient id="oracleGrad_{id(oracle_points)}" x1="0%" y1="0%" x2="0%" y2="100%">
                        <stop offset="0%" style="stop-color:#e74c3c;stop-opacity:0.3" />
                        <stop offset="100%" style="stop-color:#e74c3c;stop-opacity:0.05" />
                    </linearGradient>
                    <filter id="shadow_{id(title)}">
                        <feGaussianBlur in="SourceAlpha" stdDeviation="2"/>
                        <feOffset dx="0" dy="2" result="offsetblur"/>
                        <feComponentTransfer>
                            <feFuncA type="linear" slope="0.3"/>
                        </feComponentTransfer>
                        <feMerge>
                            <feMergeNode/>
                            <feMergeNode in="SourceGraphic"/>
                        </feMerge>
                    </filter>
                </defs>

                <!-- Grid lines -->
                <g stroke="#e8eaf0" stroke-width="1" stroke-dasharray="4,4">
'''

    # Horizontal grid lines
    for i in range(6):
        y = height - padding_bottom - (i / 5) * chart_height
        y_value = (i / 5) * max_y
        svg += f'''                    <line x1="{padding_left}" y1="{y}" x2="{width - padding_right}" y2="{y}"/>
                    <text x="{padding_left - 15}" y="{y + 5}" text-anchor="end" font-size="13" fill="#64748b" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif">{value_formatter(y_value)}</text>
'''

    # Vertical grid lines with labels
    for x_pos, x_label in x_labels:
        x = scale_x(x_pos)
        svg += f'''                    <line x1="{x}" y1="{padding_top}" x2="{x}" y2="{height - padding_bottom}"/>
'''

    svg += '''                </g>

'''

    # X-axis labels (rotated for better fit)
    for x_pos, x_label in x_labels:
        x = scale_x(x_pos)
        svg += f'''                <text x="{x}" y="{height - padding_bottom + 20}" text-anchor="end" font-size="11" fill="#64748b" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" transform="rotate(-45, {x}, {height - padding_bottom + 20})">{x_label}</text>
'''

    # MongoDB data
    if mongo_points:
        # Convert to (x_pos, y_val) for path generation
        mongo_path_points = [(p[2], p[1]) for p in mongo_points]
        mongo_path = create_smooth_path(mongo_path_points, scale_x, scale_y, tension=0.25)

        # Area fill
        mongo_area = mongo_path
        first_x = mongo_path_points[0][0]
        last_x = mongo_path_points[-1][0]
        mongo_area += f" L {scale_x(last_x)},{height - padding_bottom} L {scale_x(first_x)},{height - padding_bottom} Z"

        svg += f'''                <path d="{mongo_area}" fill="url(#mongoGrad_{id(mongo_points)})" opacity="0.6"/>
                <path d="{mongo_path}" stroke="#667eea" stroke-width="3.5" fill="none" stroke-linecap="round" stroke-linejoin="round" filter="url(#shadow_{id(title)})"/>
'''

        for _, y_val, x_pos in mongo_points:
            x, y = scale_x(x_pos), scale_y(y_val)
            svg += f'''                <circle cx="{x}" cy="{y}" r="6" fill="white" stroke="#667eea" stroke-width="3"/>
                <circle cx="{x}" cy="{y}" r="3" fill="#667eea"/>
'''

    # Oracle data
    if oracle_points:
        oracle_path_points = [(p[2], p[1]) for p in oracle_points]
        oracle_path = create_smooth_path(oracle_path_points, scale_x, scale_y, tension=0.25)

        # Area fill
        oracle_area = oracle_path
        first_x = oracle_path_points[0][0]
        last_x = oracle_path_points[-1][0]
        oracle_area += f" L {scale_x(last_x)},{height - padding_bottom} L {scale_x(first_x)},{height - padding_bottom} Z"

        svg += f'''                <path d="{oracle_area}" fill="url(#oracleGrad_{id(oracle_points)})" opacity="0.6"/>
                <path d="{oracle_path}" stroke="#e74c3c" stroke-width="3.5" fill="none" stroke-linecap="round" stroke-linejoin="round" filter="url(#shadow_{id(title)})"/>
'''

        for _, y_val, x_pos in oracle_points:
            x, y = scale_x(x_pos), scale_y(y_val)
            svg += f'''                <circle cx="{x}" cy="{y}" r="6" fill="white" stroke="#e74c3c" stroke-width="3"/>
                <circle cx="{x}" cy="{y}" r="3" fill="#e74c3c"/>
'''

    # Axis labels
    svg += f'''
                <text x="{width / 2}" y="{height - 12}" text-anchor="middle" font-size="13" font-weight="600" fill="#2c3e50" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif">Document Configuration</text>
                <text x="{padding_left - 50}" y="{height / 2}" text-anchor="middle" font-size="13" font-weight="600" fill="#2c3e50" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" transform="rotate(-90, {padding_left - 50}, {height / 2})">{y_axis_label}</text>

            </svg>
        </div>
    </div>
'''

    return svg


def generate_insertion_performance_charts(data):
    """
    Generate insertion performance charts (both throughput and time) for single and multi-attribute tests.

    Args:
        data: Benchmark data dict with 'single_attribute' and 'multi_attribute' sections

    Returns:
        HTML string with charts
    """
    if not data:
        return "<p>No data available for charts.</p>"

    html = '''<div style="display: flex; align-items: center; justify-content: space-between; margin-top: 40px; margin-bottom: 10px;">
        <h3 style='color: #667eea; margin: 0;'>Insertion Performance</h3>
        <div style="display: flex; gap: 25px; align-items: center; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-size: 14px;">
            <div style="display: flex; align-items: center; gap: 8px;">
                <div style="width: 30px; height: 3px; background: #667eea; border-radius: 2px;"></div>
                <span style="color: #2c3e50; font-weight: 500;">MongoDB</span>
            </div>
            <div style="display: flex; align-items: center; gap: 8px;">
                <div style="width: 30px; height: 3px; background: #e74c3c; border-radius: 2px;"></div>
                <span style="color: #2c3e50; font-weight: 500;">Oracle</span>
            </div>
        </div>
    </div>'''

    # Single-attribute insertion charts
    single_attr = data.get('single_attribute', {})
    mongo_single = single_attr.get('mongodb', [])
    oracle_single = single_attr.get('oracle_jct', [])

    if mongo_single or oracle_single:
        # Throughput chart
        mongo_throughput = [(f"{t['size']}B", t.get('throughput', 0), t['size']) for t in mongo_single if t.get('throughput', 0) > 0]
        oracle_throughput = [(f"{t['size']}B", t.get('throughput', 0), t['size']) for t in oracle_single if t.get('throughput', 0) > 0]

        # Time chart
        mongo_time = [(f"{t['size']}B", t.get('time_ms', 0), t['size']) for t in mongo_single if t.get('time_ms', 0) > 0]
        oracle_time = [(f"{t['size']}B", t.get('time_ms', 0), t['size']) for t in oracle_single if t.get('time_ms', 0) > 0]

        # Generate side-by-side
        html += '<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin: 20px 0;">'
        html += generate_chart(
            mongo_throughput,
            oracle_throughput,
            "Single-Attribute Insertion Throughput",
            "Documents per Second",
            lambda x: f"{int(x):,}"
        )
        html += generate_chart(
            mongo_time,
            oracle_time,
            "Single-Attribute Insertion Time",
            "Milliseconds",
            lambda x: f"{int(x):,}"
        )
        html += '</div>'

    # Multi-attribute insertion charts
    multi_attr = data.get('multi_attribute', {})
    mongo_multi = multi_attr.get('mongodb', [])
    oracle_multi = multi_attr.get('oracle_jct', [])

    if mongo_multi or oracle_multi:
        # Throughput chart - x-axis shows size and attrs
        mongo_throughput = [
            (f"{t['size']}B\n{t.get('attrs', 1)} attrs", t.get('throughput', 0), t['size'] * 100 + t.get('attrs', 1))
            for t in mongo_multi if t.get('throughput', 0) > 0
        ]
        oracle_throughput = [
            (f"{t['size']}B\n{t.get('attrs', 1)} attrs", t.get('throughput', 0), t['size'] * 100 + t.get('attrs', 1))
            for t in oracle_multi if t.get('throughput', 0) > 0
        ]

        # Time chart
        mongo_time = [
            (f"{t['size']}B\n{t.get('attrs', 1)} attrs", t.get('time_ms', 0), t['size'] * 100 + t.get('attrs', 1))
            for t in mongo_multi if t.get('time_ms', 0) > 0
        ]
        oracle_time = [
            (f"{t['size']}B\n{t.get('attrs', 1)} attrs", t.get('time_ms', 0), t['size'] * 100 + t.get('attrs', 1))
            for t in oracle_multi if t.get('time_ms', 0) > 0
        ]

        # Generate side-by-side
        html += '<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin: 20px 0;">'
        html += generate_chart(
            mongo_throughput,
            oracle_throughput,
            "Multi-Attribute Insertion Throughput",
            "Documents per Second",
            lambda x: f"{int(x):,}"
        )
        html += generate_chart(
            mongo_time,
            oracle_time,
            "Multi-Attribute Insertion Time",
            "Milliseconds",
            lambda x: f"{int(x):,}"
        )
        html += '</div>'

    return html


def generate_query_performance_charts(data):
    """
    Generate query performance charts (both throughput and time) for single and multi-attribute tests.

    Args:
        data: Benchmark data dict with 'single_attribute' and 'multi_attribute' sections

    Returns:
        HTML string with charts
    """
    if not data:
        return "<p>No data available for charts.</p>"

    html = '''<div style="display: flex; align-items: center; justify-content: space-between; margin-top: 40px; margin-bottom: 10px;">
        <h3 style='color: #667eea; margin: 0;'>Query Performance</h3>
        <div style="display: flex; gap: 25px; align-items: center; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-size: 14px;">
            <div style="display: flex; align-items: center; gap: 8px;">
                <div style="width: 30px; height: 3px; background: #667eea; border-radius: 2px;"></div>
                <span style="color: #2c3e50; font-weight: 500;">MongoDB</span>
            </div>
            <div style="display: flex; align-items: center; gap: 8px;">
                <div style="width: 30px; height: 3px; background: #e74c3c; border-radius: 2px;"></div>
                <span style="color: #2c3e50; font-weight: 500;">Oracle</span>
            </div>
        </div>
    </div>'''

    # Single-attribute query charts
    single_attr = data.get('single_attribute', {})
    mongo_single = single_attr.get('mongodb', [])
    oracle_single = single_attr.get('oracle_jct', [])

    if mongo_single or oracle_single:
        # Throughput chart
        mongo_throughput = [(f"{t['size']}B", t.get('query_throughput', 0), t['size']) for t in mongo_single if t.get('query_throughput', 0) > 0]
        oracle_throughput = [(f"{t['size']}B", t.get('query_throughput', 0), t['size']) for t in oracle_single if t.get('query_throughput', 0) > 0]

        # Time chart
        mongo_time = [(f"{t['size']}B", t.get('query_time_ms', 0), t['size']) for t in mongo_single if t.get('query_time_ms', 0) > 0]
        oracle_time = [(f"{t['size']}B", t.get('query_time_ms', 0), t['size']) for t in oracle_single if t.get('query_time_ms', 0) > 0]

        if (mongo_throughput or oracle_throughput) and (mongo_time or oracle_time):
            # Generate side-by-side
            html += '<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin: 20px 0;">'
            html += generate_chart(
                mongo_throughput,
                oracle_throughput,
                "Single-Attribute Query Throughput",
                "Queries per Second",
                lambda x: f"{int(x):,}"
            )
            html += generate_chart(
                mongo_time,
                oracle_time,
                "Single-Attribute Query Time",
                "Milliseconds",
                lambda x: f"{int(x):,}"
            )
            html += '</div>'

    # Multi-attribute query charts
    multi_attr = data.get('multi_attribute', {})
    mongo_multi = multi_attr.get('mongodb', [])
    oracle_multi = multi_attr.get('oracle_jct', [])

    if mongo_multi or oracle_multi:
        # Throughput chart
        mongo_throughput = [
            (f"{t['size']}B\n{t.get('attrs', 1)} attrs", t.get('query_throughput', 0), t['size'] * 100 + t.get('attrs', 1))
            for t in mongo_multi if t.get('query_throughput', 0) > 0
        ]
        oracle_throughput = [
            (f"{t['size']}B\n{t.get('attrs', 1)} attrs", t.get('query_throughput', 0), t['size'] * 100 + t.get('attrs', 1))
            for t in oracle_multi if t.get('query_throughput', 0) > 0
        ]

        # Time chart
        mongo_time = [
            (f"{t['size']}B\n{t.get('attrs', 1)} attrs", t.get('query_time_ms', 0), t['size'] * 100 + t.get('attrs', 1))
            for t in mongo_multi if t.get('query_time_ms', 0) > 0
        ]
        oracle_time = [
            (f"{t['size']}B\n{t.get('attrs', 1)} attrs", t.get('query_time_ms', 0), t['size'] * 100 + t.get('attrs', 1))
            for t in oracle_multi if t.get('query_time_ms', 0) > 0
        ]

        if (mongo_throughput or oracle_throughput) and (mongo_time or oracle_time):
            # Generate side-by-side
            html += '<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin: 20px 0;">'
            html += generate_chart(
                mongo_throughput,
                oracle_throughput,
                "Multi-Attribute Query Throughput",
                "Queries per Second",
                lambda x: f"{int(x):,}"
            )
            html += generate_chart(
                mongo_time,
                oracle_time,
                "Multi-Attribute Query Time",
                "Milliseconds",
                lambda x: f"{int(x):,}"
            )
            html += '</div>'

    return html


# Legacy functions for backward compatibility
def generate_query_performance_chart(data, title="Query Performance by Document Size"):
    """Legacy function - redirects to new chart generation."""
    return generate_query_performance_charts(data)


def generate_insertion_performance_chart(data, title="Insertion Performance by Document Size"):
    """Legacy function - redirects to new chart generation."""
    return generate_insertion_performance_charts(data)
