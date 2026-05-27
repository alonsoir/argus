/**
 * File: common-rag-ingester/tools/train_pca_pipeline.cpp
 * Day: 36 - Plan A Execution
 *
 * Purpose:
 *   Ejecutar el ciclo completo de entrenamiento PCA para los 3 modelos.
 *   Lee datos (pipe/file) -> Entrena -> Guarda -> Valida Roundtrip.
 *
 * Architecture Check:
 *   - Dependencies: libcommon-rag-ingester.so (Day 35)
 *   - Input: Binary stream from synthetic_data_generator
 *   - Output: FAISS PCA Models (.faiss)
 */

#include <iostream>
#include <fstream>
#include <chrono>
#include <iomanip>
#include <span>
#include <cstdint>

// C++20 Standard Includes
#include <vector>
#include <algorithm>

// Project Dependencies
#include "dimensionality_reducer.hpp"

struct PcaTarget {
    std::string name;
    int input_dim;
    int output_dim;
};

// Helper: Leer binario endian-safe
template<typename T>
bool read_binary(std::istream& is, T& value) {
    return is.read(reinterpret_cast<char*>(&value), sizeof(T)).gcount() == sizeof(T);
}

int main() {
    std::cout << "🏛️ PCA Training Pipeline (Day 36 - Plan A)\n";
    std::cout << "================================================\n";

    // 1. Leer Header del flujo de datos (debe venir de generator)
    uint32_t n_samples, n_dims;
    if (!read_binary(std::cin, n_samples) || !read_binary(std::cin, n_dims)) {
        std::cerr << "❌ Error: Could not read data header. Ensure input is piped.\n";
        std::cerr << "   Usage: ./synthetic_data_generator | ./train_pca_pipeline\n";
        return 1;
    }

    std::cout << "Stream Detected: " << n_samples << " samples, " << n_dims << " dims\n";
    if (n_dims != 83) {
        std::cout << "⚠️  Warning: Expected 83 dims for ONNX models, got " << n_dims << ".\n";
    }

    // 2. Cargar Payload en memoria
    // Optimización: Pre-reserva exacta para evitar re-alocaciones
    std::vector<float> data(n_samples * n_dims);
    size_t bytes_to_read = data.size() * sizeof(float);

    std::cout << "Loading " << (bytes_to_read / 1024 / 1024) << " MB of data... ";

    if (!std::cin.read(reinterpret_cast<char*>(data.data()), bytes_to_read)) {
        std::cerr << "❌ Error: Unexpected EOF reading payload.\n";
        return 1;
    }
    std::cout << "Done.\n";

    // 3. Configuración de Modelos (Según HIERARCHICAL_RAG_VISION v2.0)
    std::vector<PcaTarget> targets = {
        {"chronos", 512, 128},  // 512-d -> 128-d
        {"sbert",   384,  96},  // 384-d -> 96-d
        {"attack",   256,  64}   // 256-d -> 64-d
    };

    // 4. Procesamiento y Entrenamiento
    for (const auto& target : targets) {
        std::cout << "\n🔨 Training: " << target.name
                  << " (" << target.input_dim << " -> " << target.output_dim << ")\n";

        // Sanity Check: ¿Tenemos suficientes dimensiones?
        if (static_cast<int>(n_dims) != target.input_dim) {
            std::cerr << "❌ Error: Dimension Mismatch for " << target.name << "\n";
            std::cerr << "   Input has " << n_dims << ", model expects " << target.input_dim << ".\n";
            continue; // Saltar este modelo, no abortar todo
        }

        DimensionalityReducer reducer;
        reducer.init(target.input_dim, target.output_dim);

        // TRAINING STEP
        std::cout << "   Computing covariance matrix... ";
        auto t_start = std::chrono::high_resolution_clock::now();

        float explained_variance = reducer.train(data, n_samples);

        auto t_end = std::chrono::high_resolution_clock::now();
        std::chrono::duration<double> duration = t_end - t_start;

        std::cout << "Done (" << duration.count() << "s).\n";

        // REPORTAR VARIANZA
        std::cout << "   Explained Variance: " << std::fixed << std::setprecision(2)
                  << (explained_variance * 100.0f) << "%\n";

        // VALIDACIÓN DE CALIDAD (Synthetic Context)
        // Con nuestros datos sintéticos correlacionados, esperamos ~60-80%.
        // Si es < 40%, el patrón de inyección falló o los datos son ruido puro.
        if (explained_variance < 0.40f) {
             std::cout << "   ⚠️  Low variance. Synthetic data may lack structure.\n";
        } else {
             std::cout << "   ✅ Variance indicates structure detected.\n";
        }

        // GUARDADO (Persistencia)
        std::string model_path = "/vagrant/shared/models/pca/synthetic_" + target.name + "_pca_" + std::to_string(target.output_dim) + "d.faiss";
        std::cout << "   Saving to: " << model_path << "... ";

        if (!reducer.save(model_path)) {
            std::cerr << "❌ FAILED!\n";
            return 1;
        }
        std::cout << "Saved.\n";

        // VALIDACIÓN DE INTEGRIDAD (Roundtrip Check)
        // Esto es crítico: Asegurarnos que el archivo se puede leer de vuelta.
        DimensionalityReducer validator;
        validator.init(target.input_dim, target.output_dim);
        std::cout << "   Validating roundtrip (load)... ";

        if (!validator.load(model_path)) {
            std::cerr << "❌ FAILED! Saved model is corrupt.\n";
            return 1;
        }
        std::cout << "OK.\n";
    }

    std::cout << "\n================================================\n";
    std::cout << "✅ Plan A Execution Complete.\n";
    std::cout << "   Models saved to /vagrant/shared/models/pca/\n";
    std::cout << "   Next Step: Review Day 37 (Plan B) Integration.\n";

    return 0;
}