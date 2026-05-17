#pragma once
// ============================================================================
// autonomy_reactor.hpp — DEBT-FIREWALL-DENY-SELECTIVE-001 (DAY 155)
// ============================================================================
// CORRECCIÓN P0: la regla anterior (-I INPUT 1 -j DROP) bloqueaba loopback,
// sesiones activas y subredes clínicas. Ahora se usa cadena dedicada
// "argus-autonomy" con whitelist OBLIGATORIA desde firewall.json.
//
// Apply (AUTONOMOUS / DEGRADED):
//   iptables -N argus-autonomy
//   iptables -A argus-autonomy -i lo -j ACCEPT              [argus-autonomy-lo]
//   iptables -A argus-autonomy -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
//   iptables -A argus-autonomy -s <cidr> -j ACCEPT          [argus-autonomy-permit] × N
//   iptables -A argus-autonomy -j DROP                      [argus-autonomy-deny]
//   iptables -I INPUT 1 -j argus-autonomy
//
// Lift (NORMAL):
//   iptables -D INPUT -j argus-autonomy
//   iptables -F argus-autonomy
//   iptables -X argus-autonomy
//
// whitelist_cidrs viene SIEMPRE de firewall.json["autonomy"]["whitelist_cidrs"].
// Constructor lanza std::invalid_argument si el vector está vacío.
// ============================================================================
#include <atomic>
#include <functional>
#include <stdexcept>
#include <string>
#include <vector>

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

using IptablesExecutor = std::function<int(const std::string&)>;

class FirewallAutonomyReactor {
public:
    // ── Identificadores de cadena y comentarios ──────────────────────────────
    static constexpr const char* CHAIN_NAME          = "argus-autonomy";
    static constexpr const char* RULE_COMMENT        = "argus-autonomy-deny"; // compat DAY 154
    static constexpr const char* COMMENT_LO          = "argus-autonomy-lo";
    static constexpr const char* COMMENT_ESTABLISHED = "argus-autonomy-established";
    static constexpr const char* COMMENT_PERMIT      = "argus-autonomy-permit";
    static constexpr const char* COMMENT_DENY        = "argus-autonomy-deny";

    // whitelist_cidrs es OBLIGATORIO — vacío lanza std::invalid_argument.
    // Sin defaults: quien construye este objeto debe haber leído firewall.json.
    explicit FirewallAutonomyReactor(
        std::vector<std::string> whitelist_cidrs,
        bool             dry_run  = false,
        IptablesExecutor executor = nullptr
    );

    void set_mode(FirewallAutonomyMode mode);

    FirewallAutonomyMode current_mode() const noexcept {
        return mode_.load(std::memory_order_acquire);
    }
    bool is_deny_active() const noexcept { return deny_active_.load(); }

    const std::vector<std::string>& whitelist_cidrs() const noexcept {
        return whitelist_cidrs_;
    }

private:
    void apply_default_deny();
    void lift_default_deny();
    int  exec(const std::string& cmd);
    int  run(const std::string& cmd);

    std::atomic<FirewallAutonomyMode> mode_{FirewallAutonomyMode::NORMAL};
    std::atomic<bool>                 deny_active_{false};
    bool                              dry_run_;
    IptablesExecutor                  executor_;
    std::vector<std::string>          whitelist_cidrs_;
};

} // namespace mldefender::firewall