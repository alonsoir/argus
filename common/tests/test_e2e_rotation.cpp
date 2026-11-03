// common/tests/test_e2e_rotation.cpp
// BACKLOG-CRYPTO-E2E-ROTATION-001 — DAY 165
// [ADR045-FUERA-D316] DAY316: sin ADR-045 (HttpEtcdRegistrar y CryptoEpochCoordinator borrados) se van T1 y T4, que
// probaban el coordinador. Se quedan las pruebas de la época en el cable, única cobertura que tiene:
//   encrypt(epoch_id) → decrypt_v2 → epoch_id correcto (épocas 1 y 2), ventana de dos y centinela 0xFFFF.
// ============================================================================
#include <crypto_transport/transport.hpp>
#include <seed_client/seed_client.hpp>
#include <sodium.h>

#include <array>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

// ── Test framework ────────────────────────────────────────────────────────────
static int passed = 0;
static int failed = 0;
static int prev_failed = 0;

#define ASSERT_TRUE(expr) \
    do { if (!(expr)) { \
        std::cerr << "❌ FAIL: " << __func__ << " — " #expr \
                  << " (" << __FILE__ << ":" << __LINE__ << ")\n"; \
        failed++; return; } } while(0)

#define ASSERT_EQ(a,b) \
    do { if ((a)!=(b)) { \
        std::cerr << "❌ FAIL: " << __func__ << " — " #a "=" << (a) \
                  << " != " #b "=" << (b) \
                  << " (" << __FILE__ << ":" << __LINE__ << ")\n"; \
        failed++; return; } } while(0)

#define ASSERT_THROWS(expr) \
    do { bool threw = false; \
         try { (void)(expr); } catch (...) { threw = true; } \
         if (threw == false) { \
             std::cerr << "❌ FAIL: " << __func__ << " — expected exception: " #expr \
                       << " (" << __FILE__ << ":" << __LINE__ << ")\n"; \
             failed++; return; } } while(0)

#define RUN_TEST(name) \
    do { prev_failed = failed; \
         std::cout << "  🔵 " #name "..."; \
         name(); \
         if (failed == prev_failed) { std::cout << " ✅\n"; passed++; } \
         else std::cout << "\n"; \
    } while(0)

// ── TestSeedEnv (patrón test_crypto_transport) ────────────────────────────────
struct TestSeedEnv {
    std::filesystem::path dir;
    std::filesystem::path json_path;

    explicit TestSeedEnv(const std::string& id = "e2e") {
        dir = std::filesystem::temp_directory_path() / ("argus_e2e_rotation_" + id);
        std::filesystem::create_directories(dir);

        std::array<uint8_t, 32> seed{};
        randombytes_buf(seed.data(), seed.size());

        auto seed_path = dir / "seed.bin";
        std::ofstream sf(seed_path, std::ios::binary);
        sf.write(reinterpret_cast<const char*>(seed.data()), 32);
        sf.close();
        std::filesystem::permissions(seed_path,
            std::filesystem::perms::owner_read,
            std::filesystem::perm_options::replace);

        json_path = dir / (id + ".json");
        std::ofstream jf(json_path);
        jf << "{\"identity\":{\"component_id\":\"" << id
           << "\",\"keys_dir\":\"" << dir.string() << "/\"}}";
    }

    ~TestSeedEnv() { std::filesystem::remove_all(dir); }

    ml_defender::SeedClient make_client() const {
        ml_defender::SeedClient sc(json_path.string());
        sc.load();
        return sc;
    }
};

// ── T2: round-trip epoch_id=1 en wire ────────────────────────────────────────
void test_wire_roundtrip_epoch1() {
    if (sodium_init() < 0) { ASSERT_TRUE(false); return; }
    TestSeedEnv env("e2e_t2");
    auto sc = env.make_client();
    crypto_transport::CryptoTransport tx(sc, "ml-defender:test:v1:tx");
    crypto_transport::CryptoTransport rx(sc, "ml-defender:test:v1:tx");

    const std::vector<uint8_t> plaintext = {0x01, 0x02, 0x03, 0x04};
    auto wire   = tx.encrypt(plaintext, 1);
    auto result = rx.decrypt_v2(wire);

    ASSERT_TRUE(result.data == plaintext);
    ASSERT_EQ(result.epoch_id, static_cast<uint16_t>(1));
}

// ── T3: round-trip epoch_id=2 en wire ────────────────────────────────────────
void test_wire_roundtrip_epoch2() {
    TestSeedEnv env("e2e_t3");
    auto sc = env.make_client();
    crypto_transport::CryptoTransport tx(sc, "ml-defender:test:v1:tx");
    crypto_transport::CryptoTransport rx(sc, "ml-defender:test:v1:tx");

    const std::vector<uint8_t> plaintext = {0xDE, 0xAD, 0xBE, 0xEF};
    auto wire   = tx.encrypt(plaintext, 2);
    auto result = rx.decrypt_v2(wire);

    ASSERT_TRUE(result.data == plaintext);
    ASSERT_EQ(result.epoch_id, static_cast<uint16_t>(2));
}

// ── T5: ventana dual-key — mensajes pre-rotación siguen descifrables ──────────
// En community mode (mismo seed), ambas épocas usan la misma clave HKDF.
// epoch_id es metadato de coordinación — no cambia la clave de descifrado.
void test_dual_key_window_pre_rotation_messages_still_decryptable() {
    TestSeedEnv env("e2e_t5");
    auto sc_tx = env.make_client();
    auto sc_rx = env.make_client();
    crypto_transport::CryptoTransport tx(sc_tx, "ml-defender:test:v1:tx");
    crypto_transport::CryptoTransport rx(sc_rx, "ml-defender:test:v1:tx");

    const std::vector<uint8_t> plain_pre  = {0x01, 0x02};
    const std::vector<uint8_t> plain_post = {0x03, 0x04};

    // mensaje pre-rotación: epoch_id=1
    auto wire_pre  = tx.encrypt(plain_pre,  1);
    // mensaje post-rotación: epoch_id=2
    auto wire_post = tx.encrypt(plain_post, 2);

    // ambos descifrables por el mismo rx (ventana dual-key community)
    auto res_pre  = rx.decrypt_v2(wire_pre);
    auto res_post = rx.decrypt_v2(wire_post);

    ASSERT_TRUE(res_pre.data == plain_pre);
    ASSERT_EQ(res_pre.epoch_id,  static_cast<uint16_t>(1));
    ASSERT_TRUE(res_post.data == plain_post);
    ASSERT_EQ(res_post.epoch_id, static_cast<uint16_t>(2));
}


// ── T6: epoch_id=0xFFFF rechazado ANTES de descifrar (DEBT-CRYPTO-NEGATIVE-TEST-001) ──
// Garantia: no oracle de padding — validacion del header precede al MAC check.
void test_epoch_id_sentinel_rejected() {
    TestSeedEnv env("e2e_t6");
    auto sc_tx = env.make_client();
    auto sc_rx = env.make_client();
    crypto_transport::CryptoTransport tx(sc_tx, "ml-defender:test:v1:tx");
    crypto_transport::CryptoTransport rx(sc_rx, "ml-defender:test:v1:tx");

    const std::vector<uint8_t> plaintext = {0x01, 0x02, 0x03};
    auto wire = tx.encrypt(plaintext, 0xFFFF);
    ASSERT_THROWS(rx.decrypt_v2(wire));
}

// ── main ──────────────────────────────────────────────────────────────────────
int main() {
    if (sodium_init() < 0) {
        std::cerr << "❌ libsodium init failed\n";
        return 1;
    }

    std::cout << "\n══════════════════════════════════════════════\n";
    std::cout <<   "  test_e2e_rotation — BACKLOG-CRYPTO-E2E-ROTATION-001\n";
    std::cout <<   "  DAY 165 / DAY316: época en el cable (sin ADR-045)\n";
    std::cout <<   "══════════════════════════════════════════════\n";

    RUN_TEST(test_wire_roundtrip_epoch1);
    RUN_TEST(test_wire_roundtrip_epoch2);
    RUN_TEST(test_dual_key_window_pre_rotation_messages_still_decryptable);
    RUN_TEST(test_epoch_id_sentinel_rejected);

    std::cout << "\n──────────────────────────────────────────────\n";
    std::cout << "  Passed: " << passed << "  Failed: " << failed << "\n";
    std::cout << "══════════════════════════════════════════════\n\n";
    return failed == 0 ? 0 : 1;
}
