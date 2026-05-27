#include "config_manager.hpp"
#include <fstream>
#include <iostream>
#include <sstream>
#include <algorithm>
#include <cstdlib>
#include <filesystem>

namespace sniffer {

std::unique_ptr<SnifferConfig> ConfigManager::load_from_file(const std::string& config_path) {
    if (!std::filesystem::exists(config_path)) {
        fail_fast("Configuration file not found: " + config_path);
    }

    std::ifstream config_file(config_path);
    if (!config_file.is_open()) {
        fail_fast("Cannot open configuration file: " + config_path);
    }

    Json::Value root;
    Json::CharReaderBuilder builder;
    std::string errors;

    if (!Json::parseFromStream(builder, config_file, &root, &errors)) {
        fail_fast("JSON parsing error: " + errors);
    }

    auto config = std::make_unique<SnifferConfig>();

    // Parse component information
    auto component = root["component"];
    config->component_name = component.get("name", "cpp_evolutionary_sniffer").asString();
    config->version = component.get("version", "3.1.0").asString();
    config->mode = component.get("mode", "kernel_user_hybrid").asString();
    config->kernel_version_required = component.get("kernel_version_required", "6.12.0").asString();

    // Parse basic identifiers
    config->node_id = root.get("node_id", "cpp_sniffer_v31_001").asString();
    config->cluster_name = root.get("cluster_name", "default_cluster").asString();

    // Parse profiles
    if (root.isMember("profiles")) {
        for (const auto& profile_name : root["profiles"].getMemberNames()) {
            config->profiles[profile_name] = parse_profile(root["profiles"][profile_name]);
        }
    }

    // Parse active profile
    config->active_profile = root.get("profile", "lab").asString();

    // Parse all configuration sections
    config->buffers = parse_buffers(root.get("buffers", Json::Value{}));
    config->threading = parse_threading(root.get("threading", Json::Value{}));
    config->capture = parse_capture(root.get("capture", Json::Value{}));
    config->kernel_space = parse_kernel_space(root.get("kernel_space", Json::Value{}));
    config->user_space = parse_user_space(root.get("user_space", Json::Value{}));

    // Parse feature groups
    if (root.isMember("feature_groups")) {
        for (const auto& group_name : root["feature_groups"].getMemberNames()) {
            auto group_json = root["feature_groups"][group_name];
            FeatureGroupConfig group;
            group.count = group_json.get("count", 0).asInt();
            group.reference = group_json.get("reference", "").asString();
            group.description = group_json.get("description", "").asString();
            config->feature_groups[group_name] = group;
        }
    }

    config->sniffer_time_windows = parse_time_windows(root.get("sniffer_time_windows", Json::Value{}));
    config->network = parse_network(root.get("network", Json::Value{}));
    config->zmq = parse_zmq(root.get("zmq", Json::Value{}));
    config->transport = parse_transport(root.get("transport", Json::Value{}));
    config->etcd = parse_etcd(root.get("etcd", Json::Value{}));
    config->processing = parse_processing(root.get("processing", Json::Value{}));
    config->auto_tuner = parse_auto_tuner(root.get("auto_tuner", Json::Value{}));
    config->monitoring = parse_monitoring(root.get("monitoring", Json::Value{}));
    config->logging = parse_logging(root.get("logging", Json::Value{}));
    config->protobuf = parse_protobuf(root.get("protobuf", Json::Value{}));
    config->security = parse_security(root.get("security", Json::Value{}));
    config->backpressure = parse_backpressure(root.get("backpressure", Json::Value{}));

    config->ml_defender = parse_ml_defender(root.get("ml_defender", Json::Value{}));
    // Apply profile overrides
    config->apply_profile_overrides();

    std::cout << "[INFO] Enhanced configuration loaded successfully from: " << config_path << std::endl;
    log_config_summary(*config);

    return config;
}

ProfileConfig ConfigManager::parse_profile(const Json::Value& profile_json) {
    ProfileConfig profile;
    profile.capture_interface = profile_json.get("capture_interface", "eth0").asString();
    profile.promiscuous_mode = profile_json.get("promiscuous_mode", true).asBool();
    profile.af_xdp_enabled = profile_json.get("af_xdp_enabled", true).asBool();
    profile.worker_threads = profile_json.get("worker_threads", 4).asInt();
    profile.compression_level = profile_json.get("compression_level", 1).asInt();
    profile.cpu_affinity_enabled = profile_json.get("cpu_affinity_enabled", false).asBool();
    return profile;
}

BufferConfig ConfigManager::parse_buffers(const Json::Value& buffers_json) {
    BufferConfig buffers;
    buffers.ring_buffer_entries = buffers_json.get("ring_buffer_entries", 1048576).asUInt64();
    buffers.user_processing_queue_depth = buffers_json.get("user_processing_queue_depth", 10000).asUInt64();
    buffers.protobuf_serialize_buffer_size = buffers_json.get("protobuf_serialize_buffer_size", 65536).asUInt64();
    buffers.zmq_send_buffer_size = buffers_json.get("zmq_send_buffer_size", 1048576).asUInt64();
    buffers.flow_state_buffer_entries = buffers_json.get("flow_state_buffer_entries", 1000000).asUInt64();
    buffers.statistics_buffer_entries = buffers_json.get("statistics_buffer_entries", 100000).asUInt64();
    buffers.batch_processing_size = buffers_json.get("batch_processing_size", 100).asUInt64();
    return buffers;
}

ThreadingConfig ConfigManager::parse_threading(const Json::Value& threading_json) {
    ThreadingConfig threading;
    threading.ring_consumer_threads = threading_json.get("ring_consumer_threads", 2).asInt();
    threading.feature_processor_threads = threading_json.get("feature_processor_threads", 4).asInt();
    threading.zmq_sender_threads = threading_json.get("zmq_sender_threads", 2).asInt();
    threading.statistics_collector_threads = threading_json.get("statistics_collector_threads", 1).asInt();
    threading.total_worker_threads = threading_json.get("total_worker_threads", 8).asInt();

    // Parse CPU affinity
    auto affinity_json = threading_json["cpu_affinity"];
    threading.cpu_affinity.enabled = affinity_json.get("enabled", false).asBool();
    threading.cpu_affinity.ring_consumers = parse_int_array(affinity_json["ring_consumers"]);
    threading.cpu_affinity.processors = parse_int_array(affinity_json["processors"]);
    threading.cpu_affinity.zmq_senders = parse_int_array(affinity_json["zmq_senders"]);
    threading.cpu_affinity.statistics = parse_int_array(affinity_json["statistics"]);

    // Parse thread priorities
    if (threading_json.isMember("thread_priorities")) {
        threading.thread_priorities = parse_string_map(threading_json["thread_priorities"]);
    }

    return threading;
}

CaptureConfig ConfigManager::parse_capture(const Json::Value& capture_json) {
    CaptureConfig capture;
    capture.interface = capture_json.get("interface", "eth0").asString();
    capture.kernel_interface = capture_json.get("kernel_interface", "").asString();
    capture.user_interface = capture_json.get("user_interface", "").asString();
    capture.mode = capture_json.get("mode", "ebpf_xdp").asString();
    capture.xdp_flags = parse_string_array(capture_json["xdp_flags"]);
    capture.promiscuous_mode = capture_json.get("promiscuous_mode", true).asBool();
    capture.filter_expression = capture_json.get("filter_expression", "").asString();
    capture.buffer_size = capture_json.get("buffer_size", 65536).asUInt64();
    capture.min_packet_size = capture_json.get("min_packet_size", 20).asUInt64();
    capture.max_packet_size = capture_json.get("max_packet_size", 65536).asUInt64();
    capture.excluded_ports = parse_int_array(capture_json["excluded_ports"]);
    capture.included_protocols = parse_string_array(capture_json["included_protocols"]);

    // Parse AF_XDP configuration
    auto af_xdp_json = capture_json["af_xdp"];
    capture.af_xdp.enabled = af_xdp_json.get("enabled", true).asBool();
    capture.af_xdp.queue_id = af_xdp_json.get("queue_id", 0).asInt();
    capture.af_xdp.frame_size = af_xdp_json.get("frame_size", 2048).asUInt64();
    capture.af_xdp.fill_ring_size = af_xdp_json.get("fill_ring_size", 2048).asUInt64();
    capture.af_xdp.comp_ring_size = af_xdp_json.get("comp_ring_size", 2048).asUInt64();
    capture.af_xdp.tx_ring_size = af_xdp_json.get("tx_ring_size", 2048).asUInt64();
    capture.af_xdp.rx_ring_size = af_xdp_json.get("rx_ring_size", 2048).asUInt64();
    capture.af_xdp.umem_size = af_xdp_json.get("umem_size", 16777216).asUInt64();

    return capture;
}

KernelSpaceConfig ConfigManager::parse_kernel_space(const Json::Value& kernel_json) {
    KernelSpaceConfig kernel;
    kernel.ebpf_program = kernel_json.get("ebpf_program", "sniffer.bpf.o").asString();
    kernel.xdp_mode = kernel_json.get("xdp_mode", "native").asString();
    kernel.ring_buffer_size = kernel_json.get("ring_buffer_size", 1048576).asUInt64();
    kernel.max_flows_in_kernel = kernel_json.get("max_flows_in_kernel", 100000).asUInt64();
    kernel.flow_timeout_seconds = kernel_json.get("flow_timeout_seconds", 300).asInt();
    kernel.kernel_features = parse_string_array(kernel_json["kernel_features"]);

    // Parse performance settings
    auto perf_json = kernel_json["performance"];
    kernel.performance.cpu_budget_us_per_packet = perf_json.get("cpu_budget_us_per_packet", 50).asInt();
    kernel.performance.max_instructions_per_program = perf_json.get("max_instructions_per_program", 1000000).asUInt64();
    kernel.performance.map_update_batch_size = perf_json.get("map_update_batch_size", 100).asUInt64();

    return kernel;
}

UserSpaceConfig ConfigManager::parse_user_space(const Json::Value& user_json) {
    UserSpaceConfig user;
    user.flow_table_size = user_json.get("flow_table_size", 1000000).asUInt64();
    user.time_window_buffer_size = user_json.get("time_window_buffer_size", 10000).asUInt64();
    user.user_features = parse_string_array(user_json["user_features"]);

    // Parse memory management
    auto mem_json = user_json["memory_management"];
    user.memory_management.flow_eviction_policy = mem_json.get("flow_eviction_policy", "lru").asString();
    user.memory_management.max_memory_usage_mb = mem_json.get("max_memory_usage_mb", 2048).asUInt64();
    user.memory_management.gc_interval_seconds = mem_json.get("gc_interval_seconds", 60).asInt();

    return user;
}

TimeWindowsConfig ConfigManager::parse_time_windows(const Json::Value& windows_json) {
    TimeWindowsConfig windows;
    windows.flow_tracking_window_seconds = windows_json.get("flow_tracking_window_seconds", 300).asInt();
    windows.statistics_collection_window_seconds = windows_json.get("statistics_collection_window_seconds", 60).asInt();
    windows.feature_aggregation_window_seconds = windows_json.get("feature_aggregation_window_seconds", 30).asInt();
    windows.cleanup_interval_seconds = windows_json.get("cleanup_interval_seconds", 30).asInt();
    windows.max_flows_per_window = windows_json.get("max_flows_per_window", 100000).asUInt64();
    windows.window_overlap_seconds = windows_json.get("window_overlap_seconds", 10).asInt();
    return windows;
}

NetworkConfig ConfigManager::parse_network(const Json::Value& network_json) {
    NetworkConfig network;
    auto socket_json = network_json["output_socket"];
    network.output_socket.address = socket_json.get("address", "0.0.0.0").asString();
    network.output_socket.port = socket_json.get("port", 5571).asInt();
    network.output_socket.mode = socket_json.get("mode", "bind").asString();
    network.output_socket.socket_type = socket_json.get("socket_type", "PUSH").asString();
    network.output_socket.high_water_mark = socket_json.get("high_water_mark", 2000).asInt();
    return network;
}

ZmqConfig ConfigManager::parse_zmq(const Json::Value& zmq_json) {
    ZmqConfig zmq;
    zmq.worker_threads = zmq_json.get("worker_threads", 4).asInt();
    zmq.io_thread_pools = zmq_json.get("io_thread_pools", 2).asInt();

    // Parse socket pools
    auto pools_json = zmq_json["socket_pools"];
    zmq.socket_pools.push_sockets = pools_json.get("push_sockets", 4).asInt();
    zmq.socket_pools.load_balancing = pools_json.get("load_balancing", "round_robin").asString();
    zmq.socket_pools.failover_enabled = pools_json.get("failover_enabled", true).asBool();

    // Parse queue management
    auto queue_json = zmq_json["queue_management"];
    zmq.queue_management.internal_queues = queue_json.get("internal_queues", 4).asInt();
    zmq.queue_management.queue_size = queue_json.get("queue_size", 10000).asInt();
    zmq.queue_management.queue_timeout_ms = queue_json.get("queue_timeout_ms", 100).asInt();
    zmq.queue_management.overflow_policy = queue_json.get("overflow_policy", "drop_oldest").asString();

    // Parse connection settings
    auto conn_json = zmq_json["connection_settings"];
    zmq.connection_settings.sndhwm = conn_json.get("sndhwm", 10000).asInt();
    zmq.connection_settings.linger_ms = conn_json.get("linger_ms", 0).asInt();
    zmq.connection_settings.send_timeout_ms = conn_json.get("send_timeout_ms", 100).asInt();
    zmq.connection_settings.rcvhwm = conn_json.get("rcvhwm", 10000).asInt();
    zmq.connection_settings.recv_timeout_ms = conn_json.get("recv_timeout_ms", 100).asInt();
    zmq.connection_settings.tcp_keepalive = conn_json.get("tcp_keepalive", 1).asInt();
    zmq.connection_settings.sndbuf = conn_json.get("sndbuf", 1048576).asUInt64();
    zmq.connection_settings.rcvbuf = conn_json.get("rcvbuf", 1048576).asUInt64();
    zmq.connection_settings.reconnect_interval_ms = conn_json.get("reconnect_interval_ms", 1000).asInt();
    zmq.connection_settings.max_reconnect_attempts = conn_json.get("max_reconnect_attempts", 10).asInt();

    // Parse batch processing
    auto batch_json = zmq_json["batch_processing"];
    zmq.batch_processing.enabled = batch_json.get("enabled", true).asBool();
    zmq.batch_processing.batch_size = batch_json.get("batch_size", 50).asInt();
    zmq.batch_processing.batch_timeout_ms = batch_json.get("batch_timeout_ms", 10).asInt();
    zmq.batch_processing.max_batches_queued = batch_json.get("max_batches_queued", 100).asInt();

    return zmq;
}

TransportConfig ConfigManager::parse_transport(const Json::Value& transport_json) {
    TransportConfig transport;

    // Parse compression
    auto comp_json = transport_json["compression"];
    transport.compression.enabled = comp_json.get("enabled", true).asBool();
    transport.compression.algorithm = comp_json.get("algorithm", "lz4").asString();
    transport.compression.level = comp_json.get("level", 1).asInt();
// esto es un bug, si en el campo transport.compression.min_compress_size vale 0, el parser lo convierte en basura!
//    transport.compression.min_compress_size = comp_json.get("min_compress_size", 1024).asUInt64();
    //std::cerr << "[DEBUG] Raw min_compress_size JSON: " << comp_json["min_compress_size"] << std::endl;
    transport.compression.min_compress_size = comp_json.isMember("min_compress_size")
    ? static_cast<uint64_t>(
          comp_json["min_compress_size"].isString()
              ? std::stoull(comp_json["min_compress_size"].asString())
              : comp_json["min_compress_size"].asInt64()
      )
    : 0;

    transport.compression.compression_ratio_threshold = comp_json.get("compression_ratio_threshold", 0.8).asDouble();
    transport.compression.adaptive_compression = comp_json.get("adaptive_compression", false).asBool();

    // Parse encryption
    auto enc_json = transport_json["encryption"];
    transport.encryption.enabled = enc_json.get("enabled", false).asBool();
    transport.encryption.etcd_token_required = enc_json.get("etcd_token_required", true).asBool();
    transport.encryption.algorithm = enc_json.get("algorithm", "chacha20-poly1305").asString();
    transport.encryption.key_size = enc_json.get("key_size", 256).asInt();
    transport.encryption.key_rotation_hours = enc_json.get("key_rotation_hours", 24).asInt();
    transport.encryption.fallback_mode = enc_json.get("fallback_mode", "compression_only").asString();
    transport.encryption.zmq_curve_enabled = enc_json.get("zmq_curve_enabled", true).asBool();
    transport.encryption.curve_server_key = enc_json.get("curve_server_key", "").asString();
    transport.encryption.curve_secret_key = enc_json.get("curve_secret_key", "").asString();

    return transport;
}

EtcdConfig ConfigManager::parse_etcd(const Json::Value& etcd_json) {
    EtcdConfig etcd;
    etcd.enabled = etcd_json.get("enabled", true).asBool();
    etcd.endpoints = parse_string_array(etcd_json["endpoints"]);
    if (etcd.endpoints.empty()) {
        etcd.endpoints.push_back("localhost:2379");
    }
    etcd.connection_timeout_ms = etcd_json.get("connection_timeout_ms", 5000).asInt();
    etcd.retry_attempts = etcd_json.get("retry_attempts", 3).asInt();
    etcd.retry_interval_ms = etcd_json.get("retry_interval_ms", 1000).asInt();
    etcd.crypto_token_path = etcd_json.get("crypto_token_path", "/crypto/sniffer/tokens").asString();
    etcd.config_sync_path = etcd_json.get("config_sync_path", "/config/sniffer").asString();
    etcd.required_for_encryption = etcd_json.get("required_for_encryption", true).asBool();
    etcd.fallback_mode = etcd_json.get("fallback_mode", "standalone_unencrypted").asString();
    etcd.heartbeat_interval_seconds = etcd_json.get("heartbeat_interval_seconds", 30).asInt();
    etcd.lease_ttl_seconds = etcd_json.get("lease_ttl_seconds", 60).asInt();
    return etcd;
}

ProcessingConfig ConfigManager::parse_processing(const Json::Value& processing_json) {
    ProcessingConfig processing;

    // Parse kernel processing
    auto kernel_json = processing_json["kernel_processing"];
    processing.kernel_processing.max_map_entries = kernel_json.get("max_map_entries", 1000000).asUInt64();
    processing.kernel_processing.flow_hash_table_size = kernel_json.get("flow_hash_table_size", 1000000).asUInt64();
    processing.kernel_processing.counter_map_size = kernel_json.get("counter_map_size", 100000).asUInt64();
    processing.kernel_processing.stats_collection_interval_ms = kernel_json.get("stats_collection_interval_ms", 1000).asInt();

    // Parse user processing
    auto user_json = processing_json["user_processing"];
    processing.user_processing.internal_queue_size = user_json.get("internal_queue_size", 10000).asUInt64();
    processing.user_processing.queue_timeout_seconds = user_json.get("queue_timeout_seconds", 1).asInt();
    processing.user_processing.batch_size = user_json.get("batch_size", 100).asInt();
    processing.user_processing.lockfree_queues = user_json.get("lockfree_queues", true).asBool();
    processing.user_processing.numa_aware_allocation = user_json.get("numa_aware_allocation", true).asBool();
    processing.user_processing.memory_prefaulting = user_json.get("memory_prefaulting", true).asBool();

    // Parse feature extraction
    auto feature_json = processing_json["feature_extraction"];
    processing.feature_extraction.enabled = feature_json.get("enabled", true).asBool();
    processing.feature_extraction.extract_all_features = feature_json.get("extract_all_features", true).asBool();
    processing.feature_extraction.cache_flow_states = feature_json.get("cache_flow_states", true).asBool();
    processing.feature_extraction.flow_timeout_seconds = feature_json.get("flow_timeout_seconds", 300).asInt();
    processing.feature_extraction.max_concurrent_flows = feature_json.get("max_concurrent_flows", 1000000).asUInt64();
    processing.feature_extraction.statistics_engine = feature_json.get("statistics_engine", "high_performance_cpp").asString();
    processing.feature_extraction.simd_optimization = feature_json.get("simd_optimization", true).asBool();

    return processing;
}

MonitoringConfig ConfigManager::parse_monitoring(const Json::Value& monitoring_json) {
    MonitoringConfig monitoring;
    monitoring.stats_interval_seconds = monitoring_json.get("stats_interval_seconds", 30).asInt();
    monitoring.performance_tracking = monitoring_json.get("performance_tracking", true).asBool();

    // Parse kernel metrics
    auto kernel_metrics = monitoring_json["kernel_metrics"];
    monitoring.kernel_metrics.ebpf_program_stats = kernel_metrics.get("ebpf_program_stats", true).asBool();
    monitoring.kernel_metrics.map_utilization = kernel_metrics.get("map_utilization", true).asBool();
    monitoring.kernel_metrics.instruction_count = kernel_metrics.get("instruction_count", true).asBool();
    monitoring.kernel_metrics.processing_time_per_packet = kernel_metrics.get("processing_time_per_packet", true).asBool();

    // Parse user metrics
    auto user_metrics = monitoring_json["user_metrics"];
    monitoring.user_metrics.feature_extraction_rate = user_metrics.get("feature_extraction_rate", true).asBool();
    monitoring.user_metrics.queue_depth = user_metrics.get("queue_depth", true).asBool();
    monitoring.user_metrics.memory_usage = user_metrics.get("memory_usage", true).asBool();
    monitoring.user_metrics.thread_utilization = user_metrics.get("thread_utilization", true).asBool();
    monitoring.user_metrics.compression_ratio = user_metrics.get("compression_ratio", true).asBool();
    monitoring.user_metrics.zmq_throughput = user_metrics.get("zmq_throughput", true).asBool();

    // Parse alerts
    auto alerts = monitoring_json["alerts"];
    monitoring.alerts.max_drop_rate_percent = alerts.get("max_drop_rate_percent", 1.0).asDouble();
    monitoring.alerts.max_queue_usage_percent = alerts.get("max_queue_usage_percent", 85).asInt();
    monitoring.alerts.max_memory_usage_mb = alerts.get("max_memory_usage_mb", 4096).asUInt64();
    monitoring.alerts.max_cpu_usage_percent = alerts.get("max_cpu_usage_percent", 80).asInt();
    monitoring.alerts.max_processing_latency_us = alerts.get("max_processing_latency_us", 100).asInt();
    monitoring.alerts.min_compression_ratio = alerts.get("min_compression_ratio", 0.3).asDouble();

    return monitoring;
}

LoggingConfig ConfigManager::parse_logging(const Json::Value& logging_json) {
    LoggingConfig logging;
    logging.level = logging_json.get("level", "INFO").asString();
    logging.file = logging_json.get("file", "logs/cpp_evolutionary_sniffer_v31.log").asString();
    logging.max_file_size_mb = logging_json.get("max_file_size_mb", 200).asInt();
    logging.backup_count = logging_json.get("backup_count", 10).asInt();
    logging.include_performance_logs = logging_json.get("include_performance_logs", true).asBool();
    logging.include_compression_stats = logging_json.get("include_compression_stats", true).asBool();
    logging.include_thread_stats = logging_json.get("include_thread_stats", true).asBool();
    return logging;
}

ProtobufConfig ConfigManager::parse_protobuf(const Json::Value& protobuf_json) {
    ProtobufConfig protobuf;
    protobuf.schema_version = protobuf_json.get("schema_version", "v3.1.0").asString();
    protobuf.validate_before_send = protobuf_json.get("validate_before_send", true).asBool();
    protobuf.max_event_size_bytes = protobuf_json.get("max_event_size_bytes", 100000).asUInt64();
    protobuf.serialization_timeout_ms = protobuf_json.get("serialization_timeout_ms", 50).asInt();
    protobuf.pool_size = protobuf_json.get("pool_size", 1000).asInt();
    protobuf.reuse_objects = protobuf_json.get("reuse_objects", true).asBool();
    return protobuf;
}

SecurityConfig ConfigManager::parse_security(const Json::Value& security_json) {
    SecurityConfig security;
    auto input_validation = security_json["input_validation"];
    security.input_validation.enabled = input_validation.get("enabled", true).asBool();
    security.input_validation.max_packet_size_bytes = input_validation.get("max_packet_size_bytes", 65536).asUInt64();
    security.input_validation.validate_ip_addresses = input_validation.get("validate_ip_addresses", true).asBool();
    security.input_validation.validate_ports = input_validation.get("validate_ports", true).asBool();
    security.input_validation.sanitize_inputs = input_validation.get("sanitize_inputs", true).asBool();
    return security;
}

BackpressureConfig ConfigManager::parse_backpressure(const Json::Value& backpressure_json) {
    BackpressureConfig backpressure;
    backpressure.enabled = backpressure_json.get("enabled", true).asBool();

    auto kernel_bp = backpressure_json["kernel_backpressure"];
    backpressure.kernel_backpressure.ring_buffer_full_action = kernel_bp.get("ring_buffer_full_action", "drop_oldest").asString();

    auto user_bp = backpressure_json["user_backpressure"];
    backpressure.user_backpressure.max_drops_per_second = user_bp.get("max_drops_per_second", 1000).asInt();
    backpressure.user_backpressure.adaptive_rate_limiting = user_bp.get("adaptive_rate_limiting", true).asBool();

    auto circuit_breaker = backpressure_json["circuit_breaker"];
    backpressure.circuit_breaker.enabled = circuit_breaker.get("enabled", true).asBool();
    backpressure.circuit_breaker.failure_threshold = circuit_breaker.get("failure_threshold", 50).asInt();
    backpressure.circuit_breaker.recovery_timeout = circuit_breaker.get("recovery_timeout", 30).asInt();

    return backpressure;
}

// ============================================================================
// ML Defender Configuration Parser (Phase 1, Day 5 - No hardcoding)
// ============================================================================

MLDefenderConfig ConfigManager::parse_ml_defender(const Json::Value& ml_defender_json) {
    MLDefenderConfig config;

    // Parse thresholds with fallback defaults
    if (ml_defender_json.isMember("thresholds")) {
        const auto& thresholds = ml_defender_json["thresholds"];
        config.thresholds.ddos = thresholds.get("ddos", 0.85).asFloat();
        config.thresholds.ransomware = thresholds.get("ransomware", 0.90).asFloat();
        config.thresholds.traffic = thresholds.get("traffic", 0.80).asFloat();
        config.thresholds.internal = thresholds.get("internal", 0.85).asFloat();
    } else {
        // Fallback to conservative defaults if JSON missing
        config.thresholds.ddos = 0.85f;
        config.thresholds.ransomware = 0.90f;
        config.thresholds.traffic = 0.80f;
        config.thresholds.internal = 0.85f;
    }

    // Parse validation rules
    if (ml_defender_json.isMember("validation")) {
        const auto& validation = ml_defender_json["validation"];
        config.validation.min_threshold = validation.get("min_threshold", 0.5).asFloat();
        config.validation.max_threshold = validation.get("max_threshold", 0.99).asFloat();
        config.validation.fallback_threshold = validation.get("fallback_threshold", 0.75).asFloat();
    } else {
        config.validation.min_threshold = 0.5f;
        config.validation.max_threshold = 0.99f;
        config.validation.fallback_threshold = 0.75f;
    }

    // Validate thresholds are within acceptable range [0.5, 0.99]
    auto validate_threshold = [&](float threshold, const std::string& name) -> float {
        if (threshold < config.validation.min_threshold ||
            threshold > config.validation.max_threshold) {
            std::cerr << "[WARNING] ML Defender threshold '" << name
                      << "' (" << threshold << ") out of range ["
                      << config.validation.min_threshold << ", "
                      << config.validation.max_threshold << "]. "
                      << "Using fallback: " << config.validation.fallback_threshold << std::endl;
            return config.validation.fallback_threshold;
        }
        return threshold;
    };

    config.thresholds.ddos = validate_threshold(config.thresholds.ddos, "ddos");
    config.thresholds.ransomware = validate_threshold(config.thresholds.ransomware, "ransomware");
    config.thresholds.traffic = validate_threshold(config.thresholds.traffic, "traffic");
    config.thresholds.internal = validate_threshold(config.thresholds.internal, "internal");

    std::cout << "[Config] ML Defender thresholds loaded: "
              << "DDoS=" << config.thresholds.ddos << ", "
              << "Ransomware=" << config.thresholds.ransomware << ", "
              << "Traffic=" << config.thresholds.traffic << ", "
              << "Internal=" << config.thresholds.internal << std::endl;

    return config;
}

AutoTunerConfig ConfigManager::parse_auto_tuner(const Json::Value& auto_tuner_json) {
    AutoTunerConfig auto_tuner;
    auto_tuner.enabled = auto_tuner_json.get("enabled", false).asBool();
    auto_tuner.calibration_on_startup = auto_tuner_json.get("calibration_on_startup", true).asBool();
    auto_tuner.benchmark_iterations = auto_tuner_json.get("benchmark_iterations", 100000).asInt();
    auto_tuner.recalibration_interval_hours = auto_tuner_json.get("recalibration_interval_hours", 24).asInt();
    auto_tuner.safety_margin_factor = auto_tuner_json.get("safety_margin_factor", 1.2).asDouble();
    auto_tuner.feature_placement_strategy = auto_tuner_json.get("feature_placement_strategy", "cost_benefit_optimization").asString();
    return auto_tuner;
}

void ConfigManager::apply_profile(SnifferConfig& config, const std::string& profile_name) {
    auto it = config.profiles.find(profile_name);
    if (it == config.profiles.end()) {
        std::cerr << "[WARNING] Profile '" << profile_name << "' not found, using defaults" << std::endl;
        return;
    }

    const ProfileConfig& profile = it->second;

    // Apply profile overrides
    if (!profile.capture_interface.empty()) {
        config.capture.interface = profile.capture_interface;
    }
    config.capture.promiscuous_mode = profile.promiscuous_mode;
    config.capture.af_xdp.enabled = profile.af_xdp_enabled;
    config.threading.total_worker_threads = profile.worker_threads;
    config.transport.compression.level = profile.compression_level;
    config.threading.cpu_affinity.enabled = profile.cpu_affinity_enabled;

    std::cout << "[INFO] Applied profile: " << profile_name << std::endl;
}

void ConfigManager::validate_config(const SnifferConfig& config) {
    std::vector<std::string> errors;

    // Validate basic configuration
    if (config.component_name.empty()) {
        errors.push_back("Component name cannot be empty");
    }

    if (config.node_id.empty()) {
        errors.push_back("Node ID cannot be empty");
    }

    // Validate network configuration
    if (config.network.output_socket.port <= 0 || config.network.output_socket.port > 65535) {
        errors.push_back("Invalid port number: " + std::to_string(config.network.output_socket.port));
    }

    // Validate threading configuration
    validate_threading_config(config.threading);
    validate_zmq_config(config.zmq);
    validate_transport_config(config.transport);

    // Validate interface
    if (config.capture.interface.empty()) {
        errors.push_back("Capture interface cannot be empty");
    }

    // Validate buffer sizes
    if (config.buffers.ring_buffer_entries == 0) {
        errors.push_back("Ring buffer entries must be > 0");
    }

    // Validate feature groups
    for (const auto& [name, group] : config.feature_groups) {
        if (group.count <= 0) {
            errors.push_back("Feature group '" + name + "' must have count > 0");
        }
        if (group.reference.empty()) {
            errors.push_back("Feature group '" + name + "' must have reference file");
        }
    }

    if (!errors.empty()) {
        std::string error_msg = "Configuration validation failed:\n";
        for (const auto& error : errors) {
            error_msg += "  - " + error + "\n";
        }
        fail_fast(error_msg);
    }

    std::cout << "[INFO] Enhanced configuration validation passed" << std::endl;
}

void ConfigManager::validate_threading_config(const ThreadingConfig& threading) {
    if (threading.ring_consumer_threads <= 0) {
        fail_fast("Ring consumer threads must be > 0");
    }
    if (threading.feature_processor_threads <= 0) {
        fail_fast("Feature processor threads must be > 0");
    }
    if (threading.zmq_sender_threads <= 0) {
        fail_fast("ZMQ sender threads must be > 0");
    }
    if (threading.total_worker_threads !=
        (threading.ring_consumer_threads + threading.feature_processor_threads +
         threading.zmq_sender_threads + threading.statistics_collector_threads)) {
        std::cout << "[WARNING] Total worker threads mismatch with individual thread counts" << std::endl;
    }
}

void ConfigManager::validate_zmq_config(const ZmqConfig& zmq) {
    if (zmq.worker_threads <= 0) {
        fail_fast("ZMQ worker threads must be > 0");
    }
    if (zmq.socket_pools.push_sockets <= 0) {
        fail_fast("ZMQ push sockets must be > 0");
    }
    if (zmq.connection_settings.sndhwm <= 0) {
        fail_fast("ZMQ send high water mark must be > 0");
    }
}

void ConfigManager::validate_transport_config(const TransportConfig& transport) {
    // Validate compression algorithm
    std::vector<std::string> valid_compression = {"lz4", "zstd", "snappy", "lzo", "gzip", "brotli"};
    if (std::find(valid_compression.begin(), valid_compression.end(),
                  transport.compression.algorithm) == valid_compression.end()) {
        fail_fast("Invalid compression algorithm: " + transport.compression.algorithm);
    }

    // Validate encryption algorithm
    if (transport.encryption.enabled) {
        std::vector<std::string> valid_encryption = {"chacha20-poly1305", "aes256-gcm", "xchacha20-poly1305", "aes128-gcm"};
        if (std::find(valid_encryption.begin(), valid_encryption.end(),
                      transport.encryption.algorithm) == valid_encryption.end()) {
            fail_fast("Invalid encryption algorithm: " + transport.encryption.algorithm);
        }
    }
}

void ConfigManager::fail_fast(const std::string& error_message) {
    std::cerr << "[FATAL] " << error_message << std::endl;
    std::exit(1);
}

void ConfigManager::log_config_summary(const SnifferConfig& config) {
    std::cout << "\n=== Enhanced Configuration Summary ===" << std::endl;
    std::cout << "Component: " << config.component_name << " v" << config.version << std::endl;
    std::cout << "Mode: " << config.mode << std::endl;
    std::cout << "Node ID: " << config.node_id << std::endl;
    std::cout << "Cluster: " << config.cluster_name << std::endl;
    std::cout << "Active Profile: " << config.active_profile << std::endl;

    // Threading info
    std::cout << "Threading: " << config.threading.total_worker_threads << " total workers" << std::endl;
    std::cout << "  - Ring consumers: " << config.threading.ring_consumer_threads << std::endl;
    std::cout << "  - Feature processors: " << config.threading.feature_processor_threads << std::endl;
    std::cout << "  - ZMQ senders: " << config.threading.zmq_sender_threads << std::endl;

    // Capture info
    std::cout << "Capture: " << config.capture.interface << " (" << config.capture.mode << ")" << std::endl;

    // Network info
    std::cout << "Output: " << config.network.output_socket.address
              << ":" << config.network.output_socket.port
              << " (" << config.network.output_socket.socket_type << ")" << std::endl;

    // Transport info
    std::cout << "Compression: " << config.transport.compression.algorithm
              << " level " << config.transport.compression.level
              << " (" << (config.transport.compression.enabled ? "enabled" : "disabled") << ")" << std::endl;
    std::cout << "Encryption: " << config.transport.encryption.algorithm
              << " (" << (config.transport.encryption.enabled ? "enabled" : "disabled") << ")" << std::endl;

    // Feature groups
    std::cout << "Feature groups: " << config.feature_groups.size() << " defined" << std::endl;
    for (const auto& [name, group] : config.feature_groups) {
        std::cout << "  - " << name << ": " << group.count << " features" << std::endl;
    }

    // etcd info
    std::cout << "etcd: " << (config.etcd.enabled ? "enabled" : "disabled") << std::endl;
    if (config.etcd.enabled && !config.etcd.endpoints.empty()) {
        std::cout << "  - Endpoints: " << config.etcd.endpoints[0];
        if (config.etcd.endpoints.size() > 1) {
            std::cout << " (+" << (config.etcd.endpoints.size() - 1) << " more)";
        }
        std::cout << std::endl;
    }

    std::cout << "=========================================\n" << std::endl;
}

// Helper functions for parsing arrays and maps
std::vector<int> ConfigManager::parse_int_array(const Json::Value& array_json) {
    std::vector<int> result;
    if (array_json.isArray()) {
        for (const auto& item : array_json) {
            if (item.isInt()) {
                result.push_back(item.asInt());
            }
        }
    }
    return result;
}

std::vector<std::string> ConfigManager::parse_string_array(const Json::Value& array_json) {
    std::vector<std::string> result;
    if (array_json.isArray()) {
        for (const auto& item : array_json) {
            if (item.isString()) {
                result.push_back(item.asString());
            }
        }
    }
    return result;
}

std::unordered_map<std::string, std::string> ConfigManager::parse_string_map(const Json::Value& map_json) {
    std::unordered_map<std::string, std::string> result;
    if (map_json.isObject()) {
        for (const auto& key : map_json.getMemberNames()) {
            if (map_json[key].isString()) {
                result[key] = map_json[key].asString();
            }
        }
    }
    return result;
}

// SnifferConfig methods
bool SnifferConfig::is_valid() const {
    return !component_name.empty() && !node_id.empty() && !capture.interface.empty();
}

std::vector<std::string> SnifferConfig::validate() const {
    std::vector<std::string> errors;
    if (component_name.empty()) errors.push_back("Component name required");
    if (node_id.empty()) errors.push_back("Node ID required");
    if (capture.interface.empty()) errors.push_back("Capture interface required");
    if (network.output_socket.port <= 0) errors.push_back("Valid network port required");
    return errors;
}

const ProfileConfig& SnifferConfig::get_active_profile() const {
    auto it = profiles.find(active_profile);
    if (it != profiles.end()) {
        return it->second;
    }
    // Return a default profile if active profile not found
    static ProfileConfig default_profile = {
        "eth0", true, true, 4, 1, false
    };
    return default_profile;
}

void SnifferConfig::apply_profile_overrides() {
    ConfigManager::apply_profile(*this, active_profile);
}

} // namespace sniffer