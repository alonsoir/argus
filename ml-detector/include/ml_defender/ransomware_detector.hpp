// ML Defender - Ransomware Detector C++20 Implementation
// Embedded RandomForest (100 trees, 10 features)
// Author: Alonso + Claude (Co-authored)
// Performance target: <100μs per prediction

#pragma once

#include <array>
#include <cstdint>
#include <string>
#include <vector>

namespace ml_defender {

/// High-performance ransomware detector using embedded RandomForest
/// Thread-safe, no heap allocations in hot path, <100μs latency
class RansomwareDetector {
public:
    /// Input features (MUST be in this exact order)
    struct Features {
        float io_intensity;        // [0.0-2.0] - 24% importance
        float entropy;             // [0.0-2.0] - ⭐ 36% importance (MOST CRITICAL)
        float resource_usage;      // [0.0-2.0] - 25% importance
        float network_activity;    // [0.0-2.0] - 8% importance
        float file_operations;     // [0.0-2.0] - 2% importance
        float process_anomaly;     // [0.0-2.0] - <1% importance
        float temporal_pattern;    // [0.0-2.0] - <1% importance
        float access_frequency;    // [0.0-2.0] - 2% importance
        float data_volume;         // [0.0-2.0] - 1% importance
        float behavior_consistency;// [0.0-1.0] - 2% importance

        /// Convert to array for indexed access
        [[nodiscard]] constexpr std::array<float, 10> to_array() const noexcept {
            return {io_intensity, entropy, resource_usage, network_activity,
                    file_operations, process_anomaly, temporal_pattern,
                    access_frequency, data_volume, behavior_consistency};
        }
    };

    /// Prediction result
    struct Prediction {
        int class_id;           // 0=benign, 1=ransomware
        float probability;      // Confidence [0.0-1.0]
        float benign_prob;      // P(benign)
        float ransomware_prob;  // P(ransomware)

        /// Check if detection exceeds threshold
        [[nodiscard]] constexpr bool is_ransomware(float threshold = 0.75f) const noexcept {
            return ransomware_prob >= threshold;
        }

        /// Get confidence level: low (<0.6), medium (0.6-0.8), high (>0.8)
        [[nodiscard]] constexpr const char* confidence_level() const noexcept {
            if (probability < 0.6f) return "low";
            if (probability < 0.8f) return "medium";
            return "high";
        }
    };

    /// Constructor - validates model is embedded correctly
    RansomwareDetector() noexcept;

    /// Single prediction (thread-safe, const, noexcept)
    /// Target: <100μs (typically 30-50μs)
    [[nodiscard]] Prediction predict(const Features& features) const noexcept;

    /// Batch prediction for improved throughput
    [[nodiscard]] std::vector<Prediction> predict_batch(
        const std::vector<Features>& batch) const;

    /// Get model metadata
    [[nodiscard]] constexpr size_t num_trees() const noexcept { return 100; }
    [[nodiscard]] constexpr size_t num_features() const noexcept { return 10; }
    [[nodiscard]] constexpr const char* model_version() const noexcept {
        return "v1.0-embedded";
    }

private:
    // Model is embedded at compile-time, no runtime data needed
    bool m_initialized;
};

} // namespace ml_defender