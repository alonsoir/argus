// sniffer/src/userspace/time_window_manager.cpp
#include "time_window_manager.hpp"
#include <numeric>
#include <iostream>

namespace sniffer {

TimeWindowManager::TimeWindowManager(const Config& config)
    : config_(config) {
}

void TimeWindowManager::add_packet(uint64_t timestamp_ns,
                                   uint32_t packet_len,
                                   bool is_forward) {
    // Track init window (first 10 packets per direction)
    if (is_forward && !init_fwd_complete_) {
        init_fwd_bytes_ += packet_len;
        init_fwd_packet_count_++;
        if (init_fwd_packet_count_ >= INIT_WIN_SIZE) {
            init_fwd_complete_ = true;
        }
    } else if (!is_forward && !init_bwd_complete_) {
        init_bwd_bytes_ += packet_len;
        init_bwd_packet_count_++;
        if (init_bwd_packet_count_ >= INIT_WIN_SIZE) {
            init_bwd_complete_ = true;
        }
    }

    // Get or create window for this timestamp
    WindowStats* window = get_or_create_window(timestamp_ns);
    if (window) {
        if (is_forward) {
            window->subflow_fwd_packets++;
            window->subflow_fwd_bytes += packet_len;
        } else {
            window->subflow_bwd_packets++;
            window->subflow_bwd_bytes += packet_len;
        }
    }

    // Update bulk transfer detection
    update_bulk_transfer(timestamp_ns, packet_len, is_forward);
}

WindowStats* TimeWindowManager::get_or_create_window(uint64_t timestamp_ns) {
    // Check if timestamp fits in existing window
    for (auto& window : windows_) {
        if (window.contains(timestamp_ns)) {
            return &window;
        }
    }

    // Create new window
    uint64_t window_start = (timestamp_ns / config_.window_duration_ns) * config_.window_duration_ns;
    uint64_t window_end = window_start + config_.window_duration_ns;

    windows_.emplace_back(window_start, window_end);

    // Cleanup if too many windows
    if (windows_.size() > config_.max_windows) {
        windows_.pop_front();
    }

    return &windows_.back();
}

void TimeWindowManager::update_bulk_transfer(uint64_t timestamp_ns,
                                             uint32_t packet_len,
                                             bool is_forward) {
    BulkState& bulk = is_forward ? fwd_bulk_ : bwd_bulk_;
    auto& rates = is_forward ? fwd_bulk_rates_ : bwd_bulk_rates_;
    auto& sizes = is_forward ? fwd_bulk_sizes_ : bwd_bulk_sizes_;
    auto& durations = is_forward ? fwd_bulk_durations_ : bwd_bulk_durations_;
    auto& packet_counts = is_forward ? fwd_bulk_packet_counts_ : bwd_bulk_packet_counts_;

    if (!bulk.active) {
        // Start new bulk transfer
        bulk.active = true;
        bulk.start_ns = timestamp_ns;
        bulk.last_packet_ns = timestamp_ns;
        bulk.bytes = packet_len;
        bulk.packets = 1;
    } else {
        // Check if gap is too large (end of bulk)
        uint64_t gap_ns = timestamp_ns - bulk.last_packet_ns;

        if (gap_ns > config_.bulk_gap_threshold_ns) {
            // Finalize previous bulk
            if (bulk.bytes >= config_.bulk_threshold_bytes &&
                bulk.packets >= config_.bulk_threshold_packets) {
                finalize_bulk(bulk, rates, sizes, durations, packet_counts);
            }

            // Start new bulk
            bulk.start_ns = timestamp_ns;
            bulk.bytes = packet_len;
            bulk.packets = 1;
        } else {
            // Continue current bulk
            bulk.bytes += packet_len;
            bulk.packets++;
        }

        bulk.last_packet_ns = timestamp_ns;
    }
}

void TimeWindowManager::finalize_bulk(BulkState& bulk,
                                      std::vector<double>& rates,
                                      std::vector<double>& sizes,
                                      std::vector<double>& durations,
                                      std::vector<double>& packet_counts) {
    if (bulk.packets == 0) return;

    uint64_t duration_ns = bulk.last_packet_ns - bulk.start_ns;
    if (duration_ns == 0) duration_ns = 1;

    double duration_sec = duration_ns / 1'000'000'000.0;
    double rate = (bulk.bytes * 8.0) / duration_sec;  // bits per second

    rates.push_back(rate);
    sizes.push_back(static_cast<double>(bulk.bytes));
    durations.push_back(duration_sec);
    packet_counts.push_back(static_cast<double>(bulk.packets));  // Store packet count

    // Reset bulk
    bulk.active = false;
    bulk.start_ns = 0;
    bulk.last_packet_ns = 0;
    bulk.bytes = 0;
    bulk.packets = 0;
}

void TimeWindowManager::cleanup_old_windows(uint64_t current_ns) {
    // Remove windows older than 2x window duration
    uint64_t cutoff_ns = current_ns - (2 * config_.window_duration_ns);

    while (!windows_.empty() && windows_.front().window_end_ns < cutoff_ns) {
        windows_.pop_front();
    }
}

// Subflow statistics
double TimeWindowManager::get_subflow_fwd_packets_mean() const {
    if (windows_.empty()) return 0.0;

    uint64_t total = 0;
    for (const auto& window : windows_) {
        total += window.subflow_fwd_packets;
    }

    return static_cast<double>(total) / static_cast<double>(windows_.size());
}

double TimeWindowManager::get_subflow_fwd_bytes_mean() const {
    if (windows_.empty()) return 0.0;

    uint64_t total = 0;
    for (const auto& window : windows_) {
        total += window.subflow_fwd_bytes;
    }

    return static_cast<double>(total) / static_cast<double>(windows_.size());
}

double TimeWindowManager::get_subflow_bwd_packets_mean() const {
    if (windows_.empty()) return 0.0;

    uint64_t total = 0;
    for (const auto& window : windows_) {
        total += window.subflow_bwd_packets;
    }

    return static_cast<double>(total) / static_cast<double>(windows_.size());
}

double TimeWindowManager::get_subflow_bwd_bytes_mean() const {
    if (windows_.empty()) return 0.0;

    uint64_t total = 0;
    for (const auto& window : windows_) {
        total += window.subflow_bwd_bytes;
    }

    return static_cast<double>(total) / static_cast<double>(windows_.size());
}

// Bulk transfer statistics
double TimeWindowManager::get_fwd_bulk_rate_avg() const {
    return calculate_mean(fwd_bulk_rates_);
}

double TimeWindowManager::get_fwd_bulk_size_avg() const {
    return calculate_mean(fwd_bulk_sizes_);
}

double TimeWindowManager::get_fwd_bulk_duration_avg() const {
    return calculate_mean(fwd_bulk_durations_);
}

double TimeWindowManager::get_fwd_bulk_packets_avg() const {
    return calculate_mean(fwd_bulk_packet_counts_);
}

double TimeWindowManager::get_bwd_bulk_rate_avg() const {
    return calculate_mean(bwd_bulk_rates_);
}

double TimeWindowManager::get_bwd_bulk_size_avg() const {
    return calculate_mean(bwd_bulk_sizes_);
}

double TimeWindowManager::get_bwd_bulk_duration_avg() const {
    return calculate_mean(bwd_bulk_durations_);
}

double TimeWindowManager::get_bwd_bulk_packets_avg() const {
    return calculate_mean(bwd_bulk_packet_counts_);
}

// Init window bytes
uint64_t TimeWindowManager::get_init_fwd_win_bytes() const {
    return init_fwd_bytes_;
}

uint64_t TimeWindowManager::get_init_bwd_win_bytes() const {
    return init_bwd_bytes_;
}

// Helper
double TimeWindowManager::calculate_mean(const std::vector<double>& values) const {
    if (values.empty()) return 0.0;

    double sum = std::accumulate(values.begin(), values.end(), 0.0);
    return sum / static_cast<double>(values.size());
}

} // namespace sniffer