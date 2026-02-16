package com.mongodb;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * Collects per-operation latency measurements for SaaS/cloud database benchmarks.
 * Records individual batch insert and query latencies, then calculates
 * min, max, avg, p50, p95, p99 percentile statistics.
 */
public class LatencyCollector {
    private final List<Double> samples = new ArrayList<>();
    private final List<Long> timestamps = new ArrayList<>();
    private final String operationType;

    public LatencyCollector(String operationType) {
        this.operationType = operationType;
    }

    /**
     * Record a single operation's latency.
     * @param latencyMs latency in milliseconds (fractional)
     */
    public void record(double latencyMs) {
        samples.add(latencyMs);
        timestamps.add(System.currentTimeMillis());
    }

    /**
     * Record a single operation's latency measured in nanoseconds.
     * Converts to milliseconds internally.
     * @param latencyNanos latency in nanoseconds
     */
    public void recordNanos(long latencyNanos) {
        record(latencyNanos / 1_000_000.0);
    }

    public int getSampleCount() {
        return samples.size();
    }

    public double getMin() {
        if (samples.isEmpty()) return 0;
        return Collections.min(samples);
    }

    public double getMax() {
        if (samples.isEmpty()) return 0;
        return Collections.max(samples);
    }

    public double getAvg() {
        if (samples.isEmpty()) return 0;
        double sum = 0;
        for (double s : samples) sum += s;
        return sum / samples.size();
    }

    public double getPercentile(double percentile) {
        if (samples.isEmpty()) return 0;
        List<Double> sorted = new ArrayList<>(samples);
        Collections.sort(sorted);
        int index = (int) Math.ceil(percentile / 100.0 * sorted.size()) - 1;
        index = Math.max(0, Math.min(index, sorted.size() - 1));
        return sorted.get(index);
    }

    public double getP50() { return getPercentile(50); }
    public double getP95() { return getPercentile(95); }
    public double getP99() { return getPercentile(99); }

    /**
     * Output latency statistics in a structured, parseable format.
     * Format: LATENCY_STATS|<type>|<json>
     */
    public void printStats() {
        if (samples.isEmpty()) return;

        StringBuilder sb = new StringBuilder();
        sb.append("LATENCY_STATS|").append(operationType).append("|{");
        sb.append("\"operation\":\"").append(operationType).append("\",");
        sb.append("\"sample_count\":").append(samples.size()).append(",");
        sb.append(String.format("\"min_ms\":%.2f,", getMin()));
        sb.append(String.format("\"max_ms\":%.2f,", getMax()));
        sb.append(String.format("\"avg_ms\":%.2f,", getAvg()));
        sb.append(String.format("\"p50_ms\":%.2f,", getP50()));
        sb.append(String.format("\"p95_ms\":%.2f,", getP95()));
        sb.append(String.format("\"p99_ms\":%.2f,", getP99()));

        // Output all samples for latency-over-time analysis
        sb.append("\"samples\":[");
        for (int i = 0; i < samples.size(); i++) {
            if (i > 0) sb.append(",");
            sb.append(String.format("{\"ts\":%d,\"ms\":%.2f}", timestamps.get(i), samples.get(i)));
        }
        sb.append("]}");

        System.out.println(sb.toString());
    }
}
