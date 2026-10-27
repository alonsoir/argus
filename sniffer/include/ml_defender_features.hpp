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
#include "ddos_flow_snap.hpp"  // [DDOS-SNAP-D290]
#include <map>
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
     * Extract Level 2 - Ransomware Features (10 features)
     * Detects file encryption patterns, lateral movement, C2 communication
     */
    void extract_ransomware_features(
        const FlowStatsCore& flow,
        float len_entropy,  // [D308-PASO1] entropia de longitudes de la foto DDoS v2
        ::protobuf::RansomwareEmbeddedFeatures* ransomware) const;

    /**
     * Extract Level 3 - Traffic Features (10 features)
     * General traffic classification: benign, scanning, data exfiltration
     */
    void extract_traffic_features(
        const FlowStatsCore& flow,
        ::protobuf::TrafficFeatures* traffic) const;

    /**
     * Extract Level 3 - Internal Features (10 features)
     * Internal network behavior, lateral movement, privilege escalation
     */
    void extract_internal_features(
        const FlowStatsCore& flow,
        float len_entropy,  // [D308-PASO1] entropia de longitudes de la foto DDoS v2
        ::protobuf::InternalFeatures* internal) const;

    // ========================================================================
    // CONVENIENCE METHOD - Populate all ML Defender features at once
    // ========================================================================

    /**
     * Populate ALL ML Defender features (40 features across 4 detectors)
     * This is a convenience wrapper that calls all 4 extraction methods
     *
     * @param flow Flow statistics from FlowManager (copia del nucleo de tamano fijo) [D308-PASO1]
     * @param len_entropy Entropia de longitudes del flujo: la packet_size_entropy de la foto DDoS v2
     *        (ddos_v2_flow_snapshot, en el lock); MISSING_FEATURE_SENTINEL si no hay foto [D308-PASO1, D1]
     * @param proto_event NetworkSecurityEvent to populate
     */
    void populate_ml_defender_features(
        const FlowStatsCore& flow,
        float len_entropy,
        ::protobuf::NetworkSecurityEvent& proto_event) const;

    // [DDOS-SNAP-D290] Foto O(k) de los 5 rasgos DDoS v2 de flujo (syn_ack_ratio,
    // flow_completion_rate, flow_packet_count, mean_packet_size, packet_size_entropy), sobre los
    // estadisticos incrementales del flujo. Unica fuente de esos 5 rasgos [D307-PASO2].
    DdosFlowSnap ddos_v2_flow_snapshot(const FlowStatistics& flow) const;

private:
    // [WINSTATS-CACHE-D289] Una sola pasada por la ventana de 30 s por evento: los 9 extractores
    // de ventana comparten el WindowStats calculado al entrar en populate_ml_defender_features.
    // Fuera de populate (llamadas sueltas a los extract_* públicos) no hay caché: se calcula como antes.
    WindowStats window_stats_30s() const;
    mutable WindowStats window_cache_{};
    mutable bool window_cache_active_ = false;
    mutable bool window_cache_valid_ = false;

    // ========================================================================
    // DDOS FEATURE EXTRACTORS — contrato v2 [DDOS-V1-RETIRE-D306]
    // ========================================================================

    float extract_ddos_syn_ack_ratio(const FlowStatsCore& flow) const;
    float extract_ddos_flow_completion_rate(const FlowStatsCore& flow) const;

    // ========================================================================
    // RANSOMWARE FEATURE EXTRACTORS (10 features)
    // ========================================================================

    float extract_ransomware_io_intensity(const FlowStatsCore& flow) const;
    float extract_ransomware_entropy(float len_entropy) const;
    float extract_ransomware_resource_usage(const FlowStatsCore& flow) const;
    float extract_ransomware_network_activity(const FlowStatsCore& flow) const;
    float extract_ransomware_file_operations(const FlowStatsCore& flow) const;
    float extract_ransomware_process_anomaly(const FlowStatsCore& flow) const;
    float extract_ransomware_temporal_pattern(const FlowStatsCore& flow) const;
    float extract_ransomware_access_frequency(const FlowStatsCore& flow) const;
    float extract_ransomware_data_volume(const FlowStatsCore& flow) const;
    float extract_ransomware_behavior_consistency(const FlowStatsCore& flow) const;

    // ========================================================================
    // TRAFFIC FEATURE EXTRACTORS (10 features)
    // ========================================================================

    float extract_traffic_packet_rate(const FlowStatsCore& flow) const;
    float extract_traffic_connection_rate(const FlowStatsCore& flow) const;
    float extract_traffic_tcp_udp_ratio(const FlowStatsCore& flow) const;
    float extract_traffic_avg_packet_size(const FlowStatsCore& flow) const;
    float extract_traffic_port_entropy(const FlowStatsCore& flow) const;
    float extract_traffic_flow_duration_std(const FlowStatsCore& flow) const;
    float extract_traffic_src_ip_entropy(const FlowStatsCore& flow) const;
    float extract_traffic_dst_ip_concentration(const FlowStatsCore& flow) const;
    float extract_traffic_protocol_variety(const FlowStatsCore& flow) const;
    float extract_traffic_temporal_consistency(const FlowStatsCore& flow) const;

    // ========================================================================
    // INTERNAL FEATURE EXTRACTORS (10 features)
    // ========================================================================

    float extract_internal_connection_rate(const FlowStatsCore& flow) const;
    float extract_internal_service_port_consistency(const FlowStatsCore& flow) const;
    float extract_internal_protocol_regularity(const FlowStatsCore& flow) const;
    float extract_internal_packet_size_consistency(const FlowStatsCore& flow) const;
    float extract_internal_connection_duration_std(const FlowStatsCore& flow) const;
    float extract_internal_lateral_movement_score(const FlowStatsCore& flow) const;
    float extract_internal_service_discovery_patterns(const FlowStatsCore& flow) const;
    float extract_internal_data_exfiltration_indicators(const FlowStatsCore& flow) const;
    float extract_internal_temporal_anomaly_score(const FlowStatsCore& flow) const;
    float extract_internal_access_pattern_entropy(float len_entropy) const;

    // ========================================================================
    // HELPER FUNCTIONS - Statistical calculations
    // ========================================================================

    /**
     * Safe division - returns 0.0 if denominator is zero
     */
    float safe_divide(float numerator, float denominator) const {
        return (denominator != 0.0f) ? (numerator / denominator) : 0.0f;
    }

    float calculate_entropy_from_hist(const std::map<uint32_t, uint32_t>& hist,
                                      uint64_t total_count) const;  // [DDOS-SNAP-D290]

    /**
     * Calculate flow duration in seconds (from nanoseconds)
     */
    double get_flow_duration_seconds(const FlowStatsCore& flow) const {
        if (flow.flow_last_seen_ns <= flow.flow_start_ns) return 0.0;
        uint64_t duration_ns = flow.flow_last_seen_ns - flow.flow_start_ns;
        return static_cast<double>(duration_ns) / 1e9;
    }

    /**
     * Calculate packet rate (packets per second)
     */
    float calculate_packet_rate(const FlowStatsCore& flow) const {
        double duration_sec = get_flow_duration_seconds(flow);
        if (duration_sec <= 0.0) return 0.0f;
        uint64_t total_packets = flow.spkts + flow.dpkts;
        return static_cast<float>(total_packets) / static_cast<float>(duration_sec);
    }

    /**
     * Calculate byte rate (bytes per second)
     */
    float calculate_byte_rate(const FlowStatsCore& flow) const {
        double duration_sec = get_flow_duration_seconds(flow);
        if (duration_sec <= 0.0) return 0.0f;
        uint64_t total_bytes = flow.sbytes + flow.dbytes;
        return static_cast<float>(total_bytes) / static_cast<float>(duration_sec);
    }

    // [D308-PASO1] Estadisticos sobre los acumuladores del flujo (O(1)); sustituyen a los calculos sobre un
    // vector por paquete (calculate_mean/std_dev/entropy/iat_*), retirados.

    // Media Σ/n en float, como la anterior calculate_mean (0 si no hay valores)
    float mean_of(uint64_t sum, uint64_t n) const {
        if (n == 0) return 0.0f;
        return static_cast<float>(sum) / static_cast<float>(n);
    }
    float len_std_dev(const LenAcc& acc, uint64_t n, uint64_t sum) const;
    float iat_std_dev(const IatAcc& acc) const;
    float iat_mean_quirk(const IatAcc& acc, uint64_t marcas) const;
    float iat_coefficient_of_variation(const FlowStatsCore& flow) const;

    // DAY 78: aggregator para features que requieren ventana temporal
    TimeWindowAggregator* aggregator_ = nullptr;
};

} // namespace sniffer