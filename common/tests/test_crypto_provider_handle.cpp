// ============================================================================
// test_crypto_provider_handle.cpp — RCU wrapper tests
// BACKLOG-CRYPTO-HOT-RELOAD-001 (DAY 163)
// TDH: RED → GREEN obligatorio
// ============================================================================

#include "crypto_provider_handle.hpp"
#include <atomic>
#include <cassert>
#include <chrono>
#include <iostream>
#include <string>
#include <thread>
#include <vector>

using namespace ml_defender;

// ── Contadores ────────────────────────────────────────────────────────────────
static int passed = 0;
static int failed = 0;

#define ASSERT_TRUE(expr) \
    do { \
        if (!(expr)) { \
            std::cerr << "❌ FAIL: " << __func__ << " — assertion failed: " #expr \
                      << " (" << __FILE__ << ":" << __LINE__ << ")\n"; \
            failed++; return; \
        } \
    } while (0)

#define ASSERT_EQ(a, b) ASSERT_TRUE((a) == (b))

// ── MockProvider — sin red, sin disco ────────────────────────────────────────
class MockProvider final : public ICryptoProvider {
public:
    explicit MockProvider(std::string name, bool healthy = true)
        : name_(std::move(name)), healthy_(healthy) {}

    CryptoMaterial get_material() override {
        get_count_.fetch_add(1, std::memory_order_relaxed);
        CryptoMaterial mat{};
        mat.pk[0]          = 0x42;
        mat.sk[0]          = 0x43;
        mat.fingerprint[0] = 0x44;
        mat.from_cache     = false;
        mat.key_version    = 1;
        return mat;
    }

    bool refresh()  override { return healthy_; }
    bool is_healthy() const override { return healthy_; }
    std::string component_name() const override { return name_; }

    int get_count() const { return get_count_.load(); }

private:
    std::string       name_;
    bool              healthy_;
    std::atomic<int>  get_count_{0};
};

// ── Tests ─────────────────────────────────────────────────────────────────────

static void test_null_provider_throws() {
    bool threw = false;
    try {
        CryptoProviderHandle h(nullptr);
    } catch (const std::invalid_argument&) {
        threw = true;
    }
    ASSERT_TRUE(threw);
    passed++;
    std::cout << "✅ PASS: test_null_provider_throws\n";
}

static void test_get_returns_nonnull() {
    CryptoProviderHandle h(std::make_unique<MockProvider>("comp-a"));
    ASSERT_TRUE(h.get() != nullptr);
    passed++;
    std::cout << "✅ PASS: test_get_returns_nonnull\n";
}

static void test_delegates_is_healthy_true() {
    CryptoProviderHandle h(std::make_unique<MockProvider>("comp-a", true));
    ASSERT_TRUE(h.is_healthy());
    passed++;
    std::cout << "✅ PASS: test_delegates_is_healthy_true\n";
}

static void test_delegates_is_healthy_false() {
    CryptoProviderHandle h(std::make_unique<MockProvider>("comp-a", false));
    ASSERT_TRUE(!h.is_healthy());
    passed++;
    std::cout << "✅ PASS: test_delegates_is_healthy_false\n";
}

static void test_delegates_component_name() {
    CryptoProviderHandle h(std::make_unique<MockProvider>("etcd-server"));
    ASSERT_EQ(h.component_name(), "etcd-server");
    passed++;
    std::cout << "✅ PASS: test_delegates_component_name\n";
}

static void test_reload_swaps_provider() {
    CryptoProviderHandle h(std::make_unique<MockProvider>("old", false));
    ASSERT_TRUE(!h.is_healthy());
    ASSERT_EQ(h.component_name(), "old");

    h.reload(std::make_unique<MockProvider>("new", true));

    ASSERT_TRUE(h.is_healthy());
    ASSERT_EQ(h.component_name(), "new");
    passed++;
    std::cout << "✅ PASS: test_reload_swaps_provider\n";
}

static void test_reload_null_throws() {
    CryptoProviderHandle h(std::make_unique<MockProvider>("comp-a"));
    bool threw = false;
    try {
        h.reload(nullptr);
    } catch (const std::invalid_argument&) {
        threw = true;
    }
    ASSERT_TRUE(threw);
    // Handle sigue válido tras el intento fallido
    ASSERT_TRUE(h.get() != nullptr);
    passed++;
    std::cout << "✅ PASS: test_reload_null_throws\n";
}

// N threads leen concurrentemente mientras el hilo principal hace reload.
// Invariante: ningún reader ve null. No debe haber crash ni data race.
static void test_concurrent_reads_consistent() {
    constexpr int N_READERS  = 8;
    constexpr int N_RELOADS  = 50;
    constexpr int N_READS    = 200;

    CryptoProviderHandle h(std::make_unique<MockProvider>("initial"));
    std::atomic<bool> stop{false};
    std::atomic<int>  null_reads{0};

    // Lanzar N_READERS threads que leen continuamente
    std::vector<std::thread> readers;
    for (int i = 0; i < N_READERS; ++i) {
        readers.emplace_back([&]() {
            int count = 0;
            while (!stop.load(std::memory_order_relaxed) && count < N_READS) {
                auto p = h.get();
                if (!p) null_reads.fetch_add(1, std::memory_order_relaxed);
                count++;
                std::this_thread::yield();
            }
        });
    }

    // Hilo principal: N_RELOADS reloads
    for (int i = 0; i < N_RELOADS; ++i) {
        h.reload(std::make_unique<MockProvider>("v" + std::to_string(i)));
        std::this_thread::yield();
    }

    stop.store(true, std::memory_order_relaxed);
    for (auto& t : readers) t.join();

    ASSERT_EQ(null_reads.load(), 0);
    passed++;
    std::cout << "✅ PASS: test_concurrent_reads_consistent\n";
}

// RCU: un reader captura shared_ptr ANTES del reload.
// El provider anterior debe sobrevivir hasta que el reader libere su shared_ptr.
static void test_rcu_old_provider_survives_reload() {
    auto* raw = new MockProvider("survivor");
    std::weak_ptr<ICryptoProvider> weak;

    {
        CryptoProviderHandle h{std::unique_ptr<ICryptoProvider>(raw)};

        // Capturar shared_ptr antes del reload
        auto held = h.get();
        weak = held;

        // Reload — el provider anterior no se destruye mientras 'held' vive
        h.reload(std::make_unique<MockProvider>("new"));

        ASSERT_TRUE(!weak.expired());  // 'held' sigue vivo
        ASSERT_EQ(held->component_name(), "survivor");

        // 'held' sale de scope aquí → refcount → 0 → destrucción
    }

    ASSERT_TRUE(weak.expired());  // ahora sí destruido
    passed++;
    std::cout << "✅ PASS: test_rcu_old_provider_survives_reload\n";
}

// ── main ──────────────────────────────────────────────────────────────────────
int main() {
    std::cout << "\n";
    std::cout << "╔══════════════════════════════════════════════════════╗\n";
    std::cout << "║  test_crypto_provider_handle — RCU wrapper           ║\n";
    std::cout << "║  BACKLOG-CRYPTO-HOT-RELOAD-001 (DAY 163)             ║\n";
    std::cout << "╚══════════════════════════════════════════════════════╝\n\n";

    test_null_provider_throws();
    test_get_returns_nonnull();
    test_delegates_is_healthy_true();
    test_delegates_is_healthy_false();
    test_delegates_component_name();
    test_reload_swaps_provider();
    test_reload_null_throws();
    test_concurrent_reads_consistent();
    test_rcu_old_provider_survives_reload();

    std::cout << "\n═══════════════════════════════════════════════════════\n";
    std::cout << "Results: " << passed << "/" << (passed + failed)
              << " tests passed\n";
    std::cout << "═══════════════════════════════════════════════════════\n";

    if (failed > 0) {
        std::cout << "❌ SOME TESTS FAILED\n";
        return 1;
    }
    std::cout << "🎉 ALL TESTS PASSED\n";
    return 0;
}
