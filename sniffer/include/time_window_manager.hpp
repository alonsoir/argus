// sniffer/include/time_window_manager.hpp
#pragma once

#include "time_window_aggregator.hpp"
#include "main.h"
#include <vector>
#include <deque>
#include <cstdint>
#include <algorithm>

namespace sniffer {

// Manages temporal windows for a flow
class TimeWindowManager {
public:
    // Configuration
    struct Config {
        uint64_t window_duration_ns = 30'000'000'000ULL;  // 30 seconds
        uint64_t overlap_ns = 10'000'000'000ULL;          // 10 seconds
        size_t max_windows = 10;                           // Max windows to keep
        uint64_t bulk_threshold_bytes = 4096;             // Min bytes for bulk
        uint64_t bulk_threshold_packets = 4;              // Min packets for bulk
        uint64_t bulk_gap_threshold_ns = 1'000'000'000ULL; // Max 1s gap
    };

    // ⭐ QUITAR EL = Config() - esto causa el error
    explicit TimeWindowManager(const Config& config);

    // Constructor por defecto adicional si lo necesitas
    TimeWindowManager() : TimeWindowManager(Config{}) {}

    // Add packet to appropriate window(s)
    void add_packet(uint64_t timestamp_ns,
                   uint32_t packet_len,
                   bool is_forward);

    // Get all windows
    const std::deque<WindowStats>& get_windows() const { return windows_; }

    // Get statistics from windows
    double get_subflow_fwd_packets_mean() const;
    double get_subflow_fwd_bytes_mean() const;
    double get_subflow_bwd_packets_mean() const;
    double get_subflow_bwd_bytes_mean() const;

    // Bulk transfer stats
    double get_fwd_bulk_rate_avg() const;
    double get_fwd_bulk_size_avg() const;
    double get_fwd_bulk_duration_avg() const;
    double get_fwd_bulk_packets_avg() const;     // NEW: avg packets in forward bulks
    double get_bwd_bulk_rate_avg() const;
    double get_bwd_bulk_size_avg() const;
    double get_bwd_bulk_duration_avg() const;
    double get_bwd_bulk_packets_avg() const;     // NEW: avg packets in backward bulks

    // Init window (first packets)
    uint64_t get_init_fwd_win_bytes() const;
    uint64_t get_init_bwd_win_bytes() const;

    // Clear old windows
    void cleanup_old_windows(uint64_t current_ns);

private:
    Config config_;
    std::deque<WindowStats> windows_;

    // Init window tracking (first N bytes)
    uint64_t init_fwd_bytes_ = 0;
    uint64_t init_bwd_bytes_ = 0;
    bool init_fwd_complete_ = false;
    bool init_bwd_complete_ = false;
    static constexpr uint64_t INIT_WIN_SIZE = 10;  // First 10 packets
    uint32_t init_fwd_packet_count_ = 0;
    uint32_t init_bwd_packet_count_ = 0;

    // Bulk transfer tracking
    struct BulkState {
        bool active = false;
        uint64_t start_ns = 0;
        uint64_t last_packet_ns = 0;
        uint64_t bytes = 0;
        uint32_t packets = 0;
    };
    BulkState fwd_bulk_;
    BulkState bwd_bulk_;

    std::vector<double> fwd_bulk_rates_;
    std::vector<double> fwd_bulk_sizes_;
    std::vector<double> fwd_bulk_durations_;
    std::vector<double> fwd_bulk_packet_counts_;  // NEW: packet counts per bulk
    std::vector<double> bwd_bulk_rates_;
    std::vector<double> bwd_bulk_sizes_;
    std::vector<double> bwd_bulk_durations_;
    std::vector<double> bwd_bulk_packet_counts_;  // NEW: packet counts per bulk

    // Helper methods
    WindowStats* get_or_create_window(uint64_t timestamp_ns);
    void update_bulk_transfer(uint64_t timestamp_ns,
                             uint32_t packet_len,
                             bool is_forward);
    void finalize_bulk(BulkState& bulk,
                      std::vector<double>& rates,
                      std::vector<double>& sizes,
                      std::vector<double>& durations,
                      std::vector<double>& packet_counts);
    double calculate_mean(const std::vector<double>& values) const;
};

} // namespace sniffer