// sniffer/include/fast_detector.hpp
#pragma once

#include "main.h"  // For SimpleEvent
#include <unordered_set>
#include <cstdint>

namespace sniffer {

// ============================================================================
// FastDetector - Layer 1 Heuristic Detection
// ============================================================================
// Ultra-fast behavioral detector for early ransomware detection.
//
// Architecture:
//   - Thread-local (no locks, zero contention)
//   - O(1) amortized per event
//   - 10-second sliding window
//   - Cache-aligned for multi-core performance
//
// Detection Heuristics:
//   1. Excessive external IPs (C&C scanning)
//   2. Multiple SMB connections (lateral movement)
//   3. Rapid port scanning (reconnaissance)
//   4. High RST ratio (failed connections)
//
// Usage:
//   thread_local FastDetector detector;
//   detector.ingest(event);
//   if (detector.is_suspicious()) {
//       alert_early_warning();
//   }
// ============================================================================

class FastDetector {
public:
    FastDetector();
    ~FastDetector() = default;

    // Non-copyable (thread-local instance)
    FastDetector(const FastDetector&) = delete;
    FastDetector& operator=(const FastDetector&) = delete;

    // Ingest event and update heuristics
    void ingest(const SimpleEvent& evt);

    // Check if current behavior is suspicious
    bool is_suspicious() const;

    // Reset window if stale
    void reset_if_stale(uint64_t now_ns);

    // Snapshot for debugging/logging
    struct Snapshot {
        uint32_t external_ips_10s;
        uint32_t smb_conns;
        uint32_t resets;
        uint32_t total_tcp;
        uint32_t unique_ports;
        uint64_t window_start_ns;
    };
    Snapshot snapshot() const;

    // Get individual metrics (for testing)
    uint32_t get_external_ips_count() const { return recent_external_ips_.size(); }
    uint32_t get_smb_count() const { return smb_conn_count_; }
    uint32_t get_port_count() const { return recent_ports_.size(); }
    double get_rst_ratio() const { return rst_ratio(); }

private:
    // Configuration (compile-time constants)
    static constexpr uint64_t WINDOW_NS = 10ULL * 1'000'000'000ULL;  // 10 seconds
    static constexpr uint32_t THRESHOLD_EXTERNAL_IPS = 10;
    static constexpr uint32_t THRESHOLD_SMB_CONNS = 3;
    static constexpr uint32_t THRESHOLD_PORT_SCAN = 10;
    static constexpr double THRESHOLD_RST_RATIO = 0.2;

    // State (cache-aligned for performance)
    alignas(64) uint64_t window_start_ns_;
    alignas(64) std::unordered_set<uint32_t> recent_external_ips_;
    std::unordered_set<uint16_t> recent_ports_;
    uint32_t smb_conn_count_;
    uint32_t rst_count_;
    uint32_t total_tcp_;

    // Helper functions
    bool is_external_ip(uint32_t ip) const noexcept;
    bool is_new_external_ip(uint32_t ip);
    bool is_smb_connection(uint16_t port) const noexcept;
    bool detect_rapid_port_scan() const noexcept;
    double rst_ratio() const noexcept;
};

} // namespace sniffer
