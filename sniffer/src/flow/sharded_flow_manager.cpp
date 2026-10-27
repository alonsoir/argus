// Day 44 - FIX #3: Thread-safe API implementation

#include "flow/sharded_flow_manager.hpp"
#include <iostream>
#include <chrono>

namespace sniffer::flow {

ShardedFlowManager& ShardedFlowManager::instance() {
    static ShardedFlowManager instance;
    return instance;
}

void ShardedFlowManager::initialize(const Config& config) {
    std::call_once(init_flag_, [this, &config]() {
        config_ = config;
        shards_.resize(config_.shard_count);
        
        for (size_t i = 0; i < config_.shard_count; ++i) {
            shards_[i] = std::make_unique<Shard>();
            shards_[i]->flows = std::make_unique<std::unordered_map<FlowKey, FlowEntry, FlowKey::Hash>>();
            shards_[i]->lru_queue = std::make_unique<std::list<FlowKey>>();
            shards_[i]->mutex = std::make_unique<std::mutex>();
        }
        
        initialized_.store(true, std::memory_order_release);
        
        std::cout << "[ShardedFlowManager] Initialized:" << std::endl;
        std::cout << "  Shard count: " << config_.shard_count << std::endl;
        std::cout << "  Max flows per shard: " << config_.max_flows_per_shard << std::endl;
        std::cout << "  Idle timeout: " << config_.idle_timeout_ns / 1'000'000'000 << " seconds" << std::endl;
        std::cout << "  Active timeout: " << config_.active_timeout_ns / 1'000'000'000 << " seconds"
                  << (config_.active_timeout_ns == 0 ? " (sin tope)" : "") << std::endl;
        std::cout << "  Total capacity: " << config_.shard_count * config_.max_flows_per_shard << " flows" << std::endl;
    });
}

size_t ShardedFlowManager::get_shard_id(const FlowKey& key) const {
    FlowKey::Hash hasher;
    return hasher(key) % config_.shard_count;
}

uint64_t ShardedFlowManager::now_ns() const {
    return std::chrono::duration_cast<std::chrono::nanoseconds>(
        std::chrono::steady_clock::now().time_since_epoch()
    ).count();
}

void ShardedFlowManager::add_packet(const FlowKey& key, const SimpleEvent& event) {
    if (!initialized_.load(std::memory_order_acquire)) {
        std::cerr << "[ShardedFlowManager] ERROR: Not initialized!" << std::endl;
        return;
    }

    size_t shard_id = get_shard_id(key);
    auto& shard = *shards_[shard_id];

    std::unique_lock lock(*shard.mutex);

    const uint64_t ahora = now_ns();
    shard.last_seen_ns.store(ahora, std::memory_order_relaxed);
    // [FLOW-TABLE-D308] marca del paquete posterior a la hora de la tabla: los dos relojes no son la misma base
    if (event.timestamp > ahora) marcas_futuras_.fetch_add(1, std::memory_order_relaxed);

    auto it = shard.flows->find(key);

    if (it == shard.flows->end()) {
        // New flow
        if (shard.flows->size() >= config_.max_flows_per_shard) {
            if (!shard.lru_queue->empty()) {
                FlowKey evict_key = shard.lru_queue->back();
                shard.lru_queue->pop_back();
                shard.flows->erase(evict_key);
                desalojos_lru_.fetch_add(1, std::memory_order_relaxed);  // [FLOW-TABLE-D308] antes, en silencio
            }
        }

        FlowEntry entry;
        entry.stats.add_packet(event, key);
        
        // FIX #2: O(1) LRU with iterator
        shard.lru_queue->push_front(key);
        entry.lru_pos = shard.lru_queue->begin();
        
        (*shard.flows)[key] = std::move(entry);

    } else {
        // Existing flow
        // [FLOW-TABLE-D308] Tope de duracion activa (0 = sin tope), con marcas de paquete: si el flujo ya dura el
        // tope, se cierra (estado a cero) y este paquete abre el flujo nuevo con la misma clave. O(1), sin recorrer.
        auto& st = it->second.stats;
        if (config_.active_timeout_ns > 0 && event.timestamp >= st.flow_start_ns &&
            event.timestamp - st.flow_start_ns >= config_.active_timeout_ns) {
            st = FlowStatistics{};
            cortes_tope_.fetch_add(1, std::memory_order_relaxed);
        }
        st.add_packet(event, key);
        
        // FIX #2: O(1) LRU update using splice
        shard.lru_queue->splice(
            shard.lru_queue->begin(),
            *shard.lru_queue,
            it->second.lru_pos
        );
        it->second.lru_pos = shard.lru_queue->begin();
    }
}

// FIX #3: NEW - Thread-safe copy (reads inside lock)
// [D308-PASO1] Copia del nucleo de tamano fijo, de una vez y O(1): sin vectores que crezcan con el flujo y sin
// la copia a mano campo a campo (un campo nuevo no se puede perder, DEBT-FLOWSTATS-COPY-AMPUTATED-001). El
// histograma de longitudes no viaja: solo lo lee la foto DDoS v2 dentro del lock (with_flow_stats).
std::optional<FlowStatsCore> ShardedFlowManager::get_flow_stats_copy(const FlowKey& key) const {
    if (!initialized_.load(std::memory_order_acquire)) {
        return std::nullopt;
    }

    size_t shard_id = get_shard_id(key);
    auto& shard = *shards_[shard_id];

    std::unique_lock lock(*shard.mutex);

    auto it = shard.flows->find(key);
    if (it != shard.flows->end()) {
        return std::make_optional<FlowStatsCore>(static_cast<const FlowStatsCore&>(it->second.stats));
    }
    return std::nullopt;
}

// [FLOW-TABLE-D308] Desde la cola de la LRU de cada shard (el flujo cuyo ultimo paquete llego hace mas): mientras la
// cola este caducada, se borra (O(1) por flujo); se para en la primera que no lo este. Coste O(caducados + shards) y
// cada lock solo mientras se borra lo de su shard (antes: recorria todos los flujos y borraba de la LRU con
// list::remove, O(n) por borrado; medido DAY308: 6 s con 72 000 caducados en el defender). La LRU ordena por
// llegada, no por marca: con marcas desordenadas un caducado puede esperar a una pasada posterior.
size_t ShardedFlowManager::cleanup_expired_flows(uint64_t current_ns) {
    if (!initialized_.load(std::memory_order_acquire)) {
        return 0;
    }

    size_t total_cleaned = 0;
    uint64_t max_us = 0;

    for (auto& shard_ptr : shards_) {
        auto& shard = *shard_ptr;
        const auto t0 = std::chrono::steady_clock::now();
        {
            std::unique_lock lock(*shard.mutex);
            while (!shard.lru_queue->empty()) {
                auto it = shard.flows->find(shard.lru_queue->back());
                if (it == shard.flows->end()) {  // no deberia pasar: la LRU y la tabla van juntas
                    shard.lru_queue->pop_back();
                    continue;
                }
                if (!it->second.stats.should_expire(current_ns, config_.idle_timeout_ns)) {
                    break;
                }
                shard.flows->erase(it);
                shard.lru_queue->pop_back();
                ++total_cleaned;
            }
        }
        const uint64_t us = static_cast<uint64_t>(
            std::chrono::duration_cast<std::chrono::microseconds>(std::chrono::steady_clock::now() - t0).count());
        if (us > max_us) max_us = us;
    }

    caducados_.fetch_add(total_cleaned, std::memory_order_relaxed);
    uint64_t previo = max_lock_us_.load(std::memory_order_relaxed);
    while (max_us > previo && !max_lock_us_.compare_exchange_weak(previo, max_us, std::memory_order_relaxed)) {
    }
    return total_cleaned;
}

ShardedFlowManager::Counters ShardedFlowManager::take_counters() {
    Counters c;
    c.caducados = caducados_.exchange(0, std::memory_order_relaxed);
    c.cortes_tope = cortes_tope_.exchange(0, std::memory_order_relaxed);
    c.desalojos_lru = desalojos_lru_.exchange(0, std::memory_order_relaxed);
    c.marcas_futuras = marcas_futuras_.exchange(0, std::memory_order_relaxed);
    c.max_lock_us = max_lock_us_.exchange(0, std::memory_order_relaxed);
    if (initialized_.load(std::memory_order_acquire)) {
        for (const auto& shard_ptr : shards_) {
            std::unique_lock lock(*shard_ptr->mutex);
            c.vivos += shard_ptr->flows->size();
        }
    }
    return c;
}

void ShardedFlowManager::print_stats() const {
    if (!initialized_.load(std::memory_order_acquire)) {
        std::cout << "[ShardedFlowManager] Not initialized" << std::endl;
        return;
    }

    size_t total_flows = 0;
    for (const auto& shard_ptr : shards_) {
        auto& shard = *shard_ptr;
        std::unique_lock lock(*shard.mutex);
        total_flows += shard.flows->size();
    }

    std::cout << "[ShardedFlowManager] Stats:" << std::endl;
    std::cout << "  Active flows: " << total_flows << std::endl;
    std::cout << "  Shards: " << config_.shard_count << std::endl;
}

ShardedFlowManager::~ShardedFlowManager() {
    if (!initialized_.load(std::memory_order_acquire)) {
        return;
    }

    size_t total_flows = 0;
    for (auto& shard_ptr : shards_) {
        auto& shard = *shard_ptr;
        std::unique_lock lock(*shard.mutex);
        total_flows += shard.flows->size();
        shard.flows->clear();
        shard.lru_queue->clear();
    }

    if (total_flows > 0) {
        std::cout << "[ShardedFlowManager] Cleaned up " << total_flows << " flows" << std::endl;
    }
}

} // namespace sniffer::flow
