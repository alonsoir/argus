// sniffer/src/userspace/ring_consumer.cpp
#include "compression_handler.hpp"
#include <crypto_transport/contexts.hpp>
#include "ring_consumer.hpp"
#include "fast_detector.hpp"
#include <reason_codes.hpp>
// ADR-013 PHASE 2 — DAY 98
// DEPRECATED DAY 98 — #include <crypto_transport/utils.hpp>
#include <lz4.h>
#include <cstring>
#include "feature_logger.hpp"
#include "flow/sharded_flow_manager.hpp"  // ✅ DAY 45: Migrated
#include "ml_defender_features.hpp"
#include <iostream>
#include <cstring>
#include <arpa/inet.h>
#include <google/protobuf/timestamp.pb.h>
#include <chrono>
#include <iomanip>

extern FeatureLogger::VerbosityLevel g_verbosity;

// Thread-local FastDetector instance (Layer 1 detection)

// DAY 77: NaN sentinel — fuerza serializacion sin contaminar distribuciones reales
// NaN es non-default en proto3 -> submensaje presente en wire
// NaN != ninguna metrica real -> modelo ML no lo interpreta como senal valida
// Reemplaza 0.5f (DAY 76) que podia coincidir con trafico real (tcp_udp_ratio~0.5)
static void init_embedded_sentinels(protobuf::NetworkFeatures* net) {
    // DAY 78: sentinel en ml_defender_features.hpp
    auto* ddos = net->mutable_ddos_embedded();
    ddos->set_syn_ack_ratio(MISSING_FEATURE_SENTINEL);
    ddos->set_packet_symmetry(MISSING_FEATURE_SENTINEL);
    ddos->set_source_ip_dispersion(MISSING_FEATURE_SENTINEL);
    ddos->set_protocol_anomaly_score(MISSING_FEATURE_SENTINEL);
    ddos->set_packet_size_entropy(MISSING_FEATURE_SENTINEL);
    ddos->set_traffic_amplification_factor(MISSING_FEATURE_SENTINEL);
    ddos->set_flow_completion_rate(MISSING_FEATURE_SENTINEL);
    ddos->set_geographical_concentration(MISSING_FEATURE_SENTINEL);
    ddos->set_traffic_escalation_rate(MISSING_FEATURE_SENTINEL);
    ddos->set_resource_saturation_score(MISSING_FEATURE_SENTINEL);
    auto* ransom = net->mutable_ransomware_embedded();
    ransom->set_io_intensity(MISSING_FEATURE_SENTINEL);
    ransom->set_entropy(MISSING_FEATURE_SENTINEL);
    ransom->set_resource_usage(MISSING_FEATURE_SENTINEL);
    ransom->set_network_activity(MISSING_FEATURE_SENTINEL);
    ransom->set_file_operations(MISSING_FEATURE_SENTINEL);
    ransom->set_process_anomaly(MISSING_FEATURE_SENTINEL);
    ransom->set_temporal_pattern(MISSING_FEATURE_SENTINEL);
    ransom->set_access_frequency(MISSING_FEATURE_SENTINEL);
    ransom->set_data_volume(MISSING_FEATURE_SENTINEL);
    ransom->set_behavior_consistency(MISSING_FEATURE_SENTINEL);
    auto* traffic = net->mutable_traffic_classification();
    traffic->set_packet_rate(MISSING_FEATURE_SENTINEL);
    traffic->set_connection_rate(MISSING_FEATURE_SENTINEL);
    traffic->set_tcp_udp_ratio(MISSING_FEATURE_SENTINEL);
    traffic->set_avg_packet_size(MISSING_FEATURE_SENTINEL);
    traffic->set_port_entropy(MISSING_FEATURE_SENTINEL);
    traffic->set_flow_duration_std(MISSING_FEATURE_SENTINEL);
    traffic->set_src_ip_entropy(MISSING_FEATURE_SENTINEL);
    traffic->set_dst_ip_concentration(MISSING_FEATURE_SENTINEL);
    traffic->set_protocol_variety(MISSING_FEATURE_SENTINEL);
    traffic->set_temporal_consistency(MISSING_FEATURE_SENTINEL);
    auto* internal = net->mutable_internal_anomaly();
    internal->set_internal_connection_rate(MISSING_FEATURE_SENTINEL);
    internal->set_service_port_consistency(MISSING_FEATURE_SENTINEL);
    internal->set_protocol_regularity(MISSING_FEATURE_SENTINEL);
    internal->set_packet_size_consistency(MISSING_FEATURE_SENTINEL);
    internal->set_connection_duration_std(MISSING_FEATURE_SENTINEL);
    internal->set_lateral_movement_score(MISSING_FEATURE_SENTINEL);
    internal->set_service_discovery_patterns(MISSING_FEATURE_SENTINEL);
    internal->set_data_exfiltration_indicators(MISSING_FEATURE_SENTINEL);
    internal->set_temporal_anomaly_score(MISSING_FEATURE_SENTINEL);
    internal->set_access_pattern_entropy(MISSING_FEATURE_SENTINEL);
}

namespace sniffer {
    // ============================================================================
    // Thread-Local Detectors and Extractors (Phase 1, Day 3)
    // ============================================================================
    thread_local FastDetector RingBufferConsumer::fast_detector_;
    thread_local PayloadAnalyzer RingBufferConsumer::payload_analyzer_;

    // ML Defender: Flow tracking (thread-local, per-consumer)

	// ML Defender: Feature extractor (thread-local, stateless)
	thread_local MLDefenderExtractor RingBufferConsumer::ml_extractor_;
	// ML Defender embedded detectors (thread-local, zero-lock architecture)
	thread_local ml_defender::DDoSDetector RingBufferConsumer::ddos_detector_;
	thread_local ml_defender::RansomwareDetector RingBufferConsumer::ransomware_detector_;
	thread_local ml_defender::TrafficDetector RingBufferConsumer::traffic_detector_;
	thread_local ml_defender::InternalDetector RingBufferConsumer::internal_detector_;

    // ============================================================================
    // CONSTRUCTOR
    // ============================================================================

    RingBufferConsumer::RingBufferConsumer(
    const SnifferConfig& config,
    const FastDetectorConfig& fast_detector_config,
    const std::string& /*encryption_seed*/)
    : config_(config)
    , fast_detector_config_(fast_detector_config)
    // DEPRECATED DAY 98 — encryption_seed ignorado, SeedClient lee desde /etc/ml-defender/sniffer/sniffer.json
    // , encryption_seed_(encryption_seed)
    , ring_buf_(nullptr)
        , ring_fd_(-1)
        , active_consumers_(0)
        , running_(false)
        , should_stop_(false)
        , initialized_(false)
        , socket_round_robin_(0)
        , ransomware_enabled_(false) {

        std::cout << "[INFO] RingBufferConsumer constructor called" << std::endl;

        // ⭐ NUEVO - Log Fast Detector config (Day 12)
        if (fast_detector_config_.enabled) {
            std::cout << "[INFO] Fast Detector enabled:" << std::endl;
            std::cout << "       High threat score: " << fast_detector_config_.ransomware.scores.high_threat << std::endl;
            std::cout << "       Suspicious score: " << fast_detector_config_.ransomware.scores.suspicious << std::endl;
            std::cout << "       Alert score: " << fast_detector_config_.ransomware.scores.alert << std::endl;
            std::cout << "       ExtIPs threshold: " << fast_detector_config_.ransomware.activation_thresholds.external_ips_30s << std::endl;
            std::cout << "       SMB diversity threshold: " << fast_detector_config_.ransomware.activation_thresholds.smb_diversity << std::endl;
        } else {
            std::cout << "[INFO] Fast Detector disabled" << std::endl;
        }

        // ✅ DAY 45: Initialize ShardedFlowManager (thread-safe singleton)
        auto& flow_manager = sniffer::flow::ShardedFlowManager::instance();
        static std::once_flag init_flag;
        std::call_once(init_flag, [&]() {
            flow_manager.initialize(sniffer::flow::ShardedFlowManager::Config{
                .shard_count = 16,
                .max_flows_per_shard = 10000,
                .flow_timeout_ns = 120000000000ULL  // 120 seconds in ns
            });
            std::cout << "[INFO] ✅ ShardedFlowManager initialized (16 shards, 10K flows/shard)" << std::endl;
        });
    }

RingBufferConsumer::~RingBufferConsumer() {
    if (running_) {
        stop();
    }
    cleanup_resources();
}

bool RingBufferConsumer::initialize(int ring_fd, std::shared_ptr<ThreadManager> thread_manager) {
    if (initialized_) {
        std::cout << "[WARNING] RingBufferConsumer already initialized" << std::endl;
        return true;
    }

    if (ring_fd < 0) {
        std::cerr << "[ERROR] Invalid ring buffer file descriptor: " << ring_fd << std::endl;
        return false;
    }

    if (!thread_manager) {
        std::cerr << "[ERROR] ThreadManager is required for enhanced RingBufferConsumer" << std::endl;
        return false;
    }

    if (!validate_configuration()) {
        std::cerr << "[ERROR] Invalid configuration" << std::endl;
        return false;
    }

    ring_fd_ = ring_fd;
    thread_manager_ = thread_manager;

    // Initialize ring buffer
    ring_buf_ = ring_buffer__new(ring_fd_, handle_event, this, nullptr);
    if (!ring_buf_) {
        std::cerr << "[ERROR] Failed to create ring buffer consumer" << std::endl;
        return false;
    }

    // Initialize ZeroMQ
    if (!initialize_zmq()) {
        std::cerr << "[ERROR] Failed to initialize ZeroMQ" << std::endl;
        return false;
    }

    // Initialize buffers
    if (!initialize_buffers()) {
        std::cerr << "[ERROR] Failed to initialize buffers" << std::endl;
        return false;
    }

    // Initialize ransomware detection
    if (!initialize_ransomware_detection()) {
        std::cerr << "[WARNING] Ransomware detection disabled" << std::endl;
    }else{
        std::cout << "[INFO] Ransomware detection initialized successfully" << std::endl;
    }

    // Initialize batching
    current_batch_ = std::make_unique<EventBatch>(get_optimal_batch_size());

    std::cout << "[ML Defender] Thresholds (JSON): "
              << "DDoS=" << config_.ml_defender.thresholds.ddos
              << " Ransomware=" << config_.ml_defender.thresholds.ransomware
              << " Traffic=" << config_.ml_defender.thresholds.traffic
              << " Internal=" << config_.ml_defender.thresholds.internal
              << std::endl;
    initialized_ = true;
    std::cout << "[INFO] Enhanced RingBufferConsumer initialized successfully" << std::endl;
    std::cout << "  - Ring buffer FD: " << ring_fd_ << std::endl;
    std::cout << "  - ZMQ sockets: " << zmq_sockets_.size() << std::endl;
    std::cout << "  - Optimal batch size: " << get_optimal_batch_size() << std::endl;

    return true;
}

bool RingBufferConsumer::start() {
    if (!initialized_) {
        std::cerr << "[ERROR] Cannot start - not initialized. Call initialize() first" << std::endl;
        return false;
    }

    if (running_) {
        std::cout << "[INFO] Enhanced RingBufferConsumer already running" << std::endl;
        return true;
    }

    should_stop_ = false;
    running_ = true;
    active_consumers_ = 0;

    // Start ring buffer consumer threads
    int consumer_count = config_.threading.ring_consumer_threads;
    consumer_threads_.reserve(consumer_count +
                             config_.threading.feature_processor_threads +
                             config_.threading.zmq_sender_threads +
                             1);  // +1 for stats thread

    for (int i = 0; i < consumer_count; ++i) {
        consumer_threads_.emplace_back(&RingBufferConsumer::ring_consumer_loop, this, i);
        active_consumers_++;
    }

    // Start feature processor threads
    for (int i = 0; i < config_.threading.feature_processor_threads; ++i) {
        consumer_threads_.emplace_back(&RingBufferConsumer::feature_processor_loop, this);
    }

    // Start ZMQ sender threads
    for (int i = 0; i < config_.threading.zmq_sender_threads; ++i) {
        consumer_threads_.emplace_back(&RingBufferConsumer::zmq_sender_loop, this);
    }

    // Start ransomware processor thread
    if (ransomware_enabled_) {
        ransomware_processor_->start();
        consumer_threads_.emplace_back(&RingBufferConsumer::ransomware_processor_loop, this);
        std::cout << "[INFO] + 1 ransomware detection thread (30s aggregation)" << std::endl;
    }

    // Start statistics display thread
    consumer_threads_.emplace_back(&RingBufferConsumer::stats_display_loop, this);

    stats_.start_time = std::chrono::steady_clock::now();

    std::cout << "[INFO] Enhanced RingBufferConsumer started with " << consumer_count
              << " ring consumer threads" << std::endl;
    std::cout << "[INFO] + " << config_.threading.feature_processor_threads
              << " feature processor threads" << std::endl;
    std::cout << "[INFO] + " << config_.threading.zmq_sender_threads
              << " ZMQ sender threads" << std::endl;
    std::cout << "[INFO] + 1 statistics display thread" << std::endl;
    std::cout << "[INFO] Multi-threaded protobuf pipeline active" << std::endl;

    return true;
}

    void RingBufferConsumer::stop() {
    if (!running_) {
        return;
    }

    std::cout << "[INFO] Stopping Enhanced RingBufferConsumer..." << std::endl;
    should_stop_ = true;

    // ORDEN CORRECTO DE PARADA:

    // 1️⃣ Parar ransomware detection PRIMERO (más costoso, tiene timer threads)
    shutdown_ransomware_detection();

    // 2️⃣ Notificar a todos los threads que deben parar
    processing_queue_cv_.notify_all();
    send_queue_cv_.notify_all();

    // 3️⃣ Flush batch pendiente (asegurar que no perdemos datos)
    flush_current_batch();

    // 4️⃣ Parar consumer threads (ya no recibirán eventos)
    shutdown_consumers();

    // 5️⃣ Parar ZMQ AL FINAL (flush final de colas)
    shutdown_zmq();

    running_ = false;
    active_consumers_ = 0;

    // 6️⃣ Stats finales (incluye ransomware)
    print_stats();

    std::cout << "[INFO] Enhanced RingBufferConsumer stopped" << std::endl;
}

bool RingBufferConsumer::initialize_zmq() {
    try {
        // Create ZeroMQ context with optimal IO threads
        int io_threads = config_.zmq.io_thread_pools;
        zmq_context_ = std::make_unique<zmq::context_t>(io_threads);

        // Create socket pool
        int socket_count = config_.zmq.socket_pools.push_sockets;
        zmq_sockets_.reserve(socket_count);

        std::string endpoint = "tcp://" + config_.network.output_socket.address + ":" +
                              std::to_string(config_.network.output_socket.port);

        for (int i = 0; i < socket_count; ++i) {
            auto socket = std::make_unique<zmq::socket_t>(*zmq_context_, ZMQ_PUSH);

            // Configure socket with enhanced settings
            socket->set(zmq::sockopt::sndhwm, static_cast<int>(config_.zmq.connection_settings.sndhwm));
            socket->set(zmq::sockopt::linger, static_cast<int>(config_.zmq.connection_settings.linger_ms));
            socket->set(zmq::sockopt::sndbuf, static_cast<int>(config_.zmq.connection_settings.sndbuf));
            socket->set(zmq::sockopt::tcp_keepalive, static_cast<int>(config_.zmq.connection_settings.tcp_keepalive));

            // Bind socket
            if (config_.network.output_socket.mode == "bind") {
                socket->bind(endpoint);
            } else {
                socket->connect(endpoint);
            }

            zmq_sockets_.push_back(std::move(socket));
            socket_mutexes_.push_back(std::make_unique<std::mutex>());
        }

        std::cout << "[INFO] ZeroMQ initialized with " << socket_count
                  << " sockets to " << endpoint << std::endl;

        // ADR-013 PHASE 2 — DAY 98: CryptoTransport via SeedClient
        try {
            seed_client_ = std::make_unique<ml_defender::SeedClient>(
                "/etc/ml-defender/sniffer/sniffer.json");
            seed_client_->load();
            tx_ = std::make_unique<crypto_transport::CryptoTransport>(
                *seed_client_, ml_defender::crypto::CTX_SNIFFER_TO_ML);
            std::cout << "[INFO] ✅ CryptoTransport inicializado (HKDF-SHA256 + ChaCha20-Poly1305)" << std::endl;
        } catch (const std::exception& e) {
            std::cerr << "[ERROR] CryptoTransport init failed: " << e.what() << std::endl;
            return false;
        }

        return true;

    } catch (const zmq::error_t& e) {
        std::cerr << "[ERROR] ZeroMQ initialization failed: " << e.what() << std::endl;
        return false;
    }
}

bool RingBufferConsumer::initialize_buffers() {
    int thread_count = config_.threading.ring_consumer_threads;

    // Pre-allocate IP buffers for each consumer thread
    ip_buffers_src_.resize(thread_count);
    ip_buffers_dst_.resize(thread_count);

    std::cout << "[INFO] Initialized " << thread_count << " buffer sets for consumer threads" << std::endl;
    return true;
}

bool RingBufferConsumer::validate_configuration() const {
    if (config_.threading.ring_consumer_threads <= 0) {
        std::cerr << "[ERROR] Ring consumer threads must be > 0" << std::endl;
        return false;
    }

    if (config_.buffers.batch_processing_size == 0) {
        std::cerr << "[ERROR] Batch processing size must be > 0" << std::endl;
        return false;
    }

    if (config_.zmq.socket_pools.push_sockets <= 0) {
        std::cerr << "[ERROR] ZMQ socket count must be > 0" << std::endl;
        return false;
    }

    return true;
}

void RingBufferConsumer::ring_consumer_loop(int consumer_id) {
    std::cout << "[INFO] Ring consumer " << consumer_id << " started" << std::endl;

    while (!should_stop_) {
        // Poll ring buffer with configurable timeout
        auto timeout_ms = std::chrono::duration_cast<std::chrono::milliseconds>(
            get_processing_timeout()).count();

        int err = ring_buffer__poll(ring_buf_, static_cast<int>(timeout_ms));
        stats_.ring_buffer_polls++;

        if (err < 0) {
            if (err != -EINTR) {
                handle_ring_buffer_error(err);
                break;
            }
        } else if (err == 0) {
            stats_.ring_buffer_timeouts++;
        }
    }

    active_consumers_--;
    std::cout << "[INFO] Ring consumer " << consumer_id << " stopped" << std::endl;
}

void RingBufferConsumer::feature_processor_loop() {
    std::cout << "[INFO] Feature processor thread started" << std::endl;
    while (!should_stop_) {
        SimpleEvent event;

        {
            std::unique_lock<std::mutex> lock(processing_queue_mutex_);
            processing_queue_cv_.wait_for(lock, get_processing_timeout(), [this] {
                return !processing_queue_.empty() || should_stop_;
            });

            if (processing_queue_.empty()) {
                continue;
            }

            event = processing_queue_.front();
            processing_queue_.pop();
        }

        process_event_features(event);
    }
    std::cout << "[INFO] Feature processor thread stopped" << std::endl;
}

void RingBufferConsumer::zmq_sender_loop() {
    std::cout << "[INFO] ZMQ sender thread started" << std::endl;
    while (!should_stop_) {
        std::vector<uint8_t> data;

        {
            std::unique_lock<std::mutex> lock(send_queue_mutex_);
            send_queue_cv_.wait_for(lock, get_processing_timeout(), [this] {
                return !send_queue_.empty() || should_stop_;
            });

            if (send_queue_.empty()) {
                continue;
            }

            data = std::move(send_queue_.front());
            send_queue_.pop();
        }

        send_protobuf_message(data);
    }
    std::cout << "[INFO] ZMQ sender thread stopped" << std::endl;
}

void RingBufferConsumer::stats_display_loop() {
    std::cout << "[INFO] Statistics display thread started (interval: "
              << stats_interval_seconds_ << "s)" << std::endl;

    while (!should_stop_) {
        std::this_thread::sleep_for(std::chrono::seconds(stats_interval_seconds_));

        if (should_stop_) break;

        // Calculate runtime and rates
        auto now = std::chrono::steady_clock::now();
        auto runtime = std::chrono::duration_cast<std::chrono::seconds>(
            now - stats_.start_time).count();

        std::cout << "\n=== ESTADÍSTICAS ===\n";
        std::cout << "Paquetes procesados: " << stats_.events_processed << "\n";
        std::cout << "Paquetes enviados: " << stats_.events_sent << "\n";
        std::cout << "Tiempo activo: " << runtime << " segundos\n";

        if (runtime > 0) {
            double rate = static_cast<double>(stats_.events_processed.load()) / runtime;
            std::cout << "Tasa: " << std::fixed << std::setprecision(2) << rate << " eventos/seg\n";
        }

        std::cout << "===================\n";
    }

    std::cout << "[INFO] Statistics display thread stopped" << std::endl;
}

int RingBufferConsumer::handle_event(void* ctx, void* data, size_t data_sz) {
    RingBufferConsumer* consumer = static_cast<RingBufferConsumer*>(ctx);

    if (data_sz != sizeof(SimpleEvent)) {
        std::cerr << "[ERROR] SIZE MISMATCH! Received: " << data_sz
                  << " bytes, Expected: " << sizeof(SimpleEvent)
                  << " bytes - DROPPING EVENT" << std::endl;
        consumer->stats_.events_dropped++;
        return 0;
    }

    const SimpleEvent* event = static_cast<const SimpleEvent*>(data);
    consumer->stats_.events_processed++;

    // Process the event in the current consumer thread context
    consumer->process_raw_event(*event, consumer->active_consumers_.load());

    return 0;
}

void RingBufferConsumer::process_raw_event(const SimpleEvent& event, [[maybe_unused]] int consumer_id) {
    auto start_time = std::chrono::steady_clock::now();

    // Fast Detection (thread-local, O(1))
    fast_detector_.ingest(event);
    if (fast_detector_.is_suspicious()) {
        send_fast_alert(event);
    }

    // ===== ML DEFENDER: Flow Tracking (Phase 1, Day 3) =====
    // Track flow state for feature extraction
    // NOTE: Each thread maintains its own flow table (thread_local)
    // ✅ DAY 45: Migración a ShardedFlowManager
    FlowKey flow_key{
        .src_ip = event.src_ip,
        .dst_ip = event.dst_ip,
        .src_port = event.src_port,
        .dst_port = event.dst_port,
        .protocol = event.protocol
    };
    auto& flow_manager = sniffer::flow::ShardedFlowManager::instance();
    flow_manager.add_packet(flow_key, event);

    // ===== Layer 1.5: Payload Analysis (thread-local, ~1-150 μs) =====
    // Only analyze if payload is present
    if (event.payload_len > 0) {
        auto payload_features = payload_analyzer_.analyze(event.payload, event.payload_len);

        // Check for high-risk indicators
        if (payload_features.high_entropy ||
            payload_features.is_pe_executable ||
            payload_features.suspicious_strings > 0) {

            // TODO: Store payload features for protobuf
            // Could add to thread_local cache or pass to populate_protobuf_event

            // Optional: Log suspicious payloads
            if (g_verbosity >= FeatureLogger::VerbosityLevel::BASIC) {
                std::cout << "[Payload] Suspicious: entropy=" << payload_features.entropy
                          << " PE=" << payload_features.is_pe_executable
                          << " patterns=" << payload_features.suspicious_strings << std::endl;
            }
        }
    }

#ifdef PLUGIN_LOADER_ENABLED
    // PHASE 2c: plugin_process_message con payload real (ADR-023)
    // mode=PLUGIN_MODE_NORMAL, D8-v2 CRC32 activo, result_code!=0 → paquete descartado
    if (plugin_loader_ && event.payload_len > 0) {
        MessageContext ctx_msg{};
        ctx_msg.payload     = event.payload;
        ctx_msg.payload_len = event.payload_len;
        ctx_msg.mode        = PLUGIN_MODE_NORMAL;
        ctx_msg.src_ip      = event.src_ip;
        ctx_msg.dst_ip      = event.dst_ip;
        ctx_msg.src_port    = event.src_port;
        ctx_msg.dst_port    = event.dst_port;
        ctx_msg.protocol    = event.protocol;
        ctx_msg.direction   = 0;  // RX — capturado por XDP
        ctx_msg.nonce       = nullptr;  // sniffer: pre-encrypt, no nonce aún
        ctx_msg.tag         = nullptr;
        ctx_msg.result_code = 0;
        plugin_loader_->invoke_all(ctx_msg);
        if (ctx_msg.result_code != 0) {
            // Plugin señaló anomalía — descartar paquete
            stats_.events_dropped++;
            return;
        }
    }
#endif
#ifdef PLUGIN_LOADER_ENABLED
    // PHASE 2c: plugin_process_message con payload real (ADR-023)
    // mode=PLUGIN_MODE_NORMAL, D8-v2 CRC32 activo, result_code!=0 → paquete descartado
    if (plugin_loader_ && event.payload_len > 0) {
        MessageContext ctx_msg{};
        ctx_msg.payload     = event.payload;
        ctx_msg.payload_len = event.payload_len;
        ctx_msg.mode        = PLUGIN_MODE_NORMAL;
        ctx_msg.src_ip      = event.src_ip;
        ctx_msg.dst_ip      = event.dst_ip;
        ctx_msg.src_port    = event.src_port;
        ctx_msg.dst_port    = event.dst_port;
        ctx_msg.protocol    = event.protocol;
        ctx_msg.direction   = 0;  // RX — capturado por XDP
        ctx_msg.nonce       = nullptr;  // sniffer: pre-encrypt, no nonce aún
        ctx_msg.tag         = nullptr;
        ctx_msg.result_code = 0;
        plugin_loader_->invoke_all(ctx_msg);
        if (ctx_msg.result_code != 0) {
            // Plugin señaló anomalía — descartar paquete
            stats_.events_dropped++;
            return;
        }
    }
#endif
    // Deep Analysis (thread-safe)
    if (ransomware_enabled_ && ransomware_processor_) {
        ransomware_processor_->process_packet(event);
    }

    // Call external callback if set
    if (external_callback_) {
        try {
            external_callback_(event);
        } catch (const std::exception& e) {
            std::cerr << "[WARNING] External callback failed: " << e.what() << std::endl;
        }
    }

    // Add to batch for efficient processing
    add_to_batch(event);

    // Update processing time statistics
    auto end_time = std::chrono::steady_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::microseconds>(end_time - start_time);
    update_processing_time(duration);
}

void RingBufferConsumer::process_event_features(const SimpleEvent& event) {
    try {
        // Create protobuf message
        protobuf::NetworkSecurityEvent proto_event;
        populate_protobuf_event(event, proto_event, 0);

        // Log features if verbosity is enabled
        if (g_verbosity != FeatureLogger::VerbosityLevel::NONE) {
            FeatureLogger::log_packet_features(proto_event, g_verbosity);
        }

        // Serialize to binary
        std::vector<uint8_t> serialized_data;
        std::string serialized_string;

        if (!proto_event.SerializeToString(&serialized_string)) {
            std::cerr << "[ERROR] Protobuf serialization FAILED!" << std::endl;
            stats_.protobuf_serialization_failures++;
            return;
        }

        // Convert to vector for queue
        serialized_data.assign(serialized_string.begin(), serialized_string.end());

        // Add to send queue
        {
            std::lock_guard<std::mutex> lock(send_queue_mutex_);
            send_queue_.push(std::move(serialized_data));
        }
        send_queue_cv_.notify_one();

    } catch (const std::exception& e) {
        handle_protobuf_error(e);
    }
}

void RingBufferConsumer::send_event_batch(const std::vector<SimpleEvent>& events) {
    for (const auto& event : events) {
        // Submit to feature processing queue
        {
            std::lock_guard<std::mutex> lock(processing_queue_mutex_);
            processing_queue_.push(event);
        }
        processing_queue_cv_.notify_one();
    }

}

bool RingBufferConsumer::send_protobuf_message(const std::vector<uint8_t>& serialized_data) {
    try {
        // ====================================================================
        // 🎯 DAY 29: COMPRESS + ENCRYPT using crypto-transport
        // Pattern: serialize → compress → encrypt → zmq_send
        // ====================================================================

        if (!tx_) {
            std::cerr << "[ERROR] CryptoTransport no inicializado!" << std::endl;
            stats_.zmq_send_failures++;
            return false;
        }

        // Step 1: Comprimir con LZ4
        std::vector<uint8_t> to_encrypt;
        {
            int orig_size = static_cast<int>(serialized_data.size());
            int max_compressed = LZ4_compressBound(orig_size);
            std::vector<uint8_t> compressed(sizeof(uint32_t) + max_compressed);
            uint32_t orig_le = static_cast<uint32_t>(orig_size);
            std::memcpy(compressed.data(), &orig_le, sizeof(orig_le));
            int compressed_size = LZ4_compress_default(
                reinterpret_cast<const char*>(serialized_data.data()),
                reinterpret_cast<char*>(compressed.data() + sizeof(uint32_t)),
                orig_size, max_compressed
            );
            if (compressed_size > 0) {
                compressed.resize(sizeof(uint32_t) + compressed_size);
                to_encrypt = std::move(compressed);
                std::cout << "[CRYPTO] 📦 Compressed: " << orig_size
                          << " → " << to_encrypt.size() << " bytes" << std::endl;
            } else {
                to_encrypt = serialized_data;
                std::cerr << "[CRYPTO] ⚠️  LZ4 falló — enviando sin comprimir" << std::endl;
            }
        }

        // Step 2: Cifrar con CryptoTransport
        auto encrypted = tx_->encrypt(to_encrypt);
        std::cout << "[CRYPTO] 🔒 Encrypted: " << to_encrypt.size()
                  << " → " << encrypted.size() << " bytes" << std::endl;

        // Step 3: Send encrypted
        zmq::message_t message(encrypted.size());
        memcpy(message.data(), encrypted.data(), encrypted.size());

        // Get next socket using round-robin with proper locking
        size_t idx = socket_round_robin_.fetch_add(1, std::memory_order_relaxed) % zmq_sockets_.size();
        std::lock_guard<std::mutex> lock(*socket_mutexes_[idx]);
        zmq::socket_t* socket = zmq_sockets_[idx].get();

        auto result = socket->send(message, zmq::send_flags::dontwait);

        if (result.has_value()) {
            stats_.events_sent++;
            return true;
        } else {
            std::cerr << "[ERROR] ZMQ send falló!" << std::endl;
            stats_.zmq_send_failures++;
            return false;
        }

    } catch (const zmq::error_t& e) {
        std::cerr << "[ERROR] ZMQ exception: " << e.what() << std::endl;
        handle_zmq_error(e);
        return false;
    } catch (const std::exception& e) {
        std::cerr << "[ERROR] Crypto exception: " << e.what() << std::endl;
        stats_.zmq_send_failures++;
        return false;
    }
}

void RingBufferConsumer::add_to_batch(const SimpleEvent& event) {
    std::lock_guard<std::mutex> lock(batch_mutex_);

    if (!current_batch_) {
        current_batch_ = std::make_unique<EventBatch>(get_optimal_batch_size());
    }

    current_batch_->events.push_back(event);

    if (current_batch_->is_ready()) {
        send_event_batch(current_batch_->events);
        current_batch_ = std::make_unique<EventBatch>(get_optimal_batch_size());
    }
}

void RingBufferConsumer::flush_current_batch() {
    std::lock_guard<std::mutex> lock(batch_mutex_);

    if (current_batch_ && !current_batch_->events.empty()) {
        std::cout << "[INFO] flush_current_batch(): Flushing "
                  << current_batch_->events.size() << " eventos pendientes" << std::endl;
        send_event_batch(current_batch_->events);
        current_batch_.reset();
    } else {
        std::cout << "[INFO] flush_current_batch(): No hay eventos pendientes" << std::endl;
    }
}

void RingBufferConsumer::populate_protobuf_event(const SimpleEvent& event,
                                                 protobuf::NetworkSecurityEvent& proto_event,
                                                 int buffer_index) const {
    // ============================================================================
    // DAY 77: NaN-first — orden correcto: NaN -> populate(reales) -> run_ml_detection
    init_embedded_sentinels(proto_event.mutable_network_features());

    // ML DEFENDER: Feature Extraction (Phase 1, Day 3)
    // ============================================================================

    // Create flow key from event
    FlowKey flow_key{
        .src_ip = event.src_ip,
        .dst_ip = event.dst_ip,
        .src_port = event.src_port,
        .dst_port = event.dst_port,
        .protocol = event.protocol
    };
    auto& flow_manager = sniffer::flow::ShardedFlowManager::instance();
    auto flow_stats_opt = flow_manager.get_flow_stats_copy(flow_key);

    if (flow_stats_opt.has_value()) {
        const auto& flow_stats = flow_stats_opt.value();

        // Extract and populate ML Defender features (40 features)
        // This populates 4 submessages: DDoS, Ransomware, Traffic, Internal
        // DAY 78: inyección lazy — thread_local no admite constructor con args
		if (!ml_extractor_.has_aggregator() && ransomware_processor_) {
    		ml_extractor_.set_aggregator(ransomware_processor_->get_aggregator());
		}
		ml_extractor_.populate_ml_defender_features(flow_stats, proto_event);

        // Optional: Log feature extraction if verbosity enabled
        if (g_verbosity >= FeatureLogger::VerbosityLevel::GROUPED) {
            std::cout << "[ML Defender] Extracted features for flow: "
                      << "spkts=" << flow_stats.spkts
                      << ", dpkts=" << flow_stats.dpkts
                      << ", duration=" << (flow_stats.get_duration_us() / 1000.0) << "ms"
                      << std::endl;
        }
    } else {
        // Flow not found (shouldn't happen, but handle gracefully)
        if (g_verbosity >= FeatureLogger::VerbosityLevel::DETAILED) {
            std::cout << "[ML Defender] WARNING: Flow not found for feature extraction" << std::endl;
        }
    }
	// ============================================================================
    // ML DEFENDER: Embedded Detectors Inference (Phase 1, Day 4)
    // ============================================================================
    const_cast<RingBufferConsumer*>(this)->run_ml_detection(proto_event);
    // ============================================================================
    // END ML DEFENDER Integration
    // ============================================================================

    // Use pre-allocated buffers for IP conversion
    struct in_addr src_addr = {.s_addr = event.src_ip};
    struct in_addr dst_addr = {.s_addr = event.dst_ip};

    char* src_buffer = ip_buffers_src_[buffer_index % ip_buffers_src_.size()].data();
    char* dst_buffer = ip_buffers_dst_[buffer_index % ip_buffers_dst_.size()].data();

    inet_ntop(AF_INET, &src_addr, src_buffer, 16);
    inet_ntop(AF_INET, &dst_addr, dst_buffer, 16);

    // Generate event ID
    std::string event_id = std::to_string(event.timestamp) + "_" +
                          std::to_string(event.src_ip ^ event.dst_ip);

    // Populate basic fields
    proto_event.set_event_id(event_id);
    proto_event.set_originating_node_id(config_.node_id);
    proto_event.set_correlation_id(event_id);
    proto_event.set_schema_version(31);
    proto_event.set_protobuf_version("3.1.0");

    // Timestamp
    google::protobuf::Timestamp* timestamp = proto_event.mutable_event_timestamp();
    timestamp->set_seconds(event.timestamp / 1000000000ULL);
    timestamp->set_nanos(event.timestamp % 1000000000ULL);

    // Network features
    protobuf::NetworkFeatures* features = proto_event.mutable_network_features();
    features->set_source_ip(src_buffer);
    features->set_destination_ip(dst_buffer);
    features->set_source_port(event.src_port);
    features->set_destination_port(event.dst_port);
    features->set_protocol_number(event.protocol);
    features->set_protocol_name(protocol_to_string(event.protocol));

    // Dual-NIC deployment metadata (Phase 1, Day 7)
    // [DEBUG] Dual-NIC values from eBPF
    std::cout << "[DUAL-NIC] ifindex=" << event.source_ifindex
              << " mode=" << (int)event.interface_mode
              << " wan=" << (int)event.is_wan_facing
              << " iface=" << event.source_interface << std::endl;
    features->set_interface_mode(event.interface_mode);
    features->set_is_wan_facing(event.is_wan_facing);
    features->set_source_ifindex(event.source_ifindex);
    features->set_source_interface(event.source_interface);

    // Basic packet features
    features->set_total_forward_packets(1);
    features->set_total_backward_packets(0);
    features->set_total_forward_bytes(event.packet_len);
    features->set_total_backward_bytes(0);
    features->set_minimum_packet_length(event.packet_len);
    features->set_maximum_packet_length(event.packet_len);
    features->set_packet_length_mean(static_cast<double>(event.packet_len));
    features->set_average_packet_size(static_cast<double>(event.packet_len));

    // Flow start time
    google::protobuf::Timestamp* flow_start = features->mutable_flow_start_time();
    flow_start->set_seconds(event.timestamp / 1000000000ULL);
    flow_start->set_nanos(event.timestamp % 1000000000ULL);

    // Time window
    protobuf::TimeWindow* time_window = proto_event.mutable_time_window();
    google::protobuf::Timestamp* window_start = time_window->mutable_window_start();
    window_start->set_seconds(event.timestamp / 1000000000ULL);
    window_start->set_nanos(event.timestamp % 1000000000ULL);
    time_window->set_window_type(protobuf::TimeWindow::SLIDING);
    time_window->set_sequence_number(event.timestamp);

    // Distributed node info
    protobuf::DistributedNode* node = proto_event.mutable_capturing_node();
    node->set_node_id(config_.node_id);
    node->set_node_hostname("ebpf_sniffer_enhanced");
    node->set_node_role(protobuf::DistributedNode::PACKET_SNIFFER);
    node->set_node_status(protobuf::DistributedNode::ACTIVE);
    node->set_agent_version("3.1.0");

    // Heartbeat timestamp
    google::protobuf::Timestamp* heartbeat = node->mutable_last_heartbeat();
    heartbeat->set_seconds(event.timestamp / 1000000000ULL);
    heartbeat->set_nanos(event.timestamp % 1000000000ULL);

    // Classification
    proto_event.set_overall_threat_score(0.0);
    proto_event.set_final_classification("UNCATEGORIZED");
    proto_event.set_threat_category("RAW_CAPTURE");

    // Tags
    proto_event.add_event_tags("raw_ebpf_capture");
    proto_event.add_event_tags("enhanced_multithreaded");
    proto_event.add_event_tags("requires_processing");

}

std::string RingBufferConsumer::protocol_to_string(uint8_t protocol) const {
    switch (protocol) {
        case 1: return "ICMP";
        case 6: return "TCP";
        case 17: return "UDP";
        case 47: return "GRE";
        case 50: return "ESP";
        case 51: return "AH";
        case 58: return "ICMPv6";
        default: return "UNKNOWN";
    }
}

// Statistics and utility methods

RingConsumerStatsSnapshot RingBufferConsumer::get_stats() const {
    RingConsumerStatsSnapshot snapshot;
    snapshot.events_processed = stats_.events_processed.load();
    snapshot.events_sent = stats_.events_sent.load();
    snapshot.events_dropped = stats_.events_dropped.load();
    snapshot.protobuf_serialization_failures = stats_.protobuf_serialization_failures.load();
    snapshot.zmq_send_failures = stats_.zmq_send_failures.load();
    snapshot.ring_buffer_polls = stats_.ring_buffer_polls.load();
    snapshot.ring_buffer_timeouts = stats_.ring_buffer_timeouts.load();
    snapshot.total_processing_time_us = stats_.total_processing_time_us.load();
    snapshot.average_processing_time_us = stats_.average_processing_time_us.load();
    snapshot.start_time = stats_.start_time;

    // NEW: Ransomware stats
    snapshot.ransomware_fast_alerts = stats_.ransomware_fast_alerts.load();
    snapshot.ransomware_feature_extractions = stats_.ransomware_feature_extractions.load();
    snapshot.ransomware_confirmed_threats = stats_.ransomware_confirmed_threats.load();
    snapshot.ransomware_processing_time_us = stats_.ransomware_processing_time_us.load();

	// ML Defender embedded detection stats
    snapshot.ddos_attacks_detected = stats_.ddos_attacks_detected.load();
    snapshot.ransomware_attacks_detected = stats_.ransomware_attacks_detected.load();
    snapshot.suspicious_traffic_detected = stats_.suspicious_traffic_detected.load();
    snapshot.internal_anomalies_detected = stats_.internal_anomalies_detected.load();
    snapshot.ml_detection_time_us = stats_.ml_detection_time_us.load();

	return snapshot;
}

void RingBufferConsumer::print_stats() const {
    auto now = std::chrono::steady_clock::now();
    auto runtime = std::chrono::duration_cast<std::chrono::seconds>(now - stats_.start_time).count();

    std::cout << "\n╔═══════════════════════════════════════════════════════╗\n";
    std::cout << "║  Enhanced RingBufferConsumer Statistics              ║\n";
    std::cout << "╚═══════════════════════════════════════════════════════╝\n";

    std::cout << "\n📊 General Statistics:\n";
    std::cout << "  Runtime: " << runtime << " seconds\n";
    std::cout << "  Events processed: " << stats_.events_processed << "\n";
    std::cout << "  Events sent: " << stats_.events_sent << "\n";
    std::cout << "  Events dropped: " << stats_.events_dropped << "\n";

    if (runtime > 0) {
        double eps = static_cast<double>(stats_.events_processed.load()) / runtime;
        double send_rate = static_cast<double>(stats_.events_sent.load()) / runtime;
        std::cout << "  Events per second: " << std::fixed << std::setprecision(2) << eps << "\n";
        std::cout << "  Send rate: " << send_rate << "\n";
    }

    std::cout << "\n🔧 Processing:\n";
    std::cout << "  Protobuf failures: " << stats_.protobuf_serialization_failures << "\n";
    std::cout << "  ZMQ send failures: " << stats_.zmq_send_failures << "\n";
    std::cout << "  Ring buffer polls: " << stats_.ring_buffer_polls << "\n";
    std::cout << "  Ring buffer timeouts: " << stats_.ring_buffer_timeouts << "\n";
    std::cout << "  Avg processing time: " << std::fixed << std::setprecision(2)
              << stats_.average_processing_time_us.load() << " μs\n";

    // Ransomware statistics section
    if (ransomware_enabled_) {
        std::cout << "\n🚨 Ransomware Detection:\n";
        std::cout << "  Fast alerts (Layer 1): " << stats_.ransomware_fast_alerts << "\n";
        std::cout << "  Feature extractions (Layer 2): " << stats_.ransomware_feature_extractions << "\n";
        std::cout << "  Confirmed threats: " << stats_.ransomware_confirmed_threats << "\n";

        uint64_t ransom_time = stats_.ransomware_processing_time_us.load();
        if (ransom_time > 0) {
            std::cout << "  Ransomware processing time: "
                      << (ransom_time / 1000.0) << " ms total\n";

            if (stats_.ransomware_fast_alerts.load() > 0) {
                double avg_alert_time = static_cast<double>(ransom_time) /
                                       stats_.ransomware_fast_alerts.load();
                std::cout << "  Avg alert time: " << std::fixed << std::setprecision(2)
                          << avg_alert_time << " μs\n";
            }
        }

        // Detection rates
        if (runtime > 0 && stats_.ransomware_fast_alerts.load() > 0) {
            double alerts_per_min = (stats_.ransomware_fast_alerts.load() * 60.0) / runtime;
            std::cout << "  Alert rate: " << std::fixed << std::setprecision(2)
                      << alerts_per_min << " alerts/min\n";
        }
    } else {
        std::cout << "\n🚨 Ransomware Detection: DISABLED\n";
    }

	// ML Defender embedded detectors statistics
    std::cout << "\n🛡️  ML Defender Embedded Detectors:\n";
    std::cout << "  DDoS attacks detected: " << stats_.ddos_attacks_detected << "\n";
    std::cout << "  Ransomware attacks detected: " << stats_.ransomware_attacks_detected << "\n";
    std::cout << "  Suspicious traffic detected: " << stats_.suspicious_traffic_detected << "\n";
    std::cout << "  Internal anomalies detected: " << stats_.internal_anomalies_detected << "\n";

    uint64_t ml_time = stats_.ml_detection_time_us.load();
    if (ml_time > 0 && stats_.events_processed.load() > 0) {
        double avg_ml_time = static_cast<double>(ml_time) / stats_.events_processed.load();
        std::cout << "  Avg ML detection time: " << std::fixed << std::setprecision(2)
                  << avg_ml_time << " μs\n";
    }

    std::cout << "\n⚙️  System Status:\n";
    std::cout << "  Active consumers: " << active_consumers_ << "\n";
    std::cout << "  Processing queue size: " << processing_queue_.size() << "\n";
    std::cout << "  Send queue size: " << send_queue_.size() << "\n";

    std::cout << "╚═══════════════════════════════════════════════════════╝\n";
}

void RingBufferConsumer::reset_stats() {
    stats_.events_processed = 0;
    stats_.events_sent = 0;
    stats_.events_dropped = 0;
    stats_.protobuf_serialization_failures = 0;
    stats_.zmq_send_failures = 0;
    stats_.ring_buffer_polls = 0;
    stats_.ring_buffer_timeouts = 0;
    stats_.total_processing_time_us = 0;
    stats_.average_processing_time_us = 0.0;

    // NEW: Reset ransomware stats
    stats_.ransomware_fast_alerts = 0;
    stats_.ransomware_feature_extractions = 0;
    stats_.ransomware_confirmed_threats = 0;
    stats_.ransomware_processing_time_us = 0;

    stats_.ddos_attacks_detected = 0;
    stats_.ransomware_attacks_detected = 0;
    stats_.suspicious_traffic_detected = 0;
    stats_.internal_anomalies_detected = 0;
    stats_.ml_detection_time_us = 0;

    stats_.start_time = std::chrono::steady_clock::now();
}

void RingBufferConsumer::set_event_callback(EventCallback callback) {
    external_callback_ = std::move(callback);
}

// Configuration helpers
size_t RingBufferConsumer::get_optimal_batch_size() const {
    return config_.buffers.batch_processing_size;
}

int RingBufferConsumer::get_optimal_consumer_count() const {
    return config_.threading.ring_consumer_threads;
}

std::chrono::milliseconds RingBufferConsumer::get_processing_timeout() const {
    return std::chrono::milliseconds(config_.zmq.queue_management.queue_timeout_ms);
}

// Error handling
void RingBufferConsumer::handle_ring_buffer_error(int error_code) {
    std::cerr << "[ERROR] Ring buffer error: " << strerror(-error_code) << std::endl;
    stats_.events_dropped++;
}

void RingBufferConsumer::handle_zmq_error(const zmq::error_t& error) {
    if (error.num() != EAGAIN) {
        std::cerr << "[ERROR] ZeroMQ error: " << error.what() << std::endl;
    }
    stats_.zmq_send_failures++;
}

void RingBufferConsumer::handle_protobuf_error(const std::exception& error) {
    std::cerr << "[ERROR] Protobuf error: " << error.what() << std::endl;
    stats_.protobuf_serialization_failures++;
}

// Shutdown methods
void RingBufferConsumer::shutdown_consumers() {
    for (auto& thread : consumer_threads_) {
        if (thread.joinable()) {
            thread.join();
        }
    }
    consumer_threads_.clear();
}

void RingBufferConsumer::shutdown_zmq() {
    for (auto& socket : zmq_sockets_) {
        if (socket) {
            socket->close();
        }
    }
    zmq_sockets_.clear();
	socket_mutexes_.clear();
    zmq_context_.reset();
}

void RingBufferConsumer::cleanup_resources() {
    if (ring_buf_) {
        ring_buffer__free(ring_buf_);
        ring_buf_ = nullptr;
    }
}

void RingBufferConsumer::update_processing_time(std::chrono::microseconds duration) {
    stats_.total_processing_time_us += duration.count();

    // Update rolling average (exponential moving average)
    double current_avg = stats_.average_processing_time_us.load();
    double new_avg = EMA_SMOOTHING_FACTOR * current_avg +
                     EMA_NEW_SAMPLE_WEIGHT * duration.count();
    stats_.average_processing_time_us = new_avg;
}

bool RingBufferConsumer::initialize_ransomware_detection() {
    try {
        ransomware_processor_ = std::make_unique<RansomwareFeatureProcessor>();

        if (!ransomware_processor_->initialize()) {
            std::cerr << "[ERROR] Failed to initialize RansomwareFeatureProcessor" << std::endl;
            return false;
        }

        ransomware_enabled_ = true;
        std::cout << "[INFO] ✅ Ransomware detection initialized (2-layer system)" << std::endl;
        std::cout << "       Layer 1: FastDetector (10s window, heuristics)" << std::endl;
        std::cout << "       Layer 2: FeatureProcessor (30s aggregation)" << std::endl;
        return true;

    } catch (const std::exception& e) {
        std::cerr << "[ERROR] Ransomware detection init failed: " << e.what() << std::endl;
        ransomware_enabled_ = false;
        return false;
    }
}

void RingBufferConsumer::ransomware_processor_loop() {
    std::cout << "[INFO] Ransomware processor thread started ("
              << RANSOMWARE_EXTRACTION_INTERVAL_SEC << "s extraction)" << std::endl;

    while (!should_stop_) {
        std::this_thread::sleep_for(
            std::chrono::seconds(RANSOMWARE_EXTRACTION_INTERVAL_SEC));

        if (should_stop_) break;

        protobuf::RansomwareFeatures features;
        if (ransomware_processor_->get_features_if_ready(features)) {
            send_ransomware_features(features);
        }
    }

    std::cout << "[INFO] Ransomware processor thread stopped" << std::endl;
}

void RingBufferConsumer::send_fast_alert(const SimpleEvent& event) {
    auto start_time = std::chrono::steady_clock::now();

    try {
        protobuf::NetworkSecurityEvent alert;
        alert.set_event_id("fast-alert-" + std::to_string(event.timestamp));

        auto* ts = alert.mutable_event_timestamp();
        ts->set_seconds(event.timestamp / 1'000'000'000ULL);
        ts->set_nanos(event.timestamp % 1'000'000'000ULL);

        alert.set_originating_node_id(config_.node_id);

        auto* net_features = alert.mutable_network_features();

        char src_ip_str[INET_ADDRSTRLEN];
        char dst_ip_str[INET_ADDRSTRLEN];
        struct in_addr src_addr, dst_addr;
        src_addr.s_addr = htonl(event.src_ip);
        dst_addr.s_addr = htonl(event.dst_ip);
        inet_ntop(AF_INET, &src_addr, src_ip_str, INET_ADDRSTRLEN);
        inet_ntop(AF_INET, &dst_addr, dst_ip_str, INET_ADDRSTRLEN);

        net_features->set_source_ip(src_ip_str);
        net_features->set_destination_ip(dst_ip_str);
        net_features->set_source_port(event.src_port);
        net_features->set_destination_port(event.dst_port);
        net_features->set_protocol_number(event.protocol);
        net_features->set_protocol_name(sniffer::protocol_to_string(event.protocol));
		// FIX 76
		init_embedded_sentinels(net_features);

        alert.set_overall_threat_score(fast_detector_config_.ransomware.scores.alert);

		// 🎯 DAY 13: Dual-Score Architecture
		alert.set_fast_detector_score(fast_detector_config_.ransomware.scores.alert);
		alert.set_ml_detector_score(0.0);  // ML no ha ejecutado aún
		alert.set_fast_detector_triggered(true);
		alert.set_fast_detector_reason("high_external_ips");
		alert.set_authoritative_source(protobuf::DETECTOR_SOURCE_FAST_ONLY);

        // 🎯 ADR-002: Multi-Engine Provenance (Day 37)
        auto* provenance = alert.mutable_provenance();
        auto* sniffer_verdict = provenance->add_verdicts();
        sniffer_verdict->set_engine_name("fast-path-sniffer");
        sniffer_verdict->set_classification("SUSPICIOUS");
        sniffer_verdict->set_confidence(fast_detector_config_.ransomware.scores.alert);
        sniffer_verdict->set_reason_code(ml_defender::to_string(ml_defender::ReasonCode::STAT_ANOMALY));
        sniffer_verdict->set_timestamp_ns(event.timestamp);

        provenance->set_global_timestamp_ns(event.timestamp);
        provenance->set_final_decision("ALERT");  // Sniffer solo alerta, no bloquea
        provenance->set_discrepancy_score(0.0);   // Solo un motor por ahora

		alert.set_final_classification("SUSPICIOUS");
        alert.set_threat_category("RANSOMWARE_FAST_DETECTION");

        auto snapshot = fast_detector_.snapshot();
        alert.set_correlation_id("ransomware-" + std::to_string(event.timestamp / 1'000'000'000ULL));

        std::string serialized;
        if (alert.SerializeToString(&serialized)) {
            std::vector<uint8_t> data(serialized.begin(), serialized.end());

            std::lock_guard<std::mutex> lock(send_queue_mutex_);
            send_queue_.push(std::move(data));
            send_queue_cv_.notify_one();

            stats_.ransomware_fast_alerts++;

            std::cout << "[FAST ALERT] Ransomware heuristic: "
                      << "src=" << src_ip_str << ":" << event.src_port
                      << " dst=" << dst_ip_str << ":" << event.dst_port
                      << " (ExtIPs=" << snapshot.external_ips_10s
                      << ", SMB=" << snapshot.smb_conns << ")" << std::endl;
        }

    } catch (const std::exception& e) {
        std::cerr << "[WARNING] Fast alert failed: " << e.what() << std::endl;
    }

    auto end_time = std::chrono::steady_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::microseconds>(end_time - start_time);
    stats_.ransomware_processing_time_us += duration.count();
}

void RingBufferConsumer::send_ransomware_features(const protobuf::RansomwareFeatures& features) {
    auto start_time = std::chrono::steady_clock::now();

    try {
        protobuf::NetworkSecurityEvent event;

        uint64_t now_ns = std::chrono::duration_cast<std::chrono::nanoseconds>(
            std::chrono::system_clock::now().time_since_epoch()).count();
        event.set_event_id("ransomware-features-" + std::to_string(now_ns));

        auto* ts = event.mutable_event_timestamp();
        ts->set_seconds(now_ns / 1'000'000'000ULL);
        ts->set_nanos(now_ns % 1'000'000'000ULL);

        event.set_originating_node_id(config_.node_id);

        auto* net_features = event.mutable_network_features();
        auto* ransom_features = net_features->mutable_ransomware();
        ransom_features->CopyFrom(features);

        // DAY 75 FIX: Populate embedded detector messages with Phase 1 sentinel values.
        // These events are time-window aggregates from RansomwareProcessor —
        // no FlowStatistics is available here, so populate_ml_defender_features()
        // cannot be called. Proto3 does NOT serialize submessages where all float
        // fields equal 0.0f (the default), causing has_ddos_embedded()==false on
        // the receiver side and "Skipping artifact save" in rag_logger.
        // Sentinel 0.5f matches the Phase 1 TODO neutral used in ml_defender_features.cpp.
        // Phase 2: replace with real values once FlowAggregator is available.
        // DAY 76 FIX: reemplaza bloque DAY75 parcial con helper completo (40 campos)
        init_embedded_sentinels(net_features);

        bool high_threat = (
            features.new_external_ips_30s() > fast_detector_config_.ransomware.activation_thresholds.external_ips_30s ||
            features.smb_connection_diversity() > fast_detector_config_.ransomware.activation_thresholds.smb_diversity
        );

        // Calculate fast detector score
        double fast_score = high_threat
        ? fast_detector_config_.ransomware.scores.high_threat
        : fast_detector_config_.ransomware.scores.suspicious;

        // 🎯 DAY 13: Dual-Score Architecture
        event.set_fast_detector_score(fast_score);
        event.set_ml_detector_score(0.0);  // ML no ha ejecutado aún
        event.set_fast_detector_triggered(true);
        event.set_fast_detector_reason(
            high_threat ? "external_ips_smb_high" : "external_ips_smb_medium"
        );
        event.set_authoritative_source(protobuf::DETECTOR_SOURCE_FAST_ONLY);

        // 🎯 ADR-002: Multi-Engine Provenance (Day 37)
        auto* provenance = event.mutable_provenance();
        auto* sniffer_verdict = provenance->add_verdicts();
        sniffer_verdict->set_engine_name("fast-path-sniffer");
        sniffer_verdict->set_classification(high_threat ? "MALICIOUS" : "SUSPICIOUS");
        sniffer_verdict->set_confidence(fast_score);
        sniffer_verdict->set_reason_code(
            high_threat
                ? ml_defender::to_string(ml_defender::ReasonCode::STAT_ANOMALY)
                : ml_defender::to_string(ml_defender::ReasonCode::STAT_ANOMALY)
        );
        sniffer_verdict->set_timestamp_ns(now_ns);

        provenance->set_global_timestamp_ns(now_ns);
        provenance->set_final_decision(high_threat ? "DROP" : "ALERT");
        provenance->set_discrepancy_score(0.0);

        // Set overall score and classification
        event.set_overall_threat_score(fast_score);

    if (high_threat) {
        event.set_final_classification("MALICIOUS");
        stats_.ransomware_confirmed_threats++;

        // ✅ Day 12: Logging detallado con configuración externalizada
        if (fast_detector_config_.logging.log_activations) {
            std::cout << "[FAST-DETECT] HIGH_THREAT: "
                      << "ExtIPs=" << features.new_external_ips_30s()
                      << " (threshold=" << fast_detector_config_.ransomware.activation_thresholds.external_ips_30s << "), "
                      << "SMB=" << features.smb_connection_diversity()
                      << " (threshold=" << fast_detector_config_.ransomware.activation_thresholds.smb_diversity << "), "
                      << "DNS=" << std::fixed << std::setprecision(2) << features.dns_query_entropy()
                      << ", FastScore=" << fast_score
                      << std::endl;
        }
    } else {
        event.set_final_classification("SUSPICIOUS");

        // ✅ Day 12: Logging detallado con configuración externalizada
        if (fast_detector_config_.logging.log_activations) {
            std::cout << "[FAST-DETECT] SUSPICIOUS: "
                      << "ExtIPs=" << features.new_external_ips_30s()
                      << " (threshold=" << fast_detector_config_.ransomware.activation_thresholds.external_ips_30s << "), "
                      << "SMB=" << features.smb_connection_diversity()
                      << " (threshold=" << fast_detector_config_.ransomware.activation_thresholds.smb_diversity << "), "
                      << "DNS=" << std::fixed << std::setprecision(2) << features.dns_query_entropy()
                      << ", FastScore=" << fast_score
                      << std::endl;
        }
    }

            event.set_threat_category("RANSOMWARE_CONFIRMED");
            event.set_correlation_id("ransomware-analysis-" + std::to_string(now_ns / 1'000'000'000ULL));

            std::string serialized;
            if (event.SerializeToString(&serialized)) {
                std::vector<uint8_t> data(serialized.begin(), serialized.end());

                std::lock_guard<std::mutex> lock(send_queue_mutex_);
                send_queue_.push(std::move(data));
                send_queue_cv_.notify_one();

                stats_.ransomware_feature_extractions++;

                std::cout << "[RANSOMWARE] Features: ExtIPs=" << features.new_external_ips_30s()
                          << ", SMB=" << features.smb_connection_diversity()
                          << ", DNS=" << features.dns_query_entropy()
                          << ", Score=" << event.overall_threat_score()
                          << ", Class=" << event.final_classification() << std::endl;
            }

    } catch (const std::exception& e) {
        std::cerr << "[ERROR] Ransomware features failed: " << e.what() << std::endl;
    }

    auto end_time = std::chrono::steady_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::microseconds>(end_time - start_time);
    stats_.ransomware_processing_time_us += duration.count();
}
void RingBufferConsumer::shutdown_ransomware_detection() {
    if (ransomware_processor_) {
        ransomware_processor_->stop();
        ransomware_processor_.reset();
    }
    ransomware_enabled_ = false;
}
// ============================================================================
// ML DEFENDER: Feature Extraction Functions (Phase 1, Day 4)
// ============================================================================

ml_defender::DDoSDetector::Features
RingBufferConsumer::extract_ddos_features(
    const protobuf::NetworkSecurityEvent& proto_event) const {

    const auto& ddos = proto_event.network_features().ddos_embedded();

    return ml_defender::DDoSDetector::Features{
        .syn_ack_ratio = ddos.syn_ack_ratio(),
        .packet_symmetry = ddos.packet_symmetry(),
        .source_ip_dispersion = ddos.source_ip_dispersion(),
        .protocol_anomaly_score = ddos.protocol_anomaly_score(),
        .packet_size_entropy = ddos.packet_size_entropy(),
        .traffic_amplification_factor = ddos.traffic_amplification_factor(),
        .flow_completion_rate = ddos.flow_completion_rate(),
        .geographical_concentration = ddos.geographical_concentration(),
        .traffic_escalation_rate = ddos.traffic_escalation_rate(),
        .resource_saturation_score = ddos.resource_saturation_score()
    };
}

ml_defender::RansomwareDetector::Features
RingBufferConsumer::extract_ransomware_features(
    const protobuf::NetworkSecurityEvent& proto_event) const {

    const auto& ransom = proto_event.network_features().ransomware_embedded();

    return ml_defender::RansomwareDetector::Features{
        .io_intensity = ransom.io_intensity(),
        .entropy = ransom.entropy(),
        .resource_usage = ransom.resource_usage(),
        .network_activity = ransom.network_activity(),
        .file_operations = ransom.file_operations(),
        .process_anomaly = ransom.process_anomaly(),
        .temporal_pattern = ransom.temporal_pattern(),
        .access_frequency = ransom.access_frequency(),
        .data_volume = ransom.data_volume(),
        .behavior_consistency = ransom.behavior_consistency()
    };
}

ml_defender::TrafficDetector::Features
RingBufferConsumer::extract_traffic_features(
    const protobuf::NetworkSecurityEvent& proto_event) const {

    const auto& traffic = proto_event.network_features().traffic_classification();

    return ml_defender::TrafficDetector::Features{
        .packet_rate = traffic.packet_rate(),
        .connection_rate = traffic.connection_rate(),
        .tcp_udp_ratio = traffic.tcp_udp_ratio(),
        .avg_packet_size = traffic.avg_packet_size(),
        .port_entropy = traffic.port_entropy(),
        .flow_duration_std = traffic.flow_duration_std(),
        .src_ip_entropy = traffic.src_ip_entropy(),
        .dst_ip_concentration = traffic.dst_ip_concentration(),
        .protocol_variety = traffic.protocol_variety(),
        .temporal_consistency = traffic.temporal_consistency()
    };
}

ml_defender::InternalDetector::Features
RingBufferConsumer::extract_internal_features(
    const protobuf::NetworkSecurityEvent& proto_event) const {

    const auto& internal = proto_event.network_features().internal_anomaly();

    return ml_defender::InternalDetector::Features{
        .internal_connection_rate = internal.internal_connection_rate(),
        .service_port_consistency = internal.service_port_consistency(),
        .protocol_regularity = internal.protocol_regularity(),
        .packet_size_consistency = internal.packet_size_consistency(),
        .connection_duration_std = internal.connection_duration_std(),
        .lateral_movement_score = internal.lateral_movement_score(),
        .service_discovery_patterns = internal.service_discovery_patterns(),
        .data_exfiltration_indicators = internal.data_exfiltration_indicators(),
        .temporal_anomaly_score = internal.temporal_anomaly_score(),
        .access_pattern_entropy = internal.access_pattern_entropy()
    };
}



// ============================================================================
// ML DEFENDER: Embedded Detectors Inference Engine
// ============================================================================

void RingBufferConsumer::run_ml_detection(protobuf::NetworkSecurityEvent& proto_event) {
    // DAY 77 STATUS: Inferencia funciona, scores NO se escriben al proto.
    // DAY 78 TODO: implementar PHASE 3/4 — escribir scores con sentinel -1.0f
    //   proto_event.set_ddos_score(-1.0f)       // -1.0f = no inferido ([0,1] = valido)
    //   proto_event.set_ransomware_score(-1.0f)
    //   proto_event.set_final_classification("PENDING")
    // DAY 80 ✅ thresholds leídos desde JSON vía config_.ml_defender (Phase1-Day4-CRITICAL CERRADO)

    auto start = std::chrono::high_resolution_clock::now();

    // ========================================================================
    // PHASE 1: Feature Extraction
    // ========================================================================
    auto ddos_features = extract_ddos_features(proto_event);
    auto ransomware_features = extract_ransomware_features(proto_event);
    auto traffic_features = extract_traffic_features(proto_event);
    auto internal_features = extract_internal_features(proto_event);

    // ========================================================================
    // PHASE 2: Model Inference (Thread-local, <100μs per detector)
    // ========================================================================
    auto ddos_pred = ddos_detector_.predict(ddos_features);
    auto ransomware_pred = ransomware_detector_.predict(ransomware_features);
    auto traffic_pred = traffic_detector_.predict(traffic_features);
    auto internal_pred = internal_detector_.predict(internal_features);

    // ========================================================================
    // PHASE 3: Threshold Application & Classification
    // DAY 78: scores escritos al proto con sentinel -1.0f para no inferido
    // DAY 80 ✅ thresholds leídos desde config_.ml_defender.thresholds (JSON is the LAW)
    // ========================================================================
    double threat_score = -1.0;
    std::string classification = "BENIGN";
    std::string category = "NORMAL";

    // DDoS
    if (ddos_pred.is_ddos(config_.ml_defender.thresholds.ddos)) {
        stats_.ddos_attacks_detected++;
        threat_score = ddos_pred.ddos_prob;
        classification = "MALICIOUS";
        category = "DDOS";
        proto_event.mutable_ml_analysis()->set_final_threat_classification("DDOS");
    }

    // Ransomware (solo si no hay DDoS ya clasificado)
    if (ransomware_pred.is_ransomware(config_.ml_defender.thresholds.ransomware)) {
        stats_.ransomware_attacks_detected++;
        if (classification != "MALICIOUS") {
            threat_score = ransomware_pred.ransomware_prob;
            classification = "MALICIOUS";
            category = "RANSOMWARE";
            proto_event.mutable_ml_analysis()->set_final_threat_classification("RANSOMWARE");
        }
    }

    // Traffic context (siempre)
    proto_event.mutable_ml_analysis()->set_traffic_context(
        traffic_pred.probability >= 0.5f ? "INTERNAL" : "EXTERNAL"
    );
    if (traffic_pred.probability >= config_.ml_defender.thresholds.traffic) {
        stats_.suspicious_traffic_detected++;
        if (classification == "BENIGN") {
            threat_score = traffic_pred.probability;
            classification = "SUSPICIOUS";
            category = "SUSPICIOUS_TRAFFIC";
        }
    }

    // Internal anomaly
    if (internal_pred.is_suspicious(config_.ml_defender.thresholds.internal)) {
        stats_.internal_anomalies_detected++;
        if (classification == "BENIGN") {
            threat_score = internal_pred.suspicious_prob;
            classification = "SUSPICIOUS";
            category = "INTERNAL_ANOMALY";
        }
    }

    // ========================================================================
    // PHASE 4: Write to proto
    // ========================================================================
    if (threat_score >= 0.0) {
        proto_event.set_overall_threat_score(threat_score);
    }
    proto_event.set_final_classification(classification);
    proto_event.set_threat_category(category);

    // ========================================================================
    // PHASE 5: Performance Metrics
    // ========================================================================
    auto end = std::chrono::high_resolution_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::microseconds>(end - start);
    stats_.ml_detection_time_us += duration.count();

    // Optional: Log detections if verbosity enabled
    if (g_verbosity >= FeatureLogger::VerbosityLevel::GROUPED) {
        bool any_detection = (ddos_pred.is_ddos(config_.ml_defender.thresholds.ddos) ||
                             ransomware_pred.is_ransomware(config_.ml_defender.thresholds.ransomware) ||
                             traffic_pred.probability >= config_.ml_defender.thresholds.traffic ||
                             internal_pred.is_suspicious(config_.ml_defender.thresholds.internal));

        if (any_detection) {
            std::cout << "[ML Defender] Detection: "
                      << "DDoS=" << ddos_pred.ddos_prob << " "
                      << "Ransom=" << ransomware_pred.ransomware_prob << " "
                      << "Traffic=" << traffic_pred.probability << " "
                      << "Internal=" << internal_pred.suspicious_prob << " "
                      << "(" << duration.count() << "μs)"
                      << std::endl;
        }
    }
}
} // namespace sniffer