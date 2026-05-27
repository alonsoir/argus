// DDoS Detection Model
// Binary Classification: Normal vs DDoS Traffic
// Trees: 100
// Features: 10
// Via Appia Quality - Embedded C++20

#pragma once

#include <array>
#include <vector>
#include <cstddef>

namespace ml_defender {

class DDoSDetector {
public:
    /// Input features for DDoS detection
    struct Features {
        float syn_ack_ratio;
        float packet_symmetry;
        float source_ip_dispersion;
        float protocol_anomaly_score;
        float packet_size_entropy;
        float traffic_amplification_factor;
        float flow_completion_rate;
        float geographical_concentration;
        float traffic_escalation_rate;
        float resource_saturation_score;

        /// Convert to array for prediction
        std::array<float, 10> to_array() const noexcept {
            return {
                syn_ack_ratio,
                packet_symmetry,
                source_ip_dispersion,
                protocol_anomaly_score,
                packet_size_entropy,
                traffic_amplification_factor,
                flow_completion_rate,
                geographical_concentration,
                traffic_escalation_rate,
                resource_saturation_score
            };
        }
    };

    /// Prediction result
    struct Prediction {
        int class_id;           // 0=normal, 1=ddos
        float probability;      // Probability of predicted class
        float normal_prob;      // P(normal)
        float ddos_prob;        // P(ddos)

        /// Check if traffic is normal (using threshold)
        bool is_normal(float threshold = 0.5f) const noexcept {
            return class_id == 0 && probability >= threshold;
        }

        /// Check if traffic is DDoS attack (using threshold)
        bool is_ddos(float threshold = 0.5f) const noexcept {
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
    DDoSDetector() noexcept;

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