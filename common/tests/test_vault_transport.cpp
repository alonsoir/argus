// ============================================================================
// test_vault_transport.cpp — Tests IVaultTransport (ADR-045 DAY 153)
// Sin red, sin Vault. Solo stubs y nulls.
// ============================================================================
#include "../vault_transport.h"
#include <cassert>
#include <iostream>

using namespace ml_defender;

static int g_passed = 0;
static int g_failed = 0;

#define ASSERT_EQ(a, b, msg) \
    do { if ((a)==(b)) { std::cout<<"  ✅ PASS: "<<msg<<"\n"; ++g_passed; } \
         else { std::cout<<"  ❌ FAIL: "<<msg<<"\n"; ++g_failed; } } while(0)
#define ASSERT_TRUE(e,m)  ASSERT_EQ((e), true,  m)
#define ASSERT_FALSE(e,m) ASSERT_EQ((e), false, m)

VaultClientConfig make_config(const std::string& family = "A") {
    VaultClientConfig cfg;
    cfg.component_name  = "test-component";
    cfg.component_index = 0;
    cfg.family          = family;
    cfg.env             = "dev";
    cfg.timeout_ms      = 100;  // timeout rápido para tests
    return cfg;
}

// TEST 1: NullVaultTransport siempre retorna nullopt
void test_null_transport() {
    std::cout << "\n── TEST 1: NullVaultTransport ──\n";
    NullVaultTransport t;
    auto cfg = make_config();
    ASSERT_FALSE(t.fetch_seed(cfg).has_value(),
        "NullVaultTransport retorna nullopt");
}

// TEST 2: StubVaultTransport retorna seed configurado
void test_stub_transport_with_seed() {
    std::cout << "\n── TEST 2: StubVaultTransport con seed ──\n";
    const std::string seed(64, 'a');  // 32 bytes hex
    StubVaultTransport t{seed};
    auto cfg = make_config();
    auto result = t.fetch_seed(cfg);
    ASSERT_TRUE(result.has_value(),
        "StubVaultTransport retorna valor");
    ASSERT_EQ(result.value(), seed,
        "StubVaultTransport retorna seed exacto");
}

// TEST 3: StubVaultTransport set_unavailable → nullopt
void test_stub_transport_unavailable() {
    std::cout << "\n── TEST 3: StubVaultTransport unavailable ──\n";
    StubVaultTransport t{"some_seed"};
    t.set_unavailable();
    auto cfg = make_config();
    auto result = t.fetch_seed(cfg);
    ASSERT_FALSE(result.has_value(),
        "StubVaultTransport unavailable retorna nullopt");
}

// TEST 4: StubVaultTransport set_seed actualiza valor
void test_stub_transport_set_seed() {
    std::cout << "\n── TEST 4: StubVaultTransport set_seed ──\n";
    StubVaultTransport t{"seed_v1"};
    auto cfg = make_config();
    ASSERT_EQ(t.fetch_seed(cfg).value(), std::string("seed_v1"),
        "seed inicial correcto");
    t.set_seed("seed_v2");
    ASSERT_EQ(t.fetch_seed(cfg).value(), std::string("seed_v2"),
        "seed actualizado correcto");
}

// TEST 5: HttpVaultTransport con Vault KO retorna nullopt (timeout rápido)
void test_http_transport_vault_ko() {
    std::cout << "\n── TEST 5: HttpVaultTransport Vault KO ──\n";
    HttpVaultTransport t;
    VaultClientConfig cfg = make_config();
    cfg.vault_addr     = "http://127.0.0.1:19999";  // puerto que no existe
    cfg.timeout_ms     = 100;                         // timeout 100ms
    cfg.component_index = 0;                          // sin jitter
    auto result = t.fetch_seed(cfg);
    ASSERT_FALSE(result.has_value(),
        "HttpVaultTransport Vault KO retorna nullopt");
}

int main() {
    std::cout << "╔════════════════════════════════════════════════════╗\n";
    std::cout << "║  IVaultTransport — DAY 153 Tests                  ║\n";
    std::cout << "╚════════════════════════════════════════════════════╝\n";

    test_null_transport();
    test_stub_transport_with_seed();
    test_stub_transport_unavailable();
    test_stub_transport_set_seed();
    test_http_transport_vault_ko();

    std::cout << "\n═══════════════════════════════════════════════════\n";
    std::cout << "Results: " << g_passed << "/" << (g_passed + g_failed)
              << " tests passed\n";
    std::cout << "═══════════════════════════════════════════════════\n";
    if (g_failed == 0) {
        std::cout << "🎉 ALL TESTS PASSED!\n";
        return 0;
    }
    std::cout << "❌ " << g_failed << " test(s) FAILED\n";
    return 1;
}