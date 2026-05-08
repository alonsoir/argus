#include "embedders/attack_embedder.hpp"
#include "event_loader.hpp"
#include <spdlog/spdlog.h>
#include <stdexcept>

namespace rag_ingester {

AttackEmbedder::AttackEmbedder(const std::string& onnx_path, float benign_sample_rate)
    : onnx_path_(onnx_path), benign_sample_rate_(benign_sample_rate) {
    spdlog::info("AttackEmbedder initialized: {} (benign_sample_rate={}, INPUT_DIM={})", 
                onnx_path, benign_sample_rate, INPUT_DIM);
    // TODO: Load ONNX Runtime session
}

AttackEmbedder::~AttackEmbedder() {
    spdlog::info("AttackEmbedder destroyed");
}

std::vector<float> AttackEmbedder::embed(const Event& event) {
    // Day 38: Construct 103-dimensional input (101 core + 2 meta)
    std::vector<float> input;
    input.reserve(INPUT_DIM);
    
    // 101 core features from event.features
    input.insert(input.end(), event.features.begin(), event.features.end());
    
    // Meta feature #1: discrepancy_score (ADR-002)
    input.push_back(event.discrepancy_score);
    
    // Meta feature #2: verdict count (ADR-002)
    input.push_back(static_cast<float>(event.verdicts.size()));
    
    // Validate input size (defensive programming)
    if (input.size() != INPUT_DIM) {
        throw std::runtime_error(
            "AttackEmbedder: Invalid input size " + std::to_string(input.size()) +
            " (expected " + std::to_string(INPUT_DIM) + ")"
        );
    }
    
    spdlog::debug("AttackEmbedder::embed() - input validated ({} features)", input.size());
    
    // TODO: Pass input to ONNX Runtime model
    // For now, return stub (256-d zero vector)
    return std::vector<float>(OUTPUT_DIM, 0.0f);
}

std::vector<std::vector<float>> AttackEmbedder::embed_batch(const std::vector<Event>& events) {
    spdlog::debug("AttackEmbedder::embed_batch() - {} events", events.size());
    
    // TODO: Implement batched ONNX inference
    // For now, call embed() individually
    std::vector<std::vector<float>> results;
    results.reserve(events.size());
    
    for (const auto& event : events) {
        results.push_back(embed(event));
    }
    
    return results;
}

bool AttackEmbedder::should_embed(const Event& /*event*/) const {
    // TODO: Implement sampling logic
    return true;
}

} // namespace rag_ingester
