#pragma once
// ============================================================================
// autonomy_reactor.hpp — DEBT-FIREWALL-AUTONOMY-MODE-001 (ADR-045, DAY 154)
// ============================================================================
// Cuando el crypto-provider entra en AUTONOMOUS (Vault KO, cache válida),
// el firewall aplica default-deny para tráfico nuevo entrante.
// Cuando vuelve a NORMAL o RECONCILING, levanta la restricción.
//
// Señal actual: conectividad etcd (proxy del modo crypto).
// Señal futura: eventos ZMQ desde CryptoAutonomyStateMachine
//               (DEBT-AUTONOMY-ZMQ-EVENTS-001)
//
// Regla aplicada:
//   iptables -I INPUT 1 -m comment --comment "argus-autonomy-deny" -j DROP
// Regla retirada:
//   iptables -D INPUT -m comment --comment "argus-autonomy-deny" -j DROP
// ============================================================================
#include <string>
#include <functional>
#include <atomic>

namespace mldefender::firewall {

enum class FirewallAutonomyMode {
    NORMAL,      // Vault OK — reglas normales
    AUTONOMOUS,  // Vault KO, cache válida — default-deny nuevas conexiones
    DEGRADED,    // Tampering/revocación — fail-closed total
};

inline const char* autonomy_mode_str(FirewallAutonomyMode m) {
    switch (m) {
        case FirewallAutonomyMode::NORMAL:     return "NORMAL";
        case FirewallAutonomyMode::AUTONOMOUS: return "AUTONOMOUS";
        case FirewallAutonomyMode::DEGRADED:   return "DEGRADED";
    }
    return "UNKNOWN";
}

// Ejecutor de comandos iptables — inyectable para tests
using IptablesExecutor = std::function<int(const std::string&)>;

class FirewallAutonomyReactor {
public:
    static constexpr const char* RULE_COMMENT = "argus-autonomy-deny";

    explicit FirewallAutonomyReactor(bool dry_run = false,
                                      IptablesExecutor executor = nullptr);

    // Actualiza el modo. Si cambia, aplica o retira la regla default-deny.
    // Thread-safe (llamable desde health-check loop).
    void set_mode(FirewallAutonomyMode mode);

    FirewallAutonomyMode current_mode() const noexcept {
        return mode_.load(std::memory_order_acquire);
    }

    bool is_deny_active() const noexcept { return deny_active_.load(); }

private:
    void apply_default_deny();
    void lift_default_deny();
    int  exec(const std::string& cmd);

    std::atomic<FirewallAutonomyMode> mode_{FirewallAutonomyMode::NORMAL};
    std::atomic<bool>                 deny_active_{false};
    bool                              dry_run_;
    IptablesExecutor                  executor_;
};

} // namespace mldefender::firewall
