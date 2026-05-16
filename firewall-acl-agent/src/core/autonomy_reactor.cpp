// ============================================================================
// autonomy_reactor.cpp — DEBT-FIREWALL-AUTONOMY-MODE-001 (DAY 154)
// ============================================================================
#include "firewall/autonomy_reactor.hpp"
#include <cstdlib>
#include <iostream>

namespace mldefender::firewall {

static int default_executor(const std::string& cmd) {
    return std::system(cmd.c_str());
}

FirewallAutonomyReactor::FirewallAutonomyReactor(bool dry_run,
                                                   IptablesExecutor executor)
    : dry_run_(dry_run)
    , executor_(executor ? std::move(executor) : default_executor)
{}

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
    const std::string cmd =
        "iptables -I INPUT 1 -m comment --comment \""
        + std::string(RULE_COMMENT) + "\" -j DROP";
    if (dry_run_) {
        std::cerr << "[autonomy_reactor] DRY-RUN: " << cmd << "\n";
        deny_active_.store(true);
        return;
    }
    if (exec(cmd) == 0) {
        deny_active_.store(true);
        std::cerr << "[autonomy_reactor] WARN: default-deny ACTIVADO"
                     " (modo autónomo)\n";
    } else {
        std::cerr << "[autonomy_reactor] ERROR: no se pudo aplicar"
                     " default-deny\n";
    }
}

void FirewallAutonomyReactor::lift_default_deny() {
    const std::string cmd =
        "iptables -D INPUT -m comment --comment \""
        + std::string(RULE_COMMENT) + "\" -j DROP";
    if (dry_run_) {
        std::cerr << "[autonomy_reactor] DRY-RUN lift: " << cmd << "\n";
        deny_active_.store(false);
        return;
    }
    if (exec(cmd) == 0) {
        deny_active_.store(false);
        std::cerr << "[autonomy_reactor] INFO: default-deny RETIRADO"
                     " (modo normal)\n";
    } else {
        std::cerr << "[autonomy_reactor] ERROR: no se pudo retirar"
                     " default-deny\n";
    }
}

int FirewallAutonomyReactor::exec(const std::string& cmd) {
    return executor_(cmd);
}

} // namespace mldefender::firewall
