#pragma once
//===----------------------------------------------------------------------===//
// ML Defender - Firewall ACL Agent
// config.hpp - Complete Configuration Structures (JSON is LAW)
//===----------------------------------------------------------------------===//

#include <string>
#include <vector>
#include <chrono>
#include <json/json.h>

namespace mldefender::firewall {

//===----------------------------------------------------------------------===//
// Operation Configuration (DRY-RUN Support!)
//===----------------------------------------------------------------------===//
struct OperationConfig {
    bool dry_run = true;
    std::string log_directory = "/vagrant/firewall-acl-agent/build/logs";
    bool enable_debug_logging = true;
    bool simulate_block = true;
    std::string validation_strictness = "high";
    int max_processing_delay_ms = 10;
};

//===----------------------------------------------------------------------===//
// ZMQ Configuration  
//===----------------------------------------------------------------------===//
struct ZMQConfigNew {
    std::string endpoint = "tcp://localhost:5572";
    std::string topic = "BlockRequest";
    int recv_timeout_ms = 1000;
    int linger_ms = 1000;
    int reconnect_interval_ms = 1000;
    int max_reconnect_interval_ms = 30000;
    bool enable_reconnect = true;
    int high_water_mark = 1000;
    int monitor_interval_sec = 30;
};

//===----------------------------------------------------------------------===//
// IPSet Configuration
//===----------------------------------------------------------------------===//
struct IPSetConfigNew {
    std::string set_name = "ml_defender_blacklist_test";
    std::string set_type = "hash:ip";
    int hash_size = 1024;
    int max_elements = 1000;
    int timeout = 3600;
    std::string comment = "ML Defender TEST blocked IPs";
    std::string family = "inet";
    bool create_if_missing = true;
    bool flush_on_startup = false;
};

//===----------------------------------------------------------------------===//
// IPTables Configuration
//===----------------------------------------------------------------------===//
struct IPTablesConfigNew {
    std::string chain_name = "ML_DEFENDER_TEST";
    std::string default_policy = "ACCEPT";
    bool log_blocked = true;
    std::string log_prefix = "ML_DEFENDER_TEST_DROP: ";
    bool enable_rate_limiting = false;
    int rate_limit_connections = 100;
    bool create_chain = true;
    int insert_rule_position = 1;
};

//===----------------------------------------------------------------------===//
// Batch Processor Configuration
//===----------------------------------------------------------------------===//
struct BatchProcessorConfigNew {
    int batch_size_threshold = 10;
    int batch_time_threshold_ms = 1000;
    int max_pending_ips = 100;
    float min_confidence = 0.5f;
    bool enable_batching = true;
    bool flush_on_shutdown = true;
};

//===----------------------------------------------------------------------===//
// Validation Configuration
//===----------------------------------------------------------------------===//
struct ValidationConfig {
    bool validate_ip_addresses = true;
    bool validate_confidence_scores = true;
    float min_confidence_score = 0.5f;
    float max_confidence_score = 1.0f;
    std::vector<std::string> allowed_ip_ranges = {
        "192.168.0.0/16", "10.0.0.0/8", "172.16.0.0/12"
    };
    bool block_localhost = false;
    bool block_gateway = false;
};

//===----------------------------------------------------------------------===//
// Logging Configuration
//===----------------------------------------------------------------------===//
struct LoggingConfigNew {
    std::string level = "debug";
    bool console = true;
    bool syslog = false;
    std::string file = "/vagrant/logs/lab/firewall-agent.log";
    int max_file_size_mb = 10;
    int backup_count = 5;
    bool log_protobuf_messages = true;
    bool log_zmq_events = true;
    bool log_block_decisions = true;
    bool log_performance_metrics = true;
};
    //===----------------------------------------------------------------------===//
    // CSV Batch Logger Configuration (Day 59)
    //===----------------------------------------------------------------------===//
    struct CsvBatchLoggerConfig {
        bool enabled = false;
        std::string output_dir;
        int batch_size = 100;
        int batch_timeout_sec = 5;
    };
    //===----------------------------------------------------------------------===//
    // Etcd Configuration
    //===----------------------------------------------------------------------===//
    struct EtcdConfig {
        bool enabled = false;
        std::vector<std::string> endpoints;
        int connection_timeout_ms = 5000;
        int retry_attempts = 3;
        int retry_interval_ms = 1000;
        int heartbeat_interval_seconds = 30;
        int lease_ttl_seconds = 60;
    };

    //===----------------------------------------------------------------------===//
    // Transport Configuration (Day 23)
    //===----------------------------------------------------------------------===//
    struct CompressionConfig {
        bool enabled = false;
        bool decompression_only = true;
        std::string algorithm = "lz4";
    };

    struct EncryptionConfig {
        bool enabled = false;
        bool decryption_only = true;
        bool etcd_token_required = true;
        std::string algorithm = "chacha20-poly1305";
        std::string fallback_mode = "compressed_only";
    };

    struct TransportConfig {
        CompressionConfig compression;
        EncryptionConfig encryption;
    };

//===----------------------------------------------------------------------===//
// IRP Configuration (ADR-042 — auto-isolate via argus-network-isolate)
//===----------------------------------------------------------------------===//
struct IrpConfig {
    bool        auto_isolate           = false;  // sin política — siempre sobreescrito por isolate.json (única fuente de verdad)
    double      threat_score_threshold = 0.95;
    std::string isolate_interface      = "eth0";
    std::string isolate_config_path    = "/etc/ml-defender/firewall-acl-agent/isolate.json";
    std::string isolate_binary_path    = "/usr/local/bin/argus-network-isolate";
    std::vector<std::string> auto_isolate_event_types;
};
//===----------------------------------------------------------------------===//
// MAIN CONFIGURATION STRUCTURE
//===----------------------------------------------------------------------===//
struct FirewallAgentConfig {
    OperationConfig operation;
    ZMQConfigNew zmq;
    IPSetConfigNew ipset;
    std::map<std::string, IPSetConfigNew> ipsets;  // Multiple ipsets (blacklist, whitelist)
    IPTablesConfigNew iptables;
    BatchProcessorConfigNew batch_processor;
    ValidationConfig validation;
    LoggingConfigNew logging;
    EtcdConfig etcd;
    TransportConfig transport;  // ✅ Day 23: AÑADIR ESTA LÍNEA
    CsvBatchLoggerConfig csv_batch_logger;  // ✅ Day 59
    IrpConfig irp;                           // ADR-042 auto-isolate

    bool is_valid() const { return true; }
    std::vector<std::string> validate() const { return {}; }
};

//===----------------------------------------------------------------------===//
// ConfigLoader - Loads firewall.json (JSON is LAW, fail fast)
//===----------------------------------------------------------------------===//
class ConfigLoader {
public:
    // public para testabilidad directa — función pura de parseo (ADR-042, DEBT-IRP-AUTOISO-FALSE-001)
    static IrpConfig parse_irp(const std::string& isolate_json_path);
    // Load configuration from JSON file
    static FirewallAgentConfig load_from_file(const std::string& config_path,
                                                const std::string& allowed_prefix = "/etc/ml-defender/");
    
    // Validation
    static void validate_config(const FirewallAgentConfig& config);
    static void fail_fast(const std::string& error_message);
    static void log_config_summary(const FirewallAgentConfig& config);

private:
    // JSON parsing helpers
    static OperationConfig parse_operation(const Json::Value& json);
    static ZMQConfigNew parse_zmq(const Json::Value& json);
    static IPSetConfigNew parse_ipset(const Json::Value& json);
    static std::map<std::string, IPSetConfigNew> parse_ipsets(const Json::Value& json);
    static IPTablesConfigNew parse_iptables(const Json::Value& json);
    static BatchProcessorConfigNew parse_batch_processor(const Json::Value& json);
    static ValidationConfig parse_validation(const Json::Value& json);
    static LoggingConfigNew parse_logging(const Json::Value& json);
    static EtcdConfig parse_etcd(const Json::Value& json);
    static TransportConfig parse_transport(const Json::Value& json);  // ✅ Day 23: AÑADIR

    // Utility helpers
    template<typename T>
    static T get_required(const Json::Value& json, const std::string& key, 
                         const std::string& context, const std::string& config_path);
    
    template<typename T>
    static T get_optional(const Json::Value& json, const std::string& key, const T& default_value);
    
    static std::vector<std::string> parse_string_array(const Json::Value& array);

    static CsvBatchLoggerConfig parse_csv_batch_logger(const Json::Value& json);
};

} // namespace mldefender::firewall
