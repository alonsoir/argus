// ML Defender - Ransomware Detector Implementation
// Optimized for <100μs latency with inline constexpr trees

#include "ml_defender/ransomware_detector.hpp"
#include "forest_trees_inline.hpp"  // Auto-generated trees

#include <algorithm>
#include <cmath>

namespace ml_defender {

RansomwareDetector::RansomwareDetector() noexcept : m_initialized(true) {
    // Validate embedded model at construction
    static_assert(detail::NUM_TREES == 100, "Expected 100 trees");
    static_assert(detail::NUM_FEATURES == 10, "Expected 10 features");

    // Compile-time validation passed
    // Trees are already embedded as constexpr data
}

RansomwareDetector::Prediction RansomwareDetector::predict(const Features& features) const noexcept {
    // Convert features to array for fast indexed access
    const auto feature_array = features.to_array();

    // Accumulator for tree votes
    float votes_ransomware = 0.0f;

    // Iterate through all 100 trees
    for (size_t tree_idx = 0; tree_idx < detail::NUM_TREES; ++tree_idx) {
        const detail::TreeNode* tree = detail::all_trees[tree_idx];
        int32_t node_idx = 0;  // Start at root

        // Navigate tree until reaching a leaf
        // Leaves have feature_idx == -2
        while (tree[node_idx].feature_idx >= 0) [[likely]] {
            const int16_t feature_idx = tree[node_idx].feature_idx;
            const float threshold = tree[node_idx].threshold;
            const float feature_value = feature_array[static_cast<size_t>(feature_idx)];

            // Branch prediction hint: left branch more common in trained model
            if (feature_value <= threshold) [[likely]] {
                node_idx = tree[node_idx].left_child;
            } else {
                node_idx = tree[node_idx].right_child;
            }
        }

        // Accumulate leaf vote: value[1] = P(ransomware)
        votes_ransomware += tree[node_idx].value[1];
    }

    // Average across all trees
    const float prob_ransomware = votes_ransomware / static_cast<float>(detail::NUM_TREES);
    const float prob_benign = 1.0f - prob_ransomware;

    // Determine final class
    const int class_id = (prob_ransomware > 0.5f) ? 1 : 0;
    const float confidence = std::max(prob_benign, prob_ransomware);

    return Prediction{
        .class_id = class_id,
        .probability = confidence,
        .benign_prob = prob_benign,
        .ransomware_prob = prob_ransomware
    };
}

std::vector<RansomwareDetector::Prediction> RansomwareDetector::predict_batch(
    const std::vector<Features>& batch) const {

    std::vector<Prediction> results;
    results.reserve(batch.size());

    for (const auto& features : batch) {
        results.push_back(predict(features));
    }

    return results;
}

} // namespace ml_defender