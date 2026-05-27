// generate_synthetic_events.cpp
// Synthetic Event Generator for RAG Ingester Testing
// Via Appia Quality - Uses Production RAGLogger
//
// PURPOSE: Generate synthetic events with 101 features + ADR-002 provenance
// STRATEGY: Reuse RAGLogger directly to guarantee compliance
//
// AUTHORS: Alonso Isidoro Roman + Claude (Anthropic)
// DATE: 15 Enero 2026 - Day 38 (Consistent with ml-detector - etcd-client)
#include <iostream>
#include <random>
#include <vector>
#include <string>
#include <fstream>
#include <filesystem>
#include <chrono>
#include <iomanip>
#include <map>

// Logging
#include <spdlog/spdlog.h>
#include <spdlog/sinks/stdout_color_sinks.h>

// JSON for SPEC and stats
#include <nlohmann/json.hpp>

// Protobuf
#include "network_security.pb.h"

// Crypto
#include <crypto_transport/crypto_manager.hpp>
#include <crypto_transport/utils.hpp>
// etcd-client (consistent with ml-detector, rag-ingester)
#include <etcd_client/etcd_client.hpp>
// RAG Logger (PRODUCTION CODE - zero drift)
#include "rag_logger.hpp"

// Reason codes
#include "reason_codes.hpp"

namespace fs = std::filesystem;
using json = nlohmann::json;

// ============================================================================
// SPEC Definition (Ground Truth)
// ============================================================================

json get_spec() {
    json spec;
    spec["version"] = "1.0.0";
    spec["date"] = "2026-01-15";
    spec["protobuf_version"] = "3.1.0";

    spec["features"]["total_count"] = 101;
    spec["features"]["basic_flow"] = 61;
    spec["features"]["embedded_ddos"] = 10;
    spec["features"]["embedded_ransomware"] = 10;
    spec["features"]["embedded_traffic"] = 10;
    spec["features"]["embedded_internal"] = 10;

    spec["provenance"]["engines"] = json::array({"fast-path-sniffer", "random-forest-level1"});
    spec["provenance"]["reason_codes"] = json::array({
        "SIG_MATCH",
        "STAT_ANOMALY",
        "PCA_OUTLIER",
        "PROT_VIOLATION",
        "ENGINE_CONFLICT"
    });

    spec["provenance"]["discrepancy_ranges"]["low"] = json::array({0.0, 0.25});
    spec["provenance"]["discrepancy_ranges"]["medium"] = json::array({0.25, 0.50});
    spec["provenance"]["discrepancy_ranges"]["high"] = json::array({0.50, 1.0});

    spec["encryption"]["algorithm"] = "ChaCha20-Poly1305";
    spec["encryption"]["key_size"] = 32;

    spec["compression"]["algorithm"] = "LZ4";

    return spec;
}

// ============================================================================
// Random Number Generator (thread-safe, seeded)
// ============================================================================

class RandomGen {
public:
    RandomGen() : rng_(std::random_device{}()) {}

    double uniform(double min, double max) {
        std::uniform_real_distribution<double> dist(min, max);
        return dist(rng_);
    }

    int uniform_int(int min, int max) {
        std::uniform_int_distribution<int> dist(min, max);
        return dist(rng_);
    }

    template<typename T>
    T choice(const std::vector<T>& vec) {
        std::uniform_int_distribution<size_t> dist(0, vec.size() - 1);
        return vec[dist(rng_)];
    }

    template<typename T>
    T weighted_choice(const std::map<T, double>& weights) {
        std::vector<T> keys;
        std::vector<double> probs;

        for (const auto& [key, prob] : weights) {
            keys.push_back(key);
            probs.push_back(prob);
        }

        std::discrete_distribution<> dist(probs.begin(), probs.end());
        return keys[dist(rng_)];
    }

private:
    std::mt19937_64 rng_;
};

// ============================================================================
// Feature Generation (101 features - EXACT spec)
// ============================================================================

struct FeatureSet {
    std::vector<double> basic_flow;       // 61 features
    std::vector<float> ddos;              // 10 features
    std::vector<float> ransomware;        // 10 features
    std::vector<float> traffic;           // 10 features
    std::vector<float> internal;          // 10 features
};

FeatureSet generate_features(RandomGen& rng, bool is_malicious, const std::string& attack_type) {
    FeatureSet features;

    // PART 1: BASIC FLOW STATISTICS (61 features)
    uint64_t fwd_packets, bwd_packets;
    double bytes_per_sec;
    uint32_t syn_count;

    if (is_malicious) {
        fwd_packets = rng.uniform_int(500, 5000);
        bwd_packets = rng.uniform_int(10, 100);
        bytes_per_sec = rng.uniform(100000, 1000000);
        syn_count = rng.uniform_int(100, 500);
    } else {
        fwd_packets = rng.uniform_int(10, 200);
        bwd_packets = rng.uniform_int(10, 200);
        bytes_per_sec = rng.uniform(1000, 50000);
        syn_count = rng.uniform_int(0, 5);
    }

    features.basic_flow = {
        6.0, 1.0, 0.0, rng.uniform(0.1, 10.0),
        static_cast<double>(fwd_packets),
        static_cast<double>(bwd_packets),
        static_cast<double>(fwd_packets * rng.uniform_int(40, 1500)),
        static_cast<double>(bwd_packets * rng.uniform_int(40, 1500)),
        static_cast<double>(rng.uniform_int(40, 1500)), 40.0,
        rng.uniform(100, 800), rng.uniform(50, 300),
        static_cast<double>(rng.uniform_int(40, 1500)), 40.0,
        rng.uniform(100, 800), rng.uniform(50, 300),
        bytes_per_sec, fwd_packets / 10.0, fwd_packets / 10.0, bwd_packets / 10.0,
        static_cast<double>(bwd_packets) / static_cast<double>(std::max(fwd_packets, 1UL)),
        rng.uniform(200, 800), rng.uniform(200, 800), rng.uniform(200, 800),
        rng.uniform(1000, 50000), rng.uniform(500, 20000),
        static_cast<double>(rng.uniform_int(100000, 500000)),
        static_cast<double>(rng.uniform_int(100, 5000)),
        rng.uniform(10000, 100000), rng.uniform(1000, 50000), rng.uniform(500, 20000),
        static_cast<double>(rng.uniform_int(100000, 500000)),
        static_cast<double>(rng.uniform_int(100, 5000)),
        rng.uniform(10000, 100000), rng.uniform(1000, 50000), rng.uniform(500, 20000),
        static_cast<double>(rng.uniform_int(100000, 500000)),
        static_cast<double>(rng.uniform_int(100, 5000)),
        static_cast<double>(rng.uniform_int(0, 10)),
        static_cast<double>(syn_count),
        static_cast<double>(rng.uniform_int(0, 5)),
        static_cast<double>(rng.uniform_int(0, 50)),
        static_cast<double>(rng.uniform_int(10, 200)),
        0.0, 0.0, 0.0,
        static_cast<double>(rng.uniform_int(0, 20)),
        static_cast<double>(rng.uniform_int(0, 20)),
        0.0, 0.0,
        rng.uniform(20, 60), rng.uniform(20, 60),
        0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
        40.0,
        static_cast<double>(rng.uniform_int(1000, 1500)),
        rng.uniform(200, 800), rng.uniform(100, 400),
        rng.uniform(10000, 160000),
        rng.uniform(1000, 50000), rng.uniform(1000, 50000)
    };

    // PART 2: EMBEDDED DETECTOR FEATURES (40 features)
    if (is_malicious && attack_type == "DDoS") {
        features.ddos = {
            static_cast<float>(rng.uniform(0.8, 1.0)),
            static_cast<float>(rng.uniform(0.1, 0.3)),
            static_cast<float>(rng.uniform(0.7, 1.0)),
            static_cast<float>(rng.uniform(0.7, 1.0)),
            static_cast<float>(rng.uniform(0.6, 0.9)),
            static_cast<float>(rng.uniform(2.0, 10.0)),
            static_cast<float>(rng.uniform(0.1, 0.3)),
            static_cast<float>(rng.uniform(0.7, 1.0)),
            static_cast<float>(rng.uniform(5.0, 20.0)),
            static_cast<float>(rng.uniform(0.8, 1.0))
        };
    } else {
        for (int i = 0; i < 10; i++) {
            features.ddos.push_back(rng.uniform(0.0, 0.3));
        }
    }

    if (is_malicious && attack_type == "Ransomware") {
        features.ransomware = {
            static_cast<float>(rng.uniform(0.7, 1.0)),
            static_cast<float>(rng.uniform(0.8, 1.0)),
            static_cast<float>(rng.uniform(0.7, 1.0)),
            static_cast<float>(rng.uniform(0.6, 0.9)),
            static_cast<float>(rng.uniform(0.8, 1.0)),
            static_cast<float>(rng.uniform(0.7, 1.0)),
            static_cast<float>(rng.uniform(0.6, 0.9)),
            static_cast<float>(rng.uniform(0.7, 1.0)),
            static_cast<float>(rng.uniform(0.8, 1.0)),
            static_cast<float>(rng.uniform(0.5, 0.8))
        };
    } else {
        for (int i = 0; i < 10; i++) {
            features.ransomware.push_back(rng.uniform(0.0, 0.3));
        }
    }

    features.traffic = {
        static_cast<float>(rng.uniform(10, 100)),
        static_cast<float>(rng.uniform(1, 10)),
        static_cast<float>(rng.uniform(0.5, 1.5)),
        static_cast<float>(rng.uniform(200, 800)),
        static_cast<float>(rng.uniform(0.3, 0.8)),
        static_cast<float>(rng.uniform(1000, 50000)),
        static_cast<float>(rng.uniform(0.2, 0.7)),
        static_cast<float>(rng.uniform(0.3, 0.8)),
        static_cast<float>(rng.uniform(0.2, 0.6)),
        static_cast<float>(rng.uniform(0.4, 0.9))
    };

    features.internal = {
        static_cast<float>(rng.uniform(0.1, 5.0)),
        static_cast<float>(rng.uniform(0.5, 1.0)),
        static_cast<float>(rng.uniform(0.6, 1.0)),
        static_cast<float>(rng.uniform(0.5, 1.0)),
        static_cast<float>(rng.uniform(1000, 20000)),
        static_cast<float>(rng.uniform(0.0, 0.3)),
        static_cast<float>(rng.uniform(0.0, 0.4)),
        static_cast<float>(rng.uniform(0.0, 0.3)),
        static_cast<float>(rng.uniform(0.0, 0.4)),
        static_cast<float>(rng.uniform(0.3, 0.7))
    };

    return features;
}

// ============================================================================
// Provenance Generation (ADR-002)
// ============================================================================

struct ProvenanceData {
    std::vector<protobuf::EngineVerdict> verdicts;
    float discrepancy_score;
    std::string final_decision;
};

ProvenanceData generate_provenance(RandomGen& rng, bool is_malicious) {
    ProvenanceData prov;

    std::map<std::string, double> reason_dist = {
        {"SIG_MATCH", 0.40},
        {"STAT_ANOMALY", 0.35},
        {"PCA_OUTLIER", 0.10},
        {"PROT_VIOLATION", 0.10},
        {"ENGINE_CONFLICT", 0.05}
    };

    protobuf::EngineVerdict sniffer;
    sniffer.set_engine_name("fast-path-sniffer");
    sniffer.set_classification(is_malicious ? "MALICIOUS" : "BENIGN");
    sniffer.set_confidence(is_malicious ? rng.uniform(0.75, 0.95) : rng.uniform(0.05, 0.25));
    sniffer.set_reason_code(rng.weighted_choice(reason_dist));
    sniffer.set_timestamp_ns(std::chrono::system_clock::now().time_since_epoch().count());
    prov.verdicts.push_back(sniffer);

    protobuf::EngineVerdict rf;
    rf.set_engine_name("random-forest-level1");
    rf.set_classification(is_malicious ? "Attack" : "Benign");
    rf.set_confidence(is_malicious ? rng.uniform(0.80, 0.98) : rng.uniform(0.05, 0.20));
    rf.set_reason_code("STAT_ANOMALY");
    rf.set_timestamp_ns(std::chrono::system_clock::now().time_since_epoch().count());
    prov.verdicts.push_back(rf);

    double rand = rng.uniform(0.0, 1.0);
    if (rand < 0.78) {
        prov.discrepancy_score = rng.uniform(0.0, 0.25);
    } else if (rand < 0.90) {
        prov.discrepancy_score = rng.uniform(0.25, 0.50);
    } else {
        prov.discrepancy_score = rng.uniform(0.50, 1.0);
    }

    prov.final_decision = is_malicious ? "DROP" : "ALLOW";

    return prov;
}

// ============================================================================
// Event Generation (Complete Protobuf)
// ============================================================================

protobuf::NetworkSecurityEvent generate_event(
    RandomGen& rng,
    int event_id,
    bool is_malicious,
    const std::string& attack_type)
{
    protobuf::NetworkSecurityEvent event;

    std::ostringstream oss;
    oss << "synthetic_" << std::setfill('0') << std::setw(6) << event_id;
    event.set_event_id(oss.str());

    auto now = std::chrono::system_clock::now();
    auto seconds = std::chrono::duration_cast<std::chrono::seconds>(now.time_since_epoch()).count();
    auto nanos = std::chrono::duration_cast<std::chrono::nanoseconds>(now.time_since_epoch()).count() % 1000000000;

    event.mutable_event_timestamp()->set_seconds(seconds);
    event.mutable_event_timestamp()->set_nanos(nanos);

    auto feat = generate_features(rng, is_malicious, attack_type);
    auto* nf = event.mutable_network_features();

    auto& bf = feat.basic_flow;
    nf->set_protocol_number(static_cast<uint32_t>(bf[0]));
    nf->set_interface_mode(static_cast<uint32_t>(bf[1]));
    nf->set_source_ifindex(static_cast<uint32_t>(bf[2]));
    nf->set_flow_duration_microseconds(static_cast<uint64_t>(bf[3] * 1e6));
    nf->set_total_forward_packets(static_cast<uint64_t>(bf[4]));
    nf->set_total_backward_packets(static_cast<uint64_t>(bf[5]));
    nf->set_total_forward_bytes(static_cast<uint64_t>(bf[6]));
    nf->set_total_backward_bytes(static_cast<uint64_t>(bf[7]));
    nf->set_forward_packet_length_max(static_cast<uint64_t>(bf[8]));
    nf->set_forward_packet_length_min(static_cast<uint64_t>(bf[9]));
    nf->set_forward_packet_length_mean(bf[10]);
    nf->set_forward_packet_length_std(bf[11]);
    nf->set_backward_packet_length_max(static_cast<uint64_t>(bf[12]));
    nf->set_backward_packet_length_min(static_cast<uint64_t>(bf[13]));
    nf->set_backward_packet_length_mean(bf[14]);
    nf->set_backward_packet_length_std(bf[15]);
    nf->set_flow_bytes_per_second(bf[16]);
    nf->set_flow_packets_per_second(bf[17]);
    nf->set_forward_packets_per_second(bf[18]);
    nf->set_backward_packets_per_second(bf[19]);
    nf->set_download_upload_ratio(bf[20]);
    nf->set_average_packet_size(bf[21]);
    nf->set_average_forward_segment_size(bf[22]);
    nf->set_average_backward_segment_size(bf[23]);
    nf->set_flow_inter_arrival_time_mean(bf[24]);
    nf->set_flow_inter_arrival_time_std(bf[25]);
    nf->set_flow_inter_arrival_time_max(static_cast<uint64_t>(bf[26]));
    nf->set_flow_inter_arrival_time_min(static_cast<uint64_t>(bf[27]));
    nf->set_forward_inter_arrival_time_total(bf[28]);
    nf->set_forward_inter_arrival_time_mean(bf[29]);
    nf->set_forward_inter_arrival_time_std(bf[30]);
    nf->set_forward_inter_arrival_time_max(static_cast<uint64_t>(bf[31]));
    nf->set_forward_inter_arrival_time_min(static_cast<uint64_t>(bf[32]));
    nf->set_backward_inter_arrival_time_total(bf[33]);
    nf->set_backward_inter_arrival_time_mean(bf[34]);
    nf->set_backward_inter_arrival_time_std(bf[35]);
    nf->set_backward_inter_arrival_time_max(static_cast<uint64_t>(bf[36]));
    nf->set_backward_inter_arrival_time_min(static_cast<uint64_t>(bf[37]));
    nf->set_fin_flag_count(static_cast<uint32_t>(bf[38]));
    nf->set_syn_flag_count(static_cast<uint32_t>(bf[39]));
    nf->set_rst_flag_count(static_cast<uint32_t>(bf[40]));
    nf->set_psh_flag_count(static_cast<uint32_t>(bf[41]));
    nf->set_ack_flag_count(static_cast<uint32_t>(bf[42]));
    nf->set_urg_flag_count(static_cast<uint32_t>(bf[43]));
    nf->set_cwe_flag_count(static_cast<uint32_t>(bf[44]));
    nf->set_ece_flag_count(static_cast<uint32_t>(bf[45]));
    nf->set_forward_psh_flags(static_cast<uint32_t>(bf[46]));
    nf->set_backward_psh_flags(static_cast<uint32_t>(bf[47]));
    nf->set_forward_urg_flags(static_cast<uint32_t>(bf[48]));
    nf->set_backward_urg_flags(static_cast<uint32_t>(bf[49]));
    nf->set_forward_header_length(bf[50]);
    nf->set_backward_header_length(bf[51]);
    nf->set_forward_average_bytes_bulk(bf[52]);
    nf->set_forward_average_packets_bulk(bf[53]);
    nf->set_forward_average_bulk_rate(bf[54]);
    nf->set_backward_average_bytes_bulk(bf[55]);
    nf->set_backward_average_packets_bulk(bf[56]);
    nf->set_backward_average_bulk_rate(bf[57]);
    nf->set_minimum_packet_length(static_cast<uint64_t>(bf[58]));
    nf->set_maximum_packet_length(static_cast<uint64_t>(bf[59]));
    nf->set_packet_length_mean(bf[60]);
    nf->set_packet_length_std(bf[61]);
    nf->set_packet_length_variance(bf[62]);
    nf->set_active_mean(bf[63]);
    nf->set_idle_mean(bf[64]);

    auto* ddos = nf->mutable_ddos_embedded();
    ddos->set_syn_ack_ratio(feat.ddos[0]);
    ddos->set_packet_symmetry(feat.ddos[1]);
    ddos->set_source_ip_dispersion(feat.ddos[2]);
    ddos->set_protocol_anomaly_score(feat.ddos[3]);
    ddos->set_packet_size_entropy(feat.ddos[4]);
    ddos->set_traffic_amplification_factor(feat.ddos[5]);
    ddos->set_flow_completion_rate(feat.ddos[6]);
    ddos->set_geographical_concentration(feat.ddos[7]);
    ddos->set_traffic_escalation_rate(feat.ddos[8]);
    ddos->set_resource_saturation_score(feat.ddos[9]);

    auto* ransomware = nf->mutable_ransomware_embedded();
    ransomware->set_io_intensity(feat.ransomware[0]);
    ransomware->set_entropy(feat.ransomware[1]);
    ransomware->set_resource_usage(feat.ransomware[2]);
    ransomware->set_network_activity(feat.ransomware[3]);
    ransomware->set_file_operations(feat.ransomware[4]);
    ransomware->set_process_anomaly(feat.ransomware[5]);
    ransomware->set_temporal_pattern(feat.ransomware[6]);
    ransomware->set_access_frequency(feat.ransomware[7]);
    ransomware->set_data_volume(feat.ransomware[8]);
    ransomware->set_behavior_consistency(feat.ransomware[9]);

    auto* traffic = nf->mutable_traffic_classification();
    traffic->set_packet_rate(feat.traffic[0]);
    traffic->set_connection_rate(feat.traffic[1]);
    traffic->set_tcp_udp_ratio(feat.traffic[2]);
    traffic->set_avg_packet_size(feat.traffic[3]);
    traffic->set_port_entropy(feat.traffic[4]);
    traffic->set_flow_duration_std(feat.traffic[5]);
    traffic->set_src_ip_entropy(feat.traffic[6]);
    traffic->set_dst_ip_concentration(feat.traffic[7]);
    traffic->set_protocol_variety(feat.traffic[8]);
    traffic->set_temporal_consistency(feat.traffic[9]);

    auto* internal = nf->mutable_internal_anomaly();
    internal->set_internal_connection_rate(feat.internal[0]);
    internal->set_service_port_consistency(feat.internal[1]);
    internal->set_protocol_regularity(feat.internal[2]);
    internal->set_packet_size_consistency(feat.internal[3]);
    internal->set_connection_duration_std(feat.internal[4]);
    internal->set_lateral_movement_score(feat.internal[5]);
    internal->set_service_discovery_patterns(feat.internal[6]);
    internal->set_data_exfiltration_indicators(feat.internal[7]);
    internal->set_temporal_anomaly_score(feat.internal[8]);
    internal->set_access_pattern_entropy(feat.internal[9]);

    nf->set_source_ip("192.168." + std::to_string(rng.uniform_int(1, 254)) +
                      "." + std::to_string(rng.uniform_int(1, 254)));
    nf->set_destination_ip("10.0." + std::to_string(rng.uniform_int(1, 254)) +
                           "." + std::to_string(rng.uniform_int(1, 254)));
    nf->set_source_port(rng.uniform_int(1024, 65535));

    std::vector<uint32_t> common_ports = {80, 443, 22, 3389, 445};
    nf->set_destination_port(rng.choice(common_ports));
    nf->set_protocol_name("TCP");

    auto prov_data = generate_provenance(rng, is_malicious);
    auto* prov = event.mutable_provenance();

    for (const auto& v : prov_data.verdicts) {
        auto* verdict = prov->add_verdicts();
        *verdict = v;
    }

    prov->set_discrepancy_score(prov_data.discrepancy_score);
    prov->set_final_decision(prov_data.final_decision);
    prov->set_global_timestamp_ns(std::chrono::system_clock::now().time_since_epoch().count());

    if (prov_data.discrepancy_score > 0.30f) {
        prov->set_discrepancy_reason("Engines disagree on threat level");
    }

    event.set_final_classification(is_malicious ? "MALICIOUS" : "BENIGN");
    event.set_overall_threat_score(prov_data.verdicts[1].confidence());

    return event;
}

// ============================================================================
// Statistics Tracking
// ============================================================================

struct Statistics {
    int total = 0;
    int malicious = 0;
    int benign = 0;

    std::map<std::string, int> attack_types;
    std::map<std::string, int> reason_codes;

    struct {
        int low = 0;
        int medium = 0;
        int high = 0;
    } discrepancy;
};

// ============================================================================
// Main
// ============================================================================

int main(int argc, char** argv) {
    int count = 100;
    double malicious_ratio = 0.20;
    std::string config_path = "/vagrant/tools/config/synthetic_generator_config.json";

    if (argc >= 2) count = std::stoi(argv[1]);
    if (argc >= 3) malicious_ratio = std::stod(argv[2]);
    if (argc >= 4) config_path = argv[3];

    std::cout << "\n";
    std::cout << "╔════════════════════════════════════════════════════════════╗\n";
    std::cout << "║  Synthetic Event Generator - Via Appia Quality             ║\n";
    std::cout << "║  Simplified: HTTP GET /seed (no EtcdClient dependency)     ║\n";
    std::cout << "╚════════════════════════════════════════════════════════════╝\n\n";

    try {
        // ═══════════════════════════════════════════════════════════════
        // 1. Load Configuration
        // ═══════════════════════════════════════════════════════════════
        std::cout << "📋 Loading configuration from: " << config_path << "\n";

        std::ifstream config_file(config_path);
        if (!config_file) {
            throw std::runtime_error("Cannot open config file: " + config_path);
        }

        json config;
        config_file >> config;
        std::string output_base = config["generation"]["output_base"];

        std::cout << "✅ Configuration loaded\n\n";

        // ═══════════════════════════════════════════════════════════════
        // 2. Get Encryption Seed from etcd-server (via etcd-client)
        // ═══════════════════════════════════════════════════════════════

        std::string encryption_seed_hex;

        if (config["etcd"]["enabled"]) {
            // Parse endpoint: "localhost:2379" → host="localhost", port=2379
            std::string endpoint = config["etcd"]["endpoints"][0];
            size_t colon_pos = endpoint.find(':');

            if (colon_pos == std::string::npos) {
                throw std::runtime_error("[etcd] Invalid endpoint format: " + endpoint +
                                        " (expected host:port)");
            }

            std::string host = endpoint.substr(0, colon_pos);
            int port = std::stoi(endpoint.substr(colon_pos + 1));

            std::cout << "🔗 [etcd] Initializing etcd-client: " << host << ":" << port << "\n";

            // Build etcd-client Config (CORRECT way)
            etcd_client::Config etcd_config;
            etcd_config.host = host;
            etcd_config.port = port;
            etcd_config.timeout_seconds = 5;
            etcd_config.component_name = config["component"]["name"];
            etcd_config.encryption_enabled = true;
            etcd_config.heartbeat_enabled = true;

            // Initialize etcd-client
            etcd_client::EtcdClient etcd(etcd_config);

            // CRITICAL: Connect and register (this initializes encryption_key)
            if (!etcd.connect()) {
                throw std::runtime_error("[etcd] Failed to connect to etcd-server");
            }

            if (!etcd.register_component()) {
                throw std::runtime_error("[etcd] Failed to register component");
            }

            std::cout << "✅ [etcd] Connected and registered: "
                      << config["component"]["name"] << "\n";

            // NOW we can get the encryption key (it's been initialized)
            encryption_seed_hex = etcd.get_encryption_key();

            if (encryption_seed_hex.empty()) {
                throw std::runtime_error("[etcd] Encryption key is empty after registration");
            }

            std::cout << "✅ [etcd] Retrieved encryption key ("
                      << encryption_seed_hex.size() << " hex chars)\n";

        } else {
            throw std::runtime_error("etcd is REQUIRED for 100% compliance");
        }

        // ═══════════════════════════════════════════════════════════════
        // 3. Convert HEX seed to binary
        // ═══════════════════════════════════════════════════════════════

        std::string encryption_seed;
        try {
            auto key_bytes = crypto_transport::hex_to_bytes(encryption_seed_hex);
            encryption_seed = std::string(key_bytes.begin(), key_bytes.end());
        } catch (const std::exception& e) {
            throw std::runtime_error(
                std::string("[crypto] Failed to convert hex seed: ") + e.what()
            );
        }

        if (encryption_seed.size() != 32) {
            throw std::runtime_error(
                "[crypto] Invalid key size: " + std::to_string(encryption_seed.size()) +
                " bytes (expected 32)"
            );
        }

        std::cout << "✅ [crypto] Encryption key converted: 32 bytes\n\n";

        // ═══════════════════════════════════════════════════════════════
        // 4. Create CryptoManager
        // ═══════════════════════════════════════════════════════════════

        auto crypto_manager = std::make_shared<crypto::CryptoManager>(encryption_seed);
        std::cout << "✅ [crypto] CryptoManager initialized (ChaCha20-Poly1305 + LZ4)\n\n";

        // ═══════════════════════════════════════════════════════════════
        // 5. Create Logger
        // ═══════════════════════════════════════════════════════════════

        auto console_sink = std::make_shared<spdlog::sinks::stdout_color_sink_mt>();
        auto logger = std::make_shared<spdlog::logger>("generator", console_sink);
        logger->set_level(spdlog::level::info);

        // ═══════════════════════════════════════════════════════════════
        // 6. Create RAGLogger (SAME as ml-detector)
        // ═══════════════════════════════════════════════════════════════

        ml_defender::RAGLoggerConfig rag_config;
        rag_config.base_path = config["rag_logger"]["base_dir"];
        rag_config.deployment_id = config["rag_logger"]["deployment_id"];
        rag_config.node_id = config["rag_logger"]["node_id"];
        rag_config.min_score_to_log = config["rag_logger"]["min_score_to_log"];
        rag_config.min_divergence_to_log = 0.0;
        rag_config.save_protobuf_artifacts = config["rag_logger"]["save_protobuf_artifacts"];
        rag_config.save_json_artifacts = config["rag_logger"]["save_json_artifacts"];

        auto rag_logger = std::make_unique<ml_defender::RAGLogger>(
            rag_config, logger, crypto_manager
        );

        logger->info("✅ RAGLogger initialized");
        logger->info("");

        // ═══════════════════════════════════════════════════════════════
        // 7. Print Summary
        // ═══════════════════════════════════════════════════════════════

        std::cout << "╔═══════════════════════════════════════════════════════════════╗\n";
        std::cout << "║  SYNTHETIC EVENT GENERATOR - CONFIGURATION                    ║\n";
        std::cout << "╚═══════════════════════════════════════════════════════════════╝\n\n";

        std::cout << "📦 Component: " << config["component"]["name"]
                  << " v" << config["component"]["version"] << "\n";
        std::cout << "   Node: " << config["component"]["node_id"] << "\n\n";

        std::cout << "🔒 Security:\n";
        std::cout << "   etcd-client: ";
        for (const auto& ep : config["etcd"]["endpoints"]) {
            std::cout << ep << " ";
        }
        std::cout << "\n";
        std::cout << "   Encryption: ChaCha20-Poly1305 (32-byte key via etcd-client)\n";
        std::cout << "   Compression: LZ4\n\n";

        std::cout << "🎯 Generation:\n";
        std::cout << "   Events: " << count << "\n";
        std::cout << "   Malicious ratio: " << std::fixed << std::setprecision(1)
                  << (malicious_ratio * 100) << "%\n";
        std::cout << "   Output: " << output_base << "\n\n";

        logger->info("🔒 Generating {} synthetic events...", count);
        logger->info("");

        // ═══════════════════════════════════════════════════════════════
        // 8. Generate Events
        // ═══════════════════════════════════════════════════════════════

        RandomGen rng;
        Statistics stats;
        stats.total = count;

        for (int i = 0; i < count; i++) {
            bool is_malicious = (rng.uniform(0.0, 1.0) < malicious_ratio);

            std::vector<std::string> attack_types = {"DDoS", "Ransomware"};
            std::string attack_type = is_malicious ? rng.choice(attack_types) : "Benign";

            auto event = generate_event(rng, i, is_malicious, attack_type);

            ml_defender::MLContext context;
            context.events_processed_total = i;
            context.attack_family = attack_type;
            context.level_1_label = is_malicious ? "Attack" : "Benign";
            context.level_1_confidence = event.overall_threat_score();
            context.investigation_priority =
                (event.provenance().discrepancy_score() > 0.50) ? "HIGH" : "MEDIUM";

            rag_logger->log_event(event, context);

            if (is_malicious) {
                stats.malicious++;
                stats.attack_types[attack_type]++;
            } else {
                stats.benign++;
            }

            float disc = event.provenance().discrepancy_score();
            if (disc < 0.25f) stats.discrepancy.low++;
            else if (disc < 0.50f) stats.discrepancy.medium++;
            else stats.discrepancy.high++;

            for (const auto& v : event.provenance().verdicts()) {
                stats.reason_codes[v.reason_code()]++;
            }

            if ((i + 1) % 10 == 0 || (i + 1) == count) {
                std::cout << "   [" << std::setw(3) << (i + 1) << "/" << count << "] "
                         << std::setw(12) << std::left << attack_type << " | "
                         << "disc=" << std::fixed << std::setprecision(3) << disc
                         << "\n";
            }
        }

        rag_logger->flush();

        // ═══════════════════════════════════════════════════════════════
        // 9. Print Statistics
        // ═══════════════════════════════════════════════════════════════

        std::cout << "\n";
        std::cout << "═══════════════════════════════════════════════════════════\n";
        std::cout << "📊 SYNTHETIC DATASET SUMMARY\n";
        std::cout << "═══════════════════════════════════════════════════════════\n\n";

        std::cout << "✅ Total events: " << stats.total << "\n";
        std::cout << "   Malicious: " << stats.malicious
                  << " (" << std::fixed << std::setprecision(1)
                  << (stats.malicious * 100.0 / stats.total) << "%)\n";
        std::cout << "   Benign: " << stats.benign
                  << " (" << (stats.benign * 100.0 / stats.total) << "%)\n\n";

        std::cout << "📈 Attack Types:\n";
        for (const auto& [type, count_val] : stats.attack_types) {
            std::cout << "   " << type << ": " << count_val << "\n";
        }
        std::cout << "\n";

        std::cout << "🎯 Discrepancy Distribution:\n";
        std::cout << "   Low (0.0-0.25): " << stats.discrepancy.low
                  << " (" << (stats.discrepancy.low * 100.0 / stats.total) << "%)\n";
        std::cout << "   Medium (0.25-0.5): " << stats.discrepancy.medium
                  << " (" << (stats.discrepancy.medium * 100.0 / stats.total) << "%)\n";
        std::cout << "   High (0.5-1.0): " << stats.discrepancy.high
                  << " (" << (stats.discrepancy.high * 100.0 / stats.total) << "%)\n\n";

        std::cout << "🔧 Reason Codes:\n";
        for (const auto& [code, count_val] : stats.reason_codes) {
            std::cout << "   " << code << ": " << count_val << "\n";
        }
        std::cout << "\n";

        auto rag_stats = rag_logger->get_statistics();
        std::cout << "📁 RAGLogger Statistics:\n";
        std::cout << "   Events logged: " << rag_stats["events_logged"] << "\n";
        std::cout << "   Current log: " << rag_stats["current_log_path"] << "\n\n";

        std::string spec_path = output_base + "/SPEC.json";
        std::ofstream spec_file(spec_path);
        spec_file << get_spec().dump(2);
        spec_file.close();

        std::cout << "📄 SPEC saved: " << spec_path << "\n";
        std::cout << "\n✅ Synthetic dataset generation complete!\n";
        std::cout << "═══════════════════════════════════════════════════════════\n\n";

        return 0;

    } catch (const std::exception& e) {
        std::cerr << "\n❌ ERROR: " << e.what() << "\n\n";
        return 1;
    }
}