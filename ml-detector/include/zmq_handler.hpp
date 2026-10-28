#pragma once
#include "memory_utils.hpp"

#include <zmq.hpp>
#include <memory>
#include <atomic>
#include <thread>
#include <mutex>
#include <chrono>
#include <time.h>  // [TIMEBASE-D296] clock_gettime(CLOCK_MONOTONIC)
#include <spdlog/spdlog.h>

#include "feature_extractor.hpp"

#include "ml_defender/ransomware_detector.hpp"
#include "config_loader.hpp"
#include "onnx_model.hpp"
#include "ml_defender/traffic_detector.hpp"
#include "ml_defender/internal_detector.hpp"

#include "network_security.pb.h"

// ADR-013 PHASE 2 — DAY 98: CryptoTransport via SeedClient (sustituye CryptoManager)
// DEPRECATED DAY 98 — #include <crypto_transport/crypto_manager.hpp>
#include <seed_client/seed_client.hpp>
#include <crypto_transport/transport.hpp>
#include <lz4.h>

#include "correlation_writer.hpp"
#include "ddos_dataset_writer.hpp"  // [DDOS-DATASET-D287]
#include "plugin_loader/plugin_loader.hpp"  // ADR-012 PHASE 2d

namespace ml_detector {

class ZMQHandler {
public:
    struct Stats {
        uint64_t events_received = 0;
        uint64_t events_processed = 0;
        uint64_t events_sent = 0;
        uint64_t attacks_detected = 0;
        uint64_t send_failures = 0;          // [SUMMARY-D285] descartes hacia el firewall
        uint64_t detections_ransomware = 0;  // [SUMMARY-D285]
        uint64_t detections_internal = 0;    // [SUMMARY-D285]
        uint64_t ddos_v2_presion = 0;        // [DDOS-V2-D293] eventos que pasan la etapa 1
        uint64_t ddos_v2_ataque = 0;         // [DDOS-V2-D293] eventos que la cabeza v2 marca DDoS
        uint64_t ddos_v2_sin_estado = 0;     // [DDOS-ETAPA1-D298] eventos sin victim_state (etapa 1 antigua)
        uint64_t deserialization_errors = 0;
        uint64_t feature_extraction_errors = 0;
        uint64_t inference_errors = 0;
        double avg_processing_time_ms = 0.0;
    };

    ZMQHandler(
        const DetectorConfig& config,
        std::shared_ptr<ONNXModel> level1_model,
        std::shared_ptr<FeatureExtractor> extractor,
        std::shared_ptr<ml_defender::RansomwareDetector> ransomware_detector,
        std::shared_ptr<ml_defender::TrafficDetector> traffic_detector,
        std::shared_ptr<ml_defender::InternalDetector> internal_detector,
        // DEPRECATED DAY 98 — crypto_manager eliminado (ADR-013)
        // std::shared_ptr<crypto::CryptoManager> crypto_manager,
        std::string hmac_key_hex = ""   // clave HMAC del bronce (/secrets/ml-detector, del etcd-server)
    );

    ~ZMQHandler();

    void start();
    void stop();

    Stats get_stats() const;
    void reset_stats();
    // ADR-012 PHASE 2d — plugin_loader setter (Consejo DAY 111)
    void set_plugin_loader(ml_defender::PluginLoader* pl) { plugin_loader_ = pl; }
    // DEBUG DAY271 -- fuerza las cabezas L2 sin veto de level1 (medicion grieta B)
    void set_force_all_heads(bool v) { force_all_heads_ = v; }

    void start_memory_monitoring();
    void stop_memory_monitoring();
    double get_memory_usage_mb();

private:
    void run();
    void process_event(const std::string& message);
    void send_enriched_event(const protobuf::NetworkSecurityEvent& event);

    void log_periodic_stats();
    void periodic_health_check();
    void memory_monitor_loop();
    // [HEADS-SWITCH-D305] estado EFECTIVO de cada cabeza; siempre visible (arranque + informe de estadisticas)
    void log_heads_state(const char* momento) const;

    // Config & Models
    DetectorConfig config_;
    std::shared_ptr<ONNXModel> level1_model_;
    std::shared_ptr<ml_defender::RansomwareDetector> ransomware_detector_;
    std::shared_ptr<ml_defender::TrafficDetector> traffic_detector_;
    std::shared_ptr<ml_defender::InternalDetector> internal_detector_;
    std::shared_ptr<FeatureExtractor> extractor_;

    // ADR-013 PHASE 2 — DAY 98: CryptoTransport via SeedClient
    // DEPRECATED DAY 98 — crypto_manager_ sustituido por seed_client_ + tx_ + rx_
    std::unique_ptr<ml_defender::SeedClient>           seed_client_;
    std::unique_ptr<crypto_transport::CryptoTransport> tx_;
    std::unique_ptr<crypto_transport::CryptoTransport> rx_;

    // ZMQ
    zmq::context_t context_;
    std::unique_ptr<zmq::socket_t> input_socket_;
    std::unique_ptr<zmq::socket_t> output_socket_;

    // Threading
    std::atomic<bool> running_;
    std::unique_ptr<std::thread> worker_thread_;

    // Stats
    mutable std::mutex stats_mutex_;
    // [TIMEBASE-D296] D17: sello de recepcion (CLOCK_MONOTONIC, mismo reloj que bpf_ktime_get_ns del sniffer) tomado
    // en run() justo tras el recv, ANTES de descifrar/descomprimir/parsear. Solo lo usa worker_thread_.
    uint64_t mld_recv_mono_ns_ = 0;
    static uint64_t mld_mono_now_ns() {
        timespec ts{};
        clock_gettime(CLOCK_MONOTONIC, &ts);
        return static_cast<uint64_t>(ts.tv_sec) * 1000000000ULL + static_cast<uint64_t>(ts.tv_nsec);
    }
    Stats stats_;
    std::chrono::steady_clock::time_point last_stats_report_;

    // Logging
    std::shared_ptr<spdlog::logger> logger_;

    // ADR-012 PHASE 2d — plugin_loader (Consejo DAY 111)
    ml_defender::PluginLoader* plugin_loader_ = nullptr;
    // DEBUG DAY271 -- default false: un pipeline-start normal NUNCA abre la compuerta
    bool force_all_heads_ = false;
    std::chrono::system_clock::time_point start_time_;

    // DAY 175: CorrelationWriter (zona bronce, contrato correlation_v1)
    std::shared_ptr<ml_defender::CorrelationWriter> correlation_writer_;
    std::unique_ptr<ml_defender::DdosDatasetWriter> ddos_dataset_writer_;  // [DDOS-DATASET-D287]

    // Memory monitoring thread
    std::thread memory_monitor_thread_;
    std::atomic<bool> memory_monitor_running_{false};
    std::atomic<double> current_memory_mb_{0.0};

    std::string hmac_key_hex_;  // clave HMAC del bronce (correlation_writer_)
};
} // namespace ml_detector