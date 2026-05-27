// External Traffic Classification Model
// Binary Classification: Internet vs Internal Traffic
// Trees: 100
// Features: 10
// Via Appia Quality - Embedded C++20

#pragma once

#include <array>
#include <vector>
#include <cstddef>

namespace ml_defender {

class TrafficDetector {
public:
    /// Input features for traffic classification
    struct Features {
        float packet_rate;
        float connection_rate;
        float tcp_udp_ratio;
        float avg_packet_size;
        float port_entropy;
        float flow_duration_std;
        float src_ip_entropy;
        float dst_ip_concentration;
        float protocol_variety;
        float temporal_consistency;

        /// Convert to array for prediction
        std::array<float, 10> to_array() const noexcept {
            return {
                packet_rate,
                connection_rate,
                tcp_udp_ratio,
                avg_packet_size,
                port_entropy,
                flow_duration_std,
                src_ip_entropy,
                dst_ip_concentration,
                protocol_variety,
                temporal_consistency
            };
        }
    };

    /// Prediction result
    struct Prediction {
        int class_id;           // 0=internet, 1=internal
        float probability;      // Probability of predicted class
        float internet_prob;    // P(internet)
        float internal_prob;    // P(internal)

        /// Check if traffic is internet-bound (using threshold)
        bool is_internet(float threshold = 0.5f) const noexcept {
            return class_id == 0 && probability >= threshold;
        }

        /// Check if traffic is internal (using threshold)
        bool is_internal(float threshold = 0.5f) const noexcept {
            return class_id == 1 && probability >= threshold;
        }

        /// Get confidence level as string
        const char* confidence_level() const noexcept {
            if (probability >= 0.95f) return "very_high";
            if (probability >= 0.85f) return "high";
            if (probability >= 0.70f) return "medium";
            if (probability >= 0.55f) return "low";
            return "very_low";
        }
    };

    /// Constructor - validates model at compile time
    TrafficDetector() noexcept;

    /// Predict single sample (latency target: <100μs)
    Prediction predict(const Features& features) const noexcept;

    /// Batch prediction for multiple samples
    std::vector<Prediction> predict_batch(
        const std::vector<Features>& features_batch
    ) const;

    /// Get model metadata
    size_t num_trees() const noexcept { return 100; }
    size_t num_features() const noexcept { return 10; }
    const char* model_version() const noexcept { return "1.0.0"; }
};

} // namespace ml_defender