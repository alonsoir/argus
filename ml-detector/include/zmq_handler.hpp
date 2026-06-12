#pragma once
#include "memory_utils.hpp"

#include <zmq.hpp>
#include <memory>
#include <atomic>
#include <thread>
#include <mutex>
#include <chrono>
#include <spdlog/spdlog.h>

#include "feature_extractor.hpp"

#include "ml_defender/ransomware_detector.hpp"
#include "config_loader.hpp"
#include "onnx_model.hpp"
#include "ml_defender/ddos_detector.hpp"
#include "ml_defender/traffic_detector.hpp"
#include "ml_defender/internal_detector.hpp"

#include "network_security.pb.h"

// 🎯 DAY 14: RAG Logger
#include "rag_logger.hpp"

// ADR-013 PHASE 2 — DAY 98: CryptoTransport via SeedClient (sustituye CryptoManager)
// DEPRECATED DAY 98 — #include <crypto_transport/crypto_manager.hpp>
#include <seed_client/seed_client.hpp>
#include <crypto_transport/transport.hpp>
#include <lz4.h>

// Day 63: CSV Event Writer
#include "csv_event_writer.hpp"
#include "correlation_writer.hpp"
#include "plugin_loader/plugin_loader.hpp"  // ADR-012 PHASE 2d

namespace ml_detector {

class ZMQHandler {
public:
    struct Stats {
        uint64_t events_received = 0;
        uint64_t events_processed = 0;
        uint64_t events_sent = 0;
        uint64_t attacks_detected = 0;
        uint64_t deserialization_errors = 0;
        uint64_t feature_extraction_errors = 0;
        uint64_t inference_errors = 0;
        double avg_processing_time_ms = 0.0;
    };

    ZMQHandler(
        const DetectorConfig& config,
        std::shared_ptr<ONNXModel> level1_model,
        std::shared_ptr<FeatureExtractor> extractor,
        std::shared_ptr<ml_defender::DDoSDetector> ddos_detector,
        std::shared_ptr<ml_defender::RansomwareDetector> ransomware_detector,
        std::shared_ptr<ml_defender::TrafficDetector> traffic_detector,
        std::shared_ptr<ml_defender::InternalDetector> internal_detector,
        // DEPRECATED DAY 98 — crypto_manager eliminado (ADR-013)
        // std::shared_ptr<crypto::CryptoManager> crypto_manager,
        std::string hmac_key_hex = ""   // Day 63: CSV integrity key from etcd
    );

    ~ZMQHandler();

    void start();
    void stop();

    Stats get_stats() const;
    void reset_stats();
    // ADR-012 PHASE 2d — plugin_loader setter (Consejo DAY 111)
    void set_plugin_loader(ml_defender::PluginLoader* pl) { plugin_loader_ = pl; }

    void start_memory_monitoring();
    void stop_memory_monitoring();
    double get_memory_usage_mb();

private:
    void run();
    void process_event(const std::string& message);
    void send_enriched_event(const protobuf::NetworkSecurityEvent& event);

    // 🎯 DAY 14: RAG Logger methods
    void log_rag_statistics();
    uint64_t calculate_events_per_minute();
    void log_periodic_stats();
    void periodic_health_check();
    void memory_monitor_loop();

    // Config & Models
    DetectorConfig config_;
    std::shared_ptr<ONNXModel> level1_model_;
    std::shared_ptr<ml_defender::DDoSDetector> ddos_detector_;
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
    Stats stats_;
    std::chrono::steady_clock::time_point last_stats_report_;

    // Logging
    std::shared_ptr<spdlog::logger> logger_;

    // 🎯 DAY 14: RAG Logger
    std::unique_ptr<ml_defender::RAGLogger> rag_logger_;
    uint64_t events_processed_total_{0};
    // ADR-012 PHASE 2d — plugin_loader (Consejo DAY 111)
    ml_defender::PluginLoader* plugin_loader_ = nullptr;
    std::chrono::system_clock::time_point start_time_;

    // Day 66: CsvEventWriter standalone (activo aunque RAG Logger falle)
    std::shared_ptr<ml_defender::CsvEventWriter> csv_writer_;
    // DAY 175: CorrelationWriter (zona bronce, contrato correlation_v1)
    std::shared_ptr<ml_defender::CorrelationWriter> correlation_writer_;

    // Memory monitoring thread
    std::thread memory_monitor_thread_;
    std::atomic<bool> memory_monitor_running_{false};
    std::atomic<double> current_memory_mb_{0.0};

    std::string hmac_key_hex_;  // Day 63: stored for CsvEventWriter init
};
} // namespace ml_detector