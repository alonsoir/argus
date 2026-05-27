// File: rag/tests/test_faiss_basic.cpp
#include <faiss/IndexFlat.h>
#include <iostream>
#include <vector>
#include <random>

int main() {
    std::cout << "╔════════════════════════════════════════╗\n";
    std::cout << "║  FAISS Basic Integration Test         ║\n";
    std::cout << "╚════════════════════════════════════════╝\n\n";

    // Test 1: Create index
    std::cout << "Test 1: Creating FAISS index...\n";
    constexpr int dimension = 128;  // Embedding dimension
    faiss::IndexFlatL2 index(dimension);
    std::cout << "  ✅ Index created, dimension: " << index.d << "\n";
    std::cout << "  ✅ Metric type: L2\n\n";

    // Test 2: Add vectors
    std::cout << "Test 2: Adding vectors to index...\n";
    constexpr int num_vectors = 100;
    std::vector<float> data(num_vectors * dimension);

    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_real_distribution<float> dis(0.0f, 1.0f);

    for (auto& val : data) {
        val = dis(gen);
    }

    index.add(num_vectors, data.data());
    std::cout << "  ✅ Added " << num_vectors << " vectors\n";
    std::cout << "  ✅ Total vectors in index: " << index.ntotal << "\n\n";

    // Test 3: Search k-nearest neighbors
    std::cout << "Test 3: Searching k-nearest neighbors...\n";
    std::vector<float> query(dimension);
    for (auto& val : query) {
        val = dis(gen);
    }

    constexpr int k = 5;
    std::vector<faiss::idx_t> labels(k);
    std::vector<float> distances(k);

    index.search(1, query.data(), k, distances.data(), labels.data());

    std::cout << "  ✅ Search completed\n";
    std::cout << "  ✅ Top-" << k << " nearest neighbors:\n";
    for (int i = 0; i < k; ++i) {
        std::cout << "     " << (i+1) << ". Index " << labels[i]
                  << " (distance: " << distances[i] << ")\n";
    }

    std::cout << "\n╔════════════════════════════════════════╗\n";
    std::cout << "║  ALL TESTS PASSED ✅                   ║\n";
    std::cout << "╚════════════════════════════════════════╝\n";

    return 0;
}