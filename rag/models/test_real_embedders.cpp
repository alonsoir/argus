/*
 * ML Defender - C++ Embedder Test (Day 34)
 *
 * Tests ONNX embedder models with dummy 83-feature input.
 * Validates C++ inference pipeline with ONNX Runtime.
 */

#include <iostream>
#include <vector>
#include <iomanip>
#include <stdexcept>
#include <onnxruntime_cxx_api.h>

// Test one embedder with 83 features
void test_embedder(const char* model_path, const char* name, size_t expected_dim) {
    std::cout << "\n" << std::string(60, '=') << "\n";
    std::cout << "Testing: " << name << "\n";
    std::cout << std::string(60, '=') << "\n";

    // Initialize ONNX Runtime
    Ort::Env env(ORT_LOGGING_LEVEL_WARNING, "ml-defender");
    Ort::SessionOptions session_options;

    // Load model
    std::cout << "Step 1: Loading model...\n";
    Ort::Session session(env, model_path, session_options);
    std::cout << "  ✅ Model loaded: " << model_path << "\n";

    // Prepare 83 features (dummy values for now)
    std::vector<float> input_data(83, 0.5f);  // All 0.5 as placeholder

    // Add some variance to make it more realistic
    for (size_t i = 0; i < 83; ++i) {
        input_data[i] = 0.5f + (i % 10) * 0.05f;  // Values from 0.5 to 0.95
    }

    // Create input tensor
    auto memory_info = Ort::MemoryInfo::CreateCpu(OrtArenaAllocator, OrtMemTypeDefault);
    std::vector<int64_t> input_shape = {1, 83};

    Ort::Value input_tensor = Ort::Value::CreateTensor<float>(
        memory_info,
        input_data.data(),
        input_data.size(),
        input_shape.data(),
        input_shape.size()
    );

    // Run inference
    std::cout << "\nStep 2: Running inference...\n";
    const char* input_names[] = {"features"};
    const char* output_names[] = {"embedding"};

    auto output_tensors = session.Run(
        Ort::RunOptions{nullptr},
        input_names, &input_tensor, 1,
        output_names, 1
    );

    // Validate output
    float* output_data = output_tensors[0].GetTensorMutableData<float>();
    auto output_shape = output_tensors[0].GetTensorTypeAndShapeInfo().GetShape();

    std::cout << "  ✅ Inference completed\n";
    std::cout << "  Input shape: [" << input_shape[0] << ", " << input_shape[1] << "]\n";
    std::cout << "  Output shape: [" << output_shape[0] << ", " << output_shape[1] << "]\n";
    std::cout << "  Expected dim: " << expected_dim << "\n";

    // Check dimension
    if (static_cast<size_t>(output_shape[1]) == expected_dim) {
        std::cout << "  ✅ Dimension correct\n";
    } else {
        std::cout << "  ❌ Dimension mismatch!\n";
        throw std::runtime_error("Dimension mismatch");
    }

    // Calculate statistics
    float min_val = output_data[0];
    float max_val = output_data[0];
    float sum = 0.0f;

    for (size_t i = 0; i < expected_dim; ++i) {
        float val = output_data[i];
        min_val = std::min(min_val, val);
        max_val = std::max(max_val, val);
        sum += val;
    }

    float mean = sum / expected_dim;

    // Calculate std dev
    float variance = 0.0f;
    for (size_t i = 0; i < expected_dim; ++i) {
        float diff = output_data[i] - mean;
        variance += diff * diff;
    }
    float std_dev = std::sqrt(variance / expected_dim);

    std::cout << "\nStep 3: Statistics...\n";
    std::cout << "  Value range: [" << std::fixed << std::setprecision(4)
              << min_val << ", " << max_val << "]\n";
    std::cout << "  Mean: " << mean << ", Std: " << std_dev << "\n";

    // Show first few values
    std::cout << "  First 5 values: ";
    for (size_t i = 0; i < 5 && i < expected_dim; ++i) {
        std::cout << std::fixed << std::setprecision(4) << output_data[i] << " ";
    }
    std::cout << "\n";
}

int main() {
    std::cout << "╔════════════════════════════════════════════════════════╗\n";
    std::cout << "║  ML Defender - C++ Embedder Test                      ║\n";
    std::cout << "╚════════════════════════════════════════════════════════╝\n";

    try {
        test_embedder("chronos_embedder.onnx", "Chronos (Time Series)", 512);
        test_embedder("sbert_embedder.onnx", "SBERT (Semantic)", 384);
        test_embedder("attack_embedder.onnx", "Attack (Patterns)", 256);

        std::cout << "\n╔════════════════════════════════════════════════════════╗\n";
        std::cout << "║  ALL TESTS PASSED ✅                                   ║\n";
        std::cout << "╚════════════════════════════════════════════════════════╝\n";

        return 0;
    } catch (const std::exception& e) {
        std::cerr << "\n❌ TEST FAILED: " << e.what() << "\n";
        return 1;
    }
}