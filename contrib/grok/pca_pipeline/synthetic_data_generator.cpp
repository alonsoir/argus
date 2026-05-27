// synthetic_data_generator.cpp
// Generador de datos sintéticos realistas (83 features)
// Basado en rangos típicos de CTU-13 y observaciones de tráfico real

#include <iostream>
#include <fstream>
#include <random>
#include <vector>
#include <spdlog/spdlog.h>
#include <cmath>

using Features83 = std::array<float, 83>;

std::vector<Features83> generate_synthetic_features(size_t num_samples) {
    std::random_device rd;
    std::mt19937 gen(rd());

    // Distribuciones aproximadas basadas en literatura CTU-13 y tráfico real
    std::normal_distribution<float> duration_dist(5000.0f, 10000.0f);      // us
    std::normal_distribution<float> pkt_size_dist(800.0f, 600.0f);         // bytes
    std::exponential_distribution<float> iat_dist(0.001f);                 // segundos (alta tasa)
    std::normal_distribution<float> rate_dist(1000.0f, 2000.0f);           // pkts/s
    std::uniform_real_distribution<float> ratio_dist(0.1f, 10.0f);         // sbytes/dbytes ratio

    std::vector<Features83> data;
    data.reserve(num_samples);

    for (size_t i = 0; i < num_samples; ++i) {
        Features83 f{0};

        float duration = std::max(0.1f, duration_dist(gen));
        float mean_pkt_size = std::max(60.0f, pkt_size_dist(gen));
        float mean_iat = std::max(0.00001f, iat_dist(gen));

        // Grupo 1: básicos (23)
        f[0] = duration;
        f[1] = duration * rate_dist(gen);                    // spkts aprox
        f[2] = f[1] * ratio_dist(gen);                       // dpkts
        f[3] = f[1] * mean_pkt_size;                         // sbytes
        f[4] = f[2] * mean_pkt_size * ratio_dist(gen);       // dbytes

        // Rellenar el resto con variaciones coherentes
        for (size_t j = 5; j < 83; ++j) {
            // Simular estadísticas derivadas (std, min, max, ratios, flags, etc.)
            if (j % 4 == 0) f[j] = std::abs(std::normal_distribution<float>(0.0f, mean_iat)(gen));
            else if (j % 4 == 1) f[j] = mean_pkt_size + std::normal_distribution<float>(0.0f, 200.0f)(gen);
            else if (j % 4 == 2) f[j] = std::uniform_real_distribution<float>(0.0f, 1.0f)(gen); // ratios
            else f[j] = std::bernoulli_distribution(0.1)(gen) ? 1.0f : 0.0f; // flags
        }

        // Asegurar no negativos
        for (auto& v : f) v = std::max(0.0f, v);

        data.emplace_back(f);
    }

    spdlog::info("Generadas {} muestras sintéticas de 83 features", num_samples);
    return data;
}

int main(int argc, char* argv[]) {
    std::string output_path = "/shared/data/synthetic_features.bin";
    size_t num_samples = 20000;

    // Parseo simple de argumentos
    for (int i = 1; i < argc; ++i) {
        std::string arg(argv[i]);
        if (arg == "--output" && i+1 < argc) output_path = argv[++i];
        if (arg == "--samples" && i+1 < argc) num_samples = std::stoull(argv[++i]);
    }

    auto data = generate_synthetic_features(num_samples);

    std::ofstream out(output_path, std::ios::binary);
    if (!out) {
        spdlog::error("No se pudo abrir {} para escritura", output_path);
        return 1;
    }

    out.write(reinterpret_cast<const char*>(data.data()), data.size() * sizeof(Features83));
    spdlog::info("Datos sintéticos guardados en {}", output_path);
    return 0;
}