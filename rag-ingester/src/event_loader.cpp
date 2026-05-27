// event_loader.cpp
// RAG Ingester - EventLoader Implementation
// Day 38: Updated to use shared CryptoManager (consistency with ml-detector)
// Via Appia Quality - Robust, exception-safe event processing

#include "event_loader.hpp"
#include <crypto_transport/contexts.hpp>
#include <lz4.h>
#include <cstring>
#include <fstream>
#include <string>
#include <vector>
#include <memory>
#include <optional>
#include <iostream>  // Para std::cerr si no hay logging
#include <cstring>
#include <stdexcept>
#include <cmath>

#include <crypto_transport/compression.hpp>
#include <network_security.pb.h>
#include <reason_codes.hpp>

namespace rag_ingester {

// ============================================================================
// EventLoader Implementation
// ============================================================================

EventLoader::EventLoader() {
    stats_ = {};
    // ADR-013 PHASE 2 — DAY 98: CryptoTransport via SeedClient
    // Fail-closed DAY 99: FATAL en producción, modo degradado solo con MLD_DEV_MODE=1
    try {
        seed_client_ = std::make_unique<ml_defender::SeedClient>(
            "/etc/ml-defender/rag-ingester/rag-ingester.json");
        seed_client_->load();
        rx_ = std::make_unique<crypto_transport::CryptoTransport>(
            *seed_client_, ml_defender::crypto::CTX_RAG_ARTIFACTS);
        std::cout << "[INFO] EventLoader: CryptoTransport inicializado (HKDF-SHA256)" << std::endl;
    } catch (const std::exception& e) {
        const char* dev_mode = std::getenv("MLD_DEV_MODE");
        if (dev_mode && std::string(dev_mode) == "1") {
            std::cerr << "[WARN] EventLoader: MLD_DEV_MODE=1 — modo plaintext permitido: "
                      << e.what() << std::endl;
        } else {
            std::cerr << "[FATAL] EventLoader: CryptoTransport no disponible: " << e.what()
                      << "\n[FATAL] Establece MLD_DEV_MODE=1 para modo desarrollo." << std::endl;
            std::terminate();
        }
    }
}

EventLoader::~EventLoader() = default;

Event EventLoader::load(const std::string& filepath) {
    // 1. Read encrypted file
    auto encrypted = read_file(filepath);

    // 2. Decrypt (ADR-013 PHASE 2 — CryptoTransport)
    auto decrypted = decrypt(encrypted);

    // 3. Decompress con cabecera LZ4 [uint32_t orig_size LE]
    auto decompressed = decompress(decrypted);

    // 4. Parse protobuf
    return parse_protobuf(decompressed);
}

std::vector<Event> EventLoader::load_batch(const std::vector<std::string>& filepaths) {
    std::vector<Event> events;
    events.reserve(filepaths.size());

    for (const auto& filepath : filepaths) {
        try {
            events.push_back(load(filepath));
        } catch (const std::exception& e) {
            std::cerr << "[ERROR] EventLoader: " << e.what() << std::endl;
        }
    }

    return events;
}

EventLoader::LoadStats EventLoader::get_stats() const noexcept {
    return stats_;
}

std::vector<uint8_t> EventLoader::read_file(const std::string& path) {
    std::ifstream file(path, std::ios::binary | std::ios::ate);

    if (!file) {
        throw std::runtime_error("Cannot open file: " + path);
    }

    auto size = file.tellg();
    if (size <= 0) {
        throw std::runtime_error("Empty file: " + path);
    }

    std::vector<uint8_t> buffer(static_cast<size_t>(size));
    file.seekg(0, std::ios::beg);
    file.read(reinterpret_cast<char*>(buffer.data()), size);

    if (!file) {
        throw std::runtime_error("Failed to read file: " + path);
    }

    return buffer;
}

std::vector<uint8_t> EventLoader::decrypt(const std::vector<uint8_t>& encrypted) {
    if (!rx_) {
        // Modo plaintext
        return encrypted;
    }
    return rx_->decrypt(encrypted);
}

std::vector<uint8_t> EventLoader::decompress(const std::vector<uint8_t>& compressed) {
    if (compressed.size() <= sizeof(uint32_t)) {
        return compressed;
    }

    // Cabecera LZ4: [uint32_t orig_size LE] + datos comprimidos
    uint32_t orig_size = 0;
    std::memcpy(&orig_size, compressed.data(), sizeof(orig_size));

    if (orig_size == 0 || orig_size > 64 * 1024 * 1024) {
        // Sin cabecera válida — devolver tal cual
        return compressed;
    }

    std::vector<uint8_t> decompressed(orig_size);
    int result = LZ4_decompress_safe(
        reinterpret_cast<const char*>(compressed.data() + sizeof(uint32_t)),
        reinterpret_cast<char*>(decompressed.data()),
        static_cast<int>(compressed.size() - sizeof(uint32_t)),
        static_cast<int>(orig_size)
    );

    if (result < 0) {
        // Fallo LZ4 — devolver datos sin comprimir
        std::cerr << "[WARN] EventLoader: LZ4 decompress failed — datos sin comprimir" << std::endl;
        return compressed;
    }

    decompressed.resize(result);
    return decompressed;
}

Event EventLoader::parse_protobuf(const std::vector<uint8_t>& data) {
    protobuf::NetworkSecurityEvent proto_event;

    if (!proto_event.ParseFromArray(data.data(), data.size())) {
        throw std::runtime_error("Failed to parse protobuf NetworkSecurityEvent");
    }

    Event event;
    event.event_id = proto_event.event_id();

    if (proto_event.has_event_timestamp()) {
        const auto& ts = proto_event.event_timestamp();
        event.timestamp_ns = ts.seconds() * 1'000'000'000ULL + ts.nanos();
    } else {
        event.timestamp_ns = 0;
    }

    if (proto_event.has_ml_analysis()) {
        const auto& ml = proto_event.ml_analysis();

        if (ml.has_level1_general_detection()) {
            event.final_class = ml.level1_general_detection().prediction_class();
            event.confidence = ml.level1_general_detection().confidence_score();
        }

        if (!ml.final_threat_classification().empty()) {
            event.final_class = ml.final_threat_classification();
            event.confidence = ml.ensemble_confidence();
        }
    }

    if (event.final_class.empty() && !proto_event.final_classification().empty()) {
        event.final_class = proto_event.final_classification();
        event.confidence = proto_event.overall_threat_score();
    }

    if (proto_event.has_capturing_node()) {
        event.source_detector = proto_event.capturing_node().node_id();
    } else {
        event.source_detector = proto_event.originating_node_id();
    }

    event.features = extract_features(&proto_event);

    // 🎯 ADR-002: Parse Multi-Engine Provenance
    if (proto_event.has_provenance()) {
        const auto& prov = proto_event.provenance();

        // Parse all engine verdicts
        for (int i = 0; i < prov.verdicts_size(); i++) {
            const auto& v = prov.verdicts(i);

            EngineVerdict verdict;
            verdict.engine_name = v.engine_name();
            verdict.classification = v.classification();
            verdict.confidence = v.confidence();
            verdict.reason_code = v.reason_code();
            verdict.timestamp_ns = v.timestamp_ns();

            event.verdicts.push_back(verdict);
        }

        // Parse provenance metadata
        event.discrepancy_score = prov.discrepancy_score();
        event.final_decision = prov.final_decision();

        // Log if high discrepancy
        if (event.discrepancy_score > 0.30f) {
            std::cout << "[INFO] EventLoader: High discrepancy event "
                      << event.event_id << " (score=" << event.discrepancy_score
                      << ", engines=" << event.verdicts.size() << ")" << std::endl;
        }
    } else {
        // No provenance - legacy event or sniffer-only
        event.discrepancy_score = 0.0f;
        event.final_decision = "UNKNOWN";
    }

    return event;
}

std::vector<float> EventLoader::extract_features(const void* proto_event_ptr) {
    const auto* proto_event =
        static_cast<const protobuf::NetworkSecurityEvent*>(proto_event_ptr);

    if (!proto_event->has_network_features()) {
        throw std::runtime_error("NetworkSecurityEvent missing network_features");
    }

    const auto& net = proto_event->network_features();

    std::vector<float> features;
    features.reserve(140);

    // PART 1: BASIC FLOW STATISTICS (61 features)
    features.push_back(static_cast<float>(net.protocol_number()));
    features.push_back(static_cast<float>(net.interface_mode()));
    features.push_back(static_cast<float>(net.source_ifindex()));
    features.push_back(static_cast<float>(net.flow_duration_microseconds() / 1e6));

    features.push_back(static_cast<float>(net.total_forward_packets()));
    features.push_back(static_cast<float>(net.total_backward_packets()));
    features.push_back(static_cast<float>(net.total_forward_bytes()));
    features.push_back(static_cast<float>(net.total_backward_bytes()));

    features.push_back(static_cast<float>(net.forward_packet_length_max()));
    features.push_back(static_cast<float>(net.forward_packet_length_min()));
    features.push_back(static_cast<float>(net.forward_packet_length_mean()));
    features.push_back(static_cast<float>(net.forward_packet_length_std()));

    features.push_back(static_cast<float>(net.backward_packet_length_max()));
    features.push_back(static_cast<float>(net.backward_packet_length_min()));
    features.push_back(static_cast<float>(net.backward_packet_length_mean()));
    features.push_back(static_cast<float>(net.backward_packet_length_std()));

    features.push_back(static_cast<float>(net.flow_bytes_per_second()));
    features.push_back(static_cast<float>(net.flow_packets_per_second()));
    features.push_back(static_cast<float>(net.forward_packets_per_second()));
    features.push_back(static_cast<float>(net.backward_packets_per_second()));
    features.push_back(static_cast<float>(net.download_upload_ratio()));
    features.push_back(static_cast<float>(net.average_packet_size()));
    features.push_back(static_cast<float>(net.average_forward_segment_size()));
    features.push_back(static_cast<float>(net.average_backward_segment_size()));

    features.push_back(static_cast<float>(net.flow_inter_arrival_time_mean()));
    features.push_back(static_cast<float>(net.flow_inter_arrival_time_std()));
    features.push_back(static_cast<float>(net.flow_inter_arrival_time_max()));
    features.push_back(static_cast<float>(net.flow_inter_arrival_time_min()));

    features.push_back(static_cast<float>(net.forward_inter_arrival_time_total()));
    features.push_back(static_cast<float>(net.forward_inter_arrival_time_mean()));
    features.push_back(static_cast<float>(net.forward_inter_arrival_time_std()));
    features.push_back(static_cast<float>(net.forward_inter_arrival_time_max()));
    features.push_back(static_cast<float>(net.forward_inter_arrival_time_min()));

    features.push_back(static_cast<float>(net.backward_inter_arrival_time_total()));
    features.push_back(static_cast<float>(net.backward_inter_arrival_time_mean()));
    features.push_back(static_cast<float>(net.backward_inter_arrival_time_std()));
    features.push_back(static_cast<float>(net.backward_inter_arrival_time_max()));
    features.push_back(static_cast<float>(net.backward_inter_arrival_time_min()));

    features.push_back(static_cast<float>(net.fin_flag_count()));
    features.push_back(static_cast<float>(net.syn_flag_count()));
    features.push_back(static_cast<float>(net.rst_flag_count()));
    features.push_back(static_cast<float>(net.psh_flag_count()));
    features.push_back(static_cast<float>(net.ack_flag_count()));
    features.push_back(static_cast<float>(net.urg_flag_count()));
    features.push_back(static_cast<float>(net.cwe_flag_count()));
    features.push_back(static_cast<float>(net.ece_flag_count()));

    features.push_back(static_cast<float>(net.forward_psh_flags()));
    features.push_back(static_cast<float>(net.backward_psh_flags()));
    features.push_back(static_cast<float>(net.forward_urg_flags()));
    features.push_back(static_cast<float>(net.backward_urg_flags()));

    features.push_back(static_cast<float>(net.forward_header_length()));
    features.push_back(static_cast<float>(net.backward_header_length()));
    features.push_back(static_cast<float>(net.forward_average_bytes_bulk()));
    features.push_back(static_cast<float>(net.forward_average_packets_bulk()));
    features.push_back(static_cast<float>(net.forward_average_bulk_rate()));
    features.push_back(static_cast<float>(net.backward_average_bytes_bulk()));
    features.push_back(static_cast<float>(net.backward_average_packets_bulk()));
    features.push_back(static_cast<float>(net.backward_average_bulk_rate()));

    features.push_back(static_cast<float>(net.minimum_packet_length()));
    features.push_back(static_cast<float>(net.maximum_packet_length()));
    features.push_back(static_cast<float>(net.packet_length_mean()));
    features.push_back(static_cast<float>(net.packet_length_std()));
    features.push_back(static_cast<float>(net.packet_length_variance()));

    features.push_back(static_cast<float>(net.active_mean()));
    features.push_back(static_cast<float>(net.idle_mean()));

    // PART 2: EMBEDDED DETECTOR FEATURES (40 features)

    if (net.has_ddos_embedded()) {
        const auto& ddos = net.ddos_embedded();
        features.push_back(ddos.syn_ack_ratio());
        features.push_back(ddos.packet_symmetry());
        features.push_back(ddos.source_ip_dispersion());
        features.push_back(ddos.protocol_anomaly_score());
        features.push_back(ddos.packet_size_entropy());
        features.push_back(ddos.traffic_amplification_factor());
        features.push_back(ddos.flow_completion_rate());
        features.push_back(ddos.geographical_concentration());
        features.push_back(ddos.traffic_escalation_rate());
        features.push_back(ddos.resource_saturation_score());
    } else {
        for (int i = 0; i < 10; i++) features.push_back(0.0f);
    }

    if (net.has_ransomware_embedded()) {
        const auto& ransomware = net.ransomware_embedded();
        features.push_back(ransomware.io_intensity());
        features.push_back(ransomware.entropy());
        features.push_back(ransomware.resource_usage());
        features.push_back(ransomware.network_activity());
        features.push_back(ransomware.file_operations());
        features.push_back(ransomware.process_anomaly());
        features.push_back(ransomware.temporal_pattern());
        features.push_back(ransomware.access_frequency());
        features.push_back(ransomware.data_volume());
        features.push_back(ransomware.behavior_consistency());
    } else {
        for (int i = 0; i < 10; i++) features.push_back(0.0f);
    }

    if (net.has_traffic_classification()) {
        const auto& traffic = net.traffic_classification();
        features.push_back(traffic.packet_rate());
        features.push_back(traffic.connection_rate());
        features.push_back(traffic.tcp_udp_ratio());
        features.push_back(traffic.avg_packet_size());
        features.push_back(traffic.port_entropy());
        features.push_back(traffic.flow_duration_std());
        features.push_back(traffic.src_ip_entropy());
        features.push_back(traffic.dst_ip_concentration());
        features.push_back(traffic.protocol_variety());
        features.push_back(traffic.temporal_consistency());
    } else {
        for (int i = 0; i < 10; i++) features.push_back(0.0f);
    }

    if (net.has_internal_anomaly()) {
        const auto& internal = net.internal_anomaly();
        features.push_back(internal.internal_connection_rate());
        features.push_back(internal.service_port_consistency());
        features.push_back(internal.protocol_regularity());
        features.push_back(internal.packet_size_consistency());
        features.push_back(internal.connection_duration_std());
        features.push_back(internal.lateral_movement_score());
        features.push_back(internal.service_discovery_patterns());
        features.push_back(internal.data_exfiltration_indicators());
        features.push_back(internal.temporal_anomaly_score());
        features.push_back(internal.access_pattern_entropy());
    } else {
        for (int i = 0; i < 10; i++) features.push_back(0.0f);
    }

    return features;
}

} // namespace rag_ingester