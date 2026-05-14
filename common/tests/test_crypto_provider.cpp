// ============================================================================
// test_crypto_provider.cpp — Tests para ICryptoProvider (ADR-044 DAY 151)
// ============================================================================
// Fixture propio: crea directorio temporal con JSON + seed.bin sintético.
// No depende de /etc/ml-defender/ ni de permisos root.
// ============================================================================

#include "crypto_provider.h"
#include <cassert>
#include <cstring>
#include <fstream>
#include <iostream>
#include <filesystem>
#include <stdexcept>
#include <sodium.h>

namespace fs = std::filesystem;
using namespace ml_defender;

// ── Contadores ────────────────────────────────────────────────────────────────
static int passed = 0;
static int failed = 0;

// ── Fixture ───────────────────────────────────────────────────────────────────

struct TestFixture {
    fs::path dir;

    TestFixture() {
        // Crear directorio temporal en /tmp
        char tmpl[] = "/tmp/argus-test-XXXXXX";
        char* result = mkdtemp(tmpl);
        if (!result) {
            throw std::runtime_error("mkdtemp falló");
        }
        dir = result;

        // Generar seed.bin: 32 bytes aleatorios via libsodium
        std::array<uint8_t, 32> seed{};
        randombytes_buf(seed.data(), seed.size());

        fs::path seed_path = dir / "seed.bin";
        std::ofstream sf(seed_path, std::ios::binary);
        sf.write(reinterpret_cast<const char*>(seed.data()), seed.size());
        sf.close();
        fs::permissions(seed_path,
            fs::perms::owner_read,
            fs::perm_options::replace);

        // Escribir JSON mínimo con identity.keys_dir apuntando al fixture
        fs::path json_path = dir / "test-component.json";
        std::ofstream jf(json_path);
        jf << "{\n"
           << "  \"identity\": {\n"
           << "    \"component_id\": \"test-component\",\n"
           << "    \"keys_dir\": \"" << dir.string() << "\"\n"
           << "  }\n"
           << "}\n";
        jf.close();
    }

    ~TestFixture() {
        std::error_code ec;
        fs::remove_all(dir, ec);
    }

    CryptoProviderConfig config() const {
        CryptoProviderConfig cfg;
        cfg.component_name        = "test-component";
        cfg.component_config_path = dir.string() + "/";
        return cfg;
    }
};

// ── Helpers ───────────────────────────────────────────────────────────────────

static bool all_zeros(const uint8_t* data, size_t len) {
    for (size_t i = 0; i < len; ++i) {
        if (data[i] != 0) return false;
    }
    return true;
}

// ── Tests ─────────────────────────────────────────────────────────────────────

static void test_create_returns_nonnull() {
    TestFixture fx;
    auto provider = CryptoProvider::create(fx.config());
    assert(provider != nullptr);
    passed++;
    std::cout << "✅ PASS: test_create_returns_nonnull\n";
}

static void test_component_name() {
    TestFixture fx;
    auto provider = CryptoProvider::create(fx.config());
    assert(provider->component_name() == "test-component");
    passed++;
    std::cout << "✅ PASS: test_component_name\n";
}

static void test_empty_component_name_throws() {
    TestFixture fx;
    CryptoProviderConfig cfg = fx.config();
    cfg.component_name = "";
    try {
        CryptoProvider::create(cfg);
        failed++;
        std::cout << "❌ FAIL: test_empty_component_name_throws — no lanzó\n";
    } catch (const std::runtime_error&) {
        passed++;
        std::cout << "✅ PASS: test_empty_component_name_throws\n";
    }
}

static void test_get_material_valid_keys() {
    TestFixture fx;
    auto provider = CryptoProvider::create(fx.config());

#ifdef ARGUS_VAULT_ENABLED
    try {
        auto mat = provider->get_material();
        assert(!all_zeros(mat.pk.data(), mat.pk.size()));
        assert(!all_zeros(mat.sk.data(), mat.sk.size()));
        assert(!all_zeros(mat.fingerprint.data(), mat.fingerprint.size()));
        passed++;
        std::cout << "✅ PASS: test_get_material_valid_keys\n";
    } catch (const std::runtime_error& e) {
        std::cout << "⚠️  SKIP: test_get_material_valid_keys"
                  << " (Vault no disponible: " << e.what() << ")\n";
    }
#else
    auto mat = provider->get_material();
    assert(!all_zeros(mat.pk.data(), mat.pk.size()));
    assert(!all_zeros(mat.sk.data(), mat.sk.size()));
    assert(!all_zeros(mat.fingerprint.data(), mat.fingerprint.size()));
    passed++;
    std::cout << "✅ PASS: test_get_material_valid_keys\n";
#endif
}

static void test_get_material_is_cached() {
    TestFixture fx;
    auto provider = CryptoProvider::create(fx.config());

#ifdef ARGUS_VAULT_ENABLED
    try {
        auto mat1 = provider->get_material();
        auto mat2 = provider->get_material();
        assert(mat1.pk == mat2.pk);
        assert(mat1.sk == mat2.sk);
        passed++;
        std::cout << "✅ PASS: test_get_material_is_cached\n";
    } catch (const std::runtime_error&) {
        std::cout << "⚠️  SKIP: test_get_material_is_cached (Vault no disponible)\n";
    }
#else
    auto mat1 = provider->get_material();
    auto mat2 = provider->get_material();
    assert(mat1.pk == mat2.pk);
    assert(mat1.sk == mat2.sk);
    passed++;
    std::cout << "✅ PASS: test_get_material_is_cached\n";
#endif
}

static void test_is_healthy_before_and_after_get() {
    TestFixture fx;
    auto provider = CryptoProvider::create(fx.config());
    assert(!provider->is_healthy());

#ifdef ARGUS_VAULT_ENABLED
    try {
        provider->get_material();
        assert(provider->is_healthy());
        passed++;
        std::cout << "✅ PASS: test_is_healthy_before_and_after_get\n";
    } catch (const std::runtime_error&) {
        std::cout << "⚠️  SKIP: test_is_healthy_before_and_after_get (Vault no disponible)\n";
    }
#else
    provider->get_material();
    assert(provider->is_healthy());
    passed++;
    std::cout << "✅ PASS: test_is_healthy_before_and_after_get\n";
#endif
}

static void test_refresh() {
    TestFixture fx;
    auto provider = CryptoProvider::create(fx.config());

#ifdef ARGUS_VAULT_ENABLED
    bool ok = provider->refresh();
    if (ok) assert(provider->is_healthy());
    passed++;
    std::cout << "✅ PASS: test_refresh"
              << (ok ? " (Vault OK)" : " (Vault KO, false esperado)") << "\n";
#else
    bool ok = provider->refresh();
    assert(ok);
    assert(provider->is_healthy());
    passed++;
    std::cout << "✅ PASS: test_refresh\n";
#endif
}

static void test_determinism() {
#ifndef ARGUS_VAULT_ENABLED
    // Mismo seed.bin → mismo keypair desde dos providers distintos
    TestFixture fx;
    auto p1 = CryptoProvider::create(fx.config());
    auto p2 = CryptoProvider::create(fx.config());
    assert(p1->get_material().pk == p2->get_material().pk);
    assert(p1->get_material().sk == p2->get_material().sk);
    passed++;
    std::cout << "✅ PASS: test_determinism\n";
#else
    std::cout << "⚠️  SKIP: test_determinism (enterprise)\n";
#endif
}

static void test_invalid_path_throws() {
#ifndef ARGUS_VAULT_ENABLED
    CryptoProviderConfig cfg;
    cfg.component_name        = "noexiste";
    cfg.component_config_path = "/tmp/argus-noexiste-XXXXXX/";
    auto provider = CryptoProvider::create(cfg);
    try {
        provider->get_material();
        failed++;
        std::cout << "❌ FAIL: test_invalid_path_throws — no lanzó\n";
    } catch (const std::runtime_error&) {
        passed++;
        std::cout << "✅ PASS: test_invalid_path_throws\n";
    }
#else
    std::cout << "⚠️  SKIP: test_invalid_path_throws (enterprise)\n";
#endif
}

static void test_fingerprint_is_sha256_of_pk() {
#ifndef ARGUS_VAULT_ENABLED
    TestFixture fx;
    auto provider = CryptoProvider::create(fx.config());
    auto mat = provider->get_material();

    std::array<uint8_t, 32> expected{};
    crypto_hash_sha256(expected.data(), mat.pk.data(), mat.pk.size());
    assert(mat.fingerprint == expected);
    passed++;
    std::cout << "✅ PASS: test_fingerprint_is_sha256_of_pk\n";
#else
    std::cout << "⚠️  SKIP: test_fingerprint_is_sha256_of_pk (enterprise)\n";
#endif
}

// ── main ──────────────────────────────────────────────────────────────────────

int main() {
    if (sodium_init() < 0) {
        std::cerr << "❌ sodium_init() falló\n";
        return 1;
    }

    std::cout << "\n";
    std::cout << "╔══════════════════════════════════════════════════════╗\n";
#ifdef ARGUS_VAULT_ENABLED
    std::cout << "║  test_crypto_provider — VaultProvider (enterprise)   ║\n";
#else
    std::cout << "║  test_crypto_provider — SeedFileProvider (community) ║\n";
#endif
    std::cout << "╚══════════════════════════════════════════════════════╝\n\n";

    test_create_returns_nonnull();
    test_component_name();
    test_empty_component_name_throws();
    test_get_material_valid_keys();
    test_get_material_is_cached();
    test_is_healthy_before_and_after_get();
    test_refresh();
    test_determinism();
    test_invalid_path_throws();
    test_fingerprint_is_sha256_of_pk();

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