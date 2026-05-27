// sniffer/include/ip_whitelist.hpp
// IP whitelist with LRU cache for ransomware detection
// Tracks "known good" IPs to detect new external connections

#pragma once

#include <cstdint>
#include <unordered_map>
#include <list>
#include <mutex>
#include <vector>

namespace sniffer {

// IP entry with timestamp
struct IPEntry {
    uint32_t ip;
    uint64_t first_seen_ns;
    uint64_t last_seen_ns;
    
    IPEntry(uint32_t ip_addr, uint64_t timestamp)
        : ip(ip_addr)
        , first_seen_ns(timestamp)
        , last_seen_ns(timestamp)
    {}
};

/**
 * IPWhitelist: LRU cache of known IP addresses
 * 
 * Tracks "seen" IPs to detect new external connections.
 * Uses LRU (Least Recently Used) eviction when cache is full.
 * 
 * Key feature: count_new_ips_in_window()
 * - Returns count of IPs that appeared for first time in window
 * - High count indicates ransomware contacting new C&C servers
 * 
 * Thread-safe with configurable size and TTL.
 * 
 * Usage:
 *   IPWhitelist whitelist(10000, 24 * 3600);  // 10K IPs, 24h TTL
 *   whitelist.add_ip(ip_addr, timestamp);
 *   bool known = whitelist.is_known_ip(ip_addr);
 *   size_t new_ips = whitelist.count_new_ips_in_window(window_start, window_end);
 */
class IPWhitelist {
public:
    /**
     * Constructor
     * @param max_size Maximum IPs to track (LRU eviction)
     * @param ttl_seconds Time-to-live in seconds (24h default)
     */
    explicit IPWhitelist(size_t max_size = 10000, 
                        uint64_t ttl_seconds = 24 * 3600);
    
    /**
     * Add IP to whitelist (or update if exists)
     * @param ip IP address
     * @param timestamp_ns Timestamp in nanoseconds
     */
    void add_ip(uint32_t ip, uint64_t timestamp_ns);
    
    /**
     * Check if IP is known (in whitelist)
     * @param ip IP address
     * @return true if IP is in whitelist
     */
    bool is_known_ip(uint32_t ip) const;
    
    /**
     * Count new IPs that appeared in time window
     * "New" = first_seen timestamp is within window
     * @param window_start_ns Window start (nanoseconds)
     * @param window_end_ns Window end (nanoseconds)
     * @return Count of new IPs in window
     */
    size_t count_new_ips_in_window(uint64_t window_start_ns, 
                                    uint64_t window_end_ns) const;
    
    /**
     * Get all IPs that are "new" (first seen) in window
     * @param window_start_ns Window start (nanoseconds)
     * @param window_end_ns Window end (nanoseconds)
     * @return Vector of new IP addresses
     */
    std::vector<uint32_t> get_new_ips_in_window(uint64_t window_start_ns,
                                                  uint64_t window_end_ns) const;
    
    /**
     * Remove IPs older than TTL
     * @param current_time_ns Current time in nanoseconds
     * @return Number of IPs removed
     */
    size_t evict_old_entries(uint64_t current_time_ns);
    
    /**
     * Remove IPs older than TTL (uses current system time)
     * @return Number of IPs removed
     */
    size_t evict_old_entries();
    
    /**
     * Get count of IPs in whitelist
     */
    size_t get_size() const noexcept {
        std::lock_guard<std::mutex> lock(mutex_);
        return ip_map_.size();
    }
    
    /**
     * Clear all IPs (for testing)
     */
    void clear() {
        std::lock_guard<std::mutex> lock(mutex_);
        ip_map_.clear();
        lru_list_.clear();
    }
    
    /**
     * Get current timestamp in nanoseconds
     */
    static uint64_t get_current_time_ns() noexcept;

private:
    // LRU list: most recently used at front
    using LRUList = std::list<uint32_t>;
    LRUList lru_list_;
    
    // Map: IP -> (IPEntry, iterator to LRU list)
    std::unordered_map<uint32_t, std::pair<IPEntry, LRUList::iterator>> ip_map_;
    
    // Thread safety
    mutable std::mutex mutex_;
    
    // Configuration
    size_t max_size_;
    uint64_t ttl_ns_;  // TTL in nanoseconds
    
    // Helper: Move IP to front of LRU list
    void touch_ip(uint32_t ip);
    
    // Helper: Evict least recently used IP
    void evict_lru();
};

} // namespace sniffer
