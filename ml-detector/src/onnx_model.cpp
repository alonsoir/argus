#include "onnx_model.hpp"
#include <spdlog/sinks/stdout_color_sinks.h>
#include <stdexcept>
#include <algorithm>

namespace ml_detector {

Ort::Env ONNXModel::env_(ORT_LOGGING_LEVEL_WARNING, "ml-detector");

ONNXModel::ONNXModel(const std::string& model_path, int num_threads)
    : memory_info_(Ort::MemoryInfo::CreateCpu(OrtArenaAllocator, OrtMemTypeDefault))
    , logger_(spdlog::get("ml-detector"))
{
    if (!logger_) {
        logger_ = spdlog::stdout_color_mt("ml-detector");
    }
    
    logger_->info("Loading ONNX model: {}", model_path);
    
    try {
        session_options_.SetIntraOpNumThreads(num_threads > 0 ? num_threads : 1);
        session_options_.SetGraphOptimizationLevel(GraphOptimizationLevel::ORT_ENABLE_ALL);
        
        session_ = std::make_unique<Ort::Session>(env_, model_path.c_str(), session_options_);
        
        initialize_metadata();
        
        logger_->info("✅ ONNX model loaded successfully");
        logger_->info("   Input: {} (features: {})", input_name_, num_features_);
        logger_->info("   Outputs: {} nodes", output_names_.size());
        
    } catch (const Ort::Exception& e) {
        logger_->error("Failed to load ONNX model: {}", e.what());
        throw std::runtime_error("ONNX model loading failed: " + std::string(e.what()));
    }
}

void ONNXModel::initialize_metadata() {
    if (!session_) {
        throw std::runtime_error("Session not initialized");
    }
    
    Ort::AllocatorWithDefaultOptions allocator;
    
    size_t num_inputs = session_->GetInputCount();
    if (num_inputs != 1) {
        throw std::runtime_error("Model must have exactly 1 input, got " + std::to_string(num_inputs));
    }
    
    auto input_name_ptr = session_->GetInputNameAllocated(0, allocator);
    input_name_ = input_name_ptr.get();
    
    auto type_info = session_->GetInputTypeInfo(0);
    auto tensor_info = type_info.GetTensorTypeAndShapeInfo();
    auto shape = tensor_info.GetShape();
    
    if (shape.size() != 2) {
        throw std::runtime_error("Input shape must be 2D, got " + std::to_string(shape.size()));
    }
    
    num_features_ = static_cast<size_t>(shape[1]);
    
    size_t num_outputs = session_->GetOutputCount();
    output_names_.reserve(num_outputs);
    
    for (size_t i = 0; i < num_outputs; ++i) {
        auto output_name_ptr = session_->GetOutputNameAllocated(i, allocator);
        output_names_.emplace_back(output_name_ptr.get());
    }
}

std::pair<int64_t, float> ONNXModel::predict(const std::vector<float>& features) {
    if (!session_) {
        throw std::runtime_error("Model not loaded");
    }
    
    if (features.size() != num_features_) {
        throw std::invalid_argument(
            "Feature size mismatch. Expected: " + std::to_string(num_features_) + 
            ", got: " + std::to_string(features.size())
        );
    }
    
    try {
        std::vector<float> input_data = features;
        std::vector<int64_t> input_shape = {1, static_cast<int64_t>(num_features_)};
        
        auto input_tensor = Ort::Value::CreateTensor<float>(
            memory_info_,
            input_data.data(),
            input_data.size(),
            input_shape.data(),
            input_shape.size()
        );
        
        const char* input_names[] = {input_name_.c_str()};
        std::vector<const char*> output_names_cstr;
        output_names_cstr.reserve(output_names_.size());
        for (const auto& name : output_names_) {
            output_names_cstr.push_back(name.c_str());
        }
        
        auto output_tensors = session_->Run(
            Ort::RunOptions{nullptr},
            input_names,
            &input_tensor,
            1,
            output_names_cstr.data(),
            output_names_cstr.size()
        );
        
        if (output_tensors.size() < 2) {
            throw std::runtime_error("Expected 2 outputs, got " + std::to_string(output_tensors.size()));
        }
        
        int64_t* label_data = output_tensors[0].GetTensorMutableData<int64_t>();
        int64_t label = label_data[0];
        
        float* proba_data = output_tensors[1].GetTensorMutableData<float>();
        float confidence = (label == 0) ? proba_data[0] : proba_data[1];
        
        return {label, confidence};
        
    } catch (const Ort::Exception& e) {
        logger_->error("ONNX inference failed: {}", e.what());
        throw std::runtime_error("Inference failed: " + std::string(e.what()));
    }
}

} // namespace ml_detector