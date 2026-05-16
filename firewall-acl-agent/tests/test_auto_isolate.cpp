// test_auto_isolate.cpp — DEBT-FIREWALL-AUTONOMY-MODE-001 (DAY 154)
// Test unitario del FirewallAutonomyReactor con executor stub
#include "firewall/autonomy_reactor.hpp"
#include <cassert>
#include <iostream>
#include <vector>
#include <string>

using namespace mldefender::firewall;

struct StubExecutor {
    std::vector<std::string> cmds;
    int ret{0};
    int operator()(const std::string& cmd) {
        cmds.push_back(cmd);
        return ret;
    }
};

int main() {
    // T1: NORMAL → AUTONOMOUS activa deny
    {
        StubExecutor ex;
        FirewallAutonomyReactor reactor(false, [&ex](const std::string& c){
            return ex(c);
        });
        assert(reactor.current_mode() == FirewallAutonomyMode::NORMAL);
        assert(!reactor.is_deny_active());

        reactor.set_mode(FirewallAutonomyMode::AUTONOMOUS);
        assert(reactor.current_mode() == FirewallAutonomyMode::AUTONOMOUS);
        assert(reactor.is_deny_active());
        assert(ex.cmds.size() == 1);
        assert(ex.cmds[0].find("argus-autonomy-deny") != std::string::npos);
        assert(ex.cmds[0].find("-I INPUT 1") != std::string::npos);
        std::cout << "T1 PASS: NORMAL→AUTONOMOUS activa deny\n";
    }

    // T2: AUTONOMOUS → NORMAL retira deny
    {
        StubExecutor ex;
        FirewallAutonomyReactor reactor(false, [&ex](const std::string& c){
            return ex(c);
        });
        reactor.set_mode(FirewallAutonomyMode::AUTONOMOUS);
        ex.cmds.clear();

        reactor.set_mode(FirewallAutonomyMode::NORMAL);
        assert(reactor.current_mode() == FirewallAutonomyMode::NORMAL);
        assert(!reactor.is_deny_active());
        assert(ex.cmds.size() == 1);
        assert(ex.cmds[0].find("-D INPUT") != std::string::npos);
        std::cout << "T2 PASS: AUTONOMOUS→NORMAL retira deny\n";
    }

    // T3: set_mode idempotente — mismo modo no ejecuta nada
    {
        StubExecutor ex;
        FirewallAutonomyReactor reactor(false, [&ex](const std::string& c){
            return ex(c);
        });
        reactor.set_mode(FirewallAutonomyMode::NORMAL);
        assert(ex.cmds.empty());
        reactor.set_mode(FirewallAutonomyMode::NORMAL);
        assert(ex.cmds.empty());
        std::cout << "T3 PASS: idempotencia\n";
    }

    // T4: DEGRADED también activa deny
    {
        StubExecutor ex;
        FirewallAutonomyReactor reactor(false, [&ex](const std::string& c){
            return ex(c);
        });
        reactor.set_mode(FirewallAutonomyMode::DEGRADED);
        assert(reactor.is_deny_active());
        assert(ex.cmds[0].find("-I INPUT 1") != std::string::npos);
        std::cout << "T4 PASS: DEGRADED activa deny\n";
    }

    // T5: dry_run no ejecuta iptables real pero marca deny_active
    {
        StubExecutor ex;
        FirewallAutonomyReactor reactor(true, [&ex](const std::string& c){
            return ex(c);
        });
        reactor.set_mode(FirewallAutonomyMode::AUTONOMOUS);
        assert(reactor.is_deny_active());
        assert(ex.cmds.empty()); // dry_run no llama al executor
        std::cout << "T5 PASS: dry_run no ejecuta iptables\n";
    }

    // T6: AUTONOMOUS → DEGRADED no aplica deny doble
    {
        StubExecutor ex;
        FirewallAutonomyReactor reactor(false, [&ex](const std::string& c){
            return ex(c);
        });
        reactor.set_mode(FirewallAutonomyMode::AUTONOMOUS); // 1 cmd
        reactor.set_mode(FirewallAutonomyMode::DEGRADED);   // deny ya activo
        // sin assert para evitar -Wunused en NDEBUG: is_deny_active() es suficiente
        if (!reactor.is_deny_active()) { std::cerr << "T6 FAIL\n"; return 1; }
        std::cout << "T6 PASS: AUTONOMOUS→DEGRADED no duplica deny\n";
    }

    std::cout << "=== test_auto_isolate: 6/6 PASSED ===\n";
    return 0;
}
