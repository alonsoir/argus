// synthetic_data_generator.cpp
// Generador de datos sintéticos de 83 características para validación PCA
// Creado por: Claude (Anthropic) - Día 36 del Proyecto ML Defender
// Fecha: 09-Enero-2026
// Propósito: Validar pipeline arquitectónico cuando datos reales no están disponibles
//
// CONVENCIONES C++20:
// - smart pointers para ownership claro
// - RAII para manejo de recursos
// - strong typing con enum class
// - const correctness
// - no raw loops cuando hay algoritmos STL
// - manejo de errores con std::optional/excepciones

#include <iostream>
#include <fstream>
#include <vector>
#include <random>
#include <algorithm>
#include <memory>
#include <cstdint>
#include <stdexcept>
#include <filesystem>
#include <chrono>

namespace fs = std::filesystem;

// ============================================================================
// CONFIGURACIÓN Y CONSTANTES
// ============================================================================

struct SyntheticConfig {
    size_t num_events = 20000;      // N eventos para entrenamiento PCA
    size_t num_features = 83;       // Features por evento (esperado por embedders)
    size_t seed = 42;               // Semilla reproducible para debugging
    float mean = 0.0f;              // Media distribución normal
    float stddev = 1.0f;            // Desviación estándar
    std::string output_path = "/tmp/synthetic_83f.bin";

    // Validación de configuración
    bool validate() const {
        if (num_events < 1000) {
            std::cerr << "ERROR: Muy pocos eventos para PCA (<1000)" << std::endl;
            return false;
        }
        if (num_features != 83) {
            std::cerr << "ERROR: Embedders esperan 83 features, no "
                      << num_features << std::endl;
            return false;
        }
        if (output_path.empty()) {
            std::cerr << "ERROR: output_path vacío" << std::endl;
            return false;
        }
        return true;
    }
};

// ============================================================================
// GENERADOR DE DATOS SINTÉTICOS
// ============================================================================

class SyntheticDataGenerator {
private:
    SyntheticConfig config_;
    std::mt19937 rng_;
    std::normal_distribution<float> distribution_;

public:
    // Constructor con validación
    explicit SyntheticDataGenerator(const SyntheticConfig& config)
        : config_(config)
        , rng_(config.seed)
        , distribution_(config.mean, config.stddev) {

        if (!config_.validate()) {
            throw std::invalid_argument("Configuración inválida para SyntheticDataGenerator");
        }
    }

    // Generar matriz de datos [num_events × num_features]
    std::vector<std::vector<float>> generate() {
        auto start_time = std::chrono::steady_clock::now();

        std::vector<std::vector<float>> data;
        data.reserve(config_.num_events);

        std::cout << "🧪 Generando " << config_.num_events
                  << " eventos con " << config_.num_features
                  << " características cada uno..." << std::endl;

        for (size_t i = 0; i < config_.num_events; ++i) {
            std::vector<float> event(config_.num_features);

            // Usar std::generate para evitar raw loop
            std::generate(event.begin(), event.end(),
                         [this]() { return distribution_(rng_); });

            data.push_back(std::move(event));

            // Progress bar cada 10%
            if (config_.num_events >= 10 && i % (config_.num_events / 10) == 0) {
                int percent = static_cast<int>((i * 100) / config_.num_events);
                std::cout << "   " << percent << "%" << std::endl;
            }
        }

        auto end_time = std::chrono::steady_clock::now();
        auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(end_time - start_time);

        std::cout << "✅ Generación completada en " << duration.count() << "ms" << std::endl;
        std::cout << "📊 Tamaño total: "
                  << (config_.num_events * config_.num_features * sizeof(float) / (1024.0 * 1024.0))
                  << " MB" << std::endl;

        return data;
    }

    // Guardar datos en formato binario (eficiente para grandes datasets)
    bool save_to_binary(const std::vector<std::vector<float>>& data,
                       const std::string& filename) {
        std::ofstream file(filename, std::ios::binary);
        if (!file) {
            std::cerr << "ERROR: No se pudo abrir archivo " << filename << std::endl;
            return false;
        }

        // Escribir cabecera: [num_events][num_features]
        uint64_t n_events = data.size();
        uint64_t n_features = (n_events > 0) ? data[0].size() : 0;

        file.write(reinterpret_cast<const char*>(&n_events), sizeof(n_events));
        file.write(reinterpret_cast<const char*>(&n_features), sizeof(n_features));

        // Escribir datos
        for (const auto& event : data) {
            file.write(reinterpret_cast<const char*>(event.data()),
                      event.size() * sizeof(float));
        }

        if (!file) {
            std::cerr << "ERROR: Error al escribir en archivo" << std::endl;
            return false;
        }

        std::cout << "💾 Datos guardados en: " << filename << std::endl;
        std::cout << "   Eventos: " << n_events << ", Features: " << n_features << std::endl;

        return true;
    }

    // Guardar también en formato de texto para debugging (opcional)
    bool save_to_text(const std::vector<std::vector<float>>& data,
                     const std::string& filename,
                     size_t max_events = 10) {
        std::ofstream file(filename);
        if (!file) {
            std::cerr << "ERROR: No se pudo abrir archivo de texto " << filename << std::endl;
            return false;
        }

        // Escribir cabecera
        file << "# Datos sintéticos para validación PCA - ML Defender Día 36\n";
        file << "# Eventos: " << data.size()
             << ", Features por evento: " << (data.empty() ? 0 : data[0].size()) << "\n";
        file << "# Formato: evento_idx feature_0 feature_1 ... feature_82\n\n";

        // Escribir solo primeros max_events para debugging
        size_t limit = std::min(max_events, data.size());
        for (size_t i = 0; i < limit; ++i) {
            file << i;
            for (const auto& val : data[i]) {
                file << " " << val;
            }
            file << "\n";
        }

        if (limit < data.size()) {
            file << "\n# ... (" << (data.size() - limit) << " eventos más)\n";
        }

        std::cout << "📝 Debug file: " << filename
                  << " (primeros " << limit << " eventos)" << std::endl;

        return true;
    }
};

// ============================================================================
// FUNCIÓN PRINCIPAL
// ============================================================================

int main(int argc, char* argv[]) {
    std::cout << "================================================" << std::endl;
    std::cout << "🧠 ML DEFENDER - GENERADOR DATOS SINTÉTICOS D36" << std::endl;
    std::cout << "================================================" << std::endl;

    try {
        // 1. Configuración
        SyntheticConfig config;

        // Sobreescribir con argumentos si se proporcionan
        if (argc > 1) config.num_events = std::stoul(argv[1]);
        if (argc > 2) config.output_path = argv[2];
        if (argc > 3) config.seed = std::stoul(argv[3]);

        std::cout << "⚙️  Configuración:" << std::endl;
        std::cout << "   - Eventos: " << config.num_events << std::endl;
        std::cout << "   - Features por evento: " << config.num_features << std::endl;
        std::cout << "   - Semilla: " << config.seed << std::endl;
        std::cout << "   - Output: " << config.output_path << std::endl;

        // 2. Generar datos
        SyntheticDataGenerator generator(config);
        auto synthetic_data = generator.generate();

        // 3. Validar estadísticas básicas
        if (!synthetic_data.empty()) {
            float first_val = synthetic_data[0][0];
            float last_val = synthetic_data.back().back();
            std::cout << "📐 Estadísticas de muestra:" << std::endl;
            std::cout << "   - Primer valor: " << first_val << std::endl;
            std::cout << "   - Último valor: " << last_val << std::endl;
            std::cout << "   - Valores por evento: " << synthetic_data[0].size() << std::endl;
        }

        // 4. Guardar en binario (para entrenamiento)
        if (!generator.save_to_binary(synthetic_data, config.output_path)) {
            return 1;
        }

        // 5. Guardar en texto para debugging
        std::string debug_path = config.output_path + ".txt";
        generator.save_to_text(synthetic_data, debug_path, 5);

        std::cout << "================================================" << std::endl;
        std::cout << "✅ GENERACIÓN COMPLETADA CON ÉXITO" << std::endl;
        std::cout << "================================================" << std::endl;

    } catch (const std::exception& e) {
        std::cerr << "❌ ERROR EXCEPCIÓN: " << e.what() << std::endl;
        return 1;
    } catch (...) {
        std::cerr << "❌ ERROR DESCONOCIDO" << std::endl;
        return 1;
    }

    return 0;
}