#pragma once

#include <string>
#include <vector>
#include <memory>
#include <onnxruntime_cxx_api.h>
#include <spdlog/spdlog.h>

namespace ml_detector {

    class ONNXModel {
    public:
        explicit ONNXModel(const std::string& model_path, int num_threads = 0);
        ~ONNXModel() = default;

        std::pair<int64_t, float> predict(const std::vector<float>& features);

        size_t get_num_features() const { return num_features_; }
        bool is_loaded() const { return session_ != nullptr; }
        const std::string& get_input_name() const { return input_name_; }
        const std::vector<std::string>& get_output_names() const { return output_names_; }

    private:
        static Ort::Env env_;
        std::unique_ptr<Ort::Session> session_;
        Ort::MemoryInfo memory_info_;
        std::string input_name_;
        std::vector<std::string> output_names_;
        size_t num_features_;
        Ort::SessionOptions session_options_;
        std::shared_ptr<spdlog::logger> logger_;

        void initialize_metadata();
    };

} // namespace ml_detector