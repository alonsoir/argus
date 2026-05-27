// sniffer/src/userspace/dns_analyzer.cpp
// DNS analysis implementation with Shannon entropy calculation

#include "dns_analyzer.hpp"
#include <cmath>
#include <algorithm>
#include <unordered_set>
#include <unordered_map>
#include <chrono>

namespace sniffer {

DNSAnalyzer::DNSAnalyzer(size_t max_queries)
    : max_queries_(max_queries)
{
}

void DNSAnalyzer::add_query(const std::string& query_name,
                            uint64_t timestamp_ns,
                            bool success,
                            uint32_t src_ip)
{
    std::lock_guard<std::mutex> lock(mutex_);
    
    // Add query to ring buffer
    queries_.emplace_back(query_name, timestamp_ns, success, src_ip);
    
    // Maintain ring buffer size
    if (queries_.size() > max_queries_) {
        queries_.pop_front();
    }
    
    // Optional: Cleanup queries older than 5 minutes
    uint64_t cutoff = timestamp_ns - (5 * 60 * 1'000'000'000ULL);  // 5 min
    cleanup_old_queries(cutoff);
}

float DNSAnalyzer::calculate_entropy() const {
    std::lock_guard<std::mutex> lock(mutex_);
    
    if (queries_.empty()) {
        return 0.0f;
    }
    
    // Calculate average entropy across all query names
    float total_entropy = 0.0f;
    size_t count = 0;
    
    for (const auto& query : queries_) {
        if (!query.query_name.empty()) {
            total_entropy += calculate_string_entropy(query.query_name);
            count++;
        }
    }
    
    return (count > 0) ? (total_entropy / count) : 0.0f;
}

float DNSAnalyzer::calculate_string_entropy(const std::string& str) {
    if (str.empty()) {
        return 0.0f;
    }
    
    // Count character frequencies
    std::unordered_map<char, int> freq;
    for (char c : str) {
        freq[c]++;
    }
    
    // Calculate Shannon entropy
    float entropy = 0.0f;
    float len = static_cast<float>(str.length());
    
    for (const auto& [ch, count] : freq) {
        float p = count / len;
        entropy -= p * std::log2(p);
    }
    
    return entropy;
}

float DNSAnalyzer::get_query_rate_per_minute() const {
    std::lock_guard<std::mutex> lock(mutex_);
    
    if (queries_.empty()) {
        return 0.0f;
    }
    
    // Get current time
    uint64_t now_ns = get_current_time_ns();
    
    // Count queries in last 60 seconds
    uint64_t window_start = now_ns - (60 * 1'000'000'000ULL);  // 60 seconds ago
    
    size_t count = 0;
    for (const auto& query : queries_) {
        if (query.timestamp_ns >= window_start) {
            count++;
        }
    }
    
    // Return queries per minute
    return static_cast<float>(count);
}

float DNSAnalyzer::get_failure_ratio() const {
    std::lock_guard<std::mutex> lock(mutex_);
    
    if (queries_.empty()) {
        return 0.0f;
    }
    
    size_t failed_count = 0;
    
    for (const auto& query : queries_) {
        if (!query.success) {
            failed_count++;
        }
    }
    
    return static_cast<float>(failed_count) / static_cast<float>(queries_.size());
}

size_t DNSAnalyzer::count_queries_in_window(uint64_t window_start_ns,
                                             uint64_t window_end_ns) const
{
    std::lock_guard<std::mutex> lock(mutex_);
    
    size_t count = 0;
    
    for (const auto& query : queries_) {
        if (query.timestamp_ns >= window_start_ns && 
            query.timestamp_ns <= window_end_ns) {
            count++;
        }
    }
    
    return count;
}

size_t DNSAnalyzer::get_unique_domain_count() const {
    std::lock_guard<std::mutex> lock(mutex_);
    
    std::unordered_set<std::string> unique_domains;
    
    for (const auto& query : queries_) {
        unique_domains.insert(query.query_name);
    }
    
    return unique_domains.size();
}

void DNSAnalyzer::cleanup_old_queries(uint64_t cutoff_time_ns) {
    // Remove queries older than cutoff
    // Called from add_query, already locked
    
    while (!queries_.empty() && queries_.front().timestamp_ns < cutoff_time_ns) {
        queries_.pop_front();
    }
}

uint64_t DNSAnalyzer::get_current_time_ns() noexcept {
    using namespace std::chrono;
    auto now = steady_clock::now();
    return duration_cast<nanoseconds>(now.time_since_epoch()).count();
}

} // namespace sniffer
