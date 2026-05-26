// common/tests/test_e2e_rotation.cpp
// BACKLOG-CRYPTO-E2E-ROTATION-001 — DAY 165
// TDH: RED → GREEN
// Verifica ciclo completo de rotación de época:
//   FakeEtcdServer → CryptoEpochCoordinator → CryptoProviderHandle::reload()
//   → encrypt(epoch_id) → decrypt_v2 → epoch_id correcto en wire
// ============================================================================
#include "crypto_epoch_coordinator.h"
#include "crypto_provider_handle.hpp"
#include "http_etcd_registrar.h"
#include <crypto_transport/transport.hpp>
#include <seed_client/seed_client.hpp>
#include <sodium.h>

#include <array>
#include <atomic>
#include <cassert>
#include <chrono>
#include <condition_variable>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <mutex>
#include <string>
#include <thread>

#include "httplib.h"
#include <nlohmann/json.hpp>

using namespace ml_defender;
using namespace std::chrono_literals;

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

#define RUN_TEST(name) \
    do { prev_failed = failed; \
         std::cout << "  🔵 " #name "..."; \
         name(); \
         if (failed == prev_failed) { std::cout << " ✅\n"; passed++; } \
         else std::cout << "\n"; \
    } while(0)

// ── MockProvider ──────────────────────────────────────────────────────────────
class MockProvider final : public ICryptoProvider {
public:
    explicit MockProvider(std::string name, uint16_t epoch = 1)
        : name_(std::move(name)), epoch_(epoch) {}

    CryptoMaterial get_material() override {
        CryptoMaterial mat{};
        mat.pk[0]      = static_cast<uint8_t>(epoch_);
        mat.from_cache = false;
        mat.key_version = epoch_;
        return mat;
    }
    bool refresh()  override { return true; }
    bool is_healthy() const override { return true; }
    std::string component_name() const override { return name_; }

private:
    std::string name_;
    uint16_t    epoch_;
};

// ── FakeEpochServer (patrón DAY 164) ─────────────────────────────────────────
struct FakeEpochServer {
    httplib::Server svr;
    std::thread     thread;
    std::mutex      mtx;
    uint16_t        epoch_id{1};
    std::string     not_before{"2026-01-01T00:00:00Z"};

    std::atomic<int64_t> revision{1};

    explicit FakeEpochServer(int port) {
        svr.Get("/v1/epoch", [this](const httplib::Request&, httplib::Response& res) {
            std::lock_guard<std::mutex> lk(mtx);
            nlohmann::json j;
            j["epoch_id"]   = epoch_id;
            j["not_before"] = not_before;
            j["algorithm"]  = "ChaCha20-Poly1305";
            j["revision"]   = revision.load();
            res.set_content(j.dump(), "application/json");
        });
        svr.Post("/register",           [](const httplib::Request&, httplib::Response& res) {
            res.set_content("{\"status\":\"ok\"}", "application/json");
        });
        svr.Post("/v1/heartbeat/(.*)",  [](const httplib::Request&, httplib::Response& res) {
            res.set_content("{\"status\":\"ok\"}", "application/json");
        });
        thread = std::thread([this, port]() { svr.listen("127.0.0.1", port); });
        std::this_thread::sleep_for(50ms);
    }

    void bump(uint16_t new_epoch, const std::string& nb) {
        std::lock_guard<std::mutex> lk(mtx);
        epoch_id   = new_epoch;
        not_before = nb;
        revision.fetch_add(1);
    }

    ~FakeEpochServer() { svr.stop(); if (thread.joinable()) thread.join(); }
};

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

// ── T1: handle.reload() llamado cuando epoch cambia ──────────────────────────
void test_handle_reloads_on_epoch_change() {
    FakeEpochServer fake(19300);
    HttpEtcdRegistrar reg("http://127.0.0.1:19300", "test", 1000, 100);
    CryptoEpochCoordinator coord(reg, "test");

    CryptoProviderHandle handle(std::make_unique<MockProvider>("test", 1));
    std::atomic<int>      reload_count{0};
    std::atomic<uint16_t> last_epoch{0};
    std::mutex mtx; std::condition_variable cv;

    coord.start([&](uint16_t eid, const std::string&) {
        handle.reload(std::make_unique<MockProvider>("test", eid));
        last_epoch = eid;
        reload_count++;
        cv.notify_one();
    });

    std::this_thread::sleep_for(300ms);
    fake.bump(2, "2026-07-01T00:00:00Z");

    std::unique_lock<std::mutex> lk(mtx);
    bool ok = cv.wait_for(lk, 1s, [&]{ return reload_count.load() >= 1; });
    coord.stop();

    ASSERT_TRUE(ok);
    ASSERT_EQ(reload_count.load(), 1);
    ASSERT_EQ(last_epoch.load(), static_cast<uint16_t>(2));
    ASSERT_EQ(coord.current_epoch(), static_cast<uint16_t>(2));
    ASSERT_EQ(handle.get()->get_material().key_version, static_cast<uint32_t>(2));
}

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

// ── T4: coordinator + wire — epoch_id sigue a current_epoch() ────────────────
void test_coordinator_epoch_id_propagates_to_wire() {
    FakeEpochServer fake(19301);
    HttpEtcdRegistrar reg("http://127.0.0.1:19301", "test", 1000, 100);
    CryptoEpochCoordinator coord(reg, "test");

    TestSeedEnv env("e2e_t4");
    auto sc_tx = env.make_client();
    auto sc_rx = env.make_client();
    crypto_transport::CryptoTransport tx(sc_tx, "ml-defender:test:v1:tx");
    crypto_transport::CryptoTransport rx(sc_rx, "ml-defender:test:v1:tx");

    std::mutex mtx; std::condition_variable cv;
    std::atomic<int> cb_count{0};

    coord.start([&](uint16_t, const std::string&) {
        cb_count++;
        cv.notify_one();
    });
    std::this_thread::sleep_for(300ms);

    // epoch=1: wire debe llevar epoch_id=1
    {
        const std::vector<uint8_t> plain = {0xAA};
        auto wire   = tx.encrypt(plain, coord.current_epoch());
        auto result = rx.decrypt_v2(wire);
        ASSERT_EQ(result.epoch_id, static_cast<uint16_t>(1));
        ASSERT_TRUE(result.data == plain);
    }

    // rotación a epoch=2
    fake.bump(2, "2026-08-01T00:00:00Z");
    std::unique_lock<std::mutex> lk(mtx);
    cv.wait_for(lk, 1s, [&]{ return cb_count.load() >= 1; });
    coord.stop();

    // epoch=2: wire debe llevar epoch_id=2
    {
        const std::vector<uint8_t> plain = {0xBB};
        auto wire   = tx.encrypt(plain, coord.current_epoch());
        auto result = rx.decrypt_v2(wire);
        ASSERT_EQ(result.epoch_id, static_cast<uint16_t>(2));
        ASSERT_TRUE(result.data == plain);
    }
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

// ── main ──────────────────────────────────────────────────────────────────────
int main() {
    if (sodium_init() < 0) {
        std::cerr << "❌ libsodium init failed\n";
        return 1;
    }

    std::cout << "\n══════════════════════════════════════════════\n";
    std::cout <<   "  test_e2e_rotation — BACKLOG-CRYPTO-E2E-ROTATION-001\n";
    std::cout <<   "  DAY 165 — TDH RED→GREEN\n";
    std::cout <<   "══════════════════════════════════════════════\n";

    RUN_TEST(test_handle_reloads_on_epoch_change);
    RUN_TEST(test_wire_roundtrip_epoch1);
    RUN_TEST(test_wire_roundtrip_epoch2);
    RUN_TEST(test_coordinator_epoch_id_propagates_to_wire);
    RUN_TEST(test_dual_key_window_pre_rotation_messages_still_decryptable);

    std::cout << "\n──────────────────────────────────────────────\n";
    std::cout << "  Passed: " << passed << "  Failed: " << failed << "\n";
    std::cout << "══════════════════════════════════════════════\n\n";
    return failed == 0 ? 0 : 1;
}
