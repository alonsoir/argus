// sniffer/include/feature_extractor.hpp
#pragma once

#include "flow_manager.hpp"
#include <array>
#include <vector>

namespace sniffer {

class FeatureExtractor {
public:
    // Phase 4: 78 -> 83 features (100% COMPLETE!)
    static constexpr size_t FEATURE_COUNT = 83;

    // Feature indices for the array
    enum FeatureIndex {
        // === ORIGINAL 23 ===
        DURATION = 0,
        SPKTS,
        DPKTS,
        SBYTES,
        DBYTES,
        SLOAD,
        SMEAN,
        DMEAN,
        FLOW_IAT_MEAN,
        FLOW_IAT_STD,
        FWD_PSH_FLAGS,
        BWD_PSH_FLAGS,
        FWD_URG_FLAGS,
        BWD_URG_FLAGS,
        PACKET_LEN_MEAN,
        PACKET_LEN_STD,
        PACKET_LEN_VAR,
        FIN_FLAG_COUNT,
        SYN_FLAG_COUNT,
        RST_FLAG_COUNT,
        PSH_FLAG_COUNT,
        ACK_FLAG_COUNT,
        URG_FLAG_COUNT,

        // === PHASE 1: 20 features ===
        DLOAD,
        RATE,
        SRATE,
        DRATE,
        SPKTS_RATIO,
        SBYTES_RATIO,
        FLOW_IAT_MAX,
        FLOW_IAT_MIN,
        PACKET_LEN_MAX,
        PACKET_LEN_MIN,
        FWD_LEN_MAX,
        FWD_LEN_MIN,
        FWD_LEN_TOT,
        BWD_LEN_MAX,
        BWD_LEN_MIN,
        BWD_LEN_TOT,
        ECE_FLAG_COUNT,
        CWR_FLAG_COUNT,
        FWD_HEADER_LEN_MEAN,
        BWD_HEADER_LEN_MEAN,

        // === PHASE 2: 15 features ===
        // Forward IAT (5)
        FWD_IAT_MEAN,       // 43
        FWD_IAT_STD,        // 44
        FWD_IAT_MAX,        // 45
        FWD_IAT_MIN,        // 46
        FWD_IAT_TOT,        // 47

        // Backward IAT (5)
        BWD_IAT_MEAN,       // 48
        BWD_IAT_STD,        // 49
        BWD_IAT_MAX,        // 50
        BWD_IAT_MIN,        // 51
        BWD_IAT_TOT,        // 52

        // Active/Idle time (4)
        ACTIVE_MEAN,        // 53
        ACTIVE_MAX,         // 54
        IDLE_MEAN,          // 55
        IDLE_MAX,           // 56

        // Additional length stats (1)
        FWD_LEN_STD,        // 57

        // === PHASE 3: 20 NEW FEATURES ===
        SUBFLOW_FWD_PACKETS,    // 58
        SUBFLOW_FWD_BYTES,      // 59
        SUBFLOW_BWD_PACKETS,    // 60
        SUBFLOW_BWD_BYTES,      // 61
        FWD_BULK_RATE_AVG,      // 62
        FWD_BULK_SIZE_AVG,      // 63
        FWD_BULK_DURATION_AVG,  // 64
        BWD_BULK_RATE_AVG,      // 65
        BWD_BULK_SIZE_AVG,      // 66
        BWD_BULK_DURATION_AVG,  // 67
        INIT_FWD_WIN_BYTES,     // 68
        INIT_BWD_WIN_BYTES,     // 69
        BWD_LEN_STD,            // 70
        FWD_HEADER_LEN_MAX,     // 71
        FWD_HEADER_LEN_MIN,     // 72
        BWD_HEADER_LEN_MAX,     // 73
        BWD_HEADER_LEN_MIN,     // 74
        FLOW_PKTS_PER_SEC,      // 75
        FLOW_BYTES_PER_SEC,     // 76
        DOWN_UP_RATIO,          // 77

        // === PHASE 4: 5 FINAL FEATURES ===
        AVG_PACKET_SIZE,                 // 78
        AVG_FWD_SEGMENT_SIZE,            // 79
        AVG_BWD_SEGMENT_SIZE,            // 80
        FWD_AVG_PACKETS_BULK,            // 81
        BWD_AVG_PACKETS_BULK             // 82
    };

    FeatureExtractor() = default;

    // Extract all features from a flow
    std::array<double, FEATURE_COUNT> extract_features(const FlowStatistics& flow) const;

    // Get feature name by index
    static const char* get_feature_name(size_t index);

private:
    // === ORIGINAL EXTRACTORS ===
    double extract_duration(const FlowStatistics& flow) const;
    double extract_sload(const FlowStatistics& flow) const;
    double extract_smean(const FlowStatistics& flow) const;
    double extract_dmean(const FlowStatistics& flow) const;
    double extract_flow_iat_mean(const FlowStatistics& flow) const;
    double extract_flow_iat_std(const FlowStatistics& flow) const;
    double extract_packet_len_mean(const FlowStatistics& flow) const;
    double extract_packet_len_std(const FlowStatistics& flow) const;
    double extract_packet_len_var(const FlowStatistics& flow) const;

    // === FASE 1 EXTRACTORS ===
    double extract_dload(const FlowStatistics& flow) const;
    double extract_rate(const FlowStatistics& flow) const;
    double extract_srate(const FlowStatistics& flow) const;
    double extract_drate(const FlowStatistics& flow) const;
    double extract_spkts_ratio(const FlowStatistics& flow) const;
    double extract_sbytes_ratio(const FlowStatistics& flow) const;
    double extract_flow_iat_max(const FlowStatistics& flow) const;
    double extract_flow_iat_min(const FlowStatistics& flow) const;
    double extract_packet_len_max(const FlowStatistics& flow) const;
    double extract_packet_len_min(const FlowStatistics& flow) const;
    double extract_fwd_len_max(const FlowStatistics& flow) const;
    double extract_fwd_len_min(const FlowStatistics& flow) const;
    double extract_fwd_len_tot(const FlowStatistics& flow) const;
    double extract_bwd_len_max(const FlowStatistics& flow) const;
    double extract_bwd_len_min(const FlowStatistics& flow) const;
    double extract_bwd_len_tot(const FlowStatistics& flow) const;
    double extract_fwd_header_len_mean(const FlowStatistics& flow) const;
    double extract_bwd_header_len_mean(const FlowStatistics& flow) const;

    // === PHASE 2 EXTRACTORS ===
    // Forward IAT
    double extract_fwd_iat_mean(const FlowStatistics& flow) const;
    double extract_fwd_iat_std(const FlowStatistics& flow) const;
    double extract_fwd_iat_max(const FlowStatistics& flow) const;
    double extract_fwd_iat_min(const FlowStatistics& flow) const;
    double extract_fwd_iat_tot(const FlowStatistics& flow) const;

    // Backward IAT
    double extract_bwd_iat_mean(const FlowStatistics& flow) const;
    double extract_bwd_iat_std(const FlowStatistics& flow) const;
    double extract_bwd_iat_max(const FlowStatistics& flow) const;
    double extract_bwd_iat_min(const FlowStatistics& flow) const;
    double extract_bwd_iat_tot(const FlowStatistics& flow) const;

    // Active/Idle time
    double extract_active_mean(const FlowStatistics& flow) const;
    double extract_active_max(const FlowStatistics& flow) const;
    double extract_idle_mean(const FlowStatistics& flow) const;
    double extract_idle_max(const FlowStatistics& flow) const;

    // Additional length stats
    double extract_fwd_len_std(const FlowStatistics& flow) const;

    // === PHASE 3: NEW EXTRACTORS ===
    // Subflow features
    double extract_subflow_fwd_packets(const FlowStatistics& flow) const;
    double extract_subflow_fwd_bytes(const FlowStatistics& flow) const;
    double extract_subflow_bwd_packets(const FlowStatistics& flow) const;
    double extract_subflow_bwd_bytes(const FlowStatistics& flow) const;

    // Bulk transfer features
    double extract_fwd_bulk_rate_avg(const FlowStatistics& flow) const;
    double extract_fwd_bulk_size_avg(const FlowStatistics& flow) const;
    double extract_fwd_bulk_duration_avg(const FlowStatistics& flow) const;
    double extract_bwd_bulk_rate_avg(const FlowStatistics& flow) const;
    double extract_bwd_bulk_size_avg(const FlowStatistics& flow) const;
    double extract_bwd_bulk_duration_avg(const FlowStatistics& flow) const;

    // Init window features
    double extract_init_fwd_win_bytes(const FlowStatistics& flow) const;
    double extract_init_bwd_win_bytes(const FlowStatistics& flow) const;

    // Additional stats
    double extract_bwd_len_std(const FlowStatistics& flow) const;
    double extract_fwd_header_len_max(const FlowStatistics& flow) const;
    double extract_fwd_header_len_min(const FlowStatistics& flow) const;
    double extract_bwd_header_len_max(const FlowStatistics& flow) const;
    double extract_bwd_header_len_min(const FlowStatistics& flow) const;
    double extract_flow_pkts_per_sec(const FlowStatistics& flow) const;
    double extract_flow_bytes_per_sec(const FlowStatistics& flow) const;
    double extract_down_up_ratio(const FlowStatistics& flow) const;

    // === PHASE 4: LAST 5 FEATURES ===
    double extract_avg_packet_size(const FlowStatistics& flow) const;
    double extract_avg_fwd_segment_size(const FlowStatistics& flow) const;
    double extract_avg_bwd_segment_size(const FlowStatistics& flow) const;
    double extract_fwd_avg_packets_bulk(const FlowStatistics& flow) const;
    double extract_bwd_avg_packets_bulk(const FlowStatistics& flow) const;

    // === STATISTICAL HELPERS ===
    double calculate_mean(const std::vector<uint32_t>& values) const;
    double calculate_mean_u16(const std::vector<uint16_t>& values) const;
    double calculate_std(const std::vector<uint32_t>& values) const;
    double calculate_std_u16(const std::vector<uint16_t>& values) const;
    double calculate_variance(const std::vector<uint32_t>& values) const;
    double calculate_max(const std::vector<uint32_t>& values) const;
    double calculate_max_u16(const std::vector<uint16_t>& values) const;
    double calculate_min(const std::vector<uint32_t>& values) const;
    double calculate_min_u16(const std::vector<uint16_t>& values) const;
    double calculate_sum(const std::vector<uint32_t>& values) const;

    // === IAT HELPERS ===
    std::vector<uint64_t> compute_inter_arrival_times(const std::vector<uint64_t>& timestamps) const;
    double calculate_iat_mean(const std::vector<uint64_t>& timestamps) const;
    double calculate_iat_std(const std::vector<uint64_t>& timestamps) const;
    double calculate_iat_max(const std::vector<uint64_t>& timestamps) const;
    double calculate_iat_min(const std::vector<uint64_t>& timestamps) const;
    double calculate_iat_tot(const std::vector<uint64_t>& timestamps) const;

    // === ACTIVE/IDLE HELPERS ===
    struct ActiveIdleTimes {
        std::vector<uint64_t> active_times;   // Periods of continuous activity
        std::vector<uint64_t> idle_times;     // Periods of idleness
    };
    ActiveIdleTimes compute_active_idle_times(const std::vector<uint64_t>& timestamps) const;
};

} // namespace sniffer