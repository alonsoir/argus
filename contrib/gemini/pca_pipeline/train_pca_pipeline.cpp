/**
 * @file train_pca_pipeline.cpp
 * @brief Orchestrates PCA training for Chronos, SBERT, and Attack embedders.
 * @quality Via Appia - C++20, Thread-safe, Error-handled.
 */

#include "dimensionality_reducer.hpp"
#include <iostream>
#include <vector>
#include <fstream>
#include <memory>

int main() {
    const int input_dims[] = {512, 384, 256}; // Chronos, SBERT, Attack
    const int target_dim = 128;
    const size_t num_samples = 20000;
    const std::string data_path = "synthetic_features.bin";

    std::cout << "🏛️ Starting PCA Training Pipeline (Plan A - Synthetic)" << std::endl;

    // 1. Carga de datos base
    std::vector<float> raw_data(num_samples * 83);
    std::ifstream in(data_path, std::ios::binary);
    if (!in) {
        std::cerr << "❌ Missing synthetic data. Run generator first." << std::endl;
        return 1;
    }
    in.read(reinterpret_cast<char*>(raw_data.data()), raw_data.size() * sizeof(float));

    // 2. Simulación de ONNX Embeddings + Entrenamiento PCA
    // Nota: En Plan A' aquí llamaríamos a los modelos ONNX reales.
    // Para el test de arquitectura, simulamos la salida del embedder.

    auto train_model = [&](const std::string& name, int in_dim) {
        std::cout << "\n--- Training Reducer: " << name << " (" << in_dim << " -> " << target_dim << ") ---" << std::endl;

        // Simulamos salida de ONNX: num_samples x in_dim
        std::vector<float> simulated_embeddings(num_samples * in_dim, 0.5f);

        auto reducer = std::make_unique<ml_defender::DimensionalityReducer>(in_dim, target_dim);

        if (reducer->train(simulated_embeddings)) {
            std::string model_file = "pca_" + name + ".faiss";
            if (reducer->save(model_file)) {
                std::cout << "✅ Model saved: " << model_file << std::endl;
            }
        } else {
            std::cerr << "❌ Training failed for " << name << std::endl;
        }
    };

    train_model("chronos", 512);
    train_model("sbert", 384);
    train_model("attack", 256);

    std::cout << "\n🏁 Pipeline execution complete." << std::endl;
    return 0;
}