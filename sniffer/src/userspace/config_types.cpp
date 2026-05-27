// sniffer/src/userspace/config_types.cpp - Minimal implementation for v3.2
// Implements strict_load_json_config using existing ConfigManager
#include "config_types.h"
#include "config_manager.hpp"
#include <fstream>
#include <iostream>

bool strict_load_json_config(const std::string& config_path, StrictSnifferConfig& config, bool verbose) {
    try {
        // Use existing ConfigManager to load
        auto sniffer_config = sniffer::ConfigManager::load_from_file(config_path);

        if (!sniffer_config) {
            std::cerr << "Failed to load configuration using ConfigManager" << std::endl;
            return false;
        }

        // Convert SnifferConfig to StrictSnifferConfig
        config.component_name = sniffer_config->component_name;
        config.component_version = sniffer_config->version;
        config.component_mode = sniffer_config->mode;
        config.kernel_version_required = sniffer_config->kernel_version_required;

        config.node_id = sniffer_config->node_id;
        config.cluster_name = sniffer_config->cluster_name;
        config.active_profile = sniffer_config->active_profile;

        // Apply profile settings
        if (sniffer_config->profiles.count(config.active_profile) > 0) {
            auto& profile = sniffer_config->profiles[config.active_profile];
            config.capture_interface = profile.capture_interface;
            config.promiscuous_mode = profile.promiscuous_mode;
            config.af_xdp_enabled = profile.af_xdp_enabled;
            config.worker_threads = profile.worker_threads;
            config.compression_level = profile.compression_level;
        }

        // Capture settings
        config.kernel_interface = sniffer_config->capture.kernel_interface;
        config.user_interface = sniffer_config->capture.user_interface;
        config.capture_mode = sniffer_config->capture.mode;
        config.xdp_flags = sniffer_config->capture.xdp_flags;
        config.filter_expression = sniffer_config->capture.filter_expression;
        config.buffer_size = sniffer_config->capture.buffer_size;
        config.min_packet_size = sniffer_config->capture.min_packet_size;
        config.max_packet_size = sniffer_config->capture.max_packet_size;
        config.excluded_ports = sniffer_config->capture.excluded_ports;
        config.included_protocols = sniffer_config->capture.included_protocols;

        // AF_XDP
        config.af_xdp.enabled = sniffer_config->capture.af_xdp.enabled;
        config.af_xdp.queue_id = sniffer_config->capture.af_xdp.queue_id;
        config.af_xdp.frame_size = sniffer_config->capture.af_xdp.frame_size;
        config.af_xdp.fill_ring_size = sniffer_config->capture.af_xdp.fill_ring_size;
        config.af_xdp.comp_ring_size = sniffer_config->capture.af_xdp.comp_ring_size;
        config.af_xdp.tx_ring_size = sniffer_config->capture.af_xdp.tx_ring_size;
        config.af_xdp.rx_ring_size = sniffer_config->capture.af_xdp.rx_ring_size;
        config.af_xdp.umem_size = sniffer_config->capture.af_xdp.umem_size;

        // Buffers
        config.buffers.ring_buffer_entries = sniffer_config->buffers.ring_buffer_entries;
        config.buffers.user_processing_queue_depth = sniffer_config->buffers.user_processing_queue_depth;
        config.buffers.protobuf_serialize_buffer_size = sniffer_config->buffers.protobuf_serialize_buffer_size;
        config.buffers.zmq_send_buffer_size = sniffer_config->buffers.zmq_send_buffer_size;
        config.buffers.flow_state_buffer_entries = sniffer_config->buffers.flow_state_buffer_entries;
        config.buffers.statistics_buffer_entries = sniffer_config->buffers.statistics_buffer_entries;
        config.buffers.batch_processing_size = sniffer_config->buffers.batch_processing_size;

        // Threading
        config.threading.ring_consumer_threads = sniffer_config->threading.ring_consumer_threads;
        config.threading.feature_processor_threads = sniffer_config->threading.feature_processor_threads;
        config.threading.zmq_sender_threads = sniffer_config->threading.zmq_sender_threads;
        config.threading.statistics_collector_threads = sniffer_config->threading.statistics_collector_threads;
        config.threading.total_worker_threads = sniffer_config->threading.total_worker_threads;
        config.threading.cpu_affinity_enabled = sniffer_config->threading.cpu_affinity.enabled;
        config.threading.ring_consumers_affinity = sniffer_config->threading.cpu_affinity.ring_consumers;
        config.threading.processors_affinity = sniffer_config->threading.cpu_affinity.processors;
        config.threading.zmq_senders_affinity = sniffer_config->threading.cpu_affinity.zmq_senders;
        config.threading.statistics_affinity = sniffer_config->threading.cpu_affinity.statistics;

        // Thread priorities
        if (sniffer_config->threading.thread_priorities.count("ring_consumers") > 0) {
            config.threading.ring_consumers_priority = sniffer_config->threading.thread_priorities["ring_consumers"];
        }
        if (sniffer_config->threading.thread_priorities.count("processors") > 0) {
            config.threading.processors_priority = sniffer_config->threading.thread_priorities["processors"];
        }
        if (sniffer_config->threading.thread_priorities.count("zmq_senders") > 0) {
            config.threading.zmq_senders_priority = sniffer_config->threading.thread_priorities["zmq_senders"];
        }

        // Kernel space
        config.kernel_space.ebpf_program = sniffer_config->kernel_space.ebpf_program;
        config.kernel_space.xdp_mode = sniffer_config->kernel_space.xdp_mode;
        config.kernel_space.ring_buffer_size = sniffer_config->kernel_space.ring_buffer_size;
        config.kernel_space.max_flows_in_kernel = sniffer_config->kernel_space.max_flows_in_kernel;
        config.kernel_space.flow_timeout_seconds = sniffer_config->kernel_space.flow_timeout_seconds;
        config.kernel_space.kernel_features = sniffer_config->kernel_space.kernel_features;

        // Network output
        config.network_output.address = sniffer_config->network.output_socket.address;
        config.network_output.port = sniffer_config->network.output_socket.port;
        config.network_output.mode = sniffer_config->network.output_socket.mode;
        config.network_output.socket_type = sniffer_config->network.output_socket.socket_type;
        config.network_output.high_water_mark = sniffer_config->network.output_socket.high_water_mark;

        // ZMQ
        config.zmq.worker_threads = sniffer_config->zmq.worker_threads;
        config.zmq.io_thread_pools = sniffer_config->zmq.io_thread_pools;
        config.zmq.push_sockets = sniffer_config->zmq.socket_pools.push_sockets;
        config.zmq.load_balancing = sniffer_config->zmq.socket_pools.load_balancing;
        config.zmq.failover_enabled = sniffer_config->zmq.socket_pools.failover_enabled;
        config.zmq.internal_queues = sniffer_config->zmq.queue_management.internal_queues;
        config.zmq.queue_size = sniffer_config->zmq.queue_management.queue_size;
        config.zmq.queue_timeout_ms = sniffer_config->zmq.queue_management.queue_timeout_ms;
        config.zmq.overflow_policy = sniffer_config->zmq.queue_management.overflow_policy;
        config.zmq.sndhwm = sniffer_config->zmq.connection_settings.sndhwm;
        config.zmq.linger_ms = sniffer_config->zmq.connection_settings.linger_ms;
        config.zmq.send_timeout_ms = sniffer_config->zmq.connection_settings.send_timeout_ms;
        config.zmq.rcvhwm = sniffer_config->zmq.connection_settings.rcvhwm;
        config.zmq.recv_timeout_ms = sniffer_config->zmq.connection_settings.recv_timeout_ms;
        config.zmq.tcp_keepalive = sniffer_config->zmq.connection_settings.tcp_keepalive;
        config.zmq.sndbuf = sniffer_config->zmq.connection_settings.sndbuf;
        config.zmq.rcvbuf = sniffer_config->zmq.connection_settings.rcvbuf;
        config.zmq.reconnect_interval_ms = sniffer_config->zmq.connection_settings.reconnect_interval_ms;
        config.zmq.max_reconnect_attempts = sniffer_config->zmq.connection_settings.max_reconnect_attempts;
        config.zmq.batch_enabled = sniffer_config->zmq.batch_processing.enabled;
        config.zmq.batch_size = sniffer_config->zmq.batch_processing.batch_size;
        config.zmq.batch_timeout_ms = sniffer_config->zmq.batch_processing.batch_timeout_ms;
        config.zmq.max_batches_queued = sniffer_config->zmq.batch_processing.max_batches_queued;

        // Compression
        config.compression.enabled = sniffer_config->transport.compression.enabled;
        config.compression.algorithm = sniffer_config->transport.compression.algorithm;
        config.compression.level = sniffer_config->transport.compression.level;
        config.compression.min_compress_size = sniffer_config->transport.compression.min_compress_size;
        config.compression.compression_ratio_threshold = sniffer_config->transport.compression.compression_ratio_threshold;
        config.compression.adaptive_compression = sniffer_config->transport.compression.adaptive_compression;

        // etcd - Day 20 mapping
        config.etcd.enabled = sniffer_config->etcd.enabled;
        config.etcd.endpoints = sniffer_config->etcd.endpoints;

        // Monitoring
        config.monitoring.stats_interval_seconds = sniffer_config->monitoring.stats_interval_seconds;

        // Fast Detector - Parse directly from JSON since it's new
        Json::Value root;
        std::ifstream config_file(config_path);
        if (config_file.is_open()) {
            config_file >> root;
            config_file.close();

            if (root.isMember("fast_detector")) {
                const auto& fd = root["fast_detector"];

                // Main settings
                config.fast_detector.enabled = fd.get("enabled", true).asBool();

                // Ransomware scores
                if (fd.isMember("ransomware") && fd["ransomware"].isMember("scores")) {
                    const auto& scores = fd["ransomware"]["scores"];
                    config.fast_detector.ransomware.scores.high_threat = scores.get("high_threat", 0.95).asDouble();
                    config.fast_detector.ransomware.scores.suspicious = scores.get("suspicious", 0.70).asDouble();
                    config.fast_detector.ransomware.scores.alert = scores.get("alert", 0.75).asDouble();
                }

                // Ransomware thresholds
                if (fd.isMember("ransomware") && fd["ransomware"].isMember("activation_thresholds")) {
                    const auto& thresholds = fd["ransomware"]["activation_thresholds"];
                    config.fast_detector.ransomware.activation_thresholds.external_ips_30s =
                        thresholds.get("external_ips_30s", 15).asInt();
                    config.fast_detector.ransomware.activation_thresholds.smb_diversity =
                        thresholds.get("smb_diversity", 10).asInt();
                    config.fast_detector.ransomware.activation_thresholds.dns_entropy =
                        thresholds.get("dns_entropy", 2.5).asDouble();
                    config.fast_detector.ransomware.activation_thresholds.failed_dns_ratio =
                        thresholds.get("failed_dns_ratio", 0.3).asDouble();
                    config.fast_detector.ransomware.activation_thresholds.upload_download_ratio =
                        thresholds.get("upload_download_ratio", 3.0).asDouble();
                    config.fast_detector.ransomware.activation_thresholds.burst_connections =
                        thresholds.get("burst_connections", 50).asInt();
                    config.fast_detector.ransomware.activation_thresholds.unique_destinations_30s =
                        thresholds.get("unique_destinations_30s", 30).asInt();
                }

                // Logging
                if (fd.isMember("logging")) {
                    const auto& logging = fd["logging"];
                    config.fast_detector.logging.log_activations = logging.get("log_activations", true).asBool();
                    config.fast_detector.logging.log_features = logging.get("log_features", true).asBool();
                    config.fast_detector.logging.log_decisions = logging.get("log_decisions", true).asBool();
                    config.fast_detector.logging.log_frequency_seconds = logging.get("log_frequency_seconds", 60).asInt();
                }

                // Performance
                if (fd.isMember("performance")) {
                    const auto& perf = fd["performance"];
                    config.fast_detector.performance.max_latency_us = perf.get("max_latency_us", 10).asInt();
                    config.fast_detector.performance.enable_metrics = perf.get("enable_metrics", true).asBool();
                    config.fast_detector.performance.track_activation_rate = perf.get("track_activation_rate", true).asBool();
                }

    // DAY 80 ✅ ml_defender thresholds desde JSON (Phase1-Day4-CRITICAL CERRADO)
    if (root.isMember("ml_defender") && root["ml_defender"].isMember("thresholds")) {
        const auto& t = root["ml_defender"]["thresholds"];
        config.ml_defender.ddos       = t.get("ddos",       0.85).asFloat();
        config.ml_defender.ransomware = t.get("ransomware", 0.90).asFloat();
        config.ml_defender.traffic    = t.get("traffic",    0.80).asFloat();
        config.ml_defender.internal   = t.get("internal",   0.85).asFloat();
    }
    std::cout << "[Config] ML Defender thresholds (StrictConfig): "
              << "DDoS=" << config.ml_defender.ddos
              << " Ransomware=" << config.ml_defender.ransomware
              << " Traffic=" << config.ml_defender.traffic
              << " Internal=" << config.ml_defender.internal << std::endl;

                if (verbose) {
                    std::cout << "✅ Fast Detector configuration loaded:" << std::endl;
                    std::cout << "   - Enabled: " << (config.fast_detector.enabled ? "YES" : "NO") << std::endl;
                    std::cout << "   - High threat score: " << config.fast_detector.ransomware.scores.high_threat << std::endl;
                    std::cout << "   - ExtIPs threshold: " << config.fast_detector.ransomware.activation_thresholds.external_ips_30s << std::endl;
                    std::cout << "   - SMB diversity threshold: " << config.fast_detector.ransomware.activation_thresholds.smb_diversity << std::endl;
                }
            } else {
                // Set defaults if section missing
                config.fast_detector.enabled = false;
                if (verbose) {
                    std::cout << "⚠️  Fast Detector section not found, disabled by default" << std::endl;
                }
            }
        }

        if (verbose) {
            std::cout << "✅ Configuration loaded and converted successfully" << std::endl;
        }

        return true;

    } catch (const std::exception& e) {
        std::cerr << "❌ Error loading configuration: " << e.what() << std::endl;
        return false;
    }
}

// Stub implementations for validate functions (not used but declared in header)
void validate_component_section(const Json::Value&, StrictSnifferConfig&, bool) {}
void validate_profiles_section(const Json::Value&, StrictSnifferConfig&, bool) {}
void validate_capture_section(const Json::Value&, StrictSnifferConfig&, bool) {}
void validate_buffers_section(const Json::Value&, StrictSnifferConfig&, bool) {}
void validate_threading_section(const Json::Value&, StrictSnifferConfig&, bool) {}
void validate_kernel_space_section(const Json::Value&, StrictSnifferConfig&, bool) {}
void validate_user_space_section(const Json::Value&, StrictSnifferConfig&, bool) {}
void validate_feature_groups_section(const Json::Value&, StrictSnifferConfig&, bool) {}
void validate_time_windows_section(const Json::Value&, StrictSnifferConfig&, bool) {}
void validate_network_section(const Json::Value&, StrictSnifferConfig&, bool) {}
void validate_zmq_section(const Json::Value&, StrictSnifferConfig&, bool) {}
void validate_transport_section(const Json::Value&, StrictSnifferConfig&, bool) {}
void validate_etcd_section(const Json::Value&, StrictSnifferConfig&, bool) {}
void validate_processing_section(const Json::Value&, StrictSnifferConfig&, bool) {}
void validate_auto_tuner_section(const Json::Value&, StrictSnifferConfig&, bool) {}
void validate_monitoring_section(const Json::Value&, StrictSnifferConfig&, bool) {}
void validate_logging_section(const Json::Value&, StrictSnifferConfig&, bool) {}
void validate_protobuf_section(const Json::Value&, StrictSnifferConfig&, bool) {}
void validate_security_section(const Json::Value&, StrictSnifferConfig&, bool) {}
void validate_backpressure_section(const Json::Value&, StrictSnifferConfig&, bool) {}
void validate_fast_detector_section(const Json::Value&, StrictSnifferConfig&, bool) {}