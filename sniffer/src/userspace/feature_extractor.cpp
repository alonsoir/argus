// sniffer/src/userspace/feature_extractor.cpp
// FINAL VERSION: 83 complete features
#include "feature_extractor.hpp"
#include <numeric>
#include <cmath>
#include <algorithm>
#include <iostream>

namespace sniffer {

std::array<double, FeatureExtractor::FEATURE_COUNT>
FeatureExtractor::extract_features(const FlowStatistics& flow) const {

    std::array<double, FEATURE_COUNT> features;
    features.fill(0.0);

    // === ORIGINAL 23 ===
    features[DURATION] = static_cast<double>(flow.get_duration_us());
    features[SPKTS] = static_cast<double>(flow.spkts);
    features[DPKTS] = static_cast<double>(flow.dpkts);
    features[SBYTES] = static_cast<double>(flow.sbytes);
    features[DBYTES] = static_cast<double>(flow.dbytes);
    features[SLOAD] = extract_sload(flow);
    features[SMEAN] = extract_smean(flow);
    features[DMEAN] = extract_dmean(flow);
    features[FLOW_IAT_MEAN] = extract_flow_iat_mean(flow);
    features[FLOW_IAT_STD] = extract_flow_iat_std(flow);
    features[FWD_PSH_FLAGS] = static_cast<double>(flow.fwd_psh_flags);
    features[BWD_PSH_FLAGS] = static_cast<double>(flow.bwd_psh_flags);
    features[FWD_URG_FLAGS] = static_cast<double>(flow.fwd_urg_flags);
    features[BWD_URG_FLAGS] = static_cast<double>(flow.bwd_urg_flags);
    features[PACKET_LEN_MEAN] = extract_packet_len_mean(flow);
    features[PACKET_LEN_STD] = extract_packet_len_std(flow);
    features[PACKET_LEN_VAR] = extract_packet_len_var(flow);
    features[FIN_FLAG_COUNT] = static_cast<double>(flow.fin_count);
    features[SYN_FLAG_COUNT] = static_cast<double>(flow.syn_count);
    features[RST_FLAG_COUNT] = static_cast<double>(flow.rst_count);
    features[PSH_FLAG_COUNT] = static_cast<double>(flow.psh_count);
    features[ACK_FLAG_COUNT] = static_cast<double>(flow.ack_count);
    features[URG_FLAG_COUNT] = static_cast<double>(flow.urg_count);

    // === PHASE 1: 20 ===
    features[DLOAD] = extract_dload(flow);
    features[RATE] = extract_rate(flow);
    features[SRATE] = extract_srate(flow);
    features[DRATE] = extract_drate(flow);
    features[SPKTS_RATIO] = extract_spkts_ratio(flow);
    features[SBYTES_RATIO] = extract_sbytes_ratio(flow);
    features[FLOW_IAT_MAX] = extract_flow_iat_max(flow);
    features[FLOW_IAT_MIN] = extract_flow_iat_min(flow);
    features[PACKET_LEN_MAX] = extract_packet_len_max(flow);
    features[PACKET_LEN_MIN] = extract_packet_len_min(flow);
    features[FWD_LEN_MAX] = extract_fwd_len_max(flow);
    features[FWD_LEN_MIN] = extract_fwd_len_min(flow);
    features[FWD_LEN_TOT] = extract_fwd_len_tot(flow);
    features[BWD_LEN_MAX] = extract_bwd_len_max(flow);
    features[BWD_LEN_MIN] = extract_bwd_len_min(flow);
    features[BWD_LEN_TOT] = extract_bwd_len_tot(flow);
    features[ECE_FLAG_COUNT] = static_cast<double>(flow.ece_count);
    features[CWR_FLAG_COUNT] = static_cast<double>(flow.cwr_count);
    features[FWD_HEADER_LEN_MEAN] = extract_fwd_header_len_mean(flow);
    features[BWD_HEADER_LEN_MEAN] = extract_bwd_header_len_mean(flow);

    // === PHASE 2: 15 ===
    features[FWD_IAT_MEAN] = extract_fwd_iat_mean(flow);
    features[FWD_IAT_STD] = extract_fwd_iat_std(flow);
    features[FWD_IAT_MAX] = extract_fwd_iat_max(flow);
    features[FWD_IAT_MIN] = extract_fwd_iat_min(flow);
    features[FWD_IAT_TOT] = extract_fwd_iat_tot(flow);
    features[BWD_IAT_MEAN] = extract_bwd_iat_mean(flow);
    features[BWD_IAT_STD] = extract_bwd_iat_std(flow);
    features[BWD_IAT_MAX] = extract_bwd_iat_max(flow);
    features[BWD_IAT_MIN] = extract_bwd_iat_min(flow);
    features[BWD_IAT_TOT] = extract_bwd_iat_tot(flow);
    features[ACTIVE_MEAN] = extract_active_mean(flow);
    features[ACTIVE_MAX] = extract_active_max(flow);
    features[IDLE_MEAN] = extract_idle_mean(flow);
    features[IDLE_MAX] = extract_idle_max(flow);
    features[FWD_LEN_STD] = extract_fwd_len_std(flow);

    // === PHASE 3: 20 ===
    features[SUBFLOW_FWD_PACKETS] = extract_subflow_fwd_packets(flow);
    features[SUBFLOW_FWD_BYTES] = extract_subflow_fwd_bytes(flow);
    features[SUBFLOW_BWD_PACKETS] = extract_subflow_bwd_packets(flow);
    features[SUBFLOW_BWD_BYTES] = extract_subflow_bwd_bytes(flow);
    features[FWD_BULK_RATE_AVG] = extract_fwd_bulk_rate_avg(flow);
    features[FWD_BULK_SIZE_AVG] = extract_fwd_bulk_size_avg(flow);
    features[FWD_BULK_DURATION_AVG] = extract_fwd_bulk_duration_avg(flow);
    features[BWD_BULK_RATE_AVG] = extract_bwd_bulk_rate_avg(flow);
    features[BWD_BULK_SIZE_AVG] = extract_bwd_bulk_size_avg(flow);
    features[BWD_BULK_DURATION_AVG] = extract_bwd_bulk_duration_avg(flow);
    features[INIT_FWD_WIN_BYTES] = extract_init_fwd_win_bytes(flow);
    features[INIT_BWD_WIN_BYTES] = extract_init_bwd_win_bytes(flow);
    features[BWD_LEN_STD] = extract_bwd_len_std(flow);
    features[FWD_HEADER_LEN_MAX] = extract_fwd_header_len_max(flow);
    features[FWD_HEADER_LEN_MIN] = extract_fwd_header_len_min(flow);
    features[BWD_HEADER_LEN_MAX] = extract_bwd_header_len_max(flow);
    features[BWD_HEADER_LEN_MIN] = extract_bwd_header_len_min(flow);
    features[FLOW_PKTS_PER_SEC] = extract_flow_pkts_per_sec(flow);
    features[FLOW_BYTES_PER_SEC] = extract_flow_bytes_per_sec(flow);
    features[DOWN_UP_RATIO] = extract_down_up_ratio(flow);

    // === PHASE 4: 5 FINAL ===
    features[AVG_PACKET_SIZE] = extract_avg_packet_size(flow);
    features[AVG_FWD_SEGMENT_SIZE] = extract_avg_fwd_segment_size(flow);
    features[AVG_BWD_SEGMENT_SIZE] = extract_avg_bwd_segment_size(flow);
    features[FWD_AVG_PACKETS_BULK] = extract_fwd_avg_packets_bulk(flow);
    features[BWD_AVG_PACKETS_BULK] = extract_bwd_avg_packets_bulk(flow);

    return features;
}

// ============================================================================
// ORIGINAL + PHASE 1/2/3 EXTRACTORS (keep same as before)
// ============================================================================

double FeatureExtractor::extract_duration(const FlowStatistics& flow) const {
    return static_cast<double>(flow.get_duration_us());
}

double FeatureExtractor::extract_sload(const FlowStatistics& flow) const {
    uint64_t duration_us = flow.get_duration_us();
    if (duration_us == 0) return 0.0;
    double duration_sec = duration_us / 1'000'000.0;
    return (flow.sbytes * 8.0) / duration_sec;
}

double FeatureExtractor::extract_smean(const FlowStatistics& flow) const {
    return calculate_mean(flow.fwd_lengths);
}

double FeatureExtractor::extract_dmean(const FlowStatistics& flow) const {
    return calculate_mean(flow.bwd_lengths);
}

double FeatureExtractor::extract_flow_iat_mean(const FlowStatistics& flow) const {
    return calculate_iat_mean(flow.packet_timestamps);
}

double FeatureExtractor::extract_flow_iat_std(const FlowStatistics& flow) const {
    return calculate_iat_std(flow.packet_timestamps);
}

double FeatureExtractor::extract_packet_len_mean(const FlowStatistics& flow) const {
    return calculate_mean(flow.all_lengths);
}

double FeatureExtractor::extract_packet_len_std(const FlowStatistics& flow) const {
    return calculate_std(flow.all_lengths);
}

double FeatureExtractor::extract_packet_len_var(const FlowStatistics& flow) const {
    return calculate_variance(flow.all_lengths);
}

double FeatureExtractor::extract_dload(const FlowStatistics& flow) const {
    uint64_t duration_us = flow.get_duration_us();
    if (duration_us == 0) return 0.0;
    double duration_sec = duration_us / 1'000'000.0;
    return (flow.dbytes * 8.0) / duration_sec;
}

double FeatureExtractor::extract_rate(const FlowStatistics& flow) const {
    uint64_t duration_us = flow.get_duration_us();
    if (duration_us == 0) return 0.0;
    double duration_sec = duration_us / 1'000'000.0;
    uint64_t total_packets = flow.spkts + flow.dpkts;
    return static_cast<double>(total_packets) / duration_sec;
}

double FeatureExtractor::extract_srate(const FlowStatistics& flow) const {
    uint64_t duration_us = flow.get_duration_us();
    if (duration_us == 0) return 0.0;
    double duration_sec = duration_us / 1'000'000.0;
    return static_cast<double>(flow.spkts) / duration_sec;
}

double FeatureExtractor::extract_drate(const FlowStatistics& flow) const {
    uint64_t duration_us = flow.get_duration_us();
    if (duration_us == 0) return 0.0;
    double duration_sec = duration_us / 1'000'000.0;
    return static_cast<double>(flow.dpkts) / duration_sec;
}

double FeatureExtractor::extract_spkts_ratio(const FlowStatistics& flow) const {
    uint64_t total_packets = flow.spkts + flow.dpkts;
    if (total_packets == 0) return 0.0;
    return static_cast<double>(flow.spkts) / static_cast<double>(total_packets);
}

double FeatureExtractor::extract_sbytes_ratio(const FlowStatistics& flow) const {
    uint64_t total_bytes = flow.sbytes + flow.dbytes;
    if (total_bytes == 0) return 0.0;
    return static_cast<double>(flow.sbytes) / static_cast<double>(total_bytes);
}

double FeatureExtractor::extract_flow_iat_max(const FlowStatistics& flow) const {
    return calculate_iat_max(flow.packet_timestamps);
}

double FeatureExtractor::extract_flow_iat_min(const FlowStatistics& flow) const {
    return calculate_iat_min(flow.packet_timestamps);
}

double FeatureExtractor::extract_packet_len_max(const FlowStatistics& flow) const {
    return calculate_max(flow.all_lengths);
}

double FeatureExtractor::extract_packet_len_min(const FlowStatistics& flow) const {
    return calculate_min(flow.all_lengths);
}

double FeatureExtractor::extract_fwd_len_max(const FlowStatistics& flow) const {
    return calculate_max(flow.fwd_lengths);
}

double FeatureExtractor::extract_fwd_len_min(const FlowStatistics& flow) const {
    return calculate_min(flow.fwd_lengths);
}

double FeatureExtractor::extract_fwd_len_tot(const FlowStatistics& flow) const {
    return calculate_sum(flow.fwd_lengths);
}

double FeatureExtractor::extract_bwd_len_max(const FlowStatistics& flow) const {
    return calculate_max(flow.bwd_lengths);
}

double FeatureExtractor::extract_bwd_len_min(const FlowStatistics& flow) const {
    return calculate_min(flow.bwd_lengths);
}

double FeatureExtractor::extract_bwd_len_tot(const FlowStatistics& flow) const {
    return calculate_sum(flow.bwd_lengths);
}

double FeatureExtractor::extract_fwd_header_len_mean(const FlowStatistics& flow) const {
    return calculate_mean_u16(flow.fwd_header_lengths);
}

double FeatureExtractor::extract_bwd_header_len_mean(const FlowStatistics& flow) const {
    return calculate_mean_u16(flow.bwd_header_lengths);
}

// ============================================================================
// PHASE 2 EXTRACTORS
// ============================================================================

double FeatureExtractor::extract_fwd_iat_mean(const FlowStatistics& flow) const {
    return calculate_iat_mean(flow.fwd_timestamps);
}

double FeatureExtractor::extract_fwd_iat_std(const FlowStatistics& flow) const {
    return calculate_iat_std(flow.fwd_timestamps);
}

double FeatureExtractor::extract_fwd_iat_max(const FlowStatistics& flow) const {
    return calculate_iat_max(flow.fwd_timestamps);
}

double FeatureExtractor::extract_fwd_iat_min(const FlowStatistics& flow) const {
    return calculate_iat_min(flow.fwd_timestamps);
}

double FeatureExtractor::extract_fwd_iat_tot(const FlowStatistics& flow) const {
    return calculate_iat_tot(flow.fwd_timestamps);
}

double FeatureExtractor::extract_bwd_iat_mean(const FlowStatistics& flow) const {
    return calculate_iat_mean(flow.bwd_timestamps);
}

double FeatureExtractor::extract_bwd_iat_std(const FlowStatistics& flow) const {
    return calculate_iat_std(flow.bwd_timestamps);
}

double FeatureExtractor::extract_bwd_iat_max(const FlowStatistics& flow) const {
    return calculate_iat_max(flow.bwd_timestamps);
}

double FeatureExtractor::extract_bwd_iat_min(const FlowStatistics& flow) const {
    return calculate_iat_min(flow.bwd_timestamps);
}

double FeatureExtractor::extract_bwd_iat_tot(const FlowStatistics& flow) const {
    return calculate_iat_tot(flow.bwd_timestamps);
}

double FeatureExtractor::extract_active_mean(const FlowStatistics& flow) const {
    auto times = compute_active_idle_times(flow.packet_timestamps);
    if (times.active_times.empty()) return 0.0;
    double sum = std::accumulate(times.active_times.begin(), times.active_times.end(), 0.0);
    return sum / static_cast<double>(times.active_times.size());
}

double FeatureExtractor::extract_active_max(const FlowStatistics& flow) const {
    auto times = compute_active_idle_times(flow.packet_timestamps);
    if (times.active_times.empty()) return 0.0;
    auto max_it = std::max_element(times.active_times.begin(), times.active_times.end());
    return static_cast<double>(*max_it);
}

double FeatureExtractor::extract_idle_mean(const FlowStatistics& flow) const {
    auto times = compute_active_idle_times(flow.packet_timestamps);
    if (times.idle_times.empty()) return 0.0;
    double sum = std::accumulate(times.idle_times.begin(), times.idle_times.end(), 0.0);
    return sum / static_cast<double>(times.idle_times.size());
}

double FeatureExtractor::extract_idle_max(const FlowStatistics& flow) const {
    auto times = compute_active_idle_times(flow.packet_timestamps);
    if (times.idle_times.empty()) return 0.0;
    auto max_it = std::max_element(times.idle_times.begin(), times.idle_times.end());
    return static_cast<double>(*max_it);
}

double FeatureExtractor::extract_fwd_len_std(const FlowStatistics& flow) const {
    return calculate_std(flow.fwd_lengths);
}

// ============================================================================
// PHASE 3 EXTRACTORS
// ============================================================================

double FeatureExtractor::extract_subflow_fwd_packets(const FlowStatistics& flow) const {
    if (!flow.time_windows) return 0.0;
    return flow.time_windows->get_subflow_fwd_packets_mean();
}

double FeatureExtractor::extract_subflow_fwd_bytes(const FlowStatistics& flow) const {
    if (!flow.time_windows) return 0.0;
    return flow.time_windows->get_subflow_fwd_bytes_mean();
}

double FeatureExtractor::extract_subflow_bwd_packets(const FlowStatistics& flow) const {
    if (!flow.time_windows) return 0.0;
    return flow.time_windows->get_subflow_bwd_packets_mean();
}

double FeatureExtractor::extract_subflow_bwd_bytes(const FlowStatistics& flow) const {
    if (!flow.time_windows) return 0.0;
    return flow.time_windows->get_subflow_bwd_bytes_mean();
}

double FeatureExtractor::extract_fwd_bulk_rate_avg(const FlowStatistics& flow) const {
    if (!flow.time_windows) return 0.0;
    return flow.time_windows->get_fwd_bulk_rate_avg();
}

double FeatureExtractor::extract_fwd_bulk_size_avg(const FlowStatistics& flow) const {
    if (!flow.time_windows) return 0.0;
    return flow.time_windows->get_fwd_bulk_size_avg();
}

double FeatureExtractor::extract_fwd_bulk_duration_avg(const FlowStatistics& flow) const {
    if (!flow.time_windows) return 0.0;
    return flow.time_windows->get_fwd_bulk_duration_avg();
}

double FeatureExtractor::extract_bwd_bulk_rate_avg(const FlowStatistics& flow) const {
    if (!flow.time_windows) return 0.0;
    return flow.time_windows->get_bwd_bulk_rate_avg();
}

double FeatureExtractor::extract_bwd_bulk_size_avg(const FlowStatistics& flow) const {
    if (!flow.time_windows) return 0.0;
    return flow.time_windows->get_bwd_bulk_size_avg();
}

double FeatureExtractor::extract_bwd_bulk_duration_avg(const FlowStatistics& flow) const {
    if (!flow.time_windows) return 0.0;
    return flow.time_windows->get_bwd_bulk_duration_avg();
}

double FeatureExtractor::extract_init_fwd_win_bytes(const FlowStatistics& flow) const {
    if (!flow.time_windows) return 0.0;
    return static_cast<double>(flow.time_windows->get_init_fwd_win_bytes());
}

double FeatureExtractor::extract_init_bwd_win_bytes(const FlowStatistics& flow) const {
    if (!flow.time_windows) return 0.0;
    return static_cast<double>(flow.time_windows->get_init_bwd_win_bytes());
}

double FeatureExtractor::extract_bwd_len_std(const FlowStatistics& flow) const {
    return calculate_std(flow.bwd_lengths);
}

double FeatureExtractor::extract_fwd_header_len_max(const FlowStatistics& flow) const {
    return calculate_max_u16(flow.fwd_header_lengths);
}

double FeatureExtractor::extract_fwd_header_len_min(const FlowStatistics& flow) const {
    return calculate_min_u16(flow.fwd_header_lengths);
}

double FeatureExtractor::extract_bwd_header_len_max(const FlowStatistics& flow) const {
    return calculate_max_u16(flow.bwd_header_lengths);
}

double FeatureExtractor::extract_bwd_header_len_min(const FlowStatistics& flow) const {
    return calculate_min_u16(flow.bwd_header_lengths);
}

double FeatureExtractor::extract_flow_pkts_per_sec(const FlowStatistics& flow) const {
    uint64_t duration_us = flow.get_duration_us();
    if (duration_us == 0) return 0.0;
    double duration_sec = duration_us / 1'000'000.0;
    uint64_t total_packets = flow.spkts + flow.dpkts;
    return static_cast<double>(total_packets) / duration_sec;
}

double FeatureExtractor::extract_flow_bytes_per_sec(const FlowStatistics& flow) const {
    uint64_t duration_us = flow.get_duration_us();
    if (duration_us == 0) return 0.0;
    double duration_sec = duration_us / 1'000'000.0;
    uint64_t total_bytes = flow.sbytes + flow.dbytes;
    return static_cast<double>(total_bytes) / duration_sec;
}

double FeatureExtractor::extract_down_up_ratio(const FlowStatistics& flow) const {
    if (flow.sbytes == 0) return 0.0;
    return static_cast<double>(flow.dbytes) / static_cast<double>(flow.sbytes);
}

// ============================================================================
// PHASE 4: LAST 5 FEATURES
// ============================================================================

double FeatureExtractor::extract_avg_packet_size(const FlowStatistics& flow) const {
    uint64_t total_packets = flow.spkts + flow.dpkts;
    if (total_packets == 0) return 0.0;
    uint64_t total_bytes = flow.sbytes + flow.dbytes;
    return static_cast<double>(total_bytes) / static_cast<double>(total_packets);
}

double FeatureExtractor::extract_avg_fwd_segment_size(const FlowStatistics& flow) const {
    if (flow.spkts == 0) return 0.0;
    return static_cast<double>(flow.sbytes) / static_cast<double>(flow.spkts);
}

double FeatureExtractor::extract_avg_bwd_segment_size(const FlowStatistics& flow) const {
    if (flow.dpkts == 0) return 0.0;
    return static_cast<double>(flow.dbytes) / static_cast<double>(flow.dpkts);
}

double FeatureExtractor::extract_fwd_avg_packets_bulk(const FlowStatistics& flow) const {
    if (!flow.time_windows) return 0.0;
    return flow.time_windows->get_fwd_bulk_packets_avg();
}

double FeatureExtractor::extract_bwd_avg_packets_bulk(const FlowStatistics& flow) const {
    if (!flow.time_windows) return 0.0;
    return flow.time_windows->get_bwd_bulk_packets_avg();
}

// ============================================================================
// STATISTICAL HELPERS (mantener igual)
// ============================================================================

double FeatureExtractor::calculate_mean(const std::vector<uint32_t>& values) const {
    if (values.empty()) return 0.0;
    double sum = std::accumulate(values.begin(), values.end(), 0.0);
    return sum / static_cast<double>(values.size());
}

double FeatureExtractor::calculate_mean_u16(const std::vector<uint16_t>& values) const {
    if (values.empty()) return 0.0;
    double sum = std::accumulate(values.begin(), values.end(), 0.0);
    return sum / static_cast<double>(values.size());
}

double FeatureExtractor::calculate_std(const std::vector<uint32_t>& values) const {
    if (values.size() < 2) return 0.0;
    double mean = calculate_mean(values);
    double sum_sq_diff = 0.0;
    for (uint32_t val : values) {
        double diff = static_cast<double>(val) - mean;
        sum_sq_diff += diff * diff;
    }
    double variance = sum_sq_diff / static_cast<double>(values.size());
    return std::sqrt(variance);
}

double FeatureExtractor::calculate_std_u16(const std::vector<uint16_t>& values) const {
    if (values.size() < 2) return 0.0;
    double mean = calculate_mean_u16(values);
    double sum_sq_diff = 0.0;
    for (uint16_t val : values) {
        double diff = static_cast<double>(val) - mean;
        sum_sq_diff += diff * diff;
    }
    double variance = sum_sq_diff / static_cast<double>(values.size());
    return std::sqrt(variance);
}

double FeatureExtractor::calculate_variance(const std::vector<uint32_t>& values) const {
    if (values.size() < 2) return 0.0;
    double mean = calculate_mean(values);
    double sum_sq_diff = 0.0;
    for (uint32_t val : values) {
        double diff = static_cast<double>(val) - mean;
        sum_sq_diff += diff * diff;
    }
    return sum_sq_diff / static_cast<double>(values.size());
}

double FeatureExtractor::calculate_max(const std::vector<uint32_t>& values) const {
    if (values.empty()) return 0.0;
    auto max_it = std::max_element(values.begin(), values.end());
    return static_cast<double>(*max_it);
}

double FeatureExtractor::calculate_max_u16(const std::vector<uint16_t>& values) const {
    if (values.empty()) return 0.0;
    auto max_it = std::max_element(values.begin(), values.end());
    return static_cast<double>(*max_it);
}

double FeatureExtractor::calculate_min(const std::vector<uint32_t>& values) const {
    if (values.empty()) return 0.0;
    auto min_it = std::min_element(values.begin(), values.end());
    return static_cast<double>(*min_it);
}

double FeatureExtractor::calculate_min_u16(const std::vector<uint16_t>& values) const {
    if (values.empty()) return 0.0;
    auto min_it = std::min_element(values.begin(), values.end());
    return static_cast<double>(*min_it);
}

double FeatureExtractor::calculate_sum(const std::vector<uint32_t>& values) const {
    if (values.empty()) return 0.0;
    return static_cast<double>(std::accumulate(values.begin(), values.end(), 0ULL));
}

std::vector<uint64_t> FeatureExtractor::compute_inter_arrival_times(
    const std::vector<uint64_t>& timestamps) const {
    std::vector<uint64_t> iats;
    if (timestamps.size() < 2) return iats;
    iats.reserve(timestamps.size() - 1);
    for (size_t i = 1; i < timestamps.size(); ++i) {
        if (timestamps[i] >= timestamps[i-1]) {
            iats.push_back(timestamps[i] - timestamps[i-1]);
        }
    }
    return iats;
}

double FeatureExtractor::calculate_iat_mean(const std::vector<uint64_t>& timestamps) const {
    auto iats = compute_inter_arrival_times(timestamps);
    if (iats.empty()) return 0.0;
    double sum = std::accumulate(iats.begin(), iats.end(), 0.0);
    return sum / static_cast<double>(iats.size());
}

double FeatureExtractor::calculate_iat_std(const std::vector<uint64_t>& timestamps) const {
    auto iats = compute_inter_arrival_times(timestamps);
    if (iats.size() < 2) return 0.0;
    double sum = std::accumulate(iats.begin(), iats.end(), 0.0);
    double mean = sum / static_cast<double>(iats.size());
    double sum_sq_diff = 0.0;
    for (uint64_t iat : iats) {
        double diff = static_cast<double>(iat) - mean;
        sum_sq_diff += diff * diff;
    }
    double variance = sum_sq_diff / static_cast<double>(iats.size());
    return std::sqrt(variance);
}

double FeatureExtractor::calculate_iat_max(const std::vector<uint64_t>& timestamps) const {
    auto iats = compute_inter_arrival_times(timestamps);
    if (iats.empty()) return 0.0;
    auto max_it = std::max_element(iats.begin(), iats.end());
    return static_cast<double>(*max_it);
}

double FeatureExtractor::calculate_iat_min(const std::vector<uint64_t>& timestamps) const {
    auto iats = compute_inter_arrival_times(timestamps);
    if (iats.empty()) return 0.0;
    auto min_it = std::min_element(iats.begin(), iats.end());
    return static_cast<double>(*min_it);
}

double FeatureExtractor::calculate_iat_tot(const std::vector<uint64_t>& timestamps) const {
    auto iats = compute_inter_arrival_times(timestamps);
    if (iats.empty()) return 0.0;
    return static_cast<double>(std::accumulate(iats.begin(), iats.end(), 0ULL));
}

FeatureExtractor::ActiveIdleTimes FeatureExtractor::compute_active_idle_times(
    const std::vector<uint64_t>& timestamps) const {
    ActiveIdleTimes result;
    if (timestamps.size() < 2) return result;

    const uint64_t ACTIVE_THRESHOLD_NS = 1'000'000'000ULL;
    auto iats = compute_inter_arrival_times(timestamps);

    uint64_t current_active = 0;
    uint64_t current_idle = 0;
    bool in_active_period = false;

    for (uint64_t iat : iats) {
        if (iat < ACTIVE_THRESHOLD_NS) {
            if (in_active_period) {
                current_active += iat;
            } else {
                if (current_idle > 0) {
                    result.idle_times.push_back(current_idle);
                    current_idle = 0;
                }
                current_active = iat;
                in_active_period = true;
            }
        } else {
            if (!in_active_period) {
                current_idle += iat;
            } else {
                if (current_active > 0) {
                    result.active_times.push_back(current_active);
                    current_active = 0;
                }
                current_idle = iat;
                in_active_period = false;
            }
        }
    }

    if (current_active > 0) result.active_times.push_back(current_active);
    if (current_idle > 0) result.idle_times.push_back(current_idle);

    return result;
}

// Feature names (all 83)
const char* FeatureExtractor::get_feature_name(size_t index) {
    static const char* names[] = {
        // Original 23
        "duration", "spkts", "dpkts", "sbytes", "dbytes", "sload", "smean", "dmean",
        "flow_iat_mean", "flow_iat_std", "fwd_psh_flags", "bwd_psh_flags",
        "fwd_urg_flags", "bwd_urg_flags", "packet_len_mean", "packet_len_std",
        "packet_len_var", "fin_flag_count", "syn_flag_count", "rst_flag_count",
        "psh_flag_count", "ack_flag_count", "urg_flag_count",
        // Phase 1: 20
        "dload", "rate", "srate", "drate", "spkts_ratio", "sbytes_ratio",
        "flow_iat_max", "flow_iat_min", "packet_len_max", "packet_len_min",
        "fwd_len_max", "fwd_len_min", "fwd_len_tot", "bwd_len_max", "bwd_len_min",
        "bwd_len_tot", "ece_flag_count", "cwr_flag_count", "fwd_header_len_mean",
        "bwd_header_len_mean",
        // Phase 2: 15
        "fwd_iat_mean", "fwd_iat_std", "fwd_iat_max", "fwd_iat_min", "fwd_iat_tot",
        "bwd_iat_mean", "bwd_iat_std", "bwd_iat_max", "bwd_iat_min", "bwd_iat_tot",
        "active_mean", "active_max", "idle_mean", "idle_max", "fwd_len_std",
        // Phase 3: 20
        "subflow_fwd_packets", "subflow_fwd_bytes", "subflow_bwd_packets", "subflow_bwd_bytes",
        "fwd_bulk_rate_avg", "fwd_bulk_size_avg", "fwd_bulk_duration_avg",
        "bwd_bulk_rate_avg", "bwd_bulk_size_avg", "bwd_bulk_duration_avg",
        "init_fwd_win_bytes", "init_bwd_win_bytes", "bwd_len_std",
        "fwd_header_len_max", "fwd_header_len_min", "bwd_header_len_max", "bwd_header_len_min",
        "flow_pkts_per_sec", "flow_bytes_per_sec", "down_up_ratio",
        // Phase 4: 5 final
        "avg_packet_size", "avg_fwd_segment_size", "avg_bwd_segment_size",
        "fwd_avg_packets_bulk", "bwd_avg_packets_bulk"
    };

    if (index >= FEATURE_COUNT) return "UNKNOWN";
    return names[index];
}

} // namespace sniffer