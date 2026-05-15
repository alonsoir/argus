// ============================================================================
// test_cache_manager.cpp — Tests ICacheManager (ADR-045 DAY 153)
// NullCacheManager e InMemoryCacheManager: sin filesystem.
// FilesystemCacheManager: con mkdtemp.
// ============================================================================
#include "../cache_manager.h"
#include <cassert>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <iostream>

using namespace ml_defender;

static int g_passed = 0;
static int g_failed = 0;

#define ASSERT_EQ(a, b, msg) \
    do { if ((a)==(b)) { std::cout<<"  ✅ PASS: "<<msg<<"\n"; ++g_passed; } \
         else { std::cout<<"  ❌ FAIL: "<<msg<<"\n"; ++g_failed; } } while(0)
#define ASSERT_TRUE(e,m)  ASSERT_EQ((e), true,  m)
#define ASSERT_FALSE(e,m) ASSERT_EQ((e), false, m)

CryptoMaterial make_material() {
    CryptoMaterial mat;
    mat.pk.fill(0x01);
    mat.sk.fill(0x02);
    mat.fingerprint.fill(0x03);
    mat.family           = "A";
    mat.key_version      = 1;
    mat.derivation_timestamp = "2026-05-15T00:00:00Z";
    mat.from_cache       = false;
    return mat;
}

// TEST 1: NullCacheManager — nunca válida, write OK, read nullopt
void test_null_cache() {
    std::cout << "\n── TEST 1: NullCacheManager ──\n";
    NullCacheManager c;
    ASSERT_FALSE(c.is_valid(), "NullCacheManager: is_valid false");
    ASSERT_TRUE(c.write(make_material()), "NullCacheManager: write true");
    ASSERT_FALSE(c.read().has_value(), "NullCacheManager: read nullopt");
    ASSERT_EQ(c.path(), std::string("/dev/null"),
        "NullCacheManager: path /dev/null");
}

// TEST 2: InMemoryCacheManager — ciclo write/read
void test_in_memory_cache_write_read() {
    std::cout << "\n── TEST 2: InMemoryCacheManager write/read ──\n";
    InMemoryCacheManager c;
    ASSERT_FALSE(c.is_valid(), "inicialmente inválida");
    ASSERT_FALSE(c.read().has_value(), "inicialmente vacía");

    auto mat = make_material();
    ASSERT_TRUE(c.write(mat), "write OK");
    ASSERT_TRUE(c.is_valid(), "válida tras write");

    auto result = c.read();
    ASSERT_TRUE(result.has_value(), "read retorna valor");
    ASSERT_EQ(result->family, std::string("A"), "family correcta");
    ASSERT_EQ(result->key_version, uint32_t(1), "key_version correcta");
}

// TEST 3: InMemoryCacheManager invalidate
void test_in_memory_cache_invalidate() {
    std::cout << "\n── TEST 3: InMemoryCacheManager invalidate ──\n";
    InMemoryCacheManager c;
    c.write(make_material());
    ASSERT_TRUE(c.is_valid(), "válida tras write");
    c.invalidate();
    ASSERT_FALSE(c.is_valid(), "inválida tras invalidate");
    // Nota: read() con is_valid=false retorna nullopt
    ASSERT_FALSE(c.read().has_value(), "read nullopt tras invalidate");
}

// TEST 4: InMemoryCacheManager clear
void test_in_memory_cache_clear() {
    std::cout << "\n── TEST 4: InMemoryCacheManager clear ──\n";
    InMemoryCacheManager c;
    c.write(make_material());
    c.clear();
    ASSERT_FALSE(c.is_valid(), "inválida tras clear");
    ASSERT_FALSE(c.read().has_value(), "vacía tras clear");
}

// TEST 5: FilesystemCacheManager — write/read roundtrip
void test_filesystem_cache_roundtrip() {
    std::cout << "\n── TEST 5: FilesystemCacheManager roundtrip ──\n";

    // mkdtemp en /tmp
    char tmpl[] = "/tmp/argus-test-cache-XXXXXX";
    const char* tmpdir = mkdtemp(tmpl);
    if (!tmpdir) {
        std::cout << "  ⚠️  SKIP: mkdtemp falló\n";
        return;
    }

    VaultClientConfig cfg;
    cfg.component_name = "test-comp";
    cfg.family         = "A";
    cfg.cache_dir      = tmpdir;
    cfg.cache_ttl_s    = 3600;

    FilesystemCacheManager c{cfg};
    ASSERT_FALSE(c.is_valid(), "sin cache: is_valid false");

    auto mat = make_material();
    ASSERT_TRUE(c.write(mat), "write a disco OK");
    ASSERT_TRUE(c.is_valid(), "válida tras write");

    auto result = c.read();
    ASSERT_TRUE(result.has_value(), "read desde disco OK");
    ASSERT_EQ(result->family, std::string("A"), "family correcta");
    ASSERT_EQ(result->key_version, uint32_t(1), "key_version correcta");
    ASSERT_EQ(result->derivation_timestamp,
        std::string("2026-05-15T00:00:00Z"), "timestamp correcto");

    // Cleanup
    std::filesystem::remove_all(tmpdir);
}

// TEST 6: FilesystemCacheManager TTL expirado
void test_filesystem_cache_expired() {
    std::cout << "\n── TEST 6: FilesystemCacheManager TTL=0 expirado ──\n";

    char tmpl[] = "/tmp/argus-test-cache-XXXXXX";
    const char* tmpdir = mkdtemp(tmpl);
    if (!tmpdir) {
        std::cout << "  ⚠️  SKIP: mkdtemp falló\n";
        return;
    }

    VaultClientConfig cfg;
    cfg.component_name = "test-comp";
    cfg.family         = "A";
    cfg.cache_dir      = tmpdir;
    cfg.cache_ttl_s    = 0;  // TTL=0 → siempre expirado

    FilesystemCacheManager c{cfg};
    c.write(make_material());
    ASSERT_FALSE(c.is_valid(), "TTL=0: is_valid false (expirado)");

    std::filesystem::remove_all(tmpdir);
}

int main() {
    std::cout << "╔════════════════════════════════════════════════════╗\n";
    std::cout << "║  ICacheManager — DAY 153 Tests                    ║\n";
    std::cout << "╚════════════════════════════════════════════════════╝\n";

    test_null_cache();
    test_in_memory_cache_write_read();
    test_in_memory_cache_invalidate();
    test_in_memory_cache_clear();
    test_filesystem_cache_roundtrip();
    test_filesystem_cache_expired();

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