// sniffer/include/dns_analyzer.hpp
// DNS analysis for ransomware C&C detection
// Calculates Shannon entropy, tracks query rates, detects DGA

#pragma once

#include <string>
#include <deque>
#include <cstdint>
#include <mutex>
#include <array>

namespace sniffer {

// DNS query information
struct DNSQuery {
    std::string query_name;     // Domain name queried
    uint64_t timestamp_ns;      // Query time in nanoseconds
    bool success;               // true = got response, false = NXDOMAIN
    uint32_t src_ip;            // Source IP of query
    
    DNSQuery(const std::string& name, uint64_t ts, bool succ, uint32_t ip)
        : query_name(name), timestamp_ns(ts), success(succ), src_ip(ip) {}
};

/**
 * DNSAnalyzer: Analyzes DNS queries for ransomware detection
 * 
 * Key features extracted:
 * - Shannon entropy (DGA detection)
 * - Query rate per minute
 * - Failed query ratio (NXDOMAIN)
 * 
 * Thread-safe with ring buffer for memory efficiency.
 * 
 * Usage:
 *   DNSAnalyzer analyzer(1000);  // Ring buffer of 1000 queries
 *   analyzer.add_query("example.com", timestamp, true, src_ip);
 *   float entropy = analyzer.calculate_entropy();
 *   float rate = analyzer.get_query_rate_per_minute();
 */
class DNSAnalyzer {
public:
    /**
     * Constructor
     * @param max_queries Maximum queries to keep in ring buffer
     */
    explicit DNSAnalyzer(size_t max_queries = 1000);
    
    /**
     * Add DNS query to analyzer
     * @param query_name Domain name queried
     * @param timestamp_ns Query timestamp in nanoseconds
     * @param success true if query succeeded, false if NXDOMAIN
     * @param src_ip Source IP address
     */
    void add_query(const std::string& query_name, 
                   uint64_t timestamp_ns,
                   bool success,
                   uint32_t src_ip);
    
    /**
     * Calculate Shannon entropy of DNS query names
     * High entropy (>6.0) indicates DGA (Domain Generation Algorithm)
     * @return Entropy value (0.0 to 8.0)
     */
    float calculate_entropy() const;
    
    /**
     * Get DNS query rate per minute
     * Based on queries in last 60 seconds
     * @return Queries per minute
     */
    float get_query_rate_per_minute() const;
    
    /**
     * Get ratio of failed queries (NXDOMAIN)
     * High ratio (>0.3) indicates DGA
     * @return Failure ratio (0.0 to 1.0)
     */
    float get_failure_ratio() const;
    
    /**
     * Get count of queries in time window
     * @param window_start_ns Window start (nanoseconds)
     * @param window_end_ns Window end (nanoseconds)
     * @return Number of queries in window
     */
    size_t count_queries_in_window(uint64_t window_start_ns, 
                                    uint64_t window_end_ns) const;
    
    /**
     * Get count of unique domains queried
     * @return Number of unique domains
     */
    size_t get_unique_domain_count() const;
    
    /**
     * Get total query count
     * @return Total queries in buffer
     */
    size_t get_query_count() const noexcept {
        std::lock_guard<std::mutex> lock(mutex_);
        return queries_.size();
    }
    
    /**
     * Clear all queries (for testing)
     */
    void clear() {
        std::lock_guard<std::mutex> lock(mutex_);
        queries_.clear();
    }
    
    /**
     * Get current timestamp in nanoseconds
     */
    static uint64_t get_current_time_ns() noexcept;

private:
    // Ring buffer of recent queries
    std::deque<DNSQuery> queries_;
    
    // Thread safety
    mutable std::mutex mutex_;
    
    // Configuration
    size_t max_queries_;
    
    // Helper: Calculate entropy of a single string
    static float calculate_string_entropy(const std::string& str);
    
    // Helper: Clean up old queries outside time window
    void cleanup_old_queries(uint64_t cutoff_time_ns);
};

} // namespace sniffer
