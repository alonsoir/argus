#pragma once

#include <memory>
#include <vector>

namespace faiss {
    class Index;
}

namespace rag_ingester {

class MultiIndexManager {
public:
    MultiIndexManager();
    ~MultiIndexManager();
    
    void add_chronos(const std::vector<float>& embeddings);
    void add_sbert(const std::vector<float>& embeddings);
    void add_entity_benign(const std::vector<float>& embeddings);
    void add_entity_malicious(const std::vector<float>& embeddings);
    
    void save_all(const std::string& path);
    void load_all(const std::string& path);

    // Day 40: Getters para save_indices_to_disk()
    faiss::Index& get_chronos_index() {
        if (!chronos_index_) {
            throw std::runtime_error("Chronos index not initialized");
        }
        return *chronos_index_;
    }

    faiss::Index& get_sbert_index() {
        if (!sbert_index_) {
            throw std::runtime_error("SBERT index not initialized");
        }
        return *sbert_index_;
    }

    faiss::Index& get_entity_malicious_index() {
        if (!entity_malicious_index_) {
            throw std::runtime_error("Entity malicious index not initialized");
        }
        return *entity_malicious_index_;
    }
    
private:
    std::unique_ptr<faiss::Index> chronos_index_;
    std::unique_ptr<faiss::Index> sbert_index_;
    std::unique_ptr<faiss::Index> entity_benign_index_;
    std::unique_ptr<faiss::Index> entity_malicious_index_;
};

} // namespace rag_ingester
