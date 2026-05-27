// sniffer/src/userspace/ml_defender_features.cpp
// ML Defender - Phase 1, Day 2
// Implementation of 40 features for 4 embedded detectors
//
// STATUS: 22 features implemented, 18 with honest TODOs
// PHILOSOPHY: Works > Perfect, measure before optimize

#include "ml_defender_features.hpp"
#include <cmath>
#include <map>
#include <algorithm>
#include <numeric>

// Protobuf header - path configured in CMakeLists.txt via ${CMAKE_BINARY_DIR}/proto
#include "proto/network_security.pb.h"

namespace sniffer {

// ============================================================================
// DDOS FEATURES (10 features)
// ============================================================================

void MLDefenderExtractor::extract_ddos_features(
    const FlowStatistics& flow,
    ::protobuf::DDoSFeatures* ddos) const {

    ddos->set_syn_ack_ratio(extract_ddos_syn_ack_ratio(flow));
    ddos->set_packet_symmetry(extract_ddos_packet_symmetry(flow));
    ddos->set_source_ip_dispersion(extract_ddos_source_ip_dispersion(flow));
    ddos->set_protocol_anomaly_score(extract_ddos_protocol_anomaly_score(flow));
    ddos->set_packet_size_entropy(extract_ddos_packet_size_entropy(flow));
    ddos->set_traffic_amplification_factor(extract_ddos_traffic_amplification_factor(flow));
    ddos->set_flow_completion_rate(extract_ddos_flow_completion_rate(flow));
    ddos->set_geographical_concentration(extract_ddos_geographical_concentration(flow));
    ddos->set_traffic_escalation_rate(extract_ddos_traffic_escalation_rate(flow));
    ddos->set_resource_saturation_score(extract_ddos_resource_saturation_score(flow));
}

float MLDefenderExtractor::extract_ddos_syn_ack_ratio(const FlowStatistics& flow) const {
    // SYN/ACK ratio: High ratio indicates potential SYN flood
    // Normal TCP: ratio ≈ 1.0, SYN flood: ratio > 5.0
    float syn_count = static_cast<float>(flow.syn_count);
    float ack_count = static_cast<float>(flow.ack_count);

    // Add 1.0 to denominator to avoid extreme values for low counts
    float ratio = safe_divide(syn_count, ack_count + 1.0f);

    // Cap at 10.0 to avoid extreme outliers
    return std::min(ratio, 10.0f);
}

float MLDefenderExtractor::extract_ddos_packet_symmetry(const FlowStatistics& flow) const {
    // Packet symmetry: DDoS often shows highly asymmetric patterns
    // 0.0 = perfect symmetry, 1.0 = completely one-directional
    uint64_t total = flow.spkts + flow.dpkts;
    if (total == 0) return 0.0f;

    int64_t diff = static_cast<int64_t>(flow.spkts) - static_cast<int64_t>(flow.dpkts);
    float asymmetry = static_cast<float>(std::abs(diff)) / static_cast<float>(total);

    return asymmetry;
}

float MLDefenderExtractor::extract_ddos_source_ip_dispersion(const FlowStatistics& /*flow*/) const {
    if (!aggregator_) return MISSING_FEATURE_SENTINEL;
    auto now = TimeWindowAggregator::get_current_time_ns();
    auto start = now - 30'000'000'000ULL;
    auto stats = aggregator_->get_window_stats(start, now);
    if (stats.event_count == 0) return 0.0f;
    return std::min(
        std::log2f(static_cast<float>(stats.unique_ips_count) + 1.0f) /
        std::log2f(static_cast<float>(stats.event_count) + 2.0f),
        1.0f);
}

float MLDefenderExtractor::extract_ddos_protocol_anomaly_score(const FlowStatistics& flow) const {
    // Protocol anomaly: Unusual flag combinations or patterns
    // 0.0 = normal, 1.0 = highly anomalous

    uint64_t total_packets = flow.spkts + flow.dpkts;
    if (total_packets == 0) return 0.0f;

    float anomaly_score = 0.0f;

    // Check 1: High SYN without corresponding ACK (incomplete handshakes)
    if (flow.syn_count > flow.ack_count * 2) {
        anomaly_score += 0.3f;
    }

    // Check 2: Excessive RST (connection refused/reset attacks)
    float rst_ratio = safe_divide(static_cast<float>(flow.rst_count),
                                   static_cast<float>(total_packets));
    if (rst_ratio > 0.3f) {
        anomaly_score += 0.3f;
    }

    // Check 3: FIN without proper handshake completion
    if (flow.fin_count > 0 && flow.ack_count < flow.fin_count) {
        anomaly_score += 0.2f;
    }

    // Check 4: Unusual URG flag usage (rare in normal traffic)
    if (flow.urg_count > 0) {
        anomaly_score += 0.2f;
    }

    return std::min(anomaly_score, 1.0f);
}

float MLDefenderExtractor::extract_ddos_packet_size_entropy(const FlowStatistics& flow) const {
    // Packet size entropy: DDoS often has uniform packet sizes (low entropy)
    // Normal traffic: varied sizes (high entropy)
    return calculate_entropy(flow.all_lengths);
}

float MLDefenderExtractor::extract_ddos_traffic_amplification_factor(const FlowStatistics& flow) const {
    // Amplification factor: Ratio of response to request bytes
    // DNS/NTP amplification attacks have high factors (>10x)
    float amplification = safe_divide(
        static_cast<float>(flow.dbytes),  // Backward (response)
        static_cast<float>(flow.sbytes)   // Forward (request)
    );

    // Cap at 100.0 to avoid extreme outliers
    return std::min(amplification, 100.0f);
}

float MLDefenderExtractor::extract_ddos_flow_completion_rate(const FlowStatistics& flow) const {
    // Flow completion: TCP flows that complete proper handshake and termination
    // 1.0 = complete, 0.5 = established but not closed, 0.0 = incomplete

    bool has_syn = flow.syn_count > 0;
    bool has_ack = flow.ack_count > 0;
    bool has_fin = flow.fin_count > 0;

    if (has_syn && has_ack && has_fin) {
        return 1.0f;  // Complete connection
    } else if (has_syn && has_ack) {
        return 0.5f;  // Established but not closed
    } else {
        return 0.0f;  // Incomplete
    }
}

float MLDefenderExtractor::extract_ddos_geographical_concentration(const FlowStatistics& /* flow */) const {
    // TODO(Phase 2): GeoIP deliberately NOT in critical path
    //
    // ARCHITECTURAL DECISION:
    // GeoIP lookups introduce unacceptable latency (100-500ms REST calls)
    // in a sub-microsecond pipeline.
    //
    // GeoIP will be calculated AFTER blocking decision by RAG when needed
    // for post-mortem analysis, NOT for the blocking decision itself.
    //
    // Rationale: Geographic location is USEFUL context but NOT NECESSARY
    // for determining if traffic is an attack. A SYN flood is a SYN flood
    // whether it comes from China, Russia, or USA.
    //
    // For Phase 1: Return neutral value
    // For Phase 2: GeoIP service available to RAG for analysis queries
    return MISSING_FEATURE_SENTINEL;
}

float MLDefenderExtractor::extract_ddos_traffic_escalation_rate(const FlowStatistics& flow) const {
    // Traffic escalation: How quickly traffic volume increases
    // Measured as packets per second
    float pps = calculate_packet_rate(flow);

    // Normalize: 0-100 pps = 0.0, 1000+ pps = 1.0
    float normalized = pps / 1000.0f;
    return std::min(normalized, 1.0f);
}

float MLDefenderExtractor::extract_ddos_resource_saturation_score(const FlowStatistics& flow) const {
    // Resource saturation: Combination of high rate + small packets + many connections
    // Small packets are more CPU-intensive to process

    float avg_size = calculate_mean(flow.all_lengths);
    float pps = calculate_packet_rate(flow);

    // Small packet factor: <100 bytes is suspicious
    float small_packet_factor = (avg_size < 100.0f) ? 1.0f : 0.0f;

    // High rate factor: >500 pps is high
    float high_rate_factor = (pps > 500.0f) ? 1.0f : 0.0f;

    // Combined score
    float saturation = (small_packet_factor + high_rate_factor) / 2.0f;
    return saturation;
}

// ============================================================================
// RANSOMWARE FEATURES (10 features)
// ============================================================================

void MLDefenderExtractor::extract_ransomware_features(
    const FlowStatistics& flow,
    ::protobuf::RansomwareEmbeddedFeatures* ransomware) const {

    ransomware->set_io_intensity(extract_ransomware_io_intensity(flow));
    ransomware->set_entropy(extract_ransomware_entropy(flow));
    ransomware->set_resource_usage(extract_ransomware_resource_usage(flow));
    ransomware->set_network_activity(extract_ransomware_network_activity(flow));
    ransomware->set_file_operations(extract_ransomware_file_operations(flow));
    ransomware->set_process_anomaly(extract_ransomware_process_anomaly(flow));
    ransomware->set_temporal_pattern(extract_ransomware_temporal_pattern(flow));
    ransomware->set_access_frequency(extract_ransomware_access_frequency(flow));
    ransomware->set_data_volume(extract_ransomware_data_volume(flow));
    ransomware->set_behavior_consistency(extract_ransomware_behavior_consistency(flow));
}

float MLDefenderExtractor::extract_ransomware_io_intensity(const FlowStatistics& /*flow*/) const {
    // TODO(Phase 2): Requires system-level I/O metrics
    //
    // This feature measures file system I/O operations (reads/writes per second).
    // Cannot be derived from network flow data alone.
    //
    // Options for Phase 2:
    // 1. Integrate with eBPF tracepoints for file operations
    // 2. Add system metrics collector component
    // 3. Correlate network flow with endpoint agent data
    //
    // For Phase 1: Return neutral value
    return MISSING_FEATURE_SENTINEL;
}

float MLDefenderExtractor::extract_ransomware_entropy(const FlowStatistics& flow) const {
    // Entropy: High entropy in packet sizes suggests encryption
    // Ransomware encrypts files before exfiltration
    float entropy = calculate_entropy(flow.all_lengths);

    // Normalize: entropy typically 0-5 for packet sizes
    float normalized = entropy / 5.0f;
    return std::min(normalized, 1.0f);
}

float MLDefenderExtractor::extract_ransomware_resource_usage(const FlowStatistics& /*flow*/) const {
    // TODO(Phase 2): Requires CPU/memory metrics from system
    //
    // Ransomware typically shows high CPU usage during encryption phase.
    // This requires system-level resource monitoring, not network flow data.
    //
    // For Phase 1: Return neutral value
    return MISSING_FEATURE_SENTINEL;
}

float MLDefenderExtractor::extract_ransomware_network_activity(const FlowStatistics& flow) const {
    // Network activity: Packet rate + byte rate combined
    float pps = calculate_packet_rate(flow);
    float bps = calculate_byte_rate(flow);

    // Normalize both and average
    float pps_normalized = std::min(pps / 1000.0f, 1.0f);
    float bps_normalized = std::min(bps / 1000000.0f, 1.0f);  // 1 Mbps

    return (pps_normalized + bps_normalized) / 2.0f;
}

float MLDefenderExtractor::extract_ransomware_file_operations(const FlowStatistics& /*flow*/) const {
    // TODO(Phase 2): Requires protocol inspection for SMB/CIFS
    //
    // File operations require deep packet inspection to identify:
    // - SMB/CIFS packets (port 445)
    // - File open/close/read/write commands
    // - Unusual access patterns
    //
    // Options for Phase 2:
    // 1. Add protocol field to FlowStatistics
    // 2. Implement SMB parser in userspace
    // 3. Count packets to port 445 as proxy metric
    //
    // For Phase 1: Return neutral value
    return MISSING_FEATURE_SENTINEL;
}

float MLDefenderExtractor::extract_ransomware_process_anomaly(const FlowStatistics& /*flow*/) const {
    // TODO(Phase 2): Requires process-level monitoring
    //
    // Process anomaly detection requires:
    // - Process name and parent process
    // - Command line arguments
    // - Process behavior baseline
    //
    // This is outside the scope of network flow analysis.
    // Consider integration with endpoint agent or eBPF process monitoring.
    //
    // For Phase 1: Return neutral value
    return MISSING_FEATURE_SENTINEL;
}

float MLDefenderExtractor::extract_ransomware_temporal_pattern(const FlowStatistics& flow) const {
    // Temporal pattern: Regularity vs randomness in packet timing
    // Ransomware often shows regular patterns during C2 communication
    float cv = calculate_iat_coefficient_of_variation(flow.packet_timestamps);

    // Low CoV (< 0.5) = regular pattern (suspicious)
    // High CoV (> 1.0) = random pattern (normal)
    if (cv < 0.5f) {
        return 0.8f;  // Suspicious regular pattern
    } else if (cv > 1.0f) {
        return 0.2f;  // Normal random pattern
    } else {
        return MISSING_FEATURE_SENTINEL;  // Neutral
    }
}

float MLDefenderExtractor::extract_ransomware_access_frequency(const FlowStatistics& flow) const {
    // Access frequency: Packet rate as proxy
    float pps = calculate_packet_rate(flow);

    // Normalize: 0-100 pps = 0.0-1.0
    float normalized = pps / 100.0f;
    return std::min(normalized, 1.0f);
}

float MLDefenderExtractor::extract_ransomware_data_volume(const FlowStatistics& flow) const {
    // Data volume: Total bytes transferred
    uint64_t total_bytes = flow.sbytes + flow.dbytes;

    // Log scale normalization: 0-10MB range
    float log_bytes = std::log10(static_cast<float>(total_bytes + 1));
    float normalized = log_bytes / 7.0f;  // log10(10MB) ≈ 7

    return std::min(normalized, 1.0f);
}

float MLDefenderExtractor::extract_ransomware_behavior_consistency(const FlowStatistics& flow) const {
    // Behavior consistency: Low std dev in IAT = consistent behavior
    float iat_std = calculate_iat_std_dev(flow.packet_timestamps);
    float iat_mean = calculate_iat_mean(flow.packet_timestamps);

    if (iat_mean == 0.0f) return MISSING_FEATURE_SENTINEL;

    float cv = iat_std / iat_mean;

    // Low CV = high consistency (0.0-0.3 → 1.0-0.7)
    // High CV = low consistency (0.3+ → 0.7-0.0)
    float consistency = std::max(0.0f, 1.0f - cv);
    return consistency;
}

// ============================================================================
// TRAFFIC FEATURES (10 features)
// ============================================================================

void MLDefenderExtractor::extract_traffic_features(
    const FlowStatistics& flow,
    ::protobuf::TrafficFeatures* traffic) const {

    traffic->set_packet_rate(extract_traffic_packet_rate(flow));
    traffic->set_connection_rate(extract_traffic_connection_rate(flow));
    traffic->set_tcp_udp_ratio(extract_traffic_tcp_udp_ratio(flow));
    traffic->set_avg_packet_size(extract_traffic_avg_packet_size(flow));
    traffic->set_port_entropy(extract_traffic_port_entropy(flow));
    traffic->set_flow_duration_std(extract_traffic_flow_duration_std(flow));
    traffic->set_src_ip_entropy(extract_traffic_src_ip_entropy(flow));
    traffic->set_dst_ip_concentration(extract_traffic_dst_ip_concentration(flow));
    traffic->set_protocol_variety(extract_traffic_protocol_variety(flow));
    traffic->set_temporal_consistency(extract_traffic_temporal_consistency(flow));
}

float MLDefenderExtractor::extract_traffic_packet_rate(const FlowStatistics& flow) const {
    // Packets per second
    float pps = calculate_packet_rate(flow);

    // Normalize: 0-1000 pps = 0.0-1.0
    float normalized = pps / 1000.0f;
    return std::min(normalized, 1.0f);
}

float MLDefenderExtractor::extract_traffic_connection_rate(const FlowStatistics& /*flow*/) const {
    if (!aggregator_) return MISSING_FEATURE_SENTINEL;
    auto now = TimeWindowAggregator::get_current_time_ns();
    auto start = now - 30'000'000'000ULL;
    auto stats = aggregator_->get_window_stats(start, now);
    // connections per second en ventana de 30s, normalizado a [0,1] (saturación en 100 conn/s)
    float rate = static_cast<float>(stats.event_count) / 30.0f;
    return std::min(rate / 100.0f, 1.0f);
}

float MLDefenderExtractor::extract_traffic_tcp_udp_ratio(const FlowStatistics& /*flow*/) const {
    // TODO(Phase 2): Requires protocol field in FlowStatistics
    //
    // Current FlowStatistics doesn't store protocol type.
    // Need to add uint8_t protocol field (6=TCP, 17=UDP).
    //
    // For Phase 1: Return neutral value
    return MISSING_FEATURE_SENTINEL;  // Phase 2: implement with TimeWindowAggregator
}

float MLDefenderExtractor::extract_traffic_avg_packet_size(const FlowStatistics& flow) const {
    // Average packet size
    uint64_t total_packets = flow.spkts + flow.dpkts;
    if (total_packets == 0) return 0.0f;

    uint64_t total_bytes = flow.sbytes + flow.dbytes;
    float avg_size = safe_divide(
        static_cast<float>(total_bytes),
        static_cast<float>(total_packets)
    );

    // Normalize: 0-1500 bytes (MTU) = 0.0-1.0
    float normalized = avg_size / 1500.0f;
    return std::min(normalized, 1.0f);
}

float MLDefenderExtractor::extract_traffic_port_entropy(const FlowStatistics& /*flow*/) const {
    if (!aggregator_) return MISSING_FEATURE_SENTINEL;
    auto now = TimeWindowAggregator::get_current_time_ns();
    auto start = now - 30'000'000'000ULL;
    auto stats = aggregator_->get_window_stats(start, now);
    if (stats.event_count == 0) return 0.0f;
    return std::min(
        std::log2f(static_cast<float>(stats.unique_ports_count) + 1.0f) /
        std::log2f(static_cast<float>(stats.event_count) + 2.0f),
        1.0f);
}

float MLDefenderExtractor::extract_traffic_flow_duration_std(const FlowStatistics& /*flow*/) const {
    // TODO(Phase 2): Requires multi-flow aggregator
    //
    // Standard deviation of flow durations requires multiple flows.
    // Single flow has no std dev of duration.
    //
    // For Phase 1: Return neutral value
    return MISSING_FEATURE_SENTINEL;  // Phase 2: implement with TimeWindowAggregator
}

float MLDefenderExtractor::extract_traffic_src_ip_entropy(const FlowStatistics& /*flow*/) const {
    if (!aggregator_) return MISSING_FEATURE_SENTINEL;
    auto now = TimeWindowAggregator::get_current_time_ns();
    auto start = now - 30'000'000'000ULL;
    auto stats = aggregator_->get_window_stats(start, now);
    if (stats.event_count == 0) return 0.0f;
    // Shannon aproximado: log2(unique_ips) / log2(event_count)
    return std::min(
        std::log2f(static_cast<float>(stats.unique_ips_count) + 1.0f) /
        std::log2f(static_cast<float>(stats.event_count) + 2.0f),
        1.0f);
}

float MLDefenderExtractor::extract_traffic_dst_ip_concentration(const FlowStatistics& /*flow*/) const {
    if (!aggregator_) return MISSING_FEATURE_SENTINEL;
    auto now = TimeWindowAggregator::get_current_time_ns();
    auto start = now - 30'000'000'000ULL;
    auto stats = aggregator_->get_window_stats(start, now);
    if (stats.event_count == 0) return 0.0f;
    // Alta concentración = pocas IPs destino únicas (DDoS a un target)
    return 1.0f - std::min(
        static_cast<float>(stats.unique_ips_count) /
        static_cast<float>(stats.event_count),
        1.0f);
}

float MLDefenderExtractor::extract_traffic_protocol_variety(const FlowStatistics& /*flow*/) const {
    // TODO(Phase 2): Requires multi-flow aggregator
    //
    // Protocol variety = number of unique protocols in time window.
    // Requires multi-flow tracking.
    //
    // For Phase 1: Return neutral value
    return MISSING_FEATURE_SENTINEL;  // Phase 2: implement with TimeWindowAggregator
}

float MLDefenderExtractor::extract_traffic_temporal_consistency(const FlowStatistics& flow) const {
    // Temporal consistency: Low CoV = consistent timing
    float cv = calculate_iat_coefficient_of_variation(flow.packet_timestamps);

    // Low CV = high consistency
    float consistency = std::max(0.0f, 1.0f - cv);
    return consistency;
}

// ============================================================================
// INTERNAL FEATURES (10 features)
// ============================================================================

void MLDefenderExtractor::extract_internal_features(
    const FlowStatistics& flow,
    ::protobuf::InternalFeatures* internal) const {

    internal->set_internal_connection_rate(extract_internal_connection_rate(flow));
    internal->set_service_port_consistency(extract_internal_service_port_consistency(flow));
    internal->set_protocol_regularity(extract_internal_protocol_regularity(flow));
    internal->set_packet_size_consistency(extract_internal_packet_size_consistency(flow));
    internal->set_connection_duration_std(extract_internal_connection_duration_std(flow));
    internal->set_lateral_movement_score(extract_internal_lateral_movement_score(flow));
    internal->set_service_discovery_patterns(extract_internal_service_discovery_patterns(flow));
    internal->set_data_exfiltration_indicators(extract_internal_data_exfiltration_indicators(flow));
    internal->set_temporal_anomaly_score(extract_internal_temporal_anomaly_score(flow));
    internal->set_access_pattern_entropy(extract_internal_access_pattern_entropy(flow));
}

float MLDefenderExtractor::extract_internal_connection_rate(const FlowStatistics& /*flow*/) const {
    if (!aggregator_) return MISSING_FEATURE_SENTINEL;
    auto now = TimeWindowAggregator::get_current_time_ns();
    auto start = now - 30'000'000'000ULL;
    auto stats = aggregator_->get_window_stats(start, now);
    float rate = static_cast<float>(stats.event_count) / 30.0f;
    return std::min(rate / 100.0f, 1.0f);
}

float MLDefenderExtractor::extract_internal_service_port_consistency(const FlowStatistics& /*flow*/) const {
    if (!aggregator_) return MISSING_FEATURE_SENTINEL;
    auto now = TimeWindowAggregator::get_current_time_ns();
    auto start = now - 30'000'000'000ULL;
    auto stats = aggregator_->get_window_stats(start, now);
    if (stats.event_count == 0) return 0.0f;
    // Alta consistencia = pocas variaciones de puerto (comportamiento normal)
    return 1.0f - std::min(
        static_cast<float>(stats.unique_ports_count) /
        static_cast<float>(stats.event_count),
        1.0f);
}

float MLDefenderExtractor::extract_internal_protocol_regularity(const FlowStatistics& flow) const {
    // Protocol regularity: Consistency in packet timing
    float cv = calculate_iat_coefficient_of_variation(flow.packet_timestamps);

    // Low CV = high regularity
    float regularity = std::max(0.0f, 1.0f - cv);
    return regularity;
}

float MLDefenderExtractor::extract_internal_packet_size_consistency(const FlowStatistics& flow) const {
    // Packet size consistency: Low std dev = consistent sizes
    float std_dev = calculate_std_dev(flow.all_lengths);
    float mean = calculate_mean(flow.all_lengths);

    if (mean == 0.0f) return MISSING_FEATURE_SENTINEL;

    float cv = std_dev / mean;

    // Low CV = high consistency
    float consistency = std::max(0.0f, 1.0f - cv);
    return consistency;
}

float MLDefenderExtractor::extract_internal_connection_duration_std(const FlowStatistics& /*flow*/) const {
    // TODO(Phase 2): Requires multi-flow aggregator
    //
    // Standard deviation of connection durations requires multiple flows.
    //
    // For Phase 1: Return neutral value
    return MISSING_FEATURE_SENTINEL;  // Phase 2: implement with TimeWindowAggregator
}

float MLDefenderExtractor::extract_internal_lateral_movement_score(const FlowStatistics& /*flow*/) const {
    if (!aggregator_) return MISSING_FEATURE_SENTINEL;
    auto now = TimeWindowAggregator::get_current_time_ns();
    auto start = now - 30'000'000'000ULL;
    auto stats = aggregator_->get_window_stats(start, now);
    if (stats.event_count == 0) return 0.0f;
    // Muchas IPs únicas contactadas = posible lateral movement
    return std::min(
        static_cast<float>(stats.unique_ips_count) /
        static_cast<float>(stats.event_count),
        1.0f);
}

float MLDefenderExtractor::extract_internal_service_discovery_patterns(const FlowStatistics& /*flow*/) const {
    if (!aggregator_) return MISSING_FEATURE_SENTINEL;
    auto now = TimeWindowAggregator::get_current_time_ns();
    auto start = now - 30'000'000'000ULL;
    auto stats = aggregator_->get_window_stats(start, now);
    if (stats.event_count == 0) return 0.0f;
    // Muchos puertos únicos por evento = patrón de port scanning
    return std::min(
        static_cast<float>(stats.unique_ports_count) /
        static_cast<float>(stats.event_count),
        1.0f);
}

float MLDefenderExtractor::extract_internal_data_exfiltration_indicators(const FlowStatistics& flow) const {
    // Data exfiltration: High upload ratio
    float upload_download_ratio = safe_divide(
        static_cast<float>(flow.sbytes),  // Upload (forward)
        static_cast<float>(flow.dbytes)   // Download (backward)
    );

    // High ratio (>5) = potential exfiltration
    float normalized = std::min(upload_download_ratio / 10.0f, 1.0f);
    return normalized;
}

float MLDefenderExtractor::extract_internal_temporal_anomaly_score(const FlowStatistics& flow) const {
    // Temporal anomaly: Unusual timing patterns
    float cv = calculate_iat_coefficient_of_variation(flow.packet_timestamps);

    // Very low CV (<0.2) or very high CV (>2.0) = anomalous
    if (cv < 0.2f) {
        return 0.8f;  // Too regular (bot-like)
    } else if (cv > 2.0f) {
        return 0.7f;  // Too random (scan-like)
    } else {
        return 0.3f;  // Normal range
    }
}

float MLDefenderExtractor::extract_internal_access_pattern_entropy(const FlowStatistics& flow) const {
    // Access pattern entropy: Entropy of packet sizes as proxy
    float entropy = calculate_entropy(flow.all_lengths);

    // Normalize: 0-5 → 0.0-1.0
    float normalized = entropy / 5.0f;
    return std::min(normalized, 1.0f);
}

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

float MLDefenderExtractor::calculate_entropy(const std::vector<uint32_t>& data) const {
    if (data.empty()) return 0.0f;

    // Count frequency of each value
    std::map<uint32_t, uint32_t> freq_map;
    for (uint32_t val : data) {
        freq_map[val]++;
    }

    // Calculate Shannon entropy
    float entropy = 0.0f;
    float total = static_cast<float>(data.size());

    for (const auto& [value, count] : freq_map) {
        float probability = static_cast<float>(count) / total;
        if (probability > 0.0f) {
            entropy -= probability * std::log2(probability);
        }
    }

    return entropy;
}

float MLDefenderExtractor::calculate_std_dev(const std::vector<uint32_t>& data) const {
    if (data.size() < 2) return 0.0f;

    float mean = calculate_mean(data);

    float sum_sq_diff = 0.0f;
    for (uint32_t val : data) {
        float diff = static_cast<float>(val) - mean;
        sum_sq_diff += diff * diff;
    }

    float variance = sum_sq_diff / static_cast<float>(data.size());
    return std::sqrt(variance);
}

float MLDefenderExtractor::calculate_coefficient_of_variation(const std::vector<uint32_t>& data) const {
    if (data.size() < 2) return 0.0f;

    float mean = calculate_mean(data);
    if (mean == 0.0f) return 0.0f;

    float std_dev = calculate_std_dev(data);
    return std_dev / mean;
}

float MLDefenderExtractor::calculate_iat_mean(const std::vector<uint64_t>& timestamps) const {
    if (timestamps.size() < 2) return 0.0f;

    uint64_t sum_iat = 0;
    for (size_t i = 1; i < timestamps.size(); ++i) {
        if (timestamps[i] >= timestamps[i-1]) {
            sum_iat += (timestamps[i] - timestamps[i-1]);
        }
    }

    return static_cast<float>(sum_iat) / static_cast<float>(timestamps.size() - 1);
}

float MLDefenderExtractor::calculate_iat_std_dev(const std::vector<uint64_t>& timestamps) const {
    if (timestamps.size() < 2) return 0.0f;

    // Calculate IATs
    std::vector<uint64_t> iats;
    iats.reserve(timestamps.size() - 1);

    for (size_t i = 1; i < timestamps.size(); ++i) {
        if (timestamps[i] >= timestamps[i-1]) {
            iats.push_back(timestamps[i] - timestamps[i-1]);
        }
    }

    if (iats.empty()) return 0.0f;

    // Calculate mean
    uint64_t sum = 0;
    for (uint64_t iat : iats) sum += iat;
    float mean = static_cast<float>(sum) / static_cast<float>(iats.size());

    // Calculate std dev
    float sum_sq_diff = 0.0f;
    for (uint64_t iat : iats) {
        float diff = static_cast<float>(iat) - mean;
        sum_sq_diff += diff * diff;
    }

    float variance = sum_sq_diff / static_cast<float>(iats.size());
    return std::sqrt(variance);
}

float MLDefenderExtractor::calculate_iat_coefficient_of_variation(const std::vector<uint64_t>& timestamps) const {
    float mean = calculate_iat_mean(timestamps);
    if (mean == 0.0f) return 0.0f;

    float std_dev = calculate_iat_std_dev(timestamps);
    return std_dev / mean;
}

    // ============================================================================
    // CONVENIENCE METHOD - Populate all ML Defender features at once
    // DAY 46 COMPLETION: Now extracts ALL 142 fields from FlowStatistics
    // ============================================================================

void MLDefenderExtractor::populate_ml_defender_features(
        const FlowStatistics& flow,
        ::protobuf::NetworkSecurityEvent& proto_event) const {

    // Get network_features submessage
    auto* net_features = proto_event.mutable_network_features();

    // ========================================================================
    // PART 1: ML DEFENDER EMBEDDED FEATURES (40 features)
    // ========================================================================

    // Extract DDoS features (10 features)
    auto* ddos = net_features->mutable_ddos_embedded();
    extract_ddos_features(flow, ddos);

    // Extract Ransomware features (10 features)
    auto* ransomware = net_features->mutable_ransomware_embedded();
    extract_ransomware_features(flow, ransomware);

    // Extract Traffic features (10 features)
    auto* traffic = net_features->mutable_traffic_classification();
    extract_traffic_features(flow, traffic);

    // Extract Internal features (10 features)
    auto* internal = net_features->mutable_internal_anomaly();
    extract_internal_features(flow, internal);

    // ========================================================================
    // PART 2: BASE NETWORK FEATURES (102+ fields) - DAY 46 COMPLETION
    // ========================================================================

    // 📊 ESTADÍSTICAS BÁSICAS DE PAQUETES
    net_features->set_total_forward_packets(flow.spkts);
    net_features->set_total_backward_packets(flow.dpkts);
    net_features->set_total_forward_bytes(flow.sbytes);
    net_features->set_total_backward_bytes(flow.dbytes);

    // ⏰ TIMING - Flow duration
    uint64_t duration_us = flow.get_duration_us();
    net_features->set_flow_duration_microseconds(duration_us);

    // 📏 ESTADÍSTICAS DE LONGITUD - FORWARD
    if (!flow.fwd_lengths.empty()) {
        auto fwd_minmax = std::minmax_element(flow.fwd_lengths.begin(), flow.fwd_lengths.end());
        net_features->set_forward_packet_length_min(*fwd_minmax.first);
        net_features->set_forward_packet_length_max(*fwd_minmax.second);
        net_features->set_forward_packet_length_mean(calculate_mean(flow.fwd_lengths));
        net_features->set_forward_packet_length_std(calculate_std_dev(flow.fwd_lengths));
    }

    // 📏 ESTADÍSTICAS DE LONGITUD - BACKWARD
    if (!flow.bwd_lengths.empty()) {
        auto bwd_minmax = std::minmax_element(flow.bwd_lengths.begin(), flow.bwd_lengths.end());
        net_features->set_backward_packet_length_min(*bwd_minmax.first);
        net_features->set_backward_packet_length_max(*bwd_minmax.second);
        net_features->set_backward_packet_length_mean(calculate_mean(flow.bwd_lengths));
        net_features->set_backward_packet_length_std(calculate_std_dev(flow.bwd_lengths));
    }

    // 📊 ESTADÍSTICAS GLOBALES DE LONGITUD
    if (!flow.all_lengths.empty()) {
        auto all_minmax = std::minmax_element(flow.all_lengths.begin(), flow.all_lengths.end());
        net_features->set_minimum_packet_length(*all_minmax.first);
        net_features->set_maximum_packet_length(*all_minmax.second);

        float mean = calculate_mean(flow.all_lengths);
        float std_dev = calculate_std_dev(flow.all_lengths);

        net_features->set_packet_length_mean(mean);
        net_features->set_packet_length_std(std_dev);
        net_features->set_packet_length_variance(std_dev * std_dev);
        net_features->set_average_packet_size(mean);
    }

    // 🚀 VELOCIDADES Y RATIOS
    float duration_sec = duration_us / 1000000.0f;
    if (duration_sec > 0.0f) {
        uint64_t total_packets = flow.spkts + flow.dpkts;
        uint64_t total_bytes = flow.sbytes + flow.dbytes;

        net_features->set_flow_packets_per_second(total_packets / duration_sec);
        net_features->set_flow_bytes_per_second(total_bytes / duration_sec);
        net_features->set_forward_packets_per_second(flow.spkts / duration_sec);
        net_features->set_backward_packets_per_second(flow.dpkts / duration_sec);
    }

    // Download/Upload ratio
    float download_upload = safe_divide(
        static_cast<float>(flow.dbytes),
        static_cast<float>(flow.sbytes)
    );
    net_features->set_download_upload_ratio(download_upload);

    // Average segment sizes
    if (flow.spkts > 0) {
        net_features->set_average_forward_segment_size(
            static_cast<double>(flow.sbytes) / flow.spkts
        );
    }
    if (flow.dpkts > 0) {
        net_features->set_average_backward_segment_size(
            static_cast<double>(flow.dbytes) / flow.dpkts
        );
    }

    // ⏱️ INTER-ARRIVAL TIMES - FLOW (all packets)
    if (flow.packet_timestamps.size() >= 2) {
        std::vector<uint64_t> iats;
        iats.reserve(flow.packet_timestamps.size() - 1);

        for (size_t i = 1; i < flow.packet_timestamps.size(); ++i) {
            if (flow.packet_timestamps[i] >= flow.packet_timestamps[i-1]) {
                iats.push_back(flow.packet_timestamps[i] - flow.packet_timestamps[i-1]);
            }
        }

        if (!iats.empty()) {
            auto iat_minmax = std::minmax_element(iats.begin(), iats.end());

            uint64_t sum = std::accumulate(iats.begin(), iats.end(), 0ULL);
            float mean_ns = static_cast<float>(sum) / iats.size();

            // Calculate std dev
            float sum_sq_diff = 0.0f;
            for (uint64_t iat : iats) {
                float diff = static_cast<float>(iat) - mean_ns;
                sum_sq_diff += diff * diff;
            }
            float std_ns = std::sqrt(sum_sq_diff / iats.size());

            net_features->set_flow_inter_arrival_time_min(*iat_minmax.first);
            net_features->set_flow_inter_arrival_time_max(*iat_minmax.second);
            net_features->set_flow_inter_arrival_time_mean(mean_ns / 1000.0);  // Convert to microseconds
            net_features->set_flow_inter_arrival_time_std(std_ns / 1000.0);
        }
    }

    // ⏱️ INTER-ARRIVAL TIMES - FORWARD
    if (flow.fwd_timestamps.size() >= 2) {
        std::vector<uint64_t> fwd_iats;
        fwd_iats.reserve(flow.fwd_timestamps.size() - 1);

        for (size_t i = 1; i < flow.fwd_timestamps.size(); ++i) {
            if (flow.fwd_timestamps[i] >= flow.fwd_timestamps[i-1]) {
                fwd_iats.push_back(flow.fwd_timestamps[i] - flow.fwd_timestamps[i-1]);
            }
        }

        if (!fwd_iats.empty()) {
            auto fwd_minmax = std::minmax_element(fwd_iats.begin(), fwd_iats.end());
            uint64_t sum = std::accumulate(fwd_iats.begin(), fwd_iats.end(), 0ULL);
            float mean_ns = static_cast<float>(sum) / fwd_iats.size();

            float sum_sq_diff = 0.0f;
            for (uint64_t iat : fwd_iats) {
                float diff = static_cast<float>(iat) - mean_ns;
                sum_sq_diff += diff * diff;
            }
            float std_ns = std::sqrt(sum_sq_diff / fwd_iats.size());

            net_features->set_forward_inter_arrival_time_min(*fwd_minmax.first);
            net_features->set_forward_inter_arrival_time_max(*fwd_minmax.second);
            net_features->set_forward_inter_arrival_time_mean(mean_ns / 1000.0);
            net_features->set_forward_inter_arrival_time_std(std_ns / 1000.0);
            net_features->set_forward_inter_arrival_time_total(sum / 1000.0);
        }
    }

    // ⏱️ INTER-ARRIVAL TIMES - BACKWARD
    if (flow.bwd_timestamps.size() >= 2) {
        std::vector<uint64_t> bwd_iats;
        bwd_iats.reserve(flow.bwd_timestamps.size() - 1);

        for (size_t i = 1; i < flow.bwd_timestamps.size(); ++i) {
            if (flow.bwd_timestamps[i] >= flow.bwd_timestamps[i-1]) {
                bwd_iats.push_back(flow.bwd_timestamps[i] - flow.bwd_timestamps[i-1]);
            }
        }

        if (!bwd_iats.empty()) {
            auto bwd_minmax = std::minmax_element(bwd_iats.begin(), bwd_iats.end());
            uint64_t sum = std::accumulate(bwd_iats.begin(), bwd_iats.end(), 0ULL);
            float mean_ns = static_cast<float>(sum) / bwd_iats.size();

            float sum_sq_diff = 0.0f;
            for (uint64_t iat : bwd_iats) {
                float diff = static_cast<float>(iat) - mean_ns;
                sum_sq_diff += diff * diff;
            }
            float std_ns = std::sqrt(sum_sq_diff / bwd_iats.size());

            net_features->set_backward_inter_arrival_time_min(*bwd_minmax.first);
            net_features->set_backward_inter_arrival_time_max(*bwd_minmax.second);
            net_features->set_backward_inter_arrival_time_mean(mean_ns / 1000.0);
            net_features->set_backward_inter_arrival_time_std(std_ns / 1000.0);
            net_features->set_backward_inter_arrival_time_total(sum / 1000.0);
        }
    }

    // 🏳️ TCP FLAGS COUNTS
    net_features->set_fin_flag_count(flow.fin_count);
    net_features->set_syn_flag_count(flow.syn_count);
    net_features->set_rst_flag_count(flow.rst_count);
    net_features->set_psh_flag_count(flow.psh_count);
    net_features->set_ack_flag_count(flow.ack_count);
    net_features->set_urg_flag_count(flow.urg_count);
    net_features->set_ece_flag_count(flow.ece_count);
    net_features->set_cwe_flag_count(flow.cwr_count);

    // 🏳️ TCP FLAGS DIRECTIONAL
    net_features->set_forward_psh_flags(flow.fwd_psh_flags);
    net_features->set_backward_psh_flags(flow.bwd_psh_flags);
    net_features->set_forward_urg_flags(flow.fwd_urg_flags);
    net_features->set_backward_urg_flags(flow.bwd_urg_flags);

    // 🔍 SMB SCAN FEATURES (SYN-1, SYN-2 — DAY 92)
    // rst_ratio = RST/SYN — WannaCry > 0.70 (escaneo masivo con RST inmediato)
    // syn_ack_ratio = ACK/SYN — WannaCry < 0.10 (sin handshake completo)
    // Sentinel: MISSING_FEATURE_SENTINEL = -9999.0f cuando syn_flag_count == 0
    {
        constexpr float MISSING_FEATURE_SENTINEL = -9999.0f;
        auto* smb = net_features->mutable_smb_scan();

        const float syn_count = static_cast<float>(flow.syn_count);
        const float rst_count = static_cast<float>(flow.rst_count);
        const float ack_count = static_cast<float>(flow.ack_count);

        if (syn_count > 0.0f) {
            smb->set_rst_ratio(rst_count / syn_count);
            smb->set_syn_ack_ratio(ack_count / syn_count);
        } else {
            smb->set_rst_ratio(MISSING_FEATURE_SENTINEL);
            smb->set_syn_ack_ratio(MISSING_FEATURE_SENTINEL);
        }
        // flow_duration_min_ms — SYN-8b, P2 (DAY 97+)
    }

    // 📋 HEADERS
    if (!flow.fwd_header_lengths.empty()) {
        uint64_t sum = std::accumulate(flow.fwd_header_lengths.begin(),
                                       flow.fwd_header_lengths.end(), 0ULL);
        net_features->set_forward_header_length(
            static_cast<double>(sum) / flow.fwd_header_lengths.size()
        );
    }

    if (!flow.bwd_header_lengths.empty()) {
        uint64_t sum = std::accumulate(flow.bwd_header_lengths.begin(),
                                       flow.bwd_header_lengths.end(), 0ULL);
        net_features->set_backward_header_length(
            static_cast<double>(sum) / flow.bwd_header_lengths.size()
        );
    }

    // 📋 BULK TRANSFER (placeholders - require deeper analysis)
    // These would need analysis of packet sequences to detect bulk transfers
    // For now, set to 0 (no bulk detected)
    net_features->set_forward_average_bytes_bulk(0.0);
    net_features->set_forward_average_packets_bulk(0.0);
    net_features->set_forward_average_bulk_rate(0.0);
    net_features->set_backward_average_bytes_bulk(0.0);
    net_features->set_backward_average_packets_bulk(0.0);
    net_features->set_backward_average_bulk_rate(0.0);

    // 🎯 ACTIVE/IDLE TIMES (placeholders - require time window analysis)
    // These would need TimeWindowManager data
    // For now, use flow duration as approximation
    net_features->set_active_mean(duration_us);
    net_features->set_idle_mean(0.0);
}

} // namespace sniffer
