// test_auto_isolate.cpp — DEBT-FIREWALL-DENY-SELECTIVE-001 (DAY 155)
// Tests del FirewallAutonomyReactor con cadena dedicada + whitelist configurable
#include "firewall/autonomy_reactor.hpp"
#include "test_firewall_stubs.hpp"
#include <cassert>
#include <algorithm>
#include <iostream>
#include <vector>
#include <string>
using namespace mldefender::firewall;

// ── Helpers ──────────────────────────────────────────────────────────────────



[[maybe_unused]] static bool has_cmd(const std::vector<std::string>& cmds, const std::string& fragment) {
    return std::any_of(cmds.begin(), cmds.end(),
        [&](const std::string& c){ return c.find(fragment) != std::string::npos; });
}

// Número de comandos esperados en apply con N CIDRs:
// 3 cleanup (D/F/X) + 1 N + 1 lo + 1 established + N permit + 1 DROP + 1 INPUT = N+8
static constexpr int apply_cmd_count(int n_cidrs) { return n_cidrs + 8; }
// Número de comandos en lift: D + F + X = 3
static constexpr int lift_cmd_count() { return 3; }

static const std::vector<std::string> TEST_CIDRS{"192.168.1.0/24"};
static const std::vector<std::string> MULTI_CIDRS{
    "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"
};

int main() {
    // ── T1: NORMAL → AUTONOMOUS activa cadena selectiva ──────────────────────
    {
        StubExecutor ex;
        FirewallAutonomyReactor reactor(TEST_CIDRS, false,
            [&ex](const std::string& c){ return ex(c); });
        assert(reactor.current_mode() == FirewallAutonomyMode::NORMAL);
        assert(!reactor.is_deny_active());

        reactor.set_mode(FirewallAutonomyMode::AUTONOMOUS);

        assert(reactor.current_mode() == FirewallAutonomyMode::AUTONOMOUS);
        assert(reactor.is_deny_active());
        assert((int)ex.cmds.size() == apply_cmd_count(1));
        assert(has_cmd(ex.cmds, "-N argus-autonomy"));
        assert(has_cmd(ex.cmds, "-I INPUT 1 -j argus-autonomy"));
        assert(has_cmd(ex.cmds, "-j DROP"));
        assert(has_cmd(ex.cmds, "argus-autonomy-deny"));
        std::cout << "T1 PASS: NORMAL→AUTONOMOUS activa cadena selectiva\n";
    }
    // ── T2: AUTONOMOUS → NORMAL retira cadena (D→F→X) ────────────────────────
    {
        StubExecutor ex;
        FirewallAutonomyReactor reactor(TEST_CIDRS, false,
            [&ex](const std::string& c){ return ex(c); });
        reactor.set_mode(FirewallAutonomyMode::AUTONOMOUS);
        ex.cmds.clear();

        reactor.set_mode(FirewallAutonomyMode::NORMAL);

        assert(reactor.current_mode() == FirewallAutonomyMode::NORMAL);
        assert(!reactor.is_deny_active());
        assert((int)ex.cmds.size() == lift_cmd_count());
        assert(has_cmd(ex.cmds, "-D INPUT -j argus-autonomy"));
        assert(has_cmd(ex.cmds, "-F argus-autonomy"));
        assert(has_cmd(ex.cmds, "-X argus-autonomy"));
        std::cout << "T2 PASS: AUTONOMOUS→NORMAL retira cadena (D→F→X)\n";
    }
    // ── T3: idempotencia — mismo modo no ejecuta nada ────────────────────────
    {
        StubExecutor ex;
        FirewallAutonomyReactor reactor(TEST_CIDRS, false,
            [&ex](const std::string& c){ return ex(c); });
        reactor.set_mode(FirewallAutonomyMode::NORMAL);
        assert(ex.cmds.empty());
        reactor.set_mode(FirewallAutonomyMode::NORMAL);
        assert(ex.cmds.empty());
        std::cout << "T3 PASS: idempotencia\n";
    }
    // ── T4: DEGRADED también activa cadena selectiva ──────────────────────────
    {
        StubExecutor ex;
        FirewallAutonomyReactor reactor(TEST_CIDRS, false,
            [&ex](const std::string& c){ return ex(c); });
        reactor.set_mode(FirewallAutonomyMode::DEGRADED);
        assert(reactor.is_deny_active());
        assert(has_cmd(ex.cmds, "-I INPUT 1 -j argus-autonomy"));
        std::cout << "T4 PASS: DEGRADED activa cadena selectiva\n";
    }
    // ── T5: dry_run no llama executor pero marca deny_active ─────────────────
    {
        StubExecutor ex;
        FirewallAutonomyReactor reactor(TEST_CIDRS, true,
            [&ex](const std::string& c){ return ex(c); });
        reactor.set_mode(FirewallAutonomyMode::AUTONOMOUS);
        assert(reactor.is_deny_active());
        assert(ex.cmds.empty()); // dry_run no llama al executor
        std::cout << "T5 PASS: dry_run no ejecuta iptables\n";
    }
    // ── T6: AUTONOMOUS → DEGRADED no duplica deny ────────────────────────────
    {
        StubExecutor ex;
        FirewallAutonomyReactor reactor(TEST_CIDRS, false,
            [&ex](const std::string& c){ return ex(c); });
        reactor.set_mode(FirewallAutonomyMode::AUTONOMOUS);
        [[maybe_unused]] const auto cmds_after_autonomous = ex.cmds.size();
        reactor.set_mode(FirewallAutonomyMode::DEGRADED); // deny ya activo
        assert(ex.cmds.size() == cmds_after_autonomous); // sin comandos adicionales
        if (!reactor.is_deny_active()) { std::cerr << "T6 FAIL\n"; return 1; }
        std::cout << "T6 PASS: AUTONOMOUS→DEGRADED no duplica deny\n";
    }
    // ── T7: orden garantizado — lo→established→CIDRs→DROP→INPUT ─────────────
    {
        StubExecutor ex;
        FirewallAutonomyReactor reactor(TEST_CIDRS, false,
            [&ex](const std::string& c){ return ex(c); });
        reactor.set_mode(FirewallAutonomyMode::AUTONOMOUS);

        // Encontrar índices de los comandos clave (ignorar los 3 cleanup iniciales)
        auto idx = [&](const std::string& frag) -> int {
            for (int i = 0; i < (int)ex.cmds.size(); ++i)
                if (ex.cmds[i].find(frag) != std::string::npos) return i;
            return -1;
        };
        [[maybe_unused]] const int i_N           = idx("-N argus-autonomy");
        [[maybe_unused]] const int i_lo          = idx("argus-autonomy-lo");
        [[maybe_unused]] const int i_established = idx("argus-autonomy-established");
        [[maybe_unused]] const int i_permit      = idx("argus-autonomy-permit");
        [[maybe_unused]] const int i_drop        = idx("argus-autonomy-deny");
        [[maybe_unused]] const int i_input       = idx("-I INPUT 1");

        assert(i_N != -1 && i_lo != -1 && i_established != -1);
        assert(i_permit != -1 && i_drop != -1 && i_input != -1);
        assert(i_N < i_lo);
        assert(i_lo < i_established);
        assert(i_established < i_permit);
        assert(i_permit < i_drop);
        assert(i_drop < i_input);
        std::cout << "T7 PASS: orden lo→established→CIDRs→DROP→INPUT garantizado\n";
    }
    // ── T8: CIDRs personalizados — cada uno genera regla ACCEPT ──────────────
    {
        StubExecutor ex;
        FirewallAutonomyReactor reactor(MULTI_CIDRS, false,
            [&ex](const std::string& c){ return ex(c); });
        reactor.set_mode(FirewallAutonomyMode::AUTONOMOUS);

        assert((int)ex.cmds.size() == apply_cmd_count(3));
        assert(has_cmd(ex.cmds, "10.0.0.0/8"));
        assert(has_cmd(ex.cmds, "172.16.0.0/12"));
        assert(has_cmd(ex.cmds, "192.168.0.0/16"));
        assert(reactor.whitelist_cidrs().size() == 3);
        std::cout << "T8 PASS: 3 CIDRs personalizados generan 3 reglas ACCEPT\n";
    }
    // ── T9: constructor con CIDRs vacíos lanza std::invalid_argument ─────────
    {
        [[maybe_unused]] bool threw = false;
        try {
            FirewallAutonomyReactor reactor({}, false, nullptr);
        } catch (const std::invalid_argument&) {
            threw = true;
        }
        assert(threw);
        std::cout << "T9 PASS: constructor con whitelist vacía lanza invalid_argument\n";
    }
    // ── T10: lift emite D→F→X en ese orden exacto ────────────────────────────
    {
        StubExecutor ex;
        FirewallAutonomyReactor reactor(TEST_CIDRS, false,
            [&ex](const std::string& c){ return ex(c); });
        reactor.set_mode(FirewallAutonomyMode::AUTONOMOUS);
        ex.cmds.clear();
        reactor.set_mode(FirewallAutonomyMode::NORMAL);

        assert(ex.cmds.size() == 3);
        assert(ex.cmds[0].find("-D INPUT") != std::string::npos);
        assert(ex.cmds[1].find("-F argus-autonomy") != std::string::npos);
        assert(ex.cmds[2].find("-X argus-autonomy") != std::string::npos);
        std::cout << "T10 PASS: lift emite D→F→X en orden correcto\n";
    }
    // ── T11: apply idempotente — cleanup previo antes de recrear ─────────────
    {
        StubExecutor ex;
        FirewallAutonomyReactor reactor(TEST_CIDRS, false,
            [&ex](const std::string& c){ return ex(c); });
        reactor.set_mode(FirewallAutonomyMode::AUTONOMOUS);
        // Simular vuelta a NORMAL y de nuevo a AUTONOMOUS
        reactor.set_mode(FirewallAutonomyMode::NORMAL);
        ex.cmds.clear();
        reactor.set_mode(FirewallAutonomyMode::AUTONOMOUS);

        // El segundo apply debe comenzar con cleanup D/F/X
        assert(ex.cmds.size() >= 3);
        assert(ex.cmds[0].find("-D INPUT -j argus-autonomy") != std::string::npos);
        assert(ex.cmds[1].find("-F argus-autonomy") != std::string::npos);
        assert(ex.cmds[2].find("-X argus-autonomy") != std::string::npos);
        std::cout << "T11 PASS: apply idempotente — cleanup antes de recrear\n";
    }
    // ── T12: loopback protegido — siempre primera regla ACCEPT ───────────────
    {
        StubExecutor ex;
        FirewallAutonomyReactor reactor(TEST_CIDRS, false,
            [&ex](const std::string& c){ return ex(c); });
        reactor.set_mode(FirewallAutonomyMode::AUTONOMOUS);

        assert(has_cmd(ex.cmds, "-i lo"));
        assert(has_cmd(ex.cmds, "argus-autonomy-lo"));
        // lo debe aparecer antes que el DROP
        [[maybe_unused]] auto lo_it  = std::find_if(ex.cmds.begin(), ex.cmds.end(),
            [](const std::string& c){ return c.find("-i lo") != std::string::npos; });
        [[maybe_unused]] auto drp_it = std::find_if(ex.cmds.begin(), ex.cmds.end(),
            [](const std::string& c){ return c.find("argus-autonomy-deny") != std::string::npos
                                          && c.find("-j DROP") != std::string::npos; });
        assert(lo_it != ex.cmds.end() && drp_it != ex.cmds.end());
        assert(lo_it < drp_it);
        std::cout << "T12 PASS: loopback protegido — ACCEPT antes que DROP\n";
    }

    std::cout << "=== test_auto_isolate: 12/12 PASSED ===\n";
    return 0;
}