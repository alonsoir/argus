// sniffer/src/userspace/flow_manager.cpp
#include "flow_manager.hpp"
#include <iostream>
#include <iomanip>
#include <arpa/inet.h>

namespace sniffer {

FlowManager::FlowManager(const Config& config)
    : config_(config) {

    std::cout << "[FlowManager] Initialized with:" << std::endl;
    std::cout << "  Flow timeout: " << (config_.flow_timeout_ns / 1'000'000'000ULL) << " seconds" << std::endl;
    std::cout << "  Max flows: " << config_.max_flows << std::endl;
    std::cout << "  Auto-export on TCP close: " << (config_.auto_export_on_tcp_close ? "yes" : "no") << std::endl;
}

FlowManager::~FlowManager() {
    expire_all_flows();
}

FlowKey FlowManager::create_flow_key(const SimpleEvent& pkt) const {
    FlowKey key;

    // For bidirectional flow tracking, we normalize the 5-tuple
    // Use src < dst to create canonical key
    bool forward = (pkt.src_ip < pkt.dst_ip) ||
                   (pkt.src_ip == pkt.dst_ip && pkt.src_port < pkt.dst_port);

    if (forward) {
        key.src_ip = pkt.src_ip;
        key.dst_ip = pkt.dst_ip;
        key.src_port = pkt.src_port;
        key.dst_port = pkt.dst_port;
    } else {
        // Reverse direction - swap src/dst
        key.src_ip = pkt.dst_ip;
        key.dst_ip = pkt.src_ip;
        key.src_port = pkt.dst_port;
        key.dst_port = pkt.src_port;
    }

    key.protocol = pkt.protocol;

    return key;
}

void FlowManager::add_packet(const SimpleEvent& pkt) {
    std::lock_guard<std::mutex> lock(flows_mutex_);

    // Create flow key
    FlowKey key = create_flow_key(pkt);

    // Update statistics
    if (config_.enable_statistics) {
        stats_.total_packets_processed++;
    }

    // Find or create flow
    auto it = active_flows_.find(key);

    if (it == active_flows_.end()) {
        // New flow
        if (active_flows_.size() >= config_.max_flows) {
            std::cerr << "[FlowManager] WARNING: Max flows reached ("
                      << config_.max_flows << "), dropping packet" << std::endl;
            return;
        }

        FlowStatistics flow_stats;
        flow_stats.add_packet(pkt, key);
        active_flows_[key] = std::move(flow_stats);

        if (config_.enable_statistics) {
            stats_.total_flows_created++;
            stats_.active_flows = active_flows_.size();
        }

    } else {
        // Existing flow
        it->second.add_packet(pkt, key);

        // Auto-export on TCP close
        if (config_.auto_export_on_tcp_close && should_auto_export(it->second)) {
            export_flow(key, it->second);
            active_flows_.erase(it);

            if (config_.enable_statistics) {
                stats_.flows_expired_tcp_close++;
                stats_.total_flows_expired++;
                stats_.active_flows = active_flows_.size();
            }
        }
    }
}

bool FlowManager::should_auto_export(const FlowStatistics& stats) const {
    // Export TCP flows when connection is closed (FIN or RST)
    return stats.is_tcp() && stats.is_tcp_closed();
}

size_t FlowManager::expire_flows(uint64_t current_ns) {
    std::lock_guard<std::mutex> lock(flows_mutex_);

    size_t expired_count = 0;

    // Iterate and remove expired flows
    for (auto it = active_flows_.begin(); it != active_flows_.end(); ) {
        if (it->second.should_expire(current_ns, config_.flow_timeout_ns)) {
            export_flow(it->first, it->second);
            it = active_flows_.erase(it);
            expired_count++;
        } else {
            ++it;
        }
    }

    if (config_.enable_statistics && expired_count > 0) {
        stats_.flows_expired_timeout += expired_count;
        stats_.total_flows_expired += expired_count;
        stats_.active_flows = active_flows_.size();
    }

    return expired_count;
}

size_t FlowManager::expire_all_flows() {
    std::lock_guard<std::mutex> lock(flows_mutex_);

    size_t total = active_flows_.size();

    // Export all remaining flows
    for (const auto& [key, stats] : active_flows_) {
        export_flow(key, stats);
    }

    active_flows_.clear();

    if (config_.enable_statistics) {
        stats_.total_flows_expired += total;
        stats_.active_flows = 0;
    }

    std::cout << "[FlowManager] Expired all " << total << " remaining flows" << std::endl;

    return total;
}

void FlowManager::export_flow(const FlowKey& key, const FlowStatistics& stats) {
    if (export_callback_) {
        try {
            export_callback_(key, stats);
        } catch (const std::exception& e) {
            std::cerr << "[FlowManager] Export callback error: " << e.what() << std::endl;
        }
    }
}

void FlowManager::set_export_callback(FlowExportCallback callback) {
    export_callback_ = std::move(callback);
}

FlowManager::Stats FlowManager::get_stats() const {
    std::lock_guard<std::mutex> lock(flows_mutex_);
    Stats copy = stats_;
    copy.active_flows = active_flows_.size();
    return copy;
}

void FlowManager::print_stats() const {
    auto stats = get_stats();

    std::cout << "\n=== FlowManager Statistics ===" << std::endl;
    std::cout << "Active flows:              " << stats.active_flows << std::endl;
    std::cout << "Total packets processed:   " << stats.total_packets_processed << std::endl;
    std::cout << "Total flows created:       " << stats.total_flows_created << std::endl;
    std::cout << "Total flows expired:       " << stats.total_flows_expired << std::endl;
    std::cout << "  - Expired by timeout:    " << stats.flows_expired_timeout << std::endl;
    std::cout << "  - Expired by TCP close:  " << stats.flows_expired_tcp_close << std::endl;

    if (stats.total_packets_processed > 0) {
        double avg_packets_per_flow = static_cast<double>(stats.total_packets_processed) /
                                      static_cast<double>(stats.total_flows_created);
        std::cout << "Average packets per flow:  " << std::fixed << std::setprecision(2)
                  << avg_packets_per_flow << std::endl;
    }

    std::cout << "==============================\n" << std::endl;
}

void FlowManager::reset_stats() {
    std::lock_guard<std::mutex> lock(flows_mutex_);
    stats_ = Stats{};
    stats_.active_flows = active_flows_.size();
}

} // namespace sniffer