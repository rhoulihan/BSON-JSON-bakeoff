"""
Convert flamegraph summaries format to benchmark results format for unified reporting.
This eliminates the need for article_benchmark_results.json.
"""


def convert_flamegraph_to_benchmark_format(fg_tests):
    """
    Convert flame graph test list to benchmark results format.

    Args:
        fg_tests: List of tests from flamegraph_summaries.json

    Returns:
        Dict in benchmark results format with single_attribute and multi_attribute sections
    """
    if not fg_tests:
        return {'single_attribute': {}, 'multi_attribute': {}}

    # Separate tests by type
    single_tests = [t for t in fg_tests if 'single attribute' in t.get('description', '')]
    multi_tests = [t for t in fg_tests if '×' in t.get('description', '')]

    # Convert tests to benchmark format
    def convert_test(fg_test):
        """Convert single flame graph test to benchmark format."""
        perf = fg_test.get('performance', {})
        insertion = perf.get('insertion', {})
        query = perf.get('query', {})

        # Extract size and attrs from description
        desc = fg_test.get('description', '')
        size = 0
        attrs = 1

        if 'single attribute' in desc:
            # Format: "10B single attribute" or "200B single attribute"
            parts = desc.split()
            if parts:
                size_str = parts[0].replace('B', '')
                try:
                    size = int(size_str)
                except ValueError:
                    pass
        elif '×' in desc:
            # Format: "10 attributes × 1B = 10B"
            parts = desc.split()
            if len(parts) >= 5:
                try:
                    attrs = int(parts[0])
                    size_per_attr = int(parts[3].replace('B', ''))
                    size = int(parts[5].replace('B', ''))
                except (ValueError, IndexError):
                    pass

        result = {
            'size': size,
            'attrs': attrs,
            'time_ms': insertion.get('time_ms', 0),
            'throughput': insertion.get('docs_per_sec', 0)
        }

        # Add query data if present
        if query:
            result['query_time_ms'] = query.get('time_ms', 0)
            result['query_throughput'] = query.get('queries_per_sec', 0)

        return result

    # Separate by database
    mongo_single = [convert_test(t) for t in single_tests if t.get('database') == 'MongoDB BSON']
    oracle_single = [convert_test(t) for t in single_tests if t.get('database') == 'Oracle JCT']

    mongo_multi = [convert_test(t) for t in multi_tests if t.get('database') == 'MongoDB BSON']
    oracle_multi = [convert_test(t) for t in multi_tests if t.get('database') == 'Oracle JCT']

    return {
        'single_attribute': {
            'mongodb': mongo_single,
            'oracle_jct': oracle_single
        },
        'multi_attribute': {
            'mongodb': mongo_multi,
            'oracle_jct': oracle_multi
        }
    }


def convert_all_configurations(fg_summaries):
    """
    Convert all flame graph summaries to benchmark format.

    Args:
        fg_summaries: Dict from flamegraph_summaries.json with keys like 'local_indexed', etc.

    Returns:
        Dict with same keys, but values in benchmark format
    """
    if not fg_summaries:
        return {}

    result = {}
    for config_key, tests in fg_summaries.items():
        result[config_key] = convert_flamegraph_to_benchmark_format(tests)

    return result
