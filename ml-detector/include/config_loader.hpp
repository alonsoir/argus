#pragma once
// ml_detector/include/config_loader.hpp
#include <string>
#include <vector>
#include <map>
#include <nlohmann/json.hpp>

namespace ml_detector {

/**
 * @brief Configuración COMPLETA del ML Detector Tricapa
 * Estructura 1:1 con ml_detector_config.json - JSON ES LA LEY
 */
struct DetectorConfig {
    // Component
    struct {
        std::string name;
        std::string version;
        std::string mode;
        std::string onnx_runtime_version;
    } component;
    
    std::string node_id;
    std::string cluster_name;
    
    // Profiles (lab, cloud, bare_metal)
    struct Profile {
        int worker_threads;
        int input_queue_size;
        int output_queue_size;
        int compression_level;
        bool enable_all_models;
        bool cpu_affinity_enabled = false;
    };
    std::map<std::string, Profile> profiles;
    std::string active_profile;
    
    // Network
    struct {
        struct {
            std::string endpoint;
            std::string mode;
            std::string socket_type;
            int high_water_mark;
        } input_socket;
        struct {
            std::string endpoint;
            std::string mode;
            std::string socket_type;
            int high_water_mark;
        } output_socket;
    } network;
    
    // ZMQ
    struct {
        int worker_threads;
        int io_thread_pools;
        struct {
            int sndhwm;
            int rcvhwm;
            int linger_ms;
            int send_timeout_ms;
            int recv_timeout_ms;
            int sndbuf;
            int rcvbuf;
            int immediate;
        } connection_settings;
        struct {
            int input_queue_size;
            int output_queue_size;
            int queue_timeout_ms;
            std::string overflow_policy;
        } queue_management;
    } zmq;
    
    // Transport
    struct {
        struct {
            bool enabled;
            std::string algorithm;
            int level;
            int min_compress_size;
            float compression_ratio_threshold;
            bool adaptive_compression;
        } compression;
        struct {
            bool enabled;
            bool etcd_token_required;
            std::string algorithm;
            int key_size;
            int key_rotation_hours;
            std::string fallback_mode;
        } encryption;
    } transport;
    
    // ETCD
    struct {
        bool enabled;
        std::vector<std::string> endpoints;
        int connection_timeout_ms;
        int retry_attempts;
        int retry_interval_ms;
        std::string crypto_token_path;
        std::string config_sync_path;
        std::string service_registration_path;
        bool required_for_encryption;
        std::string fallback_mode;
        int heartbeat_interval_seconds;
        int lease_ttl_seconds;
    } etcd;
    
    // Threading
    struct {
        int worker_threads;
        int protobuf_deserializer_threads;
        int feature_extractor_threads;
        int ml_inference_threads;
        int zmq_sender_threads;
        int total_worker_threads;
        struct {
            bool enabled;
            std::vector<int> deserializers;
            std::vector<int> feature_extractors;
            std::vector<int> ml_inference;
            std::vector<int> zmq_senders;
        } cpu_affinity;
        struct {
            std::string deserializers;
            std::string feature_extractors;
            std::string ml_inference;
            std::string zmq_senders;
        } thread_priorities;
    } threading;
    
    // ML
    struct {
        std::string models_base_dir;
        
        struct {
            float level1_attack;
            float level2_ddos;
            float level2_ransomware;
            float level3_anomaly;
            float level3_web;
            float level3_internal;
        } thresholds;
        
        struct ModelConfig {
            bool enabled;
            std::string name;
            std::string model_file;
            int features_count;
            std::string model_type;
            std::string description;
            bool requires_scaling;
            int timeout_ms;
            std::string scaler_file;  // Optional for level1
        };
        
        ModelConfig level1;
        
        struct {
            ModelConfig ddos;
            ModelConfig ransomware;
        } level2;
        
        struct {
            ModelConfig internal;
            ModelConfig web;
        } level3;
        
        struct {
            int batch_size;
            bool enable_model_warmup;
            int warmup_iterations;
            std::string onnx_optimization_level;
            int inter_op_threads;
            int intra_op_threads;
            bool enable_cpu_mem_arena;
            bool enable_profiling;
        } inference;
        
        struct {
            bool validate_features;
            bool pad_missing;
            bool log_extraction_errors;
            bool cache_extractions;
            int cache_size;
            bool simd_optimization;
        } feature_extraction;
        
        struct {
            int min_models_required;
            bool continue_with_partial_models;
            bool fallback_to_heuristics;
            bool log_degraded_operations;
        } degraded_mode;
    } ml;
    
    // Processing
    struct {
        int input_queue_size;
        int output_queue_size;
        int queue_timeout_ms;
        struct {
            bool enabled;
            int batch_size;
            int batch_timeout_ms;
        } batch_processing;
        bool lockfree_queues;
        bool numa_aware_allocation;
        bool memory_prefaulting;
    } processing;
    
    // Backpressure
    struct {
        bool enabled;
        float activation_threshold;
        int max_drops_per_second;
        bool adaptive_rate_limiting;
        struct {
            bool enabled;
            int failure_threshold;
            int recovery_timeout_seconds;
        } circuit_breaker;
    } backpressure;
    
    // Monitoring
    struct {
        int stats_interval_seconds;
        bool performance_tracking;
        struct {
            bool inference_time;
            bool model_accuracy;
            bool feature_importance;
            bool predictions_per_second;
            bool model_load_time;
        } ml_metrics;
        struct {
            bool queue_depth;
            bool memory_usage;
            bool thread_utilization;
            bool compression_ratio;
            bool zmq_throughput;
        } system_metrics;
        struct {
            int max_inference_latency_ms;
            int max_queue_usage_percent;
            int max_memory_usage_mb;
            int max_cpu_usage_percent;
            float min_compression_ratio;
            int max_model_failures_per_minute;
        } alerts;
    } monitoring;
    
    // Logging
    struct {
        std::string level;
        std::string file;
        int max_file_size_mb;
        int backup_count;
        bool include_performance_logs;
        bool include_compression_stats;
        bool include_thread_stats;
        bool include_ml_predictions;
        bool log_inference_scores;
        bool log_feature_extraction;
    } logging;
    
    // Protobuf
    struct {
        std::string schema_version;
        bool validate_before_processing;
        bool validate_after_enrichment;
        int max_event_size_bytes;
        int deserialization_timeout_ms;
        int serialization_timeout_ms;
        int pool_size;
        bool reuse_objects;
    } protobuf;
    
    // Security
    struct {
        struct {
            bool enabled;
            bool validate_protobuf_schema;
            bool sanitize_features;
            bool reject_malformed_events;
            double max_feature_value;
            int min_features_required;
        } input_validation;
    } security;
    
    // Performance
    struct {
        bool enable_zero_copy;
        bool enable_memory_pools;
        bool preallocate_buffers;
        int buffer_pool_size;
        bool enable_simd;
        bool enable_avx2;
        int cache_line_size;
    } performance;

    // CSV Writer
    struct {
        std::string base_dir;
        float min_score_threshold;
        int max_events_per_file;
    } csv_writer;

    // Correlation Writer (bronce correlation_v1) — DAY 201/203
    // DEBT-CONFIG-BRONZE-HARDCODE-001 + DEBT-CIRCUIT-BRONZE-ROTATION-FOLLOW-001
    struct {
        std::string base_dir;
        int rotation_seconds;
    } correlation_writer;

    // Scoring thresholds (dual-score architecture)
    struct {
        float divergence_warn_threshold;   // score_divergence > X → DIVERGENCE source
        float divergence_high_threshold;   // investigation_priority HIGH
        float malicious_threshold;         // final_score >= X → "MALICIOUS" / "DROP"
        float requires_rag_threshold;      // final_score >= X → requires_rag_analysis
    } scoring;
};

/**
 * @brief ConfigLoader - Lee ml_detector_config.json COMPLETO
 * REGLA: JSON es LA LEY, fail fast si algo falta
 */
class ConfigLoader {
public:
    explicit ConfigLoader(const std::string& config_path);
    DetectorConfig load();
    static void print_config(const DetectorConfig& config, bool verbose = false);
    
private:
    std::string config_path_;
    nlohmann::json json_;
    
    // Helpers
    template<typename T>
    T get_required(const nlohmann::json& j, const std::string& key, const std::string& context);
    
    template<typename T>
    T get_optional(const nlohmann::json& j, const std::string& key, const T& default_value);
};

} // namespace ml_detector