// /vagrant/rag/include/common/embedding_cache.hpp
#pragma once

#include <unordered_map>
#include <vector>
#include <string>
#include <mutex>
#include <chrono>
#include <optional>

namespace rag {

/**
 * @brief Cache thread-safe con TTL para embeddings
 *
 * Via Appia Quality:
 * - Simple (no dependencies externas)
 * - Thread-safe (std::mutex)
 * - TTL automático (eviction on get)
 * - Memory-bounded (max entries)
 *
 * Design Philosophy:
 * "Cache simple que funciona, no Redis embebido"
 *
 * Use Case:
 *   Thread 1: query "similar to event_000042"
 *   Thread 2: query "similar to event_000042" (100ms después)
 *   → Thread 2 usa cache (no regenera embeddings)
 */
template<typename KeyType = std::string,
         typename ValueType = std::vector<float>>
class EmbeddingCache {
public:
    /**
     * @brief Constructor
     *
     * @param ttl_seconds Time-to-live en segundos (default: 300s = 5min)
     * @param max_entries Máximo número de entradas (default: 1000)
     */
    explicit EmbeddingCache(
        uint32_t ttl_seconds = 300,
        size_t max_entries = 1000
    )
        : ttl_seconds_(ttl_seconds)
        , max_entries_(max_entries)
    {}

    /**
     * @brief Inserta embedding en cache
     *
     * Thread-safe: Múltiples threads pueden insertar simultáneamente
     *
     * @param key Event ID (e.g., "synthetic_000042")
     * @param value Embedding vector (e.g., 128-d chronos)
     */
    void put(const KeyType& key, const ValueType& value) {
        std::lock_guard<std::mutex> lock(mutex_);

        // Evict oldest if cache full
        if (cache_.size() >= max_entries_) {
            evict_oldest();
        }

        auto now = std::chrono::steady_clock::now();
        cache_[key] = CacheEntry{value, now};

        // Update access order (LRU)
        access_order_.push_back(key);
    }

    /**
     * @brief Obtiene embedding de cache
     *
     * Thread-safe: Múltiples threads pueden leer simultáneamente
     * Auto-eviction: Si TTL expirado, retorna nullopt
     *
     * @param key Event ID
     * @return Embedding si existe y no expiró, nullopt si no
     */
    std::optional<ValueType> get(const KeyType& key) {
        std::lock_guard<std::mutex> lock(mutex_);

        auto it = cache_.find(key);
        if (it == cache_.end()) {
            return std::nullopt;  // Cache miss
        }

        // Check TTL
        auto now = std::chrono::steady_clock::now();
        auto age = std::chrono::duration_cast<std::chrono::seconds>(
            now - it->second.timestamp
        ).count();

        if (age > ttl_seconds_) {
            // Expired, evict
            cache_.erase(it);
            return std::nullopt;
        }

        // Cache hit
        return it->second.value;
    }

    /**
     * @brief Limpia cache completamente
     *
     * Thread-safe
     */
    void clear() {
        std::lock_guard<std::mutex> lock(mutex_);
        cache_.clear();
        access_order_.clear();
    }

    /**
     * @brief Retorna estadísticas de cache (para logging)
     *
     * Thread-safe
     */
    struct Stats {
        size_t size;
        size_t max_entries;
        uint32_t ttl_seconds;
    };

    Stats stats() const {
        std::lock_guard<std::mutex> lock(mutex_);
        return Stats{
            cache_.size(),
            max_entries_,
            ttl_seconds_
        };
    }

private:
    struct CacheEntry {
        ValueType value;
        std::chrono::steady_clock::time_point timestamp;
    };

    void evict_oldest() {
        // Evict first entry in access order (LRU)
        if (!access_order_.empty()) {
            auto oldest_key = access_order_.front();
            cache_.erase(oldest_key);
            access_order_.erase(access_order_.begin());
        }
    }

    mutable std::mutex mutex_;
    std::unordered_map<KeyType, CacheEntry> cache_;
    std::vector<KeyType> access_order_;  // LRU tracking
    uint32_t ttl_seconds_;
    size_t max_entries_;
};

/**
 * @brief Cache manager para múltiples embedders
 *
 * Cada embedder (chronos, sbert, attack) tiene su propio cache.
 * Thread-safe: Múltiples queries pueden acceder simultáneamente.
 */
class EmbedderCacheManager {
public:
    EmbedderCacheManager(
        uint32_t ttl_seconds = 300,
        size_t max_entries = 1000
    )
        : chronos_cache_(ttl_seconds, max_entries)
        , sbert_cache_(ttl_seconds, max_entries)
        , attack_cache_(ttl_seconds, max_entries)
    {}

    // Chronos cache
    void put_chronos(const std::string& event_id,
                     const std::vector<float>& embedding) {
        chronos_cache_.put(event_id, embedding);
    }

    std::optional<std::vector<float>> get_chronos(
        const std::string& event_id
    ) {
        return chronos_cache_.get(event_id);
    }

    // SBERT cache
    void put_sbert(const std::string& event_id,
                   const std::vector<float>& embedding) {
        sbert_cache_.put(event_id, embedding);
    }

    std::optional<std::vector<float>> get_sbert(
        const std::string& event_id
    ) {
        return sbert_cache_.get(event_id);
    }

    // Attack cache
    void put_attack(const std::string& event_id,
                    const std::vector<float>& embedding) {
        attack_cache_.put(event_id, embedding);
    }

    std::optional<std::vector<float>> get_attack(
        const std::string& event_id
    ) {
        return attack_cache_.get(event_id);
    }

    // Clear all caches
    void clear_all() {
        chronos_cache_.clear();
        sbert_cache_.clear();
        attack_cache_.clear();
    }

    // Stats para logging
    struct CombinedStats {
        EmbeddingCache<>::Stats chronos;
        EmbeddingCache<>::Stats sbert;
        EmbeddingCache<>::Stats attack;
    };

    CombinedStats stats() const {
        return CombinedStats{
            chronos_cache_.stats(),
            sbert_cache_.stats(),
            attack_cache_.stats()
        };
    }

private:
    EmbeddingCache<std::string, std::vector<float>> chronos_cache_;
    EmbeddingCache<std::string, std::vector<float>> sbert_cache_;
    EmbeddingCache<std::string, std::vector<float>> attack_cache_;
};

} // namespace rag