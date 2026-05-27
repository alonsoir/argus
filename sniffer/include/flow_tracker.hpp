// sniffer/include/flow_tracker.hpp
// Flow tracking for ransomware detection
// Maintains state of TCP/UDP flows for feature aggregation

#pragma once

#include <cstdint>
#include <string>
#include <unordered_map>
#include <vector>
#include <chrono>
#include <mutex>
#include <memory>

namespace sniffer {

// 5-tuple flow key for uniquely identifying flows
struct FlowKey {
    uint32_t src_ip;
    uint32_t dst_ip;
    uint16_t src_port;
    uint16_t dst_port;
    uint8_t protocol;
    
    // Hash function for unordered_map
    struct Hash {
        std::size_t operator()(const FlowKey& key) const noexcept {
            // Combine all fields using XOR and bit shifts
            std::size_t h1 = std::hash<uint32_t>{}(key.src_ip);
            std::size_t h2 = std::hash<uint32_t>{}(key.dst_ip);
            std::size_t h3 = std::hash<uint16_t>{}(key.src_port);
            std::size_t h4 = std::hash<uint16_t>{}(key.dst_port);
            std::size_t h5 = std::hash<uint8_t>{}(key.protocol);
            
            return h1 ^ (h2 << 1) ^ (h3 << 2) ^ (h4 << 3) ^ (h5 << 4);
        }
    };
    
    // Equality operator for unordered_map
    bool operator==(const FlowKey& other) const noexcept {
        return src_ip == other.src_ip &&
               dst_ip == other.dst_ip &&
               src_port == other.src_port &&
               dst_port == other.dst_port &&
               protocol == other.protocol;
    }
};

// Statistics tracked per flow
struct FlowStats {
    // Byte and packet counters
    uint64_t bytes_sent = 0;
    uint64_t bytes_received = 0;
    uint32_t packets_sent = 0;
    uint32_t packets_received = 0;
    
    // Timing information (microseconds)
    uint64_t start_time_ns = 0;
    uint64_t last_seen_ns = 0;
    
    // TCP flags bitmask (all flags seen in this flow)
    uint16_t tcp_flags = 0;
    
    // TCP-specific counters
    uint32_t syn_count = 0;
    uint32_t ack_count = 0;
    uint32_t rst_count = 0;
    uint32_t fin_count = 0;
    
    // Connection state
    bool connection_established = false;  // SYN-ACK seen
    bool connection_closed = false;       // FIN or RST seen
    
    // Duration in microseconds
    uint64_t get_duration_us() const noexcept {
        if (start_time_ns == 0 || last_seen_ns == 0) return 0;
        return (last_seen_ns - start_time_ns) / 1000;  // ns to us
    }
    
    // Upload/download ratio
    double get_upload_download_ratio() const noexcept {
        if (bytes_received == 0) return 0.0;
        return static_cast<double>(bytes_sent) / static_cast<double>(bytes_received);
    }
};

// Packet information for flow updates
struct PacketInfo {
    uint32_t src_ip;
    uint32_t dst_ip;
    uint16_t src_port;
    uint16_t dst_port;
    uint8_t protocol;
    uint32_t length;
    uint64_t timestamp_ns;
    uint8_t tcp_flags;  // TCP flags byte
    bool is_forward;     // true if src→dst, false if dst→src (reverse)
};

/**
 * FlowTracker: Maintains state of active network flows
 * 
 * Thread-safe flow tracking with automatic cleanup of expired flows.
 * Designed for high-performance packet processing with minimal allocations.
 * 
 * Usage:
 *   FlowTracker tracker(100000, 300);  // 100K flows, 5 min timeout
 *   tracker.update_flow(packet_info);
 *   auto stats = tracker.get_flow(flow_key);
 *   tracker.cleanup_expired_flows();
 */
class FlowTracker {
public:
    /**
     * Constructor
     * @param max_flows Maximum number of flows to track (LRU eviction)
     * @param timeout_seconds Flow timeout in seconds
     */
    explicit FlowTracker(size_t max_flows = 100000, 
                        uint64_t timeout_seconds = 300);
    
    /**
     * Update flow statistics with new packet
     * @param packet Packet information
     * @return true if flow was updated, false if new flow created
     */
    bool update_flow(const PacketInfo& packet);
    
    /**
     * Get flow statistics
     * @param key Flow key
     * @return Pointer to flow stats, or nullptr if not found
     */
    const FlowStats* get_flow(const FlowKey& key) const;
    
    /**
     * Get mutable flow statistics (for feature extraction)
     * @param key Flow key
     * @return Pointer to flow stats, or nullptr if not found
     */
    FlowStats* get_flow_mut(const FlowKey& key);
    
    /**
     * Remove expired flows (older than timeout)
     * @param current_time_ns Current time in nanoseconds
     * @return Number of flows removed
     */
    size_t cleanup_expired_flows(uint64_t current_time_ns);
    
    /**
     * Remove expired flows (uses current system time)
     * @return Number of flows removed
     */
    size_t cleanup_expired_flows();
    
    /**
     * Get all active flows in a time window
     * @param window_start_ns Window start time (nanoseconds)
     * @param window_end_ns Window end time (nanoseconds)
     * @return Vector of flow keys active in window
     */
    std::vector<FlowKey> get_flows_in_window(uint64_t window_start_ns, 
                                              uint64_t window_end_ns) const;
    
    /**
     * Get count of active flows
     */
    size_t get_flow_count() const noexcept {
        std::lock_guard<std::mutex> lock(mutex_);
        return flows_.size();
    }
    
    /**
     * Clear all flows (for testing)
     */
    void clear() {
        std::lock_guard<std::mutex> lock(mutex_);
        flows_.clear();
    }
    
    /**
     * Get current timestamp in nanoseconds
     */
    static uint64_t get_current_time_ns() noexcept {
        using namespace std::chrono;
        auto now = steady_clock::now();
        return duration_cast<nanoseconds>(now.time_since_epoch()).count();
    }

private:
    // Flow storage (5-tuple -> stats)
    std::unordered_map<FlowKey, FlowStats, FlowKey::Hash> flows_;
    
    // Thread safety
    mutable std::mutex mutex_;
    
    // Configuration
    size_t max_flows_;
    uint64_t timeout_ns_;  // Timeout in nanoseconds
    
    // LRU eviction helper
    void evict_oldest_flow();
    
    // Parse TCP flags from byte
    void update_tcp_flags(FlowStats& stats, uint8_t flags);
};

} // namespace sniffer
