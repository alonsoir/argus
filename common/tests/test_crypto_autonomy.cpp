// common/tests/test_crypto_autonomy.cpp
// ============================================================================
// Tests CryptoAutonomyStateMachine — sin Vault, sin red, sin etcd.
// Solo eventos sintéticos y ManualClock.
// ============================================================================

#include "../crypto_autonomy.h"
#include <cassert>
#include <iostream>
#include <thread>
#include <vector>
#include <atomic>

using namespace ml_defender;

// ── Helpers ──────────────────────────────────────────────────────────────────

static int g_passed = 0;
static int g_failed = 0;

#define ASSERT_EQ(a, b, msg)                                              \
    do {                                                                  \
        if ((a) == (b)) {                                                 \
            std::cout << "  ✅ PASS: " << msg << "\n";                   \
            ++g_passed;                                                   \
        } else {                                                          \
            std::cout << "  ❌ FAIL: " << msg << "\n";                   \
            ++g_failed;                                                   \
        }                                                                 \
    } while(0)

#define ASSERT_TRUE(expr, msg)  ASSERT_EQ((expr), true,  msg)
#define ASSERT_FALSE(expr, msg) ASSERT_EQ((expr), false, msg)

// ── TEST 1: Estado inicial ────────────────────────────────────────────────────

void test_initial_state() {
    std::cout << "\n── TEST 1: estado inicial ──\n";
    CryptoAutonomy sm{"etcd-server"};

    ASSERT_EQ(sm.current_mode(), OperationalMode::NORMAL,
        "estado inicial es NORMAL");
    ASSERT_TRUE(sm.can_operate(),
        "can_operate() en NORMAL");
    ASSERT_EQ(std::string(sm.component_name()), std::string("etcd-server"),
        "component_name correcto");
    ASSERT_EQ(sm.degraded_reason(), std::string(""),
        "degraded_reason vacía en NORMAL");
}

// ── TEST 2: Transición NORMAL → AUTONOMOUS ────────────────────────────────────

void test_normal_to_autonomous() {
    std::cout << "\n── TEST 2: NORMAL → AUTONOMOUS ──\n";
    CryptoAutonomy sm{"sniffer"};

    sm.on_vault_unreachable();
    ASSERT_EQ(sm.current_mode(), OperationalMode::AUTONOMOUS,
        "on_vault_unreachable: NORMAL → AUTONOMOUS");
    ASSERT_TRUE(sm.can_operate(),
        "can_operate() en AUTONOMOUS");
}

// ── TEST 3: Ciclo completo NORMAL → AUTONOMOUS → RECONCILING → NORMAL ─────────

void test_full_cycle() {
    std::cout << "\n── TEST 3: ciclo completo ──\n";
    CryptoAutonomy sm{"ml-detector"};

    sm.on_vault_unreachable();
    ASSERT_EQ(sm.current_mode(), OperationalMode::AUTONOMOUS,
        "NORMAL → AUTONOMOUS");

    sm.on_vault_restored();
    ASSERT_EQ(sm.current_mode(), OperationalMode::RECONCILING,
        "AUTONOMOUS → RECONCILING");
    ASSERT_TRUE(sm.can_operate(),
        "can_operate() en RECONCILING");

    sm.on_reconciliation_ok();
    ASSERT_EQ(sm.current_mode(), OperationalMode::NORMAL,
        "RECONCILING → NORMAL");
}

// ── TEST 4: on_revocation → DEGRADED (terminal) ───────────────────────────────

void test_revocation_degraded() {
    std::cout << "\n── TEST 4: revocación → DEGRADED ──\n";
    CryptoAutonomy sm{"firewall-acl-agent"};

    sm.on_vault_unreachable();  // AUTONOMOUS
    sm.on_revocation();         // → DEGRADED

    ASSERT_EQ(sm.current_mode(), OperationalMode::DEGRADED,
        "on_revocation → DEGRADED");
    ASSERT_FALSE(sm.can_operate(),
        "can_operate() false en DEGRADED");
    ASSERT_EQ(sm.degraded_reason(), std::string("revocation"),
        "degraded_reason = revocation");
}

// ── TEST 5: on_tamper_detected → DEGRADED desde cualquier estado ──────────────

void test_tamper_degraded() {
    std::cout << "\n── TEST 5: tampering → DEGRADED ──\n";

    // Desde NORMAL
    {
        CryptoAutonomy sm{"rag-ingester"};
        sm.on_tamper_detected();
        ASSERT_EQ(sm.current_mode(), OperationalMode::DEGRADED,
            "tamper desde NORMAL → DEGRADED");
        ASSERT_EQ(sm.degraded_reason(), std::string("tamper_detected"),
            "degraded_reason = tamper_detected");
    }

    // Desde RECONCILING
    {
        CryptoAutonomy sm{"rag-security"};
        sm.on_vault_unreachable();
        sm.on_vault_restored();
        sm.on_tamper_detected();
        ASSERT_EQ(sm.current_mode(), OperationalMode::DEGRADED,
            "tamper desde RECONCILING → DEGRADED");
    }
}

// ── TEST 6: DEGRADED es terminal — ningún evento lo saca ─────────────────────

void test_degraded_is_terminal() {
    std::cout << "\n── TEST 6: DEGRADED es terminal ──\n";
    CryptoAutonomy sm{"etcd-server"};

    sm.on_revocation();
    ASSERT_EQ(sm.current_mode(), OperationalMode::DEGRADED,
        "DEGRADED tras revocación");

    sm.on_vault_unreachable();
    ASSERT_EQ(sm.current_mode(), OperationalMode::DEGRADED,
        "on_vault_unreachable no sale de DEGRADED");

    sm.on_vault_restored();
    ASSERT_EQ(sm.current_mode(), OperationalMode::DEGRADED,
        "on_vault_restored no sale de DEGRADED");

    sm.on_reconciliation_ok();
    ASSERT_EQ(sm.current_mode(), OperationalMode::DEGRADED,
        "on_reconciliation_ok no sale de DEGRADED");
}

// ── TEST 7: No-ops redundantes ────────────────────────────────────────────────

void test_noop_redundant_events() {
    std::cout << "\n── TEST 7: no-ops redundantes ──\n";
    CryptoAutonomy sm{"sniffer"};

    // on_vault_restored desde NORMAL → no-op
    sm.on_vault_restored();
    ASSERT_EQ(sm.current_mode(), OperationalMode::NORMAL,
        "on_vault_restored desde NORMAL: no-op");

    // on_reconciliation_ok desde NORMAL → no-op
    sm.on_reconciliation_ok();
    ASSERT_EQ(sm.current_mode(), OperationalMode::NORMAL,
        "on_reconciliation_ok desde NORMAL: no-op");

    // Doble on_vault_unreachable → sigue en AUTONOMOUS
    sm.on_vault_unreachable();
    sm.on_vault_unreachable();
    ASSERT_EQ(sm.current_mode(), OperationalMode::AUTONOMOUS,
        "doble on_vault_unreachable: sigue en AUTONOMOUS");
}

// ── TEST 8: TransitionCallback ────────────────────────────────────────────────

void test_transition_callback() {
    std::cout << "\n── TEST 8: TransitionCallback ──\n";

    std::vector<std::pair<OperationalMode, OperationalMode>> transitions;

    CryptoAutonomy sm{
        "ml-detector",
        [&](OperationalMode from, OperationalMode to) {
            transitions.push_back({from, to});
        }
    };

    sm.on_vault_unreachable();
    sm.on_vault_restored();
    sm.on_reconciliation_ok();

    ASSERT_EQ(transitions.size(), size_t(3),
        "3 callbacks invocados");
    ASSERT_EQ(transitions[0].first,  OperationalMode::NORMAL,
        "callback[0].from = NORMAL");
    ASSERT_EQ(transitions[0].second, OperationalMode::AUTONOMOUS,
        "callback[0].to = AUTONOMOUS");
    ASSERT_EQ(transitions[1].first,  OperationalMode::AUTONOMOUS,
        "callback[1].from = AUTONOMOUS");
    ASSERT_EQ(transitions[1].second, OperationalMode::RECONCILING,
        "callback[1].to = RECONCILING");
    ASSERT_EQ(transitions[2].first,  OperationalMode::RECONCILING,
        "callback[2].from = RECONCILING");
    ASSERT_EQ(transitions[2].second, OperationalMode::NORMAL,
        "callback[2].to = NORMAL");
}

// ── TEST 9: ManualClock — time_in_current_mode ────────────────────────────────

void test_manual_clock() {
    std::cout << "\n── TEST 9: ManualClock ──\n";
    ManualClock::reset();

    CryptoAutonomyMT sm{"etcd-server"};

    ManualClock::advance(std::chrono::seconds(10));
    auto t = sm.time_in_current_mode();

    ASSERT_TRUE(t >= std::chrono::seconds(10),
        "time_in_current_mode >= 10s tras advance");

    sm.on_vault_unreachable();
    ManualClock::advance(std::chrono::seconds(5));
    auto t2 = sm.time_in_current_mode();

    ASSERT_TRUE(t2 >= std::chrono::seconds(5),
        "time_in_current_mode reinicia tras transición");
    ASSERT_TRUE(t2 < std::chrono::seconds(10),
        "time_in_current_mode < tiempo total (reiniciado)");
}

// ── TEST 10: Thread-safety — lecturas concurrentes ────────────────────────────

void test_thread_safety() {
    std::cout << "\n── TEST 10: thread-safety ──\n";

    CryptoAutonomy sm{"sniffer"};
    std::atomic<int> read_count{0};
    constexpr int N_READERS = 8;
    constexpr int N_OPS     = 10000;

    // Escritor: cicla estados
    std::thread writer([&]{
        for (int i = 0; i < N_OPS; ++i) {
            sm.on_vault_unreachable();
            sm.on_vault_restored();
            sm.on_reconciliation_ok();
        }
    });

    // Lectores: current_mode() y can_operate() sin lock
    std::vector<std::thread> readers;
    for (int r = 0; r < N_READERS; ++r) {
        readers.emplace_back([&]{
            for (int i = 0; i < N_OPS; ++i) {
                auto m = sm.current_mode();
                (void)m;
                auto c = sm.can_operate();
                (void)c;
                ++read_count;
            }
        });
    }

    writer.join();
    for (auto& t : readers) t.join();

    ASSERT_EQ(read_count.load(), N_READERS * N_OPS,
        "todas las lecturas completadas sin crash");
    // Estado final debe ser NORMAL (ciclo completo en el writer)
    ASSERT_EQ(sm.current_mode(), OperationalMode::NORMAL,
        "estado final NORMAL tras ciclo completo");
}

// ── TEST 11: operational_mode_str ────────────────────────────────────────────

void test_mode_str() {
    std::cout << "\n── TEST 11: operational_mode_str ──\n";
    ASSERT_EQ(std::string(operational_mode_str(OperationalMode::NORMAL)),
        std::string("NORMAL"), "str NORMAL");
    ASSERT_EQ(std::string(operational_mode_str(OperationalMode::AUTONOMOUS)),
        std::string("AUTONOMOUS"), "str AUTONOMOUS");
    ASSERT_EQ(std::string(operational_mode_str(OperationalMode::RECONCILING)),
        std::string("RECONCILING"), "str RECONCILING");
    ASSERT_EQ(std::string(operational_mode_str(OperationalMode::DEGRADED)),
        std::string("DEGRADED"), "str DEGRADED");
}

// ── main ──────────────────────────────────────────────────────────────────────

int main() {
    std::cout << "╔════════════════════════════════════════════════════╗\n";
    std::cout << "║  CryptoAutonomyStateMachine — DAY 152 Tests       ║\n";
    std::cout << "╚════════════════════════════════════════════════════╝\n";

    test_initial_state();
    test_normal_to_autonomous();
    test_full_cycle();
    test_revocation_degraded();
    test_tamper_degraded();
    test_degraded_is_terminal();
    test_noop_redundant_events();
    test_transition_callback();
    test_manual_clock();
    test_thread_safety();
    test_mode_str();

    std::cout << "\n═══════════════════════════════════════════════════\n";
    std::cout << "Results: " << g_passed << "/" << (g_passed + g_failed)
              << " tests passed\n";
    std::cout << "═══════════════════════════════════════════════════\n";

    if (g_failed == 0) {
        std::cout << "🎉 ALL TESTS PASSED!\n";
        return 0;
    } else {
        std::cout << "❌ " << g_failed << " test(s) FAILED\n";
        return 1;
    }
}