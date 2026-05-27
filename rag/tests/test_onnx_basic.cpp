/**
 * @file test_onnx_basic.cpp
 * @brief Basic test for ONNX Runtime C++ API integration
 * 
 * Tests:
 *   1. ONNX Runtime initialization
 *   2. Model loading (dummy_embedder.onnx)
 *   3. Inference execution
 *   4. Output validation
 * 
 * Via Appia Quality: Test infrastructure before real models
 */

#include <onnxruntime_cxx_api.h>
#include <iostream>
#include <vector>
#include <random>
#include <cmath>
#include <cassert>

void print_header() {
    std::cout << "╔════════════════════════════════════════╗\n";
    std::cout << "║  ONNX Runtime Basic Test              ║\n";
    std::cout << "╚════════════════════════════════════════╝\n\n";
}

void print_success() {
    std::cout << "\n╔════════════════════════════════════════╗\n";
    std::cout << "║  ALL TESTS PASSED ✅                   ║\n";
    std::cout << "╚════════════════════════════════════════╝\n";
}

int main() {
    print_header();
    
    try {
        // Test 1: Initialize ONNX Runtime
        std::cout << "Test 1: Initializing ONNX Runtime...\n";
        Ort::Env env(ORT_LOGGING_LEVEL_WARNING, "test_onnx_basic");
        Ort::SessionOptions session_options;
        session_options.SetIntraOpNumThreads(1);
        session_options.SetGraphOptimizationLevel(GraphOptimizationLevel::ORT_ENABLE_BASIC);
        std::cout << "  ✅ ONNX Runtime initialized\n";
        std::cout << "  ✅ Session options configured\n\n";
        
        // Test 2: Load model
        std::cout << "Test 2: Loading ONNX model...\n";
        const char* model_path = "dummy_embedder.onnx";
        Ort::Session session(env, model_path, session_options);
        std::cout << "  ✅ Model loaded: " << model_path << "\n";
        
        // Get input/output names
        Ort::AllocatorWithDefaultOptions allocator;
        
        size_t num_input_nodes = session.GetInputCount();
        size_t num_output_nodes = session.GetOutputCount();
        
        auto input_name_ptr = session.GetInputNameAllocated(0, allocator);
        auto output_name_ptr = session.GetOutputNameAllocated(0, allocator);
        
        std::cout << "  ✅ Input nodes: " << num_input_nodes << "\n";
        std::cout << "  ✅ Output nodes: " << num_output_nodes << "\n";
        std::cout << "  ✅ Input name: " << input_name_ptr.get() << "\n";
        std::cout << "  ✅ Output name: " << output_name_ptr.get() << "\n\n";
        
        // Test 3: Prepare input data
        std::cout << "Test 3: Preparing input tensor...\n";
        
        constexpr size_t input_size = 10;
        constexpr size_t batch_size = 1;
        
        std::vector<float> input_data(batch_size * input_size);
        
        // Fill with random data
        std::random_device rd;
        std::mt19937 gen(rd());
        std::uniform_real_distribution<float> dis(-1.0f, 1.0f);
        
        for (auto& val : input_data) {
            val = dis(gen);
        }
        
        std::cout << "  ✅ Input data generated (" << input_data.size() << " values)\n";
        std::cout << "  ✅ First 5 values: ";
        for (size_t i = 0; i < 5; ++i) {
            std::cout << input_data[i] << " ";
        }
        std::cout << "\n\n";
        
        // Create input tensor
        std::vector<int64_t> input_shape = {static_cast<int64_t>(batch_size), 
                                            static_cast<int64_t>(input_size)};
        
        auto memory_info = Ort::MemoryInfo::CreateCpu(
            OrtArenaAllocator, OrtMemTypeDefault
        );
        
        Ort::Value input_tensor = Ort::Value::CreateTensor<float>(
            memory_info,
            input_data.data(),
            input_data.size(),
            input_shape.data(),
            input_shape.size()
        );
        
        assert(input_tensor.IsTensor());
        std::cout << "  ✅ Input tensor created\n";
        std::cout << "  ✅ Tensor shape: [" << input_shape[0] << ", " 
                  << input_shape[1] << "]\n\n";
        
        // Test 4: Run inference
        std::cout << "Test 4: Running inference...\n";
        
        const char* input_names[] = {input_name_ptr.get()};
        const char* output_names[] = {output_name_ptr.get()};
        
        auto output_tensors = session.Run(
            Ort::RunOptions{nullptr},
            input_names,
            &input_tensor,
            1,
            output_names,
            1
        );
        
        std::cout << "  ✅ Inference completed successfully\n";
        
        assert(output_tensors.size() == 1);
        assert(output_tensors.front().IsTensor());
        
        // Test 5: Validate output
        std::cout << "\nTest 5: Validating output...\n";
        
        float* output_data = output_tensors.front().GetTensorMutableData<float>();
        auto type_info = output_tensors.front().GetTensorTypeAndShapeInfo();
        auto output_shape = type_info.GetShape();
        size_t output_count = type_info.GetElementCount();
        
        std::cout << "  ✅ Output shape: [";
        for (size_t i = 0; i < output_shape.size(); ++i) {
            std::cout << output_shape[i];
            if (i < output_shape.size() - 1) std::cout << ", ";
        }
        std::cout << "]\n";
        
        std::cout << "  ✅ Output elements: " << output_count << "\n";
        
        // Verify expected dimensions
        assert(output_shape.size() == 2 && "Output should be 2D");
        assert(output_shape[0] == batch_size && "Batch size mismatch");
        assert(output_shape[1] == 32 && "Output dimension should be 32");
        
        std::cout << "  ✅ Dimensions correct (batch=1, dim=32)\n";
        
        // Verify output values are in valid range (Tanh: [-1, 1])
        bool all_valid = true;
        for (size_t i = 0; i < output_count; ++i) {
            if (std::isnan(output_data[i]) || std::isinf(output_data[i])) {
                all_valid = false;
                break;
            }
            if (output_data[i] < -1.0f || output_data[i] > 1.0f) {
                // Allow small numerical errors
                if (std::abs(output_data[i]) > 1.01f) {
                    all_valid = false;
                    break;
                }
            }
        }
        
        assert(all_valid && "Output contains invalid values");
        std::cout << "  ✅ All output values valid (in Tanh range)\n";
        
        // Print first few output values
        std::cout << "  ✅ First 5 output values: ";
        for (size_t i = 0; i < 5 && i < output_count; ++i) {
            std::cout << output_data[i] << " ";
        }
        std::cout << "\n";
        
        print_success();
        return 0;
        
    } catch (const Ort::Exception& e) {
        std::cerr << "\n❌ ONNX Runtime Error: " << e.what() << "\n";
        std::cerr << "Error code: " << e.GetOrtErrorCode() << "\n";
        return 1;
    } catch (const std::exception& e) {
        std::cerr << "\n❌ Standard Error: " << e.what() << "\n";
        return 1;
    }
}
