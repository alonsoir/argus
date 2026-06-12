// tools/synthetic_sniffer_injector.cpp
// Synthetic Sniffer → ML Detector Event Generator
// Generates NetworkSecurityEvent with 142 features for stress testing
// AUTHORS: Alonso Isidoro Roman + Claude (Anthropic)
// DATE: 2 February 2026 - Day 49 | Updated Day 66: --attack mode | Day 67: --ransomware mode | Migrated DAY 159: ADR-013 PHASE 2 CryptoTransport

#include <zmq.hpp>
#include <iostream>
#include <chrono>
#include <thread>
#include <random>
#include <cstdlib>
#include <iomanip>
#include <memory>

// Protobuf
#include "network_security.pb.h"
#include "flow/community_id.hpp"  // paridad cross-sensor (DAY 176)

// Crypto-transport (ADR-013 PHASE 2 — DAY 159)
#include <seed_client/seed_client.hpp>
#include <crypto_transport/transport.hpp>
#include <crypto_transport/contexts.hpp>
#include <lz4.h>
#include <cstring>

// etcd-client
#include <etcd_client/etcd_client.hpp>
// JSON config
#include <nlohmann/json.hpp>
#include <fstream>

class SyntheticSnifferInjector {
private:
    zmq::context_t zmq_ctx_;
    zmq::socket_t publisher_;  // PUSH → ml-detector PULL
    std::unique_ptr<etcd_client::EtcdClient> etcd_client_;
    std::unique_ptr<ml_defender::SeedClient> seed_client_;
    std::unique_ptr<crypto_transport::CryptoTransport> tx_;
    // crypto_manager_ eliminado DAY 159 — reemplazado por tx_ (CryptoTransport)
    std::string zmq_bind_address_{"tcp://*:5571"};  // default, overridden by JSON

    void load_zmq_config(const std::string& config_path) {
        try {
            std::ifstream f(config_path);
            if (!f.is_open()) {
                std::cerr << "⚠️  [config] Cannot open " << config_path << " — using defaults\n";
                return;
            }
            auto j = nlohmann::json::parse(f);
            auto& sock = j["network"]["output_socket"];
            std::string addr = sock["address"].get<std::string>();
            int port = sock["port"].get<int>();
            // Injector always binds (sniffer role)
            zmq_bind_address_ = "tcp://*:" + std::to_string(port);
            std::cout << "📋 [config] ZMQ endpoint from JSON: bind tcp://*:" << port << "\n";
        } catch (const std::exception& e) {
            std::cerr << "⚠️  [config] JSON parse error: " << e.what() << " — using defaults\n";
        }
    }
    std::mt19937 rng_;

    // Random generators
    float rand_float(float min, float max) {
        std::uniform_real_distribution<float> dist(min, max);
        return dist(rng_);
    }

    uint32_t rand_uint(uint32_t min, uint32_t max) {
        std::uniform_int_distribution<uint32_t> dist(min, max);
        return dist(rng_);
    }

    uint64_t rand_uint64(uint64_t min, uint64_t max) {
        std::uniform_int_distribution<uint64_t> dist(min, max);
        return dist(rng_);
    }

    std::string generate_random_ip() {
        return std::to_string(rand_uint(1, 254)) + "." +
               std::to_string(rand_uint(0, 255)) + "." +
               std::to_string(rand_uint(0, 255)) + "." +
               std::to_string(rand_uint(1, 254));
    }

    // Create complete NetworkSecurityEvent with all 142 features
    // ── community_id mode (DAY 176) ──────────────────────────────────────────
    // default=isomorphic: community_id es feature que se calcula SIEMPRE.
    // ARGUS_CID_MODE=mock -> formato auto-identificable "synth:test:<id>".
    enum class CidMode { Isomorphic, Mock };
    static CidMode parse_cid_mode() {
        const char* e = std::getenv("ARGUS_CID_MODE");
        std::string v = e ? std::string(e) : std::string("isomorphic");
        if (v == "isomorphic") return CidMode::Isomorphic;
        if (v == "mock")       return CidMode::Mock;
        std::cerr << "[FATAL] ARGUS_CID_MODE invalido: '" << v
                  << "' (esperado: isomorphic|mock)\n";
        std::exit(2);  // fail-closed: no swallowear typo de env var
    }
    protobuf::NetworkSecurityEvent create_synthetic_event(
        uint64_t event_id,
        bool is_attack = false,
        bool is_ransomware = false)
    {
        protobuf::NetworkSecurityEvent event;
        // community_id mode resuelto una sola vez (C++11 thread-safe static local)
        static const CidMode cid_mode = parse_cid_mode();

        // Event ID and timestamp
        event.set_event_id("synthetic-" + std::to_string(event_id));

        // DEBT-INJECTOR-NODEID-001 (DAY 177): node_id sintetico por eje de modo.
        // Col 3 vacia degenera flow_uid = hash(node_id || community_id || window).
        // Isomorfo emula UN punto de captura real -> node_id estable;
        // Mock es auto-identificable, se descarta antes de Kuzu -> id por evento.
        if (cid_mode == CidMode::Mock) {
            event.set_originating_node_id("synth:node:" + std::to_string(event_id));
        } else {
            event.set_originating_node_id("synth-node-00");
        }
        auto* timestamp = event.mutable_event_timestamp();
        auto now = std::chrono::system_clock::now();
        event.set_overall_threat_score(0.9f);  // synthetic — fuerza escritura en CSV

        // --force-above-threshold: fast detector fuerza escritura en CSV
        // El Level1 ONNX fue entrenado con CIC-IDS — valores sintéticos caen
        // fuera de su distribución de entrenamiento. Ver Day 66.
        if (is_attack) {
            event.set_fast_detector_score(0.9f);
            event.set_fast_detector_triggered(true);
            event.set_fast_detector_reason("synthetic_attack_forced");
        } else if (is_ransomware) {
            event.set_fast_detector_score(0.9f);
            event.set_fast_detector_triggered(true);
            event.set_fast_detector_reason("synthetic_ransomware_forced");
        }

        auto seconds = std::chrono::duration_cast<std::chrono::seconds>(now.time_since_epoch());
        timestamp->set_seconds(seconds.count());

        // Network Features (142 features)
        auto* nf = event.mutable_network_features();

        // Basic identification (6 features)
        nf->set_source_ip(generate_random_ip());
        nf->set_destination_ip(generate_random_ip());
        nf->set_source_port(rand_uint(1024, 65535));
        // Ransomware usa SMB(445)/RDP(3389) como destinos típicos
        if (is_ransomware) {
            uint32_t rdp_smb[] = {445, 3389};
            nf->set_destination_port(rdp_smb[rand_uint(0, 1)]);
            nf->set_protocol_number(6);   // TCP
            nf->set_protocol_name("TCP");
        } else {
            // DAY 177 (A): benigno correlacionable. proto=rand[1,255] daba ~99% no-TCP/UDP
            // -> compute_community_id() nullopt -> community_id vacio -> bronce vacio.
            // Un sensor real ve casi solo TCP/UDP; ademas number/name deben concordar.
            const bool use_tcp = is_attack ? true : (rand_uint(0, 1) == 1);
            nf->set_protocol_number(use_tcp ? 6 : 17);
            nf->set_protocol_name(use_tcp ? "TCP" : "UDP");
            nf->set_destination_port(is_attack ? 443 : rand_uint(1, 1024));
        }
        // 🔗 community_id — feature SIEMPRE poblada (DAY 176). Modo via ARGUS_CID_MODE.
        if (cid_mode == CidMode::Mock) {
            // auto-identificable: el correlation-engine lo descarta antes de Kuzu
            nf->set_community_id("synth:test:" + std::to_string(event_id));
        } else {
            // ISOMORFO: misma funcion pura que el sniffer real (NO reimplementacion)
            if (auto cid = sniffer::flow::compute_community_id(
                    nf->source_ip(), nf->destination_ip(),
                    static_cast<uint16_t>(nf->source_port()),
                    static_cast<uint16_t>(nf->destination_port()),
                    static_cast<uint8_t>(nf->protocol_number()))) {
                nf->set_community_id(*cid);
            }
            // else -> community_id "" diferido: proto no soportado, igual que produccion
        }

        // Dual-NIC deployment (4 features)
        nf->set_interface_mode(rand_uint(0, 2));
        nf->set_is_wan_facing(rand_uint(0, 1));
        nf->set_source_ifindex(rand_uint(1, 4));
        nf->set_source_interface("eth" + std::to_string(rand_uint(0, 1)));

        // Timing (3 features)
        auto* flow_start = nf->mutable_flow_start_time();
        flow_start->set_seconds(seconds.count());
        auto* flow_dur = nf->mutable_flow_duration();
        // Ransomware: conexiones de duración media (negociación + cifrado)
        flow_dur->set_seconds(is_attack ? rand_uint(0, 1)
                            : is_ransomware ? rand_uint(5, 120)
                            : rand_uint(0, 300));

        // Flow duration microseconds — feature[21] del Level 1
        nf->set_flow_duration_microseconds(
            is_attack    ? rand_uint64(1000, 50000)
          : is_ransomware ? rand_uint64(5000000, 120000000)
          :                 rand_uint64(1000, 300000000));

        // Packet statistics (4 features) — features [1][8][12][15] del Level 1
        if (is_attack) {
            // DDoS signature: inundación asimétrica — muchos fwd, casi nada bwd
            nf->set_total_forward_packets(rand_uint64(50000, 500000));
            nf->set_total_backward_packets(rand_uint64(0, 10));
            nf->set_total_forward_bytes(rand_uint64(3200000, 15000000));
            nf->set_total_backward_bytes(rand_uint64(0, 640));
        } else if (is_ransomware) {
            // Ransomware: volumen moderado, bidireccional (cifrado in-situ + C2)
            nf->set_total_forward_packets(rand_uint64(100, 5000));
            nf->set_total_backward_packets(rand_uint64(80, 4000));
            nf->set_total_forward_bytes(rand_uint64(50000, 5000000));
            nf->set_total_backward_bytes(rand_uint64(40000, 4000000));
        } else {
            nf->set_total_forward_packets(rand_uint64(1, 10000));
            nf->set_total_backward_packets(rand_uint64(1, 10000));
            nf->set_total_forward_bytes(rand_uint64(64, 15000000));
            nf->set_total_backward_bytes(rand_uint64(64, 15000000));
        }

        // Forward packet length stats — features [2][3][10] del Level 1
        if (is_attack) {
            // SYN packets: pequeños y muy uniformes
            nf->set_forward_packet_length_max(rand_uint64(60, 80));
            nf->set_forward_packet_length_min(rand_uint64(40, 60));
            nf->set_forward_packet_length_mean(rand_float(52, 66));
            nf->set_forward_packet_length_std(rand_float(0, 8));
        } else if (is_ransomware) {
            // Ransomware: datos cifrados → paquetes grandes y variables
            nf->set_forward_packet_length_max(rand_uint64(1400, 1500));
            nf->set_forward_packet_length_min(rand_uint64(40, 100));
            nf->set_forward_packet_length_mean(rand_float(800, 1400));
            nf->set_forward_packet_length_std(rand_float(100, 400));
        } else {
            nf->set_forward_packet_length_max(rand_uint64(64, 1500));
            nf->set_forward_packet_length_min(rand_uint64(20, 64));
            nf->set_forward_packet_length_mean(rand_float(64, 1500));
            nf->set_forward_packet_length_std(rand_float(0, 500));
        }

        // Backward packet length stats — features [7][19][20] del Level 1
        if (is_attack) {
            // Sin respuesta del servidor → backward casi vacío
            nf->set_backward_packet_length_max(rand_uint64(0, 20));
            nf->set_backward_packet_length_min(0);
            nf->set_backward_packet_length_mean(rand_float(0, 5));
            nf->set_backward_packet_length_std(rand_float(0, 2));
        } else if (is_ransomware) {
            // Respuestas del C2: también grandes (claves, instrucciones cifradas)
            nf->set_backward_packet_length_max(rand_uint64(1200, 1500));
            nf->set_backward_packet_length_min(rand_uint64(40, 100));
            nf->set_backward_packet_length_mean(rand_float(600, 1200));
            nf->set_backward_packet_length_std(rand_float(100, 400));
        } else {
            nf->set_backward_packet_length_max(rand_uint64(64, 1500));
            nf->set_backward_packet_length_min(rand_uint64(20, 64));
            nf->set_backward_packet_length_mean(rand_float(64, 1500));
            nf->set_backward_packet_length_std(rand_float(0, 500));
        }

        // Flow rates — features [11][22] del Level 1
        if (is_attack) {
            nf->set_flow_bytes_per_second(rand_float(5000000, 50000000));
            nf->set_flow_packets_per_second(rand_float(50000, 200000));
            nf->set_forward_packets_per_second(rand_float(50000, 200000));
            nf->set_backward_packets_per_second(rand_float(0, 10));
            nf->set_average_packet_size(rand_float(40, 70));
            nf->set_average_forward_segment_size(rand_float(40, 70));
            nf->set_average_backward_segment_size(rand_float(0, 10));
        } else if (is_ransomware) {
            // Tasa moderada pero sostenida (cifrado continuo de ficheros)
            nf->set_flow_bytes_per_second(rand_float(50000, 500000));
            nf->set_flow_packets_per_second(rand_float(50, 1000));
            nf->set_forward_packets_per_second(rand_float(30, 600));
            nf->set_backward_packets_per_second(rand_float(20, 400));
            nf->set_average_packet_size(rand_float(800, 1400));
            nf->set_average_forward_segment_size(rand_float(800, 1460));
            nf->set_average_backward_segment_size(rand_float(600, 1460));
        } else {
            nf->set_flow_bytes_per_second(rand_float(100, 100000));
            nf->set_flow_packets_per_second(rand_float(1, 10000));
            nf->set_forward_packets_per_second(rand_float(1, 5000));
            nf->set_backward_packets_per_second(rand_float(1, 5000));
            nf->set_average_packet_size(rand_float(64, 1500));
            nf->set_average_forward_segment_size(rand_float(64, 1460));
            nf->set_average_backward_segment_size(rand_float(64, 1460));
        }
        nf->set_download_upload_ratio(
            is_attack    ? rand_float(0.0, 0.001)
          : is_ransomware ? rand_float(0.6, 1.2)   // upload/download casi simétrico
          :                 rand_float(0.1, 10.0));

        // Flow IAT (4 features) — SIEMPRE presente en ambas ramas
        nf->set_flow_inter_arrival_time_mean(
            is_attack    ? rand_float(0.000001, 0.00005)
          : is_ransomware ? rand_float(0.001, 0.05)   // regular, pausado
          :                 rand_float(0.001, 1.0));
        nf->set_flow_inter_arrival_time_std(
            is_attack    ? rand_float(0.0, 0.00001)
          : is_ransomware ? rand_float(0.0, 0.01)
          :                 rand_float(0.0, 0.5));
        nf->set_flow_inter_arrival_time_max(
            is_attack    ? rand_uint64(100, 5000)
          : is_ransomware ? rand_uint64(5000, 50000)
          :                 rand_uint64(1000, 2000000));
        nf->set_flow_inter_arrival_time_min(
            is_attack    ? rand_uint64(0, 50)
          : is_ransomware ? rand_uint64(100, 2000)
          :                 rand_uint64(0, 10000));

        // Forward IAT (5 features) — feature[16] del Level 1
        nf->set_forward_inter_arrival_time_total(
            is_attack    ? rand_float(0.001, 5)
          : is_ransomware ? rand_float(5, 120)
          :                 rand_float(0.001, 300));
        nf->set_forward_inter_arrival_time_mean(
            is_attack    ? rand_float(0.000001, 0.00005)
          : is_ransomware ? rand_float(0.001, 0.05)
          :                 rand_float(0.001, 1.0));
        nf->set_forward_inter_arrival_time_std(
            is_attack    ? rand_float(0.0, 0.00001)
          : is_ransomware ? rand_float(0.0, 0.01)
          :                 rand_float(0.0, 0.5));
        nf->set_forward_inter_arrival_time_max(
            is_attack    ? rand_uint64(100, 5000)
          : is_ransomware ? rand_uint64(5000, 50000)
          :                 rand_uint64(1000, 2000000));
        nf->set_forward_inter_arrival_time_min(
            is_attack    ? rand_uint64(0, 100)
          : is_ransomware ? rand_uint64(100, 2000)
          :                 rand_uint64(0, 10000));

        // Backward IAT (5 features)
        nf->set_backward_inter_arrival_time_total(rand_float(0.001, 300));
        nf->set_backward_inter_arrival_time_mean(rand_float(0.001, 1.0));
        nf->set_backward_inter_arrival_time_std(rand_float(0.0, 0.5));
        nf->set_backward_inter_arrival_time_max(rand_uint64(1000, 2000000));
        nf->set_backward_inter_arrival_time_min(rand_uint64(0, 10000));

        // TCP Flags — features [4][6] del Level 1
        if (is_attack) {
            // SYN flood: muchos SYN, sin ACK ni PSH
            nf->set_fin_flag_count(rand_uint(0, 1));
            nf->set_syn_flag_count(rand_uint(500, 5000));
            nf->set_rst_flag_count(rand_uint(0, 3));
            nf->set_psh_flag_count(rand_uint(0, 2));
            nf->set_ack_flag_count(rand_uint(0, 5));
            nf->set_urg_flag_count(0);
            nf->set_cwe_flag_count(0);
            nf->set_ece_flag_count(0);
        } else if (is_ransomware) {
            // Ransomware: conexiones TCP completas (handshake + transferencia)
            nf->set_fin_flag_count(rand_uint(2, 10));
            nf->set_syn_flag_count(rand_uint(1, 5));
            nf->set_rst_flag_count(rand_uint(0, 2));
            nf->set_psh_flag_count(rand_uint(20, 200));   // mucho PSH (datos)
            nf->set_ack_flag_count(rand_uint(50, 500));
            nf->set_urg_flag_count(0);
            nf->set_cwe_flag_count(0);
            nf->set_ece_flag_count(0);
        } else {
            nf->set_fin_flag_count(rand_uint(0, 5));
            nf->set_syn_flag_count(rand_uint(0, 10));
            nf->set_rst_flag_count(rand_uint(0, 5));
            nf->set_psh_flag_count(rand_uint(0, 50));
            nf->set_ack_flag_count(rand_uint(0, 100));
            nf->set_urg_flag_count(rand_uint(0, 2));
            nf->set_cwe_flag_count(rand_uint(0, 1));
            nf->set_ece_flag_count(rand_uint(0, 1));
        }

        // TCP Flags directional (4 features)
        nf->set_forward_psh_flags(rand_uint(0, 25));
        nf->set_backward_psh_flags(rand_uint(0, 25));
        nf->set_forward_urg_flags(rand_uint(0, 1));
        nf->set_backward_urg_flags(rand_uint(0, 1));

        // Headers and bulk (8 features)
        nf->set_forward_header_length(rand_float(20, 60));
        nf->set_backward_header_length(rand_float(20, 60));
        nf->set_forward_average_bytes_bulk(rand_float(0, 100000));
        nf->set_forward_average_packets_bulk(rand_float(0, 100));
        nf->set_forward_average_bulk_rate(rand_float(0, 10000));
        nf->set_backward_average_bytes_bulk(rand_float(0, 100000));
        nf->set_backward_average_packets_bulk(rand_float(0, 100));
        nf->set_backward_average_bulk_rate(rand_float(0, 10000));

        // Additional packet stats — features [0][5][17] del Level 1
        if (is_attack) {
            nf->set_minimum_packet_length(rand_uint64(40, 60));
            nf->set_maximum_packet_length(rand_uint64(60, 80));
            nf->set_packet_length_mean(rand_float(40, 70));
            nf->set_packet_length_std(rand_float(0, 10));
            nf->set_packet_length_variance(rand_float(0, 100));
        } else if (is_ransomware) {
            // Datos cifrados: paquetes grandes y alta varianza
            nf->set_minimum_packet_length(rand_uint64(40, 100));
            nf->set_maximum_packet_length(rand_uint64(1400, 1500));
            nf->set_packet_length_mean(rand_float(700, 1300));
            nf->set_packet_length_std(rand_float(200, 500));
            nf->set_packet_length_variance(rand_float(40000, 250000));
        } else {
            nf->set_minimum_packet_length(rand_uint64(20, 64));
            nf->set_maximum_packet_length(rand_uint64(64, 1500));
            nf->set_packet_length_mean(rand_float(64, 1500));
            nf->set_packet_length_std(rand_float(0, 500));
            nf->set_packet_length_variance(rand_float(0, 250000));
        }

        // Active/Idle (2 features)
        nf->set_active_mean(rand_float(0.001, 10.0));
        nf->set_idle_mean(rand_float(0.001, 10.0));

        // DDoS Embedded Features (10 features)
        auto* ddos = nf->mutable_ddos_embedded();
        if (is_attack) {
            ddos->set_syn_ack_ratio(rand_float(0.95, 1.0));
            ddos->set_packet_symmetry(rand_float(0.0, 0.05));
            ddos->set_source_ip_dispersion(rand_float(0.8, 1.0));
            ddos->set_protocol_anomaly_score(rand_float(0.7, 1.0));
            ddos->set_packet_size_entropy(rand_float(0.0, 1.0));
            ddos->set_traffic_amplification_factor(rand_float(50, 100));
            ddos->set_flow_completion_rate(rand_float(0.0, 0.05));
            ddos->set_geographical_concentration(rand_float(0.7, 1.0));
            ddos->set_traffic_escalation_rate(rand_float(7.0, 10.0));
            ddos->set_resource_saturation_score(rand_float(0.8, 1.0));
        } else {
            // Ransomware y benign: DDoS features normales
            ddos->set_syn_ack_ratio(rand_float(0.0, 1.0));
            ddos->set_packet_symmetry(rand_float(0.0, 1.0));
            ddos->set_source_ip_dispersion(rand_float(0.0, 1.0));
            ddos->set_protocol_anomaly_score(rand_float(0.0, 1.0));
            ddos->set_packet_size_entropy(rand_float(0.0, 8.0));
            ddos->set_traffic_amplification_factor(rand_float(1.0, 100.0));
            ddos->set_flow_completion_rate(rand_float(0.0, 1.0));
            ddos->set_geographical_concentration(rand_float(0.0, 1.0));
            ddos->set_traffic_escalation_rate(rand_float(0.0, 10.0));
            ddos->set_resource_saturation_score(rand_float(0.0, 1.0));
        }

        // Ransomware Embedded Features (10 features)
        auto* ransomware = nf->mutable_ransomware_embedded();
        if (is_ransomware) {
            // Firma ransomware: alta entropía (datos cifrados), I/O intensivo,
            // operaciones de fichero masivas. Ver Day 67.
            ransomware->set_io_intensity(rand_float(0.85, 1.0));
            ransomware->set_entropy(rand_float(7.0, 8.0));
            ransomware->set_resource_usage(rand_float(0.7, 1.0));
            ransomware->set_network_activity(rand_float(0.5, 0.9));
            ransomware->set_file_operations(rand_float(0.90, 1.0));
            ransomware->set_process_anomaly(rand_float(0.7, 1.0));
            ransomware->set_temporal_pattern(rand_float(0.6, 1.0));
            ransomware->set_access_frequency(rand_float(0.7, 1.0));
            ransomware->set_data_volume(rand_float(0.6, 1.0));
            ransomware->set_behavior_consistency(rand_float(0.8, 1.0));
        } else {
            ransomware->set_io_intensity(rand_float(0.0, 1.0));
            ransomware->set_entropy(rand_float(0.0, 8.0));
            ransomware->set_resource_usage(rand_float(0.0, 1.0));
            ransomware->set_network_activity(rand_float(0.0, 1.0));
            ransomware->set_file_operations(rand_float(0.0, 1.0));
            ransomware->set_process_anomaly(rand_float(0.0, 1.0));
            ransomware->set_temporal_pattern(rand_float(0.0, 1.0));
            ransomware->set_access_frequency(rand_float(0.0, 1.0));
            ransomware->set_data_volume(rand_float(0.0, 1.0));
            ransomware->set_behavior_consistency(rand_float(0.0, 1.0));
        }

        // Traffic Classification Features (10 features)
        auto* traffic = nf->mutable_traffic_classification();
        traffic->set_packet_rate(rand_float(0.0, 1.0));
        traffic->set_connection_rate(rand_float(0.0, 1.0));
        traffic->set_tcp_udp_ratio(rand_float(0.0, 1.0));
        traffic->set_avg_packet_size(rand_float(0.0, 1.0));
        traffic->set_port_entropy(rand_float(0.0, 8.0));
        traffic->set_flow_duration_std(rand_float(0.0, 1.0));
        traffic->set_src_ip_entropy(rand_float(0.0, 8.0));
        traffic->set_dst_ip_concentration(rand_float(0.0, 1.0));
        traffic->set_protocol_variety(rand_float(0.0, 1.0));
        traffic->set_temporal_consistency(rand_float(0.0, 1.0));

        // Internal Anomaly Features (10 features)
        auto* internal = nf->mutable_internal_anomaly();
        internal->set_internal_connection_rate(rand_float(0.0, 1.0));
        internal->set_service_port_consistency(rand_float(0.0, 1.0));
        internal->set_protocol_regularity(rand_float(0.0, 1.0));
        internal->set_packet_size_consistency(rand_float(0.0, 1.0));
        internal->set_connection_duration_std(rand_float(0.0, 1.0));
        internal->set_lateral_movement_score(
            is_ransomware ? rand_float(0.7, 1.0) : rand_float(0.0, 1.0));
        internal->set_service_discovery_patterns(
            is_ransomware ? rand_float(0.6, 1.0) : rand_float(0.0, 1.0));
        internal->set_data_exfiltration_indicators(
            is_ransomware ? rand_float(0.7, 1.0) : rand_float(0.0, 1.0));
        internal->set_temporal_anomaly_score(rand_float(0.0, 1.0));
        internal->set_access_pattern_entropy(rand_float(0.0, 8.0));

        // Ransomware 20 features (additional)
        auto* ransomware20 = nf->mutable_ransomware();
        if (is_ransomware) {
            // Firma ransomware20: RDP brute-force, SMB lateral, sin SYN flood
            ransomware20->set_dns_query_entropy(rand_float(3.0, 6.0));
            ransomware20->set_new_external_ips_30s(rand_uint(1, 10));
            ransomware20->set_dns_query_rate_per_min(rand_float(5.0, 30.0));
            ransomware20->set_failed_dns_queries_ratio(rand_float(0.1, 0.4));
            ransomware20->set_tls_self_signed_cert_count(rand_uint(1, 5));
            ransomware20->set_non_standard_port_http_count(rand_uint(0, 5));
            ransomware20->set_smb_connection_diversity(rand_uint(20, 50));   // alto: lateral movement
            ransomware20->set_rdp_failed_auth_count(rand_uint(10, 50));      // alto: brute force
            ransomware20->set_new_internal_connections_30s(rand_uint(10, 40));
            ransomware20->set_port_scan_pattern_score(rand_float(0.5, 0.9));
            ransomware20->set_upload_download_ratio_30s(rand_float(0.8, 1.5));
            ransomware20->set_burst_connections_count(rand_uint(5, 30));
            ransomware20->set_unique_destinations_30s(rand_uint(5, 30));
            ransomware20->set_large_upload_sessions_count(rand_uint(2, 15));
            ransomware20->set_nocturnal_activity_flag(rand_uint(0, 1));
            ransomware20->set_connection_rate_stddev(rand_float(1.0, 5.0));
            ransomware20->set_protocol_diversity_score(rand_float(0.3, 0.7));
            ransomware20->set_avg_flow_duration_seconds(rand_float(10.0, 120.0));
            ransomware20->set_tcp_rst_ratio(rand_float(0.0, 0.1));
            ransomware20->set_syn_without_ack_ratio(rand_float(0.0, 0.05));  // bajo: TCP completo
        } else {
            ransomware20->set_dns_query_entropy(rand_float(0.0, 8.0));
            ransomware20->set_new_external_ips_30s(rand_uint(0, 100));
            ransomware20->set_dns_query_rate_per_min(rand_float(0.0, 100.0));
            ransomware20->set_failed_dns_queries_ratio(rand_float(0.0, 1.0));
            ransomware20->set_tls_self_signed_cert_count(rand_uint(0, 10));
            ransomware20->set_non_standard_port_http_count(rand_uint(0, 20));
            ransomware20->set_smb_connection_diversity(rand_uint(0, 50));
            ransomware20->set_rdp_failed_auth_count(rand_uint(0, 10));
            ransomware20->set_new_internal_connections_30s(rand_uint(0, 50));
            ransomware20->set_port_scan_pattern_score(rand_float(0.0, 1.0));
            ransomware20->set_upload_download_ratio_30s(rand_float(0.0, 10.0));
            ransomware20->set_burst_connections_count(rand_uint(0, 100));
            ransomware20->set_unique_destinations_30s(rand_uint(0, 100));
            ransomware20->set_large_upload_sessions_count(rand_uint(0, 20));
            ransomware20->set_nocturnal_activity_flag(rand_uint(0, 1));
            ransomware20->set_connection_rate_stddev(rand_float(0.0, 10.0));
            ransomware20->set_protocol_diversity_score(rand_float(0.0, 1.0));
            ransomware20->set_avg_flow_duration_seconds(rand_float(0.1, 300.0));
            ransomware20->set_tcp_rst_ratio(rand_float(0.0, 1.0));
            ransomware20->set_syn_without_ack_ratio(
                is_attack ? rand_float(0.9, 1.0) : rand_float(0.0, 1.0));
        }

        return event;
    }

public:
    SyntheticSnifferInjector(const std::string& etcd_endpoint = "localhost:2379")
        : zmq_ctx_(1)
        , publisher_(zmq_ctx_, zmq::socket_type::push)
        , rng_(std::random_device{}())
    {
        // Bind to ml-detector input port
        // DAY 159: leer endpoint desde sniffer.json (Single Source of Truth)
        load_zmq_config("/etc/ml-defender/sniffer/sniffer.json");
        publisher_.bind(zmq_bind_address_);

        // Parse endpoint: "localhost:2379" → host="localhost", port=2379
        size_t colon_pos = etcd_endpoint.find(':');
        if (colon_pos == std::string::npos) {
            throw std::runtime_error("Invalid etcd endpoint format (expected host:port)");
        }

        std::string host = etcd_endpoint.substr(0, colon_pos);
        int port = std::stoi(etcd_endpoint.substr(colon_pos + 1));

        std::cout << "🔗 [etcd] Initializing etcd-client: " << host << ":" << port << "\n";

        // Build etcd-client Config
        etcd_client::Config etcd_config;
        etcd_config.host = host;
        etcd_config.port = port;
        etcd_config.timeout_seconds = 5;
        etcd_config.component_name = "cpp_evolutionary_sniffer";
        etcd_config.encryption_enabled = true;
        etcd_config.heartbeat_enabled = true;

        // Initialize etcd-client
        etcd_client_ = std::make_unique<etcd_client::EtcdClient>(etcd_config);

        if (!etcd_client_->connect()) {
            throw std::runtime_error("Failed to connect to etcd-server");
        }
        if (!etcd_client_->register_component()) {
            throw std::runtime_error("Failed to register component");
        }

        std::cout << "✅ [etcd] Connected and registered\n";

        // ADR-013 PHASE 2 — DAY 159: CryptoTransport via SeedClient
        seed_client_ = std::make_unique<ml_defender::SeedClient>(
            "/etc/ml-defender/sniffer/sniffer.json");
        seed_client_->load();
        tx_ = std::make_unique<crypto_transport::CryptoTransport>(
            *seed_client_, ml_defender::crypto::CTX_SNIFFER_TO_ML);
        std::cout << "✅ [crypto] CryptoTransport inicializado (HKDF-SHA256 + ChaCha20-Poly1305)\n";

        std::this_thread::sleep_for(std::chrono::milliseconds(500));

        std::cout << "✅ Synthetic Sniffer Injector initialized\n";
        std::cout << "   Port: 5571 (ml-detector input)\n";
        std::cout << "   Encryption: ChaCha20-Poly1305 + LZ4\n\n";
    }

    void inject_events(uint64_t total_events, uint64_t events_per_sec,
                       bool is_attack = false, bool is_ransomware = false)
    {
        if (is_attack) {
            std::cout << "   Mode: ⚔️  ATTACK (DDoS signature)\n";
        } else if (is_ransomware) {
            std::cout << "   Mode: 🔒 RANSOMWARE (encryption + lateral movement signature)\n";
        } else {
            std::cout << "   Mode: 🟢 BENIGN (random)\n";
        }

        const auto interval = std::chrono::nanoseconds(1'000'000'000 / events_per_sec);

        std::cout << "🚀 Injecting " << total_events << " events @ "
                  << events_per_sec << " events/sec\n";
        std::cout << "   Interval: " << interval.count() << " ns\n\n";

        auto start_time = std::chrono::steady_clock::now();
        uint64_t sent = 0;
        uint64_t last_report = 0;

        for (uint64_t i = 0; i < total_events; ++i) {
            auto event_start = std::chrono::steady_clock::now();

            auto event = create_synthetic_event(i, is_attack, is_ransomware);

            std::string serialized;
            if (!event.SerializeToString(&serialized)) {
                std::cerr << "❌ Failed to serialize event " << i << "\n";
                continue;
            }

            // ADR-013 PHASE 2 — DAY 159: LZ4 LE + CryptoTransport
            std::vector<uint8_t> to_encrypt;
            {
                int orig_size = static_cast<int>(serialized.size());
                int max_compressed = LZ4_compressBound(orig_size);
                std::vector<uint8_t> compressed(sizeof(uint32_t) + static_cast<size_t>(max_compressed));
                uint32_t orig_le = static_cast<uint32_t>(orig_size);
                std::memcpy(compressed.data(), &orig_le, sizeof(orig_le));
                int compressed_size = LZ4_compress_default(
                    serialized.data(),
                    reinterpret_cast<char*>(compressed.data() + sizeof(uint32_t)),
                    orig_size, max_compressed);
                if (compressed_size > 0) {
                    compressed.resize(sizeof(uint32_t) + static_cast<size_t>(compressed_size));
                    to_encrypt = std::move(compressed);
                } else {
                    to_encrypt = std::vector<uint8_t>(serialized.begin(), serialized.end());
                }
            }
            auto encrypted = tx_->encrypt(to_encrypt);

            zmq::message_t msg(encrypted.data(), encrypted.size());
            publisher_.send(msg, zmq::send_flags::dontwait);

            sent++;

            if (sent - last_report >= events_per_sec) {
                auto elapsed     = std::chrono::steady_clock::now() - start_time;
                auto elapsed_sec = std::chrono::duration<double>(elapsed).count();
                std::cout << "\r📊 Sent: " << sent << "/" << total_events
                          << " (" << std::fixed << std::setprecision(1)
                          << (100.0 * sent / total_events) << "%) "
                          << "@ " << (sent / elapsed_sec) << " events/sec    " << std::flush;
                last_report = sent;
            }

            auto event_end = std::chrono::steady_clock::now();
            auto elapsed   = event_end - event_start;
            if (elapsed < interval) {
                std::this_thread::sleep_for(interval - elapsed);
            }
        }

        auto total_time = std::chrono::steady_clock::now() - start_time;
        auto total_sec  = std::chrono::duration<double>(total_time).count();

        std::cout << "\n\n✅ Injection complete!\n";
        std::cout << "   Total events: " << sent << "\n";
        std::cout << "   Total time:   " << total_sec << " sec\n";
        std::cout << "   Actual rate:  " << (sent / total_sec) << " events/sec\n\n";
    }
};

int main(int argc, char* argv[]) {
    if (argc < 3 || argc > 4) {
        std::cerr << "Usage: " << argv[0]
                  << " <total_events> <events_per_second> [--attack|--ransomware]\n";
        std::cerr << "Example: " << argv[0] << " 100 10 --attack\n";
        std::cerr << "Example: " << argv[0] << " 100 10 --ransomware\n";
        return 1;
    }

    uint64_t total        = std::stoull(argv[1]);
    uint64_t rate         = std::stoull(argv[2]);
    bool     is_attack    = (argc == 4 && std::string(argv[3]) == "--attack");
    bool     is_ransomware = (argc == 4 && std::string(argv[3]) == "--ransomware");

    // fail-closed ANTES de tocar etcd/crypto/ZMQ (DAY 176): valida ARGUS_CID_MODE.
    {
        const char* e = std::getenv("ARGUS_CID_MODE");
        std::string v = e ? std::string(e) : std::string("isomorphic");
        if (v != "isomorphic" && v != "mock") {
            std::cerr << "[FATAL] ARGUS_CID_MODE invalido: '" << v
                      << "' (esperado: isomorphic|mock)\n";
            return 2;  // fail-closed antes de construir el injector
        }
    }

    try {
        SyntheticSnifferInjector injector;
        injector.inject_events(total, rate, is_attack, is_ransomware);
    } catch (const std::exception& e) {
        std::cerr << "❌ Error: " << e.what() << "\n";
        return 1;
    }
    return 0;
}