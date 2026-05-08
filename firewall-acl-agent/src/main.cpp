//===----------------------------------------------------------------------===//
// ML Defender - Firewall ACL Agent
// main.cpp - High-Performance Packet DROP Agent with Full Observability
// Day 50: Comprehensive diagnostics and crash analysis
// Day 52: Config-driven logging, ipsets-only (no singleton ipset)
//===----------------------------------------------------------------------===//

#include <iostream>
#include <csignal>
#include <atomic>
#include <thread>
#include <chrono>
#include <ctime>

// Day 50: Observability infrastructure
#include "firewall_observability_logger.hpp"
#include "crash_diagnostics.hpp"

#include "firewall/config_loader.hpp"
#include "firewall/ipset_wrapper.hpp"
#include "firewall/iptables_wrapper.hpp"
#include "firewall/batch_processor.hpp"
#include "firewall/zmq_subscriber.hpp"
#include "firewall/etcd_client.hpp"

#include <json/json.h>
#include <cstring>
#include <unistd.h>
#include <exception>

#ifdef PLUGIN_LOADER_ENABLED
#include "plugin_loader/plugin_loader.hpp"
#include "plugin_loader/plugin_api.h"
#endif

using namespace mldefender::firewall;

//===----------------------------------------------------------------------===//
// Global Observability Infrastructure (Day 50)
//===----------------------------------------------------------------------===//

namespace mldefender::firewall::observability {
    std::unique_ptr<ObservabilityLogger> g_logger;
}

namespace mldefender::firewall::diagnostics {
    std::unique_ptr<SystemState> g_system_state;
}

//===----------------------------------------------------------------------===//
// Signal Handling (Enhanced for Day 50)
//===----------------------------------------------------------------------===//

std::atomic<bool> g_running{true};

void signal_handler(int signum) {
    FIREWALL_LOG_INFO("Shutdown signal received", "signal", signum);

    // Stop processing loop
    if (mldefender::firewall::diagnostics::g_system_state) {
        mldefender::firewall::diagnostics::g_system_state->is_running.store(false);
    }
    g_running.store(false);

    // Dump final state
    DUMP_STATE_ON_ERROR("graceful_shutdown");
}

void setup_signal_handlers() {
    struct sigaction sa;
    sa.sa_handler = signal_handler;
    sigemptyset(&sa.sa_mask);
    sa.sa_flags = 0;

    sigaction(SIGINT, &sa, nullptr);
    sigaction(SIGTERM, &sa, nullptr);

    FIREWALL_LOG_INFO("Signal handlers installed", "signals", "SIGINT,SIGTERM");

    // DEBT-IRP-SIGCHLD-001: evitar zombies de fork()+execv() IRP
    // SA_NOCLDWAIT: el kernel recoge hijos automáticamente, sin necesidad de wait()
    sa.sa_handler = SIG_DFL;
    sigemptyset(&sa.sa_mask);
    sa.sa_flags = SA_NOCLDWAIT;
    sigaction(SIGCHLD, &sa, nullptr);
    FIREWALL_LOG_INFO("SIGCHLD SA_NOCLDWAIT instalado — IRP zombie prevention active");
}

//===----------------------------------------------------------------------===//
// Metrics Export (Enhanced for Day 50)
//===----------------------------------------------------------------------===//

void export_metrics(const FirewallAgentConfig& config,
                   const ZMQSubscriber& subscriber,
                   const BatchProcessor& processor) {
    const auto& zmq_stats = subscriber.get_stats();

    FIREWALL_LOG_INFO("Periodic metrics export",
        "messages_received", zmq_stats.messages_received.load(),
        "detections_processed", zmq_stats.detections_processed.load(),
        "parse_errors", zmq_stats.parse_errors.load(),
        "reconnects", zmq_stats.reconnects.load());

    // Also dump system state from diagnostics
    DUMP_STATE_ON_ERROR("periodic_metrics");
}

//===----------------------------------------------------------------------===//
// Health Checks (Enhanced for Day 50, Day 52: uses ipsets)
//===----------------------------------------------------------------------===//

bool perform_health_checks(const FirewallAgentConfig& config,
                          IPSetWrapper& ipset,
                          IPTablesWrapper& iptables,
                          const ZMQSubscriber& subscriber) {
    FIREWALL_LOG_INFO("Starting health checks");
    bool all_healthy = true;

    // ✅ Day 52: Use ipsets.at("blacklist")
    const auto& blacklist_ipset = config.ipsets.at("blacklist");

    // Check IPSet
    bool ipset_exists = ipset.set_exists(blacklist_ipset.set_name);
    if (!ipset_exists) {
        FIREWALL_LOG_ERROR("Health check failed: IPSet missing",
            "ipset_name", blacklist_ipset.set_name);
        all_healthy = false;
    } else {
        FIREWALL_LOG_DEBUG("Health check passed: IPSet exists",
            "ipset_name", blacklist_ipset.set_name);
    }

    // Check IPTables rule
    auto rules = iptables.list_rules("INPUT");
    bool rule_found = false;
    for (const auto& rule : rules) {
        if (rule.find(blacklist_ipset.set_name) != std::string::npos) {
            rule_found = true;
            break;
        }
    }

    if (!rule_found) {
        FIREWALL_LOG_ERROR("Health check failed: IPTables rule missing",
            "ipset_name", blacklist_ipset.set_name);
        all_healthy = false;
    } else {
        FIREWALL_LOG_DEBUG("Health check passed: IPTables rule exists");
    }

    // Check ZMQ connection
    const auto& stats = subscriber.get_stats();
    bool zmq_connected = stats.currently_connected.load();
    if (!zmq_connected) {
        FIREWALL_LOG_WARN("Health check warning: ZMQ not connected");
        all_healthy = false;
    } else {
        FIREWALL_LOG_DEBUG("Health check passed: ZMQ connected");
    }

    FIREWALL_LOG_INFO("Health checks completed",
        "status", all_healthy ? "HEALTHY" : "DEGRADED",
        "ipset_ok", ipset_exists,
        "iptables_ok", rule_found,
        "zmq_ok", zmq_connected);

    return all_healthy;
}

//===----------------------------------------------------------------------===//
// Usage
//===----------------------------------------------------------------------===//

void print_usage(const char* program_name) {
    std::cout << "ML Defender - Firewall ACL Agent\n"
              << "High-Performance Packet DROP Agent (1M+ packets/sec)\n"
              << "Day 52: Config-driven, ipsets-only (no singleton)\n\n"
              << "Usage: " << program_name << " [options]\n\n"
              << "Options:\n"
              << "  -c, --config <file>    Configuration file (required)\n"
              << "  -d, --daemonize        Run as daemon\n"
              << "  -t, --test-config      Test configuration and exit\n"
              << "  --verbose              Enable verbose logging (DEBUG level)\n"
              << "  --quiet                Quiet mode (ERROR level only)\n"
              << "  -v, --version          Show version\n"
              << "  -h, --help             Show this help\n\n"
              << "Day 52 Features:\n"
              << "  • Log path from config.logging.file\n"
              << "  • IPSet names from config.ipsets (no singleton)\n"
              << "  • IPSet creation verification\n"
              << std::endl;
}

void print_version() {
    std::cout << "ML Defender - Firewall ACL Agent v1.0.0 (Day 52)\n"
              << "Via Appia Quality: Built to last decades\n"
              << "Enhanced: Config-driven, ipsets-only\n"
              << std::endl;
}

//===----------------------------------------------------------------------===//
// Main Entry Point (Day 52 Enhanced)
//===----------------------------------------------------------------------===//

int main(int argc, char** argv) {
#ifdef PLUGIN_LOADER_ENABLED
    std::unique_ptr<ml_defender::PluginLoader> plugin_loader;
#endif

    // SET_TERMINATE — DAY 100 (ADR-022: fail-closed, unhandled exceptions)
    std::set_terminate([]() {
        std::cerr << "[FATAL] std::terminate() called — unhandled exception or contract violation\n";
        std::abort();
    });
    // Parse command line arguments
    std::string config_path = "/etc/ml-defender/firewall-acl-agent/firewall.json";  // ✅ Prod path — symlink → /vagrant/ en dev
    bool test_config = false;
    bool verbose = false;
    bool quiet = false;

    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];

        if (arg == "-h" || arg == "--help") {
            print_usage(argv[0]);
            return 0;
        } else if (arg == "-v" || arg == "--version") {
            print_version();
            return 0;
        } else if (arg == "-c" || arg == "--config") {
            if (i + 1 < argc) {
                config_path = argv[++i];  // ✅ Use user-provided path
            } else {
                std::cerr << "[ERROR] --config requires a file path" << std::endl;
                return 1;
            }
        } else if (arg == "-t" || arg == "--test-config") {
            test_config = true;
        } else if (arg == "--verbose") {
            verbose = true;
        } else if (arg == "--quiet") {
            quiet = true;
        }
    }

    // ═══════════════════════════════════════════════════════════════════════
    // Day 52: Early initialization (crash diagnostics only, logger after config)
    // ═══════════════════════════════════════════════════════════════════════

    try {
        // Initialize system state for crash diagnostics (before config loading)
        mldefender::firewall::diagnostics::g_system_state =
            std::make_unique<mldefender::firewall::diagnostics::SystemState>();

        // Install crash diagnostics early
        mldefender::firewall::diagnostics::install_crash_handlers();

    } catch (const std::exception& e) {
        std::cerr << "[FATAL] Failed to initialize crash diagnostics: " << e.what() << std::endl;
        return 1;
    }

    std::cout << "╔════════════════════════════════════════════════════════╗\n"
              << "║  ML Defender - Firewall ACL Agent (Day 52)            ║\n"
              << "║  High-Performance Packet DROP Agent                   ║\n"
              << "║  Target: 1M+ packets/sec                               ║\n"
              << "║  Config-Driven: ipsets-only (no singleton)            ║\n"
              << "╚════════════════════════════════════════════════════════╝\n"
              << std::endl;

    // ═══════════════════════════════════════════════════════════════════════
    // Configuration Loading (Day 52: Before logger init)
    // ═══════════════════════════════════════════════════════════════════════

    std::unique_ptr<mldefender::firewall::EtcdClient> etcd_client;
    FirewallAgentConfig config;

    try {
        std::cout << "[INFO] Loading configuration from: " << config_path << std::endl;

        config = ConfigLoader::load_from_file(config_path);

        std::cout << "[INFO] Configuration loaded successfully" << std::endl;

#ifdef PLUGIN_LOADER_ENABLED
    plugin_loader = std::make_unique<ml_defender::PluginLoader>(config_path);
    plugin_loader->load_plugins();
    std::cout << "[INFO] plugin-loader: " << plugin_loader->loaded_count() << " plugin(s) cargados" << std::endl;

    // TEST-INTEG-4a: invocar plugin_process_message() con MessageContext real
    // Gate: result_code==0 + CryptoTransport decryption path sin modificar
    if (plugin_loader->loaded_count() > 0) {
        const char* synthetic_payload =
            "{\"event\":\"TEST-INTEG-4a\",\"src_ip\":\"192.168.1.1\",\"threat\":\"none\"}";
        ::MessageContext msg_ctx{};  // C ABI — namespace global (extern "C")
        msg_ctx.payload     = reinterpret_cast<const uint8_t*>(synthetic_payload);
        msg_ctx.payload_len = std::strlen(synthetic_payload);
        msg_ctx.src_ip      = 0xC0A80101; // 192.168.1.1
        msg_ctx.dst_ip      = 0xC0A80164; // 192.168.1.100
        msg_ctx.src_port    = 12345;
        msg_ctx.dst_port    = 5572;
        msg_ctx.protocol    = 6;  // TCP
        msg_ctx.direction   = 0;  // RX
        msg_ctx.nonce       = nullptr; // no disponible pre-decrypt — válido en smoke test
        msg_ctx.tag         = nullptr;
        msg_ctx.result_code = 0;
        msg_ctx.annotation[0] = '\0';

        plugin_loader->invoke_all(msg_ctx);
        std::cout << "[INFO] TEST-INTEG-4a: result_code=" << msg_ctx.result_code;
        if (msg_ctx.annotation[0] != '\0') {
            std::cout << " annotation='" << msg_ctx.annotation << "'";
        }
        std::cout << std::endl;
    }
#endif
        std::cout << "[INFO] Dry-run mode: " << (config.operation.dry_run ? "ENABLED" : "DISABLED") << std::endl;

        // Show DRY-RUN status prominently
        if (config.operation.dry_run) {
            std::cout << "\n╔════════════════════════════════════════════════════════╗\n"
                      << "║  🔍 DRY-RUN MODE ENABLED 🔍                           ║\n"
                      << "║  No actual firewall rules will be modified            ║\n"
                      << "╚════════════════════════════════════════════════════════╝\n"
                      << std::endl;
        }

        // ✅ Day 52: Validate required ipsets exist in config
        if (config.ipsets.count("blacklist") == 0) {
            std::cerr << "[FATAL] Configuration error: 'ipsets.blacklist' is required" << std::endl;
            return 1;
        }

    } catch (const std::exception& e) {
        std::cerr << "[FATAL] Failed to load configuration: " << e.what() << std::endl;
        return 1;
    }

    // ═══════════════════════════════════════════════════════════════════════
    // Day 52: Initialize Logger with Config Path
    // ═══════════════════════════════════════════════════════════════════════

    try {
        // Determine log level
        bool enable_verbose = verbose && !quiet;  // Verbose overrides quiet

        // ✅ Day 52: Use log path from config
        std::string log_path = config.logging.file;

        std::cout << "[INFO] Initializing logger: " << log_path << std::endl;

        mldefender::firewall::observability::g_logger =
            std::make_unique<mldefender::firewall::observability::ObservabilityLogger>(
                log_path, enable_verbose);

        FIREWALL_LOG_INFO("════════════════════════════════════════════════════════");
        FIREWALL_LOG_INFO("ML Defender - Firewall ACL Agent v1.0.0 (Day 52)");
        FIREWALL_LOG_INFO("High-Performance Packet DROP Agent");
        FIREWALL_LOG_INFO("Via Appia Quality: Built to last decades");
        FIREWALL_LOG_INFO("════════════════════════════════════════════════════════");

        FIREWALL_LOG_INFO("Observability initialized",
            "log_file", log_path,
            "verbose_mode", enable_verbose,
            "config_path", config_path);

    } catch (const std::exception& e) {
        std::cerr << "[FATAL] Failed to initialize logger: " << e.what() << std::endl;
        return 1;
    }

    // ═══════════════════════════════════════════════════════════════════════
    // Configuration Summary (Day 52: Now with logger available)
    // ═══════════════════════════════════════════════════════════════════════

    ConfigLoader::log_config_summary(config);

    // ═══════════════════════════════════════════════════════════════════════
    // ETCD Integration (Day 50: Fixed path bug)
    // ═══════════════════════════════════════════════════════════════════════

    if (config.etcd.enabled) {
        FIREWALL_LOG_INFO("etcd integration enabled",
            "endpoint", config.etcd.endpoints[0]);

        std::string etcd_endpoint = config.etcd.endpoints[0];

        try {
            etcd_client = std::make_unique<mldefender::firewall::EtcdClient>(
                etcd_endpoint,
                "firewall-acl-agent"
            );

            if (!etcd_client->initialize()) {
                FIREWALL_LOG_WARN("etcd initialization failed - continuing without etcd");
                etcd_client.reset();
            } else if (!etcd_client->registerService()) {
                FIREWALL_LOG_WARN("etcd service registration failed - continuing without etcd");
                etcd_client.reset();
            } else {
                FIREWALL_LOG_INFO("etcd registration successful",
                    "service", "firewall-acl-agent",
                    "endpoint", etcd_endpoint);
            }
        } catch (const std::exception& e) {
            FIREWALL_LOG_ERROR("etcd client exception",
                "error", e.what());
            etcd_client.reset();
        }
    } else {
        FIREWALL_LOG_INFO("etcd integration disabled in configuration");
    }

    FIREWALL_LOG_DEBUG("Configuration phase completed successfully");

    // Test config mode
    if (test_config) {
        FIREWALL_LOG_INFO("Configuration test mode - exiting");
        std::cout << "[INFO] Configuration test passed ✓" << std::endl;
        return 0;
    }

    // Permission check
    if (getuid() != 0 && !config.operation.dry_run) {
        FIREWALL_LOG_CRASH("Insufficient privileges - must run as root",
            "uid", getuid(),
            "dry_run", config.operation.dry_run);
        std::cerr << "[ERROR] This program must be run as root (or use dry_run mode)" << std::endl;
        return 1;
    }

    FIREWALL_LOG_DEBUG("Permission check passed",
        "uid", getuid(),
        "dry_run", config.operation.dry_run);

    // ═══════════════════════════════════════════════════════════════════════
    // Component Initialization (Day 52: ipsets-only, enhanced verification)
    // ═══════════════════════════════════════════════════════════════════════

    try {
        FIREWALL_LOG_INFO("Starting component initialization phase");

        // ───────────────────────────────────────────────────────────────────
        // IPSet Configuration (Day 52: All from ipsets map)
        // ───────────────────────────────────────────────────────────────────

        FIREWALL_LOG_INFO("Initializing IPSet wrapper");
        IPSetWrapper ipset;
        ipset.set_dry_run(config.operation.dry_run);

        // Create all ipsets from config.ipsets map
        if (!config.ipsets.empty()) {
            FIREWALL_LOG_INFO("Processing ipsets",
                "count", config.ipsets.size());

            for (const auto& [name, ipset_cfg] : config.ipsets) {
                if (!ipset.set_exists(ipset_cfg.set_name)) {
                    FIREWALL_LOG_INFO("Creating ipset",
                        "logical_name", name,
                        "set_name", ipset_cfg.set_name,
                        "timeout", ipset_cfg.timeout);

                    IPSetConfig ipset_config;
                    ipset_config.name = ipset_cfg.set_name;
                    ipset_config.type = IPSetType::HASH_IP;
                    ipset_config.family = IPSetFamily::INET;
                    ipset_config.hashsize = ipset_cfg.hash_size;
                    ipset_config.maxelem = ipset_cfg.max_elements;
                    ipset_config.timeout = ipset_cfg.timeout;
                    ipset_config.counters = true;
                    ipset_config.comment = !ipset_cfg.comment.empty();

                    if (!ipset.create_set(ipset_config)) {
                        FIREWALL_LOG_ERROR("Failed to create ipset",
                            "logical_name", name,
                            "set_name", ipset_cfg.set_name);
                        DUMP_STATE_ON_ERROR("ipset_creation_failed");
                        return 1;
                    }

                    FIREWALL_LOG_INFO("IPSet created successfully",
                        "logical_name", name,
                        "set_name", ipset_cfg.set_name);
                } else {
                    FIREWALL_LOG_DEBUG("IPSet already exists",
                        "logical_name", name,
                        "set_name", ipset_cfg.set_name);
                }
            }
        }

        // ═══════════════════════════════════════════════════════════════════════
        // Day 52: IPSet Creation Verification
        // ═══════════════════════════════════════════════════════════════════════

        FIREWALL_LOG_INFO("════════════════════════════════════════════════════════");
        FIREWALL_LOG_INFO("IPSet Creation Verification (Day 52)");
        FIREWALL_LOG_INFO("════════════════════════════════════════════════════════");

        // Verify all ipsets
        for (const auto& [name, ipset_cfg] : config.ipsets) {
            bool exists = ipset.set_exists(ipset_cfg.set_name);
            FIREWALL_LOG_INFO("IPSet verification",
                "logical_name", name,
                "set_name", ipset_cfg.set_name,
                "status", exists ? "EXISTS" : "MISSING");

            if (!exists) {
                FIREWALL_LOG_CRASH("IPSet verification failed",
                    "logical_name", name,
                    "set_name", ipset_cfg.set_name);
                std::cerr << "[FATAL] IPSet does not exist: " << ipset_cfg.set_name << std::endl;
                return 1;
            }
        }

        FIREWALL_LOG_INFO("All ipsets verified successfully",
            "count", config.ipsets.size());
        FIREWALL_LOG_INFO("════════════════════════════════════════════════════════");

        // ───────────────────────────────────────────────────────────────────
        // IPTables Configuration (Day 52: uses ipsets.at("blacklist"))
        // ───────────────────────────────────────────────────────────────────

        const auto& blacklist_ipset = config.ipsets.at("blacklist");

        FIREWALL_LOG_INFO("Configuring IPTables",
            "chain", config.iptables.chain_name,
            "rate_limiting", config.iptables.enable_rate_limiting);

        FirewallConfig firewall_config;
        firewall_config.blacklist_chain = config.iptables.chain_name;
        firewall_config.blacklist_ipset = blacklist_ipset.set_name;  // ✅ Day 52

        if (config.ipsets.count("whitelist") > 0) {
            firewall_config.whitelist_ipset = config.ipsets.at("whitelist").set_name;
            FIREWALL_LOG_INFO("Whitelist configured",
                "ipset_name", firewall_config.whitelist_ipset);
        }

        firewall_config.enable_rate_limiting = config.iptables.enable_rate_limiting;
        firewall_config.rate_limit_connections = config.iptables.rate_limit_connections;

        FIREWALL_LOG_INFO("Initializing IPTables wrapper");
        IPTablesWrapper iptables;
        iptables.set_dry_run(config.operation.dry_run);

        FIREWALL_LOG_INFO("Setting up IPTables rules");
        if (!iptables.setup_base_rules(firewall_config)) {
            FIREWALL_LOG_ERROR("Failed to setup IPTables rules");
            DUMP_STATE_ON_ERROR("iptables_setup_failed");

            if (!config.operation.dry_run) {
                std::cerr << "[ERROR] Failed to setup IPTables rules" << std::endl;
                return 1;
            }
        }

        FIREWALL_LOG_INFO("IPTables rules configured successfully");

        // ───────────────────────────────────────────────────────────────────
        // Batch Processor Configuration (Day 52: IPSet names from ipsets)
        // ───────────────────────────────────────────────────────────────────

        FIREWALL_LOG_INFO("Configuring batch processor",
            "batch_size_threshold", config.batch_processor.batch_size_threshold,
            "batch_time_threshold_ms", config.batch_processor.batch_time_threshold_ms,
            "max_pending_ips", config.batch_processor.max_pending_ips,
            "min_confidence", config.batch_processor.min_confidence);

        BatchProcessorConfig batch_config;
        batch_config.batch_size_threshold = config.batch_processor.batch_size_threshold;
        batch_config.batch_time_threshold = std::chrono::milliseconds(config.batch_processor.batch_time_threshold_ms);
        batch_config.max_pending_ips = config.batch_processor.max_pending_ips;
        batch_config.confidence_threshold = config.batch_processor.min_confidence;

        // ✅ Day 52: Assign ipset names from ipsets map
        batch_config.blacklist_ipset = blacklist_ipset.set_name;
        if (config.ipsets.count("whitelist") > 0) {
            batch_config.whitelist_ipset = config.ipsets.at("whitelist").set_name;
        }

        FIREWALL_LOG_INFO("Batch processor ipset configuration",
            "blacklist_ipset", batch_config.blacklist_ipset,
            "whitelist_ipset", batch_config.whitelist_ipset);

        FIREWALL_LOG_INFO("Initializing batch processor");
        BatchProcessor processor(ipset, batch_config);
        processor.set_irp_config(config.irp);  // ADR-042
        FIREWALL_LOG_INFO("Batch processor started successfully",
            "irp_auto_isolate", config.irp.auto_isolate,
            "irp_threshold",    config.irp.threat_score_threshold,
            "irp_interface",    config.irp.isolate_interface);

        // DEBT-IRP-AUTOISO-FALSE-001: WARNING prominente cuando IRP desactivado
        if (!config.irp.auto_isolate) {
            FIREWALL_LOG_WARN("════════════════════════════════════════════════════════");
            FIREWALL_LOG_WARN("IRP AUTO-ISOLATE DESACTIVADO (auto_isolate: false)");
            FIREWALL_LOG_WARN("El agente NO aislara el host automaticamente.");
            FIREWALL_LOG_WARN("Para activar: set auto_isolate=true en isolate.json");
            FIREWALL_LOG_WARN("SOLO activar tras onboarding explicito del operador.");
            FIREWALL_LOG_WARN("════════════════════════════════════════════════════════");
        }

        // ───────────────────────────────────────────────────────────────────
        // ZMQ Configuration (Day 50: Enhanced transport logging)
        // ───────────────────────────────────────────────────────────────────

        FIREWALL_LOG_INFO("Configuring ZMQ subscriber",
            "endpoint", config.zmq.endpoint,
            "topic", config.zmq.topic,
            "recv_timeout_ms", config.zmq.recv_timeout_ms);

        ZMQSubscriber::Config zmq_config;
        zmq_config.endpoint = config.zmq.endpoint;
        zmq_config.topic = config.zmq.topic;
        zmq_config.recv_timeout_ms = config.zmq.recv_timeout_ms;
        zmq_config.linger_ms = config.zmq.linger_ms;
        zmq_config.reconnect_interval_ms = config.zmq.reconnect_interval_ms;
        zmq_config.max_reconnect_interval_ms = config.zmq.max_reconnect_interval_ms;
        zmq_config.enable_reconnect = config.zmq.enable_reconnect;

        // ✅ Day 61: CSV batch logger output directory
        zmq_config.log_directory = config.csv_batch_logger.output_dir;

        // Transport configuration (compression)
        if (config.transport.compression.enabled) {
            zmq_config.compression_enabled = true;
            FIREWALL_LOG_INFO("LZ4 decompression enabled",
                "algorithm", config.transport.compression.algorithm);
        } else {
            zmq_config.compression_enabled = false;
            FIREWALL_LOG_INFO("LZ4 decompression disabled");
        }

        // Transport configuration (encryption)
        if (config.transport.encryption.enabled) {
            zmq_config.encryption_enabled = true;

            if (!etcd_client) {
                FIREWALL_LOG_CRASH("Encryption enabled but etcd not initialized");
                std::cerr << "[ERROR] Encryption enabled but etcd not initialized" << std::endl;
                std::cerr << "[ERROR] Set etcd.enabled = true in firewall.json" << std::endl;
                return 1;
            }

            FIREWALL_LOG_INFO("Retrieving crypto seed from etcd");
            zmq_config.crypto_token = etcd_client->get_crypto_seed();

            if (zmq_config.crypto_token.empty()) {
                FIREWALL_LOG_CRASH("Failed to retrieve crypto seed from etcd");
                std::cerr << "[ERROR] Failed to get crypto seed from etcd-server" << std::endl;
                return 1;
            }

            FIREWALL_LOG_INFO("ChaCha20-Poly1305 decryption enabled",
                "algorithm", config.transport.encryption.algorithm,
                "key_length", zmq_config.crypto_token.length());
        } else {
            zmq_config.encryption_enabled = false;
            FIREWALL_LOG_INFO("Decryption disabled");
        }

        FIREWALL_LOG_INFO("Initializing ZMQ subscriber");
        ZMQSubscriber subscriber(processor, zmq_config, etcd_client.get());

        FIREWALL_LOG_INFO("ZMQ subscriber created",
            "etcd_integration", etcd_client ? "ENABLED" : "DISABLED");

        // Start ZMQ subscriber thread
        FIREWALL_LOG_INFO("Starting ZMQ subscriber thread");
        mldefender::firewall::diagnostics::g_system_state->is_running.store(true);
        std::thread zmq_thread([&subscriber]() {
            subscriber.run();
        });
        zmq_thread.detach();

        FIREWALL_LOG_INFO("ZMQ subscriber initialized and running");

        // ───────────────────────────────────────────────────────────────────
        // Signal Handlers (Day 50: Enhanced)
        // ───────────────────────────────────────────────────────────────────

        setup_signal_handlers();

        // ───────────────────────────────────────────────────────────────────
        // Main Loop (Day 50: Enhanced with diagnostics)
        // ───────────────────────────────────────────────────────────────────

        FIREWALL_LOG_INFO("════════════════════════════════════════════════════════");
        FIREWALL_LOG_INFO("Firewall ACL Agent is now ACTIVE");
        FIREWALL_LOG_INFO("════════════════════════════════════════════════════════");
        FIREWALL_LOG_INFO("Configuration summary",
            "zmq_endpoint", config.zmq.endpoint,
            "topic_filter", config.zmq.topic.empty() ? "(all)" : config.zmq.topic,
            "blacklist_ipset", blacklist_ipset.set_name,
            "dry_run", config.operation.dry_run);

        std::cout << "\n[RUNNING] Firewall ACL Agent is now active\n"
                  << "[INFO] Listening on: " << config.zmq.endpoint << "\n"
                  << "[INFO] Topic filter: " << (config.zmq.topic.empty() ? "(all)" : config.zmq.topic) << "\n"
                  << "[INFO] Press Ctrl+C to stop\n"
                  << std::endl;

        auto last_health_check = std::chrono::steady_clock::now();
        auto last_metrics_export = std::chrono::steady_clock::now();

        while (g_running.load() &&
               mldefender::firewall::diagnostics::g_system_state->is_running.load()) {

            auto now = std::chrono::steady_clock::now();

            try {
                // Health checks every 30 seconds
                auto elapsed_health = std::chrono::duration_cast<std::chrono::seconds>(
                    now - last_health_check).count();

                if (elapsed_health >= 30) {
                    perform_health_checks(config, ipset, iptables, subscriber);
                    last_health_check = now;
                }

                // Metrics export every 30 seconds
                auto elapsed_metrics = std::chrono::duration_cast<std::chrono::seconds>(
                    now - last_metrics_export).count();

                if (elapsed_metrics >= 30) {
                    export_metrics(config, subscriber, processor);
                    last_metrics_export = now;
                }

            } catch (const std::exception& e) {
                FIREWALL_LOG_ERROR("Exception in main loop",
                    "error", e.what());
                DUMP_STATE_ON_ERROR("main_loop_exception");
            }

            std::this_thread::sleep_for(std::chrono::milliseconds(100));
        }

        // ───────────────────────────────────────────────────────────────────
        // Graceful Shutdown (Day 50: Enhanced)
        // ───────────────────────────────────────────────────────────────────

        FIREWALL_LOG_INFO("════════════════════════════════════════════════════════");
        FIREWALL_LOG_INFO("Initiating graceful shutdown");
        FIREWALL_LOG_INFO("════════════════════════════════════════════════════════");

        std::cout << "\n[SHUTDOWN] Stopping components..." << std::endl;

#ifdef PLUGIN_LOADER_ENABLED
        if (plugin_loader) {
            plugin_loader->shutdown();
            std::cout << "[INFO] plugin-loader: shutdown OK" << std::endl;
        }
#endif

        // Export final metrics
        export_metrics(config, subscriber, processor);
        FIREWALL_LOG_INFO("Final metrics exported");

        // Display final statistics
        const auto& zmq_stats = subscriber.get_stats();

        FIREWALL_LOG_INFO("Final statistics",
            "messages_received", zmq_stats.messages_received.load(),
            "detections_processed", zmq_stats.detections_processed.load(),
            "parse_errors", zmq_stats.parse_errors.load(),
            "reconnections", zmq_stats.reconnects.load());

        std::cout << "\n[STATS] Final Statistics:\n"
                  << "  Messages Received:     " << zmq_stats.messages_received.load() << "\n"
                  << "  Detections Processed:  " << zmq_stats.detections_processed.load() << "\n"
                  << "  Parse Errors:          " << zmq_stats.parse_errors.load() << "\n"
                  << "  Reconnections:         " << zmq_stats.reconnects.load() << "\n"
                  << std::endl;

        // Final state dump
        DUMP_STATE_ON_ERROR("clean_shutdown");

        FIREWALL_LOG_INFO("════════════════════════════════════════════════════════");
        FIREWALL_LOG_INFO("Firewall ACL Agent stopped cleanly");
        FIREWALL_LOG_INFO("════════════════════════════════════════════════════════");

        std::cout << "[SHUTDOWN] ✓ Firewall ACL Agent stopped cleanly" << std::endl;

    } catch (const std::exception& e) {
        FIREWALL_LOG_CRASH("Fatal exception in main",
            "error", e.what());
        DUMP_STATE_ON_ERROR("fatal_exception");

        std::cerr << "[FATAL] Exception: " << e.what() << std::endl;
        return 1;
    }

    return 0;
}
