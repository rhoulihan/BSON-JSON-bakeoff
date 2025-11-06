"""
Data enrichment module to merge query metrics from flame graph analysis
into benchmark results for comprehensive reporting.
"""


def enrich_benchmark_data_with_query_metrics(benchmark_data, flamegraph_summaries):
    """
    Enrich benchmark data with query metrics from flame graph summaries.

    Args:
        benchmark_data: Dict from article_benchmark_results.json (may lack query data)
        flamegraph_summaries: Dict from flamegraph_summaries.json (has query data)

    Returns:
        Enriched benchmark data with query metrics added
    """
    if not benchmark_data or not flamegraph_summaries:
        return benchmark_data

    # Create a copy to avoid modifying original
    import copy
    enriched = copy.deepcopy(benchmark_data)

    # Helper to match tests by size and attrs
    def find_matching_test(fg_test, benchmark_tests):
        """Find benchmark test that matches flame graph test by size/attrs."""
        desc = fg_test.get('description', '')

        # Extract size and attrs from description
        # Format: "10B 1-attr insertion test" or "200B 10-attr query test"
        parts = desc.split()
        if len(parts) < 2:
            return None

        try:
            size_str = parts[0].replace('B', '')
            size = int(size_str)

            attrs_str = parts[1].replace('-attr', '')
            attrs = int(attrs_str)

            # Find matching test
            for test in benchmark_tests:
                if test.get('size') == size and test.get('attrs') == attrs:
                    return test
        except (ValueError, IndexError):
            pass

        return None

    # Helper to extract query metrics from flame graph test
    def get_query_metrics(fg_test):
        """Extract query metrics from flame graph test."""
        perf = fg_test.get('performance', {})
        query = perf.get('query', {})

        if not query:
            return None

        return {
            'query_throughput': query.get('queries_per_sec', 0),
            'query_time_ms': query.get('time_ms', 0)
        }

    # Enrich single_attribute tests
    if 'single_attribute' in enriched and 'single_attribute' in flamegraph_summaries:
        fg_tests = flamegraph_summaries['single_attribute']

        # Separate by database
        mongo_fg = [t for t in fg_tests if t['database'] == 'MongoDB BSON']
        oracle_fg = [t for t in fg_tests if t['database'] == 'Oracle JCT']

        # Enrich MongoDB tests
        mongo_tests = enriched['single_attribute'].get('mongodb', [])
        for fg_test in mongo_fg:
            match = find_matching_test(fg_test, mongo_tests)
            if match:
                query_metrics = get_query_metrics(fg_test)
                if query_metrics:
                    match.update(query_metrics)

        # Enrich Oracle tests
        oracle_tests = enriched['single_attribute'].get('oracle_jct', [])
        for fg_test in oracle_fg:
            match = find_matching_test(fg_test, oracle_tests)
            if match:
                query_metrics = get_query_metrics(fg_test)
                if query_metrics:
                    match.update(query_metrics)

    # Enrich multi_attribute tests
    if 'multi_attribute' in enriched and 'multi_attribute' in flamegraph_summaries:
        fg_tests = flamegraph_summaries['multi_attribute']

        # Separate by database
        mongo_fg = [t for t in fg_tests if t['database'] == 'MongoDB BSON']
        oracle_fg = [t for t in fg_tests if t['database'] == 'Oracle JCT']

        # Enrich MongoDB tests
        mongo_tests = enriched['multi_attribute'].get('mongodb', [])
        for fg_test in mongo_fg:
            match = find_matching_test(fg_test, mongo_tests)
            if match:
                query_metrics = get_query_metrics(fg_test)
                if query_metrics:
                    match.update(query_metrics)

        # Enrich Oracle tests
        oracle_tests = enriched['multi_attribute'].get('oracle_jct', [])
        for fg_test in oracle_fg:
            match = find_matching_test(fg_test, oracle_tests)
            if match:
                query_metrics = get_query_metrics(fg_test)
                if query_metrics:
                    match.update(query_metrics)

    return enriched


def enrich_all_configurations(all_data, all_summaries):
    """
    Enrich all configuration data (local/remote, indexed/noindex).

    Args:
        all_data: Dict with keys 'local_indexed', 'local_noindex', etc.
        all_summaries: Dict from flamegraph_summaries.json

    Returns:
        Dict with enriched data for all configurations
    """
    enriched = {}

    config_mappings = {
        'local_indexed': 'local_indexed',
        'local_noindex': 'local_noindex',
        'remote_indexed': 'remote_indexed',
        'remote_noindex': 'remote_noindex'
    }

    for data_key, summary_key in config_mappings.items():
        if all_data.get(data_key) and all_summaries and summary_key in all_summaries:
            enriched[data_key] = enrich_benchmark_data_with_query_metrics(
                all_data[data_key],
                {'single_attribute': [t for t in all_summaries[summary_key]],
                 'multi_attribute': []}  # Summaries combine both in flat list
            )
        else:
            enriched[data_key] = all_data.get(data_key)

    return enriched
