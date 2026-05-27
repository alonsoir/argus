// Internal Traffic Classification Model
// Binary Classification: Benign vs Suspicious Internal Traffic
// Trees: 100
// Features: 10
// Via Appia Quality - Embedded C++20

#pragma once

#include <array>
#include <vector>
#include <cstddef>

namespace ml_defender {

class InternalDetector {
public:
    /// Input features for internal traffic classification
    struct Features {
        float internal_connection_rate;
        float service_port_consistency;
        float protocol_regularity;
        float packet_size_consistency;
        float connection_duration_std;
        float lateral_movement_score;
        float service_discovery_patterns;
        float data_exfiltration_indicators;
        float temporal_anomaly_score;
        float access_pattern_entropy;

        /// Convert to array for prediction
        std::array<float, 10> to_array() const noexcept {
            return {
                internal_connection_rate,
                service_port_consistency,
                protocol_regularity,
                packet_size_consistency,
                connection_duration_std,
                lateral_movement_score,
                service_discovery_patterns,
                data_exfiltration_indicators,
                temporal_anomaly_score,
                access_pattern_entropy
            };
        }
    };

    /// Prediction result
    struct Prediction {
        int class_id;           // 0=benign, 1=suspicious
        float probability;      // Probability of predicted class
        float benign_prob;      // P(benign)
        float suspicious_prob;  // P(suspicious)

        /// Check if traffic is benign (using threshold)
        bool is_benign(float threshold = 0.5f) const noexcept {
            return class_id == 0 && probability >= threshold;
        }

        /// Check if traffic is suspicious (using threshold)
        bool is_suspicious(float threshold = 0.5f) const noexcept {
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
    InternalDetector() noexcept;

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