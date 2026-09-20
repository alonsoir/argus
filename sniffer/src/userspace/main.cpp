// sniffer/src/userspace/main.cpp - Enhanced Sniffer v3.2 with Hybrid Filtering
// FECHA: 31 de Octubre de 2025
// FUNCIONALIDAD: Sistema de filtros híbridos con BPF Maps
// Stats handled by RingBufferConsumer internally
// sniffer/src/userspace/main.cpp

#include "config_types.h"
#include "main.h"
#include "network_security.pb.h"
#include "config_manager.hpp"
#include "fast_detector_config.hpp"
#include "zmq_pool_manager.hpp"
#include "ebpf_loader.hpp"
#include "ddos_kernel_reader.hpp"  // [DDOS-KREAD-D274:MAIN-INC]
#include "ring_consumer.hpp"
#include "thread_manager.hpp"
#include "bpf_map_manager.h"
#include "feature_logger.hpp"
#include "dual_nic_manager.hpp"
#include "etcd_client.hpp"

#ifdef PLUGIN_LOADER_ENABLED
#include "plugin_loader/plugin_loader.hpp"
#endif
// Sistema y captura de red
#include <json/json.h>
#include <fstream>
#include <iostream>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <netinet/ip.h>
#include <netinet/tcp.h>
#include <netinet/udp.h>
#include <netinet/ether.h>
#include <linux/if_packet.h>
#include <net/if.h>
#include <sys/ioctl.h>
#include <unistd.h>
#include <errno.h>
#include <csignal>
#include <getopt.h>
#include <iomanip>
#include <random>
#include <fstream>
#include <algorithm>
#include <memory>
#include <exception>

FeatureLogger::VerbosityLevel g_verbosity = FeatureLogger::VerbosityLevel::NONE;

// ============================================================================
// FILTER CONFIGURATION PARSING FUNCTIONS
// ============================================================================

bool parse_filter_config(const Json::Value& root, FilterConfiguration& filter_config) {
    if (!root.isMember("capture") || !root["capture"].isMember("filter")) {
        std::cerr << "⚠️  No filter configuration found in JSON, using defaults" << std::endl;
        filter_config.mode = "blacklist";
        filter_config.default_action = "capture";
        return true;
    }

    const Json::Value& filter = root["capture"]["filter"];

    // Parse mode
    if (filter.isMember("mode")) {
        filter_config.mode = filter["mode"].asString();
        if (filter_config.mode != "blacklist" &&
            filter_config.mode != "whitelist" &&
            filter_config.mode != "hybrid") {
            std::cerr << "❌ Invalid filter mode: " << filter_config.mode << std::endl;
            return false;
        }
    } else {
        filter_config.mode = "hybrid";
    }

    // Parse excluded_ports
    if (filter.isMember("excluded_ports") && filter["excluded_ports"].isArray()) {
        for (const auto& port : filter["excluded_ports"]) {
            if (port.isInt()) {
                uint16_t port_num = static_cast<uint16_t>(port.asUInt());
                if (port_num > 0) {  // Quitamos check redundante de <= 65535
                    filter_config.excluded_ports.push_back(port_num);
                }
            }
        }
    }

    // Parse included_ports
    if (filter.isMember("included_ports") && filter["included_ports"].isArray()) {
        for (const auto& port : filter["included_ports"]) {
            if (port.isInt()) {
                uint16_t port_num = static_cast<uint16_t>(port.asUInt());
                if (port_num > 0) {  // Quitamos check redundante de <= 65535
                    filter_config.included_ports.push_back(port_num);
                }
            }
        }
    }

    // Parse default_action
    if (filter.isMember("default_action")) {
        filter_config.default_action = filter["default_action"].asString();
        if (filter_config.default_action != "capture" &&
            filter_config.default_action != "drop") {
            std::cerr << "❌ Invalid default_action" << std::endl;
            return false;
        }
    } else {
        filter_config.default_action = "capture";
    }

    return true;
}

bool validate_filter_mode(const FilterConfiguration& config) {
    if (config.mode == "blacklist") {
        if (config.excluded_ports.empty()) {
            std::cerr << "⚠️  Warning: blacklist mode with no excluded_ports" << std::endl;
        }
    } else if (config.mode == "whitelist") {
        if (config.included_ports.empty()) {
            std::cerr << "❌ Error: whitelist mode requires at least one included_port" << std::endl;
            return false;
        }
    } else if (config.mode == "hybrid") {
        if (config.excluded_ports.empty() && config.included_ports.empty()) {
            std::cerr << "⚠️  Warning: hybrid mode with no filters" << std::endl;
        }
    }
    return true;
}

// ============================================================================
// USAGE AND HELP
// ============================================================================

void print_usage(const char* program_name) {
    std::cout << "╔════════════════════════════════════════════╗\n";
    std::cout << "║   Enhanced Sniffer v3.2 - Hybrid Filters  ║\n";
    std::cout << "╚════════════════════════════════════════════╝\n";
    std::cout << "Compilado: " << __DATE__ << " " << __TIME__ << "\n";
    std::cout << "Modo: JSON + BPF Maps dynamic filtering\n\n";

    std::cout << "Usage: " << program_name << " [OPTIONS]\n\n";
    std::cout << "Options:\n";
    std::cout << "  -v, --verbose           Incrementar nivel de verbosity (usar hasta 3 veces)\n";
    std::cout << "                          -v   : Resumen básico por paquete\n";
    std::cout << "                          -vv  : Features agrupadas por categoría\n";
    std::cout << "                          -vvv : Todas las features con detalle completo\n";
    std::cout << "  -h, --help              Mostrar ayuda\n";
    std::cout << "  -c, --config FILE       Archivo JSON (OBLIGATORIO)\n";
    std::cout << "  -i, --interface IFACE   Override interface\n";
    std::cout << "  -p, --profile PROFILE   Override perfil (lab/cloud/bare_metal)\n";
    std::cout << "\nFilter Configuration (in JSON):\n";
    std::cout << "  \"filter\": {\n";
    std::cout << "    \"mode\": \"hybrid\",\n";
    std::cout << "    \"excluded_ports\": [22, 4444, 8080],\n";
    std::cout << "    \"included_ports\": [8000],\n";
    std::cout << "    \"default_action\": \"capture\"\n";
    std::cout << "  }\n";
    std::cout << "\nModes: blacklist, whitelist, hybrid\n";
    std::cout << "Precedence: included_ports > excluded_ports > default_action\n";
}

// ============================================================================
// GLOBAL VARIABLES (existentes, mantener)
// ============================================================================

// ============================================================================
// GLOBAL VARIABLES
// ============================================================================

// Atomic flag para terminación limpia
std::atomic<bool> g_running{true};

// Configuración global
StrictSnifferConfig g_config;

// Punteros a componentes principales
sniffer::EbpfLoader* ebpf_loader_ptr = nullptr;
sniffer::DdosKernelReader* ddos_reader_ptr = nullptr;  // [DDOS-KREAD-D274:MAIN-PTR]
sniffer::RingBufferConsumer* ring_consumer_ptr = nullptr;
std::shared_ptr<sniffer::ThreadManager> thread_manager = nullptr;

// ============================================================================
// SIGNAL HANDLERS
// ============================================================================

void signal_handler(int signum) {
    // async-signal-safe: write() only (DEBT-SIGNAL-001)
    static const char msg[] = "\n[Signal] Shutdown signal received\n";
    write(STDERR_FILENO, msg, sizeof(msg) - 1);
    (void)signum;
    g_running = false;
}

void setup_signal_handlers() {
    struct sigaction sa;
    sa.sa_handler = signal_handler;
    sigemptyset(&sa.sa_mask);
    sa.sa_flags = 0;

    sigaction(SIGINT, &sa, nullptr);
    sigaction(SIGTERM, &sa, nullptr);

    std::cout << "✅ Signal handlers configured (SIGINT, SIGTERM)" << std::endl;
}

// ============================================================================
// MAIN FUNCTION - REFACTORIZADO CON INTEGRACIÓN DE FILTROS
// ============================================================================

int main(int argc, char* argv[]) {
    // SET_TERMINATE — DAY 100 (ADR-022: fail-closed, unhandled exceptions)
    std::set_terminate([]() {
        std::cerr << "[FATAL] std::terminate() called — unhandled exception or contract violation\n";
        std::abort();
    });
    std::cout << "╔════════════════════════════════════════════════════════════════╗\n";
    std::cout << "║         Enhanced Sniffer v3.2 - Hybrid Filtering System       ║\n";
    std::cout << "╚════════════════════════════════════════════════════════════════╝\n";
    std::cout << "Compilado: " << __DATE__ << " " << __TIME__ << "\n\n";

    // ============================================================================
    // PARSE COMMAND LINE ARGUMENTS
    // ============================================================================

    std::string config_path;
    std::string override_interface;
    std::string override_profile;

    // Parse command line arguments
    int opt;
    int option_index = 0;

    static struct option long_options[] = {
        {"config",    required_argument, 0, 'c'},
        {"interface", required_argument, 0, 'i'},
        {"profile",   required_argument, 0, 'p'},
        {"verbose",   no_argument,       0, 'v'},
        {"help",      no_argument,       0, 'h'},
        {0, 0, 0, 0}
    };

    while ((opt = getopt_long(argc, argv, "c:i:p:vh", long_options, &option_index)) != -1) {
        switch (opt) {
            case 'c':
                config_path = optarg;
                break;
            case 'i':
                override_interface = optarg;
                break;
            case 'p':
                override_profile = optarg;
                break;
            case 'v':
                // Increment verbosity level
                if (g_verbosity == FeatureLogger::VerbosityLevel::NONE) {
                    g_verbosity = FeatureLogger::VerbosityLevel::BASIC;
                } else if (g_verbosity == FeatureLogger::VerbosityLevel::BASIC) {
                    g_verbosity = FeatureLogger::VerbosityLevel::GROUPED;
                } else if (g_verbosity == FeatureLogger::VerbosityLevel::GROUPED) {
                    g_verbosity = FeatureLogger::VerbosityLevel::DETAILED;
                }
                break;
            case 'h':
                print_usage(argv[0]);
                return 0;
            default:
                print_usage(argv[0]);
                return 1;
        }
    }

    if (config_path.empty()) {
        std::cerr << "❌ Error: Config file is required (-c/--config)\n";
        print_usage(argv[0]);
        return 1;
    }

    // ============================================================================
    // SETUP SIGNAL HANDLERS
    // ============================================================================

    setup_signal_handlers();

#ifdef PLUGIN_LOADER_ENABLED
    // ADR-012 PHASE 1b — load plugins from sniffer.json
    ml_defender::PluginLoader plugin_loader_(config_path);
    plugin_loader_.load_plugins();
    std::cout << "✅ [plugin-loader] Plugins loaded (ADR-012 PHASE 1b)" << std::endl;
#endif

    // ============================================================================
    // INITIALIZE PROTOBUF
    // ============================================================================

    GOOGLE_PROTOBUF_VERIFY_VERSION;
    std::cout << "✅ Protobuf version: " << google::protobuf::internal::VersionString(GOOGLE_PROTOBUF_VERSION) << std::endl;

    try {
        // ============================================================================
        // LOAD JSON CONFIGURATION
        // ============================================================================

        std::cout << "\n[Config] Loading configuration from: " << config_path << std::endl;

        if (!strict_load_json_config(config_path, g_config, false)) {
            std::cerr << "❌ Failed to load configuration" << std::endl;
            return 1;
        }

        std::cout << "✅ Configuration loaded successfully" << std::endl;

        // ============================================================================
        // ETCD INTEGRATION - DAY 20 (Encrypted Config Upload)
        // ============================================================================

        std::unique_ptr<sniffer::EtcdClient> etcd_client;

        if (g_config.etcd.enabled) {
            std::cout << "\n[etcd] Initializing etcd client integration..." << std::endl;

            // Crear cliente etcd
            // todo cuando tengamos HA en etcd-server, esto tendrá que cambiar.
            std::string etcd_endpoint = g_config.etcd.endpoints[0];  // ← Ahora SÍ existe
            etcd_client = std::make_unique<sniffer::EtcdClient>(etcd_endpoint, "sniffer");

            // Conectar y obtener clave de cifrado
            if (!etcd_client->initialize()) {
                std::cerr << "⚠️  [etcd] Failed to initialize - continuing without etcd" << std::endl;
                etcd_client.reset();
            } else {
                // Registrar servicio y subir configuración completa
                if (!etcd_client->registerService()) {
                    std::cerr << "⚠️  [etcd] Failed to register service - continuing without etcd" << std::endl;
                    etcd_client.reset();
                } else {
                    std::cout << "✅ [etcd] Sniffer registered and config uploaded" << std::endl;
                    std::cout << "🔐 [etcd] Config encrypted with ChaCha20-Poly1305" << std::endl;
                    std::cout << "🗜️  [etcd] Config compressed with LZ4" << std::endl;
                }
            }
        } else {
            std::cout << "\n[etcd] etcd integration disabled in config" << std::endl;
        }

        // ============================================================================
        // EXTRACT FAST DETECTOR CONFIGURATION (Day 12)
        // ============================================================================
        sniffer::FastDetectorConfig fast_detector_config;
        fast_detector_config.enabled = g_config.fast_detector.enabled;

        // Ransomware scores
        fast_detector_config.ransomware.scores.high_threat =
            g_config.fast_detector.ransomware.scores.high_threat;
        fast_detector_config.ransomware.scores.suspicious =
            g_config.fast_detector.ransomware.scores.suspicious;
        fast_detector_config.ransomware.scores.alert =
            g_config.fast_detector.ransomware.scores.alert;

        // Ransomware thresholds
        fast_detector_config.ransomware.activation_thresholds.external_ips_30s =
            g_config.fast_detector.ransomware.activation_thresholds.external_ips_30s;
        fast_detector_config.ransomware.activation_thresholds.smb_diversity =
            g_config.fast_detector.ransomware.activation_thresholds.smb_diversity;
        fast_detector_config.ransomware.activation_thresholds.dns_entropy =
            g_config.fast_detector.ransomware.activation_thresholds.dns_entropy;
        fast_detector_config.ransomware.activation_thresholds.failed_dns_ratio =
            g_config.fast_detector.ransomware.activation_thresholds.failed_dns_ratio;
        fast_detector_config.ransomware.activation_thresholds.upload_download_ratio =
            g_config.fast_detector.ransomware.activation_thresholds.upload_download_ratio;
        fast_detector_config.ransomware.activation_thresholds.burst_connections =
            g_config.fast_detector.ransomware.activation_thresholds.burst_connections;
        fast_detector_config.ransomware.activation_thresholds.unique_destinations_30s =
            g_config.fast_detector.ransomware.activation_thresholds.unique_destinations_30s;

        // Logging
        fast_detector_config.logging.log_activations =
            g_config.fast_detector.logging.log_activations;
        fast_detector_config.logging.log_features =
            g_config.fast_detector.logging.log_features;
        fast_detector_config.logging.log_decisions =
            g_config.fast_detector.logging.log_decisions;
        fast_detector_config.logging.log_frequency_seconds =
            g_config.fast_detector.logging.log_frequency_seconds;

        // Performance
        fast_detector_config.performance.max_latency_us =
            g_config.fast_detector.performance.max_latency_us;
        fast_detector_config.performance.enable_metrics =
            g_config.fast_detector.performance.enable_metrics;
        fast_detector_config.performance.track_activation_rate =
            g_config.fast_detector.performance.track_activation_rate;

        std::cout << "✅ Fast Detector configuration extracted" << std::endl;

        // ============================================================================
        // PARSE FILTER CONFIGURATION (v3.2)
        // ============================================================================
        std::cout << "\n[Filter] Parsing filter configuration..." << std::endl;

        // Re-parse JSON to get root object
        std::ifstream filter_config_file(config_path);
        if (!filter_config_file.is_open()) {
            std::cerr << "❌ Failed to re-open config file for filter parsing" << std::endl;
            return 1;
        }

        Json::Value json_root;
        Json::CharReaderBuilder reader_builder;
        std::string json_errors;

        if (!Json::parseFromStream(reader_builder, filter_config_file, &json_root, &json_errors)) {
            std::cerr << "❌ Failed to parse JSON for filters: " << json_errors << std::endl;
            filter_config_file.close();
            return 1;
        }
        filter_config_file.close();

        FilterConfiguration filter_config;
        if (!parse_filter_config(json_root, filter_config)) {
            std::cerr << "❌ Failed to parse filter configuration" << std::endl;
            return 1;
        }

        if (!validate_filter_mode(filter_config)) {
            std::cerr << "❌ Invalid filter configuration" << std::endl;
            return 1;
        }

        // Display filter configuration
        std::cout << "\n📋 Filter Configuration:" << std::endl;
        std::cout << "  Mode: " << filter_config.mode << std::endl;
        std::cout << "  Excluded ports: " << filter_config.excluded_ports.size() << std::endl;
        std::cout << "  Included ports: " << filter_config.included_ports.size() << std::endl;
        std::cout << "  Default action: " << filter_config.default_action << std::endl;

        /// ============================================================================
        // LOAD AND ATTACH EBPF PROGRAM
        // ============================================================================

        std::cout << "\n[eBPF] Loading and attaching eBPF program..." << std::endl;

        ebpf_loader_ptr = new sniffer::EbpfLoader();
        auto& ebpf_loader = *ebpf_loader_ptr;

        if (!ebpf_loader.load_program(g_config.kernel_space.ebpf_program)) {
            std::cerr << "❌ Failed to load eBPF program: " << g_config.kernel_space.ebpf_program << std::endl;
            return 1;
        }

        // ============================================================================
        // >>> NUEVO: DUAL-NIC DEPLOYMENT CONFIGURATION (Phase 1, Day 7)
        // ============================================================================
        std::cout << "\n[Dual-NIC] Configuring deployment mode..." << std::endl;

        // ✅ Declarar FUERA del try-catch
        std::unique_ptr<sniffer::DualNICManager> dual_nic_manager;
        bool dual_mode_enabled = false;

        try {
            dual_nic_manager = std::make_unique<sniffer::DualNICManager>(json_root);
            dual_nic_manager->initialize();

            // Configure interface_configs BPF map
            int interface_configs_fd = ebpf_loader.get_interface_configs_fd();
            if (interface_configs_fd >= 0) {
                dual_nic_manager->configure_bpf_map(interface_configs_fd);

                // Setup network if needed (gateway mode)
                if (dual_nic_manager->is_dual_mode()) {
                    dual_nic_manager->enable_ip_forwarding();
                    dual_nic_manager->setup_nat_rules();
                    dual_mode_enabled = true;
                }
            } else {
                std::cout << "[WARNING] interface_configs map not found - using legacy single-interface mode" << std::endl;
            }
        } catch (const std::exception& e) {
            std::cerr << "[WARNING] Dual-NIC configuration failed: " << e.what() << std::endl;
            std::cerr << "          Falling back to legacy single-interface mode" << std::endl;
            dual_nic_manager.reset();
        }

        std::cout << "✅ Deployment configuration complete\n" << std::endl;
        // ============================================================================
        // >>> FIN DUAL-NIC CONFIGURATION
        // ============================================================================

        bool attached = false;
        std::cout << "[INFO] Using SKB mode (TC-based eBPF)" << std::endl;

        // Dual-NIC: attach a todas las interfaces configuradas
        if (dual_nic_manager && dual_mode_enabled) {
            std::cout << "[INFO] Dual-NIC mode: attaching to multiple interfaces" << std::endl;
            const auto& interfaces = dual_nic_manager->get_interfaces();
            attached = true;

            for (const auto& iface : interfaces) {
                bool iface_attached = ebpf_loader.attach_skb(iface.name);
                if (!iface_attached) {
                    std::cerr << "❌ Failed to attach to interface: " << iface.name << std::endl;
                    attached = false;
                } else {
                    std::cout << "✅ eBPF program attached to interface: " << iface.name << std::endl;
                }
            }
        } else {
            // Single-NIC mode
            attached = ebpf_loader.attach_skb(g_config.capture_interface);
            if (attached) {
                std::cout << "✅ eBPF program attached to interface: " << g_config.capture_interface << std::endl;
            }
        }

        if (!attached) {
            std::cerr << "❌ Failed to attach eBPF program" << std::endl;
            return 1;
        }

        int ring_fd = ebpf_loader.get_ringbuf_fd();
        if (ring_fd < 0) {
            std::cerr << "❌ Failed to get ring buffer FD" << std::endl;
            return 1;
        }

        std::cout << "✅ Ring buffer FD: " << ring_fd << std::endl;

        // ============================================================================
        // LOAD FILTER CONFIGURATION TO BPF MAPS (v3.2)
        // ============================================================================
        std::cout << "\n[BPF Maps] Loading filter configuration to kernel..." << std::endl;

        sniffer::BPFMapManager bpf_map_manager;

        if (!bpf_map_manager.load_filter_config_with_fds(
            ebpf_loader.get_excluded_ports_fd(),
            ebpf_loader.get_included_ports_fd(),
            ebpf_loader.get_filter_settings_fd(),
            filter_config.excluded_ports,
            filter_config.included_ports,
            filter_config.get_default_action_value()
        )) {
            std::cerr << "❌ Failed to load filter configuration to BPF maps" << std::endl;
            std::cerr << "   Ensure the eBPF program defines the required maps:" << std::endl;
            std::cerr << "   - excluded_ports" << std::endl;
            std::cerr << "   - included_ports" << std::endl;
            std::cerr << "   - filter_settings" << std::endl;
            return 1;
        }

        std::cout << "✅ Filter configuration loaded to kernel space" << std::endl;
        std::cout << "✅ Sniffer ready with active filtering" << std::endl;

        // ============================================================================
        // INITIALIZE THREAD MANAGER
        // ============================================================================

        std::cout << "\n[ThreadManager] Initializing thread manager..." << std::endl;

        sniffer::ThreadingConfig threading_config;
        threading_config.ring_consumer_threads = g_config.threading.ring_consumer_threads;
        threading_config.feature_processor_threads = g_config.threading.feature_processor_threads;
        threading_config.zmq_sender_threads = g_config.threading.zmq_sender_threads;
        threading_config.statistics_collector_threads = g_config.threading.statistics_collector_threads;
        threading_config.total_worker_threads = g_config.threading.total_worker_threads;
        threading_config.cpu_affinity.enabled = g_config.threading.cpu_affinity_enabled;
        threading_config.cpu_affinity.ring_consumers = g_config.threading.ring_consumers_affinity;
        threading_config.cpu_affinity.processors = g_config.threading.processors_affinity;
        threading_config.cpu_affinity.zmq_senders = g_config.threading.zmq_senders_affinity;
        threading_config.cpu_affinity.statistics = g_config.threading.statistics_affinity;

        thread_manager = std::make_shared<sniffer::ThreadManager>(threading_config);

        if (!thread_manager->start()) {
            std::cerr << "❌ Failed to start thread manager" << std::endl;
            return 1;
        }
        std::cout << "✅ Thread manager started" << std::endl;

        // ============================================================================
        // INITIALIZE RING BUFFER CONSUMER
        // ============================================================================

        std::cout << "\n[RingBuffer] Initializing RingBufferConsumer..." << std::endl;

        sniffer::SnifferConfig sniffer_config;
        sniffer_config.node_id = g_config.node_id;
        sniffer_config.cluster_name = g_config.cluster_name;

        // Mapear buffers
        sniffer_config.buffers.ring_buffer_entries = g_config.buffers.ring_buffer_entries;
        sniffer_config.buffers.user_processing_queue_depth = g_config.buffers.user_processing_queue_depth;
        sniffer_config.buffers.protobuf_serialize_buffer_size = g_config.buffers.protobuf_serialize_buffer_size;
        sniffer_config.buffers.zmq_send_buffer_size = g_config.buffers.zmq_send_buffer_size;
        sniffer_config.buffers.flow_state_buffer_entries = g_config.buffers.flow_state_buffer_entries;
        sniffer_config.buffers.statistics_buffer_entries = g_config.buffers.statistics_buffer_entries;
        sniffer_config.buffers.batch_processing_size = g_config.buffers.batch_processing_size;

        // Mapear threading
        sniffer_config.threading.ring_consumer_threads = g_config.threading.ring_consumer_threads;
        sniffer_config.threading.feature_processor_threads = g_config.threading.feature_processor_threads;
        sniffer_config.threading.zmq_sender_threads = g_config.threading.zmq_sender_threads;
        sniffer_config.threading.statistics_collector_threads = g_config.threading.statistics_collector_threads;
        sniffer_config.threading.total_worker_threads = g_config.threading.total_worker_threads;

        // Mapear CPU affinity
        sniffer_config.threading.cpu_affinity.enabled = g_config.threading.cpu_affinity_enabled;
        sniffer_config.threading.cpu_affinity.ring_consumers = g_config.threading.ring_consumers_affinity;
        sniffer_config.threading.cpu_affinity.processors = g_config.threading.processors_affinity;
        sniffer_config.threading.cpu_affinity.zmq_senders = g_config.threading.zmq_senders_affinity;
        sniffer_config.threading.cpu_affinity.statistics = g_config.threading.statistics_affinity;

        // Mapear thread priorities
        sniffer_config.threading.thread_priorities["ring_consumers"] = g_config.threading.ring_consumers_priority;
        sniffer_config.threading.thread_priorities["processors"] = g_config.threading.processors_priority;
        sniffer_config.threading.thread_priorities["zmq_senders"] = g_config.threading.zmq_senders_priority;

        // Mapear ZMQ
        sniffer_config.zmq.worker_threads = g_config.zmq.worker_threads;
        sniffer_config.zmq.io_thread_pools = g_config.zmq.io_thread_pools;

        // Mapear socket pools
        sniffer_config.zmq.socket_pools.push_sockets = g_config.zmq.push_sockets;
        sniffer_config.zmq.socket_pools.load_balancing = g_config.zmq.load_balancing;
        sniffer_config.zmq.socket_pools.failover_enabled = g_config.zmq.failover_enabled;

        // Mapear queue management
        sniffer_config.zmq.queue_management.internal_queues = g_config.zmq.internal_queues;
        sniffer_config.zmq.queue_management.queue_size = g_config.zmq.queue_size;
        sniffer_config.zmq.queue_management.queue_timeout_ms = g_config.zmq.queue_timeout_ms;
        sniffer_config.zmq.queue_management.overflow_policy = g_config.zmq.overflow_policy;

        // Mapear connection settings
        sniffer_config.zmq.connection_settings.sndhwm = g_config.zmq.sndhwm;
        sniffer_config.zmq.connection_settings.linger_ms = g_config.zmq.linger_ms;
        sniffer_config.zmq.connection_settings.send_timeout_ms = g_config.zmq.send_timeout_ms;
        sniffer_config.zmq.connection_settings.rcvhwm = g_config.zmq.rcvhwm;
        sniffer_config.zmq.connection_settings.recv_timeout_ms = g_config.zmq.recv_timeout_ms;
        sniffer_config.zmq.connection_settings.tcp_keepalive = g_config.zmq.tcp_keepalive;
        sniffer_config.zmq.connection_settings.sndbuf = g_config.zmq.sndbuf;
        sniffer_config.zmq.connection_settings.rcvbuf = g_config.zmq.rcvbuf;
        sniffer_config.zmq.connection_settings.reconnect_interval_ms = g_config.zmq.reconnect_interval_ms;
        sniffer_config.zmq.connection_settings.max_reconnect_attempts = g_config.zmq.max_reconnect_attempts;

        // Mapear batch processing
        sniffer_config.zmq.batch_processing.enabled = g_config.zmq.batch_enabled;
        sniffer_config.zmq.batch_processing.batch_size = g_config.zmq.batch_size;
        sniffer_config.zmq.batch_processing.batch_timeout_ms = g_config.zmq.batch_timeout_ms;
        sniffer_config.zmq.batch_processing.max_batches_queued = g_config.zmq.max_batches_queued;

        // Mapear network
        sniffer_config.network.output_socket.address = g_config.network_output.address;
        sniffer_config.network.output_socket.port = g_config.network_output.port;
        sniffer_config.network.output_socket.mode = g_config.network_output.mode;
        sniffer_config.network.output_socket.socket_type = g_config.network_output.socket_type;
        sniffer_config.network.output_socket.high_water_mark = g_config.network_output.high_water_mark;

        // Mapear transport/compression
        sniffer_config.transport.compression.enabled = g_config.compression.enabled;
        sniffer_config.transport.compression.algorithm = g_config.compression.algorithm;
        sniffer_config.transport.compression.level = g_config.compression.level;
        sniffer_config.transport.compression.min_compress_size = g_config.compression.min_compress_size;
        sniffer_config.transport.compression.compression_ratio_threshold = g_config.compression.compression_ratio_threshold;
        sniffer_config.transport.compression.adaptive_compression = g_config.compression.adaptive_compression;

        // ═══════════════════════════════════════════════════════════════════════
// 🎯 DAY 29: Get encryption seed from etcd (REQUIRED, with retry)
// ═══════════════════════════════════════════════════════════════════════
std::string encryption_seed;

if (!etcd_client) {
    std::cerr << "\n❌ FATAL: etcd integration is REQUIRED for sniffer" << std::endl;
    std::cerr << "   Reason: Encryption seed must be obtained from etcd-server" << std::endl;
    std::cerr << "   Action: Enable etcd in config and ensure etcd-server is running" << std::endl;
    std::cerr << "   Security: Hardcoded encryption keys are NOT acceptable" << std::endl;
    return 1;
}

// Retry mechanism (3 attempts, like firewall-acl-agent)
const int max_retries = 3;
const int retry_delay_seconds = 2;

for (int attempt = 1; attempt <= max_retries; ++attempt) {
    std::cout << "🔑 [etcd] Attempt " << attempt << "/" << max_retries
              << ": Getting encryption seed..." << std::endl;

    encryption_seed = etcd_client->get_encryption_seed();

    if (!encryption_seed.empty()) {
        std::cout << "✅ Encryption seed obtained from etcd-server" << std::endl;
        break;
    }

    if (attempt < max_retries) {
        std::cerr << "⚠️  [etcd] Failed to get seed, retrying in "
                  << retry_delay_seconds << "s..." << std::endl;
        std::this_thread::sleep_for(std::chrono::seconds(retry_delay_seconds));
    }
}

if (encryption_seed.empty()) {
    std::cerr << "\n❌ FATAL: Failed to get encryption seed after "
              << max_retries << " attempts" << std::endl;
    std::cerr << "   Reason: etcd-server did not provide encryption key" << std::endl;
    std::cerr << "   Action: Verify etcd-server is running and accessible" << std::endl;
    std::cerr << "   Network: Check connectivity to " << g_config.etcd.endpoints[0] << std::endl;
    std::cerr << "   HA Setup: Consider deploying etcd-server in HA configuration" << std::endl;
    return 1;
}

// DAY 80 ✅ ml_defender thresholds — JSON is the LAW (Phase1-Day4-CRITICAL CERRADO)
        // DAY 80 ✅ mapeo explícito (MLDefenderConfig.thresholds vs StrictConfig.ml_defender)
        sniffer_config.ml_defender.thresholds.ddos       = g_config.ml_defender.ddos;
        sniffer_config.ml_defender.thresholds.ransomware = g_config.ml_defender.ransomware;
        sniffer_config.ml_defender.thresholds.traffic    = g_config.ml_defender.traffic;
        sniffer_config.ml_defender.thresholds.internal   = g_config.ml_defender.internal;

        ring_consumer_ptr = new sniffer::RingBufferConsumer(sniffer_config, fast_detector_config, encryption_seed);
        auto& ring_consumer = *ring_consumer_ptr;

        // Configure stats interval from monitoring config
        ring_consumer.set_stats_interval(g_config.monitoring.stats_interval_seconds);
#ifdef PLUGIN_LOADER_ENABLED
        ring_consumer.set_plugin_loader(&plugin_loader_);
        std::cout << "✅ [PHASE 2c] plugin_loader conectado a RingBufferConsumer" << std::endl;
#endif
#ifdef PLUGIN_LOADER_ENABLED
        ring_consumer.set_plugin_loader(&plugin_loader_);
        std::cout << "✅ [PHASE 2c] plugin_loader conectado a RingBufferConsumer" << std::endl;
#endif

        if (!ring_consumer.initialize(ring_fd, thread_manager)) {
            std::cerr << "❌ Failed to initialize RingBufferConsumer" << std::endl;
            return 1;
        }

        if (!ring_consumer.start()) {
            std::cerr << "❌ Failed to start RingBufferConsumer" << std::endl;
            return 1;
        }

        std::cout << "✅ RingBufferConsumer started - capturing REAL packets from kernel" << std::endl;
        std::cout << "✅ Statistics will be displayed every " << g_config.monitoring.stats_interval_seconds
                  << " seconds" << std::endl;

        // ============================================================================
        // MAIN LOOP - WAIT FOR TERMINATION SIGNAL
        // ============================================================================

        std::cout << "\n🚀 Sniffer running with hybrid filtering enabled" << std::endl;
        std::cout << "   Press Ctrl+C to stop\n" << std::endl;

        // [DDOS-KREAD-D274:MAIN-START] Lector del agregador DDoS en-kernel (opcional, DAY274).
        // Es una capa de MEDICION: un fallo aqui nunca tumba el sniffer.
        if (g_config.kernel_space.ddos_kernel_agg_enabled) {
            const int ddos_fd = ebpf_loader_ptr ? ebpf_loader_ptr->get_ddos_victims_fd() : -1;
            if (ddos_fd < 0) {
                std::cerr << "[WARNING] ddos_kernel_agg_enabled=true pero el mapa ddos_victims no esta "
                             "disponible (objeto eBPF anterior al parche); lector DDoS desactivado"
                          << std::endl;
            } else if (g_config.kernel_space.ddos_kernel_agg_csv_path.empty()) {
                std::cerr << "[WARNING] ddos_kernel_agg_csv_path vacio; lector DDoS desactivado"
                          << std::endl;
            } else {
                ddos_reader_ptr = new sniffer::DdosKernelReader(
                    ddos_fd, ebpf_loader_ptr->get_ddos_victims_max_entries(),
                    g_config.kernel_space.ddos_kernel_agg_interval_ms,
                    g_config.kernel_space.ddos_kernel_agg_csv_path);
                if (!ddos_reader_ptr->start()) {
                    std::cerr << "[WARNING] no se pudo arrancar el lector DDoS; sigo sin el"
                              << std::endl;
                    delete ddos_reader_ptr;
                    ddos_reader_ptr = nullptr;
                }
            }
        }

        while (g_running) {
            std::this_thread::sleep_for(std::chrono::seconds(1));
        }

        // ============================================================================
        // CLEANUP (SIN MEMORY LEAKS)
        // ============================================================================

        std::cout << "\n[Cleanup] Stopping components..." << std::endl;

        // [DDOS-KREAD-D274:MAIN-STOP] Parar el lector DDoS ANTES de liberar el loader:
        // el fd del mapa ddos_victims se cierra con el (leerlo despues = fd invalido/reutilizado).
        if (ddos_reader_ptr) {
            ddos_reader_ptr->stop();
            delete ddos_reader_ptr;
            ddos_reader_ptr = nullptr;
        }

        // Stop RingBufferConsumer first
        if (ring_consumer_ptr) {
            ring_consumer_ptr->stop();
            delete ring_consumer_ptr;
            ring_consumer_ptr = nullptr;
        }

        // Stop ThreadManager
        if (thread_manager) {
            thread_manager->stop();
            thread_manager.reset();  // smart_ptr cleanup
        }

        // Cleanup eBPF loader
        if (ebpf_loader_ptr) {
            delete ebpf_loader_ptr;
            ebpf_loader_ptr = nullptr;
        }

#ifdef PLUGIN_LOADER_ENABLED
        plugin_loader_.shutdown();
        std::cout << "✅ [plugin-loader] Plugins shutdown cleanly" << std::endl;
#endif
        std::cout << "✅ All components stopped cleanly" << std::endl;

    } catch (const std::exception& e) {
        std::cerr << "\n❌ FATAL ERROR: " << e.what() << "\n";

        // Emergency cleanup
        // [DDOS-KREAD-D274:MAIN-EMERG] mismo orden que en el cleanup normal: lector antes que el loader
        if (ddos_reader_ptr) {
            ddos_reader_ptr->stop();
            delete ddos_reader_ptr;
            ddos_reader_ptr = nullptr;
        }
        if (ring_consumer_ptr) {
            delete ring_consumer_ptr;
            ring_consumer_ptr = nullptr;
        }

        if (ebpf_loader_ptr) {
            delete ebpf_loader_ptr;
            ebpf_loader_ptr = nullptr;
        }

        return 1;
    }

    google::protobuf::ShutdownProtobufLibrary();
    std::cout << "\n👋 Sniffer stopped correctly\n";
    return 0;
}