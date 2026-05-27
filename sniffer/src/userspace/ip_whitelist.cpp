// sniffer/src/userspace/ip_whitelist.cpp
#include "ip_whitelist.hpp"
#include <chrono>
#include <algorithm>

namespace sniffer {

IPWhitelist::IPWhitelist(size_t max_size, uint64_t ttl_seconds)
    : max_size_(max_size)
    , ttl_ns_(ttl_seconds * 1'000'000'000ULL)
{
}

void IPWhitelist::add_ip(uint32_t ip, uint64_t timestamp_ns) {
    std::lock_guard<std::mutex> lock(mutex_);
    
    auto it = ip_map_.find(ip);
    
    if (it == ip_map_.end()) {
        // New IP - create entry
        IPEntry new_entry(ip, timestamp_ns);
        
        // Add to LRU front
        lru_list_.push_front(ip);
        auto lru_it = lru_list_.begin();
        
        // Insert into map
        ip_map_.emplace(ip, std::make_pair(new_entry, lru_it));
        
        // Evict if over capacity
        if (ip_map_.size() > max_size_) {
            evict_lru();
        }
    } else {
        // Existing IP - update
        it->second.first.last_seen_ns = timestamp_ns;
        
        // Move to front of LRU
        lru_list_.erase(it->second.second);
        lru_list_.push_front(ip);
        it->second.second = lru_list_.begin();
    }
}

bool IPWhitelist::is_known_ip(uint32_t ip) const {
    std::lock_guard<std::mutex> lock(mutex_);
    return ip_map_.find(ip) != ip_map_.end();
}

size_t IPWhitelist::count_new_ips_in_window(
    uint64_t window_start_ns,
    uint64_t window_end_ns) const
{
    std::lock_guard<std::mutex> lock(mutex_);
    
    size_t count = 0;
    
    for (const auto& [ip, entry_pair] : ip_map_) {
        const IPEntry& entry = entry_pair.first;
        
        if (entry.first_seen_ns >= window_start_ns && 
            entry.first_seen_ns <= window_end_ns) {
            count++;
        }
    }
    
    return count;
}

std::vector<uint32_t> IPWhitelist::get_new_ips_in_window(
    uint64_t window_start_ns,
    uint64_t window_end_ns) const
{
    std::lock_guard<std::mutex> lock(mutex_);
    
    std::vector<uint32_t> new_ips;
    
    for (const auto& [ip, entry_pair] : ip_map_) {
        const IPEntry& entry = entry_pair.first;
        
        if (entry.first_seen_ns >= window_start_ns && 
            entry.first_seen_ns <= window_end_ns) {
            new_ips.push_back(ip);
        }
    }
    
    return new_ips;
}

size_t IPWhitelist::evict_old_entries(uint64_t current_time_ns) {
    std::lock_guard<std::mutex> lock(mutex_);
    
    std::vector<uint32_t> expired_ips;
    
    for (const auto& [ip, entry_pair] : ip_map_) {
        const IPEntry& entry = entry_pair.first;
        
        if (current_time_ns - entry.last_seen_ns > ttl_ns_) {
            expired_ips.push_back(ip);
        }
    }
    
    // Remove expired entries
    for (uint32_t ip : expired_ips) {
        auto it = ip_map_.find(ip);
        if (it != ip_map_.end()) {
            lru_list_.erase(it->second.second);
            ip_map_.erase(it);
        }
    }
    
    return expired_ips.size();
}

size_t IPWhitelist::evict_old_entries() {
    return evict_old_entries(get_current_time_ns());
}

uint64_t IPWhitelist::get_current_time_ns() noexcept {
    auto now = std::chrono::steady_clock::now();
    auto duration = now.time_since_epoch();
    return std::chrono::duration_cast<std::chrono::nanoseconds>(duration).count();
}

void IPWhitelist::touch_ip(uint32_t ip) {
    auto it = ip_map_.find(ip);
    if (it != ip_map_.end()) {
        // Move to front of LRU
        lru_list_.erase(it->second.second);
        lru_list_.push_front(ip);
        it->second.second = lru_list_.begin();
    }
}

void IPWhitelist::evict_lru() {
    if (!lru_list_.empty()) {
        uint32_t oldest_ip = lru_list_.back();
        lru_list_.pop_back();
        ip_map_.erase(oldest_ip);
    }
}

} // namespace sniffer
