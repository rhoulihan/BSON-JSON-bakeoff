"""
Benchmark data formatting module for generating HTML tables and summaries.
"""


def format_benchmark_table(data, test_category):
    """
    Generate HTML table for benchmark results.

    Args:
        data: Benchmark results dictionary
        test_category: One of 'indexed' or 'noindex'

    Returns:
        HTML string with formatted benchmark table
    """
    if not data:
        return "<p>No benchmark data available.</p>"

    html = '<div class="benchmark-results">\n'

    # Single Attribute Tests
    single_attr = data.get('single_attribute', {})
    if single_attr:
        html += generate_test_section(single_attr, "Single Attribute Tests", test_category)

    # Multi Attribute Tests
    multi_attr = data.get('multi_attribute', {})
    if multi_attr:
        html += generate_test_section(multi_attr, "Multi-Attribute Tests", test_category)

    html += '</div>\n'
    return html


def generate_test_section(tests_dict, title, test_category):
    """Generate HTML for a test section (single or multi-attribute)."""
    html = f'<h3 style="margin-top: 30px; color: #667eea;">{title}</h3>\n'

    # Get MongoDB and Oracle results (handle both key variants)
    mongodb_tests = tests_dict.get('mongodb_bson', tests_dict.get('mongodb', []))
    oracle_tests = tests_dict.get('oracle_jct', [])

    if not mongodb_tests and not oracle_tests:
        return html + "<p>No test data available.</p>\n"

    # Determine if query tests were run
    has_queries = test_category == 'indexed' or any(t.get('query_time_ms') for t in mongodb_tests + oracle_tests)

    # Generate table
    html += '''
    <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
        <thead>
            <tr style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white;">
                <th style="padding: 12px; text-align: left; border: 1px solid #ddd;">Database</th>
                <th style="padding: 12px; text-align: right; border: 1px solid #ddd;">Doc Size</th>
                <th style="padding: 12px; text-align: right; border: 1px solid #ddd;">Attributes</th>
                <th style="padding: 12px; text-align: right; border: 1px solid #ddd;">Insert Time</th>
                <th style="padding: 12px; text-align: right; border: 1px solid #ddd;">Insert Rate</th>
    '''

    if has_queries:
        html += '''
                <th style="padding: 12px; text-align: right; border: 1px solid #ddd;">Query Time</th>
                <th style="padding: 12px; text-align: right; border: 1px solid #ddd;">Query Rate</th>
        '''

    html += '''
            </tr>
        </thead>
        <tbody>
    '''

    # Combine and sort tests by size
    all_tests = []
    for test in mongodb_tests:
        all_tests.append(('MongoDB BSON', test))
    for test in oracle_tests:
        all_tests.append(('Oracle JCT', test))

    all_tests.sort(key=lambda x: (x[1].get('size', 0), x[1].get('attrs', 0)))

    for db_name, test in all_tests:
        db_color = '#667eea' if db_name == 'MongoDB BSON' else '#e74c3c'
        bg_color = 'rgba(102, 126, 234, 0.05)' if db_name == 'MongoDB BSON' else 'rgba(231, 76, 60, 0.05)'

        size = test.get('size', 0)
        attrs = test.get('attrs', 1)
        insert_time = test.get('time_ms', 0)
        insert_rate = test.get('throughput', 0)

        html += f'''
            <tr style="background: {bg_color}; border-bottom: 1px solid #eee;">
                <td style="padding: 10px; border: 1px solid #ddd;">
                    <span style="color: {db_color}; font-weight: bold;">●</span> {db_name}
                </td>
                <td style="padding: 10px; text-align: right; border: 1px solid #ddd; font-family: monospace;">
                    {size}B
                </td>
                <td style="padding: 10px; text-align: right; border: 1px solid #ddd; font-family: monospace;">
                    {attrs}
                </td>
                <td style="padding: 10px; text-align: right; border: 1px solid #ddd; font-family: monospace;">
                    {insert_time:,}ms
                </td>
                <td style="padding: 10px; text-align: right; border: 1px solid #ddd; font-family: monospace;">
                    {insert_rate:,.0f} docs/sec
                </td>
        '''

        if has_queries:
            query_time = test.get('query_time_ms', 0)
            query_rate = test.get('query_throughput', 0)
            if query_time > 0:
                html += f'''
                <td style="padding: 10px; text-align: right; border: 1px solid #ddd; font-family: monospace;">
                    {query_time:,}ms
                </td>
                <td style="padding: 10px; text-align: right; border: 1px solid #ddd; font-family: monospace;">
                    {query_rate:,.0f} qps
                </td>
                '''
            else:
                html += '''
                <td style="padding: 10px; text-align: center; border: 1px solid #ddd; color: #999;">-</td>
                <td style="padding: 10px; text-align: center; border: 1px solid #ddd; color: #999;">-</td>
                '''

        html += '            </tr>\n'

    html += '''
        </tbody>
    </table>
    '''

    return html


def calculate_summary_stats(data):
    """
    Calculate summary statistics from benchmark data.

    Returns:
        Dictionary with summary stats
    """
    if not data:
        return None

    stats = {
        'mongodb': {'insert_avg': 0, 'query_avg': 0, 'tests': 0},
        'oracle': {'insert_avg': 0, 'query_avg': 0, 'tests': 0}
    }

    # Process single attribute tests
    single_attr = data.get('single_attribute', {})
    mongodb_tests = single_attr.get('mongodb_bson', single_attr.get('mongodb', []))
    oracle_tests = single_attr.get('oracle_jct', [])

    if mongodb_tests:
        stats['mongodb']['insert_avg'] = sum(t.get('throughput', 0) for t in mongodb_tests) / len(mongodb_tests)
        query_tests = [t for t in mongodb_tests if t.get('query_throughput', 0) > 0]
        if query_tests:
            stats['mongodb']['query_avg'] = sum(t.get('query_throughput', 0) for t in query_tests) / len(query_tests)
        stats['mongodb']['tests'] = len(mongodb_tests)

    if oracle_tests:
        stats['oracle']['insert_avg'] = sum(t.get('throughput', 0) for t in oracle_tests) / len(oracle_tests)
        query_tests = [t for t in oracle_tests if t.get('query_throughput', 0) > 0]
        if query_tests:
            stats['oracle']['query_avg'] = sum(t.get('query_throughput', 0) for t in query_tests) / len(query_tests)
        stats['oracle']['tests'] = len(oracle_tests)

    # Add multi-attribute tests
    multi_attr = data.get('multi_attribute', {})
    mongodb_multi = multi_attr.get('mongodb_bson', multi_attr.get('mongodb', []))
    oracle_multi = multi_attr.get('oracle_jct', [])

    if mongodb_multi:
        multi_insert_avg = sum(t.get('throughput', 0) for t in mongodb_multi) / len(mongodb_multi)
        if stats['mongodb']['tests'] > 0:
            total_tests = stats['mongodb']['tests'] + len(mongodb_multi)
            stats['mongodb']['insert_avg'] = (stats['mongodb']['insert_avg'] * stats['mongodb']['tests'] +
                                             multi_insert_avg * len(mongodb_multi)) / total_tests
        else:
            stats['mongodb']['insert_avg'] = multi_insert_avg
        stats['mongodb']['tests'] += len(mongodb_multi)

    if oracle_multi:
        multi_insert_avg = sum(t.get('throughput', 0) for t in oracle_multi) / len(oracle_multi)
        if stats['oracle']['tests'] > 0:
            total_tests = stats['oracle']['tests'] + len(oracle_multi)
            stats['oracle']['insert_avg'] = (stats['oracle']['insert_avg'] * stats['oracle']['tests'] +
                                            multi_insert_avg * len(oracle_multi)) / total_tests
        else:
            stats['oracle']['insert_avg'] = multi_insert_avg
        stats['oracle']['tests'] += len(oracle_multi)

    # Calculate ratios
    if stats['oracle']['insert_avg'] > 0:
        stats['insert_ratio'] = stats['mongodb']['insert_avg'] / stats['oracle']['insert_avg']
    else:
        stats['insert_ratio'] = 0

    if stats['oracle']['query_avg'] > 0:
        stats['query_ratio'] = stats['mongodb']['query_avg'] / stats['oracle']['query_avg']
    else:
        stats['query_ratio'] = 0

    return stats
