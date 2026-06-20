// ============================================================================
// autonomy_reactor.cpp — DEBT-FIREWALL-DENY-SELECTIVE-001 (DAY 155)
// ============================================================================
#include "firewall/autonomy_reactor.hpp"
#include <cstdlib>
#include <iostream>

namespace mldefender::firewall {

    static int default_executor(const std::string& cmd) {
        // INTERINO (DAY190) — CWE-78 MITIGADA en la frontera de config, NO aquí:
        // el único fragmento de `cmd` derivado de input es <cidr>, validado por
        // is_valid_ip_cidr() en ConfigLoader::parse_autonomy (fail-fast throw) antes
        // de construir FirewallAutonomyReactor. CHAIN_NAME/COMMENT_* son constexpr.
        // Prueba: tests ParseAutonomyCidrInjection.{Semicolon,Newline,CommandSub} (verdes).
        // Silencia al analizador, NO al riesgo: el std::system sigue presente.
        // Eliminación definitiva (execv sin shell) = DEBT-AUTONOMY-REACTOR-SAFEEXEC-002, POST-FEDER.
        return std::system(cmd.c_str()); // nosemgrep: argus-shell-from-constructed-string
    }

FirewallAutonomyReactor::FirewallAutonomyReactor(
            std::vector<std::string> whitelist_cidrs,
            bool dry_run,
            IptablesExecutor executor)
        : dry_run_(dry_run)
        , executor_(executor ? std::move(executor) : default_executor)
        , whitelist_cidrs_(std::move(whitelist_cidrs))
{
    if (whitelist_cidrs_.empty()) {
        throw std::invalid_argument(
            "[FirewallAutonomyReactor] whitelist_cidrs vacío — "
            "operación rechazada. Especifique al menos un CIDR "
            "en firewall.json[\"autonomy\"][\"whitelist_cidrs\"]."
        );
    }
}

// ── run(): exec con soporte dry_run unificado ────────────────────────────────
int FirewallAutonomyReactor::run(const std::string& cmd) {
    if (dry_run_) {
        std::cerr << "[autonomy_reactor] DRY-RUN: " << cmd << "\n";
        return 0;
    }
    return exec(cmd);
}

void FirewallAutonomyReactor::set_mode(FirewallAutonomyMode new_mode) {
    const auto old_mode = mode_.exchange(new_mode, std::memory_order_acq_rel);
    if (old_mode == new_mode) return;

    std::cerr << "[autonomy_reactor] modo: "
              << autonomy_mode_str(old_mode) << " → "
              << autonomy_mode_str(new_mode) << "\n";

    switch (new_mode) {
        case FirewallAutonomyMode::AUTONOMOUS:
        case FirewallAutonomyMode::DEGRADED:
            if (!deny_active_.load()) apply_default_deny();
            break;
        case FirewallAutonomyMode::NORMAL:
            if (deny_active_.load()) lift_default_deny();
            break;
    }
}

void FirewallAutonomyReactor::apply_default_deny() {
    const std::string ch = CHAIN_NAME;
    const std::string cm = " -m comment --comment ";

    // ── 1. Limpiar cadena preexistente (idempotencia ante restart) ───────────
    // Estos comandos pueden fallar legítimamente si la cadena no existe — OK.
    run("iptables -D INPUT -j " + ch);
    run("iptables -F " + ch);
    run("iptables -X " + ch);

    // ── 2. Crear cadena fresca ───────────────────────────────────────────────
    if (run("iptables -N " + ch) != 0 && !dry_run_) {
        std::cerr << "[autonomy_reactor] ERROR: no se pudo crear cadena "
                  << ch << " — default-deny NO activado\n";
        return;
    }

    // ── 3. Loopback — siempre ACCEPT ─────────────────────────────────────────
    run("iptables -A " + ch + " -i lo -j ACCEPT"
        + cm + "\"" + COMMENT_LO + "\"");

    // ── 4. Conexiones establecidas / relacionadas ─────────────────────────────
    run("iptables -A " + ch
        + " -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT"
        + cm + "\"" + COMMENT_ESTABLISHED + "\"");

    // ── 5. Subredes permitidas (whitelist desde JSON) ─────────────────────────
    for (const auto& cidr : whitelist_cidrs_) {
        run("iptables -A " + ch + " -s " + cidr + " -j ACCEPT"
            + cm + "\"" + COMMENT_PERMIT + "\"");
    }

    // ── 6. DROP final — garantizado último por estructura de cadena ───────────
    run("iptables -A " + ch + " -j DROP"
        + cm + "\"" + COMMENT_DENY + "\"");

    // ── 7. Enganchar cadena en INPUT posición 1 ───────────────────────────────
    const int rc = run("iptables -I INPUT 1 -j " + ch);
    if (rc == 0 || dry_run_) {
        deny_active_.store(true);
        std::cerr << "[autonomy_reactor] WARN: default-deny ACTIVADO"
                     " (modo autónomo) — whitelist="
                  << whitelist_cidrs_.size() << " CIDRs\n";
    } else {
        std::cerr << "[autonomy_reactor] ERROR: no se pudo activar cadena"
                     " en INPUT — rollback\n";
        run("iptables -F " + ch);
        run("iptables -X " + ch);
    }
}

void FirewallAutonomyReactor::lift_default_deny() {
    const std::string ch = CHAIN_NAME;

    // Orden crítico: retirar salto primero, luego vaciar, luego eliminar.
    const int rc1 = run("iptables -D INPUT -j " + ch);
    const int rc2 = run("iptables -F " + ch);
    const int rc3 = run("iptables -X " + ch);

    if (rc1 != 0 && !dry_run_)
        std::cerr << "[autonomy_reactor] WARN: salto INPUT→" << ch
                  << " no encontrado (¿ya retirado?)\n";
    if ((rc2 != 0 || rc3 != 0) && !dry_run_)
        std::cerr << "[autonomy_reactor] WARN: limpieza parcial de cadena "
                  << ch << "\n";

    // Siempre marcamos deny_active_ = false — hemos hecho lo posible.
    deny_active_.store(false);
    std::cerr << "[autonomy_reactor] INFO: default-deny RETIRADO (modo normal)\n";
}

int FirewallAutonomyReactor::exec(const std::string& cmd) {
    return executor_(cmd);
}

} // namespace mldefender::firewall