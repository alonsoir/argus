// ddos_detector.cpp
#include "ml_defender/ddos_detector.hpp"
#include "ml_defender/ddos_trees_inline.hpp"

namespace ml_defender {

DDoSDetector::DDoSDetector() noexcept {
    // Model validated at compile time via constexpr
}

DDoSDetector::Prediction DDoSDetector::predict(const Features& features) const noexcept {
    Prediction result;

    // Convert features to array format for predict_ddos()
    const float feature_array[ddos::DDOS_NUM_FEATURES] = {
        features.syn_ack_ratio,                  // [0]
        features.packet_symmetry,                // [1]
        features.source_ip_dispersion,           // [2]
        features.protocol_anomaly_score,         // [3]
        features.packet_size_entropy,            // [4]
        features.traffic_amplification_factor,   // [5]
        features.flow_completion_rate,           // [6]
        features.traffic_escalation_rate,        // [7]
        features.resource_saturation_score       // [8]
    };

    // Use the inline prediction function from ddos_trees_inline.hpp
    // Returns P(ddos) - probability of DDoS attack
    result.ddos_prob = ddos::predict_ddos(feature_array);
    result.normal_prob = 1.0f - result.ddos_prob;

    // Determine predicted class and probability of predicted class
    if (result.ddos_prob >= 0.5f) {
        result.class_id = 1;  // DDoS
        result.probability = result.ddos_prob;
    } else {
        result.class_id = 0;  // Normal
        result.probability = result.normal_prob;
    }

    return result;
}

std::vector<DDoSDetector::Prediction> DDoSDetector::predict_batch(
    const std::vector<Features>& features_batch
) const {
    std::vector<Prediction> results;
    results.reserve(features_batch.size());

    for (const auto& features : features_batch) {
        results.push_back(predict(features));
    }

    return results;
}

} // namespace ml_defender