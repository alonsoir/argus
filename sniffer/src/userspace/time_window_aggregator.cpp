// sniffer/src/userspace/time_window_aggregator.cpp
// Time-windowed feature aggregation implementation

#include "time_window_aggregator.hpp"
#include "flow_tracker.hpp"
#include "ip_whitelist.hpp"
#include "dns_analyzer.hpp"
#include <algorithm>
#include <unordered_set>
#include <cmath>
#include <chrono>

namespace sniffer {

TimeWindowAggregator::TimeWindowAggregator(
    FlowTracker& flow_tracker,
    IPWhitelist& ip_whitelist,
    DNSAnalyzer& dns_analyzer,
    size_t max_events)
    : flow_tracker_(flow_tracker)
    , ip_whitelist_(ip_whitelist)
    , dns_analyzer_(dns_analyzer)
    , max_events_(max_events)
{

}

void TimeWindowAggregator::add_event(const TimeWindowEvent& event) {
    std::lock_guard<std::mutex> lock(mutex_);

    // Add event to ring buffer
    events_.push_back(event);

    // Maintain ring buffer size
    if (events_.size() > max_events_) {
        events_.pop_front();
    }
}

WindowStats TimeWindowAggregator::get_window_stats(
    uint64_t window_start_ns,
    uint64_t window_end_ns) const
{
    std::lock_guard<std::mutex> lock(mutex_);

    WindowStats stats;
    stats.window_start_ns = window_start_ns;
    stats.window_end_ns = window_end_ns;

    std::unordered_set<uint32_t> unique_ips;
    std::unordered_set<uint16_t> unique_ports;

    for (const auto& event : events_) {
        if (event.timestamp_ns >= window_start_ns &&
            event.timestamp_ns <= window_end_ns) {

            stats.event_count++;
            stats.total_bytes += event.bytes;

            unique_ips.insert(event.src_ip);
            unique_ips.insert(event.dst_ip);

            unique_ports.insert(event.src_port);
            unique_ports.insert(event.dst_port);
        }
    }

    stats.unique_ips_count = unique_ips.size();
    stats.unique_ports_count = unique_ports.size();

    return stats;
}

size_t TimeWindowAggregator::count_events_in_window(
    uint64_t window_start_ns,
    uint64_t window_end_ns) const
{
    std::lock_guard<std::mutex> lock(mutex_);

    size_t count = 0;

    for (const auto& event : events_) {
        if (event.timestamp_ns >= window_start_ns &&
            event.timestamp_ns <= window_end_ns) {
            count++;
        }
    }

    return count;
}

// ========== PHASE 1A: Extract Critical Features (3) ==========

RansomwareWindowFeatures TimeWindowAggregator::extract_ransomware_features_phase1a(
    uint64_t window_start_ns,
    uint64_t window_end_ns)
{
    RansomwareWindowFeatures features;

    // Use default windows if not specified
    if (window_end_ns == 0) {
        window_end_ns = get_current_time_ns();
    }

    // Feature 1: DNS Query Entropy (uses DNSAnalyzer)
    features.dns_query_entropy = extract_dns_query_entropy();

    // Feature 2: New External IPs in 30s window
    if (window_start_ns == 0) {
        window_start_ns = get_default_window_start_30s();
    }
    features.new_external_ips_30s = extract_new_external_ips_30s(
        window_start_ns, window_end_ns);

    // Feature 3: SMB Connection Diversity (60s window)
    uint64_t smb_window_start = window_end_ns - (60 * 1'000'000'000ULL); // 60s
    features.smb_connection_diversity = extract_smb_connection_diversity(
        smb_window_start, window_end_ns);

    // Set metadata
    features.window_start_ns = window_start_ns;
    features.window_end_ns = window_end_ns;
    features.features_valid = true;

    return features;
}

float TimeWindowAggregator::extract_dns_query_entropy() const {
    // Delegate to DNSAnalyzer - it already has all DNS queries
    return dns_analyzer_.calculate_entropy();
}

int32_t TimeWindowAggregator::extract_new_external_ips_30s(
    uint64_t window_start_ns,
    uint64_t window_end_ns) const
{
    // Use default 30s window if not specified
    if (window_end_ns == 0) {
        window_end_ns = get_current_time_ns();
    }
    if (window_start_ns == 0) {
        window_start_ns = get_default_window_start_30s();
    }

    // Delegate to IPWhitelist - it tracks all IPs with first_seen timestamps
    return static_cast<int32_t>(
        ip_whitelist_.count_new_ips_in_window(window_start_ns, window_end_ns));
}

int32_t TimeWindowAggregator::extract_smb_connection_diversity(
    uint64_t window_start_ns,
    uint64_t window_end_ns) const
{
    // Use default 60s window if not specified
    if (window_end_ns == 0) {
        window_end_ns = get_current_time_ns();
    }
    if (window_start_ns == 0) {
        window_start_ns = get_default_window_start_60s();
    }

    std::lock_guard<std::mutex> lock(mutex_);

    // Count unique destination IPs contacted on SMB ports (139, 445)
    std::unordered_set<uint32_t> unique_smb_destinations;

    for (const auto& event : events_) {
        // Check if event is in window
        if (event.timestamp_ns < window_start_ns ||
            event.timestamp_ns > window_end_ns) {
            continue;
        }

        // Check if event is SMB (ports 139 or 445)
        bool is_smb = (event.dst_port == 139 || event.dst_port == 445);

        if (is_smb) {
            // Add destination IP to set
            unique_smb_destinations.insert(event.dst_ip);
        }
    }

    return static_cast<int32_t>(unique_smb_destinations.size());
}

// ========== FUTURE PHASES: Additional Features ==========

RansomwareWindowFeatures TimeWindowAggregator::extract_ransomware_features_phase1b(
    uint64_t window_start_ns,
    uint64_t window_end_ns)
{
    // Start with Phase 1A features
    RansomwareWindowFeatures features = extract_ransomware_features_phase1a(
        window_start_ns, window_end_ns);

    // Use default windows if not specified
    if (window_end_ns == 0) {
        window_end_ns = get_current_time_ns();
    }
    if (window_start_ns == 0) {
        window_start_ns = get_default_window_start_30s();
    }

    // === Phase 1B Features ===

    // Feature 3 (original): DNS query rate per minute
    features.dns_query_rate_per_min = dns_analyzer_.get_query_rate_per_minute();

    // Feature 4: Failed DNS queries ratio
    features.failed_dns_queries_ratio = dns_analyzer_.get_failure_ratio();

    // Feature 9: New internal connections (30s)
    // TODO: Implement internal connection tracking
    features.new_internal_connections_30s = 0;

    // Feature 11: Upload/download ratio (30s)
    std::lock_guard<std::mutex> lock(mutex_);
    uint64_t upload_bytes = 0;
    uint64_t download_bytes = 0;

    for (const auto& event : events_) {
        if (event.timestamp_ns >= window_start_ns &&
            event.timestamp_ns <= window_end_ns) {
            // Assume events track outbound data
            upload_bytes += event.bytes;
            // Download would need bidirectional tracking
        }
    }

    if (download_bytes > 0) {
        features.upload_download_ratio_30s =
            static_cast<float>(upload_bytes) / static_cast<float>(download_bytes);
    } else {
        features.upload_download_ratio_30s = 0.0f;
    }

    // Feature 13: Unique destinations in 30s
    auto events_in_window = get_events_in_window(window_start_ns, window_end_ns);
    features.unique_destinations_30s = static_cast<int32_t>(
        count_unique_ips(events_in_window, true));  // true = destination IPs

    // Feature 17: Protocol diversity score
    std::unordered_set<uint8_t> unique_protocols;
    for (const auto& event : events_in_window) {
        unique_protocols.insert(event.protocol);
    }
    // Normalize by max expected protocols (TCP, UDP, ICMP = 3 common)
    features.protocol_diversity_score =
        std::min(1.0f, static_cast<float>(unique_protocols.size()) / 8.0f);

    return features;
}

RansomwareWindowFeatures TimeWindowAggregator::extract_ransomware_features_complete(
    uint64_t window_start_ns,
    uint64_t window_end_ns)
{
    // Start with Phase 1B features (includes 1A)
    RansomwareWindowFeatures features = extract_ransomware_features_phase1b(
        window_start_ns, window_end_ns);

    // Use default windows if not specified
    if (window_end_ns == 0) {
        window_end_ns = get_current_time_ns();
    }
    if (window_start_ns == 0) {
        window_start_ns = get_default_window_start_30s();
    }

    std::lock_guard<std::mutex> lock(mutex_);
    auto events_in_window = get_events_in_window(window_start_ns, window_end_ns);

    // === Phase 1C Features ===

    // Feature 5: TLS self-signed cert count
    // TODO: Requires TLS inspection
    features.tls_self_signed_cert_count = 0;

    // Feature 6: Non-standard port HTTP count
    // TODO: Requires HTTP signature detection
    features.non_standard_port_http_count = 0;

    // Feature 8: RDP failed auth count
    // TODO: Requires RDP protocol parsing
    features.rdp_failed_auth_count = 0;

    // Feature 10: Port scan pattern score
    // TODO: Requires sequential port detection
    features.port_scan_pattern_score = 0.0f;

    // Feature 12: Burst connections count (connections in <5s)
    // Count connections started within 5-second sub-windows
    features.burst_connections_count = 0;
    uint64_t burst_window = 5 * 1'000'000'000ULL; // 5 seconds

    for (size_t i = 0; i < events_in_window.size(); i++) {
        size_t burst_count = 1;
        uint64_t burst_start = events_in_window[i].timestamp_ns;

        for (size_t j = i + 1; j < events_in_window.size(); j++) {
            if (events_in_window[j].timestamp_ns - burst_start < burst_window) {
                burst_count++;
            } else {
                break;
            }
        }

        if (burst_count > 10) {  // Threshold: >10 connections in 5s
            features.burst_connections_count++;
        }
    }

    // Feature 14: Large upload sessions count (>10MB)
    for (const auto& event : events_in_window) {
        if (event.bytes > 10 * 1024 * 1024) {  // 10 MB
            features.large_upload_sessions_count++;
        }
    }

    // Feature 15: Nocturnal activity flag (00:00-05:00 local time)
    auto now = std::chrono::system_clock::now();
    auto now_time_t = std::chrono::system_clock::to_time_t(now);
    auto local_time = std::localtime(&now_time_t);
    int hour = local_time->tm_hour;
    features.nocturnal_activity_flag = (hour >= 0 && hour < 5);

    // Feature 16: Connection rate stddev
    // TODO: Requires sliding window of connection rates
    features.connection_rate_stddev = 0.0f;

    // Feature 18: Average flow duration
    // Calculate from FlowTracker
    auto flows_in_window = flow_tracker_.get_flows_in_window(
        window_start_ns, window_end_ns);

    if (!flows_in_window.empty()) {
        uint64_t total_duration_us = 0;
        size_t valid_flows = 0;

        for (const auto& flow_key : flows_in_window) {
            const FlowStats* stats = flow_tracker_.get_flow(flow_key);
            if (stats) {
                uint64_t duration = stats->get_duration_us();
                if (duration > 0) {
                    total_duration_us += duration;
                    valid_flows++;
                }
            }
        }

        if (valid_flows > 0) {
            features.avg_flow_duration_seconds =
                static_cast<float>(total_duration_us) /
                static_cast<float>(valid_flows) / 1'000'000.0f;  // us to seconds
        }
    }

    // Feature 19: TCP RST ratio
    // TODO: Requires TCP flag tracking from FlowTracker
    features.tcp_rst_ratio = 0.0f;

    // Feature 20: SYN without ACK ratio
    // TODO: Requires TCP handshake state tracking
    features.syn_without_ack_ratio = 0.0f;

    return features;
}

// ========== Utility Methods ==========

size_t TimeWindowAggregator::cleanup_old_events(uint64_t retention_ns) {
    std::lock_guard<std::mutex> lock(mutex_);

    uint64_t cutoff = get_current_time_ns() - retention_ns;
    size_t removed = 0;

    // Remove events older than cutoff
    while (!events_.empty() && events_.front().timestamp_ns < cutoff) {
        events_.pop_front();
        removed++;
    }

    return removed;
}

uint64_t TimeWindowAggregator::get_current_time_ns() noexcept {
    using namespace std::chrono;
    auto now = steady_clock::now();
    return duration_cast<nanoseconds>(now.time_since_epoch()).count();
}

bool TimeWindowAggregator::is_external_ip(uint32_t ip) noexcept {
    // [EXTIP-ORDEN-D339] `ip` llega en orden NUMERICO de host (a.b.c.d = a<<24|b<<16|c<<8|d), tal como lo
    // ensambla sniffer.bpf.c (event->dst_ip): no hay nada que convertir. Medido DAY339 sobre el bronce
    // (DEBT-SNIFFER-IS-EXTERNAL-IP-BYTE-ORDER-001) y fijado por tests/test_is_external_ip.cpp.
    // Rangos RFC 1918, loopback y link-local.

    // 10.0.0.0/8
    if ((ip & 0xFF000000) == 0x0A000000) {
        return false;
    }

    // 172.16.0.0/12
    if ((ip & 0xFFF00000) == 0xAC100000) {
        return false;
    }

    // 192.168.0.0/16
    if ((ip & 0xFFFF0000) == 0xC0A80000) {
        return false;
    }

    // 127.0.0.0/8 (loopback)
    if ((ip & 0xFF000000) == 0x7F000000) {
        return false;
    }

    // 169.254.0.0/16 (link-local)
    if ((ip & 0xFFFF0000) == 0xA9FE0000) {
        return false;
    }

    return true;  // External IP
}

// ========== Helper Methods ==========

std::vector<TimeWindowEvent> TimeWindowAggregator::get_events_in_window(
    uint64_t window_start_ns,
    uint64_t window_end_ns) const
{
    // Called from methods that already hold the lock

    std::vector<TimeWindowEvent> result;
    result.reserve(events_.size() / 10);  // Estimate 10% in window

    for (const auto& event : events_) {
        if (event.timestamp_ns >= window_start_ns &&
            event.timestamp_ns <= window_end_ns) {
            result.push_back(event);
        }
    }

    return result;
}

size_t TimeWindowAggregator::count_unique_ips(
    const std::vector<TimeWindowEvent>& events,
    bool check_destination)
{
    std::unordered_set<uint32_t> unique_ips;

    for (const auto& event : events) {
        uint32_t ip = check_destination ? event.dst_ip : event.src_ip;
        unique_ips.insert(ip);
    }

    return unique_ips.size();
}

size_t TimeWindowAggregator::count_unique_ports(
    const std::vector<TimeWindowEvent>& events,
    bool check_destination)
{
    std::unordered_set<uint16_t> unique_ports;

    for (const auto& event : events) {
        uint16_t port = check_destination ? event.dst_port : event.src_port;
        unique_ports.insert(port);
    }

    return unique_ports.size();
}

uint64_t TimeWindowAggregator::get_default_window_start_30s() noexcept {
    uint64_t now = get_current_time_ns();
    return now - (30 * 1'000'000'000ULL);  // 30 seconds ago
}

uint64_t TimeWindowAggregator::get_default_window_start_60s() noexcept {
    uint64_t now = get_current_time_ns();
    return now - (60 * 1'000'000'000ULL);  // 60 seconds ago
}

} // namespace sniffer
