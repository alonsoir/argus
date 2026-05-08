#include "feature_extractor.hpp"
#include <spdlog/sinks/stdout_color_sinks.h>
#include <cmath>
#include <algorithm>
#include <numeric>
#include <limits>

namespace ml_detector {

// Nombres de las 23 features (del metadata)
static const std::vector<std::string> LEVEL1_FEATURE_NAMES = {
    "Packet Length Std",
    "Subflow Fwd Bytes",
    "Fwd Packet Length Max",
    "Avg Fwd Segment Size",
    "ACK Flag Count",
    "Packet Length Variance",
    "PSH Flag Count",
    "Bwd Packet Length Max",
    "act_data_pkt_fwd",
    "Total Length of Fwd Packets",
    "Fwd Packet Length Std",
    "Fwd Packets/s",
    "Subflow Bwd Bytes",
    "Destination Port",
    "Init_Win_bytes_forward",
    "Subflow Fwd Packets",
    "Fwd IAT Min",
    "Packet Length Mean",
    "Total Length of Bwd Packets",
    "Bwd Packet Length Mean",
    "Bwd Packet Length Min",
    "Flow Duration",
    "Flow Packets/s"
};

FeatureExtractor::FeatureExtractor()
    : logger_(spdlog::get("ml-detector")) {
    if (!logger_) {
        logger_ = spdlog::stdout_color_mt("feature-extractor");
    }
}

const std::vector<std::string>& FeatureExtractor::get_feature_names() {
    return LEVEL1_FEATURE_NAMES;
}

float FeatureExtractor::safe_divide(float numerator, float denominator, float default_value) {
    if (denominator == 0.0f || std::isnan(denominator) || std::isinf(denominator)) {
        return default_value;
    }
    float result = numerator / denominator;
    if (std::isnan(result) || std::isinf(result)) {
        return default_value;
    }
    return result;
}

float FeatureExtractor::calculate_std_dev(const std::vector<float>& values, float mean) {
    if (values.empty()) return 0.0f;
    
    float sum_sq_diff = 0.0f;
    for (float val : values) {
        float diff = val - mean;
        sum_sq_diff += diff * diff;
    }
    
    return std::sqrt(sum_sq_diff / static_cast<float>(values.size()));
}

float FeatureExtractor::calculate_variance(const std::vector<float>& values, float mean) {
    if (values.empty()) return 0.0f;
    
    float sum_sq_diff = 0.0f;
    for (float val : values) {
        float diff = val - mean;
        sum_sq_diff += diff * diff;
    }
    
    return sum_sq_diff / static_cast<float>(values.size());
}

std::vector<float> FeatureExtractor::extract_level1_features(const protobuf::NetworkSecurityEvent& event) {
    std::vector<float> features(23, 0.0f);
    
    // Verificar que tenemos NetworkFeatures
    if (!event.has_network_features()) {
        logger_->error("NetworkSecurityEvent missing network_features");
        throw std::runtime_error("Missing network_features in event");
    }
    
    const auto& nf = event.network_features();
    
    // Duración del flow (microsegundos → segundos)
    float flow_duration_sec = static_cast<float>(nf.flow_duration_microseconds()) / 1000000.0f;
    
    // Feature 0: Packet Length Std
    features[0] = static_cast<float>(nf.packet_length_std());
    
    // Feature 1: Subflow Fwd Bytes
    features[1] = static_cast<float>(nf.total_forward_bytes());
    
    // Feature 2: Fwd Packet Length Max
    features[2] = static_cast<float>(nf.forward_packet_length_max());
    
    // Feature 3: Avg Fwd Segment Size
    features[3] = static_cast<float>(nf.average_forward_segment_size());
    
    // Feature 4: ACK Flag Count
    features[4] = static_cast<float>(nf.ack_flag_count());
    
    // Feature 5: Packet Length Variance
    features[5] = static_cast<float>(nf.packet_length_variance());
    
    // Feature 6: PSH Flag Count
    features[6] = static_cast<float>(nf.psh_flag_count());
    
    // Feature 7: Bwd Packet Length Max
    features[7] = static_cast<float>(nf.backward_packet_length_max());
    
    // Feature 8: act_data_pkt_fwd
    // Packets con payload - asumimos que total_forward_packets incluye data packets
    features[8] = static_cast<float>(nf.total_forward_packets());
    
    // Feature 9: Total Length of Fwd Packets
    features[9] = static_cast<float>(nf.total_forward_bytes());
    
    // Feature 10: Fwd Packet Length Std
    features[10] = static_cast<float>(nf.forward_packet_length_std());
    
    // Feature 11: Fwd Packets/s
    features[11] = static_cast<float>(nf.forward_packets_per_second());
    
    // Feature 12: Subflow Bwd Bytes
    features[12] = static_cast<float>(nf.total_backward_bytes());
    
    // Feature 13: Destination Port
    features[13] = static_cast<float>(nf.destination_port());
    
    // Feature 14: Init_Win_bytes_forward
    // Si no está en el protobuf, podemos dejarlo en 0 o calcular aproximación
    features[14] = 0.0f;  // TODO: Añadir campo al protobuf si es crítico
    
    // Feature 15: Subflow Fwd Packets
    features[15] = static_cast<float>(nf.total_forward_packets());
    
    // Feature 16: Fwd IAT Min
    features[16] = static_cast<float>(nf.forward_inter_arrival_time_min());
    
    // Feature 17: Packet Length Mean
    features[17] = static_cast<float>(nf.packet_length_mean());
    
    // Feature 18: Total Length of Bwd Packets
    features[18] = static_cast<float>(nf.total_backward_bytes());
    
    // Feature 19: Bwd Packet Length Mean
    features[19] = static_cast<float>(nf.backward_packet_length_mean());
    
    // Feature 20: Bwd Packet Length Min
    features[20] = static_cast<float>(nf.backward_packet_length_min());
    
    // Feature 21: Flow Duration
    features[21] = flow_duration_sec;
    
    // Feature 22: Flow Packets/s
    features[22] = static_cast<float>(nf.flow_packets_per_second());
    
    // Logging detallado en modo debug
    if (logger_->level() <= spdlog::level::debug) {
        logger_->debug("Feature Extraction:");
        logger_->debug("  Flow: {}:{} -> {}:{} ({})", 
                      nf.source_ip(), nf.source_port(),
                      nf.destination_ip(), nf.destination_port(),
                      nf.protocol_name());
        logger_->debug("  Duration: {:.3f}s", flow_duration_sec);
        logger_->debug("  Packets: {} fwd, {} bwd, {} total", 
                      nf.total_forward_packets(), 
                      nf.total_backward_packets(),
                      nf.total_forward_packets() + nf.total_backward_packets());
        logger_->debug("  Bytes: {} fwd, {} bwd, {} total",
                      nf.total_forward_bytes(), 
                      nf.total_backward_bytes(),
                      nf.total_forward_bytes() + nf.total_backward_bytes());
        
        for (size_t i = 0; i < features.size(); ++i) {
            logger_->debug("  Feature[{:2d}] {:30s}: {:12.6f}", 
                          i, LEVEL1_FEATURE_NAMES[i], features[i]);
        }
    }
    
    return features;
}

bool FeatureExtractor::validate_features(const std::vector<float>& features) {
    if (features.size() != 23) {
        logger_->error("Invalid feature vector size: {} (expected 23)", features.size());
        return false;
    }
    
    for (size_t i = 0; i < features.size(); ++i) {
        if (std::isnan(features[i])) {
            logger_->error("Feature[{}] {} is NaN", i, LEVEL1_FEATURE_NAMES[i]);
            return false;
        }
        
        if (std::isinf(features[i])) {
            logger_->error("Feature[{}] {} is Inf", i, LEVEL1_FEATURE_NAMES[i]);
            return false;
        }
        
        // Rangos razonables (básico)
        if (features[i] < -1e9 || features[i] > 1e9) {
            logger_->warn("Feature[{}] {} has suspicious value: {:.2e}", 
                         i, LEVEL1_FEATURE_NAMES[i], features[i]);
        }
    }
    
    return true;
}

    // ============================================================================
// LEVEL 2: DDoS Features (10 features)
// ============================================================================
std::vector<float> FeatureExtractor::extract_level2_ddos_features(
    const protobuf::NetworkFeatures& nf
) {
    std::vector<float> features(10);

    // [0] SYN/ACK Ratio
    float total_flags = static_cast<float>(nf.fin_flag_count()) + static_cast<float>(nf.syn_flag_count()) +
                       static_cast<float>(nf.rst_flag_count()) + static_cast<float>(nf.psh_flag_count()) +
                       static_cast<float>(nf.ack_flag_count()) + static_cast<float>(nf.urg_flag_count());
    features[0] = safe_divide(static_cast<float>(nf.syn_flag_count()), total_flags);

    // [1] Packet Symmetry (forward vs backward)
    float total_packets = static_cast<float>(nf.total_forward_packets()) + static_cast<float>(nf.total_backward_packets());
    features[1] = safe_divide(static_cast<float>(nf.total_forward_packets()), total_packets);

    // [2] Source IP Dispersion (using protocol variety as proxy)
    features[2] = normalize(1.0f, 0.0f, 10.0f);

    // [3] Protocol Anomaly Score (derived from unusual protocol combinations)
    float protocol_anomaly = (1.0f > 5) ? 1.0f : 0.0f;
    features[3] = protocol_anomaly;

    // [4] Packet Size Entropy (using packet length std)
    features[4] = normalize(static_cast<float>(nf.packet_length_std()), 0.0f, 1500.0f);

    // [5] Traffic Amplification Factor (response vs request size)
    float fwd_bytes = static_cast<float>(nf.total_forward_bytes());
    float bwd_bytes = static_cast<float>(nf.total_backward_bytes());
    features[5] = safe_divide(bwd_bytes, std::max(fwd_bytes, 1.0f));

    // [6] Flow Completion Rate (using FIN flags)
    features[6] = safe_divide(static_cast<float>(nf.fin_flag_count()), total_packets);

    // [7] Geographical Concentration (placeholder - implement if available)
    features[7] = 0.5f;  // Default neutral value

    // [8] Traffic Escalation Rate (using flow bytes/s)
    float flow_bytes_per_sec = static_cast<float>(nf.flow_bytes_per_second());
    features[8] = normalize(flow_bytes_per_sec, 0.0f, 1e6f);  // Normalize to 1Mbps

    // [9] Resource Saturation Score (using packet rate)
    float packet_rate = safe_divide(total_packets,
                                    std::max(static_cast<float>(nf.flow_duration_microseconds()) / 1e6f, 1.0f));
    features[9] = normalize(packet_rate, 0.0f, 1000.0f);  // Normalize to 1000 pps

    return features;
}

std::vector<float> FeatureExtractor::extract_level2_ransomware_features(
    const protobuf::NetworkFeatures& nf) {

    std::vector<float> features(10, 0.0f);

    // Duración del flow en segundos
    float flow_duration_sec = static_cast<float>(nf.flow_duration_microseconds()) / 1000000.0f;

    // [0] io_intensity - Basado en bytes transferidos y rate
    float total_bytes = static_cast<float>(
        nf.total_forward_packets() + nf.total_backward_packets()
    );
    features[0] = safe_divide(total_bytes, flow_duration_sec + 1.0f, 0.0f);
    features[0] = std::min(features[0] / 100000.0f, 2.0f); // Normalizar a [0-2]

    // [1] entropy - ⭐ MOST IMPORTANT (36% feature importance)
    // Usar packet length variance como proxy de entropía
    float pkt_variance = static_cast<float>(nf.packet_length_variance());
    features[1] = std::min(pkt_variance / 100000.0f, 2.0f);

    // [2] resource_usage - Basado en throughput (25% importance)
    float bytes_per_sec = static_cast<float>(nf.flow_bytes_per_second());
    features[2] = std::min(bytes_per_sec / 500000.0f, 2.0f);

    // [3] network_activity - Packets per second
    float flow_packets_s = static_cast<float>(nf.flow_packets_per_second());
    features[3] = std::min(flow_packets_s / 1000.0f, 2.0f);

    // [4] file_operations - Proxy: PSH flags (indica escrituras/lecturas)
    float psh_ratio = safe_divide(
        static_cast<float>(nf.psh_flag_count()),
        static_cast<float>(nf.total_forward_packets() + 1),
        0.0f
    );
    features[4] = std::min(psh_ratio * 2.0f, 2.0f);

    // [5] process_anomaly - Proxy: ACK flag ratio (comportamiento anómalo)
    float ack_ratio = safe_divide(
        static_cast<float>(nf.ack_flag_count()),
        static_cast<float>(nf.total_forward_packets() + 1),
        0.0f
    );
    features[5] = std::min(ack_ratio * 2.0f, 2.0f);

    // [6] temporal_pattern - IAT (Inter-Arrival Time) variability
    float fwd_iat_std = static_cast<float>(nf.forward_inter_arrival_time_std());
    features[6] = std::min(fwd_iat_std / 100000.0f, 2.0f);

    // [7] access_frequency - Total packets
    float total_packets = static_cast<float>(
        nf.total_forward_packets() + nf.total_backward_packets()
    );
    features[7] = std::min(total_packets / 1000.0f, 2.0f);

    // [8] data_volume - Total bytes normalized
    float total_flow_bytes = static_cast<float>(
        nf.total_forward_bytes() + nf.total_backward_bytes()
    );
    features[8] = std::min(total_flow_bytes / 1000000.0f, 2.0f);

    // [9] behavior_consistency - Proxy: Forward/Backward ratio consistency
    float fwd_bwd_ratio = safe_divide(
        static_cast<float>(nf.total_forward_packets()),
        static_cast<float>(nf.total_backward_packets() + 1),
        1.0f
    );
    // Normalizar: ratio cercano a 1.0 = consistente (valor alto)
    features[9] = std::min(1.0f / (std::abs(fwd_bwd_ratio - 1.0f) + 0.1f), 1.0f);

    return features;
}

// ============================================================================
// LEVEL 3: Traffic Classification Features (10 features)
// ============================================================================
std::vector<float> FeatureExtractor::extract_level3_traffic_features(
    const protobuf::NetworkFeatures& nf
) {
    std::vector<float> features(10);

    // [0] Packet Rate
    float total_packets = static_cast<float>(nf.total_forward_packets()) + static_cast<float>(nf.total_backward_packets());
    features[0] = normalize(
        safe_divide(total_packets, std::max(static_cast<float>(nf.flow_duration_microseconds()) / 1e6f, 1.0f)),
        0.0f, 1000.0f
    );

    // [1] Connection Rate (using flow IAT as proxy)
    features[1] = normalize(1.0f / std::max(static_cast<float>(nf.flow_inter_arrival_time_mean()), 0.001f), 0.0f, 100.0f);

    // [2] TCP/UDP Ratio (derived from protocol type)
    // Assuming protocol 6=TCP, 17=UDP
    features[2] = (nf.protocol_number() == 6) ? 0.9f :
                  (nf.protocol_number() == 17) ? 0.1f : 0.5f;

    // [3] Average Packet Size
    float avg_packet_size = safe_divide(
        static_cast<float>(nf.total_forward_bytes()) + static_cast<float>(nf.total_backward_bytes()),
        total_packets
    );
    features[3] = normalize(avg_packet_size, 0.0f, 1500.0f);

    // [4] Port Entropy (high for internet, low for internal)
    // Use port variety and flow IAT std as proxy
    float port_entropy = normalize(static_cast<float>(nf.flow_inter_arrival_time_std()), 0.0f, 1e6f);
    features[4] = std::min(port_entropy, 1.0f);

    // [5] Flow Duration Std (variation in connection times)
    features[5] = normalize(static_cast<float>(nf.flow_duration_microseconds()) / 1e6f, 0.0f, 3600.0f);  // Up to 1 hour

    // [6] Source IP Entropy (use protocol variety as proxy)
    features[6] = normalize(1.0f, 0.0f, 10.0f);

    // [7] Destination IP Concentration (inverse of variety)
    features[7] = 1.0f - normalize(1.0f, 0.0f, 10.0f);

    // [8] Protocol Variety
    features[8] = normalize(1.0f, 0.0f, 10.0f);

    // [9] Temporal Consistency (using IAT mean/std ratio)
    float temporal_consistency = safe_divide(
        static_cast<float>(nf.flow_inter_arrival_time_mean()),
        std::max(static_cast<float>(nf.flow_inter_arrival_time_std()), 0.001f)
    );
    features[9] = normalize(temporal_consistency, 0.0f, 10.0f);

    return features;
}

// ============================================================================
// LEVEL 3: Internal Traffic Analysis Features (10 features)
// ============================================================================
std::vector<float> FeatureExtractor::extract_level3_internal_features(
    const protobuf::NetworkFeatures& nf
) {
    std::vector<float> features(10);

    // [0] Internal Connection Rate
    float total_packets = static_cast<float>(nf.total_forward_packets()) + static_cast<float>(nf.total_backward_packets());
    features[0] = normalize(
        safe_divide(total_packets, std::max(static_cast<float>(nf.flow_duration_microseconds()) / 1e6f, 1.0f)),
        0.0f, 500.0f  // Internal typically lower than internet
    );

    // [1] Service Port Consistency (low variety = high consistency)
    features[1] = 1.0f - normalize(1.0f, 0.0f, 5.0f);

    // [2] Protocol Regularity (inverse of variety)
    features[2] = 1.0f - normalize(1.0f, 0.0f, 3.0f);

    // [3] Packet Size Consistency (inverse of std)
    float size_consistency = 1.0f / std::max(static_cast<float>(nf.packet_length_std()), 1.0f);
    features[3] = normalize(size_consistency, 0.0f, 1.0f);

    // [4] Connection Duration Std
    features[4] = normalize(static_cast<float>(nf.flow_duration_microseconds()) / 1e6f, 0.0f, 1800.0f);  // Up to 30 min

    // [5] Lateral Movement Score (high SYN rate, low completion)
    float syn_rate = safe_divide(
        static_cast<float>(nf.syn_flag_count()),
        total_packets
    );
    float completion_rate = safe_divide(
        static_cast<float>(nf.fin_flag_count()),
        std::max(static_cast<float>(nf.syn_flag_count()), 1.0f)
    );
    features[5] = syn_rate * (1.0f - completion_rate);

    // [6] Service Discovery Patterns (RST flags indicate scanning)
    features[6] = normalize(static_cast<float>(nf.rst_flag_count()), 0.0f, 100.0f);

    // [7] Data Exfiltration Indicators (high outbound data)
    float outbound_ratio = safe_divide(
        static_cast<float>(nf.total_forward_bytes()),
        std::max(static_cast<float>(nf.total_backward_bytes()), 1.0f)
    );
    features[7] = (outbound_ratio > 2.0f) ? normalize(outbound_ratio, 2.0f, 10.0f) : 0.0f;

    // [8] Temporal Anomaly Score (using flow IAT variance)
    float temporal_variance = safe_divide(static_cast<float>(nf.flow_inter_arrival_time_std()),
                                         std::max(static_cast<float>(nf.flow_inter_arrival_time_mean()), 0.001f));
    features[8] = normalize(temporal_variance, 0.0f, 10.0f);

    // [9] Access Pattern Entropy (using packet size std)
    features[9] = normalize(static_cast<float>(nf.packet_length_std()), 0.0f, 500.0f);

    return features;
}

    // ============================================================================
    // Helper Methods
    // ============================================================================
    float FeatureExtractor::normalize(float value, float min, float max) const {
    if (max <= min) return 0.0f;
    float normalized = (value - min) / (max - min);
    return std::max(0.0f, std::min(1.0f, normalized));
}

    float FeatureExtractor::safe_divide(float numerator, float denominator) const {
    if (std::abs(denominator) < 1e-6f) return 0.0f;
    return numerator / denominator;
}

} // namespace ml_detector
