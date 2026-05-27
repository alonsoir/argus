#include "indexers/multi_index_manager.hpp"
#include <faiss/IndexFlat.h>  // ← AGREGADO
#include <spdlog/spdlog.h>

namespace rag_ingester {

MultiIndexManager::MultiIndexManager() {
    // Crear 4 índices FAISS
    chronos_index_ = std::make_unique<faiss::IndexFlatL2>(128);
    sbert_index_ = std::make_unique<faiss::IndexFlatL2>(96);
    entity_benign_index_ = std::make_unique<faiss::IndexFlatL2>(64);
    entity_malicious_index_ = std::make_unique<faiss::IndexFlatL2>(64);
    
    spdlog::info("MultiIndexManager initialized with 4 indices:");
    spdlog::info("  - Chronos: 128-d");
    spdlog::info("  - SBERT: 96-d");
    spdlog::info("  - Entity Benign: 64-d");
    spdlog::info("  - Entity Malicious: 64-d");
}

MultiIndexManager::~MultiIndexManager() {
    spdlog::info("MultiIndexManager destroyed");
}

void MultiIndexManager::add_chronos(const std::vector<float>& embeddings) {
    if (embeddings.size() % 128 != 0) {
        spdlog::error("Invalid chronos embedding size: {}", embeddings.size());
        return;
    }
    
    size_t n = embeddings.size() / 128;
    chronos_index_->add(n, embeddings.data());
    spdlog::debug("Added {} vectors to chronos index (total: {})", 
                 n, chronos_index_->ntotal);
}

void MultiIndexManager::add_sbert(const std::vector<float>& embeddings) {
    if (embeddings.size() % 96 != 0) {
        spdlog::error("Invalid sbert embedding size: {}", embeddings.size());
        return;
    }
    
    size_t n = embeddings.size() / 96;
    sbert_index_->add(n, embeddings.data());
    spdlog::debug("Added {} vectors to sbert index (total: {})", 
                 n, sbert_index_->ntotal);
}

void MultiIndexManager::add_entity_benign(const std::vector<float>& embeddings) {
    if (embeddings.size() % 64 != 0) {
        spdlog::error("Invalid entity benign embedding size: {}", embeddings.size());
        return;
    }
    
    size_t n = embeddings.size() / 64;
    entity_benign_index_->add(n, embeddings.data());
    spdlog::debug("Added {} vectors to entity benign index (total: {})", 
                 n, entity_benign_index_->ntotal);
}

void MultiIndexManager::add_entity_malicious(const std::vector<float>& embeddings) {
    if (embeddings.size() % 64 != 0) {
        spdlog::error("Invalid entity malicious embedding size: {}", embeddings.size());
        return;
    }
    
    size_t n = embeddings.size() / 64;
    entity_malicious_index_->add(n, embeddings.data());
    spdlog::debug("Added {} vectors to entity malicious index (total: {})", 
                 n, entity_malicious_index_->ntotal);
}

void MultiIndexManager::save_all(const std::string& path) {
    spdlog::info("TODO: save_all() to {}", path);
    // TODO: Implementar persistencia
}

void MultiIndexManager::load_all(const std::string& path) {
    spdlog::info("TODO: load_all() from {}", path);
    // TODO: Implementar carga
}

} // namespace rag_ingester
