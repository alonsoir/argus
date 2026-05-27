#pragma once

#include <vector>
#include <string>

namespace rag_ingester {

struct Event;

// Simple feature projection embedder (no ONNX)
// Uses random projection to preserve semantic distances
class SimpleEmbedder {
public:
    static constexpr size_t INPUT_DIM = 105;   // 101 core + 4 embedded (features already complete)
    static constexpr size_t CHRONOS_DIM = 128; // Match FAISS index
    static constexpr size_t SBERT_DIM = 96;    // Match FAISS index  
    static constexpr size_t ATTACK_DIM = 64;   // Match FAISS index
    
    SimpleEmbedder();
    ~SimpleEmbedder() = default;
    
    // Generate embeddings for each index type
    std::vector<float> embed_chronos(const Event& event);
    std::vector<float> embed_sbert(const Event& event);
    std::vector<float> embed_attack(const Event& event);
    
private:
    // Build input vector from event (105-d)
    std::vector<float> build_input(const Event& event);
    
    // Random projection matrices (fixed seed for determinism)
    std::vector<std::vector<float>> chronos_matrix_;  // 105×128
    std::vector<std::vector<float>> sbert_matrix_;    // 105×96
    std::vector<std::vector<float>> attack_matrix_;   // 105×64
    
    void init_projection_matrix(
        std::vector<std::vector<float>>& matrix,
        size_t input_dim,
        size_t output_dim,
        int seed
    );
    
    std::vector<float> project(
        const std::vector<float>& input,
        const std::vector<std::vector<float>>& matrix
    );
};

} // namespace rag_ingester
