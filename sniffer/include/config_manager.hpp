#pragma once
// sniffer/include/config_manager.hpp
#include <string>
#include <vector>
#include <memory>
#include <stdexcept>
#include <unordered_map>
#include <json/json.h>

namespace sniffer {

// Exception para errores de configuración
class ConfigException : public std::runtime_error {
public:
    explicit ConfigException(const std::string& message)
        : std::runtime_error("Configuration Error: " + message) {}
};

// Profile configuration
struct ProfileConfig {
    std::string capture_interface;
    bool promiscuous_mode;
    bool af_xdp_enabled;
    int worker_threads;
    int compression_level;
    bool cpu_affinity_enabled = false;
};

// Buffer configuration
struct BufferConfig {
    size_t ring_buffer_entries;
    size_t user_processing_queue_depth;
    size_t protobuf_serialize_buffer_size;
    size_t zmq_send_buffer_size;
    size_t flow_state_buffer_entries;
    size_t statistics_buffer_entries;
    size_t batch_processing_size;
};

// CPU affinity configuration
struct CpuAffinityConfig {
    bool enabled;
    std::vector<int> ring_consumers;
    std::vector<int> processors;
    std::vector<int> zmq_senders;
    std::vector<int> statistics;
};

// Threading configuration
struct ThreadingConfig {
    int ring_consumer_threads;
    int feature_processor_threads;
    int zmq_sender_threads;
    int statistics_collector_threads;
    int total_worker_threads;
    CpuAffinityConfig cpu_affinity;
    std::unordered_map<std::string, std::string> thread_priorities;
};

// AF_XDP configuration
struct AfXdpConfig {
    bool enabled;
    int queue_id;
    size_t frame_size;
    size_t fill_ring_size;
    size_t comp_ring_size;
    size_t tx_ring_size;
    size_t rx_ring_size;
    size_t umem_size;
};

// Capture configuration
struct CaptureConfig {
    std::string interface;
    std::string kernel_interface;  // optional
    std::string user_interface;    // optional
    std::string mode;
    std::vector<std::string> xdp_flags;
    bool promiscuous_mode;
    std::string filter_expression;
    size_t buffer_size;
    size_t min_packet_size;
    size_t max_packet_size;
    std::vector<int> excluded_ports;
    std::vector<std::string> included_protocols;
    AfXdpConfig af_xdp;
};

// Kernel space configuration
struct KernelSpaceConfig {
    std::string ebpf_program;
    std::string xdp_mode;
    size_t ring_buffer_size;
    size_t max_flows_in_kernel;
    int flow_timeout_seconds;
    std::vector<std::string> kernel_features;

    struct Performance {
        int cpu_budget_us_per_packet;
        size_t max_instructions_per_program;
        size_t map_update_batch_size;
    } performance;
};

// Feature group configuration
struct FeatureGroupConfig {
    int count;
    std::string reference;
    std::string description;
};

// User space configuration
struct UserSpaceConfig {
    size_t flow_table_size;
    size_t time_window_buffer_size;
    std::vector<std::string> user_features;

    struct MemoryManagement {
        std::string flow_eviction_policy;
        size_t max_memory_usage_mb;
        int gc_interval_seconds;
    } memory_management;
};

// Time windows configuration
struct TimeWindowsConfig {
    int flow_tracking_window_seconds;
    int statistics_collection_window_seconds;
    int feature_aggregation_window_seconds;
    int cleanup_interval_seconds;
    size_t max_flows_per_window;
    int window_overlap_seconds;
};

// Network configuration
struct NetworkConfig {
    struct OutputSocket {
        std::string address;
        int port;
        std::string mode;
        std::string socket_type;
        int high_water_mark;
    } output_socket;
};

// Socket pool configuration
struct SocketPoolConfig {
    int push_sockets;
    std::string load_balancing;
    bool failover_enabled;
};

// Queue management configuration
struct QueueManagementConfig {
    int internal_queues;
    int queue_size;
    int queue_timeout_ms;
    std::string overflow_policy;
};

// ZMQ connection settings
struct ZmqConnectionConfig {
    int sndhwm;
    int linger_ms;
    int send_timeout_ms;
    int rcvhwm;
    int recv_timeout_ms;
    int tcp_keepalive;
    size_t sndbuf;
    size_t rcvbuf;
    int reconnect_interval_ms;
    int max_reconnect_attempts;
};

// ZMQ batch processing
struct ZmqBatchConfig {
    bool enabled;
    int batch_size;
    int batch_timeout_ms;
    int max_batches_queued;
};

// ZMQ configuration
struct ZmqConfig {
    int worker_threads;
    int io_thread_pools;
    SocketPoolConfig socket_pools;
    QueueManagementConfig queue_management;
    ZmqConnectionConfig connection_settings;
    ZmqBatchConfig batch_processing;
};

// Compression configuration
struct CompressionConfig {
    bool enabled;
    std::string algorithm;
    int level;
    size_t min_compress_size;
    double compression_ratio_threshold;
    bool adaptive_compression = false;
};

// Encryption configuration
struct EncryptionConfig {
    bool enabled;
    bool etcd_token_required;
    std::string algorithm;
    int key_size;
    int key_rotation_hours;
    std::string fallback_mode;
    bool zmq_curve_enabled;
    std::string curve_server_key;
    std::string curve_secret_key;
};

// Transport configuration
struct TransportConfig {
    CompressionConfig compression;
    EncryptionConfig encryption;
};

// etcd configuration
struct EtcdConfig {
    bool enabled;
    std::vector<std::string> endpoints;
    int connection_timeout_ms;
    int retry_attempts;
    int retry_interval_ms;
    std::string crypto_token_path;
    std::string config_sync_path;
    bool required_for_encryption;
    std::string fallback_mode;
    int heartbeat_interval_seconds;
    int lease_ttl_seconds;
};

// Monitoring configuration
struct MonitoringConfig {
    int stats_interval_seconds;
    bool performance_tracking;

    struct KernelMetrics {
        bool ebpf_program_stats;
        bool map_utilization;
        bool instruction_count;
        bool processing_time_per_packet;
    } kernel_metrics;

    struct UserMetrics {
        bool feature_extraction_rate;
        bool queue_depth;
        bool memory_usage;
        bool thread_utilization;
        bool compression_ratio;
        bool zmq_throughput;
    } user_metrics;

    struct Alerts {
        double max_drop_rate_percent;
        int max_queue_usage_percent;
        size_t max_memory_usage_mb;
        int max_cpu_usage_percent;
        int max_processing_latency_us;
        double min_compression_ratio;
    } alerts;
};

// Processing configuration
struct ProcessingConfig {
    struct KernelProcessing {
        size_t max_map_entries;
        size_t flow_hash_table_size;
        size_t counter_map_size;
        int stats_collection_interval_ms;
    } kernel_processing;

    struct UserProcessing {
        size_t internal_queue_size;
        int queue_timeout_seconds;
        int batch_size;
        bool lockfree_queues;
        bool numa_aware_allocation;
        bool memory_prefaulting;
    } user_processing;

    struct FeatureExtraction {
        bool enabled;
        bool extract_all_features;
        bool cache_flow_states;
        int flow_timeout_seconds;
        size_t max_concurrent_flows;
        std::string statistics_engine;
        bool simd_optimization;
    } feature_extraction;
};

// Logging configuration
struct LoggingConfig {
    std::string level;
    std::string file;
    int max_file_size_mb;
    int backup_count;
    bool include_performance_logs;
    bool include_compression_stats;
    bool include_thread_stats;
};

// Protobuf configuration
struct ProtobufConfig {
    std::string schema_version;
    bool validate_before_send;
    size_t max_event_size_bytes;
    int serialization_timeout_ms;
    int pool_size;
    bool reuse_objects;
};

// Security configuration
struct SecurityConfig {
    struct InputValidation {
        bool enabled;
        size_t max_packet_size_bytes;
        bool validate_ip_addresses;
        bool validate_ports;
        bool sanitize_inputs;
    } input_validation;
};

// Backpressure configuration
struct BackpressureConfig {
    bool enabled;

    struct KernelBackpressure {
        std::string ring_buffer_full_action;
    } kernel_backpressure;

    struct UserBackpressure {
        int max_drops_per_second;
        bool adaptive_rate_limiting;
    } user_backpressure;

    struct CircuitBreaker {
        bool enabled;
        int failure_threshold;
        int recovery_timeout;
    } circuit_breaker;
};

// Auto-tuner configuration
struct AutoTunerConfig {
    bool enabled;
    bool calibration_on_startup;
    int benchmark_iterations;
    int recalibration_interval_hours;
    double safety_margin_factor;
    std::string feature_placement_strategy;
};

// ML Defender configuration (Phase 1, Day 5)
struct MLDefenderConfig {
    struct Thresholds {
        float ddos;
        float ransomware;
        float traffic;
        float internal;
    } thresholds;

    struct Validation {
        float min_threshold;
        float max_threshold;
        float fallback_threshold;
    } validation;
};

// Main configuration structure
struct SnifferConfig {
    // Component info
    std::string component_name;
    std::string version;
    std::string mode;
    std::string kernel_version_required;
    std::string node_id;
    std::string cluster_name;

    // Profile management
    std::unordered_map<std::string, ProfileConfig> profiles;
    std::string active_profile;

    // Configuration sections
    BufferConfig buffers;
    ThreadingConfig threading;
    CaptureConfig capture;
    KernelSpaceConfig kernel_space;
    UserSpaceConfig user_space;
    std::unordered_map<std::string, FeatureGroupConfig> feature_groups;
    TimeWindowsConfig sniffer_time_windows;
    NetworkConfig network;
    ZmqConfig zmq;
    TransportConfig transport;
    EtcdConfig etcd;
    ProcessingConfig processing;
    AutoTunerConfig auto_tuner;
    MonitoringConfig monitoring;
    LoggingConfig logging;
    ProtobufConfig protobuf;
    SecurityConfig security;
    BackpressureConfig backpressure;
    MLDefenderConfig ml_defender;

    // Validation methods
    bool is_valid() const;
    std::vector<std::string> validate() const;

    // Profile methods
    const ProfileConfig& get_active_profile() const;
    void apply_profile_overrides();
};

// Enhanced ConfigManager
class ConfigManager {
public:
    // Load configuration from JSON file
    static std::unique_ptr<SnifferConfig> load_from_file(const std::string& config_path);

    // Profile management
    static void apply_profile(SnifferConfig& config, const std::string& profile_name);

    // Validation
    static void validate_config(const SnifferConfig& config);
    static void validate_threading_config(const ThreadingConfig& threading);
    static void validate_zmq_config(const ZmqConfig& zmq);
    static void validate_transport_config(const TransportConfig& transport);

    // Utilities
    static void fail_fast(const std::string& error_message);
    static void log_config_summary(const SnifferConfig& config);

private:
    // JSON parsing helpers
    static ProfileConfig parse_profile(const Json::Value& profile_json);
    static BufferConfig parse_buffers(const Json::Value& buffers_json);
    static ThreadingConfig parse_threading(const Json::Value& threading_json);
    static CaptureConfig parse_capture(const Json::Value& capture_json);
    static KernelSpaceConfig parse_kernel_space(const Json::Value& kernel_json);
    static UserSpaceConfig parse_user_space(const Json::Value& user_json);
    static TimeWindowsConfig parse_time_windows(const Json::Value& windows_json);
    static NetworkConfig parse_network(const Json::Value& network_json);
    static ZmqConfig parse_zmq(const Json::Value& zmq_json);
    static TransportConfig parse_transport(const Json::Value& transport_json);
    static EtcdConfig parse_etcd(const Json::Value& etcd_json);
    static ProcessingConfig parse_processing(const Json::Value& processing_json);
    static MonitoringConfig parse_monitoring(const Json::Value& monitoring_json);
    static LoggingConfig parse_logging(const Json::Value& logging_json);
    static ProtobufConfig parse_protobuf(const Json::Value& protobuf_json);
    static SecurityConfig parse_security(const Json::Value& security_json);
    static BackpressureConfig parse_backpressure(const Json::Value& backpressure_json);
    static AutoTunerConfig parse_auto_tuner(const Json::Value& auto_tuner_json);
    static MLDefenderConfig parse_ml_defender(const Json::Value& ml_defender_json);
    // Validation helpers
    static std::vector<int> parse_int_array(const Json::Value& array_json);
    static std::vector<std::string> parse_string_array(const Json::Value& array_json);
    static std::unordered_map<std::string, std::string> parse_string_map(const Json::Value& map_json);
};

} // namespace sniffer