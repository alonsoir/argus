// sniffer/include/flow_manager.hpp
// Define FlowStatistics: lo que el sniffer acumula por flujo para extraer rasgos. La tabla que lo guarda
// es flow/sharded_flow_manager.hpp; FlowKey esta en flow_tracker.hpp. [DAY307] la clase FlowManager que
// vivia aqui no la usaba nadie y se borro (la historia de git la conserva).
#pragma once

#include "main.h"
#include "flow_tracker.hpp"
#include <unordered_map>
#include <vector>
#include <map>  // [DDOS-SNAP-D290]
#include <mutex>
#include <memory>
#include <chrono>
#include <functional>

namespace sniffer {

// Flow statistics - Accumulates data for ML feature extraction
struct FlowStatistics {
    // ============ TIMING ============
    uint64_t flow_start_ns;
    uint64_t flow_last_seen_ns;

    // ============ PACKET COUNTERS ============
    uint64_t spkts = 0;  // Forward packets (source -> destination)
    uint64_t dpkts = 0;  // Backward packets (destination -> source)

    // ============ BYTE COUNTERS ============
    uint64_t sbytes = 0;  // Forward bytes
    uint64_t dbytes = 0;  // Backward bytes

    // ============ PACKET LENGTHS ============
    std::vector<uint32_t> fwd_lengths;  // For smean calculation
    std::vector<uint32_t> bwd_lengths;  // For dmean calculation
    std::vector<uint32_t> all_lengths;  // For packet_len_mean/std/var
    // [DDOS-SNAP-D290] Estadisticos incrementales de all_lengths para la foto DDoS v2:
    // suma exacta (media identica a calculate_mean) e histograma ordenado (entropia identica a
    // calculate_entropy, que tambien recorre un std::map por valor ascendente).
    uint64_t sum_all_lengths = 0;
    std::map<uint32_t, uint32_t> len_hist;

    // ============ INTER-ARRIVAL TIMES ============
    std::vector<uint64_t> packet_timestamps;  // ALL packet timestamps (for flow IAT)
    std::vector<uint64_t> fwd_timestamps;     // Forward packet timestamps
    std::vector<uint64_t> bwd_timestamps;     // Backward packet timestamps

    // ============ TCP FLAGS COUNTERS ============
    uint32_t fin_count = 0;
    uint32_t syn_count = 0;
    uint32_t rst_count = 0;
    uint32_t psh_count = 0;
    uint32_t ack_count = 0;
    uint32_t urg_count = 0;
    uint32_t ece_count = 0;
    uint32_t cwr_count = 0;

    // ============ DIRECTIONAL TCP FLAGS ============
    uint32_t fwd_psh_flags = 0;
    uint32_t bwd_psh_flags = 0;
    uint32_t fwd_urg_flags = 0;
    uint32_t bwd_urg_flags = 0;

    // ============ HEADER LENGTHS ============
    std::vector<uint16_t> fwd_header_lengths;
    std::vector<uint16_t> bwd_header_lengths;

    // ============ METHODS ============

    // Constructor
    FlowStatistics() = default;

    // Move constructor
    FlowStatistics(FlowStatistics&& other) noexcept = default;
    FlowStatistics& operator=(FlowStatistics&& other) noexcept = default;

    // Determines if packet is forward direction
    bool is_forward(const SimpleEvent& pkt, const FlowKey& flow_key) const {
        return pkt.src_ip == flow_key.src_ip &&
               pkt.dst_ip == flow_key.dst_ip &&
               pkt.src_port == flow_key.src_port &&
               pkt.dst_port == flow_key.dst_port;
    }

    // Add packet to flow statistics
    void add_packet(const SimpleEvent& pkt, const FlowKey& flow_key) {
        // Initialize timestamps on first packet
        if (spkts == 0 && dpkts == 0) {
            flow_start_ns = pkt.timestamp;
        }
        flow_last_seen_ns = pkt.timestamp;

        bool is_fwd = is_forward(pkt, flow_key);

        // Direction-specific counters
        if (is_fwd) {
            spkts++;
            sbytes += pkt.packet_len;
            fwd_lengths.push_back(pkt.packet_len);

            uint16_t total_header = pkt.ip_header_len + pkt.l4_header_len;
            fwd_header_lengths.push_back(total_header);

            fwd_timestamps.push_back(pkt.timestamp);

            // Directional TCP flags
            if (has_tcp_flag(pkt, TCP_FLAG_PSH)) fwd_psh_flags++;
            if (has_tcp_flag(pkt, TCP_FLAG_URG)) fwd_urg_flags++;

        } else {
            dpkts++;
            dbytes += pkt.packet_len;
            bwd_lengths.push_back(pkt.packet_len);

            uint16_t total_header = pkt.ip_header_len + pkt.l4_header_len;
            bwd_header_lengths.push_back(total_header);

            bwd_timestamps.push_back(pkt.timestamp);

            // Directional TCP flags
            if (has_tcp_flag(pkt, TCP_FLAG_PSH)) bwd_psh_flags++;
            if (has_tcp_flag(pkt, TCP_FLAG_URG)) bwd_urg_flags++;
        }

        // Overall statistics
        all_lengths.push_back(pkt.packet_len);
        sum_all_lengths += pkt.packet_len;                    // [DDOS-SNAP-D290]
        ++len_hist[static_cast<uint32_t>(pkt.packet_len)];
        packet_timestamps.push_back(pkt.timestamp);


        // TCP flags totals
        if (pkt.protocol == 6) {  // TCP only
            if (has_tcp_flag(pkt, TCP_FLAG_FIN)) fin_count++;
            if (has_tcp_flag(pkt, TCP_FLAG_SYN)) syn_count++;
            if (has_tcp_flag(pkt, TCP_FLAG_RST)) rst_count++;
            if (has_tcp_flag(pkt, TCP_FLAG_PSH)) psh_count++;
            if (has_tcp_flag(pkt, TCP_FLAG_ACK)) ack_count++;
            if (has_tcp_flag(pkt, TCP_FLAG_URG)) urg_count++;
            if (has_tcp_flag(pkt, TCP_FLAG_ECE)) ece_count++;
            if (has_tcp_flag(pkt, TCP_FLAG_CWR)) cwr_count++;
        }
    }

    // Get flow duration in microseconds
    uint64_t get_duration_us() const {
        if (flow_last_seen_ns <= flow_start_ns) return 0;
        return (flow_last_seen_ns - flow_start_ns) / 1000ULL;
    }

    // Get total packets
    uint64_t get_total_packets() const {
        return spkts + dpkts;
    }

    // Get total bytes
    uint64_t get_total_bytes() const {
        return sbytes + dbytes;
    }

    // Check if flow should expire (inactive for timeout period)
    bool should_expire(uint64_t current_ns, uint64_t timeout_ns) const {
        return (current_ns - flow_last_seen_ns) > timeout_ns;
    }

    // Check if flow is TCP
    bool is_tcp() const {
        return fin_count > 0 || syn_count > 0 || rst_count > 0 ||
               psh_count > 0 || ack_count > 0 || urg_count > 0;
    }

    // Check if TCP connection is closed (FIN or RST seen)
    bool is_tcp_closed() const {
        return fin_count > 0 || rst_count > 0;
    }
};

} // namespace sniffer