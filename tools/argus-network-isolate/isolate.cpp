// argus-network-isolate — implementacion
// ADR-042 Incident Response Protocol — DAY 142
// Authors: Alonso Isidoro Roman + Claude (Anthropic)

#include "isolate.hpp"
#include <fstream>
#include <sstream>
#include <chrono>
#include <cstdio>
#include <stdexcept>
#include <array>
#include <filesystem>
#include <sys/wait.h>

namespace fs = std::filesystem;
namespace argus::irp {

// ── IsolateConfig::from_file ──────────────────────────────────────────────
IsolateConfig IsolateConfig::from_file(const std::string& path) {
    std::ifstream f(path);
    if (!f.is_open())
        throw std::runtime_error("Cannot open config: " + path);
    nlohmann::json j = nlohmann::json::parse(f);
    IsolateConfig cfg;
    cfg.nft_path             = j.value("nft_path",             "/usr/sbin/nft");
    cfg.backup_dir           = j.value("backup_dir",           "/tmp");
    cfg.table_name           = j.value("table_name",           "argus_isolate");
    cfg.log_path             = j.value("log_path",             "/var/log/argus/network-isolate.log");
    cfg.forensic_log_path    = j.value("forensic_log_path",    "/var/log/argus/network-isolate-forensic.jsonl");
    cfg.rollback_timeout_sec = j.value("rollback_timeout_sec", 300);
    if (j.contains("whitelist_ips"))
        cfg.whitelist_ips = j["whitelist_ips"].get<std::vector<std::string>>();
    if (j.contains("whitelist_ports"))
        cfg.whitelist_ports = j["whitelist_ports"].get<std::vector<int>>();
    cfg.auto_isolate           = j.value("auto_isolate",           true);
    cfg.threat_score_threshold = j.value("threat_score_threshold", 0.95);
    if (j.contains("auto_isolate_event_types"))
        cfg.auto_isolate_event_types =
            j["auto_isolate_event_types"].get<std::vector<std::string>>();
    cfg.isolate_interface = j.value("isolate_interface", "eth0");
    return cfg;
}

// ── to_string ─────────────────────────────────────────────────────────────
std::string to_string(IsolateResult r) {
    switch (r) {
        case IsolateResult::OK:               return "OK";
        case IsolateResult::DRY_RUN_OK:       return "DRY_RUN_OK";
        case IsolateResult::VALIDATION_FAILED:return "VALIDATION_FAILED";
        case IsolateResult::SNAPSHOT_FAILED:  return "SNAPSHOT_FAILED";
        case IsolateResult::APPLY_FAILED:     return "APPLY_FAILED";
        case IsolateResult::ROLLBACK_OK:      return "ROLLBACK_OK";
        case IsolateResult::ROLLBACK_FAILED:  return "ROLLBACK_FAILED";
        case IsolateResult::ALREADY_ISOLATED: return "ALREADY_ISOLATED";
        case IsolateResult::NOT_ISOLATED:     return "NOT_ISOLATED";
        default:                              return "ERROR";
    }
}

// ── Constructor ───────────────────────────────────────────────────────────
NetworkIsolator::NetworkIsolator(const IsolateConfig& cfg) : cfg_(cfg) {
    try {
        fs::path log_dir = fs::path(cfg_.log_path).parent_path();
        if (!log_dir.empty()) fs::create_directories(log_dir);
    } catch (...) {}
    spdlog::info("[argus-isolate] NetworkIsolator inicializado");
    spdlog::info("[argus-isolate]   tabla:            {}", cfg_.table_name);
    spdlog::info("[argus-isolate]   nft:              {}", cfg_.nft_path);
    spdlog::info("[argus-isolate]   rollback_timeout: {}s", cfg_.rollback_timeout_sec);
}

// ── run_cmd ───────────────────────────────────────────────────────────────
std::pair<int,std::string> NetworkIsolator::run_cmd(const std::string& cmd) {
    spdlog::debug("[argus-isolate] CMD: {}", cmd);
    std::string full_cmd = cmd + " 2>&1";
    std::array<char, 4096> buf{};
    std::string output;
    FILE* pipe = popen(full_cmd.c_str(), "r");
    if (!pipe) return {-1, "popen failed"};
    while (fgets(buf.data(), buf.size(), pipe))
        output += buf.data();
    int rc = pclose(pipe);
    int exit_code = WIFEXITED(rc) ? WEXITSTATUS(rc) : -1;
    if (exit_code != 0)
        spdlog::warn("[argus-isolate] CMD exit={} out={}", exit_code, output);
    return {exit_code, output};
}

// ── log_forensic ──────────────────────────────────────────────────────────
void NetworkIsolator::log_forensic(const std::string& event,
                                   const nlohmann::json& details) {
    auto ts = std::chrono::duration_cast<std::chrono::seconds>(
        std::chrono::system_clock::now().time_since_epoch()).count();
    nlohmann::json entry;
    entry["ts"]      = ts;
    entry["event"]   = event;
    entry["details"] = details;
    // TODO DAY 143: Ed25519 de cada entrada (cadena forense ADR-042)
    std::ofstream f(cfg_.forensic_log_path, std::ios::app);
    if (f.is_open()) f << entry.dump() << "\n";
    spdlog::info("[argus-isolate] FORENSIC event={} details={}",
                 event, details.dump());
}

// ── build_nft_ruleset ─────────────────────────────────────────────────────
std::string NetworkIsolator::build_nft_ruleset(const std::string& interface) {
    std::ostringstream nft;
    nft << "# argus-network-isolate — tabla de aislamiento\n"
        << "# ADR-042 IRP — DAY 142\n"
        << "# NUNCA editar manualmente\n\n"
        << "table ip " << cfg_.table_name << " {\n\n"
        << "    chain ARGUS_INPUT {\n"
        << "        type filter hook input priority -100; policy drop;\n"
        << "        iifname \"lo\" accept\n"
        << "        ct state established,related accept\n";
    for (const auto& ip   : cfg_.whitelist_ips)
        nft << "        ip saddr " << ip << " accept\n";
    for (const int port   : cfg_.whitelist_ports)
        nft << "        tcp dport " << port << " accept\n";
    nft << "        iifname \"" << interface << "\" drop\n"
        << "    }\n\n"
        << "    chain ARGUS_OUTPUT {\n"
        << "        type filter hook output priority -100; policy drop;\n"
        << "        oifname \"lo\" accept\n"
        << "        ct state established,related accept\n";
    for (const auto& ip   : cfg_.whitelist_ips)
        nft << "        ip daddr " << ip << " accept\n";
    for (const int port   : cfg_.whitelist_ports)
        nft << "        tcp sport " << port << " accept\n";
    nft << "        oifname \"" << interface << "\" drop\n"
        << "    }\n}\n";
    return nft.str();
}

// ── PASO 1: snapshot ──────────────────────────────────────────────────────
IsolateResult NetworkIsolator::snapshot(std::string& backup_path_out) {
    spdlog::info("[argus-isolate] === PASO 1: snapshot del ruleset ===");
    auto ts = std::chrono::duration_cast<std::chrono::seconds>(
        std::chrono::system_clock::now().time_since_epoch()).count();
    backup_path_out = cfg_.backup_dir + "/argus-backup-" + std::to_string(ts) + ".nft";
    // Snapshot solo de argus_isolate — excluimos tablas iptables-managed (xt match incompatible)
    // Si la tabla no existe aun, backup queda vacio — rollback solo elimina tabla.
    run_cmd("sudo " + cfg_.nft_path + " list table ip " + cfg_.table_name +
            " > " + backup_path_out + " 2>/dev/null || true");
    int rc = 0;
    std::string out;
    // rc siempre 0 aqui — error ya manejado con || true
    (void)rc; (void)out;
    std::error_code ec;
    auto size = fs::file_size(backup_path_out, ec);
    // Backup vacio es OK en primera ejecucion — argus_isolate aun no existe
    if (ec) {
        spdlog::error("[argus-isolate] PASO 1 FAILED: no se puede leer backup {}", backup_path_out);
        return IsolateResult::SNAPSHOT_FAILED;
    }
    spdlog::info("[argus-isolate] PASO 1 OK: backup={} ({} bytes{})",
                 backup_path_out, size, size == 0 ? " — primera ejecucion" : "");
    log_forensic("snapshot_ok", {{"path", backup_path_out}, {"size_bytes", size}, {"first_run", size == 0}});
    return IsolateResult::OK;
}

// ── PASO 2: generate_rules ────────────────────────────────────────────────
IsolateResult NetworkIsolator::generate_rules(const std::string& interface,
                                              std::string& rules_path_out) {
    spdlog::info("[argus-isolate] === PASO 2: generando reglas (iface={}) ===", interface);
    auto ts = std::chrono::duration_cast<std::chrono::seconds>(
        std::chrono::system_clock::now().time_since_epoch()).count();
    rules_path_out = cfg_.backup_dir + "/argus-isolate-" + std::to_string(ts) + ".nft";
    std::ofstream f(rules_path_out);
    if (!f.is_open()) {
        spdlog::error("[argus-isolate] PASO 2 FAILED: no se puede escribir {}", rules_path_out);
        return IsolateResult::ERROR;
    }
    f << build_nft_ruleset(interface);
    f.close();
    spdlog::info("[argus-isolate] PASO 2 OK: reglas={}", rules_path_out);
    log_forensic("rules_generated", {
        {"path", rules_path_out}, {"interface", interface},
        {"whitelist_ips", cfg_.whitelist_ips},
        {"whitelist_ports", cfg_.whitelist_ports}
    });
    return IsolateResult::OK;
}

// ── PASO 3: validate_dry_run ──────────────────────────────────────────────
IsolateResult NetworkIsolator::validate_dry_run(const std::string& rules_path) {
    spdlog::info("[argus-isolate] === PASO 3: validacion en seco (nft -c) ===");
    auto [rc, out] = run_cmd("sudo " + cfg_.nft_path + " -c -f " + rules_path);
    if (rc != 0) {
        spdlog::error("[argus-isolate] PASO 3 FAILED (exit={}): {}", rc, out);
        log_forensic("dry_run_failed", {{"exit_code", rc}, {"output", out}});
        return IsolateResult::VALIDATION_FAILED;
    }
    spdlog::info("[argus-isolate] PASO 3 OK: reglas validas (nft -c exit=0)");
    log_forensic("dry_run_ok", {{"rules_path", rules_path}});
    return IsolateResult::DRY_RUN_OK;
}

// ── PASO 4: apply ─────────────────────────────────────────────────────────
IsolateResult NetworkIsolator::apply(const std::string& rules_path) {
    spdlog::info("[argus-isolate] === PASO 4: aplicando aislamiento atomico ===");
    spdlog::warn("[argus-isolate] ACCION IRREVERSIBLE SIN ROLLBACK — iniciando");
    auto [rc, out] = run_cmd("sudo " + cfg_.nft_path + " -f " + rules_path);
    if (rc != 0) {
        spdlog::error("[argus-isolate] PASO 4 FAILED (exit={}): {}", rc, out);
        log_forensic("apply_failed", {{"exit_code", rc}, {"output", out}});
        return IsolateResult::APPLY_FAILED;
    }
    spdlog::info("[argus-isolate] PASO 4 OK: aislamiento ACTIVO");
    log_forensic("apply_ok", {{"rules_path", rules_path}});
    return IsolateResult::OK;
}

// ── PASO 5: arm_rollback_timer ────────────────────────────────────────────
IsolateResult NetworkIsolator::arm_rollback_timer(const std::string& backup_path) {
    spdlog::info("[argus-isolate] === PASO 5: armando timer rollback ({}s) ===",
                 cfg_.rollback_timeout_sec);
    // systemd-run: timer de rollback automatico si nadie confirma el aislamiento
    // Limpiar timer anterior si existe (idempotente)
    run_cmd("sudo systemctl stop argus-rollback-timer.timer 2>/dev/null || true");
    run_cmd("sudo systemctl reset-failed argus-rollback-timer.timer 2>/dev/null || true");

    std::string timer_cmd =
        "sudo systemd-run --on-active=" +
        std::to_string(cfg_.rollback_timeout_sec) +
        "s --unit=argus-rollback-timer" +
        " /usr/local/bin/argus-network-isolate rollback --backup " +
        backup_path;

    auto [rc, out] = run_cmd(timer_cmd);
    if (rc != 0) {
        spdlog::warn("[argus-isolate] PASO 5 WARN: systemd-run fallido ({}): {}", rc, out);
        spdlog::warn("[argus-isolate]   rollback manual requerido: argus-network-isolate rollback --backup {}", backup_path);
        log_forensic("rollback_timer_failed", {
            {"timeout_sec", cfg_.rollback_timeout_sec},
            {"backup_path", backup_path},
            {"error", out}
        });
        // No es fatal — el aislamiento sigue activo, solo sin timer automatico
        return IsolateResult::OK;
    }

    spdlog::info("[argus-isolate] PASO 5 OK: timer rollback armado ({}s)", cfg_.rollback_timeout_sec);
    spdlog::info("[argus-isolate]   backup: {}", backup_path);
    spdlog::info("[argus-isolate]   unidad: argus-rollback-timer");
    log_forensic("rollback_timer_armed", {
        {"timeout_sec", cfg_.rollback_timeout_sec},
        {"backup_path", backup_path},
        {"systemd_unit", "argus-rollback-timer"}
    });
    return IsolateResult::OK;
}

// ── PASO 6: rollback ──────────────────────────────────────────────────────
IsolateResult NetworkIsolator::rollback(const std::string& backup_path) {
    spdlog::info("[argus-isolate] === PASO 6: rollback desde {} ===", backup_path);
    run_cmd("sudo " + cfg_.nft_path + " delete table ip " + cfg_.table_name + " 2>/dev/null || true");
    // Las tablas nat/filter de iptables-nft persisten solas — no restaurar.
    // Solo restauramos argus_isolate si el backup tiene contenido propio.
    if (!backup_path.empty() && fs::exists(backup_path)) {
        std::error_code ec;
        auto sz = fs::file_size(backup_path, ec);
        if (!ec && sz > 10) {
            auto [rc_r, out_r] = run_cmd("sudo " + cfg_.nft_path + " -f " + backup_path);
            if (rc_r != 0)
                spdlog::warn("[argus-isolate] PASO 6 WARN: restauracion backup (ignorada): {}", out_r);
        } else {
            spdlog::info("[argus-isolate] PASO 6: backup vacio — solo tabla eliminada");
        }
    }
    spdlog::info("[argus-isolate] PASO 6 OK: rollback completado");
    log_forensic("rollback_ok", {{"backup_path", backup_path}});
    return IsolateResult::ROLLBACK_OK;
}

// ── emergency_link_down ───────────────────────────────────────────────────
IsolateResult NetworkIsolator::emergency_link_down(const std::string& interface) {
    spdlog::error("[argus-isolate] FALLBACK EMERGENCIA: ip link set {} down", interface);
    log_forensic("emergency_link_down", {{"interface", interface}});
    auto [rc, out] = run_cmd("sudo ip link set " + interface + " down");
    return rc == 0 ? IsolateResult::OK : IsolateResult::ERROR;
}

// ── status ────────────────────────────────────────────────────────────────
bool NetworkIsolator::is_isolated() const {
    auto [rc, out] = const_cast<NetworkIsolator*>(this)->run_cmd(
        cfg_.nft_path + " list table ip " + cfg_.table_name + " 2>/dev/null");
    return rc == 0 && !out.empty();
}

IsolateResult NetworkIsolator::status() {
    bool isolated = is_isolated();
    spdlog::info("[argus-isolate] STATUS: {}",
        isolated ? "ISOLATED (tabla argus_isolate activa)" : "NORMAL (sin aislamiento)");
    return isolated ? IsolateResult::ALREADY_ISOLATED : IsolateResult::NOT_ISOLATED;
}

} // namespace argus::irp
