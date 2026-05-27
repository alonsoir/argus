//===----------------------------------------------------------------------===//
// ML Defender - Firewall ACL Agent
// zmq_subscriber.cpp - ZMQ Subscriber Implementation (Day 50 - Full Observability)
// firewall-acl-agent/src/api/zmq_subscriber.cpp
//===----------------------------------------------------------------------===//

#include "firewall/zmq_subscriber.hpp"
#include <crypto_transport/contexts.hpp>
#include <lz4.h>
#include <cstring>
#include "firewall_observability_logger.hpp"
#include "crash_diagnostics.hpp"
#include <crypto_transport/crypto.hpp>
#include <crypto_transport/compression.hpp>
#include <crypto_transport/utils.hpp>
#include <iostream>
#include <thread>
#include <stdexcept>
#include <cstring>

namespace mldefender {
namespace firewall {

// Helper functions for string <-> vector<uint8_t> conversion
namespace {
    inline std::vector<uint8_t> string_to_bytes(const std::string& str) {
        return std::vector<uint8_t>(str.begin(), str.end());
    }

    inline std::string bytes_to_string(const std::vector<uint8_t>& bytes) {
        return std::string(bytes.begin(), bytes.end());
    }
}

//==============================================================================
// LIFECYCLE (Day 50: Enhanced with observability)
//==============================================================================

ZMQSubscriber::ZMQSubscriber(BatchProcessor& processor,
                                 const Config& config,
                                 EtcdClient* etcd_client)
        : processor_(processor)
        , config_(config)
        , running_(false)
        , current_reconnect_interval_ms_(config.reconnect_interval_ms)
        , etcd_client_(etcd_client)  // ✅ Day 59: Store etcd client
        , hmac_key_(std::nullopt)     // ✅ Day 59: Initialize as empty
    {
    FIREWALL_LOG_INFO("Initializing ZMQ Subscriber",
        "endpoint", config.endpoint,
        "topic", config.topic,
        "recv_timeout_ms", config.recv_timeout_ms);

    // Create ZMQ context (1 IO thread is sufficient)
    try {
        context_ = std::make_unique<zmq::context_t>(1);
        FIREWALL_LOG_INFO("ZMQ context created", "io_threads", 1);
    } catch (const zmq::error_t& e) {
        FIREWALL_LOG_CRASH("Failed to create ZMQ context", "error", e.what());
        throw std::runtime_error(
            std::string("Failed to create ZMQ context: ") + e.what()
        );
    }

    // Initialize logger
    try {
        logger_ = std::make_unique<FirewallLogger>(
            config_.log_directory,
            config_.log_queue_size
        );
        logger_->start();

        // ✅ Day 59: Retrieve HMAC key from etcd if available
        // ✅ Day 59: Retrieve HMAC key from etcd if available
        if (etcd_client_) {
            try {
                // Get service discovery paths from etcd-server
                auto paths = etcd_client_->get_service_paths();

                if (!paths.is_valid()) {
                    FIREWALL_LOG_ERROR("Service discovery paths not available from etcd-server");
                    throw std::runtime_error("Missing service discovery paths");
                }

                FIREWALL_LOG_INFO("Using service discovery path for HMAC key",
                    "path", paths.hmac_key);

                auto key_result = etcd_client_->get_hmac_key(paths.hmac_key);

                if (key_result.has_value()) {
                    hmac_key_ = key_result;
                    FIREWALL_LOG_INFO("HMAC key retrieved from etcd",
                        "key_path", paths.hmac_key,
                        "key_size_bytes", hmac_key_->size());
                } else {
                    FIREWALL_LOG_WARN("HMAC key not found in etcd, CSV signing disabled",
                        "key_path", paths.hmac_key);
                }

            } catch (const std::exception& e) {
                FIREWALL_LOG_ERROR("Failed to retrieve HMAC key from etcd",
                    "error", e.what());
            }
        } else {
            FIREWALL_LOG_WARN("No etcd client provided, CSV signing disabled");
        }

        FIREWALL_LOG_INFO("Firewall logger initialized",
            "log_directory", config_.log_directory,
            "log_queue_size", config_.log_queue_size);

    } catch (const std::exception& e) {
        FIREWALL_LOG_CRASH("Failed to initialize logger", "error", e.what());
        throw std::runtime_error(
            std::string("Failed to initialize logger: ") + e.what()
        );
    }

    // ADR-013 PHASE 2 — DAY 98: inicializar CryptoTransport
    try {
        seed_client_ = std::make_unique<ml_defender::SeedClient>(
            "/etc/ml-defender/firewall-acl-agent/firewall.json");
        seed_client_->load();
        rx_ = std::make_unique<crypto_transport::CryptoTransport>(
            *seed_client_, ml_defender::crypto::CTX_ML_TO_FIREWALL);
        FIREWALL_LOG_INFO("CryptoTransport inicializado (HKDF-SHA256 + ChaCha20-Poly1305)");
    } catch (const std::exception& e) {
        FIREWALL_LOG_WARN("CryptoTransport init failed — modo plaintext", "error", std::string(e.what()));
    }

    FIREWALL_LOG_INFO("ZMQ Subscriber initialization complete",
        "encryption", config_.encryption_enabled ? "ENABLED" : "disabled",
        "compression", config_.compression_enabled ? "ENABLED" : "disabled");
}

ZMQSubscriber::~ZMQSubscriber() {
    FIREWALL_LOG_INFO("ZMQ Subscriber destructor called");

    // Ensure graceful shutdown
    if (running_.load()) {
        FIREWALL_LOG_WARN("Destructor called while running, forcing stop");
        stop();

        // Give it a moment to stop gracefully
        for (int i = 0; i < 10 && running_.load(); ++i) {
            std::this_thread::sleep_for(std::chrono::milliseconds(100));
        }
    }

    // Stop logger and print statistics
    if (logger_) {
        FIREWALL_LOG_INFO("Stopping logger");
        logger_->stop(5000);  // 5 second timeout

        FIREWALL_LOG_INFO("Logger final statistics",
            "events_logged", logger_->total_logged(),
            "events_dropped", logger_->total_dropped(),
            "queue_size", logger_->queue_size());
    }

    // Close socket before destroying context
    if (socket_) {
        try {
            socket_->close();
            FIREWALL_LOG_DEBUG("ZMQ socket closed");
        } catch (const zmq::error_t& e) {
            FIREWALL_LOG_ERROR("Error closing socket", "error", e.what());
        }
    }

    FIREWALL_LOG_INFO("ZMQ Subscriber destroyed");
}

//==============================================================================
// CONTROL (Day 50: Enhanced)
//==============================================================================

void ZMQSubscriber::run() {
    // Check if already running
    bool expected = false;
    if (!running_.compare_exchange_strong(expected, true)) {
        FIREWALL_LOG_ERROR("run() called while already running");
        throw std::runtime_error("ZMQSubscriber::run() called while already running");
    }

    FIREWALL_LOG_INFO("Starting ZMQ event loop");

    // Mark system as running
    if (firewall::diagnostics::g_system_state) {
        firewall::diagnostics::g_system_state->is_running.store(true);
    }

    try {
        while (running_.load() &&
               firewall::diagnostics::g_system_state->is_running.load()) {
            try {
                // Connect/reconnect
                connect();
                reset_reconnect_backoff();

                FIREWALL_LOG_INFO("Connected successfully to ZMQ endpoint");

                // Main receive loop
                receive_loop();

            } catch (const zmq::error_t& e) {
                // ZMQ error - likely connection issue
                FIREWALL_LOG_ERROR("ZMQ error in event loop",
                    "error", e.what(),
                    "errno", e.num());
                DUMP_STATE_ON_ERROR("zmq_error");

                if (config_.enable_reconnect && running_.load()) {
                    handle_reconnect();
                } else {
                    break;
                }

            } catch (const std::exception& e) {
                // Other error
                FIREWALL_LOG_ERROR("Exception in event loop", "error", e.what());
                DUMP_STATE_ON_ERROR("event_loop_exception");

                if (config_.enable_reconnect && running_.load()) {
                    handle_reconnect();
                } else {
                    break;
                }
            }
        }
    } catch (...) {
        FIREWALL_LOG_CRASH("Unexpected exception in event loop");
        DUMP_STATE_ON_ERROR("unexpected_exception");
        running_.store(false);
        throw;
    }

    running_.store(false);
    FIREWALL_LOG_INFO("ZMQ event loop stopped");

    // Final state dump
    DUMP_STATE_ON_ERROR("zmq_event_loop_exit");
}

void ZMQSubscriber::stop() {
    FIREWALL_LOG_INFO("Stop requested for ZMQ Subscriber");
    running_.store(false);

    if (firewall::diagnostics::g_system_state) {
        firewall::diagnostics::g_system_state->is_running.store(false);
    }
}

//==============================================================================
// INTERNAL METHODS (Day 50: Fully Instrumented)
//==============================================================================

void ZMQSubscriber::connect() {
    FIREWALL_LOG_DEBUG("Connecting to ZMQ endpoint", "endpoint", config_.endpoint);

    // Close existing socket if any
    if (socket_) {
        try {
            socket_->close();
            FIREWALL_LOG_DEBUG("Closed old socket");
        } catch (const zmq::error_t& e) {
            FIREWALL_LOG_WARN("Error closing old socket", "error", e.what());
        }
        socket_.reset();
    }

    // Create new SUB socket
    socket_ = std::make_unique<zmq::socket_t>(*context_, zmq::socket_type::sub);
    FIREWALL_LOG_DEBUG("Created new SUB socket");

    // Set socket options
    try {
        // Receive timeout for graceful shutdown
        socket_->set(zmq::sockopt::rcvtimeo, config_.recv_timeout_ms);
        FIREWALL_LOG_DEBUG("Set socket option", "rcvtimeo", config_.recv_timeout_ms);

        // Linger time on close
        socket_->set(zmq::sockopt::linger, config_.linger_ms);
        FIREWALL_LOG_DEBUG("Set socket option", "linger", config_.linger_ms);

        // High water mark — desde config (BACKLOG-ZMQ-TUNING-001)
        socket_->set(zmq::sockopt::rcvhwm, config_.high_water_mark);
        FIREWALL_LOG_DEBUG("Set socket option", "rcvhwm", config_.high_water_mark);
        // Reconnect interval — backoff exponencial hasta max
        socket_->set(zmq::sockopt::reconnect_ivl,     config_.reconnect_interval_ms);
        socket_->set(zmq::sockopt::reconnect_ivl_max, config_.max_reconnect_interval_ms);
        FIREWALL_LOG_DEBUG("Set socket option", "reconnect_ivl", config_.reconnect_interval_ms);
        FIREWALL_LOG_DEBUG("Set socket option", "reconnect_ivl_max", config_.max_reconnect_interval_ms);

    } catch (const zmq::error_t& e) {
        FIREWALL_LOG_CRASH("Failed to set socket options", "error", e.what());
        throw std::runtime_error(
            std::string("Failed to set socket options: ") + e.what()
        );
    }

    // Connect to endpoint
    try {
        socket_->connect(config_.endpoint);
        FIREWALL_LOG_INFO("Connected to endpoint", "endpoint", config_.endpoint);
    } catch (const zmq::error_t& e) {
        FIREWALL_LOG_CRASH("Failed to connect",
            "endpoint", config_.endpoint,
            "error", e.what());
        throw std::runtime_error(
            std::string("Failed to connect to ") + config_.endpoint + ": " + e.what()
        );
    }

    // Subscribe to topic
    try {
        socket_->set(zmq::sockopt::subscribe, config_.topic);
        FIREWALL_LOG_INFO("Subscribed to topic",
            "topic", config_.topic.empty() ? "(all)" : config_.topic);
    } catch (const zmq::error_t& e) {
        FIREWALL_LOG_CRASH("Failed to subscribe",
            "topic", config_.topic,
            "error", e.what());
        throw std::runtime_error(
            std::string("Failed to subscribe to topic '") +
            config_.topic + "': " + e.what()
        );
    }
}

void ZMQSubscriber::receive_loop() {
    FIREWALL_LOG_INFO("Entering receive loop");

    uint64_t messages_in_loop = 0;

    while (running_.load() &&
           firewall::diagnostics::g_system_state->is_running.load()) {
        try {
            TRACK_OPERATION("zmq_receive");

            // Receive message
            zmq::message_t message;
            auto result = socket_->recv(message, zmq::recv_flags::none);

            if (!result) {
                // Timeout or EAGAIN - check if we should stop
                if (!running_.load()) {
                    FIREWALL_LOG_DEBUG("Receive timed out, stopping flag set");
                    break;
                }
                continue;
            }

            // Update metrics
            size_t msg_size = message.size();
            messages_in_loop++;

            INCREMENT_COUNTER(zmq_recv_count);
            ADD_COUNTER(zmq_recv_bytes, msg_size);

            FIREWALL_LOG_DEBUG("ZMQ message received",
                "bytes", msg_size,
                "message_number", messages_in_loop);

            // Handle message
            if (msg_size > 0) {
                handle_message(message.data(), msg_size);
            } else {
                FIREWALL_LOG_WARN("Received empty message");
            }

            // Periodic state dump (every 1000 messages)
            if (messages_in_loop % 1000 == 0) {
                FIREWALL_LOG_INFO("Periodic checkpoint",
                    "messages_processed", messages_in_loop);
                DUMP_STATE_ON_ERROR("periodic_checkpoint");
            }

        } catch (const zmq::error_t& e) {
            // Check for specific error codes
            if (e.num() == ETERM) {
                // Context terminated
                FIREWALL_LOG_WARN("ZMQ context terminated");
                break;
            } else if (e.num() == EAGAIN) {
                // Timeout - check stop flag
                if (!running_.load()) {
                    FIREWALL_LOG_DEBUG("Timeout with stop flag set");
                    break;
                }
                continue;
            } else {
                // Other ZMQ error - rethrow to trigger reconnect
                FIREWALL_LOG_ERROR("ZMQ error in receive loop",
                    "error", e.what(),
                    "errno", e.num());
                throw;
            }
        } catch (const std::exception& e) {
            FIREWALL_LOG_ERROR("Exception in receive loop", "error", e.what());
            DUMP_STATE_ON_ERROR("receive_loop_exception");
            INCREMENT_COUNTER(events_dropped);
        }
    }

    FIREWALL_LOG_INFO("Exiting receive loop",
        "total_messages", messages_in_loop);
}

void ZMQSubscriber::handle_message(const void* msg_data, size_t msg_size) {
    TRACK_OPERATION("handle_message");

    const uint8_t* data_ptr = static_cast<const uint8_t*>(msg_data);
    size_t data_size = msg_size;

    // If we have a topic filter, skip the topic prefix
    // ZMQ PUB/SUB sends: [TOPIC][DATA]
    if (!config_.topic.empty()) {
        size_t topic_len = config_.topic.length();

        if (msg_size > topic_len &&
            std::memcmp(data_ptr, config_.topic.c_str(), topic_len) == 0) {

            data_ptr += topic_len;
            data_size -= topic_len;

            FIREWALL_LOG_DEBUG("Skipped topic prefix",
                "topic_bytes", topic_len,
                "data_bytes", data_size);
        }
    }

    // Copy to vector for decrypt/decompress
    std::vector<uint8_t> data(data_ptr, data_ptr + data_size);
    size_t original_size = data_size;  // Store for logging

    try {
        // ═══════════════════════════════════════════════════════════════════
        // STEP 1 - Decrypt if enabled (Day 50: Enhanced logging)
        // ═══════════════════════════════════════════════════════════════════
        if (config_.encryption_enabled) {
            TRACK_OPERATION("decrypt");

            auto start = std::chrono::high_resolution_clock::now();

            FIREWALL_LOG_DEBUG("Starting decryption",
                "input_bytes", original_size);

            // ADR-013 PHASE 2 — DAY 159: usar rx_ (CryptoTransport via SeedClient)
            // DEBT-FIREWALL-CRYPTO-FORMAT-001 FIX: crypto_token deprecated desde DAY 98
            if (!rx_) {
                throw std::runtime_error("CryptoTransport rx_ not initialized");
            }
            auto dr = rx_->decrypt_v2(data);  // FASE 3: extrae epoch_id
            data = std::move(dr.data);
            FIREWALL_LOG_DEBUG("epoch_id recibido", "epoch_id", dr.epoch_id);

            auto end = std::chrono::high_resolution_clock::now();
            auto duration = std::chrono::duration_cast<std::chrono::microseconds>(end - start);

            FIREWALL_LOG_DEBUG("Decryption completed",
                "duration_us", duration.count(),
                "input_bytes", original_size,
                "output_bytes", data.size(),
                "compression_ratio", static_cast<double>(original_size) / data.size());

            original_size = data.size();  // Update for decompress
        }

        // ═══════════════════════════════════════════════════════════════════
        // STEP 2 - Decompress if enabled (Day 50: Enhanced logging)
        // ═══════════════════════════════════════════════════════════════════
        if (config_.compression_enabled) {
            TRACK_OPERATION("decompress");

            auto start = std::chrono::high_resolution_clock::now();

            FIREWALL_LOG_DEBUG("Starting decompression",
                "input_bytes", data.size());

            // Validate minimum size (4-byte header + at least 1 byte data)
            if (data.size() < 5) {
                FIREWALL_LOG_ERROR("Compressed data too small",
                    "size", data.size(),
                    "minimum_required", 5);
                throw std::runtime_error("Compressed data too small (need 4-byte header + data)");
            }

            // Extract original size from 4-byte little-endian header
            // DAY 159 FIX: DEBT-FIREWALL-CRYPTO-FORMAT-001
            // ml-detector escribe LE (memcpy de uint32_t en x86)
            // El firewall leía BE → 0xBD020000 = 3171024896 → crash
            uint32_t decompressed_size = 0;
            std::memcpy(&decompressed_size, data.data(), sizeof(uint32_t));

            FIREWALL_LOG_DEBUG("Extracted decompression size from header",
                "decompressed_size", decompressed_size);

            // Sanity check: original size should be reasonable (< 100MB)
            if (decompressed_size > 100 * 1024 * 1024) {
                FIREWALL_LOG_ERROR("Invalid decompressed size",
                    "size", decompressed_size,
                    "max_allowed", 100 * 1024 * 1024);
                throw std::runtime_error("Invalid decompressed size in header: " +
                                       std::to_string(decompressed_size) + " bytes (>100MB)");
            }

            // Remove 4-byte header and prepare compressed data
            std::vector<uint8_t> compressed_only(data.begin() + 4, data.end());
            size_t compressed_size = compressed_only.size();

            // Decompress using static function with EXACT size
            data = crypto_transport::decompress(compressed_only, decompressed_size);

            auto end = std::chrono::high_resolution_clock::now();
            auto duration = std::chrono::duration_cast<std::chrono::microseconds>(end - start);

            FIREWALL_LOG_DEBUG("Decompression completed",
                "duration_us", duration.count(),
                "compressed_bytes", compressed_size,
                "decompressed_bytes", data.size(),
                "expansion_ratio", static_cast<double>(data.size()) / compressed_size);
        }

    } catch (const std::exception& e) {
        FIREWALL_LOG_ERROR("Decrypt/decompress failed",
            "error", e.what(),
            "original_size", original_size);
        DUMP_STATE_ON_ERROR("crypto_transport_error");
        stats_.parse_errors++;
        INCREMENT_COUNTER(events_dropped);
        return;
    }

    // ═══════════════════════════════════════════════════════════════════
    // STEP 3 - Parse NetworkSecurityEvent protobuf (Day 50: Enhanced)
    // ═══════════════════════════════════════════════════════════════════

    protobuf::NetworkSecurityEvent event;

    try {
        TRACK_OPERATION("protobuf_parse");

        FIREWALL_LOG_DEBUG("Parsing protobuf",
            "bytes", data.size());

        if (!event.ParseFromArray(data.data(), static_cast<int>(data.size()))) {
            FIREWALL_LOG_ERROR("Protobuf parse failed",
                "bytes", data.size());
            stats_.parse_errors++;
            INCREMENT_COUNTER(events_dropped);
            return;
        }

        FIREWALL_LOG_DEBUG("Protobuf parsed successfully",
            "has_ml_analysis", event.has_ml_analysis(),
            "has_network_features", event.has_network_features(),
            "threat_category", event.threat_category());

    } catch (const std::exception& e) {
        FIREWALL_LOG_ERROR("Exception parsing protobuf",
            "error", e.what(),
            "bytes", data.size());
        stats_.parse_errors++;
        INCREMENT_COUNTER(events_dropped);
        return;
    }

    stats_.messages_received++;
    INCREMENT_COUNTER(events_processed);

    // ═══════════════════════════════════════════════════════════════════
    // STEP 4 - Validate and extract data (Day 50: Enhanced)
    // ═══════════════════════════════════════════════════════════════════

    // Check if event has ML analysis
    if (!event.has_ml_analysis()) {
        FIREWALL_LOG_DEBUG("Event missing ML analysis, skipping");
        return;
    }

    const auto& ml = event.ml_analysis();

    // Only process if attack was detected at Level 1
    if (!ml.attack_detected_level1()) {
        FIREWALL_LOG_DEBUG("No Level 1 attack detected, skipping",
            "level1_confidence", ml.level1_confidence());
        return;
    }

    // Extract source IP from network_features
    if (!event.has_network_features()) {
        FIREWALL_LOG_WARN("Event missing network_features");
        return;
    }

    const auto& nf = event.network_features();
    if (nf.source_ip().empty()) {
        FIREWALL_LOG_WARN("Event missing source_ip");
        return;
    }

    // ═══════════════════════════════════════════════════════════════════
    // STEP 5 - Determine action based on threat category (Day 50: Enhanced)
    // ═══════════════════════════════════════════════════════════════════

    std::string ipset_name = "ml_defender_blacklist_test";
    int timeout_sec = 300;  // 5 minutes default

    std::string threat_cat = event.threat_category();

    if (threat_cat == "DDOS") {
        timeout_sec = 600;  // DDoS: 10 minutes
    } else if (threat_cat == "RANSOMWARE") {
        timeout_sec = 3600; // Ransomware: 1 hour
    }

    FIREWALL_LOG_INFO("Processing threat event",
        "source_ip", nf.source_ip(),
        "threat_category", threat_cat,
        "confidence", ml.level1_confidence(),
        "timeout_sec", timeout_sec);

    // Create detection for BatchProcessor
    std::vector<protobuf::Detection> detections;
    protobuf::Detection detection;

    detection.set_src_ip(nf.source_ip());

    // Set detection type based on threat category
    if (threat_cat == "DDOS") {
        detection.set_type(protobuf::DetectionType::DETECTION_DDOS);
    } else if (threat_cat == "RANSOMWARE") {
        detection.set_type(protobuf::DetectionType::DETECTION_RANSOMWARE);
    } else if (threat_cat == "SUSPICIOUS_INTERNAL") {
        detection.set_type(protobuf::DetectionType::DETECTION_INTERNAL_THREAT);
    } else {
        detection.set_type(protobuf::DetectionType::DETECTION_SUSPICIOUS_TRAFFIC);
    }

    detection.set_confidence(ml.level1_confidence());
    detection.set_timestamp(event.event_timestamp().seconds());
    detection.set_description("Attack detected: " + threat_cat);

    detections.push_back(detection);

    // ═══════════════════════════════════════════════════════════════════
    // STEP 6 - Forward to BatchProcessor (Day 50: Enhanced)
    // ═══════════════════════════════════════════════════════════════════

    try {
        TRACK_OPERATION("batch_processor_forward");

        processor_.add_detections(detections);
        stats_.detections_processed += detections.size();

        FIREWALL_LOG_INFO("Forwarded to batch processor",
            "source_ip", nf.source_ip(),
            "threat_type", threat_cat,
            "confidence", ml.level1_confidence(),
            "detections_count", detections.size());

    } catch (const std::exception& e) {
        FIREWALL_LOG_ERROR("Error forwarding to batch processor",
            "error", e.what(),
            "source_ip", nf.source_ip());
        DUMP_STATE_ON_ERROR("batch_processor_forward_error");
        return;  // Don't log if we didn't actually forward
    }

    // ═══════════════════════════════════════════════════════════════════
    // STEP 7 - Log blocked event (Day 50: Enhanced)
    // ═══════════════════════════════════════════════════════════════════

    try {
        TRACK_OPERATION("log_blocked_event");

        BlockedEvent log_event = create_blocked_event_from_proto(
            event,
            "BLOCKED",
            ipset_name,
            timeout_sec
        );

        bool logged = logger_->log_blocked_event(log_event);

        if (logged) {
            stats_.events_logged++;

            FIREWALL_LOG_INFO("Event logged successfully",
                "source_ip", nf.source_ip(),
                "log_directory", config_.log_directory,
                "timestamp_ms", log_event.timestamp_ms);
        } else {
            stats_.log_errors++;
            FIREWALL_LOG_WARN("Log queue full, event dropped",
                "source_ip", nf.source_ip(),
                "queue_size", logger_->queue_size());
        }

    } catch (const std::exception& e) {
        stats_.log_errors++;
        FIREWALL_LOG_ERROR("Error logging event",
            "error", e.what(),
            "source_ip", nf.source_ip());
        DUMP_STATE_ON_ERROR("logging_error");
    }

    // ═══════════════════════════════════════════════════════════════════
    // STEP 8 - Append to CSV log with HMAC signature (Day 59)
    // ═══════════════════════════════════════════════════════════════════

    if (hmac_key_.has_value()) {
        try {
            TRACK_OPERATION("append_csv_log");

            BlockedEvent log_event = create_blocked_event_from_proto(
                event,
                "BLOCKED",
                ipset_name,
                timeout_sec
            );

            logger_->append_csv_log(log_event, hmac_key_.value());

            FIREWALL_LOG_DEBUG("CSV log entry appended with HMAC",
                "source_ip", nf.source_ip());

        } catch (const std::exception& e) {
            FIREWALL_LOG_ERROR("Error appending CSV log",
                "error", e.what(),
                "source_ip", nf.source_ip());
        }
    }
}

void ZMQSubscriber::handle_reconnect() {
    stats_.reconnects++;

    FIREWALL_LOG_WARN("Connection lost, attempting reconnect",
        "reconnect_interval_ms", current_reconnect_interval_ms_,
        "attempt_number", stats_.reconnects.load());

    // Sleep for backoff interval
    std::this_thread::sleep_for(
        std::chrono::milliseconds(current_reconnect_interval_ms_)
    );

    // Exponential backoff (double interval, up to max)
    uint32_t new_interval = std::min(
        current_reconnect_interval_ms_ * 2,
        config_.max_reconnect_interval_ms
    );

    FIREWALL_LOG_DEBUG("Updating reconnect interval",
        "old_interval_ms", current_reconnect_interval_ms_,
        "new_interval_ms", new_interval);

    current_reconnect_interval_ms_ = new_interval;
}

void ZMQSubscriber::reset_reconnect_backoff() {
    if (current_reconnect_interval_ms_ != config_.reconnect_interval_ms) {
        FIREWALL_LOG_DEBUG("Resetting reconnect backoff",
            "from_ms", current_reconnect_interval_ms_,
            "to_ms", config_.reconnect_interval_ms);

        current_reconnect_interval_ms_ = config_.reconnect_interval_ms;
    }
}

} // namespace firewall
} // namespace mldefender