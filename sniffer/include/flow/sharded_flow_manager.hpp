// Day 44 - FIX #3: Thread-safe API (no raw pointers)
// Eliminates ALL data races by never exposing unprotected pointers

#pragma once

#include "flow_manager.hpp"
#include "flow_table_params.hpp"  // [FLOW-TABLE-D308] defectos de la tabla, un solo sitio
#include <memory>
#include <mutex>
#include <atomic>
#include <list>
#include <optional>
#include <functional>

namespace sniffer::flow {

class ShardedFlowManager {
public:
    // [FLOW-TABLE-D308] Mismos defectos que flow_table_config.hpp (y que sniffer.json). En el sniffer la rellena
    // ring_consumer desde la seccion flow_table del JSON.
    struct Config {
        size_t shard_count = ::argus::flowtable::FlowTableParams{}.shards;
        size_t max_flows_per_shard = ::argus::flowtable::FlowTableParams{}.max_flows_per_shard;
        uint64_t idle_timeout_ns = ::argus::flowtable::FlowTableParams{}.idle_timeout_s * 1'000'000'000ULL;
        uint64_t active_timeout_ns = 0;  // 0 = sin tope de duracion activa
    };

    // [FLOW-TABLE-D308] Contadores desde la ultima toma (take_counters los devuelve y los pone a cero), salvo
    // 'vivos' (flujos en la tabla en el momento de la toma).
    struct Counters {
        uint64_t caducados = 0;       // borrados por la limpieza por inactividad
        uint64_t cortes_tope = 0;     // flujos reiniciados por el tope de duracion activa
        uint64_t desalojos_lru = 0;   // flujos echados por la LRU al llegar uno nuevo con el shard lleno
        uint64_t marcas_futuras = 0;  // paquetes con marca posterior a la hora de la tabla (relojes distintos)
        uint64_t max_lock_us = 0;     // mayor tiempo con el lock de un shard tomado en la limpieza
        size_t vivos = 0;
    };

    static ShardedFlowManager& instance();

    void initialize(const Config& config);
    void add_packet(const FlowKey& key, const SimpleEvent& event);
    
    // REMOVED: get_flow_stats() - returned unprotected pointer (data race)
    // REMOVED: get_flow_stats_mut() - returned unprotected pointer (data race)
    
    // NEW: Thread-safe API - returns copy inside lock
    // [D308-PASO1] copia del nucleo de tamano fijo (sin el histograma de longitudes)
    std::optional<FlowStatsCore> get_flow_stats_copy(const FlowKey& key) const;
    
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
    
    // [FLOW-TABLE-D308] Limpieza por inactividad desde la cola de la LRU de cada shard: O(caducados). current_ns en
    // la misma base que las marcas de los paquetes (CLOCK_MONOTONIC: bpf_ktime_get_ns y steady_clock).
    size_t cleanup_expired_flows(uint64_t current_ns);
    Counters take_counters();
    uint64_t now_ns() const;
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

    // [FLOW-TABLE-D308] contadores (relajados: solo se leen en la linea [FLOW-TABLE])
    std::atomic<uint64_t> caducados_{0};
    std::atomic<uint64_t> cortes_tope_{0};
    std::atomic<uint64_t> desalojos_lru_{0};
    std::atomic<uint64_t> marcas_futuras_{0};
    std::atomic<uint64_t> max_lock_us_{0};
    
    // FIX #1: Thread-safe initialization
    std::once_flag init_flag_;
    std::atomic<bool> initialized_{false};

    size_t get_shard_id(const FlowKey& key) const;
};

} // namespace sniffer::flow
