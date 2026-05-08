// rag_logger.cpp - RAG Event Logger Implementation
// Day 16 - RACE CONDITION FIX Applied
// Authors: Alonso Isidoro Roman + Claude (Anthropic)
//
// CHANGES from Day 14:
// - check_rotation() moved INSIDE write_jsonl() critical section
// - Added check_rotation_locked() and rotate_logs_locked()
// - Eliminates race conditions on current_date_, current_log_, events_in_current_file_

#include "rag_logger.hpp"
#include <crypto_transport/contexts.hpp>
#include <lz4.h>
#include <cstring>
#include "csv_event_writer.hpp"
#include <fstream>
#include <sstream>
#include <iomanip>
#include <filesystem>
#include <openssl/sha.h>
#include <openssl/evp.h>

namespace fs = std::filesystem;

namespace ml_defender {

    RAGLogger::RAGLogger(const RAGLoggerConfig& config,
                         std::shared_ptr<spdlog::logger> logger,
                         std::shared_ptr<void> /*deprecated_crypto_manager*/)
        : config_(config)
        , logger_(logger)
        // DEPRECATED DAY 98 — crypto_manager ignorado (ADR-013)
        // , crypto_manager_(crypto_manager)
        , start_time_(std::chrono::system_clock::now())
    {
        logger_->info("🎯 Initializing RAG Logger");
        logger_->info("   Base path: {}", config_.base_path);
        logger_->info("   Deployment: {}", config_.deployment_id);

        // ADR-013 PHASE 2 — DAY 98: CryptoTransport para artefactos cifrados
        // Fail-closed DAY 99: FATAL en producción, modo degradado solo con MLD_DEV_MODE=1
        try {
            artifact_seed_client_ = std::make_unique<ml_defender::SeedClient>(
                "/etc/ml-defender/ml-detector/ml_detector_config.json");
            artifact_seed_client_->load();
            artifact_tx_ = std::make_unique<crypto_transport::CryptoTransport>(
                *artifact_seed_client_, ml_defender::crypto::CTX_RAG_ARTIFACTS);
            logger_->info("🔐 RAGLogger artifact encryption: CryptoTransport inicializado");
        } catch (const std::exception& e) {
            const char* dev_mode = std::getenv("MLD_DEV_MODE");
            if (dev_mode && std::string(dev_mode) == "1") {
                logger_->warn("⚠️  RAGLogger: MLD_DEV_MODE=1 — modo plaintext permitido: {}",
                              e.what());
            } else {
                logger_->critical("💀 RAGLogger: CryptoTransport no disponible: {}", e.what());
                logger_->critical("💀 Establece MLD_DEV_MODE=1 para modo desarrollo.");
                std::terminate();
            }
        }
        logger_->info("   Node: {}", config_.node_id);

        // Ensure directories exist
        ensure_directories();

        // Open initial log file
        current_date_ = get_date_string();
        current_log_path_ = get_current_log_path();

        current_log_.open(current_log_path_, std::ios::app);
        if (!current_log_.is_open()) {
            throw std::runtime_error("Failed to open RAG log file: " + current_log_path_);
        }

        logger_->info("✅ RAG Logger initialized: {}", current_log_path_);
    }

RAGLogger::~RAGLogger() {
    flush();
    logger_->info("📊 RAG Logger Statistics:");
    logger_->info("   Events logged: {}", events_logged_.load());
    logger_->info("   Events skipped: {}", events_skipped_.load());
    logger_->info("   Divergent events: {}", divergent_events_.load());
}

void RAGLogger::set_csv_writer(std::shared_ptr<CsvEventWriter> writer) {
        csv_writer_ = writer;
        logger_->info("[RAGLogger] CsvEventWriter attached — CSV output active");
        logger_->info("[RAGLogger]   Output: {}/YYYY-MM-DD.csv",
                      csv_writer_ ? "/vagrant/logs/ml-detector/events" : "n/a");
}

// ============================================================================
// Main Public Interface
// ============================================================================

bool RAGLogger::log_event(const protobuf::NetworkSecurityEvent& event,
                          const MLContext& context) {
    // Quick check without lock
    if (!should_log_event(event)) {
        events_skipped_.fetch_add(1, std::memory_order_relaxed);
        return false;
    }

    try {
        // Build JSON record
        auto json_record = build_json_record(event, context);

        // Write to log (thread-safe) - rotation check happens INSIDE
        bool success = write_jsonl(json_record);

        if (success) {
            events_logged_.fetch_add(1, std::memory_order_relaxed);

            // Track divergence
            if (event.has_decision_metadata() &&
                event.decision_metadata().score_divergence() > 0.30) {
                divergent_events_.fetch_add(1, std::memory_order_relaxed);
            }

            // Save artifacts if enabled
            if (config_.save_protobuf_artifacts || config_.save_json_artifacts) {
                save_artifacts(event, json_record);
            }
            if (csv_writer_) {
                csv_writer_->write_event(event);
                // Note: write_event() has its own error handling and logging.
                // A CSV write failure never affects JSONL success.
            }
            // FIX: Removed check_rotation() call here - now happens inside write_jsonl()
        }

        return success;

    } catch (const std::exception& e) {
        logger_->error("Failed to log RAG event: {}", e.what());
        return false;
    }
}

void RAGLogger::flush() {
    std::lock_guard<std::mutex> lock(mutex_);
    if (current_log_.is_open()) {
        current_log_.flush();
    }
}

void RAGLogger::rotate_logs() {
    std::lock_guard<std::mutex> lock(mutex_);
    rotate_logs_locked();
}

nlohmann::json RAGLogger::get_statistics() const {
    auto uptime = std::chrono::duration_cast<std::chrono::seconds>(
        std::chrono::system_clock::now() - start_time_
    ).count();

    nlohmann::json stats;
    stats["events_logged"] = events_logged_.load();
    stats["events_skipped"] = events_skipped_.load();
    stats["divergent_events"] = divergent_events_.load();
    stats["consensus_events"] = events_logged_.load() - divergent_events_.load();
    stats["events_in_current_file"] = events_in_current_file_.load();
    stats["current_log_path"] = current_log_path_;
    stats["uptime_seconds"] = uptime;
    stats["deployment_id"] = config_.deployment_id;
    stats["node_id"] = config_.node_id;

    return stats;
}

// ============================================================================
// Private Implementation
// ============================================================================

bool RAGLogger::should_log_event(const protobuf::NetworkSecurityEvent& event) const {
    // Check if decision metadata exists and requires RAG analysis
    if (event.has_decision_metadata()) {
        if (event.decision_metadata().requires_rag_analysis()) {
            return true;
        }
    }

    // Check minimum threat score
    if (event.overall_threat_score() >= config_.min_score_to_log) {
        return true;
    }

    // Check divergence
    if (event.has_decision_metadata()) {
        double divergence = event.decision_metadata().score_divergence();
        if (divergence >= config_.min_divergence_to_log) {
            return true;
        }
    }

    return false;
}

nlohmann::json RAGLogger::build_json_record(
    const protobuf::NetworkSecurityEvent& event,
    const MLContext& context) const {

    nlohmann::json record;

    // ========================================================================
    // RAG METADATA
    // ========================================================================
    record["rag_metadata"] = {
        {"logged_at", get_iso8601_timestamp()},
        {"deployment_id", config_.deployment_id},
        {"node_id", config_.node_id},
        {"log_version", "1.0.0"}
    };

    // ========================================================================
    // DETECTION - Scores y clasificación
    // ========================================================================
    nlohmann::json detection;

    // Timestamp del evento
    if (event.has_event_timestamp()) {
        detection["detection_timestamp"] = event.event_timestamp().seconds();
    }

    // Scores
    detection["scores"] = {
        {"fast_detector", event.fast_detector_score()},
        {"ml_detector", event.ml_detector_score()},
        {"final_score", event.overall_threat_score()},
        {"divergence", event.has_provenance() ? event.provenance().discrepancy_score()
                                              : (event.has_decision_metadata() ? event.decision_metadata().score_divergence() : 0.0)}
    };

    // Classification
    detection["classification"] = {
        {"authoritative_source", protobuf::DetectorSource_Name(event.authoritative_source())},
        {"attack_family", context.attack_family},
        {"level_1_label", context.level_1_label},
        {"final_class", event.final_classification()},
        {"threat_category", event.threat_category()},
        {"confidence", context.level_1_confidence}
    };

    // Reasons
    detection["reasons"] = {
        {"fast_detector_triggered", event.fast_detector_triggered()},
        {"fast_detector_reason", event.fast_detector_reason()},
        {"requires_rag_analysis", event.has_decision_metadata() ?
            event.decision_metadata().requires_rag_analysis() : false},
        {"investigation_priority", context.investigation_priority}
    };

    // Decision metadata
    if (event.has_decision_metadata()) {
        const auto& dm = event.decision_metadata();
        detection["decision"] = {
            {"confidence_level", dm.confidence_level()},
            {"divergence_reason", dm.divergence_reason()}
        };
    }

    record["detection"] = detection;

    // ========================================================================
    // NETWORK - 5-tuple y contexto
    // ========================================================================
    nlohmann::json network;

    if (event.has_network_features()) {
        const auto& nf = event.network_features();

        network["five_tuple"] = {
            {"src_ip", nf.source_ip()},
            {"src_port", nf.source_port()},
            {"dst_ip", nf.destination_ip()},
            {"dst_port", nf.destination_port()},
            {"protocol", nf.protocol_name()}
        };

        network["interface"] = nf.source_interface();
        network["interface_mode"] = nf.interface_mode();
        network["is_wan_facing"] = nf.is_wan_facing();

        // Flow statistics
        network["flow"] = {
            {"duration_us", nf.flow_duration_microseconds()},
            {"total_packets", nf.total_forward_packets() + nf.total_backward_packets()},
            {"total_bytes", nf.total_forward_bytes() + nf.total_backward_bytes()},
            {"bytes_per_sec", nf.flow_bytes_per_second()},
            {"packets_per_sec", nf.flow_packets_per_second()}
        };
    }

    // GeoIP if available
    if (event.has_geo_enrichment()) {
        const auto& geo = event.geo_enrichment();

        nlohmann::json geoip;

        if (geo.has_source_ip_geo()) {
            geoip["source"] = {
                {"country", geo.source_ip_geo().country_code()},
                {"city", geo.source_ip_geo().city_name()},
                {"threat_level", protobuf::GeoLocationInfo_ThreatLevel_Name(
                    geo.source_ip_geo().threat_level())}
            };
        }

        if (geo.has_destination_ip_geo()) {
            geoip["destination"] = {
                {"country", geo.destination_ip_geo().country_code()},
                {"city", geo.destination_ip_geo().city_name()}
            };
        }

        network["geoip"] = geoip;
    }

    record["network"] = network;

    // ========================================================================
    // FEATURES - Raw features agregadas
    // ========================================================================
    nlohmann::json features;

    if (event.has_network_features()) {
        const auto& nf = event.network_features();

        // Estadísticas básicas
        features["basic_stats"] = {
            {"forward_packets", nf.total_forward_packets()},
            {"backward_packets", nf.total_backward_packets()},
            {"forward_bytes", nf.total_forward_bytes()},
            {"backward_bytes", nf.total_backward_bytes()},
            {"avg_packet_size", nf.average_packet_size()}
        };

        // TCP Flags
        features["tcp_flags"] = {
            {"syn", nf.syn_flag_count()},
            {"ack", nf.ack_flag_count()},
            {"fin", nf.fin_flag_count()},
            {"rst", nf.rst_flag_count()},
            {"psh", nf.psh_flag_count()}
        };

        // Timing
        features["timing"] = {
            {"flow_iat_mean", nf.flow_inter_arrival_time_mean()},
            {"flow_iat_std", nf.flow_inter_arrival_time_std()},
            {"forward_iat_mean", nf.forward_inter_arrival_time_mean()},
            {"backward_iat_mean", nf.backward_inter_arrival_time_mean()}
        };
    }

    record["features"] = features;

    // ========================================================================
    // SYSTEM STATE
    // ========================================================================
    record["system_state"] = {
        {"events_processed_total", context.events_processed_total},
        {"events_in_last_minute", context.events_in_last_minute},
        {"memory_usage_mb", context.memory_usage_mb},
        {"cpu_usage_percent", context.cpu_usage_percent},
        {"uptime_seconds", context.uptime_seconds}
    };

    // ========================================================================
    // ML TRAINING METADATA
    // ========================================================================
    record["ml_training_metadata"] = {
        {"can_be_used_for_training", true},
        {"ground_truth_label", "UNKNOWN"},  // Will be set by analyst
        {"human_validated", false}
    };

    return record;
}

bool RAGLogger::write_jsonl(const nlohmann::json& record) {
    std::lock_guard<std::mutex> lock(mutex_);

    if (!current_log_.is_open()) {
        logger_->error("RAG log file not open");
        return false;
    }

    try {
        // Escribir directo (nlohmann::json tiene operator<< optimizado)
        current_log_ << record << "\n";
        current_log_.flush();  // ← MANTENER, es crítico

        events_in_current_file_++;
        check_rotation_locked();
        return true;
    } catch (const std::exception& e) {
        logger_->error("Failed to write JSON record: {}", e.what());
        return false;
    }
}

void RAGLogger::save_artifacts(const protobuf::NetworkSecurityEvent& event,
                               const nlohmann::json& json_record) {
    try {
        // ====================================================================
        // 🎯 ISSUE-004 FIX: Validate event completeness before serialization
        // ====================================================================
        // CRITICAL: Protobuf serialization crashes on null embedded messages
        // This validation prevents SEGFAULT when processing incomplete events
        
        if (!event.has_network_features()) {
            logger_->warn("⚠️  Skipping artifact save: event {} missing network_features", 
                         event.event_id());
            return;
        }
        

        // DAY 75 FIX: Removed proto2-style has_required_embedded guard.
        // In proto3, submessages are NEVER null pointers — accessing
        // nf.ddos_embedded() on an unset field returns a safe default instance.
        // The original check (has_ddos_embedded() == false) incorrectly blocked
        // ransomware-features events whose embedded messages contained all-zero
        // floats: proto3 omits zero-value fields on the wire, making has_X()
        // return false even for a fully constructed message.
        // The real fix is in ring_consumer.cpp::send_ransomware_features()
        // which now populates sentinel values to force serialization.
        
        // ====================================================================
        // Event is valid, proceed with artifact save
        // ====================================================================
        
        // Get artifact directory for today
        std::string artifact_dir = config_.base_path + "/artifacts/" + current_date_;
        fs::create_directories(artifact_dir);

        // Generate filename based on event ID
        std::string base_filename = artifact_dir + "/event_" + event.event_id();

        // 🎯 ADR-001: Save ENCRYPTED protobuf if enabled
        // DAY 75: Guard crypto_manager_ — may be null in test/degraded mode
        if (config_.save_protobuf_artifacts) {
            std::string pb_path = base_filename + ".pb.enc";  // .enc extension
            std::ofstream pb_file(pb_path, std::ios::binary);

            if (pb_file.is_open()) {
                // Serialize protobuf (SAFE now - validated above)
                std::string serialized;
                event.SerializeToString(&serialized);

                // ADR-013 PHASE 2 — LZ4 + CryptoTransport
                if (artifact_tx_) {
                    int orig_size = static_cast<int>(serialized.size());
                    int max_c = LZ4_compressBound(orig_size);
                    std::vector<uint8_t> compressed(sizeof(uint32_t) + static_cast<size_t>(max_c));
                    uint32_t orig_le = static_cast<uint32_t>(orig_size);
                    std::memcpy(compressed.data(), &orig_le, sizeof(orig_le));
                    int c_size = LZ4_compress_default(serialized.data(),
                        reinterpret_cast<char*>(compressed.data() + sizeof(uint32_t)),
                        orig_size, max_c);
                    if (c_size > 0) compressed.resize(sizeof(uint32_t) + static_cast<size_t>(c_size));
                    else compressed = std::vector<uint8_t>(serialized.begin(), serialized.end());
                    auto encrypted = artifact_tx_->encrypt(compressed);
                    pb_file.write(reinterpret_cast<const char*>(encrypted.data()), static_cast<std::streamsize>(encrypted.size()));
                } else {
                    pb_file.write(serialized.data(), static_cast<std::streamsize>(serialized.size()));
                }
                pb_file.close();

                logger_->trace("🔒 Saved encrypted protobuf: {}", pb_path);
            }
        }

        // 🎯 ADR-001: Save ENCRYPTED JSON if enabled
        if (config_.save_json_artifacts) {
            std::string json_path = base_filename + ".json.enc";  // .enc extension
            std::ofstream json_file(json_path, std::ios::binary);

            if (json_file.is_open()) {
                // Serialize JSON (pretty print)
                std::string json_str = json_record.dump(2);

                // ADR-013 PHASE 2 — LZ4 + CryptoTransport
                if (artifact_tx_) {
                    int orig_size = static_cast<int>(json_str.size());
                    int max_c = LZ4_compressBound(orig_size);
                    std::vector<uint8_t> compressed(sizeof(uint32_t) + static_cast<size_t>(max_c));
                    uint32_t orig_le = static_cast<uint32_t>(orig_size);
                    std::memcpy(compressed.data(), &orig_le, sizeof(orig_le));
                    int c_size = LZ4_compress_default(json_str.data(),
                        reinterpret_cast<char*>(compressed.data() + sizeof(uint32_t)),
                        orig_size, max_c);
                    if (c_size > 0) compressed.resize(sizeof(uint32_t) + static_cast<size_t>(c_size));
                    else compressed = std::vector<uint8_t>(json_str.begin(), json_str.end());
                    auto encrypted = artifact_tx_->encrypt(compressed);
                    json_file.write(reinterpret_cast<const char*>(encrypted.data()), static_cast<std::streamsize>(encrypted.size()));
                } else {
                    json_file.write(json_str.data(), static_cast<std::streamsize>(json_str.size()));
                }
                json_file.close();

                logger_->trace("🔒 Saved encrypted JSON: {}", json_path);
            }
        }

    } catch (const std::exception& e) {
        logger_->warn("Failed to save encrypted artifacts: {}", e.what());
    }
}


// FIX: New function that assumes mutex_ is already held
void RAGLogger::check_rotation_locked() {
    // PRECONDITION: mutex_ must be held by caller

    // Check if date changed
    std::string new_date = get_date_string();
    if (new_date != current_date_) {
        rotate_logs_locked();
        return;
    }

    // Check if file is too large or has too many events
    if (events_in_current_file_ >= config_.max_events_per_file) {
        logger_->info("RAG log file reached max events ({}), rotating",
                     config_.max_events_per_file);
        rotate_logs_locked();
    }
}

// FIX: New function that assumes mutex_ is already held
void RAGLogger::rotate_logs_locked() {
    // PRECONDITION: mutex_ must be held by caller

    std::string new_date = get_date_string();
    if (new_date != current_date_) {
        // Date changed, rotate
        logger_->info("📅 Date changed, rotating RAG log file");

        if (current_log_.is_open()) {
            current_log_.close();
        }

        current_date_ = new_date;
        current_log_path_ = get_current_log_path();
        current_log_.open(current_log_path_, std::ios::app);

        events_in_current_file_ = 0;

        if (!current_log_.is_open()) {
            logger_->error("Failed to open new RAG log file: {}", current_log_path_);
        }
    }
}

void RAGLogger::ensure_directories() const {
    try {
        fs::create_directories(config_.base_path + "/events");
        fs::create_directories(config_.base_path + "/artifacts");
    } catch (const std::exception& e) {
        throw std::runtime_error("Failed to create RAG directories: " +
                                std::string(e.what()));
    }
}

std::string RAGLogger::get_date_string() const {
    auto now = std::chrono::system_clock::now();
    auto time_t = std::chrono::system_clock::to_time_t(now);
    std::tm tm;
    localtime_r(&time_t, &tm);

    std::ostringstream oss;
    oss << std::put_time(&tm, "%Y-%m-%d");
    return oss.str();
}

std::string RAGLogger::get_current_log_path() const {
    return config_.base_path + "/events/" + current_date_ + ".jsonl";
}

std::string RAGLogger::get_iso8601_timestamp() const {
    auto now = std::chrono::system_clock::now();
    auto time_t = std::chrono::system_clock::to_time_t(now);
    std::tm tm;
    gmtime_r(&time_t, &tm);

    std::ostringstream oss;
    oss << std::put_time(&tm, "%Y-%m-%dT%H:%M:%S") << "Z";
    return oss.str();
}

std::string RAGLogger::calculate_sha256(const std::string& data) {
    unsigned char hash[SHA256_DIGEST_LENGTH];
    EVP_MD_CTX* ctx = EVP_MD_CTX_new();
    EVP_DigestInit_ex(ctx, EVP_sha256(), nullptr);
    EVP_DigestUpdate(ctx, data.c_str(), data.size());
    unsigned int hash_len = 0;
    EVP_DigestFinal_ex(ctx, hash, &hash_len);
    EVP_MD_CTX_free(ctx);

    std::ostringstream oss;
    for (int i = 0; i < SHA256_DIGEST_LENGTH; i++) {
        oss << std::hex << std::setw(2) << std::setfill('0') << static_cast<int>(hash[i]);
    }
    return oss.str();
}

// ============================================================================
// Factory Function
// ============================================================================

std::unique_ptr<RAGLogger> create_rag_logger_from_config(
    const std::string& config_path,
    std::shared_ptr<spdlog::logger> logger,
    std::shared_ptr<void> /*deprecated*/) {

    // Load config from JSON file
    std::ifstream config_file(config_path);
    if (!config_file.is_open()) {
        throw std::runtime_error("Failed to open RAG logger config: " + config_path);
    }

    nlohmann::json config_json;
    config_file >> config_json;

    // Build config struct
    RAGLoggerConfig config;
    config.base_path = config_json.value("base_path", "/vagrant/logs/rag");
    config.deployment_id = config_json.value("deployment_id", "ml-defender-dev");
    config.node_id = config_json.value("node_id", "detector-01");
    config.min_score_to_log = config_json.value("min_score_to_log", 0.70);
    config.min_divergence_to_log = config_json.value("min_divergence_to_log", 0.30);
    config.max_events_per_file = static_cast<size_t>(config_json.value("max_events_per_file", 10000));
    config.max_file_size_mb = static_cast<size_t>(config_json.value("max_file_size_mb", 100));
    config.save_protobuf_artifacts = config_json.value("save_protobuf_artifacts", true);
    config.save_json_artifacts = config_json.value("save_json_artifacts", true);

    return std::make_unique<RAGLogger>(config, logger);
}

} // namespace ml_defender