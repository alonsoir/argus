// sniffer/include/ml_defender_features.hpp
// ML Defender - Phase 1, Day 2
// 40 Features for 4 Embedded C++20 RandomForest Detectors
//
// ARCHITECTURAL DECISION:
// All features calculated in USERSPACE (not kernel)
// Reason: Statistical nature of synthetic datasets requires temporal windows
// Future work: Explore kernel pre-computation (Option B) after performance baseline

#pragma once

#include "flow_manager.hpp"  // For FlowStatistics definition
// Tras #include "flow_manager.hpp"
#include "time_window_aggregator.hpp"
#include <cstdint>
#include <vector>
#include <cmath>
#include <algorithm>

/// Sentinel para features no computadas (ventana temporal insuficiente).
/// Rango real de splits embedded: [0.0, 5.1] → -9999.0f inalcanzable.
/// Routing determinista: siempre left_child en todos los árboles.
constexpr float MISSING_FEATURE_SENTINEL = -9999.0f;

// Forward declarations for protobuf types (in global protobuf namespace)
namespace protobuf {
    class DDoSFeatures;
    class RansomwareEmbeddedFeatures;
    class TrafficFeatures;
    class InternalFeatures;
    class NetworkSecurityEvent;
}

namespace sniffer {

/**
 * ML Defender Feature Extractor
 * Extracts 40 features (10 per detector) from flow statistics
 * for embedded C++20 RandomForest models
 */
class MLDefenderExtractor {
public:
    MLDefenderExtractor() = default;
    ~MLDefenderExtractor() = default;

    // DAY 78: inyección lazy de TimeWindowAggregator para features multi-flow
    void set_aggregator(TimeWindowAggregator* agg) {
        if (!aggregator_) aggregator_ = agg;
    }
    bool has_aggregator() const { return aggregator_ != nullptr; }

    // ========================================================================
    // MAIN EXTRACTION METHODS
    // ========================================================================

    /**
     * Extract Level 2 - DDoS Features (10 features)
     * Detects volumetric attacks, SYN floods, amplification attacks
     */
    void extract_ddos_features(
        const FlowStatistics& flow,
        ::protobuf::DDoSFeatures* ddos) const;

    /**
     * Extract Level 2 - Ransomware Features (10 features)
     * Detects file encryption patterns, lateral movement, C2 communication
     */
    void extract_ransomware_features(
        const FlowStatistics& flow,
        ::protobuf::RansomwareEmbeddedFeatures* ransomware) const;

    /**
     * Extract Level 3 - Traffic Features (10 features)
     * General traffic classification: benign, scanning, data exfiltration
     */
    void extract_traffic_features(
        const FlowStatistics& flow,
        ::protobuf::TrafficFeatures* traffic) const;

    /**
     * Extract Level 3 - Internal Features (10 features)
     * Internal network behavior, lateral movement, privilege escalation
     */
    void extract_internal_features(
        const FlowStatistics& flow,
        ::protobuf::InternalFeatures* internal) const;

    // ========================================================================
    // CONVENIENCE METHOD - Populate all ML Defender features at once
    // ========================================================================

    /**
     * Populate ALL ML Defender features (40 features across 4 detectors)
     * This is a convenience wrapper that calls all 4 extraction methods
     *
     * @param flow Flow statistics from FlowManager
     * @param proto_event NetworkSecurityEvent to populate
     */
    void populate_ml_defender_features(
        const FlowStatistics& flow,
        ::protobuf::NetworkSecurityEvent& proto_event) const;

private:
    // ========================================================================
    // DDOS FEATURE EXTRACTORS (10 features)
    // ========================================================================

    float extract_ddos_syn_ack_ratio(const FlowStatistics& flow) const;
    float extract_ddos_packet_symmetry(const FlowStatistics& flow) const;
    float extract_ddos_source_ip_dispersion(const FlowStatistics& flow) const;
    float extract_ddos_protocol_anomaly_score(const FlowStatistics& flow) const;
    float extract_ddos_packet_size_entropy(const FlowStatistics& flow) const;
    float extract_ddos_traffic_amplification_factor(const FlowStatistics& flow) const;
    float extract_ddos_flow_completion_rate(const FlowStatistics& flow) const;
    float extract_ddos_geographical_concentration(const FlowStatistics& flow) const;
    float extract_ddos_traffic_escalation_rate(const FlowStatistics& flow) const;
    float extract_ddos_resource_saturation_score(const FlowStatistics& flow) const;

    // ========================================================================
    // RANSOMWARE FEATURE EXTRACTORS (10 features)
    // ========================================================================

    float extract_ransomware_io_intensity(const FlowStatistics& flow) const;
    float extract_ransomware_entropy(const FlowStatistics& flow) const;
    float extract_ransomware_resource_usage(const FlowStatistics& flow) const;
    float extract_ransomware_network_activity(const FlowStatistics& flow) const;
    float extract_ransomware_file_operations(const FlowStatistics& flow) const;
    float extract_ransomware_process_anomaly(const FlowStatistics& flow) const;
    float extract_ransomware_temporal_pattern(const FlowStatistics& flow) const;
    float extract_ransomware_access_frequency(const FlowStatistics& flow) const;
    float extract_ransomware_data_volume(const FlowStatistics& flow) const;
    float extract_ransomware_behavior_consistency(const FlowStatistics& flow) const;

    // ========================================================================
    // TRAFFIC FEATURE EXTRACTORS (10 features)
    // ========================================================================

    float extract_traffic_packet_rate(const FlowStatistics& flow) const;
    float extract_traffic_connection_rate(const FlowStatistics& flow) const;
    float extract_traffic_tcp_udp_ratio(const FlowStatistics& flow) const;
    float extract_traffic_avg_packet_size(const FlowStatistics& flow) const;
    float extract_traffic_port_entropy(const FlowStatistics& flow) const;
    float extract_traffic_flow_duration_std(const FlowStatistics& flow) const;
    float extract_traffic_src_ip_entropy(const FlowStatistics& flow) const;
    float extract_traffic_dst_ip_concentration(const FlowStatistics& flow) const;
    float extract_traffic_protocol_variety(const FlowStatistics& flow) const;
    float extract_traffic_temporal_consistency(const FlowStatistics& flow) const;

    // ========================================================================
    // INTERNAL FEATURE EXTRACTORS (10 features)
    // ========================================================================

    float extract_internal_connection_rate(const FlowStatistics& flow) const;
    float extract_internal_service_port_consistency(const FlowStatistics& flow) const;
    float extract_internal_protocol_regularity(const FlowStatistics& flow) const;
    float extract_internal_packet_size_consistency(const FlowStatistics& flow) const;
    float extract_internal_connection_duration_std(const FlowStatistics& flow) const;
    float extract_internal_lateral_movement_score(const FlowStatistics& flow) const;
    float extract_internal_service_discovery_patterns(const FlowStatistics& flow) const;
    float extract_internal_data_exfiltration_indicators(const FlowStatistics& flow) const;
    float extract_internal_temporal_anomaly_score(const FlowStatistics& flow) const;
    float extract_internal_access_pattern_entropy(const FlowStatistics& flow) const;

    // ========================================================================
    // HELPER FUNCTIONS - Statistical calculations
    // ========================================================================

    /**
     * Safe division - returns 0.0 if denominator is zero
     */
    float safe_divide(float numerator, float denominator) const {
        return (denominator != 0.0f) ? (numerator / denominator) : 0.0f;
    }

    /**
     * Calculate Shannon entropy of a dataset
     * Returns value between 0.0 (no entropy) and log2(unique_values)
     */
    float calculate_entropy(const std::vector<uint32_t>& data) const;

    /**
     * Calculate standard deviation
     */
    float calculate_std_dev(const std::vector<uint32_t>& data) const;

    /**
     * Calculate coefficient of variation (std_dev / mean)
     * Useful for detecting regularity vs randomness
     */
    float calculate_coefficient_of_variation(const std::vector<uint32_t>& data) const;

    /**
     * Calculate flow duration in seconds (from nanoseconds)
     */
    double get_flow_duration_seconds(const FlowStatistics& flow) const {
        if (flow.flow_last_seen_ns <= flow.flow_start_ns) return 0.0;
        uint64_t duration_ns = flow.flow_last_seen_ns - flow.flow_start_ns;
        return static_cast<double>(duration_ns) / 1e9;
    }

    /**
     * Calculate packet rate (packets per second)
     */
    float calculate_packet_rate(const FlowStatistics& flow) const {
        double duration_sec = get_flow_duration_seconds(flow);
        if (duration_sec <= 0.0) return 0.0f;
        uint64_t total_packets = flow.spkts + flow.dpkts;
        return static_cast<float>(total_packets) / static_cast<float>(duration_sec);
    }

    /**
     * Calculate byte rate (bytes per second)
     */
    float calculate_byte_rate(const FlowStatistics& flow) const {
        double duration_sec = get_flow_duration_seconds(flow);
        if (duration_sec <= 0.0) return 0.0f;
        uint64_t total_bytes = flow.sbytes + flow.dbytes;
        return static_cast<float>(total_bytes) / static_cast<float>(duration_sec);
    }

    /**
     * Calculate mean of uint32_t vector
     */
    float calculate_mean(const std::vector<uint32_t>& data) const {
        if (data.empty()) return 0.0f;
        uint64_t sum = 0;
        for (uint32_t val : data) sum += val;
        return static_cast<float>(sum) / static_cast<float>(data.size());
    }

    /**
     * Calculate inter-arrival time statistics
     */
    float calculate_iat_mean(const std::vector<uint64_t>& timestamps) const;
    float calculate_iat_std_dev(const std::vector<uint64_t>& timestamps) const;
    float calculate_iat_coefficient_of_variation(const std::vector<uint64_t>& timestamps) const;

    // DAY 78: aggregator para features que requieren ventana temporal
    TimeWindowAggregator* aggregator_ = nullptr;
};

} // namespace sniffer