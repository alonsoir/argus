#include "protocol_numbers.hpp"
#include "feature_logger.hpp"
#include "network_security.pb.h"
#include <iostream>
#include <iomanip>
#include <sstream>
#include <ctime>

namespace FeatureLogger {

// Color codes for terminal output
const std::string RESET = "\033[0m";
const std::string BOLD = "\033[1m";
const std::string CYAN = "\033[36m";
const std::string GREEN = "\033[32m";
const std::string YELLOW = "\033[33m";
const std::string BLUE = "\033[34m";
const std::string MAGENTA = "\033[35m";

void print_separator(const std::string& title) {
    if (title.empty()) {
        std::cout << "================================================================\n";
    } else {
        std::cout << BOLD << CYAN << "=== " << title << " ===" << RESET << "\n";
    }
}

void print_subsection(const std::string& title) {
    std::cout << BOLD << BLUE << "[" << title << "]" << RESET << "\n";
}

std::string format_timestamp(uint64_t timestamp_ns) {
    uint64_t seconds = timestamp_ns / 1000000000ULL;
    uint64_t nanos = timestamp_ns % 1000000000ULL;

    time_t time_sec = static_cast<time_t>(seconds);
    struct tm* tm_info = localtime(&time_sec);

    char buffer[80];
    strftime(buffer, sizeof(buffer), "%Y-%m-%d %H:%M:%S", tm_info);

    std::ostringstream oss;
    oss << buffer << "." << std::setw(9) << std::setfill('0') << nanos;
    return oss.str();
}

std::string protocol_name(uint32_t protocol_num) {
    switch (protocol_num) {
        case 1: return "ICMP";
        case 6: return "TCP";
        case 17: return "UDP";
        case 47: return "GRE";
        case 50: return "ESP";
        case 51: return "AH";
        case 58: return "ICMPv6";
        default: return "UNKNOWN(" + std::to_string(protocol_num) + ")";
    }
}

std::string tcp_flags_string(uint32_t flags) {
    std::string result;
    if (flags & 0x01) result += "FIN ";
    if (flags & 0x02) result += "SYN ";
    if (flags & 0x04) result += "RST ";
    if (flags & 0x08) result += "PSH ";
    if (flags & 0x10) result += "ACK ";
    if (flags & 0x20) result += "URG ";
    if (flags & 0x40) result += "ECE ";
    if (flags & 0x80) result += "CWR ";
    return result.empty() ? "NONE" : result;
}

void log_packet_features(const protobuf::NetworkSecurityEvent& event, VerbosityLevel level) {
    switch (level) {
        case VerbosityLevel::BASIC:
            print_basic_summary(event);
            break;
        case VerbosityLevel::GROUPED:
            print_grouped_features(event);
            break;
        case VerbosityLevel::DETAILED:
            print_all_features_detailed(event);
            break;
        default:
            break;
    }
}

void print_basic_summary(const protobuf::NetworkSecurityEvent& event) {
    const auto& nf = event.network_features();

    std::cout << GREEN << "[PKT #" << event.event_id() << "] " << RESET
              << protocol_name(nf.protocol_number()) << " "
              << nf.source_ip() << ":" << nf.source_port() << " → "
              << nf.destination_ip() << ":" << nf.destination_port() << " "
              << YELLOW << nf.total_forward_bytes() + nf.total_backward_bytes() << "B" << RESET;

    if (nf.protocol_number() == static_cast<uint8_t>(sniffer::IPProtocol::TCP)) {  // TCP
        std::cout << " flags:" << tcp_flags_string(
            nf.syn_flag_count() ? 0x02 : 0 |
            nf.ack_flag_count() ? 0x10 : 0 |
            nf.fin_flag_count() ? 0x01 : 0
        );
    }

    std::cout << "  cid=" << nf.community_id() << "\n";
}

void print_grouped_features(const protobuf::NetworkSecurityEvent& event) {
    const auto& nf = event.network_features();

    print_separator("PACKET #" + event.event_id());

    // Basic Info
    print_subsection("BASIC INFO");
    std::cout << "  Timestamp: " << format_timestamp(event.event_timestamp().seconds() * 1000000000ULL) << "\n"
              << "  Source: " << nf.source_ip() << ":" << nf.source_port() << "\n"
              << "  Destination: " << nf.destination_ip() << ":" << nf.destination_port() << "\n"
              << "  Protocol: " << protocol_name(nf.protocol_number()) << " (" << nf.protocol_number() << ")\n"
              << "  Total Bytes: " << (nf.total_forward_bytes() + nf.total_backward_bytes()) << "\n"
              << "  Forward: " << nf.total_forward_packets() << " pkts, " << nf.total_forward_bytes() << " bytes\n"
              << "  Backward: " << nf.total_backward_packets() << " pkts, " << nf.total_backward_bytes() << " bytes\n";

    // Timing
    if (nf.has_flow_duration()) {
        print_subsection("TIMING");
        std::cout << "  Flow duration: " << nf.flow_duration().seconds() << "."
                  << std::setw(6) << std::setfill('0') << nf.flow_duration().nanos() / 1000 << " s\n"
                  << "  Microseconds: " << nf.flow_duration_microseconds() << " µs\n"
                  << "  Flow IAT mean: " << nf.flow_inter_arrival_time_mean() << " µs\n"
                  << "  Fwd IAT mean: " << nf.forward_inter_arrival_time_mean() << " µs\n"
                  << "  Bwd IAT mean: " << nf.backward_inter_arrival_time_mean() << " µs\n";
    }

    // TCP Flags
    if (nf.protocol_number() == static_cast<uint8_t>(sniffer::IPProtocol::TCP)) {
        print_subsection("TCP FLAGS");
        std::cout << "  FIN: " << nf.fin_flag_count()
                  << "  SYN: " << nf.syn_flag_count()
                  << "  RST: " << nf.rst_flag_count()
                  << "  PSH: " << nf.psh_flag_count() << "\n"
                  << "  ACK: " << nf.ack_flag_count()
                  << "  URG: " << nf.urg_flag_count()
                  << "  ECE: " << nf.ece_flag_count()
                  << "  CWR: " << nf.cwe_flag_count() << "\n";
    }

    // Rates
    print_subsection("RATES & RATIOS");
    std::cout << "  Bytes/sec: " << nf.flow_bytes_per_second() << "\n"
              << "  Packets/sec: " << nf.flow_packets_per_second() << "\n"
              << "  Fwd packets/sec: " << nf.forward_packets_per_second() << "\n"
              << "  Bwd packets/sec: " << nf.backward_packets_per_second() << "\n"
              << "  Download/Upload ratio: " << nf.download_upload_ratio() << "\n"
              << "  Avg packet size: " << nf.average_packet_size() << "\n";

    // Feature Arrays
    if (nf.general_attack_features_size() > 0) {
        print_subsection("GENERAL ATTACK FEATURES (RF)");
        std::cout << "  Count: " << nf.general_attack_features_size() << " features\n";
        std::cout << "  Sample: [";
        for (int i = 0; i < std::min(5, nf.general_attack_features_size()); i++) {
            std::cout << nf.general_attack_features(i);
            if (i < std::min(5, nf.general_attack_features_size()) - 1) std::cout << ", ";
        }
        if (nf.general_attack_features_size() > 5) std::cout << ", ...";
        std::cout << "]\n";
    }

    if (nf.internal_traffic_features_size() > 0) {
        print_subsection("INTERNAL TRAFFIC FEATURES");
        std::cout << "  Count: " << nf.internal_traffic_features_size() << " features\n";
        std::cout << "  Values: [";
        for (int i = 0; i < nf.internal_traffic_features_size(); i++) {
            std::cout << nf.internal_traffic_features(i);
            if (i < nf.internal_traffic_features_size() - 1) std::cout << ", ";
        }
        std::cout << "]\n";
    }

    if (nf.ransomware_features_size() > 0) {
        print_subsection("RANSOMWARE DETECTION FEATURES");
        std::cout << "  Count: " << nf.ransomware_features_size() << " features\n";
        std::cout << "  Sample: [";
        for (int i = 0; i < std::min(5, nf.ransomware_features_size()); i++) {
            std::cout << nf.ransomware_features(i);
            if (i < std::min(5, nf.ransomware_features_size()) - 1) std::cout << ", ";
        }
        if (nf.ransomware_features_size() > 5) std::cout << ", ...";
        std::cout << "]\n";
    }

    if (nf.ddos_features_size() > 0) {
        print_subsection("DDOS DETECTION FEATURES");
        std::cout << "  Count: " << nf.ddos_features_size() << " features\n";
        std::cout << "  Sample: [";
        for (int i = 0; i < std::min(5, nf.ddos_features_size()); i++) {
            std::cout << nf.ddos_features(i);
            if (i < std::min(5, nf.ddos_features_size()) - 1) std::cout << ", ";
        }
        if (nf.ddos_features_size() > 5) std::cout << ", ...";
        std::cout << "]\n";
    }

    print_separator();
    std::cout << "\n";
}

void print_all_features_detailed(const protobuf::NetworkSecurityEvent& event) {
    const auto& nf = event.network_features();

    print_separator("PACKET #" + event.event_id() + " - FULL FEATURE DUMP");

    // Basic Identification
    print_subsection("BASIC IDENTIFICATION");
    std::cout << "  Event ID: " << event.event_id() << "\n"
              << "  Node ID: " << event.originating_node_id() << "\n"
              << "  Timestamp: " << format_timestamp(event.event_timestamp().seconds() * 1000000000ULL) << "\n"
              << "  Classification: " << event.final_classification() << "\n"
              << "  Threat Score: " << event.overall_threat_score() << "\n\n";

    // Network Basic Features
    print_subsection("NETWORK FEATURES - BASIC");
    std::cout << "  [src_ip] " << nf.source_ip() << "\n"
              << "  [dst_ip] " << nf.destination_ip() << "\n"
              << "  [src_port] " << nf.source_port() << "\n"
              << "  [dst_port] " << nf.destination_port() << "\n"
              << "  [protocol_number] " << nf.protocol_number() << "\n"
              << "  [protocol_name] " << nf.protocol_name() << "\n\n";

    // Packet Statistics
    print_subsection("PACKET STATISTICS");
    std::cout << "  [total_forward_packets] " << nf.total_forward_packets() << "\n"
              << "  [total_backward_packets] " << nf.total_backward_packets() << "\n"
              << "  [total_forward_bytes] " << nf.total_forward_bytes() << "\n"
              << "  [total_backward_bytes] " << nf.total_backward_bytes() << "\n"
              << "  [minimum_packet_length] " << nf.minimum_packet_length() << "\n"
              << "  [maximum_packet_length] " << nf.maximum_packet_length() << "\n"
              << "  [packet_length_mean] " << nf.packet_length_mean() << "\n"
              << "  [packet_length_std] " << nf.packet_length_std() << "\n"
              << "  [packet_length_variance] " << nf.packet_length_variance() << "\n\n";

    // Forward Packet Length
    print_subsection("FORWARD PACKET LENGTH");
    std::cout << "  [forward_packet_length_max] " << nf.forward_packet_length_max() << "\n"
              << "  [forward_packet_length_min] " << nf.forward_packet_length_min() << "\n"
              << "  [forward_packet_length_mean] " << nf.forward_packet_length_mean() << "\n"
              << "  [forward_packet_length_std] " << nf.forward_packet_length_std() << "\n\n";

    // Backward Packet Length
    print_subsection("BACKWARD PACKET LENGTH");
    std::cout << "  [backward_packet_length_max] " << nf.backward_packet_length_max() << "\n"
              << "  [backward_packet_length_min] " << nf.backward_packet_length_min() << "\n"
              << "  [backward_packet_length_mean] " << nf.backward_packet_length_mean() << "\n"
              << "  [backward_packet_length_std] " << nf.backward_packet_length_std() << "\n\n";

    // Rates
    print_subsection("RATES & SPEEDS");
    std::cout << "  [flow_bytes_per_second] " << nf.flow_bytes_per_second() << "\n"
              << "  [flow_packets_per_second] " << nf.flow_packets_per_second() << "\n"
              << "  [forward_packets_per_second] " << nf.forward_packets_per_second() << "\n"
              << "  [backward_packets_per_second] " << nf.backward_packets_per_second() << "\n"
              << "  [download_upload_ratio] " << nf.download_upload_ratio() << "\n"
              << "  [average_packet_size] " << nf.average_packet_size() << "\n"
              << "  [average_forward_segment_size] " << nf.average_forward_segment_size() << "\n"
              << "  [average_backward_segment_size] " << nf.average_backward_segment_size() << "\n\n";

    // Inter-Arrival Times - Flow
    print_subsection("INTER-ARRIVAL TIMES - FLOW");
    std::cout << "  [flow_inter_arrival_time_mean] " << nf.flow_inter_arrival_time_mean() << "\n"
              << "  [flow_inter_arrival_time_std] " << nf.flow_inter_arrival_time_std() << "\n"
              << "  [flow_inter_arrival_time_max] " << nf.flow_inter_arrival_time_max() << "\n"
              << "  [flow_inter_arrival_time_min] " << nf.flow_inter_arrival_time_min() << "\n\n";

    // Inter-Arrival Times - Forward
    print_subsection("INTER-ARRIVAL TIMES - FORWARD");
    std::cout << "  [forward_inter_arrival_time_total] " << nf.forward_inter_arrival_time_total() << "\n"
              << "  [forward_inter_arrival_time_mean] " << nf.forward_inter_arrival_time_mean() << "\n"
              << "  [forward_inter_arrival_time_std] " << nf.forward_inter_arrival_time_std() << "\n"
              << "  [forward_inter_arrival_time_max] " << nf.forward_inter_arrival_time_max() << "\n"
              << "  [forward_inter_arrival_time_min] " << nf.forward_inter_arrival_time_min() << "\n\n";

    // Inter-Arrival Times - Backward
    print_subsection("INTER-ARRIVAL TIMES - BACKWARD");
    std::cout << "  [backward_inter_arrival_time_total] " << nf.backward_inter_arrival_time_total() << "\n"
              << "  [backward_inter_arrival_time_mean] " << nf.backward_inter_arrival_time_mean() << "\n"
              << "  [backward_inter_arrival_time_std] " << nf.backward_inter_arrival_time_std() << "\n"
              << "  [backward_inter_arrival_time_max] " << nf.backward_inter_arrival_time_max() << "\n"
              << "  [backward_inter_arrival_time_min] " << nf.backward_inter_arrival_time_min() << "\n\n";

    // TCP Flags
    if (nf.protocol_number() == static_cast<uint8_t>(sniffer::IPProtocol::TCP)) {
        print_subsection("TCP FLAGS");
        std::cout << "  [fin_flag_count] " << nf.fin_flag_count() << "\n"
                  << "  [syn_flag_count] " << nf.syn_flag_count() << "\n"
                  << "  [rst_flag_count] " << nf.rst_flag_count() << "\n"
                  << "  [psh_flag_count] " << nf.psh_flag_count() << "\n"
                  << "  [ack_flag_count] " << nf.ack_flag_count() << "\n"
                  << "  [urg_flag_count] " << nf.urg_flag_count() << "\n"
                  << "  [cwe_flag_count] " << nf.cwe_flag_count() << "\n"
                  << "  [ece_flag_count] " << nf.ece_flag_count() << "\n"
                  << "  [forward_psh_flags] " << nf.forward_psh_flags() << "\n"
                  << "  [backward_psh_flags] " << nf.backward_psh_flags() << "\n"
                  << "  [forward_urg_flags] " << nf.forward_urg_flags() << "\n"
                  << "  [backward_urg_flags] " << nf.backward_urg_flags() << "\n\n";
    }

    // Headers & Bulk
    print_subsection("HEADERS & BULK TRANSFER");
    std::cout << "  [forward_header_length] " << nf.forward_header_length() << "\n"
              << "  [backward_header_length] " << nf.backward_header_length() << "\n"
              << "  [forward_average_bytes_bulk] " << nf.forward_average_bytes_bulk() << "\n"
              << "  [forward_average_packets_bulk] " << nf.forward_average_packets_bulk() << "\n"
              << "  [forward_average_bulk_rate] " << nf.forward_average_bulk_rate() << "\n"
              << "  [backward_average_bytes_bulk] " << nf.backward_average_bytes_bulk() << "\n"
              << "  [backward_average_packets_bulk] " << nf.backward_average_packets_bulk() << "\n"
              << "  [backward_average_bulk_rate] " << nf.backward_average_bulk_rate() << "\n\n";

    // Feature Arrays
    if (nf.general_attack_features_size() > 0) {
        print_subsection("GENERAL ATTACK FEATURES (RF Model - 23 features)");
        for (int i = 0; i < nf.general_attack_features_size(); i++) {
            std::cout << "  [" << std::setw(3) << i << "] "
                      << std::setw(20) << std::left << ("feature_" + std::to_string(i))
                      << " : " << nf.general_attack_features(i) << "\n";
        }
        std::cout << "\n";
    }

    if (nf.internal_traffic_features_size() > 0) {
        print_subsection("INTERNAL TRAFFIC FEATURES (4-5 features)");
        for (int i = 0; i < nf.internal_traffic_features_size(); i++) {
            std::cout << "  [" << std::setw(3) << i << "] "
                      << std::setw(20) << std::left << ("internal_" + std::to_string(i))
                      << " : " << nf.internal_traffic_features(i) << "\n";
        }
        std::cout << "\n";
    }

    if (nf.ransomware_features_size() > 0) {
        print_subsection("RANSOMWARE DETECTION FEATURES (83 features)");
        for (int i = 0; i < nf.ransomware_features_size(); i++) {
            std::cout << "  [" << std::setw(3) << i << "] "
                      << std::setw(20) << std::left << ("ransomware_" + std::to_string(i))
                      << " : " << nf.ransomware_features(i) << "\n";
        }
        std::cout << "\n";
    }

    if (nf.ddos_features_size() > 0) {
        print_subsection("DDOS DETECTION FEATURES (83 features)");
        for (int i = 0; i < nf.ddos_features_size(); i++) {
            std::cout << "  [" << std::setw(3) << i << "] "
                      << std::setw(20) << std::left << ("ddos_" + std::to_string(i))
                      << " : " << nf.ddos_features(i) << "\n";
        }
        std::cout << "\n";
    }

    // Summary
    int total_features = nf.general_attack_features_size() +
                        nf.internal_traffic_features_size() +
                        nf.ransomware_features_size() +
                        nf.ddos_features_size();

    print_subsection("SUMMARY");
    std::cout << "  Total feature arrays: " << total_features << " features\n"
              << "  + Individual features: ~50 fields\n"
              << "  Total: ~" << (total_features + 50) << " data points\n";

    print_separator();
    std::cout << "\n";
}

} // namespace FeatureLogger