#include "embedders/simple_embedder.hpp"
#include "event_loader.hpp"
#include <spdlog/spdlog.h>
#include <random>
#include <cmath>

namespace rag_ingester {

SimpleEmbedder::SimpleEmbedder() {
    spdlog::info("SimpleEmbedder: Initializing random projection matrices...");
    
    // Initialize with different seeds for each embedding type
    init_projection_matrix(chronos_matrix_, INPUT_DIM, CHRONOS_DIM, 42);
    init_projection_matrix(sbert_matrix_, INPUT_DIM, SBERT_DIM, 43);
    init_projection_matrix(attack_matrix_, INPUT_DIM, ATTACK_DIM, 44);
    
    spdlog::info("SimpleEmbedder initialized:");
    spdlog::info("  Chronos: {}→{} dims", INPUT_DIM, CHRONOS_DIM);
    spdlog::info("  SBERT:   {}→{} dims", INPUT_DIM, SBERT_DIM);
    spdlog::info("  Attack:  {}→{} dims", INPUT_DIM, ATTACK_DIM);
}

void SimpleEmbedder::init_projection_matrix(
    std::vector<std::vector<float>>& matrix,
    size_t input_dim,
    size_t output_dim,
    int seed
) {
    // Random Gaussian matrix (Johnson-Lindenstrauss)
    std::mt19937 rng(seed);
    std::normal_distribution<float> dist(0.0f, 1.0f / std::sqrt(output_dim));
    
    matrix.resize(input_dim);
    for (size_t i = 0; i < input_dim; ++i) {
        matrix[i].resize(output_dim);
        for (size_t j = 0; j < output_dim; ++j) {
            matrix[i][j] = dist(rng);
        }
    }
}

std::vector<float> SimpleEmbedder::build_input(const Event& event) {
    // event.features already contains complete 105-d vector:
    // - 101 core network features
    // - 4 embedded detector features
    // No need to add anything - just validate and return
    
    std::vector<float> input(event.features.begin(), event.features.end());
    
    if (input.size() != INPUT_DIM) {
        throw std::runtime_error(
            "SimpleEmbedder: Invalid input size " + std::to_string(input.size()) +
            " (expected " + std::to_string(INPUT_DIM) + ")"
        );
    }
    
    return input;
}

std::vector<float> SimpleEmbedder::project(
    const std::vector<float>& input,
    const std::vector<std::vector<float>>& matrix
) {
    size_t output_dim = matrix[0].size();
    std::vector<float> output(output_dim, 0.0f);
    
    // Matrix multiplication: output = input · matrix
    for (size_t i = 0; i < input.size(); ++i) {
        for (size_t j = 0; j < output_dim; ++j) {
            output[j] += input[i] * matrix[i][j];
        }
    }
    
    // L2 normalize for better FAISS performance
    float norm = 0.0f;
    for (float val : output) {
        norm += val * val;
    }
    norm = std::sqrt(norm);
    
    if (norm > 1e-6f) {
        for (float& val : output) {
            val /= norm;
        }
    }
    
    return output;
}

std::vector<float> SimpleEmbedder::embed_chronos(const Event& event) {
    auto input = build_input(event);
    return project(input, chronos_matrix_);
}

std::vector<float> SimpleEmbedder::embed_sbert(const Event& event) {
    auto input = build_input(event);
    return project(input, sbert_matrix_);
}

std::vector<float> SimpleEmbedder::embed_attack(const Event& event) {
    auto input = build_input(event);
    return project(input, attack_matrix_);
}

} // namespace rag_ingester
