// train_pca_pipeline.cpp
// Pipeline completo de entrenamiento PCA sobre embeddings ONNX

#include <iostream>
#include <fstream>
#include <vector>
#include <string>
#include <spdlog/spdlog.h>
#include <onnxruntime_cxx_api.h>
#include "dimensionality_reducer.hpp"  // Tu biblioteca del proyecto

constexpr int64_t BATCH_SIZE = 1000;
constexpr float TARGET_VARIANCE = 0.96f;

struct Embedder {
    Ort::Session* session;
    std::vector<int64_t> input_shape{1, 83};
    std::string input_name;
    std::string output_name;
    int output_dim;
};

bool load_features(const std::string& path, std::vector<std::array<float, 83>>& features) {
    std::ifstream in(path, std::ios::binary);
    if (!in) {
        spdlog::error("No se pudo abrir {}", path);
        return false;
    }
    in.seekg(0, std::ios::end);
    size_t bytes = in.tellg();
    size_t expected = sizeof(std::array<float, 83>);
    size_t num_samples = bytes / expected;
    in.seekg(0, std::ios::beg);

    features.resize(num_samples);
    in.read(reinterpret_cast<char*>(features.data()), bytes);
    spdlog::info("Cargadas {} muestras de features", num_samples);
    return true;
}

std::vector<float> run_embedder(const Embedder& embedder, const float* input_batch, size_t batch_size) {
    std::vector<int64_t> input_shape{batch_size, 83};
    auto memory_info = Ort::MemoryInfo::CreateCpu(OrtDeviceAllocator, OrtMemTypeCPU);

    Ort::Value input_tensor = Ort::Value::CreateTensor<float>(
        memory_info, const_cast<float*>(input_batch), batch_size * 83, input_shape.data(), input_shape.size());

    const char* input_names[] = {embedder.input_name.c_str()};
    const char* output_names[] = {embedder.output_name.c_str()};

    auto output_tensors = embedder.session->Run(Ort::RunOptions{nullptr},
                                                input_names, &input_tensor, 1,
                                                output_names, 1);

    float* output_data = output_tensors[0].GetTensorMutableData<float>();
    return std::vector<float>(output_data, output_data + batch_size * embedder.output_dim);
}

int main(int argc, char* argv[]) {
    std::string features_path = "/shared/data/synthetic_features.bin";
    std::string output_dir = "/shared/models/pca/";
    std::string suffix = "_v1_synthetic";
    float target_variance = TARGET_VARIANCE;

    // Parseo argumentos
    for (int i = 1; i < argc; ++i) {
        std::string arg(argv[i]);
        if (arg == "--features" && i+1 < argc) features_path = argv[++i];
        if (arg == "--output-dir" && i+1 < argc) output_dir = argv[++i];
        if (arg == "--suffix" && i+1 < argc) suffix = argv[++i];
        if (arg == "--target-variance" && i+1 < argc) target_variance = std::stof(argv[++i]);
    }

    Ort::Env env{ORT_LOGGING_LEVEL_WARNING, "PCA_Pipeline"};
    Ort::SessionOptions session_options;
    session_options.SetIntraOpNumThreads(1);

    // Cargar los 3 embedders ONNX
    std::vector<Embedder> embedders(3);
    const std::vector<std::string> model_paths = {
        "/vagrant/rag/models/chronos_embedder.onnx",
        "/vagrant/rag/models/sbert_embedder.onnx",
        "/vagrant/rag/models/attack_embedder.onnx"
    };
    const std::vector<int> output_dims = {512, 384, 256};

    for (int i = 0; i < 3; ++i) {
        embedders[i].session = new Ort::Session(env, model_paths[i].c_str(), session_options);
        embedders[i].input_name = embedders[i].session->GetInputNameAllocated(0, Ort::AllocatorWithDefaultOptions()).get();
        embedders[i].output_name = embedders[i].session->GetOutputNameAllocated(0, Ort::AllocatorWithDefaultOptions()).get();
        embedders[i].output_dim = output_dims[i];
    }

    // Cargar features
    std::vector<std::array<float, 83>> features;
    if (!load_features(features_path, features)) return 1;

    // Procesar en batches y entrenar PCA para cada embedder
    for (int e = 0; e < 3; ++e) {
        const auto& embedder = embedders[e];
        DimensionalityReducer pca_reducer(embedder.output_dim, 128);

        size_t total = features.size();
        for (size_t start = 0; start < total; start += BATCH_SIZE) {
            size_t current_batch = std::min(BATCH_SIZE, total - start);
            const float* batch_input = reinterpret_cast<const float*>(features.data() + start);

            auto embeddings = run_embedder(embedder, batch_input, current_batch);
            pca_reducer.partial_fit(embeddings.data(), current_batch);
        }

        pca_reducer.finalize(target_variance);
        float achieved = pca_reducer.get_explained_variance();

        std::string model_name = output_dir +
            (e == 0 ? "pca_chronos" : e == 1 ? "pca_sbert" : "pca_attack") + suffix + ".bin";

        pca_reducer.save(model_name);
        spdlog::info("PCA {} entrenado: {} → {} dims, variance explicada: {:.1f}% → guardado en {}",
                     e==0?"chronos":e==1?"sbert":"attack", embedder.output_dim, pca_reducer.get_output_dim(),
                     achieved * 100.0f, model_name);
    }

    spdlog::info("Pipeline PCA completado con éxito");
    return 0;
}