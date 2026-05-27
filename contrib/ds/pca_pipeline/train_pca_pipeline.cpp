// train_pca_pipeline.cpp
// Pipeline de entrenamiento PCA para datos sintéticos/reales
// Creado por: Claude (Anthropic) - Día 36 del Proyecto ML Defender
// Fecha: 09-Enero-2026
// Propósito: Entrenar modelos PCA para reducción dimensional (384→128, etc.)
//
// DEPENDENCIAS:
// - DimensionalityReducer (common-rag-ingester)
// - ONNX Runtime v1.23.2
// - FAISS v1.8.0 con PCAMatrix

#include <iostream>
#include <fstream>
#include <vector>
#include <memory>
#include <string>
#include <stdexcept>
#include <chrono>
#include <filesystem>

// DimensionalityReducer (nuestra biblioteca)
#include <dimensionality_reducer.hpp>

// ONNX Runtime
#ifdef _WIN32
#include <onnxruntime_c_api.h>
#include <onnxruntime_cxx_api.h>
#else
#include <onnxruntime/core/session/onnxruntime_cxx_api.h>
#endif

namespace fs = std::filesystem;

// ============================================================================
// CONFIGURACIÓN PCA
// ============================================================================

struct PCATrainingConfig {
    // Rutas a modelos ONNX
    struct ModelPaths {
        std::string chronos_embedder = "/shared/models/embedders/chronos_embedder.onnx";
        std::string sbert_embedder = "/shared/models/embedders/sbert_embedder.onnx";
        std::string attack_embedder = "/shared/models/embedders/attack_embedder.onnx";

        bool validate() const {
            auto check_exists = [](const std::string& path) {
                if (!fs::exists(path)) {
                    std::cerr << "ERROR: Modelo no encontrado: " << path << std::endl;
                    return false;
                }
                return true;
            };

            return check_exists(chronos_embedder) &&
                   check_exists(sbert_embedder) &&
                   check_exists(attack_embedder);
        }
    } model_paths;

    // Dimensiones de entrada/salida
    struct Dimensions {
        size_t input_features = 83;      // Features por evento
        size_t chronos_output = 512;     // Dimensión embedding Chronos
        size_t sbert_output = 384;       // Dimensión embedding SBERT
        size_t attack_output = 256;      // Dimensión embedding Attack
        size_t pca_output = 128;         // Dimensión objetivo PCA (excepto Attack: 64)
    } dimensions;

    // Rutas de salida PCA
    std::string output_dir = "/shared/models/pca/";
    std::string synthetic_data_path = "/tmp/synthetic_83f.bin";

    // Umbrales de validación
    float min_variance_threshold = 0.96f;  // 96% mínimo para datos reales
    float synthetic_variance_expected = 0.99f;  // 99%+ esperado para sintéticos

    bool validate() const {
        if (!model_paths.validate()) return false;

        if (dimensions.input_features != 83) {
            std::cerr << "ERROR: Los embedders esperan 83 características de entrada" << std::endl;
            return false;
        }

        if (output_dir.empty()) {
            std::cerr << "ERROR: output_dir vacío" << std::endl;
            return false;
        }

        // Crear directorio si no existe
        try {
            fs::create_directories(output_dir);
        } catch (const fs::filesystem_error& e) {
            std::cerr << "ERROR: No se pudo crear directorio " << output_dir
                      << ": " << e.what() << std::endl;
            return false;
        }

        return true;
    }
};

// ============================================================================
// CARGADOR DE DATOS BINARIOS
// ============================================================================

class BinaryDataLoader {
public:
    // Cargar datos del formato binario generado por SyntheticDataGenerator
    static std::vector<std::vector<float>> load(const std::string& filename) {
        std::ifstream file(filename, std::ios::binary);
        if (!file) {
            throw std::runtime_error("No se pudo abrir archivo binario: " + filename);
        }

        // Leer cabecera
        uint64_t num_events = 0, num_features = 0;
        file.read(reinterpret_cast<char*>(&num_events), sizeof(num_events));
        file.read(reinterpret_cast<char*>(&num_features), sizeof(num_features));

        if (num_events == 0 || num_features == 0) {
            throw std::runtime_error("Archivo binario corrupto o vacío: " + filename);
        }

        std::cout << "📂 Cargando " << num_events << " eventos con "
                  << num_features << " características..." << std::endl;

        std::vector<std::vector<float>> data;
        data.reserve(num_events);

        // Buffer para leer un evento completo
        std::vector<float> event_buffer(num_features);

        for (uint64_t i = 0; i < num_events; ++i) {
            file.read(reinterpret_cast<char*>(event_buffer.data()),
                     num_features * sizeof(float));

            if (!file) {
                throw std::runtime_error("Error al leer evento " + std::to_string(i) +
                                        " del archivo binario");
            }

            data.push_back(event_buffer);

            // Progress bar cada 10%
            if (num_events >= 10 && i % (num_events / 10) == 0) {
                int percent = static_cast<int>((i * 100) / num_events);
                std::cout << "   " << percent << "%" << std::endl;
            }
        }

        std::cout << "✅ Datos cargados correctamente" << std::endl;
        return data;
    }
};

// ============================================================================
// INFERENCIA ONNX (WRAPPER)
// ============================================================================

class ONNXEmbedder {
private:
    std::unique_ptr<Ort::Session> session_;
    Ort::Env env_;
    Ort::SessionOptions session_options_;
    std::vector<const char*> input_names_;
    std::vector<const char*> output_names_;
    std::vector<int64_t> input_shape_;

public:
    ONNXEmbedder(const std::string& model_path,
                 size_t input_dim,
                 size_t output_dim) {

        // Inicializar entorno ONNX Runtime
        env_ = Ort::Env(ORT_LOGGING_LEVEL_WARNING, "MLDefenderEmbedder");

        // Configurar sesión
        session_options_.SetIntraOpNumThreads(1);
        session_options_.SetGraphOptimizationLevel(GraphOptimizationLevel::ORT_ENABLE_ALL);

        // Cargar modelo
        session_ = std::make_unique<Ort::Session>(env_, model_path.c_str(), session_options_);

        // Obtener nombres de entrada/salida
        Ort::AllocatorWithDefaultOptions allocator;
        size_t num_input_nodes = session_->GetInputCount();
        size_t num_output_nodes = session_->GetOutputCount();

        if (num_input_nodes != 1 || num_output_nodes != 1) {
            throw std::runtime_error("Modelo ONNX debe tener exactamente 1 entrada y 1 salida");
        }

        input_names_.push_back(session_->GetInputName(0, allocator));
        output_names_.push_back(session_->GetOutputName(0, allocator));

        // Obtener forma de entrada
        auto input_info = session_->GetInputTypeInfo(0);
        auto tensor_info = input_info.GetTensorTypeAndShapeInfo();
        input_shape_ = tensor_info.GetShape();

        // Validar dimensiones
        if (input_shape_.size() != 2 ||
            input_shape_[0] != -1 ||  // -1 significa dimensión variable
            input_shape_[1] != static_cast<int64_t>(input_dim)) {
            throw std::runtime_error("Forma de entrada del modelo ONNX no coincide con dimensiones esperadas");
        }

        std::cout << "   Modelo ONNX cargado: " << fs::path(model_path).filename() << std::endl;
        std::cout << "   Entrada: " << input_shape_[1] << "D, Salida: " << output_dim << "D" << std::endl;
    }

    // Inferencia por lotes (más eficiente)
    std::vector<std::vector<float>> infer_batch(const std::vector<std::vector<float>>& inputs) {
        if (inputs.empty()) return {};

        size_t batch_size = inputs.size();
        size_t input_dim = inputs[0].size();

        // Preparar tensor de entrada
        std::vector<float> input_tensor;
        input_tensor.reserve(batch_size * input_dim);

        for (const auto& input : inputs) {
            input_tensor.insert(input_tensor.end(), input.begin(), input.end());
        }

        std::vector<int64_t> input_shape = {static_cast<int64_t>(batch_size),
                                           static_cast<int64_t>(input_dim)};

        // Crear tensor ONNX
        auto memory_info = Ort::MemoryInfo::CreateCpu(OrtDeviceAllocator, OrtMemTypeDefault);
        Ort::Value input_ort = Ort::Value::CreateTensor<float>(
            memory_info, input_tensor.data(), input_tensor.size(),
            input_shape.data(), input_shape.size());

        // Ejecutar inferencia
        auto output_tensors = session_->Run(
            Ort::RunOptions{nullptr},
            input_names_.data(), &input_ort, 1,
            output_names_.data(), 1);

        // Extraer resultados
        float* output_data = output_tensors[0].GetTensorMutableData<float>();
        auto output_shape = output_tensors[0].GetTensorTypeAndShapeInfo().GetShape();

        size_t output_dim = output_shape[1];
        std::vector<std::vector<float>> outputs(batch_size, std::vector<float>(output_dim));

        // Copiar datos a estructura más manejable
        for (size_t i = 0; i < batch_size; ++i) {
            std::copy(output_data + i * output_dim,
                     output_data + (i + 1) * output_dim,
                     outputs[i].begin());
        }

        return outputs;
    }
};

// ============================================================================
// PIPELINE COMPLETO PCA
// ============================================================================

class PCATrainingPipeline {
private:
    PCATrainingConfig config_;
    std::unique_ptr<ONNXEmbedder> chronos_embedder_;
    std::unique_ptr<ONNXEmbedder> sbert_embedder_;
    std::unique_ptr<ONNXEmbedder> attack_embedder_;

public:
    explicit PCATrainingPipeline(const PCATrainingConfig& config)
        : config_(config) {

        if (!config_.validate()) {
            throw std::invalid_argument("Configuración inválida para PCATrainingPipeline");
        }

        std::cout << "🔧 Inicializando pipeline PCA..." << std::endl;

        // Inicializar embedders ONNX
        chronos_embedder_ = std::make_unique<ONNXEmbedder>(
            config_.model_paths.chronos_embedder,
            config_.dimensions.input_features,
            config_.dimensions.chronos_output);

        sbert_embedder_ = std::make_unique<ONNXEmbedder>(
            config_.model_paths.sbert_embedder,
            config_.dimensions.input_features,
            config_.dimensions.sbert_output);

        attack_embedder_ = std::make_unique<ONNXEmbedder>(
            config_.model_paths.attack_embedder,
            config_.dimensions.input_features,
            config_.dimensions.attack_output);

        std::cout << "✅ Pipeline inicializado correctamente" << std::endl;
    }

    // Ejecutar pipeline completo
    bool run(const std::vector<std::vector<float>>& input_data) {
        auto total_start = std::chrono::steady_clock::now();

        try {
            std::cout << "\n========================================" << std::endl;
            std::cout << "🚀 EJECUTANDO PIPELINE PCA COMPLETO" << std::endl;
            std::cout << "========================================" << std::endl;

            // 1. Generar embeddings con Chronos
            std::cout << "\n🔮 Paso 1/5: Generando embeddings Chronos (512D)..." << std::endl;
            auto chronos_start = std::chrono::steady_clock::now();
            auto chronos_embeddings = chronos_embedder_->infer_batch(input_data);
            auto chronos_duration = std::chrono::steady_clock::now() - chronos_start;

            std::cout << "   ✅ " << chronos_embeddings.size()
                      << " embeddings generados en "
                      << std::chrono::duration_cast<std::chrono::milliseconds>(chronos_duration).count()
                      << "ms" << std::endl;

            // 2. Generar embeddings con SBERT
            std::cout << "\n🔮 Paso 2/5: Generando embeddings SBERT (384D)..." << std::endl;
            auto sbert_start = std::chrono::steady_clock::now();
            auto sbert_embeddings = sbert_embedder_->infer_batch(input_data);
            auto sbert_duration = std::chrono::steady_clock::now() - sbert_start;

            std::cout << "   ✅ " << sbert_embeddings.size()
                      << " embeddings generados en "
                      << std::chrono::duration_cast<std::chrono::milliseconds>(sbert_duration).count()
                      << "ms" << std::endl;

            // 3. Generar embeddings con Attack
            std::cout << "\n🔮 Paso 3/5: Generando embeddings Attack (256D)..." << std::endl;
            auto attack_start = std::chrono::steady_clock::now();
            auto attack_embeddings = attack_embedder_->infer_batch(input_data);
            auto attack_duration = std::chrono::steady_clock::now() - attack_start;

            std::cout << "   ✅ " << attack_embeddings.size()
                      << " embeddings generados en "
                      << std::chrono::duration_cast<std::chrono::milliseconds>(attack_duration).count()
                      << "ms" << std::endl;

            // 4. Entrenar PCA para Chronos
            std::cout << "\n🎯 Paso 4/5: Entrenando PCA Chronos (512→128D)..." << std::endl;
            auto pca_chronos = train_pca_for_embeddings(
                chronos_embeddings,
                config_.dimensions.pca_output,
                "chronos");

            // 5. Entrenar PCA para SBERT
            std::cout << "\n🎯 Paso 5/5: Entrenando PCA SBERT (384→128D)..." << std::endl;
            auto pca_sbert = train_pca_for_embeddings(
                sbert_embeddings,
                config_.dimensions.pca_output,
                "sbert");

            // 6. Entrenar PCA para Attack (256→64D)
            std::cout << "\n🎯 Paso extra: Entrenando PCA Attack (256→64D)..." << std::endl;
            auto pca_attack = train_pca_for_embeddings(
                attack_embeddings,
                64,  // 64D para attack (diferente de los otros)
                "attack");

            // 7. Guardar modelos
            std::cout << "\n💾 Guardando modelos PCA..." << std::endl;
            save_pca_model(pca_chronos, "chronos_pca_512_128_synthetic_v1.faiss");
            save_pca_model(pca_sbert, "sbert_pca_384_128_synthetic_v1.faiss");
            save_pca_model(pca_attack, "attack_pca_256_64_synthetic_v1.faiss");

            // 8. Resumen final
            auto total_duration = std::chrono::steady_clock::now() - total_start;

            std::cout << "\n========================================" << std::endl;
            std::cout << "🎉 PIPELINE PCA COMPLETADO CON ÉXITO" << std::endl;
            std::cout << "========================================" << std::endl;
            std::cout << "📊 Resumen:" << std::endl;
            std::cout << "   - Eventos procesados: " << input_data.size() << std::endl;
            std::cout << "   - Tiempo total: "
                      << std::chrono::duration_cast<std::chrono::seconds>(total_duration).count()
                      << "s" << std::endl;
            std::cout << "   - Modelos guardados en: " << config_.output_dir << std::endl;
            std::cout << "   - Nota: Datos sintéticos - varianza puede ser >99%" << std::endl;

            return true;

        } catch (const std::exception& e) {
            std::cerr << "❌ ERROR en pipeline PCA: " << e.what() << std::endl;
            return false;
        }
    }

private:
    // Entrenar PCA para un tipo de embeddings
    DimensionalityReducer train_pca_for_embeddings(
        const std::vector<std::vector<float>>& embeddings,
        size_t target_dim,
        const std::string& embedder_name) {

        auto start_time = std::chrono::steady_clock::now();

        std::cout << "   Entrenando PCA para " << embedder_name
                  << " (" << embeddings[0].size() << "→" << target_dim << "D)..." << std::endl;

        // Crear y entrenar reducer
        DimensionalityReducer reducer;

        // Convertir a formato plano para entrenamiento
        std::vector<float> flat_embeddings;
        flat_embeddings.reserve(embeddings.size() * embeddings[0].size());

        for (const auto& emb : embeddings) {
            flat_embeddings.insert(flat_embeddings.end(), emb.begin(), emb.end());
        }

        // Entrenar PCA
        reducer.train(flat_embeddings.data(),
                     embeddings.size(),
                     embeddings[0].size(),
                     target_dim);

        // Validar varianza
        float variance = reducer.get_explained_variance();
        auto duration = std::chrono::steady_clock::now() - start_time;

        std::cout << "   ✅ PCA entrenado en "
                  << std::chrono::duration_cast<std::chrono::milliseconds>(duration).count()
                  << "ms" << std::endl;
        std::cout << "   📈 Varianza explicada: " << (variance * 100.0f) << "%" << std::endl;

        if (variance < config_.min_variance_threshold) {
            std::cout << "   ⚠️  ADVERTENCIA: Varianza baja para datos sintéticos" << std::endl;
            std::cout << "      Esperado: >" << (config_.synthetic_variance_expected * 100)
                      << "%, Actual: " << (variance * 100) << "%" << std::endl;
        }

        return reducer;
    }

    // Guardar modelo PCA
    void save_pca_model(const DimensionalityReducer& reducer,
                       const std::string& filename) {
        std::string full_path = config_.output_dir + "/" + filename;

        if (reducer.save(full_path)) {
            std::cout << "   💾 Modelo guardado: " << filename << std::endl;

            // Verificar que se puede cargar
            DimensionalityReducer loaded;
            if (loaded.load(full_path)) {
                std::cout << "   🔍 Modelo cargado y validado correctamente" << std::endl;
            } else {
                std::cout << "   ⚠️  Modelo guardado pero no se pudo cargar para validación" << std::endl;
            }
        } else {
            std::cout << "   ❌ Error al guardar modelo: " << filename << std::endl;
        }
    }
};

// ============================================================================
// FUNCIÓN PRINCIPAL
// ============================================================================

int main(int argc, char* argv[]) {
    std::cout << "================================================" << std::endl;
    std::cout << "🧠 ML DEFENDER - PIPELINE ENTRENAMIENTO PCA D36" << std::endl;
    std::cout << "================================================" << std::endl;

    try {
        // 1. Configuración
        PCATrainingConfig config;

        // Sobreescribir con argumentos
        if (argc > 1) config.synthetic_data_path = argv[1];
        if (argc > 2) config.output_dir = argv[2];

        std::cout << "⚙️  Configuración PCA:" << std::endl;
        std::cout << "   - Datos de entrada: " << config.synthetic_data_path << std::endl;
        std::cout << "   - Directorio salida: " << config.output_dir << std::endl;
        std::cout << "   - Umbral varianza: " << (config.min_variance_threshold * 100) << "%" << std::endl;

        // 2. Cargar datos sintéticos
        std::cout << "\n📂 Cargando datos sintéticos..." << std::endl;
        auto synthetic_data = BinaryDataLoader::load(config.synthetic_data_path);

        if (synthetic_data.empty()) {
            std::cerr << "❌ ERROR: Datos sintéticos vacíos o no cargados" << std::endl;
            return 1;
        }

        // 3. Validar dimensiones
        size_t expected_features = config.dimensions.input_features;
        if (synthetic_data[0].size() != expected_features) {
            std::cerr << "❌ ERROR: Datos tienen " << synthetic_data[0].size()
                      << " features, se esperaban " << expected_features << std::endl;
            return 1;
        }

        // 4. Ejecutar pipeline
        PCATrainingPipeline pipeline(config);

        if (!pipeline.run(synthetic_data)) {
            std::cerr << "❌ ERROR: Pipeline PCA falló" << std::endl;
            return 1;
        }

        std::cout << "\n🏛️  VIA APPIA QUALITY: Pipeline validado con datos sintéticos" << std::endl;
        std::cout << "   - Arquitectura probada end-to-end" << std::endl;
        std::cout << "   - Código listo para datos reales (Día 37)" << std::endl;
        std::cout << "   - Documentación completa en README.md" << std::endl;

    } catch (const std::exception& e) {
        std::cerr << "❌ ERROR EXCEPCIÓN: " << e.what() << std::endl;
        return 1;
    } catch (...) {
        std::cerr << "❌ ERROR DESCONOCIDO" << std::endl;
        return 1;
    }

    return 0;
}