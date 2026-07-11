#include "config_loader.hpp"
#include <fstream>
#include <stdexcept>
#include <iostream>
#include <iomanip>

namespace ml_detector {

ConfigLoader::ConfigLoader(const std::string& config_path)
    : config_path_(config_path) {
}

template<typename T>
T ConfigLoader::get_required(const nlohmann::json& j, const std::string& key, const std::string& context) {
    if (!j.contains(key)) {
        throw std::invalid_argument(
            "❌ MISSING REQUIRED FIELD: '" + key + "' in [" + context + "]\n"
            "   Config file: " + config_path_ + "\n"
            "   Fix: Add '" + key + "' to the JSON and restart"
        );
    }
    
    try {
        return j[key].get<T>();
    } catch (const nlohmann::json::exception& e) {
        throw std::invalid_argument(
            "❌ INVALID TYPE: '" + key + "' in [" + context + "]\n"
            "   Expected type doesn't match JSON value\n"
            "   Error: " + std::string(e.what())
        );
    }
}

template<typename T>
T ConfigLoader::get_optional(const nlohmann::json& j, const std::string& key, const T& default_value) {
    if (!j.contains(key)) {
        return default_value;
    }
    try {
        return j[key].get<T>();
    } catch (...) {
        return default_value;
    }
}

DetectorConfig ConfigLoader::load() {
    // Abrir archivo JSON
    std::ifstream file(config_path_);
    if (!file.is_open()) {
        throw std::runtime_error(
            "❌ CANNOT OPEN CONFIG FILE: " + config_path_ + "\n"
            "   Check that the file exists and has read permissions"
        );
    }
    
    // Parsear JSON
    try {
        file >> json_;
    } catch (const nlohmann::json::exception& e) {
        throw std::runtime_error(
            "❌ INVALID JSON in " + config_path_ + "\n"
            "   Parse error: " + std::string(e.what()) + "\n"
            "   Fix the JSON syntax and restart"
        );
    }
    
    DetectorConfig config{};  // value-init: sin esto, un campo no parseado queda INDETERMINADO (DEBT-CONFIG-L3-...-001)
    
    // ========================================
    // Component
    // ========================================
    {
        auto& comp = json_["component"];
        config.component.name = get_required<std::string>(comp, "name", "component");
        config.component.version = get_required<std::string>(comp, "version", "component");
        config.component.mode = get_required<std::string>(comp, "mode", "component");
        config.component.onnx_runtime_version = get_required<std::string>(comp, "onnx_runtime_version", "component");
    }
    
    config.node_id = get_required<std::string>(json_, "node_id", "root");
    config.cluster_name = get_required<std::string>(json_, "cluster_name", "root");
    
    // ========================================
    // Profiles
    // ========================================
    {
        auto& profiles = json_["profiles"];
        for (auto& [profile_name, profile_json] : profiles.items()) {
            DetectorConfig::Profile p;
            p.worker_threads = get_required<int>(profile_json, "worker_threads", "profiles." + profile_name);
            p.input_queue_size = get_required<int>(profile_json, "input_queue_size", "profiles." + profile_name);
            p.output_queue_size = get_required<int>(profile_json, "output_queue_size", "profiles." + profile_name);
            p.compression_level = get_required<int>(profile_json, "compression_level", "profiles." + profile_name);
            p.enable_all_models = get_required<bool>(profile_json, "enable_all_models", "profiles." + profile_name);
            p.cpu_affinity_enabled = get_optional<bool>(profile_json, "cpu_affinity_enabled", false);
            config.profiles[profile_name] = p;
        }
        
        config.active_profile = get_required<std::string>(json_, "profile", "root");
        
        if (config.profiles.find(config.active_profile) == config.profiles.end()) {
            throw std::invalid_argument(
                "❌ INVALID PROFILE: '" + config.active_profile + "' not found in profiles section\n"
                "   Available profiles: lab, cloud, bare_metal"
            );
        }
    }
    
    // ========================================
    // Network
    // ========================================
    {
        auto& net = json_["network"];
        auto& in_sock = net["input_socket"];
        config.network.input_socket.endpoint = get_required<std::string>(in_sock, "endpoint", "network.input_socket");
        config.network.input_socket.mode = get_required<std::string>(in_sock, "mode", "network.input_socket");
        config.network.input_socket.socket_type = get_required<std::string>(in_sock, "socket_type", "network.input_socket");
        config.network.input_socket.high_water_mark = get_required<int>(in_sock, "high_water_mark", "network.input_socket");
        
        auto& out_sock = net["output_socket"];
        config.network.output_socket.endpoint = get_required<std::string>(out_sock, "endpoint", "network.output_socket");
        config.network.output_socket.mode = get_required<std::string>(out_sock, "mode", "network.output_socket");
        config.network.output_socket.socket_type = get_required<std::string>(out_sock, "socket_type", "network.output_socket");
        config.network.output_socket.high_water_mark = get_required<int>(out_sock, "high_water_mark", "network.output_socket");
    }
    
    // ========================================
    // ZMQ
    // ========================================
    {
        auto& zmq = json_["zmq"];
        config.zmq.worker_threads = get_required<int>(zmq, "worker_threads", "zmq");
        config.zmq.io_thread_pools = get_required<int>(zmq, "io_thread_pools", "zmq");
        
        auto& conn = zmq["connection_settings"];
        config.zmq.connection_settings.sndhwm = get_required<int>(conn, "sndhwm", "zmq.connection_settings");
        config.zmq.connection_settings.rcvhwm = get_required<int>(conn, "rcvhwm", "zmq.connection_settings");
        config.zmq.connection_settings.linger_ms = get_required<int>(conn, "linger_ms", "zmq.connection_settings");
        config.zmq.connection_settings.send_timeout_ms = get_required<int>(conn, "send_timeout_ms", "zmq.connection_settings");
        config.zmq.connection_settings.recv_timeout_ms = get_required<int>(conn, "recv_timeout_ms", "zmq.connection_settings");
        config.zmq.connection_settings.sndbuf = get_required<int>(conn, "sndbuf", "zmq.connection_settings");
        config.zmq.connection_settings.rcvbuf = get_required<int>(conn, "rcvbuf", "zmq.connection_settings");
        config.zmq.connection_settings.immediate = get_required<int>(conn, "immediate", "zmq.connection_settings");
        
        auto& queue = zmq["queue_management"];
        config.zmq.queue_management.input_queue_size = get_required<int>(queue, "input_queue_size", "zmq.queue_management");
        config.zmq.queue_management.output_queue_size = get_required<int>(queue, "output_queue_size", "zmq.queue_management");
        config.zmq.queue_management.queue_timeout_ms = get_required<int>(queue, "queue_timeout_ms", "zmq.queue_management");
        config.zmq.queue_management.overflow_policy = get_required<std::string>(queue, "overflow_policy", "zmq.queue_management");
    }
    
    // ========================================
    // Transport
    // ========================================
    {
        auto& transport = json_["transport"];
        
        auto& comp = transport["compression"];
        config.transport.compression.enabled = get_required<bool>(comp, "enabled", "transport.compression");
        config.transport.compression.algorithm = get_required<std::string>(comp, "algorithm", "transport.compression");
        config.transport.compression.level = get_required<int>(comp, "level", "transport.compression");
        config.transport.compression.min_compress_size = get_required<int>(comp, "min_compress_size", "transport.compression");
        config.transport.compression.compression_ratio_threshold = get_required<float>(comp, "compression_ratio_threshold", "transport.compression");
        config.transport.compression.adaptive_compression = get_required<bool>(comp, "adaptive_compression", "transport.compression");
        
        auto& enc = transport["encryption"];
        config.transport.encryption.enabled = get_required<bool>(enc, "enabled", "transport.encryption");
        config.transport.encryption.etcd_token_required = get_required<bool>(enc, "etcd_token_required", "transport.encryption");
        config.transport.encryption.algorithm = get_required<std::string>(enc, "algorithm", "transport.encryption");
        config.transport.encryption.key_size = get_required<int>(enc, "key_size", "transport.encryption");
        config.transport.encryption.key_rotation_hours = get_required<int>(enc, "key_rotation_hours", "transport.encryption");
        config.transport.encryption.fallback_mode = get_required<std::string>(enc, "fallback_mode", "transport.encryption");
    }
    
    // ========================================
    // ETCD
    // ========================================
    {
        auto& etcd = json_["etcd"];
        config.etcd.enabled = get_required<bool>(etcd, "enabled", "etcd");
        config.etcd.endpoints = get_required<std::vector<std::string>>(etcd, "endpoints", "etcd");
        config.etcd.connection_timeout_ms = get_required<int>(etcd, "connection_timeout_ms", "etcd");
        config.etcd.retry_attempts = get_required<int>(etcd, "retry_attempts", "etcd");
        config.etcd.retry_interval_ms = get_required<int>(etcd, "retry_interval_ms", "etcd");
        config.etcd.crypto_token_path = get_required<std::string>(etcd, "crypto_token_path", "etcd");
        config.etcd.config_sync_path = get_required<std::string>(etcd, "config_sync_path", "etcd");
        config.etcd.service_registration_path = get_required<std::string>(etcd, "service_registration_path", "etcd");
        config.etcd.required_for_encryption = get_required<bool>(etcd, "required_for_encryption", "etcd");
        config.etcd.fallback_mode = get_required<std::string>(etcd, "fallback_mode", "etcd");
        config.etcd.heartbeat_interval_seconds = get_required<int>(etcd, "heartbeat_interval_seconds", "etcd");
        config.etcd.lease_ttl_seconds = get_required<int>(etcd, "lease_ttl_seconds", "etcd");
    }
    
    // ========================================
    // Threading
    // ========================================
    {
        auto& thread = json_["threading"];
        config.threading.worker_threads = get_required<int>(thread, "worker_threads", "threading");
        config.threading.protobuf_deserializer_threads = get_required<int>(thread, "protobuf_deserializer_threads", "threading");
        config.threading.feature_extractor_threads = get_required<int>(thread, "feature_extractor_threads", "threading");
        config.threading.ml_inference_threads = get_required<int>(thread, "ml_inference_threads", "threading");
        config.threading.zmq_sender_threads = get_required<int>(thread, "zmq_sender_threads", "threading");
        config.threading.total_worker_threads = get_required<int>(thread, "total_worker_threads", "threading");
        
        auto& affinity = thread["cpu_affinity"];
        config.threading.cpu_affinity.enabled = get_required<bool>(affinity, "enabled", "threading.cpu_affinity");
        config.threading.cpu_affinity.deserializers = get_required<std::vector<int>>(affinity, "deserializers", "threading.cpu_affinity");
        config.threading.cpu_affinity.feature_extractors = get_required<std::vector<int>>(affinity, "feature_extractors", "threading.cpu_affinity");
        config.threading.cpu_affinity.ml_inference = get_required<std::vector<int>>(affinity, "ml_inference", "threading.cpu_affinity");
        config.threading.cpu_affinity.zmq_senders = get_required<std::vector<int>>(affinity, "zmq_senders", "threading.cpu_affinity");
        
        auto& priorities = thread["thread_priorities"];
        config.threading.thread_priorities.deserializers = get_required<std::string>(priorities, "deserializers", "threading.thread_priorities");
        config.threading.thread_priorities.feature_extractors = get_required<std::string>(priorities, "feature_extractors", "threading.thread_priorities");
        config.threading.thread_priorities.ml_inference = get_required<std::string>(priorities, "ml_inference", "threading.thread_priorities");
        config.threading.thread_priorities.zmq_senders = get_required<std::string>(priorities, "zmq_senders", "threading.thread_priorities");
    }
    
    // ========================================
    // ML
    // ========================================
    {
        auto& ml = json_["ml"];
        config.ml.models_base_dir = get_required<std::string>(ml, "models_base_dir", "ml");
        
        // Thresholds
        auto& thresh = ml["thresholds"];
        config.ml.thresholds.level1_attack = get_required<float>(thresh, "level1_attack", "ml.thresholds");
        config.ml.thresholds.level2_ddos = get_required<float>(thresh, "level2_ddos", "ml.thresholds");
        config.ml.thresholds.level2_ransomware = get_required<float>(thresh, "level2_ransomware", "ml.thresholds");
        config.ml.thresholds.level3_anomaly = get_required<float>(thresh, "level3_anomaly", "ml.thresholds");
        config.ml.thresholds.level3_web = get_required<float>(thresh, "level3_web", "ml.thresholds");
        config.ml.thresholds.level3_internal = get_required<float>(thresh, "level3_internal", "ml.thresholds");
        
        // Level 1
        auto& l1 = ml["level1"];
        config.ml.level1.enabled = get_required<bool>(l1, "enabled", "ml.level1");
        config.ml.level1.name = get_required<std::string>(l1, "name", "ml.level1");
        config.ml.level1.model_file = get_required<std::string>(l1, "model_file", "ml.level1");
        config.ml.level1.scaler_file = get_optional<std::string>(l1, "scaler_file", "");
        config.ml.level1.features_count = get_required<int>(l1, "features_count", "ml.level1");
        config.ml.level1.model_type = get_required<std::string>(l1, "model_type", "ml.level1");
        config.ml.level1.description = get_required<std::string>(l1, "description", "ml.level1");
        config.ml.level1.requires_scaling = get_required<bool>(l1, "requires_scaling", "ml.level1");
        config.ml.level1.timeout_ms = get_required<int>(l1, "timeout_ms", "ml.level1");
        
        // Level 2
        auto& l2 = ml["level2"];
        
        auto& l2ddos = l2["ddos"];
        config.ml.level2.ddos.enabled = get_required<bool>(l2ddos, "enabled", "ml.level2.ddos");
        config.ml.level2.ddos.name = get_required<std::string>(l2ddos, "name", "ml.level2.ddos");
        config.ml.level2.ddos.model_file = get_required<std::string>(l2ddos, "model_file", "ml.level2.ddos");
        config.ml.level2.ddos.features_count = get_required<int>(l2ddos, "features_count", "ml.level2.ddos");
        config.ml.level2.ddos.model_type = get_required<std::string>(l2ddos, "model_type", "ml.level2.ddos");
        config.ml.level2.ddos.description = get_required<std::string>(l2ddos, "description", "ml.level2.ddos");
        config.ml.level2.ddos.requires_scaling = get_required<bool>(l2ddos, "requires_scaling", "ml.level2.ddos");
        config.ml.level2.ddos.timeout_ms = get_required<int>(l2ddos, "timeout_ms", "ml.level2.ddos");
        config.ml.level2.ddos.scaler_file = "";
        
        auto& l2ransom = l2["ransomware"];
        config.ml.level2.ransomware.enabled = get_required<bool>(l2ransom, "enabled", "ml.level2.ransomware");
        config.ml.level2.ransomware.name = get_required<std::string>(l2ransom, "name", "ml.level2.ransomware");
        config.ml.level2.ransomware.model_file = get_required<std::string>(l2ransom, "model_file", "ml.level2.ransomware");
        config.ml.level2.ransomware.features_count = get_required<int>(l2ransom, "features_count", "ml.level2.ransomware");
        config.ml.level2.ransomware.model_type = get_required<std::string>(l2ransom, "model_type", "ml.level2.ransomware");
        config.ml.level2.ransomware.description = get_required<std::string>(l2ransom, "description", "ml.level2.ransomware");
        config.ml.level2.ransomware.requires_scaling = get_required<bool>(l2ransom, "requires_scaling", "ml.level2.ransomware");
        config.ml.level2.ransomware.timeout_ms = get_required<int>(l2ransom, "timeout_ms", "ml.level2.ransomware");
        config.ml.level2.ransomware.scaler_file = "";
        
        // Level 3
        auto& l3 = ml["level3"];
        
        auto& l3int = l3["internal"];
        config.ml.level3.internal.enabled = get_required<bool>(l3int, "enabled", "ml.level3.internal");
        config.ml.level3.internal.name = get_required<std::string>(l3int, "name", "ml.level3.internal");
        config.ml.level3.internal.model_file = get_required<std::string>(l3int, "model_file", "ml.level3.internal");
        config.ml.level3.internal.features_count = get_required<int>(l3int, "features_count", "ml.level3.internal");
        config.ml.level3.internal.model_type = get_required<std::string>(l3int, "model_type", "ml.level3.internal");
        config.ml.level3.internal.description = get_required<std::string>(l3int, "description", "ml.level3.internal");
        config.ml.level3.internal.requires_scaling = get_required<bool>(l3int, "requires_scaling", "ml.level3.internal");
        config.ml.level3.internal.timeout_ms = get_required<int>(l3int, "timeout_ms", "ml.level3.internal");
        config.ml.level3.internal.scaler_file = "";
        
        auto& l3web = l3["web"];
        config.ml.level3.web.enabled = get_required<bool>(l3web, "enabled", "ml.level3.web");
        config.ml.level3.web.name = get_required<std::string>(l3web, "name", "ml.level3.web");
        config.ml.level3.web.model_file = get_required<std::string>(l3web, "model_file", "ml.level3.web");
        config.ml.level3.web.features_count = get_required<int>(l3web, "features_count", "ml.level3.web");
        config.ml.level3.web.model_type = get_required<std::string>(l3web, "model_type", "ml.level3.web");
        config.ml.level3.web.description = get_required<std::string>(l3web, "description", "ml.level3.web");
        config.ml.level3.web.requires_scaling = get_required<bool>(l3web, "requires_scaling", "ml.level3.web");
        config.ml.level3.web.timeout_ms = get_required<int>(l3web, "timeout_ms", "ml.level3.web");
        config.ml.level3.web.scaler_file = "";
        
        // Inference
        auto& inf = ml["inference"];
        config.ml.inference.batch_size = get_required<int>(inf, "batch_size", "ml.inference");
        config.ml.inference.enable_model_warmup = get_required<bool>(inf, "enable_model_warmup", "ml.inference");
        config.ml.inference.warmup_iterations = get_required<int>(inf, "warmup_iterations", "ml.inference");
        config.ml.inference.onnx_optimization_level = get_required<std::string>(inf, "onnx_optimization_level", "ml.inference");
        config.ml.inference.inter_op_threads = get_required<int>(inf, "inter_op_threads", "ml.inference");
        config.ml.inference.intra_op_threads = get_required<int>(inf, "intra_op_threads", "ml.inference");
        config.ml.inference.enable_cpu_mem_arena = get_required<bool>(inf, "enable_cpu_mem_arena", "ml.inference");
        config.ml.inference.enable_profiling = get_required<bool>(inf, "enable_profiling", "ml.inference");
        
        // Feature extraction
        auto& feat = ml["feature_extraction"];
        config.ml.feature_extraction.validate_features = get_required<bool>(feat, "validate_features", "ml.feature_extraction");
        config.ml.feature_extraction.pad_missing = get_required<bool>(feat, "pad_missing", "ml.feature_extraction");
        config.ml.feature_extraction.log_extraction_errors = get_required<bool>(feat, "log_extraction_errors", "ml.feature_extraction");
        config.ml.feature_extraction.cache_extractions = get_required<bool>(feat, "cache_extractions", "ml.feature_extraction");
        config.ml.feature_extraction.cache_size = get_required<int>(feat, "cache_size", "ml.feature_extraction");
        config.ml.feature_extraction.simd_optimization = get_required<bool>(feat, "simd_optimization", "ml.feature_extraction");
        
        // Degraded mode
        auto& degraded = ml["degraded_mode"];
        config.ml.degraded_mode.min_models_required = get_required<int>(degraded, "min_models_required", "ml.degraded_mode");
        config.ml.degraded_mode.continue_with_partial_models = get_required<bool>(degraded, "continue_with_partial_models", "ml.degraded_mode");
        config.ml.degraded_mode.fallback_to_heuristics = get_required<bool>(degraded, "fallback_to_heuristics", "ml.degraded_mode");
        config.ml.degraded_mode.log_degraded_operations = get_required<bool>(degraded, "log_degraded_operations", "ml.degraded_mode");
    }
    
    // ========================================
    // Processing
    // ========================================
    {
        auto& proc = json_["processing"];
        config.processing.input_queue_size = get_required<int>(proc, "input_queue_size", "processing");
        config.processing.output_queue_size = get_required<int>(proc, "output_queue_size", "processing");
        config.processing.queue_timeout_ms = get_required<int>(proc, "queue_timeout_ms", "processing");
        
        auto& batch = proc["batch_processing"];
        config.processing.batch_processing.enabled = get_required<bool>(batch, "enabled", "processing.batch_processing");
        config.processing.batch_processing.batch_size = get_required<int>(batch, "batch_size", "processing.batch_processing");
        config.processing.batch_processing.batch_timeout_ms = get_required<int>(batch, "batch_timeout_ms", "processing.batch_processing");
        
        config.processing.lockfree_queues = get_required<bool>(proc, "lockfree_queues", "processing");
        config.processing.numa_aware_allocation = get_required<bool>(proc, "numa_aware_allocation", "processing");
        config.processing.memory_prefaulting = get_required<bool>(proc, "memory_prefaulting", "processing");
    }
    
    // ========================================
    // Backpressure
    // ========================================
    {
        auto& back = json_["backpressure"];
        config.backpressure.enabled = get_required<bool>(back, "enabled", "backpressure");
        config.backpressure.activation_threshold = get_required<float>(back, "activation_threshold", "backpressure");
        config.backpressure.max_drops_per_second = get_required<int>(back, "max_drops_per_second", "backpressure");
        config.backpressure.adaptive_rate_limiting = get_required<bool>(back, "adaptive_rate_limiting", "backpressure");
        
        auto& breaker = back["circuit_breaker"];
        config.backpressure.circuit_breaker.enabled = get_required<bool>(breaker, "enabled", "backpressure.circuit_breaker");
        config.backpressure.circuit_breaker.failure_threshold = get_required<int>(breaker, "failure_threshold", "backpressure.circuit_breaker");
        config.backpressure.circuit_breaker.recovery_timeout_seconds = get_required<int>(breaker, "recovery_timeout_seconds", "backpressure.circuit_breaker");
    }
    
    // ========================================
    // Monitoring
    // ========================================
    {
        auto& mon = json_["monitoring"];
        config.monitoring.stats_interval_seconds = get_required<int>(mon, "stats_interval_seconds", "monitoring");
        config.monitoring.performance_tracking = get_required<bool>(mon, "performance_tracking", "monitoring");
        
        auto& ml_met = mon["ml_metrics"];
        config.monitoring.ml_metrics.inference_time = get_required<bool>(ml_met, "inference_time", "monitoring.ml_metrics");
        config.monitoring.ml_metrics.model_accuracy = get_required<bool>(ml_met, "model_accuracy", "monitoring.ml_metrics");
        config.monitoring.ml_metrics.feature_importance = get_required<bool>(ml_met, "feature_importance", "monitoring.ml_metrics");
        config.monitoring.ml_metrics.predictions_per_second = get_required<bool>(ml_met, "predictions_per_second", "monitoring.ml_metrics");
        config.monitoring.ml_metrics.model_load_time = get_required<bool>(ml_met, "model_load_time", "monitoring.ml_metrics");
        
        auto& sys_met = mon["system_metrics"];
        config.monitoring.system_metrics.queue_depth = get_required<bool>(sys_met, "queue_depth", "monitoring.system_metrics");
        config.monitoring.system_metrics.memory_usage = get_required<bool>(sys_met, "memory_usage", "monitoring.system_metrics");
        config.monitoring.system_metrics.thread_utilization = get_required<bool>(sys_met, "thread_utilization", "monitoring.system_metrics");
        config.monitoring.system_metrics.compression_ratio = get_required<bool>(sys_met, "compression_ratio", "monitoring.system_metrics");
        config.monitoring.system_metrics.zmq_throughput = get_required<bool>(sys_met, "zmq_throughput", "monitoring.system_metrics");
        
        auto& alerts = mon["alerts"];
        config.monitoring.alerts.max_inference_latency_ms = get_required<int>(alerts, "max_inference_latency_ms", "monitoring.alerts");
        config.monitoring.alerts.max_queue_usage_percent = get_required<int>(alerts, "max_queue_usage_percent", "monitoring.alerts");
        config.monitoring.alerts.max_memory_usage_mb = get_required<int>(alerts, "max_memory_usage_mb", "monitoring.alerts");
        config.monitoring.alerts.max_cpu_usage_percent = get_required<int>(alerts, "max_cpu_usage_percent", "monitoring.alerts");
        config.monitoring.alerts.min_compression_ratio = get_required<float>(alerts, "min_compression_ratio", "monitoring.alerts");
        config.monitoring.alerts.max_model_failures_per_minute = get_required<int>(alerts, "max_model_failures_per_minute", "monitoring.alerts");
    }
    
    // ========================================
    // Logging
    // ========================================
    {
        auto& log = json_["logging"];
        config.logging.level = get_required<std::string>(log, "level", "logging");
        config.logging.file = get_required<std::string>(log, "file", "logging");
        config.logging.max_file_size_mb = get_required<int>(log, "max_file_size_mb", "logging");
        config.logging.backup_count = get_required<int>(log, "backup_count", "logging");
        config.logging.include_performance_logs = get_required<bool>(log, "include_performance_logs", "logging");
        config.logging.include_compression_stats = get_required<bool>(log, "include_compression_stats", "logging");
        config.logging.include_thread_stats = get_required<bool>(log, "include_thread_stats", "logging");
        config.logging.include_ml_predictions = get_required<bool>(log, "include_ml_predictions", "logging");
        config.logging.log_inference_scores = get_required<bool>(log, "log_inference_scores", "logging");
        config.logging.log_feature_extraction = get_required<bool>(log, "log_feature_extraction", "logging");
    }
    
    // ========================================
    // Protobuf
    // ========================================
    {
        auto& pb = json_["protobuf"];
        config.protobuf.schema_version = get_required<std::string>(pb, "schema_version", "protobuf");
        config.protobuf.validate_before_processing = get_required<bool>(pb, "validate_before_processing", "protobuf");
        config.protobuf.validate_after_enrichment = get_required<bool>(pb, "validate_after_enrichment", "protobuf");
        config.protobuf.max_event_size_bytes = get_required<int>(pb, "max_event_size_bytes", "protobuf");
        config.protobuf.deserialization_timeout_ms = get_required<int>(pb, "deserialization_timeout_ms", "protobuf");
        config.protobuf.serialization_timeout_ms = get_required<int>(pb, "serialization_timeout_ms", "protobuf");
        config.protobuf.pool_size = get_required<int>(pb, "pool_size", "protobuf");
        config.protobuf.reuse_objects = get_required<bool>(pb, "reuse_objects", "protobuf");
    }
    
    // ========================================
    // Security
    // ========================================
    {
        auto& sec = json_["security"];
        auto& val = sec["input_validation"];
        config.security.input_validation.enabled = get_required<bool>(val, "enabled", "security.input_validation");
        config.security.input_validation.validate_protobuf_schema = get_required<bool>(val, "validate_protobuf_schema", "security.input_validation");
        config.security.input_validation.sanitize_features = get_required<bool>(val, "sanitize_features", "security.input_validation");
        config.security.input_validation.reject_malformed_events = get_required<bool>(val, "reject_malformed_events", "security.input_validation");
        config.security.input_validation.max_feature_value = get_required<double>(val, "max_feature_value", "security.input_validation");
        config.security.input_validation.min_features_required = get_required<int>(val, "min_features_required", "security.input_validation");
    }
    
    // ========================================
    // Performance
    // ========================================
    {
        auto& perf = json_["performance"];
        config.performance.enable_zero_copy = get_required<bool>(perf, "enable_zero_copy", "performance");
        config.performance.enable_memory_pools = get_required<bool>(perf, "enable_memory_pools", "performance");
        config.performance.preallocate_buffers = get_required<bool>(perf, "preallocate_buffers", "performance");
        config.performance.buffer_pool_size = get_required<int>(perf, "buffer_pool_size", "performance");
        config.performance.enable_simd = get_required<bool>(perf, "enable_simd", "performance");
        config.performance.enable_avx2 = get_required<bool>(perf, "enable_avx2", "performance");
        config.performance.cache_line_size = get_required<int>(perf, "cache_line_size", "performance");
    }

    // ========================================
    // CSV Writer (Day 66)
    // ========================================
    {
        auto& csv = json_["csv_writer"];
        config.csv_writer.base_dir = get_required<std::string>(csv, "base_dir", "csv_writer");
        config.csv_writer.min_score_threshold = get_required<float>(csv, "min_score_threshold", "csv_writer");
        config.csv_writer.max_events_per_file = get_required<int>(csv, "max_events_per_file", "csv_writer");
    }

    // ========================================
    // Correlation Writer (bronce correlation_v1) — DAY 201/203
    // DEBT-CONFIG-BRONZE-HARDCODE-001 + DEBT-CIRCUIT-BRONZE-ROTATION-FOLLOW-001
    // ========================================
    {
        auto& corr = json_["correlation_writer"];
        config.correlation_writer.base_dir = get_required<std::string>(corr, "base_dir", "correlation_writer");
        config.correlation_writer.rotation_seconds = get_required<int>(corr, "rotation_seconds", "correlation_writer");
    }

    // ========================================
    // Scoring thresholds (Day 66)
    // ========================================
    {
        auto& sc = json_["scoring"];
        config.scoring.divergence_warn_threshold = get_required<float>(sc, "divergence_warn_threshold", "scoring");
        config.scoring.divergence_high_threshold = get_required<float>(sc, "divergence_high_threshold", "scoring");
        config.scoring.malicious_threshold       = get_required<float>(sc, "malicious_threshold",       "scoring");
        config.scoring.requires_rag_threshold    = get_required<float>(sc, "requires_rag_threshold",    "scoring");
    }

    return config;
}

void ConfigLoader::print_config(const DetectorConfig& config, bool verbose) {
    std::cout << "\n╔═══════════════════════════════════════════════════════════════╗\n";
    std::cout <<   "║  ML DETECTOR TRICAPA - CONFIGURATION                          ║\n";
    std::cout <<   "╚═══════════════════════════════════════════════════════════════╝\n\n";
    
    std::cout << "📦 Component: " << config.component.name << " v" << config.component.version << "\n";
    std::cout << "   Mode: " << config.component.mode << "\n";
    std::cout << "   Node: " << config.node_id << " @ " << config.cluster_name << "\n";
    std::cout << "   Profile: " << config.active_profile << "\n\n";
    
    std::cout << "🔌 Network:\n";
    std::cout << "   Input:  " << config.network.input_socket.socket_type << " " 
              << config.network.input_socket.mode << " " << config.network.input_socket.endpoint << "\n";
    std::cout << "   Output: " << config.network.output_socket.socket_type << " "
              << config.network.output_socket.mode << " " << config.network.output_socket.endpoint << "\n\n";
    
    std::cout << "🧵 Threading:\n";
    std::cout << "   Workers: " << config.threading.worker_threads << "\n";
    std::cout << "   ML Inference: " << config.threading.ml_inference_threads << " threads\n";
    std::cout << "   Feature Extraction: " << config.threading.feature_extractor_threads << " threads\n";
    std::cout << "   CPU Affinity: " << (config.threading.cpu_affinity.enabled ? "✅ enabled" : "❌ disabled") << "\n\n";
    
    std::cout << "🤖 ML Models:\n";
    std::cout << "   Base Dir: " << config.ml.models_base_dir << "\n";
    std::cout << "   Level 1: " << (config.ml.level1.enabled ? "✅" : "❌") 
              << " " << config.ml.level1.name << " (" << config.ml.level1.features_count << " features)\n";
    std::cout << "   Level 2 DDoS: " << (config.ml.level2.ddos.enabled ? "✅" : "❌")
              << " " << config.ml.level2.ddos.name << " (" << config.ml.level2.ddos.features_count << " features)\n";
    std::cout << "   Level 2 Ransomware: " << (config.ml.level2.ransomware.enabled ? "✅" : "❌")
              << " " << config.ml.level2.ransomware.name << " (" << config.ml.level2.ransomware.features_count << " features)\n";
    std::cout << "   Level 3 Internal: " << (config.ml.level3.internal.enabled ? "✅" : "❌")
              << " " << config.ml.level3.internal.name << " (" << config.ml.level3.internal.features_count << " features)\n";
    std::cout << "   Level 3 Web: " << (config.ml.level3.web.enabled ? "✅" : "❌")
              << " " << config.ml.level3.web.name << " (" << config.ml.level3.web.features_count << " features)\n\n";
    
    std::cout << "📝 Logging: " << config.logging.level << " → " << config.logging.file << "\n";
    std::cout << "📊 Monitoring: Stats every " << config.monitoring.stats_interval_seconds << "s\n";
    std::cout << "🔒 Transport: Compression=" << (config.transport.compression.enabled ? "✅" : "❌")
              << ", Encryption=" << (config.transport.encryption.enabled ? "✅" : "❌") << "\n\n";
    
    if (verbose) {
        std::cout << "═══════════════════════════════════════════════════════════════\n";
        std::cout << "VERBOSE MODE - COMPLETE CONFIGURATION\n";
        std::cout << "═══════════════════════════════════════════════════════════════\n\n";
        
        // Aquí añadirías más detalles si es necesario
        std::cout << "ZMQ Connection Settings:\n";
        std::cout << "  SNDHWM: " << config.zmq.connection_settings.sndhwm << "\n";
        std::cout << "  RCVHWM: " << config.zmq.connection_settings.rcvhwm << "\n";
        std::cout << "  Linger: " << config.zmq.connection_settings.linger_ms << " ms\n";
        std::cout << "  Send Timeout: " << config.zmq.connection_settings.send_timeout_ms << " ms\n";
        std::cout << "  Recv Timeout: " << config.zmq.connection_settings.recv_timeout_ms << " ms\n\n";
        
        std::cout << "ML Thresholds:\n";
        std::cout << "  Level 1 Attack: " << std::fixed << std::setprecision(2) << config.ml.thresholds.level1_attack << "\n";
        std::cout << "  Level 2 DDoS: " << config.ml.thresholds.level2_ddos << "\n";
        std::cout << "  Level 2 Ransomware: " << config.ml.thresholds.level2_ransomware << "\n";
        std::cout << "  Level 3 Anomaly: " << config.ml.thresholds.level3_anomaly << "\n";
        std::cout << "  Level 3 Web: " << config.ml.thresholds.level3_web << "\n";
        std::cout << "  Level 3 Internal: " << config.ml.thresholds.level3_internal << "\n\n";
        
        std::cout << "Performance:\n";
        std::cout << "  Zero Copy: " << (config.performance.enable_zero_copy ? "✅" : "❌") << "\n";
        std::cout << "  Memory Pools: " << (config.performance.enable_memory_pools ? "✅" : "❌") << "\n";
        std::cout << "  SIMD: " << (config.performance.enable_simd ? "✅" : "❌") << "\n";
        std::cout << "  AVX2: " << (config.performance.enable_avx2 ? "✅" : "❌") << "\n\n";
    }
    
    std::cout << "═══════════════════════════════════════════════════════════════\n\n";
}

} // namespace ml_detector