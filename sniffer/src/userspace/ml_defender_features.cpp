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

// Protobuf header - path configured in CMakeLists.txt via ${CMAKE_BINARY_DIR}/proto
#include "proto/network_security.pb.h"

namespace sniffer {

// ============================================================================
// DDOS FEATURES — contrato v2 (cabeza ddos_v2) [DDOS-V1-RETIRE-D306]
// ============================================================================

// [D307-PASO2] Los 5 rasgos DDoS v2 de flujo solo los calcula ddos_v2_flow_snapshot (foto en el lock del shard,
// O(k)); ring_consumer los escribe en el protobuf. El antiguo extract_ddos_features los recalculaba sobre la copia
// recorriendo all_lengths en cada evento, y ring_consumer los sobrescribia siempre con la foto.

float MLDefenderExtractor::extract_ddos_syn_ack_ratio(const FlowStatsCore& flow) const {
    // SYN/ACK ratio: High ratio indicates potential SYN flood
    // Normal TCP: ratio ≈ 1.0, SYN flood: ratio > 5.0
    float syn_count = static_cast<float>(flow.syn_count);
    float ack_count = static_cast<float>(flow.ack_count);

    // Add 1.0 to denominator to avoid extreme values for low counts
    float ratio = safe_divide(syn_count, ack_count + 1.0f);

    // Cap at 10.0 to avoid extreme outliers
    return std::min(ratio, 10.0f);
}

float MLDefenderExtractor::extract_ddos_flow_completion_rate(const FlowStatsCore& flow) const {
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

// ============================================================================
// RANSOMWARE FEATURES (10 features)
// ============================================================================

void MLDefenderExtractor::extract_ransomware_features(
    const FlowStatsCore& flow,
    float len_entropy,
    ::protobuf::RansomwareEmbeddedFeatures* ransomware) const {

    ransomware->set_io_intensity(extract_ransomware_io_intensity(flow));
    ransomware->set_entropy(extract_ransomware_entropy(len_entropy));
    ransomware->set_resource_usage(extract_ransomware_resource_usage(flow));
    ransomware->set_network_activity(extract_ransomware_network_activity(flow));
    ransomware->set_file_operations(extract_ransomware_file_operations(flow));
    ransomware->set_process_anomaly(extract_ransomware_process_anomaly(flow));
    ransomware->set_temporal_pattern(extract_ransomware_temporal_pattern(flow));
    ransomware->set_access_frequency(extract_ransomware_access_frequency(flow));
    ransomware->set_data_volume(extract_ransomware_data_volume(flow));
    ransomware->set_behavior_consistency(extract_ransomware_behavior_consistency(flow));
}

float MLDefenderExtractor::extract_ransomware_io_intensity(const FlowStatsCore& /*flow*/) const {
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

float MLDefenderExtractor::extract_ransomware_entropy(float len_entropy) const {
    // Entropy: High entropy in packet sizes suggests encryption
    // Ransomware encrypts files before exfiltration
    // [D308-PASO1] len_entropy es la entropia de longitudes de la foto DDoS v2 (mismo calculo, en el lock)
    if (len_entropy == MISSING_FEATURE_SENTINEL) return MISSING_FEATURE_SENTINEL;
    float entropy = len_entropy;

    // Normalize: entropy typically 0-5 for packet sizes
    float normalized = entropy / 5.0f;
    return std::min(normalized, 1.0f);
}

float MLDefenderExtractor::extract_ransomware_resource_usage(const FlowStatsCore& /*flow*/) const {
    // TODO(Phase 2): Requires CPU/memory metrics from system
    //
    // Ransomware typically shows high CPU usage during encryption phase.
    // This requires system-level resource monitoring, not network flow data.
    //
    // For Phase 1: Return neutral value
    return MISSING_FEATURE_SENTINEL;
}

float MLDefenderExtractor::extract_ransomware_network_activity(const FlowStatsCore& flow) const {
    // Network activity: Packet rate + byte rate combined
    float pps = calculate_packet_rate(flow);
    float bps = calculate_byte_rate(flow);

    // Normalize both and average
    float pps_normalized = std::min(pps / 1000.0f, 1.0f);
    float bps_normalized = std::min(bps / 1000000.0f, 1.0f);  // 1 Mbps

    return (pps_normalized + bps_normalized) / 2.0f;
}

float MLDefenderExtractor::extract_ransomware_file_operations(const FlowStatsCore& /*flow*/) const {
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

float MLDefenderExtractor::extract_ransomware_process_anomaly(const FlowStatsCore& /*flow*/) const {
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

float MLDefenderExtractor::extract_ransomware_temporal_pattern(const FlowStatsCore& flow) const {
    // Temporal pattern: Regularity vs randomness in packet timing
    // Ransomware often shows regular patterns during C2 communication
    float cv = iat_coefficient_of_variation(flow);

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

float MLDefenderExtractor::extract_ransomware_access_frequency(const FlowStatsCore& flow) const {
    // Access frequency: Packet rate as proxy
    float pps = calculate_packet_rate(flow);

    // Normalize: 0-100 pps = 0.0-1.0
    float normalized = pps / 100.0f;
    return std::min(normalized, 1.0f);
}

float MLDefenderExtractor::extract_ransomware_data_volume(const FlowStatsCore& flow) const {
    // Data volume: Total bytes transferred
    uint64_t total_bytes = flow.sbytes + flow.dbytes;

    // Log scale normalization: 0-10MB range
    float log_bytes = std::log10(static_cast<float>(total_bytes + 1));
    float normalized = log_bytes / 7.0f;  // log10(10MB) ≈ 7

    return std::min(normalized, 1.0f);
}

float MLDefenderExtractor::extract_ransomware_behavior_consistency(const FlowStatsCore& flow) const {
    // Behavior consistency: Low std dev in IAT = consistent behavior
    float iat_std = iat_std_dev(flow.iat_all);
    float iat_mean = iat_mean_quirk(flow.iat_all, flow.get_total_packets());

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
    const FlowStatsCore& flow,
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

float MLDefenderExtractor::extract_traffic_packet_rate(const FlowStatsCore& flow) const {
    // Packets per second
    float pps = calculate_packet_rate(flow);

    // Normalize: 0-1000 pps = 0.0-1.0
    float normalized = pps / 1000.0f;
    return std::min(normalized, 1.0f);
}

float MLDefenderExtractor::extract_traffic_connection_rate(const FlowStatsCore& /*flow*/) const {
    if (!aggregator_) return MISSING_FEATURE_SENTINEL;
    auto stats = window_stats_30s();  // [WINSTATS-CACHE-D289]
    // connections per second en ventana de 30s, normalizado a [0,1] (saturación en 100 conn/s)
    float rate = static_cast<float>(stats.event_count) / 30.0f;
    return std::min(rate / 100.0f, 1.0f);
}

float MLDefenderExtractor::extract_traffic_tcp_udp_ratio(const FlowStatsCore& /*flow*/) const {
    // TODO(Phase 2): Requires protocol field in FlowStatistics
    //
    // Current FlowStatistics doesn't store protocol type.
    // Need to add uint8_t protocol field (6=TCP, 17=UDP).
    //
    // For Phase 1: Return neutral value
    return MISSING_FEATURE_SENTINEL;  // Phase 2: implement with TimeWindowAggregator
}

float MLDefenderExtractor::extract_traffic_avg_packet_size(const FlowStatsCore& flow) const {
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

float MLDefenderExtractor::extract_traffic_port_entropy(const FlowStatsCore& /*flow*/) const {
    if (!aggregator_) return MISSING_FEATURE_SENTINEL;
    auto stats = window_stats_30s();  // [WINSTATS-CACHE-D289]
    if (stats.event_count == 0) return 0.0f;
    return std::min(
        std::log2f(static_cast<float>(stats.unique_ports_count) + 1.0f) /
        std::log2f(static_cast<float>(stats.event_count) + 2.0f),
        1.0f);
}

float MLDefenderExtractor::extract_traffic_flow_duration_std(const FlowStatsCore& /*flow*/) const {
    // TODO(Phase 2): Requires multi-flow aggregator
    //
    // Standard deviation of flow durations requires multiple flows.
    // Single flow has no std dev of duration.
    //
    // For Phase 1: Return neutral value
    return MISSING_FEATURE_SENTINEL;  // Phase 2: implement with TimeWindowAggregator
}

float MLDefenderExtractor::extract_traffic_src_ip_entropy(const FlowStatsCore& /*flow*/) const {
    if (!aggregator_) return MISSING_FEATURE_SENTINEL;
    auto stats = window_stats_30s();  // [WINSTATS-CACHE-D289]
    if (stats.event_count == 0) return 0.0f;
    // Shannon aproximado: log2(unique_ips) / log2(event_count)
    return std::min(
        std::log2f(static_cast<float>(stats.unique_ips_count) + 1.0f) /
        std::log2f(static_cast<float>(stats.event_count) + 2.0f),
        1.0f);
}

float MLDefenderExtractor::extract_traffic_dst_ip_concentration(const FlowStatsCore& /*flow*/) const {
    if (!aggregator_) return MISSING_FEATURE_SENTINEL;
    auto stats = window_stats_30s();  // [WINSTATS-CACHE-D289]
    if (stats.event_count == 0) return 0.0f;
    // Alta concentración = pocas IPs destino únicas (DDoS a un target)
    return 1.0f - std::min(
        static_cast<float>(stats.unique_ips_count) /
        static_cast<float>(stats.event_count),
        1.0f);
}

float MLDefenderExtractor::extract_traffic_protocol_variety(const FlowStatsCore& /*flow*/) const {
    // TODO(Phase 2): Requires multi-flow aggregator
    //
    // Protocol variety = number of unique protocols in time window.
    // Requires multi-flow tracking.
    //
    // For Phase 1: Return neutral value
    return MISSING_FEATURE_SENTINEL;  // Phase 2: implement with TimeWindowAggregator
}

float MLDefenderExtractor::extract_traffic_temporal_consistency(const FlowStatsCore& flow) const {
    // Temporal consistency: Low CoV = consistent timing
    float cv = iat_coefficient_of_variation(flow);

    // Low CV = high consistency
    float consistency = std::max(0.0f, 1.0f - cv);
    return consistency;
}

// ============================================================================
// INTERNAL FEATURES (10 features)
// ============================================================================

void MLDefenderExtractor::extract_internal_features(
    const FlowStatsCore& flow,
    float len_entropy,
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
    internal->set_access_pattern_entropy(extract_internal_access_pattern_entropy(len_entropy));
}

float MLDefenderExtractor::extract_internal_connection_rate(const FlowStatsCore& /*flow*/) const {
    if (!aggregator_) return MISSING_FEATURE_SENTINEL;
    auto stats = window_stats_30s();  // [WINSTATS-CACHE-D289]
    float rate = static_cast<float>(stats.event_count) / 30.0f;
    return std::min(rate / 100.0f, 1.0f);
}

float MLDefenderExtractor::extract_internal_service_port_consistency(const FlowStatsCore& /*flow*/) const {
    if (!aggregator_) return MISSING_FEATURE_SENTINEL;
    auto stats = window_stats_30s();  // [WINSTATS-CACHE-D289]
    if (stats.event_count == 0) return 0.0f;
    // Alta consistencia = pocas variaciones de puerto (comportamiento normal)
    return 1.0f - std::min(
        static_cast<float>(stats.unique_ports_count) /
        static_cast<float>(stats.event_count),
        1.0f);
}

float MLDefenderExtractor::extract_internal_protocol_regularity(const FlowStatsCore& flow) const {
    // Protocol regularity: Consistency in packet timing
    float cv = iat_coefficient_of_variation(flow);

    // Low CV = high regularity
    float regularity = std::max(0.0f, 1.0f - cv);
    return regularity;
}

float MLDefenderExtractor::extract_internal_packet_size_consistency(const FlowStatsCore& flow) const {
    // Packet size consistency: Low std dev = consistent sizes
    const uint64_t n = flow.get_total_packets();
    float std_dev = len_std_dev(flow.len_all, n, flow.get_total_bytes());
    float mean = mean_of(flow.get_total_bytes(), n);

    if (mean == 0.0f) return MISSING_FEATURE_SENTINEL;

    float cv = std_dev / mean;

    // Low CV = high consistency
    float consistency = std::max(0.0f, 1.0f - cv);
    return consistency;
}

float MLDefenderExtractor::extract_internal_connection_duration_std(const FlowStatsCore& /*flow*/) const {
    // TODO(Phase 2): Requires multi-flow aggregator
    //
    // Standard deviation of connection durations requires multiple flows.
    //
    // For Phase 1: Return neutral value
    return MISSING_FEATURE_SENTINEL;  // Phase 2: implement with TimeWindowAggregator
}

float MLDefenderExtractor::extract_internal_lateral_movement_score(const FlowStatsCore& /*flow*/) const {
    if (!aggregator_) return MISSING_FEATURE_SENTINEL;
    auto stats = window_stats_30s();  // [WINSTATS-CACHE-D289]
    if (stats.event_count == 0) return 0.0f;
    // Muchas IPs únicas contactadas = posible lateral movement
    return std::min(
        static_cast<float>(stats.unique_ips_count) /
        static_cast<float>(stats.event_count),
        1.0f);
}

float MLDefenderExtractor::extract_internal_service_discovery_patterns(const FlowStatsCore& /*flow*/) const {
    if (!aggregator_) return MISSING_FEATURE_SENTINEL;
    auto stats = window_stats_30s();  // [WINSTATS-CACHE-D289]
    if (stats.event_count == 0) return 0.0f;
    // Muchos puertos únicos por evento = patrón de port scanning
    return std::min(
        static_cast<float>(stats.unique_ports_count) /
        static_cast<float>(stats.event_count),
        1.0f);
}

float MLDefenderExtractor::extract_internal_data_exfiltration_indicators(const FlowStatsCore& flow) const {
    // Data exfiltration: High upload ratio
    float upload_download_ratio = safe_divide(
        static_cast<float>(flow.sbytes),  // Upload (forward)
        static_cast<float>(flow.dbytes)   // Download (backward)
    );

    // High ratio (>5) = potential exfiltration
    float normalized = std::min(upload_download_ratio / 10.0f, 1.0f);
    return normalized;
}

float MLDefenderExtractor::extract_internal_temporal_anomaly_score(const FlowStatsCore& flow) const {
    // Temporal anomaly: Unusual timing patterns
    float cv = iat_coefficient_of_variation(flow);

    // Very low CV (<0.2) or very high CV (>2.0) = anomalous
    if (cv < 0.2f) {
        return 0.8f;  // Too regular (bot-like)
    } else if (cv > 2.0f) {
        return 0.7f;  // Too random (scan-like)
    } else {
        return 0.3f;  // Normal range
    }
}

float MLDefenderExtractor::extract_internal_access_pattern_entropy(float len_entropy) const {
    // Access pattern entropy: Entropy of packet sizes as proxy
    // [D308-PASO1] len_entropy es la entropia de longitudes de la foto DDoS v2 (mismo calculo, en el lock)
    if (len_entropy == MISSING_FEATURE_SENTINEL) return MISSING_FEATURE_SENTINEL;
    float entropy = len_entropy;

    // Normalize: 0-5 → 0.0-1.0
    float normalized = entropy / 5.0f;
    return std::min(normalized, 1.0f);
}

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

// [DDOS-SNAP-D290] Entropia de Shannon de las longitudes sobre el histograma incremental del flujo (std::map,
// orden ascendente, acumulacion en float). [D308-PASO1] Es la unica entropia de longitudes: la foto DDoS v2 la
// calcula en el lock y populate la recibe para ransomware.entropy e internal.access_pattern_entropy.
float MLDefenderExtractor::calculate_entropy_from_hist(const std::map<uint32_t, uint32_t>& hist,
                                                       uint64_t total_count) const {
    if (total_count == 0) return 0.0f;

    float entropy = 0.0f;
    float total = static_cast<float>(total_count);

    for (const auto& [value, count] : hist) {
        (void)value;
        float probability = static_cast<float>(count) / total;
        if (probability > 0.0f) {
            entropy -= probability * std::log2(probability);
        }
    }

    return entropy;
}

// [DDOS-SNAP-D290] Foto de los rasgos DDoS v2 de flujo. Se llama en el hilo del anillo DENTRO del
// lock del shard (with_flow_stats): sin recorrer vectores; O(k), k = longitudes distintas.
DdosFlowSnap MLDefenderExtractor::ddos_v2_flow_snapshot(const FlowStatistics& flow) const {
    DdosFlowSnap s;
    const uint64_t n = flow.get_total_packets();
    s.valid = true;
    s.syn_ack_ratio = extract_ddos_syn_ack_ratio(flow);
    s.flow_completion_rate = extract_ddos_flow_completion_rate(flow);
    s.flow_packet_count = static_cast<float>(n);
    s.mean_packet_size = (n == 0) ? 0.0f
        : static_cast<float>(flow.get_total_bytes()) / static_cast<float>(n);  // [D308-PASO1] D4
    s.packet_size_entropy = calculate_entropy_from_hist(flow.len_hist, n);
    return s;
}

// [D308-PASO1] Estadisticos sobre los acumuladores del flujo (O(1), sin recorrer paquetes). Varianza
// poblacional: E[x^2] - E[x]^2 con las sumas enteras exactas, evaluada en long double y recortada a 0; el error
// relativo es ~2^-64 * (1 + media^2 / var), muy por debajo de la precision del float que se devuelve
// (day308_paso1_diseno.md, seccion 1). Antes: dos pasadas en float sobre un vector por paquete.
static float std_dev_from_sums(long double sum, long double sum_sq, uint64_t n) {
    const long double m = sum / static_cast<long double>(n);
    long double var = sum_sq / static_cast<long double>(n) - m * m;
    if (var < 0.0L) var = 0.0L;
    return static_cast<float>(std::sqrt(var));
}

float MLDefenderExtractor::len_std_dev(const LenAcc& acc, uint64_t n, uint64_t sum) const {
    if (n < 2) return 0.0f;  // como el calculo anterior: menos de 2 valores -> 0
    return std_dev_from_sums(static_cast<long double>(sum), static_cast<long double>(acc.sum_sq), n);
}

float MLDefenderExtractor::iat_std_dev(const IatAcc& acc) const {
    if (acc.pairs == 0) return 0.0f;  // sin pares validos (o menos de 2 marcas) -> 0, como antes
    return std_dev_from_sums(static_cast<long double>(acc.sum), static_cast<long double>(acc.sum_sq), acc.pairs);
}

// Peculiaridad que se conserva: divide la suma de los pares VALIDOS entre (marcas - 1), es decir, cuenta tambien
// los pares desordenados; la desviacion (iat_std_dev) usa solo los pares validos.
float MLDefenderExtractor::iat_mean_quirk(const IatAcc& acc, uint64_t marcas) const {
    if (marcas < 2) return 0.0f;
    return static_cast<float>(acc.sum) / static_cast<float>(marcas - 1);
}

float MLDefenderExtractor::iat_coefficient_of_variation(const FlowStatsCore& flow) const {
    float mean = iat_mean_quirk(flow.iat_all, flow.get_total_packets());
    if (mean == 0.0f) return 0.0f;

    float std_dev = iat_std_dev(flow.iat_all);
    return std_dev / mean;
}

    // ============================================================================
    // CONVENIENCE METHOD - Populate all ML Defender features at once
    // DAY 46 COMPLETION: Now extracts ALL 142 fields from FlowStatistics
    // ============================================================================

// [WINSTATS-CACHE-D289] WindowStats de los últimos 30 s, una vez por evento dentro de populate.
WindowStats MLDefenderExtractor::window_stats_30s() const {
    if (window_cache_active_ && window_cache_valid_) return window_cache_;
    const auto now = TimeWindowAggregator::get_current_time_ns();
    WindowStats ws = aggregator_->get_window_stats(now - 30'000'000'000ULL, now);
    if (window_cache_active_) {
        window_cache_ = ws;
        window_cache_valid_ = true;
    }
    return ws;
}

namespace {
// [WINSTATS-CACHE-D289] Activa la caché durante un populate y la apaga al salir (también ante excepción).
struct WindowCacheScope {
    bool& active;
    bool& valid;
    WindowCacheScope(bool& a, bool& v) : active(a), valid(v) { active = true; valid = false; }
    ~WindowCacheScope() { active = false; valid = false; }
    WindowCacheScope(const WindowCacheScope&) = delete;
    WindowCacheScope& operator=(const WindowCacheScope&) = delete;
};
}  // namespace

void MLDefenderExtractor::populate_ml_defender_features(
        const FlowStatsCore& flow,
        float len_entropy,
        ::protobuf::NetworkSecurityEvent& proto_event) const {
    WindowCacheScope cache_scope(window_cache_active_, window_cache_valid_);  // [WINSTATS-CACHE-D289]

    // Get network_features submessage
    auto* net_features = proto_event.mutable_network_features();

    // ========================================================================
    // PART 1: ML DEFENDER EMBEDDED FEATURES (40 features)
    // ========================================================================

    // DDoS: ring_consumer escribe los 5 rasgos de flujo desde la foto (ddos_v2_flow_snapshot) [D307-PASO2]

    // Extract Ransomware features (10 features)
    auto* ransomware = net_features->mutable_ransomware_embedded();
    extract_ransomware_features(flow, len_entropy, ransomware);

    // Extract Traffic features (10 features)
    auto* traffic = net_features->mutable_traffic_classification();
    extract_traffic_features(flow, traffic);

    // Extract Internal features (10 features)
    auto* internal = net_features->mutable_internal_anomaly();
    extract_internal_features(flow, len_entropy, internal);

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

    // 📏 ESTADÍSTICAS DE LONGITUD - FORWARD  [D308-PASO1] desde los acumuladores; la suma es sbytes
    if (flow.spkts > 0) {
        net_features->set_forward_packet_length_min(flow.len_fwd.min);
        net_features->set_forward_packet_length_max(flow.len_fwd.max);
        net_features->set_forward_packet_length_mean(mean_of(flow.sbytes, flow.spkts));
        net_features->set_forward_packet_length_std(len_std_dev(flow.len_fwd, flow.spkts, flow.sbytes));
    }

    // 📏 ESTADÍSTICAS DE LONGITUD - BACKWARD  [D308-PASO1] la suma es dbytes
    if (flow.dpkts > 0) {
        net_features->set_backward_packet_length_min(flow.len_bwd.min);
        net_features->set_backward_packet_length_max(flow.len_bwd.max);
        net_features->set_backward_packet_length_mean(mean_of(flow.dbytes, flow.dpkts));
        net_features->set_backward_packet_length_std(len_std_dev(flow.len_bwd, flow.dpkts, flow.dbytes));
    }

    // 📊 ESTADÍSTICAS GLOBALES DE LONGITUD  [D308-PASO1] la suma es sbytes + dbytes
    const uint64_t n_total = flow.get_total_packets();
    if (n_total > 0) {
        net_features->set_minimum_packet_length(flow.len_all.min);
        net_features->set_maximum_packet_length(flow.len_all.max);

        float mean = mean_of(flow.get_total_bytes(), n_total);
        float std_dev = len_std_dev(flow.len_all, n_total, flow.get_total_bytes());

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

    // ⏱️ INTER-ARRIVAL TIMES - FLOW (all packets)  [D308-PASO1] desde los acumuladores: solo pares validos
    // (marca >= la anterior en llegada); se escriben si hay al menos uno, como antes
    if (flow.iat_all.pairs > 0) {
        float mean_ns = static_cast<float>(flow.iat_all.sum) / static_cast<float>(flow.iat_all.pairs);
        float std_ns = iat_std_dev(flow.iat_all);

        net_features->set_flow_inter_arrival_time_min(flow.iat_all.min);
        net_features->set_flow_inter_arrival_time_max(flow.iat_all.max);
        net_features->set_flow_inter_arrival_time_mean(mean_ns / 1000.0);  // Convert to microseconds
        net_features->set_flow_inter_arrival_time_std(std_ns / 1000.0);
    }

    // ⏱️ INTER-ARRIVAL TIMES - FORWARD
    if (flow.iat_fwd.pairs > 0) {
        float mean_ns = static_cast<float>(flow.iat_fwd.sum) / static_cast<float>(flow.iat_fwd.pairs);
        float std_ns = iat_std_dev(flow.iat_fwd);

        net_features->set_forward_inter_arrival_time_min(flow.iat_fwd.min);
        net_features->set_forward_inter_arrival_time_max(flow.iat_fwd.max);
        net_features->set_forward_inter_arrival_time_mean(mean_ns / 1000.0);
        net_features->set_forward_inter_arrival_time_std(std_ns / 1000.0);
        net_features->set_forward_inter_arrival_time_total(flow.iat_fwd.sum / 1000.0);
    }

    // ⏱️ INTER-ARRIVAL TIMES - BACKWARD
    if (flow.iat_bwd.pairs > 0) {
        float mean_ns = static_cast<float>(flow.iat_bwd.sum) / static_cast<float>(flow.iat_bwd.pairs);
        float std_ns = iat_std_dev(flow.iat_bwd);

        net_features->set_backward_inter_arrival_time_min(flow.iat_bwd.min);
        net_features->set_backward_inter_arrival_time_max(flow.iat_bwd.max);
        net_features->set_backward_inter_arrival_time_mean(mean_ns / 1000.0);
        net_features->set_backward_inter_arrival_time_std(std_ns / 1000.0);
        net_features->set_backward_inter_arrival_time_total(flow.iat_bwd.sum / 1000.0);
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

    // 📋 HEADERS  [D308-PASO1] suma por sentido; la cuenta es spkts / dpkts
    if (flow.spkts > 0) {
        net_features->set_forward_header_length(
            static_cast<double>(flow.fwd_header_sum) / static_cast<double>(flow.spkts)
        );
    }

    if (flow.dpkts > 0) {
        net_features->set_backward_header_length(
            static_cast<double>(flow.bwd_header_sum) / static_cast<double>(flow.dpkts)
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
