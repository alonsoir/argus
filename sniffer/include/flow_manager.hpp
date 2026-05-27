// sniffer/include/flow_manager.hpp
#pragma once

#include "main.h"
#include "time_window_manager.hpp"
#include "flow_tracker.hpp"
#include <unordered_map>
#include <vector>
#include <mutex>
#include <memory>
#include <chrono>
#include <functional>

namespace sniffer {

// Flow statistics - Accumulates data for ML feature extraction
struct FlowStatistics {
    // ============ TIMING ============
    uint64_t flow_start_ns;
    uint64_t flow_last_seen_ns;

    // ============ PACKET COUNTERS ============
    uint64_t spkts = 0;  // Forward packets (source -> destination)
    uint64_t dpkts = 0;  // Backward packets (destination -> source)

    // ============ BYTE COUNTERS ============
    uint64_t sbytes = 0;  // Forward bytes
    uint64_t dbytes = 0;  // Backward bytes

    // ============ PACKET LENGTHS ============
    std::vector<uint32_t> fwd_lengths;  // For smean calculation
    std::vector<uint32_t> bwd_lengths;  // For dmean calculation
    std::vector<uint32_t> all_lengths;  // For packet_len_mean/std/var

    // ============ INTER-ARRIVAL TIMES ============
    std::vector<uint64_t> packet_timestamps;  // ALL packet timestamps (for flow IAT)
    std::vector<uint64_t> fwd_timestamps;     // Forward packet timestamps
    std::vector<uint64_t> bwd_timestamps;     // Backward packet timestamps

    // ============ TCP FLAGS COUNTERS ============
    uint32_t fin_count = 0;
    uint32_t syn_count = 0;
    uint32_t rst_count = 0;
    uint32_t psh_count = 0;
    uint32_t ack_count = 0;
    uint32_t urg_count = 0;
    uint32_t ece_count = 0;
    uint32_t cwr_count = 0;

    // ============ DIRECTIONAL TCP FLAGS ============
    uint32_t fwd_psh_flags = 0;
    uint32_t bwd_psh_flags = 0;
    uint32_t fwd_urg_flags = 0;
    uint32_t bwd_urg_flags = 0;

    // ============ HEADER LENGTHS ============
    std::vector<uint16_t> fwd_header_lengths;
    std::vector<uint16_t> bwd_header_lengths;

    // ============ FASE 3: TIME WINDOW MANAGER ============
    std::unique_ptr<TimeWindowManager> time_windows;

    // ============ METHODS ============

    // Constructor
    FlowStatistics() {
        time_windows = std::make_unique<TimeWindowManager>();
    }

    // Move constructor
    FlowStatistics(FlowStatistics&& other) noexcept = default;
    FlowStatistics& operator=(FlowStatistics&& other) noexcept = default;

    // Determines if packet is forward direction
    bool is_forward(const SimpleEvent& pkt, const FlowKey& flow_key) const {
        return pkt.src_ip == flow_key.src_ip &&
               pkt.dst_ip == flow_key.dst_ip &&
               pkt.src_port == flow_key.src_port &&
               pkt.dst_port == flow_key.dst_port;
    }

    // Add packet to flow statistics
    void add_packet(const SimpleEvent& pkt, const FlowKey& flow_key) {
        // Initialize timestamps on first packet
        if (spkts == 0 && dpkts == 0) {
            flow_start_ns = pkt.timestamp;
        }
        flow_last_seen_ns = pkt.timestamp;

        bool is_fwd = is_forward(pkt, flow_key);

        // Direction-specific counters
        if (is_fwd) {
            spkts++;
            sbytes += pkt.packet_len;
            fwd_lengths.push_back(pkt.packet_len);

            uint16_t total_header = pkt.ip_header_len + pkt.l4_header_len;
            fwd_header_lengths.push_back(total_header);

            fwd_timestamps.push_back(pkt.timestamp);

            // Directional TCP flags
            if (has_tcp_flag(pkt, TCP_FLAG_PSH)) fwd_psh_flags++;
            if (has_tcp_flag(pkt, TCP_FLAG_URG)) fwd_urg_flags++;

        } else {
            dpkts++;
            dbytes += pkt.packet_len;
            bwd_lengths.push_back(pkt.packet_len);

            uint16_t total_header = pkt.ip_header_len + pkt.l4_header_len;
            bwd_header_lengths.push_back(total_header);

            bwd_timestamps.push_back(pkt.timestamp);

            // Directional TCP flags
            if (has_tcp_flag(pkt, TCP_FLAG_PSH)) bwd_psh_flags++;
            if (has_tcp_flag(pkt, TCP_FLAG_URG)) bwd_urg_flags++;
        }

        // Overall statistics
        all_lengths.push_back(pkt.packet_len);
        packet_timestamps.push_back(pkt.timestamp);

        // ⭐ FASE 3: Update time windows
        if (time_windows) {
            time_windows->add_packet(pkt.timestamp, pkt.packet_len, is_fwd);
        }

        // TCP flags totals
        if (pkt.protocol == 6) {  // TCP only
            if (has_tcp_flag(pkt, TCP_FLAG_FIN)) fin_count++;
            if (has_tcp_flag(pkt, TCP_FLAG_SYN)) syn_count++;
            if (has_tcp_flag(pkt, TCP_FLAG_RST)) rst_count++;
            if (has_tcp_flag(pkt, TCP_FLAG_PSH)) psh_count++;
            if (has_tcp_flag(pkt, TCP_FLAG_ACK)) ack_count++;
            if (has_tcp_flag(pkt, TCP_FLAG_URG)) urg_count++;
            if (has_tcp_flag(pkt, TCP_FLAG_ECE)) ece_count++;
            if (has_tcp_flag(pkt, TCP_FLAG_CWR)) cwr_count++;
        }
    }

    // Get flow duration in microseconds
    uint64_t get_duration_us() const {
        if (flow_last_seen_ns <= flow_start_ns) return 0;
        return (flow_last_seen_ns - flow_start_ns) / 1000ULL;
    }

    // Get total packets
    uint64_t get_total_packets() const {
        return spkts + dpkts;
    }

    // Get total bytes
    uint64_t get_total_bytes() const {
        return sbytes + dbytes;
    }

    // Check if flow should expire (inactive for timeout period)
    bool should_expire(uint64_t current_ns, uint64_t timeout_ns) const {
        return (current_ns - flow_last_seen_ns) > timeout_ns;
    }

    // Check if flow is TCP
    bool is_tcp() const {
        return fin_count > 0 || syn_count > 0 || rst_count > 0 ||
               psh_count > 0 || ack_count > 0 || urg_count > 0;
    }

    // Check if TCP connection is closed (FIN or RST seen)
    bool is_tcp_closed() const {
        return fin_count > 0 || rst_count > 0;
    }
};

// Callback for when a flow expires and needs to be processed
using FlowExportCallback = std::function<void(const FlowKey&, const FlowStatistics&)>;

// Flow Manager - Tracks active flows and manages expiration
class FlowManager {
public:
    // Configuration
    struct Config {
        uint64_t flow_timeout_ns = 120'000'000'000ULL;  // 120 seconds default
        size_t max_flows = 100'000;                      // Max concurrent flows
        bool auto_export_on_tcp_close = true;            // Export TCP flows on FIN/RST
        bool enable_statistics = true;                   // Track FlowManager stats
    };

    explicit FlowManager(const Config& config);
    ~FlowManager();

    // Add packet to flow tracking
    void add_packet(const SimpleEvent& pkt);

    // Expire flows that have timed out
    // Returns number of flows expired
    size_t expire_flows(uint64_t current_ns);

    // Force expire all flows (for shutdown)
    size_t expire_all_flows();

    // Set callback for flow export
    void set_export_callback(FlowExportCallback callback);

    // Get current statistics
    struct Stats {
        size_t active_flows = 0;
        uint64_t total_packets_processed = 0;
        uint64_t total_flows_created = 0;
        uint64_t total_flows_expired = 0;
        uint64_t flows_expired_timeout = 0;
        uint64_t flows_expired_tcp_close = 0;
    };

    Stats get_stats() const;
    void print_stats() const;
    void reset_stats();

    // ============================================================================
    // ML DEFENDER INTEGRATION (Phase 1, Day 3 - Nov 17, 2025)
    // ============================================================================

    // Get flow statistics for feature extraction (thread-local safe)
    // SAFETY NOTE: This method is NOT thread-safe for shared FlowManager instances.
    // Only use with thread_local FlowManager where each thread has its own instance.
    // Returns nullptr if flow doesn't exist.
    FlowStatistics* get_flow_stats_unsafe(const FlowKey& key) {
        auto it = active_flows_.find(key);
        return (it != active_flows_.end()) ? &it->second : nullptr;
    }

private:
    Config config_;

    // Flow storage
    std::unordered_map<FlowKey, FlowStatistics, FlowKey::Hash> active_flows_;
    mutable std::mutex flows_mutex_;

    // Statistics
    Stats stats_;

    // Export callback
    FlowExportCallback export_callback_;

    // Helper methods
    FlowKey create_flow_key(const SimpleEvent& pkt) const;
    void export_flow(const FlowKey& key, const FlowStatistics& stats);
    bool should_auto_export(const FlowStatistics& stats) const;
};

} // namespace sniffer