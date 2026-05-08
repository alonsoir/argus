// argus-network-isolate — punto de entrada
// ADR-042 Incident Response Protocol — DAY 142
// Authors: Alonso Isidoro Roman + Claude (Anthropic)

#include "isolate.hpp"
#include <iostream>
#include <spdlog/sinks/stdout_color_sinks.h>
#include <spdlog/sinks/basic_file_sink.h>

static void setup_logging(const std::string& log_path, bool verbose) {
    try {
        auto console = std::make_shared<spdlog::sinks::stdout_color_sink_mt>();
        console->set_level(verbose ? spdlog::level::debug : spdlog::level::info);
        std::vector<spdlog::sink_ptr> sinks{console};
        try {
            auto file = std::make_shared<spdlog::sinks::basic_file_sink_mt>(log_path, false);
            file->set_level(spdlog::level::debug);
            sinks.push_back(file);
        } catch (...) {}
        auto logger = std::make_shared<spdlog::logger>("argus-isolate", sinks.begin(), sinks.end());
        logger->set_level(spdlog::level::debug);
        spdlog::set_default_logger(logger);
        spdlog::set_pattern("[%Y-%m-%d %H:%M:%S.%e] [%l] %v");
    } catch (...) {}
}

static void print_usage() {
    std::cout <<
        "argus-network-isolate -- ADR-042 Incident Response Protocol\n"
        "Via Appia Quality -- aRGus NDR\n\n"
        "USAGE:\n"
        "  isolate  --interface <iface> [--dry-run] [--config <path>] [--verbose]\n"
        "  rollback [--backup <path>]   [--config <path>] [--verbose]\n"
        "  status   [--config <path>]   [--verbose]\n\n"
        "EXIT CODES: 0=OK 1=error 2=validation_failed 3=snapshot_failed 4=apply_failed\n";
}

int main(int argc, char* argv[]) {
    if (argc < 2) { print_usage(); return 1; }

    std::string command     = argv[1];
    std::string interface_name;
    std::string backup_path;
    std::string config_path = "/etc/ml-defender/firewall-acl-agent/isolate.json";
    bool        dry_run     = false;
    bool        verbose     = false;

    for (int i = 2; i < argc; ++i) {
        std::string arg = argv[i];
        if      (arg == "--interface" && i+1 < argc) interface_name = argv[++i];
        else if (arg == "--backup"    && i+1 < argc) backup_path    = argv[++i];
        else if (arg == "--config"    && i+1 < argc) config_path    = argv[++i];
        else if (arg == "--dry-run")                 dry_run        = true;
        else if (arg == "--verbose")                 verbose        = true;
    }

    argus::irp::IsolateConfig cfg;
    try {
        cfg = argus::irp::IsolateConfig::from_file(config_path);
    } catch (const std::exception& e) {
        std::cerr << "[argus-isolate] WARN: config no encontrado (" << config_path
                  << "): " << e.what() << " -- usando defaults\n";
    }

    setup_logging(cfg.log_path, verbose);

    spdlog::info("[argus-isolate] ===========================================");
    spdlog::info("[argus-isolate] aRGus NDR -- Incident Response Protocol");
    spdlog::info("[argus-isolate] ADR-042 -- DAY 142");
    spdlog::info("[argus-isolate] comando={} dry_run={}", command, dry_run);
    spdlog::info("[argus-isolate] ===========================================");

    argus::irp::NetworkIsolator isolator(cfg);

    if (command == "status") {
        isolator.status();
        return 0;
    }

    if (command == "rollback") {
        auto r = isolator.rollback(backup_path);
        if (r == argus::irp::IsolateResult::ROLLBACK_OK) {
            spdlog::info("[argus-isolate] rollback completado");
            return 0;
        }
        spdlog::error("[argus-isolate] rollback fallido");
        return 1;
    }

    if (command == "isolate") {
        if (interface_name.empty()) {
            spdlog::error("[argus-isolate] --interface es obligatorio");
            print_usage();
            return 1;
        }

        std::string backup_out, rules_out;

        auto r1 = isolator.snapshot(backup_out);
        if (r1 != argus::irp::IsolateResult::OK) {
            spdlog::error("[argus-isolate] ABORTANDO en PASO 1");
            return 3;
        }

        auto r2 = isolator.generate_rules(interface_name, rules_out);
        if (r2 != argus::irp::IsolateResult::OK) {
            spdlog::error("[argus-isolate] ABORTANDO en PASO 2");
            return 1;
        }

        auto r3 = isolator.validate_dry_run(rules_out);
        if (r3 != argus::irp::IsolateResult::DRY_RUN_OK) {
            spdlog::error("[argus-isolate] ABORTANDO en PASO 3 (nft -c fallido)");
            return 2;
        }

        if (dry_run) {
            spdlog::info("[argus-isolate] DRY-RUN completado (pasos 1-3 OK)");
            spdlog::info("[argus-isolate]   backup: {}", backup_out);
            spdlog::info("[argus-isolate]   reglas: {}", rules_out);
            return 0;
        }

        auto r4 = isolator.apply(rules_out);
        if (r4 != argus::irp::IsolateResult::OK) {
            spdlog::error("[argus-isolate] PASO 4 FALLIDO -- activando fallback");
            isolator.emergency_link_down(interface_name);
            return 4;
        }

        isolator.arm_rollback_timer(backup_out);
        spdlog::info("[argus-isolate] AISLAMIENTO ACTIVO en {}", interface_name);
        return 0;
    }

    spdlog::error("[argus-isolate] comando desconocido: {}", command);
    print_usage();
    return 1;
}
