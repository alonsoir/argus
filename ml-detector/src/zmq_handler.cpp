#include "csv_event_writer.hpp"
#include <crypto_transport/contexts.hpp>
#include <filesystem>
#include <reason_codes.hpp>
#include "zmq_handler.hpp"
#include "rag_logger.hpp"
#include "contract_validator.h"
#include <spdlog/sinks/stdout_color_sinks.h>
#include <chrono>
#include <sstream>
#include <unistd.h>
#include <cstdio>

namespace ml_detector {

ZMQHandler::ZMQHandler(
    const DetectorConfig& config,
    std::shared_ptr<ONNXModel> level1_model,
    std::shared_ptr<FeatureExtractor> extractor,
    std::shared_ptr<ml_defender::DDoSDetector> ddos_detector,
    std::shared_ptr<ml_defender::RansomwareDetector> ransomware_detector,
    std::shared_ptr<ml_defender::TrafficDetector> traffic_detector,
    std::shared_ptr<ml_defender::InternalDetector> internal_detector,
    // DEPRECATED DAY 98 — crypto_manager eliminado (ADR-013)
    std::string hmac_key_hex
)
    : config_(config)
    , level1_model_(level1_model)
    , ddos_detector_(ddos_detector)
    , ransomware_detector_(ransomware_detector)
    , traffic_detector_(traffic_detector)
    , internal_detector_(internal_detector)
    , extractor_(extractor)
    , context_(1)
    , running_(false)
    , last_stats_report_(std::chrono::steady_clock::now())
    , logger_(spdlog::get("ml-detector"))
    , start_time_(std::chrono::system_clock::now())
    // DEPRECATED DAY 98 — crypto_manager ignorado
    , hmac_key_hex_(std::move(hmac_key_hex))
{
    if (!logger_) {
        logger_ = spdlog::stdout_color_mt("zmq-handler");
    }

    logger_->info("🔌 Initializing ZMQ Handler");

    // ADR-013 PHASE 2 — DAY 98: inicializar CryptoTransport via SeedClient
    try {
        seed_client_ = std::make_unique<ml_defender::SeedClient>(
            "/etc/ml-defender/ml-detector/ml_detector_config.json");
        seed_client_->load();
        tx_ = std::make_unique<crypto_transport::CryptoTransport>(
            *seed_client_, ml_defender::crypto::CTX_ML_TO_FIREWALL);
        rx_ = std::make_unique<crypto_transport::CryptoTransport>(
            *seed_client_, ml_defender::crypto::CTX_SNIFFER_TO_ML);
        logger_->info("🔐 CryptoTransport inicializado (HKDF-SHA256 + ChaCha20-Poly1305)");
    } catch (const std::exception& e) {
        logger_->error("❌ CryptoTransport init failed: {}", e.what());
        throw;
    }

    // Log detector status
    logger_->info("📊 ML Detectors loaded:");
    logger_->info("   Level 1: General Attack (ONNX)");
    if (ddos_detector_) {
        logger_->info("   Level 2: DDoS ({} trees, {} features)",
                     ddos_detector_->num_trees(), ddos_detector_->num_features());
    }
    if (ransomware_detector_) {
        logger_->info("   Level 2: Ransomware ({} trees, {} features)",
                     ransomware_detector_->num_trees(), ransomware_detector_->num_features());
    }
    if (traffic_detector_) {
        logger_->info("   Level 3: Traffic ({} trees, {} features)",
                     traffic_detector_->num_trees(), traffic_detector_->num_features());
    }
    if (internal_detector_) {
        logger_->info("   Level 3: Internal ({} trees, {} features)",
                     internal_detector_->num_trees(), internal_detector_->num_features());
    }

    // ZMQ sockets
    try {
        input_socket_ = std::make_unique<zmq::socket_t>(context_, zmq::socket_type::pull);
        int hwm = config_.network.input_socket.high_water_mark;
        input_socket_->set(zmq::sockopt::rcvhwm, hwm);
        input_socket_->set(zmq::sockopt::linger, config_.zmq.connection_settings.linger_ms);

        if (config_.network.input_socket.mode == "connect") {
            logger_->info("   Input: PULL connect {}", config_.network.input_socket.endpoint);
            input_socket_->connect(config_.network.input_socket.endpoint);
        } else {
            logger_->info("   Input: PULL bind {}", config_.network.input_socket.endpoint);
            input_socket_->bind(config_.network.input_socket.endpoint);
        }

        output_socket_ = std::make_unique<zmq::socket_t>(context_, zmq::socket_type::pub);
        hwm = config_.network.output_socket.high_water_mark;
        output_socket_->set(zmq::sockopt::sndhwm, hwm);
        output_socket_->set(zmq::sockopt::linger, config_.zmq.connection_settings.linger_ms);

        if (config_.network.output_socket.mode == "connect") {
            logger_->info("   Output: PUB connect {}", config_.network.output_socket.endpoint);
            output_socket_->connect(config_.network.output_socket.endpoint);
        } else {
            logger_->info("   Output: PUB bind {}", config_.network.output_socket.endpoint);
            output_socket_->bind(config_.network.output_socket.endpoint);
        }

        logger_->info("✅ ZMQ sockets initialized successfully");

    } catch (const zmq::error_t& e) {
        logger_->error("❌ ZMQ initialization failed: {}", e.what());
        throw;
    }

    // =========================================================================
    // Day 66: CsvEventWriter — standalone, NO depende del RAG Logger
    // Política: CSV activo siempre que haya HMAC key, independientemente del RAG
    // =========================================================================
    if (!hmac_key_hex_.empty()) {
        try {
            std::string csv_dir = config_.csv_writer.base_dir;
            std::filesystem::create_directories(csv_dir);

            ml_defender::CsvEventWriterConfig csv_cfg;
            csv_cfg.base_dir            = csv_dir;
            csv_cfg.hmac_key_hex        = hmac_key_hex_;
            csv_cfg.max_events_per_file = static_cast<size_t>(config_.csv_writer.max_events_per_file);
            csv_cfg.min_score_threshold = config_.csv_writer.min_score_threshold;

			csv_writer_ = std::make_shared<ml_defender::CsvEventWriter>(csv_cfg, logger_);

            logger_->info("✅ CsvEventWriter initialized (standalone)");
            logger_->info("   Output: {}/YYYY-MM-DD.csv", csv_dir);
            logger_->info("   Threshold: {:.2f}", csv_cfg.min_score_threshold);
            logger_->info("   Columns: {} (14 meta + 105 features + 1 hmac)",
                         ml_defender::CSV_TOTAL_COLS);

        } catch (const std::exception& e) {
            logger_->error("❌ Failed to initialize CsvEventWriter: {}", e.what());
            logger_->warn("⚠️  Continuing without CSV output");
            csv_writer_ = nullptr;
        }
    } else {
        logger_->warn("⚠️  CsvEventWriter disabled — no HMAC key available");
    }

    // =========================================================================
    // RAG Logger — opcional, su fallo no afecta al CSV
    // =========================================================================
    try {
        rag_logger_ = ml_defender::create_rag_logger_from_config(
            "../config/rag_logger_config.json",
            logger_
            // DEPRECATED DAY 98 — crypto_manager eliminado
        );
		logger_->info("✅ RAG Logger initialized successfully (encrypted artifacts enabled)");
		if (csv_writer_) {
    		rag_logger_->set_csv_writer(csv_writer_);
		}
        // Si RAG Logger está disponible, comparte el csv_writer con él
        // Nota: RAG Logger no toma ownership — csv_writer_ sigue siendo el owner
        // Se pasa una referencia lógica; RAG Logger escribe a través de él
        // (set_csv_writer toma unique_ptr — ver nota abajo)

    } catch (const std::exception& e) {
        logger_->error("❌ Failed to initialize RAG Logger: {}", e.what());
        logger_->warn("⚠️  Continuing without RAG logging (CSV still active)");
        rag_logger_ = nullptr;
    }
}

ZMQHandler::~ZMQHandler() {
    stop();

    // Flush CSV antes de destruir
    if (csv_writer_) {
        logger_->info("🔄 Flushing CsvEventWriter...");
        csv_writer_->flush();
    }

    if (rag_logger_) {
        logger_->info("🔄 Flushing RAG logger...");
        rag_logger_->flush();
        auto stats = rag_logger_->get_statistics();
        logger_->info("📊 RAG Statistics: {}", stats.dump(2));
    }
}

void ZMQHandler::start() {
    if (running_.load()) {
        logger_->warn("ZMQ Handler already running");
        return;
    }

    logger_->info("🚀 Starting ZMQ Handler");
    running_.store(true);
    worker_thread_ = std::make_unique<std::thread>(&ZMQHandler::run, this);
    logger_->info("✅ ZMQ Handler started");
}

void ZMQHandler::stop() {
    if (!running_.load()) {
        return;
    }

    logger_->info("🛑 Stopping ZMQ Handler...");
    running_.store(false);

    if (worker_thread_ && worker_thread_->joinable()) {
        worker_thread_->join();
    }
    if (input_socket_)  input_socket_->close();
    if (output_socket_) output_socket_->close();

    logger_->info("✅ ZMQ Handler stopped");
}

void ZMQHandler::run() {
    logger_->info("📥 ZMQ Handler loop started");

    auto stats_interval = std::chrono::seconds(config_.monitoring.stats_interval_seconds);

    while (running_.load()) {
        try {
            zmq::message_t encrypted_message;
            auto result = input_socket_->recv(encrypted_message, zmq::recv_flags::dontwait);

            if (result) {
                std::string encrypted_data(
                    static_cast<char*>(encrypted_message.data()),
                    encrypted_message.size()
                );

                {
                    std::lock_guard<std::mutex> lock(stats_mutex_);
                    stats_.events_received++;
                }

                try {
                    // ADR-013 PHASE 2 — DAY 98: decrypt + LZ4 decompress
                    std::vector<uint8_t> cipher_bytes(encrypted_data.begin(), encrypted_data.end());
                    auto plain_bytes = rx_->decrypt(cipher_bytes);

                    // LZ4 decompress: cabecera [uint32_t orig_size LE] + datos
                    std::string decompressed;
                    if (plain_bytes.size() > sizeof(uint32_t)) {
                        uint32_t orig_size = 0;
                        std::memcpy(&orig_size, plain_bytes.data(), sizeof(orig_size));
                        decompressed.resize(orig_size);
                        int result = LZ4_decompress_safe(
                            reinterpret_cast<const char*>(plain_bytes.data() + sizeof(uint32_t)),
                            decompressed.data(),
                            static_cast<int>(plain_bytes.size() - sizeof(uint32_t)),
                            static_cast<int>(orig_size)
                        );
                        if (result < 0) {
                            // Sin cabecera LZ4 — asumir sin compresión
                            decompressed = std::string(plain_bytes.begin(), plain_bytes.end());
                        }
                    } else {
                        decompressed = std::string(plain_bytes.begin(), plain_bytes.end());
                    }

                    logger_->trace("🔓 Decrypted: {} → {} bytes", encrypted_data.size(), decompressed.size());
                    process_event(decompressed);

                } catch (const std::exception& e) {
                    logger_->error("❌ Decryption/decompression failed: {}", e.what());
                    std::lock_guard<std::mutex> lock(stats_mutex_);
                    stats_.deserialization_errors++;
                }

            } else {
                std::this_thread::sleep_for(std::chrono::milliseconds(1));
            }

            // Stats report
            auto now = std::chrono::steady_clock::now();
            if (now - last_stats_report_ >= stats_interval) {
                auto stats = get_stats();
                logger_->info("📊 Stats: received={}, processed={}, sent={}, attacks={}, "
                             "errors=(deser:{}, feat:{}, inf:{})",
                             stats.events_received, stats.events_processed, stats.events_sent,
                             stats.attacks_detected, stats.deserialization_errors,
                             stats.feature_extraction_errors, stats.inference_errors);
                last_stats_report_ = now;
            }

        } catch (const zmq::error_t& e) {
            if (e.num() == ETERM) break;
            logger_->error("ZMQ error: {}", e.what());
            std::this_thread::sleep_for(std::chrono::milliseconds(100));
        } catch (const std::exception& e) {
            logger_->error("Unexpected error: {}", e.what());
            std::this_thread::sleep_for(std::chrono::milliseconds(100));
        }
    }

    logger_->info("📥 ZMQ Handler loop stopped");
}

void ZMQHandler::process_event(const std::string& message) {
    auto start_time = std::chrono::steady_clock::now();

    try {
        // Deserialization
        protobuf::NetworkSecurityEvent event;
        if (!event.ParseFromString(message)) {
            logger_->error("Failed to deserialize protobuf message");
            std::lock_guard<std::mutex> lock(stats_mutex_);
            stats_.deserialization_errors++;
            return;
        }

        logger_->debug("📦 Event received: id={}", event.event_id());

        // Contract validation (Day 48)
        static std::atomic<uint64_t> event_counter{0};
        event_counter++;

        int feature_count = mldefender::ContractValidator::count_features(event);
        mldefender::g_contract_stats.record(feature_count);
        mldefender::g_contract_stats.log_progress(event_counter.load());

        static std::atomic<uint64_t> violations_logged{0};
        if (feature_count < 100 && violations_logged.load() < 10) {
            mldefender::ContractValidator::log_missing_features(event, event_counter.load());
            violations_logged++;
        }

        // Fast detector score
        double fast_score   = event.fast_detector_score();
        bool fast_triggered = event.fast_detector_triggered();
        std::string fast_reason = event.fast_detector_reason();

        logger_->debug("🎯 Fast Detector: score={:.4f}, triggered={}, reason={}",
                       fast_score, fast_triggered, fast_reason);

        // Level 1: General Attack Detection (ONNX)
        std::vector<float> features_l1;
        try {
            features_l1 = extractor_->extract_level1_features(event);
            if (!extractor_->validate_features(features_l1)) {
                logger_->error("Feature validation failed for event {}", event.event_id());
                std::lock_guard<std::mutex> lock(stats_mutex_);
                stats_.feature_extraction_errors++;
                return;
            }
        } catch (const std::exception& e) {
            logger_->error("Level 1 feature extraction failed: {}", e.what());
            std::lock_guard<std::mutex> lock(stats_mutex_);
            stats_.feature_extraction_errors++;
            return;
        }

        int64_t label_l1      = -1;
        float confidence_l1   = 0.0f;

        try {
            auto [pred_label, pred_confidence] = level1_model_->predict(features_l1);
            label_l1      = pred_label;
            confidence_l1 = pred_confidence;

            logger_->debug("🤖 Level 1: label={} ({}), confidence={:.4f}",
                          label_l1, (label_l1 == 0 ? "BENIGN" : "ATTACK"), confidence_l1);

        } catch (const std::exception& e) {
            logger_->error("Level 1 inference failed: {}", e.what());
            std::lock_guard<std::mutex> lock(stats_mutex_);
            stats_.inference_errors++;
            return;
        }

        // Enrich with Level 1
        auto* ml_analysis  = event.mutable_ml_analysis();
        auto* level1_pred  = ml_analysis->mutable_level1_general_detection();
        level1_pred->set_model_name("level1_attack_detector");
        level1_pred->set_model_version("1.0.0");
        level1_pred->set_model_type(protobuf::ModelPrediction::RANDOM_FOREST_GENERAL);
        level1_pred->set_prediction_class(label_l1 == 0 ? "BENIGN" : "ATTACK");
        level1_pred->set_confidence_score(confidence_l1);

        ml_analysis->set_attack_detected_level1(label_l1 == 1);
        ml_analysis->set_level1_confidence(confidence_l1);

        // Dual-Score Architecture
        double ml_score    = label_l1 == 1 ? confidence_l1 : (1.0 - confidence_l1);
        event.set_ml_detector_score(ml_score);

        double final_score = std::max(fast_score, ml_score);
        event.set_overall_threat_score(final_score);

        double score_divergence = std::abs(fast_score - ml_score);

        if (score_divergence > config_.scoring.divergence_warn_threshold) {
            event.set_authoritative_source(protobuf::DETECTOR_SOURCE_DIVERGENCE);
            logger_->warn("⚠️  Score divergence: fast={:.4f}, ml={:.4f}, diff={:.4f}",
                          fast_score, ml_score, score_divergence);
        } else if (fast_triggered && ml_score > 0.5) {
            event.set_authoritative_source(protobuf::DETECTOR_SOURCE_CONSENSUS);
        } else if (fast_score > ml_score) {
            event.set_authoritative_source(protobuf::DETECTOR_SOURCE_FAST_PRIORITY);
        } else {
            event.set_authoritative_source(protobuf::DETECTOR_SOURCE_ML_PRIORITY);
        }

        auto* metadata = event.mutable_decision_metadata();
        metadata->set_score_divergence(score_divergence);
        metadata->set_requires_rag_analysis(
            score_divergence > config_.scoring.divergence_warn_threshold ||
            final_score >= config_.scoring.requires_rag_threshold
        );
        metadata->set_confidence_level(std::min(fast_score, ml_score));

        logger_->info("[DUAL-SCORE] event={}, fast={:.4f}, ml={:.4f}, final={:.4f}, source={}, div={:.4f}",
                      event.event_id(), fast_score, ml_score, final_score,
                      protobuf::DetectorSource_Name(event.authoritative_source()),
                      score_divergence);

        event.set_final_classification(
            final_score >= config_.scoring.malicious_threshold ? "MALICIOUS" : "BENIGN"
        );

        // Provenance (ADR-002)
        auto* provenance = event.mutable_provenance();
        bool sniffer_verdict_exists = (provenance->verdicts_size() > 0);

        if (sniffer_verdict_exists) {
            logger_->debug("📊 Provenance: Sniffer verdict exists, adding ML verdict");
        }

        auto* rf_verdict = provenance->add_verdicts();
        rf_verdict->set_engine_name("random-forest-level1");
        rf_verdict->set_classification(label_l1 == 0 ? "Benign" : "Attack");
        rf_verdict->set_confidence(confidence_l1);
        rf_verdict->set_reason_code(
            label_l1 == 1
                ? ml_defender::to_string(ml_defender::ReasonCode::STAT_ANOMALY)
                : ml_defender::to_string(ml_defender::ReasonCode::UNKNOWN)
        );
        rf_verdict->set_timestamp_ns(
            static_cast<uint64_t>(std::chrono::duration_cast<std::chrono::nanoseconds>(
                std::chrono::system_clock::now().time_since_epoch()
            ).count())
        );

        float discrepancy = 0.0f;
        if (sniffer_verdict_exists) {
            const auto& sniffer_v = provenance->verdicts(0);
            discrepancy = std::abs(sniffer_v.confidence() - static_cast<float>(ml_score));
            logger_->debug("📊 Provenance discrepancy: sniffer={:.4f}, ml={:.4f}, diff={:.4f}",
                          sniffer_v.confidence(), ml_score, discrepancy);
        }

        provenance->set_discrepancy_score(discrepancy);
        provenance->set_global_timestamp_ns(
            static_cast<uint64_t>(std::chrono::duration_cast<std::chrono::nanoseconds>(
                std::chrono::system_clock::now().time_since_epoch()
            ).count())
        );
        provenance->set_final_decision(
            final_score >= config_.scoring.malicious_threshold ? "DROP" : "ALLOW"
        );

        if (score_divergence > config_.scoring.divergence_warn_threshold) {
            provenance->set_discrepancy_reason(
                "Fast detector and ML detector disagree (divergence: " +
                std::to_string(score_divergence) + ")"
            );
        }

        // =====================================================================
        // RAG Logging (opcional — csv_writer_ funciona aunque rag_logger_ sea null)
        // =====================================================================
        ml_defender::MLContext ml_context;

        ml_context.events_processed_total  = ++events_processed_total_;
        ml_context.events_in_last_minute   = calculate_events_per_minute();
        ml_context.memory_usage_mb         = get_memory_usage_mb();
        ml_context.cpu_usage_percent       = 0.0;
        ml_context.uptime_seconds          = static_cast<uint64_t>(std::chrono::duration_cast<std::chrono::seconds>(
            std::chrono::system_clock::now() - start_time_
        ).count());

        ml_context.attack_family           = "RANSOMWARE";  // TODO: Get from detector
        ml_context.level_1_label           = label_l1 == 1 ? "MALICIOUS" : "BENIGN";
        ml_context.level_2_category        = "UNKNOWN";
        ml_context.level_3_subcategory     = "UNKNOWN";
        ml_context.level_1_confidence      = confidence_l1;

        ml_context.window_start            = std::chrono::system_clock::now() - std::chrono::seconds(30);
        ml_context.window_end              = std::chrono::system_clock::now();
        ml_context.events_in_window        = 1;

        if (score_divergence > config_.scoring.divergence_high_threshold) {
            ml_context.investigation_priority = "HIGH";
        } else if (score_divergence > config_.scoring.divergence_warn_threshold) {
            ml_context.investigation_priority = "MEDIUM";
        } else {
            ml_context.investigation_priority = "LOW";
        }

        // RAG Logger — escribe JSON artifacts + delega en csv_writer_ si fue conectado
        if (rag_logger_) {
            bool logged = rag_logger_->log_event(event, ml_context);
            if (logged) {
                logger_->debug("📝 Event logged to RAG: {}", event.event_id());
            }
        }

        // =====================================================================
        // Day 66: CSV standalone — activo aunque rag_logger_ sea null
        // Escribe directamente si rag_logger_ no está disponible
        // =====================================================================
        if (!rag_logger_ && csv_writer_) {
            bool written = csv_writer_->write_event(event);
            if (written) {
                logger_->debug("📝 Event written to CSV (standalone): {}", event.event_id());
            }
        }

        // Level 2 & 3: Specialized detectors (si Level 1 detectó ATTACK)
        if (label_l1 == 1 && confidence_l1 >= config_.ml.thresholds.level1_attack) {
            event.set_threat_category("ATTACK");

            {
                std::lock_guard<std::mutex> lock(stats_mutex_);
                stats_.attacks_detected++;
            }

            // Level 2: DDoS
            if (ddos_detector_ && config_.ml.level2.ddos.enabled) {
                try {
                    logger_->debug("🔍 Running Level 2 DDoS classification...");

                    if (!event.has_network_features()) {
                        logger_->error("❌ Event {} missing network_features, skipping Level 2 DDoS",
                                      event.event_id());
                    } else {
                        const auto& nf = event.network_features();

                        std::vector<float> ddos_features_vec;
                        try {
                            ddos_features_vec = extractor_->extract_level2_ddos_features(nf);
                            if (ddos_features_vec.size() != 10) {
                                throw std::runtime_error("Invalid DDoS feature count");
                            }
                            logger_->debug("   DDoS Features: syn_ack={:.3f}, entropy={:.3f}, amp={:.3f}",
                                          ddos_features_vec[0], ddos_features_vec[4], ddos_features_vec[5]);
                        } catch (const std::exception& e) {
                            logger_->error("❌ DDoS feature extraction failed: {}", e.what());
                            std::lock_guard<std::mutex> lock(stats_mutex_);
                            stats_.feature_extraction_errors++;
                            throw;
                        }

                        ml_defender::DDoSDetector::Features ddos_features{
                            .syn_ack_ratio              = ddos_features_vec[0],
                            .packet_symmetry            = ddos_features_vec[1],
                            .source_ip_dispersion       = ddos_features_vec[2],
                            .protocol_anomaly_score     = ddos_features_vec[3],
                            .packet_size_entropy        = ddos_features_vec[4],
                            .traffic_amplification_factor = ddos_features_vec[5],
                            .flow_completion_rate       = ddos_features_vec[6],
                            .geographical_concentration = ddos_features_vec[7],
                            .traffic_escalation_rate    = ddos_features_vec[8],
                            .resource_saturation_score  = ddos_features_vec[9]
                        };

                        auto ddos_result = ddos_detector_->predict(ddos_features);
                        logger_->debug("🤖 DDoS: class={} ({}), conf={:.4f}",
                                      ddos_result.class_id,
                                      (ddos_result.class_id == 0 ? "NORMAL" : "DDOS"),
                                      ddos_result.probability);

                        auto* level2_ddos_pred = ml_analysis->add_level2_specialized_predictions();
                        level2_ddos_pred->set_model_name("ddos_detector_embedded_cpp20");
                        level2_ddos_pred->set_model_version("1.0.0");
                        level2_ddos_pred->set_model_type(protobuf::ModelPrediction::RANDOM_FOREST_DDOS);
                        level2_ddos_pred->set_prediction_class(
                            ddos_result.class_id == 0 ? "NORMAL" : "DDOS"
                        );
                        level2_ddos_pred->set_confidence_score(ddos_result.ddos_prob);

                        if (ddos_result.is_ddos(config_.ml.thresholds.level2_ddos)) {
                            event.set_threat_category("DDOS");
                            ml_analysis->set_final_threat_classification("DDOS");
                            logger_->warn("🔴 DDoS ATTACK: event={}, L1={:.2f}%, L2={:.2f}%",
                                         event.event_id(), confidence_l1 * 100, ddos_result.ddos_prob * 100);
                        }
                    }
                } catch (const std::exception& e) {
                    logger_->error("❌ Level 2 DDoS processing failed: {}", e.what());
                    std::lock_guard<std::mutex> lock(stats_mutex_);
                    stats_.inference_errors++;
                }
            }

            // Level 2: Ransomware
            if (ransomware_detector_ && config_.ml.level2.ransomware.enabled) {
                try {
                    logger_->debug("🔍 Running Level 2 Ransomware classification...");

                    if (!event.has_network_features()) {
                        logger_->error("❌ Event {} missing network_features, skipping Ransomware",
                                      event.event_id());
                    } else {
                        const auto& nf = event.network_features();

                        std::vector<float> ransomware_features_vec;
                        try {
                            ransomware_features_vec = extractor_->extract_level2_ransomware_features(nf);
                            if (ransomware_features_vec.size() != 10) {
                                throw std::runtime_error("Invalid Ransomware feature count");
                            }
                            logger_->debug("   Ransomware Features: entropy={:.3f}, io={:.3f}, resource={:.3f}",
                                          ransomware_features_vec[1], ransomware_features_vec[0],
                                          ransomware_features_vec[2]);
                        } catch (const std::exception& e) {
                            logger_->error("❌ Ransomware feature extraction failed: {}", e.what());
                            std::lock_guard<std::mutex> lock(stats_mutex_);
                            stats_.feature_extraction_errors++;
                            throw;
                        }

                        ml_defender::RansomwareDetector::Features ransomware_features{
                            .io_intensity         = ransomware_features_vec[0],
                            .entropy              = ransomware_features_vec[1],
                            .resource_usage       = ransomware_features_vec[2],
                            .network_activity     = ransomware_features_vec[3],
                            .file_operations      = ransomware_features_vec[4],
                            .process_anomaly      = ransomware_features_vec[5],
                            .temporal_pattern     = ransomware_features_vec[6],
                            .access_frequency     = ransomware_features_vec[7],
                            .data_volume          = ransomware_features_vec[8],
                            .behavior_consistency = ransomware_features_vec[9]
                        };

                        auto ransomware_result = ransomware_detector_->predict(ransomware_features);
                        logger_->debug("🤖 Ransomware: class={} ({}), conf={:.4f}",
                                      ransomware_result.class_id,
                                      (ransomware_result.class_id == 0 ? "BENIGN" : "RANSOMWARE"),
                                      ransomware_result.probability);

                        auto* level2_ransomware_pred = ml_analysis->add_level2_specialized_predictions();
                        level2_ransomware_pred->set_model_name("ransomware_detector_embedded_cpp20");
                        level2_ransomware_pred->set_model_version("1.0.0");
                        level2_ransomware_pred->set_model_type(protobuf::ModelPrediction::RANDOM_FOREST_RANSOMWARE);
                        level2_ransomware_pred->set_prediction_class(
                            ransomware_result.class_id == 0 ? "BENIGN" : "RANSOMWARE"
                        );
                        level2_ransomware_pred->set_confidence_score(ransomware_result.ransomware_prob);

                        if (ransomware_result.is_ransomware(config_.ml.thresholds.level2_ransomware)) {
                            event.set_threat_category("RANSOMWARE");
                            ml_analysis->set_final_threat_classification("RANSOMWARE");
                            logger_->warn("🔴 RANSOMWARE ATTACK: event={}, L1={:.2f}%, L2={:.2f}%, entropy={:.3f}",
                                         event.event_id(), confidence_l1 * 100,
                                         ransomware_result.ransomware_prob * 100,
                                         ransomware_features_vec[1]);
                        }
                    }
                } catch (const std::exception& e) {
                    logger_->error("❌ Level 2 Ransomware processing failed: {}", e.what());
                    std::lock_guard<std::mutex> lock(stats_mutex_);
                    stats_.inference_errors++;
                }
            }

            // Level 3: Traffic Classification
            if (traffic_detector_ && config_.ml.level3.web.enabled) {
                try {
                    logger_->debug("🔍 Running Level 3 Traffic classification...");

                    if (!event.has_network_features()) {
                        logger_->error("❌ Event {} missing network_features, skipping Traffic",
                                      event.event_id());
                    } else {
                        const auto& nf = event.network_features();

                        std::vector<float> traffic_features_vec;
                        try {
                            traffic_features_vec = extractor_->extract_level3_traffic_features(nf);
                            if (traffic_features_vec.size() != 10) {
                                throw std::runtime_error("Invalid Traffic feature count");
                            }
                        } catch (const std::exception& e) {
                            logger_->error("❌ Traffic feature extraction failed: {}", e.what());
                            std::lock_guard<std::mutex> lock(stats_mutex_);
                            stats_.feature_extraction_errors++;
                            throw;
                        }

                        ml_defender::TrafficDetector::Features traffic_features{
                            .packet_rate           = traffic_features_vec[0],
                            .connection_rate       = traffic_features_vec[1],
                            .tcp_udp_ratio         = traffic_features_vec[2],
                            .avg_packet_size       = traffic_features_vec[3],
                            .port_entropy          = traffic_features_vec[4],
                            .flow_duration_std     = traffic_features_vec[5],
                            .src_ip_entropy        = traffic_features_vec[6],
                            .dst_ip_concentration  = traffic_features_vec[7],
                            .protocol_variety      = traffic_features_vec[8],
                            .temporal_consistency  = traffic_features_vec[9]
                        };

                        auto traffic_result = traffic_detector_->predict(traffic_features);
                        logger_->debug("🤖 Traffic: class={} ({}), conf={:.4f}",
                                      traffic_result.class_id,
                                      (traffic_result.class_id == 0 ? "INTERNET" : "INTERNAL"),
                                      traffic_result.probability);

                        auto* level3_traffic_pred = ml_analysis->add_level3_specialized_predictions();
                        level3_traffic_pred->set_model_name("traffic_detector_embedded_cpp20");
                        level3_traffic_pred->set_model_version("1.0.0");
                        level3_traffic_pred->set_prediction_class(
                            traffic_result.class_id == 0 ? "INTERNET" : "INTERNAL"
                        );
                        level3_traffic_pred->set_confidence_score(traffic_result.probability);

                        // Level 3: Internal
                        if (traffic_result.is_internal(config_.ml.thresholds.level3_web) &&
                            internal_detector_ && config_.ml.level3.internal.enabled) {

                            try {
                                logger_->debug("🔍 Running Level 3 Internal analysis...");

                                std::vector<float> internal_features_vec;
                                try {
                                    internal_features_vec = extractor_->extract_level3_internal_features(nf);
                                    if (internal_features_vec.size() != 10) {
                                        throw std::runtime_error("Invalid Internal feature count");
                                    }
                                } catch (const std::exception& e) {
                                    logger_->error("❌ Internal feature extraction failed: {}", e.what());
                                    std::lock_guard<std::mutex> lock(stats_mutex_);
                                    stats_.feature_extraction_errors++;
                                    throw;
                                }

                                ml_defender::InternalDetector::Features internal_features{
                                    .internal_connection_rate  = internal_features_vec[0],
                                    .service_port_consistency  = internal_features_vec[1],
                                    .protocol_regularity       = internal_features_vec[2],
                                    .packet_size_consistency   = internal_features_vec[3],
                                    .connection_duration_std   = internal_features_vec[4],
                                    .lateral_movement_score    = internal_features_vec[5],
                                    .service_discovery_patterns = internal_features_vec[6],
                                    .data_exfiltration_indicators = internal_features_vec[7],
                                    .temporal_anomaly_score    = internal_features_vec[8],
                                    .access_pattern_entropy    = internal_features_vec[9]
                                };

                                auto internal_result = internal_detector_->predict(internal_features);
                                logger_->debug("🤖 Internal: class={} ({}), conf={:.4f}",
                                              internal_result.class_id,
                                              (internal_result.class_id == 0 ? "BENIGN" : "SUSPICIOUS"),
                                              internal_result.probability);

                                auto* level3_internal_pred = ml_analysis->add_level3_specialized_predictions();
                                level3_internal_pred->set_model_name("internal_detector_embedded_cpp20");
                                level3_internal_pred->set_model_version("1.0.0");
                                level3_internal_pred->set_prediction_class(
                                    internal_result.class_id == 0 ? "BENIGN" : "SUSPICIOUS"
                                );
                                level3_internal_pred->set_confidence_score(internal_result.suspicious_prob);

                                if (internal_result.is_suspicious(config_.ml.thresholds.level3_internal)) {
                                    event.set_threat_category("SUSPICIOUS_INTERNAL");
                                    ml_analysis->set_final_threat_classification("SUSPICIOUS_INTERNAL");
                                    logger_->warn("🔴 SUSPICIOUS INTERNAL ACTIVITY: event={}, "
                                                 "lateral_movement={:.3f}, exfiltration={:.3f}, conf={:.2f}%",
                                                 event.event_id(),
                                                 internal_features_vec[5],
                                                 internal_features_vec[7],
                                                 internal_result.suspicious_prob * 100);
                                }

                            } catch (const std::exception& e) {
                                logger_->error("❌ Level 3 Internal processing failed: {}", e.what());
                                std::lock_guard<std::mutex> lock(stats_mutex_);
                                stats_.inference_errors++;
                            }
                        }
                    }
                } catch (const std::exception& e) {
                    logger_->error("❌ Level 3 Traffic processing failed: {}", e.what());
                    std::lock_guard<std::mutex> lock(stats_mutex_);
                    stats_.inference_errors++;
                }
            }

        } else {
            event.set_threat_category("NORMAL");
        }

        // ADR-012 PHASE 2d — invoke plugins post-inferencia (Consejo DAY 111)
        if (plugin_loader_ != nullptr) {
            std::string serialized = event.SerializeAsString();
            MessageContext ctx{};
            ctx.payload     = reinterpret_cast<const uint8_t*>(serialized.data());
            ctx.payload_len = serialized.size();
            ctx.mode        = PLUGIN_MODE_NORMAL;
            ctx.result_code = 0;
            // IPs son strings en protobuf — usar 0 (payload contiene el evento completo)
            ctx.src_ip      = 0;
            ctx.dst_ip      = 0;
            ctx.src_port    = static_cast<uint16_t>(event.network_features().source_port());
            ctx.dst_port    = static_cast<uint16_t>(event.network_features().destination_port());
            ctx.protocol    = static_cast<uint8_t>(event.network_features().protocol_number());
            ctx.direction   = 0;
            ctx.nonce       = nullptr;
            ctx.tag         = nullptr;
            memset(ctx.annotation, 0, sizeof(ctx.annotation));
            memset(ctx.reserved,   0, sizeof(ctx.reserved));
            plugin_loader_->invoke_all(ctx);
            if (ctx.result_code != 0) {
                logger_->warn("[plugin-loader] plugin returned error={} — dropping event {}",
                              ctx.result_code, event.event_id());
                return;
            }
        }
        // Send enriched event
        send_enriched_event(event);

        // Stats
        auto end_time    = std::chrono::steady_clock::now();
        auto duration_ms = std::chrono::duration<double, std::milli>(end_time - start_time).count();

        {
            std::lock_guard<std::mutex> lock(stats_mutex_);
            stats_.events_processed++;
            stats_.avg_processing_time_ms =
                (stats_.avg_processing_time_ms * static_cast<double>(stats_.events_processed - 1) + duration_ms) /
                static_cast<double>(stats_.events_processed);
        }

        if (label_l1 == 1) {
            logger_->info("🚨 ATTACK: event={}, L1_conf={:.2f}%, processing={:.2f}ms",
                         event.event_id(), confidence_l1 * 100, duration_ms);
        } else {
            logger_->debug("✅ BENIGN: event={}, confidence={:.2f}%, processing={:.2f}ms",
                          event.event_id(), confidence_l1 * 100, duration_ms);
        }

    } catch (const std::exception& e) {
        logger_->error("Failed to process event: {}", e.what());
    }
}

void ZMQHandler::send_enriched_event(const protobuf::NetworkSecurityEvent& event) {
    try {
        // DAY 75: Defensive null guards — ADR-013 PHASE 2
        if (!tx_) {
            logger_->error("[DAY98] send_enriched_event: CryptoTransport tx_ NULL — dropping {}", event.event_id());
            return;
        }
        if (!output_socket_) {
            logger_->error("[DAY75] send_enriched_event: output_socket_ NULL — dropping {}", event.event_id());
            return;
        }
        std::string serialized;
        if (!event.SerializeToString(&serialized)) {
            logger_->error("Failed to serialize enriched event {}", event.event_id());
            return;
        }

        // ADR-013 PHASE 2 — LZ4 + CryptoTransport
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
                orig_size, max_compressed
            );
            if (compressed_size > 0) {
                compressed.resize(sizeof(uint32_t) + static_cast<size_t>(compressed_size));
                to_encrypt = std::move(compressed);
            } else {
                to_encrypt = std::vector<uint8_t>(serialized.begin(), serialized.end());
            }
        }
        auto encrypted = tx_->encrypt(to_encrypt);

        logger_->trace("🔒 Encrypted: {} → {} bytes", serialized.size(), encrypted.size());

        zmq::message_t message(encrypted.size());
        memcpy(message.data(), encrypted.data(), encrypted.size());

        auto result = output_socket_->send(message, zmq::send_flags::dontwait);

        if (result) {
            std::lock_guard<std::mutex> lock(stats_mutex_);
            stats_.events_sent++;
            logger_->debug("📤 Event sent: id={}, encrypted_size={} bytes",
                          event.event_id(), encrypted.size());
        } else {
            logger_->warn("Failed to send event {} (queue full?)", event.event_id());
        }

    } catch (const zmq::error_t& e) {
        logger_->error("ZMQ send error: {}", e.what());
    } catch (const std::exception& e) {
        logger_->error("Encryption/send error: {}", e.what());
    }
}

ZMQHandler::Stats ZMQHandler::get_stats() const {
    std::lock_guard<std::mutex> lock(stats_mutex_);
    return stats_;
}

void ZMQHandler::reset_stats() {
    std::lock_guard<std::mutex> lock(stats_mutex_);
    stats_ = Stats{};
    last_stats_report_ = std::chrono::steady_clock::now();
    logger_->info("📊 Stats reset");
}

void ZMQHandler::log_rag_statistics() {
    if (rag_logger_) {
        auto stats = rag_logger_->get_statistics();
        logger_->info("📊 RAG Stats: {} events logged, {} divergent, {} consensus",
                     stats["events_logged"],
                     stats["divergent_events"],
                     stats["consensus_events"]);
    }
}

uint64_t ZMQHandler::calculate_events_per_minute() {
    auto uptime_s = std::chrono::duration_cast<std::chrono::seconds>(
        std::chrono::system_clock::now() - start_time_
    ).count();

    if (uptime_s < 60) return events_processed_total_;
    return events_processed_total_ / static_cast<uint64_t>(uptime_s / 60);
}

void ZMQHandler::log_periodic_stats() {
    double memory_mb = get_memory_usage_mb();
    auto stats = get_stats();
    logger_->info("📈 Periodic Stats - Memory: {:.1f} MB, Events: {} received, {} processed",
                  memory_mb, stats.events_received, stats.events_processed);
}

void ZMQHandler::periodic_health_check() {
    double memory_mb = get_memory_usage_mb();
    auto uptime_s = std::chrono::duration_cast<std::chrono::seconds>(
        std::chrono::system_clock::now() - start_time_
    ).count();

    logger_->info("🧠 ML Detector Health - Memory: {:.1f} MB, Uptime: {}s", memory_mb, uptime_s);

    if (memory_mb > config_.monitoring.alerts.max_memory_usage_mb) {
        logger_->warn("⚠️  High memory usage: {:.1f} MB", memory_mb);
    }
}

void ZMQHandler::start_memory_monitoring() {
    memory_monitor_running_ = true;
    memory_monitor_thread_ = std::thread(&ZMQHandler::memory_monitor_loop, this);
    logger_->info("📊 Memory monitoring started");
}

void ZMQHandler::stop_memory_monitoring() {
    memory_monitor_running_ = false;
    if (memory_monitor_thread_.joinable()) {
        memory_monitor_thread_.join();
    }
    logger_->info("📊 Memory monitoring stopped");
}

void ZMQHandler::memory_monitor_loop() {
    while (memory_monitor_running_) {
        FILE* file = fopen("/proc/self/statm", "r");
        if (file) {
            long pages = 0;
            if (fscanf(file, "%*d %ld", &pages) == 1) {
                long page_size = sysconf(_SC_PAGESIZE);
                current_memory_mb_.store(compute_memory_mb(pages, page_size)); // F17 ADR-037
            }
            fclose(file);
        }
        std::this_thread::sleep_for(std::chrono::seconds(1));
    }
}

double ZMQHandler::get_memory_usage_mb() {
    return current_memory_mb_.load();
}

} // namespace ml_detector