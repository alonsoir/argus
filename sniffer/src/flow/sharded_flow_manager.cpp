// Day 44 - FIX #3: Thread-safe API implementation

#include "flow/sharded_flow_manager_fix3.hpp"
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
        std::cout << "  Flow timeout: " << config_.flow_timeout_ns / 1'000'000'000 << " seconds" << std::endl;
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

    shard.last_seen_ns.store(now_ns(), std::memory_order_relaxed);

    auto it = shard.flows->find(key);

    if (it == shard.flows->end()) {
        // New flow
        if (shard.flows->size() >= config_.max_flows_per_shard) {
            if (!shard.lru_queue->empty()) {
                FlowKey evict_key = shard.lru_queue->back();
                shard.lru_queue->pop_back();
                shard.flows->erase(evict_key);
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
        it->second.stats.add_packet(event, key);
        
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
std::optional<FlowStatistics> ShardedFlowManager::get_flow_stats_copy(const FlowKey& key) const {
    if (!initialized_.load(std::memory_order_acquire)) {
        return std::nullopt;
    }

    size_t shard_id = get_shard_id(key);
    auto& shard = *shards_[shard_id];

    std::unique_lock lock(*shard.mutex);

    auto it = shard.flows->find(key);
    if (it != shard.flows->end()) {
        // Create copy manually (FlowStatistics has unique_ptr members)
        FlowStatistics copy;
        
        // Copy primitive fields
        copy.flow_start_ns = it->second.stats.flow_start_ns;
        copy.flow_last_seen_ns = it->second.stats.flow_last_seen_ns;
        copy.spkts = it->second.stats.spkts;
        copy.dpkts = it->second.stats.dpkts;
        copy.sbytes = it->second.stats.sbytes;
        copy.dbytes = it->second.stats.dbytes;
        
        // Copy vectors
        copy.fwd_lengths = it->second.stats.fwd_lengths;
        copy.bwd_lengths = it->second.stats.bwd_lengths;
        copy.all_lengths = it->second.stats.all_lengths;
        copy.packet_timestamps = it->second.stats.packet_timestamps;
        copy.fwd_timestamps = it->second.stats.fwd_timestamps;
        copy.bwd_timestamps = it->second.stats.bwd_timestamps;
        
        // Copy TCP flags
        copy.fin_count = it->second.stats.fin_count;
        copy.syn_count = it->second.stats.syn_count;
        copy.rst_count = it->second.stats.rst_count;
        copy.psh_count = it->second.stats.psh_count;
        copy.ack_count = it->second.stats.ack_count;
        copy.urg_count = it->second.stats.urg_count;
        copy.ece_count = it->second.stats.ece_count;
        copy.cwr_count = it->second.stats.cwr_count;
        copy.fwd_psh_flags = it->second.stats.fwd_psh_flags;
        copy.bwd_psh_flags = it->second.stats.bwd_psh_flags;
        copy.fwd_urg_flags = it->second.stats.fwd_urg_flags;
        copy.bwd_urg_flags = it->second.stats.bwd_urg_flags;
        
        // Copy header lengths
        copy.fwd_header_lengths = it->second.stats.fwd_header_lengths;
        copy.sum_all_lengths = it->second.stats.sum_all_lengths;  // [DDOS-SNAP-D290]
        copy.len_hist = it->second.stats.len_hist;
        copy.bwd_header_lengths = it->second.stats.bwd_header_lengths;
        
        // time_windows will be created by FlowStatistics() constructor
        
        return std::make_optional(std::move(copy));
    }
    return std::nullopt;
}

size_t ShardedFlowManager::cleanup_expired_flows(uint64_t current_ns) {
    if (!initialized_.load(std::memory_order_acquire)) {
        return 0;
    }

    size_t total_cleaned = 0;

    for (auto& shard_ptr : shards_) {
        auto& shard = *shard_ptr;
        std::unique_lock lock(*shard.mutex);

        auto it = shard.flows->begin();
        while (it != shard.flows->end()) {
            if (it->second.stats.should_expire(current_ns, config_.flow_timeout_ns)) {
                shard.lru_queue->remove(it->first);
                it = shard.flows->erase(it);
                ++total_cleaned;
            } else {
                ++it;
            }
        }
    }

    return total_cleaned;
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
