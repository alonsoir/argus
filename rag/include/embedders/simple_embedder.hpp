// /vagrant/rag/include/embedders/simple_embedder.hpp
#pragma once

#include "embedder_interface.hpp"
#include <random>

namespace rag {

    /**
     * @brief Random projection embedder (baseline)
     *
     * NOTA: Versión simplificada sin NetworkEvent
     * Acepta vector<float> directamente
     */
    class SimpleEmbedder : public IEmbedder {
    public:
        static constexpr size_t INPUT_DIM = 105;
        static constexpr size_t CHRONOS_DIM = 128;
        static constexpr size_t SBERT_DIM = 96;
        static constexpr size_t ATTACK_DIM = 64;

        SimpleEmbedder();

        // IEmbedder interface (versión simplificada)
        std::vector<float> embed_chronos(
            const std::vector<float>& features
        ) override;

        std::vector<float> embed_sbert(
            const std::vector<float>& features
        ) override;

        std::vector<float> embed_attack(
            const std::vector<float>& features
        ) override;

        std::string name() const override {
            return "SimpleEmbedder (Random Projection)";
        }

        std::tuple<size_t, size_t, size_t> dimensions() const override {
            return {CHRONOS_DIM, SBERT_DIM, ATTACK_DIM};
        }

        int effectiveness_percent() const override {
            return 67;  // 60-75% range
        }

        std::string capabilities() const override {
            return "Feature-based similarity (random projection)";
        }

    private:
        std::vector<float> project(
            const std::vector<float>& input,
            const std::vector<std::vector<float>>& matrix
        );

        void initialize_random_matrix(
            std::vector<std::vector<float>>& matrix,
            size_t output_dim
        );

        // Matrices de proyección
        std::vector<std::vector<float>> chronos_matrix_;  // 105×128
        std::vector<std::vector<float>> sbert_matrix_;    // 105×96
        std::vector<std::vector<float>> attack_matrix_;   // 105×64
    };

} // namespace rag