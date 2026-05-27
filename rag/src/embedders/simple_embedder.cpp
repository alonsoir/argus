// /vagrant/rag/src/embedders/simple_embedder.cpp

#include "embedders/simple_embedder.hpp"
#include <cmath>
#include <stdexcept>
#include <random>

namespace rag {

SimpleEmbedder::SimpleEmbedder() {
    // Inicializar matrices de proyección aleatoria
    initialize_random_matrix(chronos_matrix_, CHRONOS_DIM);
    initialize_random_matrix(sbert_matrix_, SBERT_DIM);
    initialize_random_matrix(attack_matrix_, ATTACK_DIM);
}

std::vector<float> SimpleEmbedder::embed_chronos(
    const std::vector<float>& features
) {
    if (features.size() != INPUT_DIM) {
        throw std::runtime_error(
            "SimpleEmbedder: Invalid input size " +
            std::to_string(features.size()) +
            " (expected " + std::to_string(INPUT_DIM) + ")"
        );
    }

    return project(features, chronos_matrix_);
}

std::vector<float> SimpleEmbedder::embed_sbert(
    const std::vector<float>& features
) {
    if (features.size() != INPUT_DIM) {
        throw std::runtime_error(
            "SimpleEmbedder: Invalid input size " +
            std::to_string(features.size())
        );
    }

    return project(features, sbert_matrix_);
}

std::vector<float> SimpleEmbedder::embed_attack(
    const std::vector<float>& features
) {
    if (features.size() != INPUT_DIM) {
        throw std::runtime_error(
            "SimpleEmbedder: Invalid input size " +
            std::to_string(features.size())
        );
    }

    return project(features, attack_matrix_);
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

    // L2 normalize
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

void SimpleEmbedder::initialize_random_matrix(
    std::vector<std::vector<float>>& matrix,
    size_t output_dim
) {
    std::random_device rd;
    std::mt19937 gen(rd());
    std::normal_distribution<float> dist(0.0f, 1.0f / std::sqrt(output_dim));

    matrix.resize(INPUT_DIM);
    for (size_t i = 0; i < INPUT_DIM; ++i) {
        matrix[i].resize(output_dim);
        for (size_t j = 0; j < output_dim; ++j) {
            matrix[i][j] = dist(gen);
        }
    }
}

} // namespace rag