// /vagrant/rag/include/embedders/cached_embedder.hpp
#pragma once

#include "embedder_interface.hpp"
#include "common/embedding_cache.hpp"
#include <memory>
#include <atomic>
#include <iostream>

namespace rag {

/**
 * @brief Wrapper con cache TTL sobre IEmbedder
 *
 * NOTA: Versión simplificada sin spdlog por ahora
 * Usa std::cout para logging
 */
class CachedEmbedder : public IEmbedder {
public:
    CachedEmbedder(
        std::unique_ptr<IEmbedder> embedder,
        uint32_t ttl_seconds = 300,
        size_t max_entries = 1000
    )
        : embedder_(std::move(embedder))
        , cache_manager_(ttl_seconds, max_entries)
        , cache_hits_(0)
        , cache_misses_(0)
    {
        std::cout << "[CachedEmbedder] Initialized:" << std::endl;
        std::cout << "  Underlying: " << embedder_->name() << std::endl;
        std::cout << "  TTL: " << ttl_seconds << "s" << std::endl;
        std::cout << "  Max entries: " << max_entries << std::endl;
    }

    // IEmbedder interface con cache (versión vector<float>)
    std::vector<float> embed_chronos(
        const std::vector<float>& features
    ) override {
        // Crear key a partir de hash de features
        std::string key = make_key(features);

        auto cached = cache_manager_.get_chronos(key);
        if (cached) {
            ++cache_hits_;
            return *cached;
        }

        ++cache_misses_;
        auto embedding = embedder_->embed_chronos(features);
        cache_manager_.put_chronos(key, embedding);

        return embedding;
    }

    std::vector<float> embed_sbert(
        const std::vector<float>& features
    ) override {
        std::string key = make_key(features);

        auto cached = cache_manager_.get_sbert(key);
        if (cached) {
            ++cache_hits_;
            return *cached;
        }

        ++cache_misses_;
        auto embedding = embedder_->embed_sbert(features);
        cache_manager_.put_sbert(key, embedding);

        return embedding;
    }

    std::vector<float> embed_attack(
        const std::vector<float>& features
    ) override {
        std::string key = make_key(features);

        auto cached = cache_manager_.get_attack(key);
        if (cached) {
            ++cache_hits_;
            return *cached;
        }

        ++cache_misses_;
        auto embedding = embedder_->embed_attack(features);
        cache_manager_.put_attack(key, embedding);

        return embedding;
    }

    std::string name() const override {
        return "Cached(" + embedder_->name() + ")";
    }

    std::tuple<size_t, size_t, size_t> dimensions() const override {
        return embedder_->dimensions();
    }

    int effectiveness_percent() const override {
        return embedder_->effectiveness_percent();
    }

    std::string capabilities() const override {
        return embedder_->capabilities();
    }

    void clear_cache() {
        cache_manager_.clear_all();
        cache_hits_ = 0;
        cache_misses_ = 0;
    }

    struct CacheStats {
        uint64_t hits;
        uint64_t misses;
        double hit_rate;
        size_t chronos_entries;
        size_t sbert_entries;
        size_t attack_entries;
    };

    CacheStats cache_stats() const {
        auto stats = cache_manager_.stats();
        uint64_t total = cache_hits_ + cache_misses_;
        double hit_rate = total > 0
            ? (static_cast<double>(cache_hits_) / total * 100.0)
            : 0.0;

        return CacheStats{
            cache_hits_,
            cache_misses_,
            hit_rate,
            stats.chronos.size,
            stats.sbert.size,
            stats.attack.size
        };
    }

private:
    std::unique_ptr<IEmbedder> embedder_;
    EmbedderCacheManager cache_manager_;
    std::atomic<uint64_t> cache_hits_;
    std::atomic<uint64_t> cache_misses_;

    // Helper: Crear key a partir de hash de features
    std::string make_key(const std::vector<float>& features) const {
        // Simple hash: sum de primeros 5 valores
        float sum = 0.0f;
        size_t n = std::min(features.size(), size_t(5));
        for (size_t i = 0; i < n; ++i) {
            sum += features[i];
        }
        return "features_" + std::to_string(static_cast<int>(sum * 1000));
    }
};

} // namespace rag