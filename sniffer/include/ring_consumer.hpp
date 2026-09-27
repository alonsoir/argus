// sniffer/include/ring_consumer.hpp
#pragma once

#include "protocol_numbers.hpp"  // IANA protocol numbers
#include "main.h"
#include "fast_detector_config.hpp"
#include "network_security.pb.h"
#include "thread_manager.hpp"
#include "fast_detector.hpp"
#include "ransomware_feature_processor.hpp"
#include "ml_defender_features.hpp"
#include "ddos_victim_board.hpp"  // [DDOS-VWIN-D279:RC-INC]
#include "payload_analyzer.hpp"
// ML Defender embedded detectors
#include "ml_defender/ddos_detector.hpp"
#include "ml_defender/ransomware_detector.hpp"
#include "ml_defender/traffic_detector.hpp"
#include "ml_defender/internal_detector.hpp"
// ADR-013 PHASE 2 — DAY 98: CryptoTransport via SeedClient (sustituye CryptoManager)
// DEPRECATED DAY 98 — #include <crypto_transport/crypto_manager.hpp>
#include <seed_client/seed_client.hpp>
#include <crypto_transport/transport.hpp>
#include <bpf/libbpf.h>
#include <zmq.hpp>
#include <memory>
#include <vector>
#include <queue>
#include <thread>
#include <mutex>
#include <condition_variable>
#include <atomic>
#include <array>
#include <functional>
#include "flow/sharded_flow_manager.hpp"
#ifdef PLUGIN_LOADER_ENABLED
#include <plugin_loader/plugin_loader.hpp>
#endif
#ifdef PLUGIN_LOADER_ENABLED
#include <plugin_loader/plugin_loader.hpp>
#endif  // DAY 45

namespace sniffer {

struct RingConsumerStats {
    std::atomic<uint64_t> events_processed{0};
    std::atomic<uint64_t> events_sent{0};
    std::atomic<uint64_t> events_dropped{0};
    std::atomic<uint64_t> protobuf_serialization_failures{0};
    std::atomic<uint64_t> zmq_send_failures{0};
    std::atomic<uint64_t> ring_buffer_polls{0};
    std::atomic<uint64_t> ring_buffer_timeouts{0};
    std::atomic<uint64_t> total_processing_time_us{0};
    std::atomic<double> average_processing_time_us{0.0};
    std::chrono::steady_clock::time_point start_time;
    // NEW: Ransomware detection stats
    std::atomic<uint64_t> ransomware_fast_alerts{0};       // Layer 1 alerts
    std::atomic<uint64_t> ransomware_feature_extractions{0}; // Layer 2 extractions
    std::atomic<uint64_t> ransomware_confirmed_threats{0};  // High-confidence detections
    std::atomic<uint64_t> ransomware_processing_time_us{0}; // Time spent on ransomware

    std::atomic<uint64_t> ddos_attacks_detected{0};
    std::atomic<uint64_t> ransomware_attacks_detected{0};
    std::atomic<uint64_t> suspicious_traffic_detected{0};
    std::atomic<uint64_t> internal_anomalies_detected{0};
    std::atomic<uint64_t> ml_detection_time_us{0};
};

// Snapshot for reading stats (non-atomic copy)
struct RingConsumerStatsSnapshot {
    uint64_t events_processed;
    uint64_t events_sent;
    uint64_t events_dropped;
    uint64_t protobuf_serialization_failures;
    uint64_t zmq_send_failures;
    uint64_t ring_buffer_polls;
    uint64_t ring_buffer_timeouts;
    uint64_t total_processing_time_us;
    double average_processing_time_us;
    std::chrono::steady_clock::time_point start_time;
    // Ransomware stats
    uint64_t ransomware_fast_alerts;
    uint64_t ransomware_feature_extractions;
    uint64_t ransomware_confirmed_threats;
    uint64_t ransomware_processing_time_us;
    // embebbed models
    uint64_t ddos_attacks_detected;
    uint64_t ransomware_attacks_detected;
    uint64_t suspicious_traffic_detected;
    uint64_t internal_anomalies_detected;
    uint64_t ml_detection_time_us;
};

struct EventBatch {
    std::vector<SimpleEvent> events;
    size_t max_size;

    explicit EventBatch(size_t size) : max_size(size) {
        events.reserve(size);
    }

    bool is_ready() const { return events.size() >= max_size; }
};

class RingBufferConsumer {
public:
    using EventCallback = std::function<void(const SimpleEvent&)>;

    // 🎯 DAY 29: Constructor with encryption seed
    explicit RingBufferConsumer(
        const SnifferConfig& config,
        const FastDetectorConfig& fast_detector_config = FastDetectorConfig{},
        const std::string& encryption_seed = ""
    );

    ~RingBufferConsumer();

    bool initialize(int ring_fd, std::shared_ptr<ThreadManager> thread_manager);
    bool start();
    void stop();

    // Statistics
    RingConsumerStatsSnapshot get_stats() const;
    void print_stats() const;
    void reset_stats();

    // Configuration
    void set_event_callback(EventCallback callback);
    void set_stats_interval(int seconds) { stats_interval_seconds_ = seconds; }
#ifdef PLUGIN_LOADER_ENABLED
#endif
#ifdef PLUGIN_LOADER_ENABLED
    void set_plugin_loader(ml_defender::PluginLoader* pl) { plugin_loader_ = pl; }
#endif

    // [DDOS-VWIN-D279:RC-SETTER] tablero de ventanas por victima (agregador en-kernel).
    // Llamar ANTES de start(): el puntero se fija una vez y despues solo se lee.
    void set_victim_board(std::shared_ptr<::sniffer::DdosVictimBoard> board) {
        victim_board_ = std::move(board);
    }

private:
    // CONSTANTS - Processing statistics
    static constexpr double EMA_SMOOTHING_FACTOR = 0.9;  // Exponential Moving Average weight
    static constexpr double EMA_NEW_SAMPLE_WEIGHT = 0.1;  // Weight for new samples

    // CONSTANTS - Ransomware detection
    static constexpr int RANSOMWARE_EXTRACTION_INTERVAL_SEC = 30;  // Deep analysis interval

    // Core functionality
    bool initialize_zmq();
    bool initialize_buffers();
    bool validate_configuration() const;

    // Thread loops
    void ring_consumer_loop(int consumer_id);
    void feature_processor_loop();
    void zmq_sender_loop();
    void stats_display_loop();  // NEW: Thread for periodic stats

    // Event processing
    static int handle_event(void* ctx, void* data, size_t data_sz);
    void process_raw_event(const SimpleEvent& event, int consumer_id);
    void process_event_features(const SimpleEvent& event);

    // Batching
    void add_to_batch(const SimpleEvent& event);
    void flush_current_batch();
    void send_event_batch(const std::vector<SimpleEvent>& events);

    // Protobuf
    void populate_protobuf_event(const SimpleEvent& event,
                                protobuf::NetworkSecurityEvent& proto_event,
                                int buffer_index) const;
    std::string protocol_to_string(uint8_t protocol) const;

    // ZMQ
    bool send_protobuf_message(const std::vector<uint8_t>& data);

    // Configuration helpers
    size_t get_optimal_batch_size() const;
    int get_optimal_consumer_count() const;
    std::chrono::milliseconds get_processing_timeout() const;

    // Error handling
    void handle_ring_buffer_error(int error_code);
    void handle_zmq_error(const zmq::error_t& error);
    void handle_protobuf_error(const std::exception& error);
    void update_processing_time(std::chrono::microseconds duration);

    // Shutdown
    void shutdown_consumers();
    void shutdown_zmq();
    void cleanup_resources();

    // Configuration
    SnifferConfig config_;
    FastDetectorConfig fast_detector_config_;
    std::shared_ptr<::sniffer::DdosVictimBoard> victim_board_;  // [DDOS-VWIN-D279:RC-MEMBER]
#ifdef PLUGIN_LOADER_ENABLED
#endif
#ifdef PLUGIN_LOADER_ENABLED
    ml_defender::PluginLoader* plugin_loader_ = nullptr;  // PHASE 2c — set via set_plugin_loader()
#endif  // Day 12 - Externalized thresholds
    int stats_interval_seconds_{30};  // Default 30 seconds todo esto hay que cambiarlo, quitar números mágicos

    // Ring buffer
    ring_buffer* ring_buf_;
    int ring_fd_;

    // Threading
    std::shared_ptr<ThreadManager> thread_manager_;
    std::vector<std::thread> consumer_threads_;
    std::atomic<int> active_consumers_{0};
    std::atomic<bool> running_{false};
    std::atomic<bool> should_stop_{false};
    std::atomic<bool> initialized_{false};

    // Layer 3 - ML Defender Embedded Detectors (thread-local, zero-lock)
    thread_local static ml_defender::DDoSDetector ddos_detector_;
    thread_local static ml_defender::RansomwareDetector ransomware_detector_;
    thread_local static ml_defender::TrafficDetector traffic_detector_;
    thread_local static ml_defender::InternalDetector internal_detector_;

    // Queues
    std::queue<SimpleEvent> processing_queue_;
    std::mutex processing_queue_mutex_;
    std::condition_variable processing_queue_cv_;

    std::queue<std::vector<uint8_t>> send_queue_;
    std::mutex send_queue_mutex_;
    std::condition_variable send_queue_cv_;

    // Batching
    std::unique_ptr<EventBatch> current_batch_;
    std::mutex batch_mutex_;

    // ZeroMQ
    std::unique_ptr<zmq::context_t> zmq_context_;
    std::vector<std::unique_ptr<zmq::socket_t>> zmq_sockets_;
    std::vector<std::unique_ptr<std::mutex>> socket_mutexes_;
    std::atomic<size_t> socket_round_robin_{0};

    // Pre-allocated buffers for IP conversion
    mutable std::vector<std::array<char, 16>> ip_buffers_src_;
    mutable std::vector<std::array<char, 16>> ip_buffers_dst_;

    // Statistics
    RingConsumerStats stats_;
    EventCallback external_callback_;

    // ADR-013 PHASE 2 — DAY 98: CryptoTransport via SeedClient
    // DEPRECATED DAY 98 — crypto_manager_ + encryption_seed_ sustituidos
    std::unique_ptr<ml_defender::SeedClient>           seed_client_;
    std::unique_ptr<crypto_transport::CryptoTransport> tx_;

    // Layer 1 - Fast Detection (thread-local)
    thread_local static FastDetector fast_detector_;
    thread_local static PayloadAnalyzer payload_analyzer_;
    thread_local static MLDefenderExtractor ml_extractor_;  // Feature extraction

    // Layer 2 - Deep Analysis (singleton)
    std::unique_ptr<RansomwareFeatureProcessor> ransomware_processor_;
    std::thread ransomware_processor_thread_;
    std::atomic<bool> ransomware_enabled_{false};

    // Ransomware-specific methods
    void ransomware_processor_loop();
    void send_fast_alert(const SimpleEvent& event);
    // [DDOS-VWIN-D279:RC-STAMP-DECL]
    void stamp_victim_window(protobuf::NetworkSecurityEvent& ev, const SimpleEvent& e) const;
    void send_ransomware_features(const protobuf::RansomwareFeatures& features);
    bool initialize_ransomware_detection();
    void shutdown_ransomware_detection();

    // ML Defender feature extraction
    ml_defender::DDoSDetector::Features extract_ddos_features(const protobuf::NetworkSecurityEvent& proto_event) const;
    ml_defender::RansomwareDetector::Features extract_ransomware_features(const protobuf::NetworkSecurityEvent& proto_event) const;
    ml_defender::TrafficDetector::Features extract_traffic_features(const protobuf::NetworkSecurityEvent& proto_event) const;
    ml_defender::InternalDetector::Features extract_internal_features(const protobuf::NetworkSecurityEvent& proto_event) const;

    // ML Defender inference
    void run_ml_detection(protobuf::NetworkSecurityEvent& proto_event);
};

} // namespace sniffer