#include "dimensionality_reducer.hpp"
#include <iostream>
#include <random>
#include <vector>
#include <chrono>
#include <iomanip>

using namespace ml_defender::rag;

void generate_synthetic_data(std::vector<float>& data, size_t n_samples, int dim) {
    std::mt19937 gen(42);  // Fixed seed for reproducibility
    std::normal_distribution<float> dist(0.0f, 1.0f);

    data.resize(n_samples * dim);
    for (auto& val : data) {
        val = dist(gen);
    }
}

int main() {
    std::cout << "=== DimensionalityReducer Test ===\n\n";

    const int INPUT_DIM = 384;   // all-MiniLM-L6-v2 dimension
    const int OUTPUT_DIM = 128;  // Target reduced dimension
    const size_t N_TRAIN = 10000; // Training samples
    const size_t N_TEST = 100;    // Test samples

    try {
        // Step 1: Create reducer
        std::cout << "[1] Creating DimensionalityReducer ("
                  << INPUT_DIM << " → " << OUTPUT_DIM << ")...\n";
        DimensionalityReducer reducer(INPUT_DIM, OUTPUT_DIM);

        // Step 2: Generate synthetic training data
        std::cout << "[2] Generating " << N_TRAIN << " synthetic training samples...\n";
        std::vector<float> training_data;
        generate_synthetic_data(training_data, N_TRAIN, INPUT_DIM);

        // Step 3: Train PCA
        std::cout << "[3] Training PCA model...\n";
        auto start = std::chrono::high_resolution_clock::now();
        float variance = reducer.train(training_data.data(), N_TRAIN);
        auto end = std::chrono::high_resolution_clock::now();
        auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(end - start);

        std::cout << "    Training time: " << duration.count() << " ms\n";
        std::cout << "    Variance retained: " << std::fixed << std::setprecision(2)
                  << (variance * 100.0f) << "%\n";

        if (variance < 0.96f) {
            std::cout << "    ⚠️  WARNING: Variance below 96% target!\n";
        } else {
            std::cout << "    ✅ Variance meets 96% target\n";
        }

        // Step 4: Test single transform
        std::cout << "\n[4] Testing single vector transform...\n";
        std::vector<float> test_input(INPUT_DIM);
        std::vector<float> test_output(OUTPUT_DIM);
        generate_synthetic_data(test_input, 1, INPUT_DIM);

        start = std::chrono::high_resolution_clock::now();
        reducer.transform(test_input.data(), test_output.data());
        end = std::chrono::high_resolution_clock::now();
        auto transform_time = std::chrono::duration_cast<std::chrono::microseconds>(end - start);

        std::cout << "    Transform time: " << transform_time.count() << " μs\n";
        std::cout << "    Output sample: [" << test_output[0] << ", " << test_output[1]
                  << ", ..., " << test_output[OUTPUT_DIM-1] << "]\n";

        // Step 5: Test batch transform
        std::cout << "\n[5] Testing batch transform (" << N_TEST << " vectors)...\n";
        std::vector<float> batch_input;
        std::vector<float> batch_output(N_TEST * OUTPUT_DIM);
        generate_synthetic_data(batch_input, N_TEST, INPUT_DIM);

        start = std::chrono::high_resolution_clock::now();
        reducer.transform_batch(batch_input.data(), batch_output.data(), N_TEST);
        end = std::chrono::high_resolution_clock::now();
        auto batch_time = std::chrono::duration_cast<std::chrono::milliseconds>(end - start);

        std::cout << "    Batch transform time: " << batch_time.count() << " ms\n";
        std::cout << "    Throughput: " << (N_TEST * 1000.0 / batch_time.count())
                  << " vectors/sec\n";

        // Step 6: Save model
        std::cout << "\n[6] Saving model to /tmp/test_pca_model.faiss...\n";
        reducer.save("/tmp/test_pca_model.faiss");

        // Step 7: Load model and verify
        std::cout << "[7] Loading model and verifying...\n";
        DimensionalityReducer reducer2(INPUT_DIM, OUTPUT_DIM);
        reducer2.load("/tmp/test_pca_model.faiss");

        std::vector<float> verify_output(OUTPUT_DIM);
        reducer2.transform(test_input.data(), verify_output.data());

        // Check if outputs match
        bool match = true;
        for (int i = 0; i < OUTPUT_DIM; ++i) {
            if (std::abs(test_output[i] - verify_output[i]) > 1e-5) {
                match = false;
                break;
            }
        }

        if (match) {
            std::cout << "    ✅ Save/Load verification PASSED\n";
        } else {
            std::cout << "    ❌ Save/Load verification FAILED\n";
            return 1;
        }

        std::cout << "\n=== All Tests PASSED ===\n";
        return 0;

    } catch (const std::exception& e) {
        std::cerr << "\n❌ ERROR: " << e.what() << "\n";
        return 1;
    }
}