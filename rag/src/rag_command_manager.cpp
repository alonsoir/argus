#include "rag/rag_command_manager.hpp"
#include "rag/config_manager.hpp"
#include "rag/llama_integration.hpp"
#include <iostream>
#include <algorithm>

// Declaración externa de la instancia global de LlamaIntegration (namespace global)
extern std::unique_ptr<LlamaIntegration> llama_integration;

namespace Rag {

RagCommandManager::RagCommandManager() : validator_() {
    std::cout << "🔧 RagCommandManager inicializado" << std::endl;
}

RagCommandManager::~RagCommandManager() {
    std::cout << "🔧 RagCommandManager finalizado" << std::endl;
}

void RagCommandManager::processCommand(const std::vector<std::string>& args) {
    if (args.empty()) {
        std::cout << "❌ Comando RAG no especificado" << std::endl;
        return;
    }

    const std::string& command = args[0];

    if (command == "show_config") {
        showConfig(args);
    } else if (command == "show_capabilities") {
        showCapabilities(args);
    } else if (command == "update_setting") {
        updateSetting(args);
    } else if (command == "ask_llm") {
        askLLM(args);
        // ========== NUEVOS COMANDOS FAISS (Day 41) ==========
    } else if (command == "query_similar") {
        handleQuerySimilar(args);
    } else if (command == "list") {
        handleListEvents(args);
    } else if (command == "stats") {
        handleStats(args);
    } else if (command == "info") {
        handleInfo(args);
        // ====================================================
    } else if (command == "recent") {
        handleRecent(args);
    } else if (command == "search") {
        handleSearch(args);
    } else if (command == "help") {
            showHelp();  // ← Esta llamada está bien
    } else {
        std::cout << "❌ Comando RAG no reconocido: " << command << std::endl;
        std::cout << "💡 Comandos disponibles: show_config, update_setting, show_capabilities, ask_llm, "
                  << "query_similar, list, stats, info" << std::endl;
    }
}

void RagCommandManager::showConfig(const std::vector<std::string>& /*args*/) {
    std::cout << "\n🔧 CONFIGURACIÓN RAG - MOSTRANDO..." << std::endl;

    try {
        auto& config_manager = ConfigManager::getInstance();
        auto rag_config = config_manager.getRagConfig();
        auto etcd_config = config_manager.getEtcdConfig();

        std::cout << "📋 Configuración RAG:" << std::endl;
        std::cout << "   - Host: " << rag_config.host << std::endl;
        std::cout << "   - Port: " << rag_config.port << std::endl;
        std::cout << "   - Model: " << rag_config.model_name << std::endl;
        std::cout << "   - Embedding Dimension: " << rag_config.embedding_dimension << std::endl;

        std::cout << "📋 Configuración Etcd:" << std::endl;
        std::cout << "   - Host: " << etcd_config.host << std::endl;
        std::cout << "   - Port: " << etcd_config.port << std::endl;

        // Mostrar estado del LLM
        std::cout << "🤖 Estado LLM: " << (llama_integration ? "CARGADO" : "NO DISPONIBLE") << std::endl;

    } catch (const std::exception& e) {
        std::cerr << "❌ Error al mostrar configuración: " << e.what() << std::endl;
    }
}

void RagCommandManager::showCapabilities(const std::vector<std::string>& /*args*/) {
    std::cout << "\n🚀 CAPACIDADES DEL SISTEMA RAG" << std::endl;
    std::cout << "===============================" << std::endl;
    std::cout << "✅ Configuración persistente en JSON" << std::endl;
    std::cout << "✅ Comandos de configuración en tiempo real" << std::endl;
    std::cout << "✅ Validación robusta de configuraciones" << std::endl;
    std::cout << "✅ Integración con etcd (via WhiteListManager)" << std::endl;
    std::cout << "🤖 LLAMA Integration: " << (llama_integration ? "ACTIVA" : "INACTIVA") << std::endl;
    std::cout << "📊 Base Vectorial: PRÓXIMAMENTE (con logs del pipeline)" << std::endl;
    std::cout << "===============================" << std::endl;
}

void RagCommandManager::updateSetting(const std::vector<std::string>& args) {
    if (args.size() != 3) {
        std::cout << "❌ Error: Uso: rag update_setting <clave> <valor>" << std::endl;
        return;
    }

    const std::string& key = args[1];
    const std::string& value = args[2];

    // Usar el validador específico de RAG
    if (!validator_.validate(key, value)) {
        return;
    }

    auto& config_manager = ConfigManager::getInstance();
    std::string path = "rag." + key;

    if (config_manager.updateSetting(path, value)) {
        std::cout << "✅ Configuración actualizada: " << key << " = " << value << std::endl;
    } else {
        std::cout << "❌ Error al actualizar la configuración" << std::endl;
    }
}

void RagCommandManager::askLLM(const std::vector<std::string>& args) {
    if (args.size() < 2) {
        std::cout << "❌ Error: Uso: rag ask_llm <pregunta>" << std::endl;
        return;
    }

    // Reconstruir la pregunta completa
    std::string question;
    for (size_t i = 1; i < args.size(); ++i) {
        if (i > 1) question += " ";
        question += args[i];
    }

    std::cout << "🤖 Consultando LLM: \"" << question << "\"" << std::endl;

    // Verificar si LLAMA está disponible
    if (!llama_integration) {
        std::cout << "❌ LLAMA Integration no disponible" << std::endl;
        std::cout << "💡 Asegúrate de que el modelo TinyLlama esté en /vagrant/rag/models/" << std::endl;
        return;
    }

    try {
        // Generar respuesta usando LLAMA REAL
        std::string response = llama_integration->generateResponse(question);
        std::cout << "\n🤖 Respuesta: " << response << std::endl;

    } catch (const std::exception& e) {
        std::cerr << "❌ Error en LLAMA: " << e.what() << std::endl;
        std::cout << "⚠️  Fallo en la generación de respuesta" << std::endl;
    }
}

    // /vagrant/rag/src/rag_command_manager.cpp

// ============================================================================
// Day 41: FAISS Integration Methods
// ============================================================================

void RagCommandManager::setFAISSIndices(
    faiss::IndexFlatL2* chronos,
    faiss::IndexFlatL2* sbert,
    faiss::IndexFlatL2* attack)
{
    chronos_index_ = chronos;
    sbert_index_ = sbert;
    attack_index_ = attack;
    std::cout << "✅ FAISS indices registered in RagCommandManager" << std::endl;
}

void RagCommandManager::setMetadataReader(ml_defender::MetadataReader* metadata) {
    metadata_reader_ = metadata;
    std::cout << "✅ Metadata reader registered in RagCommandManager" << std::endl;
}

void RagCommandManager::handleQuerySimilar(const std::vector<std::string>& args) {
    if (args.size() < 2) {
        std::cout << "❌ Usage: rag query_similar <event_id> [--explain]" << std::endl;
        return;
    }

    if (!metadata_reader_) {
        std::cout << "❌ Metadata not loaded (rag-ingester must run first)" << std::endl;
        return;
    }

    if (!attack_index_ || attack_index_->ntotal == 0) {
        std::cout << "❌ FAISS indices not loaded or empty" << std::endl;
        return;
    }

    std::string event_id = args[1];
    bool explain = (args.size() >= 3 && args[2] == "--explain");

    // Find FAISS index for this event_id
    auto faiss_idx_opt = metadata_reader_->get_faiss_idx_by_event_id(event_id);
    if (!faiss_idx_opt) {
        std::cout << "❌ Event not found: " << event_id << std::endl;
        return;
    }

    size_t query_idx = *faiss_idx_opt;

    // Reconstruct query vector from FAISS
    std::vector<float> query_vector(64);
    attack_index_->reconstruct(query_idx, query_vector.data());

    // Search top-k neighbors
    int k = 5;
    std::vector<faiss::idx_t> indices(k);
    std::vector<float> distances(k);

    attack_index_->search(1, query_vector.data(), k,
                          distances.data(), indices.data());

    // Display query event
    auto query_meta = metadata_reader_->get_by_faiss_idx(query_idx);

    std::cout << "\n🔍 Query Event: " << query_meta.event_id << std::endl;
    std::cout << "   Classification: " << query_meta.classification << std::endl;
    std::cout << "   Discrepancy:    " << std::fixed << std::setprecision(3)
              << query_meta.discrepancy_score << std::endl;

    std::cout << "\n📊 Top " << k << " Similar Events:\n" << std::endl;

    int same_class_count = 0;

    for (int i = 0; i < k; ++i) {
        if (indices[i] < 0) continue;

        auto match = metadata_reader_->get_by_faiss_idx(indices[i]);

        bool is_same_class = (match.classification == query_meta.classification);
        if (is_same_class && indices[i] != static_cast<faiss::idx_t>(query_idx)) {
            same_class_count++;
        }

        std::cout << " " << (i + 1) << ". " << std::setw(20) << std::left << match.event_id
                  << " (dist: " << std::fixed << std::setprecision(3) << distances[i] << ") - "
                  << std::setw(10) << match.classification;

        if (indices[i] == static_cast<faiss::idx_t>(query_idx)) {
            std::cout << " [SELF]";
        } else if (is_same_class) {
            std::cout << " ✓";
        }

        std::cout << std::endl;
    }

    std::cout << "\n📈 Clustering Quality:" << std::endl;
    std::cout << "   Same-class neighbors: " << same_class_count << "/" << (k - 1)
              << " (" << std::fixed << std::setprecision(1)
              << (same_class_count * 100.0 / (k - 1)) << "%)" << std::endl;

    if (explain) {
        std::cout << "\n🔬 Explanation (--explain):" << std::endl;
        std::cout << "   Feature space: Attack embedding (64-dim)" << std::endl;
        std::cout << "   Distance metric: L2 (Euclidean)" << std::endl;
        std::cout << "   Lower distance = more similar behavior" << std::endl;
        std::cout << "   Expected: Same-class events cluster together (<0.5 dist)" << std::endl;
    }

    std::cout << std::endl;
}

void RagCommandManager::handleListEvents(const std::vector<std::string>& args) {
    if (!metadata_reader_) {
        std::cout << "❌ Metadata not loaded" << std::endl;
        return;
    }

    std::string filter = (args.size() >= 2) ? args[1] : "ALL";

    if (filter != "ALL" && filter != "BENIGN" && filter != "MALICIOUS") {
        std::cout << "❌ Invalid filter. Use: ALL, BENIGN, or MALICIOUS" << std::endl;
        return;
    }

    std::cout << "\n📋 Events (" << filter << "):\n" << std::endl;

    if (filter == "ALL") {
        size_t total = metadata_reader_->count();
        std::cout << "Total events: " << total << std::endl;
        std::cout << "(Use 'rag list BENIGN' or 'rag list MALICIOUS' for filtered view)" << std::endl;
    } else {
        auto events = metadata_reader_->get_by_classification(filter);
        std::cout << "Found " << events.size() << " " << filter << " events:\n" << std::endl;

        int count = 0;
        for (const auto& evt : events) {
            std::cout << " " << std::setw(20) << evt.event_id
                      << " (disc: " << std::fixed << std::setprecision(3)
                      << evt.discrepancy_score << ")" << std::endl;

            if (++count >= 20) {
                std::cout << "\n(Showing first 20 of " << events.size() << " events)" << std::endl;
                break;
            }
        }
    }

    std::cout << std::endl;
}

void RagCommandManager::handleStats(const std::vector<std::string>& /*args*/) {
    if (!metadata_reader_) {
        std::cout << "❌ Metadata not loaded" << std::endl;
        return;
    }

    auto benign = metadata_reader_->get_by_classification("BENIGN");
    auto malicious = metadata_reader_->get_by_classification("MALICIOUS");
    size_t total = metadata_reader_->count();

    std::cout << "\n📊 Dataset Statistics:\n" << std::endl;
    std::cout << "Total events:     " << total << std::endl;
    std::cout << "BENIGN:           " << benign.size()
              << " (" << std::fixed << std::setprecision(1)
              << (benign.size() * 100.0 / total) << "%)" << std::endl;
    std::cout << "MALICIOUS:        " << malicious.size()
              << " (" << (malicious.size() * 100.0 / total) << "%)" << std::endl;

    if (chronos_index_) {
        std::cout << "\nFAISS Indices:" << std::endl;
        std::cout << "Chronos vectors:  " << chronos_index_->ntotal << std::endl;
        std::cout << "SBERT vectors:    " << sbert_index_->ntotal << std::endl;
        std::cout << "Attack vectors:   " << attack_index_->ntotal << std::endl;
    }

    std::cout << std::endl;
}

void RagCommandManager::handleInfo(const std::vector<std::string>& /*args*/) {
    if (!chronos_index_) {
        std::cout << "❌ FAISS indices not loaded" << std::endl;
        return;
    }

    std::cout << "\n🔍 FAISS Index Information:\n" << std::endl;

    std::cout << "Chronos Index:" << std::endl;
    std::cout << "  Dimension: " << chronos_index_->d << std::endl;
    std::cout << "  Vectors:   " << chronos_index_->ntotal << std::endl;
    std::cout << "  Type:      IndexFlatL2 (exact search)" << std::endl;

    std::cout << "\nSBERT Index:" << std::endl;
    std::cout << "  Dimension: " << sbert_index_->d << std::endl;
    std::cout << "  Vectors:   " << sbert_index_->ntotal << std::endl;

    std::cout << "\nAttack Index:" << std::endl;
    std::cout << "  Dimension: " << attack_index_->d << std::endl;
    std::cout << "  Vectors:   " << attack_index_->ntotal << std::endl;

    std::cout << std::endl;
}

    void RagCommandManager::handleRecent(const std::vector<std::string>& args) {
    if (!metadata_reader_) {
        std::cout << "❌ Metadata not loaded" << std::endl;
        return;
    }

    size_t limit = 10;

    // Parse --limit flag
    for (size_t i = 1; i < args.size(); ++i) {
        if (args[i] == "--limit" && i + 1 < args.size()) {
            limit = std::stoi(args[i + 1]);
        }
    }

    auto events = metadata_reader_->get_recent(limit);

    std::cout << "\n📅 Recent Events (last " << limit << "):\n" << std::endl;

    for (const auto& evt : events) {
        // Convert timestamp to readable format
        time_t t = static_cast<time_t>(evt.timestamp / 1000ULL);  // nanoseconds to seconds
        char time_str[64];
        strftime(time_str, sizeof(time_str), "%Y-%m-%d %H:%M:%S", localtime(&t));

        std::cout << " " << std::setw(20) << std::left << evt.event_id
                  << " | " << time_str
                  << " | " << std::setw(10) << evt.classification
                  << " | disc: " << std::fixed << std::setprecision(3)
                  << evt.discrepancy_score << std::endl;
    }

    if (!events.empty()) {
        std::cout << "\n💡 Use: rag query_similar " << events[0].event_id
                  << " to find similar events" << std::endl;
    }

    std::cout << std::endl;
}

void RagCommandManager::handleSearch(const std::vector<std::string>& args) {
    if (!metadata_reader_) {
        std::cout << "❌ Metadata not loaded" << std::endl;
        return;
    }

    std::string classification = "";
    float discrepancy_min = 0.0;
    float discrepancy_max = 1.0;
    size_t limit = 100;

    // Parse arguments
    for (size_t i = 1; i < args.size(); ++i) {
        if (args[i] == "--classification" && i + 1 < args.size()) {
            classification = args[i + 1];
            i++;
        } else if (args[i] == "--discrepancy-min" && i + 1 < args.size()) {
            discrepancy_min = std::stof(args[i + 1]);
            i++;
        } else if (args[i] == "--discrepancy-max" && i + 1 < args.size()) {
            discrepancy_max = std::stof(args[i + 1]);
            i++;
        } else if (args[i] == "--limit" && i + 1 < args.size()) {
            limit = std::stoi(args[i + 1]);
            i++;
        }
    }

    auto events = metadata_reader_->search(classification, discrepancy_min, discrepancy_max, limit);

    std::cout << "\n🔍 Search Results:\n" << std::endl;
    std::cout << "Filters: ";
    if (!classification.empty()) std::cout << "class=" << classification << " ";
    std::cout << "disc=[" << discrepancy_min << ", " << discrepancy_max << "] ";
    std::cout << "limit=" << limit << "\n" << std::endl;

    std::cout << "Found " << events.size() << " events:\n" << std::endl;

    int count = 0;
    for (const auto& evt : events) {
        std::cout << " " << std::setw(20) << std::left << evt.event_id
                  << " | " << std::setw(10) << evt.classification
                  << " | disc: " << std::fixed << std::setprecision(3)
                  << evt.discrepancy_score << std::endl;

        if (++count >= 20) {
            std::cout << "\n(Showing first 20 of " << events.size() << " results)" << std::endl;
            break;
        }
    }

    std::cout << std::endl;
}

    void RagCommandManager::showHelp() const {
    std::cout << "\n🔍 RAG COMMANDS:" << std::endl;
    std::cout << "  rag query_similar <event_id> [--explain]         - Find similar events" << std::endl;
    std::cout << "  rag recent [--limit N]                           - Show N recent events (default: 10)" << std::endl;
    std::cout << "  rag search [--classification C] [--discrepancy-min X] - Search events" << std::endl;
    std::cout << "  rag list [BENIGN|MALICIOUS]                      - List events by type" << std::endl;
    std::cout << "  rag stats                                        - Show dataset statistics" << std::endl;
    std::cout << "  rag info                                         - Show FAISS index info" << std::endl;
    std::cout << "  rag help                                         - Show this help" << std::endl;
}

} // namespace Rag