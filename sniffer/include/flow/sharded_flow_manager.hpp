// Day 44 - FIX #3: Thread-safe API (no raw pointers)
// Eliminates ALL data races by never exposing unprotected pointers

#pragma once

#include "flow_manager.hpp"
#include <memory>
#include <mutex>
#include <atomic>
#include <list>
#include <optional>
#include <functional>

namespace sniffer::flow {

class ShardedFlowManager {
public:
    struct Config {
        size_t shard_count = 4;
        size_t max_flows_per_shard = 200;
        uint64_t flow_timeout_ns = 120'000'000'000ULL;
    };

    static ShardedFlowManager& instance();

    void initialize(const Config& config);
    void add_packet(const FlowKey& key, const SimpleEvent& event);
    
    // REMOVED: get_flow_stats() - returned unprotected pointer (data race)
    // REMOVED: get_flow_stats_mut() - returned unprotected pointer (data race)
    
    // NEW: Thread-safe API - returns copy inside lock
    std::optional<FlowStatistics> get_flow_stats_copy(const FlowKey& key) const;
    
    // NEW: Thread-safe API - executes callback inside lock
    template<typename Func>
    void with_flow_stats(const FlowKey& key, Func&& func) const {
        if (!initialized_.load(std::memory_order_acquire)) {
            return;
        }
        
        size_t shard_id = get_shard_id(key);
        auto& shard = *shards_[shard_id];
        
        std::unique_lock lock(*shard.mutex);
        
        auto it = shard.flows->find(key);
        if (it != shard.flows->end()) {
            func(it->second.stats);  // Callback ejecuta DENTRO del lock
        }
    }
    
    // DAY 219 — HALLAZGO 2 (DAY 218): el singleton NO podia vaciarse.
    // initialize() usa std::call_once => la 2a llamada es un NO-OP MUDO:
    // ni reconstruye shards, ni limpia flujos, ni aplica la Config nueva
    // (la del PRIMER initialize() gana, en silencio).
    // Resultado: los tests de un mismo binario COMPARTEN flujos. 3+4+3=10.
    // Un FlowManager que no puede volver a un estado conocido no es medible.
    void clear();

    size_t cleanup_expired_flows(uint64_t current_ns);
    void print_stats() const;

    ~ShardedFlowManager();

private:
    ShardedFlowManager() = default;

    struct FlowEntry {
        FlowStatistics stats;
        std::list<FlowKey>::iterator lru_pos;  // FIX #2: O(1) LRU
    };

    struct Shard {
        std::unique_ptr<std::unordered_map<FlowKey, FlowEntry, FlowKey::Hash>> flows;
        std::unique_ptr<std::list<FlowKey>> lru_queue;
        std::unique_ptr<std::mutex> mutex;
        std::atomic<uint64_t> last_seen_ns{0};
    };

    std::vector<std::unique_ptr<Shard>> shards_;
    Config config_;
    
    // FIX #1: Thread-safe initialization
    std::once_flag init_flag_;
    std::atomic<bool> initialized_{false};

    size_t get_shard_id(const FlowKey& key) const;
    uint64_t now_ns() const;
};

} // namespace sniffer::flow
