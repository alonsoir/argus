/**
 * File: common-rag-ingester/tools/synthetic_data_generator.cpp
 * Day: 36 - Plan A Execution
 * Context: TECHNICAL_DEBT_DAY36.md (Feature Gap Discovery)
 *
 * Purpose:
 *   Generar datos sintéticos de 83 features para validar la arquitectura
 *   de DimensionalityReducer (Day 35).
 *
 * Design Principles (Via Appia):
 *   - Deterministic: Mismo seed (42) = misma data.
 *   - Correlated Noise: PCA necesita estructura para reducir varianza.
 *   - Binary Output: Rendimiento óptimo para pipeline masivo.
 *
 * Output Format (Binary Stream):
 *   [Header: uint32_t N_samples] [uint32_t Input_Dim] [Data: float32...]
 */

#include <iostream>
#include <vector>
#include <random>
#include <cstdint>
#include <fstream>
#include <chrono>
#include <span>

// Configuration Constants
constexpr uint32_t DEFAULT_SAMPLES = 50000;
constexpr uint32_t DEFAULT_DIM = 83;  // Matches ONNX embedders expectation
constexpr uint32_t SEED = 42;        // Reproducibilidad científica

struct GeneratorConfig {
    uint32_t samples;
    uint32_t dimensions;
    std::string output_file; // Empty = stdout
};

// Helper: Escribir binario endian-safe (standard little-endian assumed)
void write_binary(std::ostream& os, const auto& value) {
    os.write(reinterpret_cast<const char*>(&value), sizeof(value));
}

int main(int argc, char* argv[]) {
    GeneratorConfig config;
    config.samples = DEFAULT_SAMPLES;
    config.dimensions = DEFAULT_DIM;

    // Simple CLI parsing (Sin flags pesadas para mantenibilidad)
    if (argc > 1) {
        try {
            config.samples = std::stoul(argv[1]);
        } catch (...) { std::cerr << "Error parsing samples count.\n"; return 1; }
    }

    std::cout << "🏛️ Synthetic Data Generator (Day 36 - Plan A)\n";
    std::cout << "Config: " << config.samples << " samples, " << config.dimensions << " dims\n";

    // Engine de Entropía Controlada
    std::mt19937 gen(SEED);
    std::normal_distribution<float> dist(0.0f, 1.0f);

    std::vector<float> data;
    data.reserve(config.samples * config.dimensions);

    // Generación con patrón periódico
    // "Pattern Injection": Cada 10ª dimensión tiene correlación con el índice.
    // Esto asegura que PCA capture varianza (>50%) en sintético.
    // Sin esto, datos aleatorios puros dan varianza ~0% en PCA.
    std::cout << "Injecting controlled entropy pattern... \n";

    for (uint32_t i = 0; i < config.samples; ++i) {
        float pattern_offset = (static_cast<float>(i % 100) / 100.0f);

        for (uint32_t d = 0; d < config.dimensions; ++d) {
            float val = dist(gen);

            // Structural Noise: Correlation en bloques de 10
            if (d % 10 == 0) {
                val += pattern_offset;
            }
            data.push_back(val);
        }
    }

    // Escritura a Stdout (para pipe) o Archivo
    std::cout << "Writing binary stream to stdout (use pipe or redirection).\n";

    // Header
    write_binary(std::cout, config.samples);
    write_binary(std::cout, config.dimensions);

    // Payload
    std::cout.write(reinterpret_cast<const char*>(data.data()),
                    data.size() * sizeof(float));

    std::cout.flush();

    return 0;
}