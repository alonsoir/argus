//===----------------------------------------------------------------------===//
// ML Defender - Firewall ACL Agent
// config_manager.cpp - JSON Configuration Parser (JSON is LAW)
//===----------------------------------------------------------------------===//

#include "firewall/config_loader.hpp"
#include <fstream>
#include <safe_path/safe_path.hpp>
#include <stdexcept>
#include <iostream>
#include <iomanip>
#include <map>

namespace mldefender::firewall {

//===----------------------------------------------------------------------===//
// Template Implementations
//===----------------------------------------------------------------------===//

template<typename T>
T ConfigLoader::get_required(const Json::Value& json, const std::string& key, 
                              const std::string& context, const std::string& config_path) {
    if (!json.isMember(key)) {
        throw std::invalid_argument(
            "❌ MISSING REQUIRED FIELD: '" + key + "' in [" + context + "]\n"
            "   Config file: " + config_path + "\n"
            "   Fix: Add '" + key + "' to the JSON and restart"
        );
    }
    
    if constexpr (std::is_same_v<T, std::string>) {
        return json[key].asString();
    } else if constexpr (std::is_same_v<T, int>) {
        return json[key].asInt();
    } else if constexpr (std::is_same_v<T, float>) {
        return json[key].asFloat();
    } else if constexpr (std::is_same_v<T, bool>) {
        return json[key].asBool();
    } else {
        throw std::invalid_argument("Unsupported type in get_required");
    }
}

template<typename T>
T ConfigLoader::get_optional(const Json::Value& json, const std::string& key, const T& default_value) {
    if (!json.isMember(key)) {
        return default_value;
    }
    
    if constexpr (std::is_same_v<T, std::string>) {
        return json[key].asString();
    } else if constexpr (std::is_same_v<T, int>) {
        return json[key].asInt();
    } else if constexpr (std::is_same_v<T, float>) {
        return json[key].asFloat();
    } else if constexpr (std::is_same_v<T, bool>) {
        return json[key].asBool();
    } else {
        return default_value;
    }
}

std::vector<std::string> ConfigLoader::parse_string_array(const Json::Value& array) {
    std::vector<std::string> result;
    if (array.isArray()) {
        for (const auto& item : array) {
            result.push_back(item.asString());
        }
    }
    return result;
}

//===----------------------------------------------------------------------===//
// Main Load Function
//===----------------------------------------------------------------------===//

FirewallAgentConfig ConfigLoader::load_from_file(const std::string& config_path,
                                                    const std::string& allowed_prefix) {
    std::cout << "[CONFIG] Loading configuration from: " << config_path << std::endl;

    // allowed_prefix es SIEMPRE fijo — nunca derivado del input.
    // Usamos resolve_config() que permite symlinks en el prefix confiable:
    // /etc/ml-defender/*.json → /vagrant/*.json en dev (paridad dev/prod).
    // (DEBT-DEV-PROD-SYMLINK-001 DAY 127)
    namespace fs = std::filesystem;
    const auto safe_config_path =
        argus::safe_path::resolve_config(config_path, allowed_prefix);
    std::ifstream file(safe_config_path);
    if (!file.is_open()) {
        throw std::runtime_error(
            "❌ CANNOT OPEN CONFIG FILE: " + config_path + "\n"
            "   Check that the file exists and has read permissions"
        );
    }
    
    // Parse JSON
    Json::Value root;
    Json::CharReaderBuilder builder;
    std::string errors;
    
    if (!Json::parseFromStream(builder, file, &root, &errors)) {
        throw std::runtime_error(
            "❌ INVALID JSON in " + config_path + "\n"
            "   Parse error: " + errors + "\n"
            "   Fix the JSON syntax and restart"
        );
    }
    
    FirewallAgentConfig config;
    
    // Parse each section
    if (root.isMember("operation")) {
        config.operation = parse_operation(root["operation"]);
    }
    
    if (root.isMember("zmq")) {
        config.zmq = parse_zmq(root["zmq"]);
    }
    
    if (root.isMember("ipset")) {
        config.ipset = parse_ipset(root["ipset"]);
    }
    
    if (root.isMember("ipsets")) {
        config.ipsets = parse_ipsets(root["ipsets"]);
    }
    
    if (root.isMember("iptables")) {
        config.iptables = parse_iptables(root["iptables"]);
    }
    
    if (root.isMember("batch_processor")) {
        config.batch_processor = parse_batch_processor(root["batch_processor"]);
    }
    // ADR-042: cargar IRP config desde isolate.json (path fijo producción)
    config.irp = parse_irp("/etc/ml-defender/firewall-acl-agent/isolate.json");
    
    if (root.isMember("validation")) {
        config.validation = parse_validation(root["validation"]);
    }
    
    if (root.isMember("logging")) {
        config.logging = parse_logging(root["logging"]);
    }

    if (root.isMember("etcd")) {
        config.etcd = parse_etcd(root["etcd"]);
    }

    // ✅ Day 23: Transport configuration
    if (root.isMember("transport")) {
        config.transport = parse_transport(root["transport"]);
    }

    // ✅ Day 61: CSV batch logger config (proper parser)
    if (root.isMember("csv_batch_logger")) {
        config.csv_batch_logger = parse_csv_batch_logger(root["csv_batch_logger"]);
        std::cout << "[CONFIG] CSV batch logger output_dir: "
                  << config.csv_batch_logger.output_dir << std::endl;
    }

    // Validate configuration
    validate_config(config);

    std::cout << "[CONFIG] ✓ Configuration loaded successfully" << std::endl;
    if (config.operation.dry_run) {
        std::cout << "[CONFIG] ⚠️  DRY-RUN MODE ENABLED - No actual firewall changes will be made" << std::endl;
    }

    return config;
}

//===----------------------------------------------------------------------===//
// Section Parsers
//===----------------------------------------------------------------------===//

OperationConfig ConfigLoader::parse_operation(const Json::Value& json) {
    OperationConfig config;
    config.dry_run = get_optional<bool>(json, "dry_run", true);

    // Default log directory (can be overridden by csv_batch_logger in load_from_file)
    config.log_directory = get_optional<std::string>(json, "log_directory",
        "/vagrant/firewall-acl-agent/build/logs");

    config.enable_debug_logging = get_optional<bool>(json, "enable_debug_logging", true);
    config.simulate_block = get_optional<bool>(json, "simulate_block", true);
    config.validation_strictness = get_optional<std::string>(json, "validation_strictness", "high");
    config.max_processing_delay_ms = get_optional<int>(json, "max_processing_delay_ms", 10);

    return config;
}

ZMQConfigNew ConfigLoader::parse_zmq(const Json::Value& json) {
    ZMQConfigNew config;
    config.endpoint = get_optional<std::string>(json, "endpoint", "tcp://localhost:5572");
    config.topic = get_optional<std::string>(json, "topic", "BlockRequest");
    config.recv_timeout_ms = get_optional<int>(json, "recv_timeout_ms", 1000);
    config.linger_ms = get_optional<int>(json, "linger_ms", 1000);
    config.reconnect_interval_ms = get_optional<int>(json, "reconnect_interval_ms", 1000);
    config.max_reconnect_interval_ms = get_optional<int>(json, "max_reconnect_interval_ms", 30000);
    config.enable_reconnect = get_optional<bool>(json, "enable_reconnect", true);
    config.high_water_mark = get_optional<int>(json, "high_water_mark", 1000);
    config.monitor_interval_sec = get_optional<int>(json, "monitor_interval_sec", 30);
    return config;
}

IPSetConfigNew ConfigLoader::parse_ipset(const Json::Value& json) {
    IPSetConfigNew config;
    config.set_name = get_optional<std::string>(json, "set_name", "ml_defender_blacklist_test");
    config.set_type = get_optional<std::string>(json, "set_type", "hash:ip");
    config.hash_size = get_optional<int>(json, "hash_size", 1024);
    config.max_elements = get_optional<int>(json, "max_elements", 1000);
    config.timeout = get_optional<int>(json, "timeout", 3600);
    config.comment = get_optional<std::string>(json, "comment", "ML Defender blocked IPs");
    config.family = get_optional<std::string>(json, "family", "inet");
    config.create_if_missing = get_optional<bool>(json, "create_if_missing", true);
    config.flush_on_startup = get_optional<bool>(json, "flush_on_startup", false);
    return config;
}

std::map<std::string, IPSetConfigNew> ConfigLoader::parse_ipsets(const Json::Value& json) {
    std::map<std::string, IPSetConfigNew> ipsets;

    if (!json.isObject()) {
        return ipsets;
    }

    // Iterar sobre cada entrada en "ipsets" (blacklist, whitelist, etc.)
    for (const auto& key : json.getMemberNames()) {
        ipsets[key] = parse_ipset(json[key]);
    }

    return ipsets;
}

IPTablesConfigNew ConfigLoader::parse_iptables(const Json::Value& json) {
    IPTablesConfigNew config;
    config.chain_name = get_optional<std::string>(json, "chain_name", "ML_DEFENDER_TEST");
    config.default_policy = get_optional<std::string>(json, "default_policy", "ACCEPT");
    config.log_blocked = get_optional<bool>(json, "log_blocked", true);
    config.log_prefix = get_optional<std::string>(json, "log_prefix", "ML_DEFENDER_DROP: ");
    config.enable_rate_limiting = get_optional<bool>(json, "enable_rate_limiting", false);
    config.rate_limit_connections = get_optional<int>(json, "rate_limit_connections", 100);
    config.create_chain = get_optional<bool>(json, "create_chain", true);
    config.insert_rule_position = get_optional<int>(json, "insert_rule_position", 1);
    return config;
}

IrpConfig ConfigLoader::parse_irp(const std::string& isolate_json_path) {
    IrpConfig cfg;
    std::ifstream f(isolate_json_path);
    if (!f.is_open()) {
        // DEBT-IRP-AUTOISO-FALSE-001: isolate.json ausente = error de despliegue.
        // No hay fallback silencioso — única fuente de verdad (ADR-042).
        throw std::runtime_error(
            "[IRP] isolate.json no encontrado en: " + isolate_json_path +
            " — despliegue incompleto. Ejecute make bootstrap o provision.sh.");
    }
    try {
        Json::Value j;
        Json::CharReaderBuilder rb;
        std::string errs;
        if (!Json::parseFromStream(rb, f, &j, &errs)) {
            throw std::runtime_error(
                "[IRP] JSON malformado en: " + isolate_json_path + " — " + errs);
        }
        // DEBT-IRP-AUTOISO-FALSE-001: isolate.json es la ÚNICA fuente de verdad.
        // Campo obligatorio — sin fallback. Si falta, es error de configuración.
        if (!j.isMember("auto_isolate")) {
            throw std::runtime_error("[IRP] 'auto_isolate' ausente en isolate.json. "
                "Campo obligatorio. Revise la documentación ADR-042.");
        }
        cfg.auto_isolate = j["auto_isolate"].asBool();
        cfg.threat_score_threshold = j.get("threat_score_threshold", 0.95).asDouble();
        cfg.isolate_interface      = j.get("isolate_interface",      "eth0").asString();
        cfg.isolate_config_path    = isolate_json_path;
        if (j.isMember("auto_isolate_event_types")) {
            for (const auto& v : j["auto_isolate_event_types"])
                cfg.auto_isolate_event_types.push_back(v.asString());
        }
    } catch (const std::runtime_error&) {
        throw;  // DEBT-IRP-AUTOISO-FALSE-001: no tragamos errores de config — relanzar
    } catch (const std::exception& e) {
        throw std::runtime_error(
            std::string("[IRP] Error parseando isolate.json: ") + e.what());
    }
    return cfg;
}

BatchProcessorConfigNew ConfigLoader::parse_batch_processor(const Json::Value& json) {
    BatchProcessorConfigNew config;
    config.batch_size_threshold = get_optional<int>(json, "batch_size_threshold", 10);
    config.batch_time_threshold_ms = get_optional<int>(json, "batch_time_threshold_ms", 1000);
    config.max_pending_ips = get_optional<int>(json, "max_pending_ips", 100);
    config.min_confidence = get_optional<float>(json, "min_confidence", 0.5f);
    config.enable_batching = get_optional<bool>(json, "enable_batching", true);
    config.flush_on_shutdown = get_optional<bool>(json, "flush_on_shutdown", true);
    return config;
}

ValidationConfig ConfigLoader::parse_validation(const Json::Value& json) {
    ValidationConfig config;
    config.validate_ip_addresses = get_optional<bool>(json, "validate_ip_addresses", true);
    config.validate_confidence_scores = get_optional<bool>(json, "validate_confidence_scores", true);
    config.min_confidence_score = get_optional<float>(json, "min_confidence_score", 0.5f);
    config.max_confidence_score = get_optional<float>(json, "max_confidence_score", 1.0f);
    config.block_localhost = get_optional<bool>(json, "block_localhost", false);
    config.block_gateway = get_optional<bool>(json, "block_gateway", false);

    if (json.isMember("allowed_ip_ranges")) {
        config.allowed_ip_ranges = parse_string_array(json["allowed_ip_ranges"]);
    }

    return config;
}

LoggingConfigNew ConfigLoader::parse_logging(const Json::Value& json) {
    LoggingConfigNew config;
    config.level = get_optional<std::string>(json, "level", "debug");
    config.console = get_optional<bool>(json, "console", true);
    config.syslog = get_optional<bool>(json, "syslog", false);
    config.file = get_optional<std::string>(json, "file", "/vagrant/firewall-acl-agent/build/logs/firewall-agent.log");
    config.max_file_size_mb = get_optional<int>(json, "max_file_size_mb", 10);
    config.backup_count = get_optional<int>(json, "backup_count", 5);
    config.log_protobuf_messages = get_optional<bool>(json, "log_protobuf_messages", true);
    config.log_zmq_events = get_optional<bool>(json, "log_zmq_events", true);
    config.log_block_decisions = get_optional<bool>(json, "log_block_decisions", true);
    config.log_performance_metrics = get_optional<bool>(json, "log_performance_metrics", true);
    return config;
}

//===----------------------------------------------------------------------===//
// Validation
//===----------------------------------------------------------------------===//

void ConfigLoader::validate_config(const FirewallAgentConfig& config) {
    std::vector<std::string> errors;

    // Validate ZMQ endpoint
    if (config.zmq.endpoint.empty()) {
        errors.push_back("ZMQ endpoint cannot be empty");
    }

    // Validate IPSet name
    if (config.ipset.set_name.empty()) {
        errors.push_back("IPSet name cannot be empty");
    }

    // Validate chain name
    if (config.iptables.chain_name.empty()) {
        errors.push_back("IPTables chain name cannot be empty");
    }

    // Validate confidence thresholds
    if (config.batch_processor.min_confidence < 0.0f || config.batch_processor.min_confidence > 1.0f) {
        errors.push_back("Batch processor min_confidence must be between 0.0 and 1.0");
    }

    if (!errors.empty()) {
        std::string error_msg = "❌ CONFIGURATION VALIDATION FAILED:\n";
        for (const auto& error : errors) {
            error_msg += "   - " + error + "\n";
        }
        throw std::invalid_argument(error_msg);
    }
}

void ConfigLoader::fail_fast(const std::string& error_message) {
    std::cerr << "\n╔════════════════════════════════════════════════════════╗\n"
              << "║  FATAL CONFIGURATION ERROR                             ║\n"
              << "╚════════════════════════════════════════════════════════╝\n"
              << error_message << std::endl;
    std::exit(1);
}

void ConfigLoader::log_config_summary(const FirewallAgentConfig& config) {
    std::cout << "\n╔════════════════════════════════════════════════════════╗\n"
              << "║  Firewall ACL Agent Configuration Summary             ║\n"
              << "╚════════════════════════════════════════════════════════╝\n";

    std::cout << "\n[Operation]\n"
              << "  Dry-Run:         " << (config.operation.dry_run ? "ENABLED ⚠️" : "DISABLED") << "\n"
              << "  Debug Logging:   " << (config.operation.enable_debug_logging ? "ON" : "OFF") << "\n"
              << "  Simulate Block:  " << (config.operation.simulate_block ? "ON" : "OFF") << "\n";

    std::cout << "\n[ZMQ]\n"
              << "  Endpoint:        " << config.zmq.endpoint << "\n"
              << "  Topic:           " << config.zmq.topic << "\n"
              << "  Timeout:         " << config.zmq.recv_timeout_ms << "ms\n";

    std::cout << "\n[IPSet]\n"
              << "  Name:            " << config.ipset.set_name << "\n"
              << "  Type:            " << config.ipset.set_type << "\n"
              << "  Max Elements:    " << config.ipset.max_elements << "\n"
              << "  Timeout:         " << config.ipset.timeout << "s\n";

    std::cout << "\n[IPTables]\n"
              << "  Chain:           " << config.iptables.chain_name << "\n"
              << "  Log Blocked:     " << (config.iptables.log_blocked ? "ON" : "OFF") << "\n"
              << "  Rate Limiting:   " << (config.iptables.enable_rate_limiting ? "ON" : "OFF") << "\n";

    std::cout << "\n[Batch Processor]\n"
              << "  Batch Size:      " << config.batch_processor.batch_size_threshold << "\n"
              << "  Min Confidence:  " << config.batch_processor.min_confidence << "\n"
              << "  Batching:        " << (config.batch_processor.enable_batching ? "ON" : "OFF") << "\n";

    std::cout << std::endl;
}

//===----------------------------------------------------------------------===//
// Etcd Parser
//===----------------------------------------------------------------------===//

EtcdConfig ConfigLoader::parse_etcd(const Json::Value& json) {
    EtcdConfig config;

    config.enabled = get_optional<bool>(json, "enabled", false);

    if (json.isMember("endpoints") && json["endpoints"].isArray()) {
        config.endpoints = parse_string_array(json["endpoints"]);
    }

    config.connection_timeout_ms = get_optional<int>(json, "connection_timeout_ms", 5000);
    config.retry_attempts = get_optional<int>(json, "retry_attempts", 3);
    config.retry_interval_ms = get_optional<int>(json, "retry_interval_ms", 1000);
    config.heartbeat_interval_seconds = get_optional<int>(json, "heartbeat_interval_seconds", 30);
    config.lease_ttl_seconds = get_optional<int>(json, "lease_ttl_seconds", 60);

    return config;
}

//===----------------------------------------------------------------------===//
// Transport Parser (Day 23)
//===----------------------------------------------------------------------===//

TransportConfig ConfigLoader::parse_transport(const Json::Value& json) {
    TransportConfig config;

    // Parse compression section
    if (json.isMember("compression")) {
        const auto& comp = json["compression"];
        config.compression.enabled = get_optional<bool>(comp, "enabled", false);
        config.compression.decompression_only = get_optional<bool>(comp, "decompression_only", true);
        config.compression.algorithm = get_optional<std::string>(comp, "algorithm", "lz4");
    }

    // Parse encryption section
    if (json.isMember("encryption")) {
        const auto& enc = json["encryption"];
        config.encryption.enabled = get_optional<bool>(enc, "enabled", false);
        config.encryption.decryption_only = get_optional<bool>(enc, "decryption_only", true);
        config.encryption.etcd_token_required = get_optional<bool>(enc, "etcd_token_required", true);
        config.encryption.algorithm = get_optional<std::string>(enc, "algorithm", "chacha20-poly1305");
        config.encryption.fallback_mode = get_optional<std::string>(enc, "fallback_mode", "compressed_only");
    }

    return config;
}
//===----------------------------------------------------------------------===//
// CSV Batch Logger Parser (Day 59)
//===----------------------------------------------------------------------===//

CsvBatchLoggerConfig ConfigLoader::parse_csv_batch_logger(const Json::Value& json) {
    CsvBatchLoggerConfig config;
    config.enabled      = get_optional<bool>(json, "enabled", false);
    config.output_dir   = get_optional<std::string>(json, "output_dir", "/vagrant/logs/firewall_logs");
    config.batch_size   = get_optional<int>(json, "batch_size", 100);
    config.batch_timeout_sec = get_optional<int>(json, "batch_timeout_sec", 5);
    return config;
}

} // namespace mldefender::firewall