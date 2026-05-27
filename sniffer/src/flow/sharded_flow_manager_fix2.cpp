// sniffer/src/flow/sharded_flow_manager.cpp
// Day 43 - ShardedFlowManager Implementation (unique_ptr version)
// Day 44 - FIX #1: Thread-safe initialization with std::call_once
// Day 44 - FIX #2: LRU O(1) with iterator tracking

#include "flow/sharded_flow_manager_fix2.hpp"
#include "main.h"
#include <iostream>
#include <iomanip>
#include <algorithm>

namespace sniffer {
namespace flow {

ShardedFlowManager& ShardedFlowManager::instance() {
    static ShardedFlowManager instance;
    return instance;
}

void ShardedFlowManager::initialize(const Config& config) {
    std::call_once(init_flag_, [this, &config]() {
        config_ = config;

        size_t shard_count;
        if (config_.shard_count == 0) {
            shard_count = std::max(4u, std::thread::hardware_concurrency());
        } else {
            shard_count = config_.shard_count;
        }

        shards_.reserve(shard_count);
        for (size_t i = 0; i < shard_count; ++i) {
            shards_.push_back(std::make_unique<Shard>());
        }

        std::cout << "[ShardedFlowManager] Initialized:" << std::endl;
        std::cout << "  Shard count: " << shard_count << std::endl;
        std::cout << "  Max flows per shard: " << config_.max_flows_per_shard << std::endl;
        std::cout << "  Flow timeout: " << (config_.flow_timeout_ns / 1000000000ULL) << " seconds" << std::endl;
        std::cout << "  Total capacity: " << (shard_count * config_.max_flows_per_shard) << " flows" << std::endl;

        initialized_.store(true, std::memory_order_release);
    });
}

void ShardedFlowManager::add_packet(const FlowKey& key, const SimpleEvent& event) {
    if (!initialized_.load(std::memory_order_acquire)) {
        std::cerr << "[ShardedFlowManager] ERROR: Not initialized!" << std::endl;
        return;
    }

    size_t shard_id = get_shard_id(key);
    Shard& shard = *shards_[shard_id];

    std::unique_lock lock(*shard.mtx);

    shard.last_seen_ns.store(now_ns(), std::memory_order_relaxed);

    auto it = shard.flows->find(key);

    if (it == shard.flows->end()) {
        // NEW FLOW
        if (shard.flows->size() >= config_.max_flows_per_shard) {
            if (!shard.lru_queue->empty()) {
                FlowKey evict_key = shard.lru_queue->back();
                shard.lru_queue->pop_back();
                shard.flows->erase(evict_key);
                shard.stats.flows_expired.fetch_add(1, std::memory_order_relaxed);
            }
        }

        FlowEntry entry;
        entry.stats.add_packet(event, key);
        
        // FIX #2: Store iterator for O(1) LRU access
        shard.lru_queue->push_front(key);
        entry.lru_pos = shard.lru_queue->begin();

        (*shard.flows)[key] = std::move(entry);

        shard.stats.flows_created.fetch_add(1, std::memory_order_relaxed);
        shard.stats.current_flows.store(shard.flows->size(), std::memory_order_relaxed);

    } else {
        // EXISTING FLOW - FIX #2: O(1) LRU update using splice
        shard.lru_queue->splice(
            shard.lru_queue->begin(),
            *shard.lru_queue,
            it->second.lru_pos
        );
        it->second.lru_pos = shard.lru_queue->begin();
        it->second.stats.add_packet(event, key);
    }

    shard.stats.packets_processed.fetch_add(1, std::memory_order_relaxed);
}

const FlowStatistics* ShardedFlowManager::get_flow_stats(const FlowKey& key) const {
    if (!initialized_.load(std::memory_order_acquire)) {
        return nullptr;
    }

    size_t shard_id = get_shard_id(key);
    const Shard& shard = *shards_[shard_id];

    std::shared_lock lock(*shard.mtx);

    auto it = shard.flows->find(key);

    if (it != shard.flows->end()) {
        return &it->second.stats;
    }

    return nullptr;
}

FlowStatistics* ShardedFlowManager::get_flow_stats_mut(const FlowKey& key) {
    if (!initialized_.load(std::memory_order_acquire)) {
        return nullptr;
    }

    size_t shard_id = get_shard_id(key);
    Shard& shard = *shards_[shard_id];

    std::unique_lock lock(*shard.mtx);

    auto it = shard.flows->find(key);

    if (it != shard.flows->end()) {
        return &it->second.stats;
    }

    return nullptr;
}

size_t ShardedFlowManager::cleanup_expired(std::chrono::seconds ttl) {
    if (!initialized_.load(std::memory_order_acquire)) {
        return 0;
    }

    size_t total_removed = 0;
    uint64_t now = now_ns();
    uint64_t ttl_ns = ttl.count() * 1000000000ULL;

    for (auto& shard_ptr : shards_) {
        Shard& shard = *shard_ptr;

        uint64_t last_seen = shard.last_seen_ns.load(std::memory_order_relaxed);
        if ((now - last_seen) < ttl_ns) {
            continue;
        }

        std::unique_lock lock(*shard.mtx, std::try_to_lock);
        if (!lock.owns_lock()) {
            shard.stats.cleanup_skipped.fetch_add(1, std::memory_order_relaxed);
            continue;
        }

        size_t removed = cleanup_shard_partial(shard, 100);
        total_removed += removed;

        shard.stats.current_flows.store(shard.flows->size(), std::memory_order_relaxed);
    }

    return total_removed;
}

size_t ShardedFlowManager::cleanup_all() {
    if (!initialized_.load(std::memory_order_acquire)) {
        return 0;
    }

    size_t total_removed = 0;

    for (auto& shard_ptr : shards_) {
        Shard& shard = *shard_ptr;
        std::unique_lock lock(*shard.mtx);

        size_t removed = shard.flows->size();
        shard.flows->clear();
        shard.lru_queue->clear();

        total_removed += removed;

        shard.stats.flows_expired.fetch_add(removed, std::memory_order_relaxed);
        shard.stats.current_flows.store(0, std::memory_order_relaxed);
    }

    std::cout << "[ShardedFlowManager] Cleaned up " << total_removed << " flows" << std::endl;

    return total_removed;
}

size_t ShardedFlowManager::cleanup_shard_partial(Shard& shard, size_t max_remove) {
    uint64_t now = now_ns();
    uint64_t timeout_ns = config_.flow_timeout_ns;
    size_t removed = 0;

    // FIX #2: Iterate LRU back → front (oldest first)
    while (removed < max_remove && !shard.lru_queue->empty()) {
        FlowKey key = shard.lru_queue->back();
        auto it = shard.flows->find(key);

        if (it != shard.flows->end()) {
            const FlowEntry& entry = it->second;
            if (entry.stats.should_expire(now, timeout_ns)) {
                shard.lru_queue->pop_back();
                shard.flows->erase(it);
                removed++;
                shard.stats.flows_expired.fetch_add(1, std::memory_order_relaxed);
            } else {
                break;  // LRU ordered → if oldest not expired, stop
            }
        } else {
            // Inconsistency - remove from LRU
            shard.lru_queue->pop_back();
        }
    }

    return removed;
}

ShardedFlowManager::GlobalStats ShardedFlowManager::get_stats() const {
    GlobalStats stats;
    stats.shard_count = shards_.size();

    for (const auto& shard_ptr : shards_) {
        const Shard& shard = *shard_ptr;

        stats.total_flows_created += shard.stats.flows_created.load(std::memory_order_relaxed);
        stats.total_flows_expired += shard.stats.flows_expired.load(std::memory_order_relaxed);
        stats.total_packets_processed += shard.stats.packets_processed.load(std::memory_order_relaxed);
        stats.total_active_flows += shard.stats.current_flows.load(std::memory_order_relaxed);
        stats.total_lock_contentions += shard.stats.lock_contentions.load(std::memory_order_relaxed);
        stats.total_cleanup_skipped += shard.stats.cleanup_skipped.load(std::memory_order_relaxed);
    }

    return stats;
}

void ShardedFlowManager::print_stats() const {
    auto stats = get_stats();

    std::cout << "\n╔═══════════════════════════════════════════════════════╗\n";
    std::cout << "║  ShardedFlowManager Statistics                        ║\n";
    std::cout << "╚═══════════════════════════════════════════════════════╝\n";
    std::cout << "\n📊 Global Statistics:\n";
    std::cout << "  Shard count: " << stats.shard_count << "\n";
    std::cout << "  Total flows created: " << stats.total_flows_created << "\n";
    std::cout << "  Total flows expired: " << stats.total_flows_expired << "\n";
    std::cout << "  Active flows: " << stats.total_active_flows << "\n";
    std::cout << "  Total packets processed: " << stats.total_packets_processed << "\n";
    std::cout << "  Lock contentions: " << stats.total_lock_contentions << "\n";
    std::cout << "  Cleanup skipped: " << stats.total_cleanup_skipped << "\n";

    if (stats.total_flows_created > 0) {
        double avg_packets = static_cast<double>(stats.total_packets_processed) /
                            static_cast<double>(stats.total_flows_created);
        std::cout << "  Average packets per flow: " << std::fixed << std::setprecision(2)
                  << avg_packets << "\n";
    }

    std::cout << "╚═══════════════════════════════════════════════════════╝\n";
}

void ShardedFlowManager::reset_stats() {
    for (auto& shard_ptr : shards_) {
        Shard& shard = *shard_ptr;
        shard.stats.flows_created.store(0, std::memory_order_relaxed);
        shard.stats.flows_expired.store(0, std::memory_order_relaxed);
        shard.stats.packets_processed.store(0, std::memory_order_relaxed);
        shard.stats.lock_contentions.store(0, std::memory_order_relaxed);
        shard.stats.cleanup_skipped.store(0, std::memory_order_relaxed);
    }

    std::cout << "[ShardedFlowManager] Statistics reset" << std::endl;
}

} // namespace flow
} // namespace sniffer
