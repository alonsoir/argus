// common/tests/test_crypto_epoch_coordinator.cpp
// BACKLOG-CRYPTO-EPOCH-001 — DAY 164
// TDH: RED → GREEN
// ============================================================================
#include "crypto_epoch_coordinator.h"
#include "vault_types.h"
#include <nlohmann/json.hpp>
#include <atomic>
#include <cassert>
#include <chrono>
#include <condition_variable>
#include <iostream>
#include <mutex>
#include <string>
#include <thread>
#include "httplib.h"

using namespace ml_defender;
using namespace std::chrono_literals;

// ── Framework ─────────────────────────────────────────────────────────────────
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

// ── FakeEtcdServer (reusado del patrón test_http_etcd_registrar) ──────────────
struct FakeEpochServer {
    httplib::Server      svr;
    std::thread          thread;
    int                  port;
    std::atomic<uint16_t> epoch_id{1};
    std::atomic<int64_t>  revision{1};
    std::string           not_before{"2026-01-01T00:00:00Z"};
    std::mutex            nb_mutex;

    explicit FakeEpochServer(int p) : port(p) {
        svr.Post("/register", [](const httplib::Request&, httplib::Response& res) {
            res.set_content(R"({"status":"ok"})", "application/json");
        });
        svr.Post(R"(/v1/heartbeat/.*)", [](const httplib::Request&, httplib::Response& res) {
            res.set_content(R"({"status":"ok"})", "application/json");
        });
        svr.Get("/v1/epoch", [this](const httplib::Request&, httplib::Response& res) {
            std::string nb;
            { std::lock_guard<std::mutex> lk(nb_mutex); nb = not_before; }
            nlohmann::json j;
            j["epoch_id"]   = epoch_id.load();
            j["not_before"] = nb;
            j["revision"]   = revision.load();
            res.set_content(j.dump(), "application/json");
        });
        thread = std::thread([this]() { svr.listen("127.0.0.1", port); });
        std::this_thread::sleep_for(100ms);
    }

    void bump(uint16_t eid, const std::string& nb) {
        { std::lock_guard<std::mutex> lk(nb_mutex); not_before = nb; }
        epoch_id = eid;
        revision++;
    }

    ~FakeEpochServer() { svr.stop(); if (thread.joinable()) thread.join(); }
};

// ── Tests ─────────────────────────────────────────────────────────────────────

// TEST 1: coordinator arranca y watch_state() == CONNECTED
void test_coordinator_starts_connected() {
    FakeEpochServer fake(19200);
    HttpEtcdRegistrar reg("http://127.0.0.1:19200", "etcd-server",
                          1000, 100);
    CryptoEpochCoordinator coord(reg, "etcd-server");
    coord.start([](uint16_t, const std::string&) {});
    std::this_thread::sleep_for(300ms);
    ASSERT_EQ(static_cast<int>(coord.watch_state()),
              static_cast<int>(WatchState::CONNECTED));
    coord.stop();
}

// TEST 2: current_epoch() devuelve 1 al inicio
void test_coordinator_initial_epoch() {
    FakeEpochServer fake(19201);
    HttpEtcdRegistrar reg("http://127.0.0.1:19201", "etcd-server",
                          1000, 100);
    CryptoEpochCoordinator coord(reg, "etcd-server");
    coord.start([](uint16_t, const std::string&) {});
    std::this_thread::sleep_for(300ms);
    ASSERT_EQ(coord.current_epoch(), static_cast<uint16_t>(1));
    coord.stop();
}

// TEST 3: on_epoch_change llamado al cambiar época
void test_coordinator_triggers_callback_on_epoch_change() {
    FakeEpochServer fake(19202);
    HttpEtcdRegistrar reg("http://127.0.0.1:19202", "etcd-server",
                          1000, 100);
    CryptoEpochCoordinator coord(reg, "etcd-server");

    std::atomic<int>      cb_count{0};
    std::atomic<uint16_t> last_eid{0};
    std::mutex mtx;
    std::condition_variable cv;

    coord.start([&](uint16_t eid, const std::string&) {
        last_eid = eid;
        cb_count++;
        cv.notify_one();
    });

    std::this_thread::sleep_for(300ms);
    fake.bump(2, "2026-07-01T00:00:00Z");

    std::unique_lock<std::mutex> lk(mtx);
    bool notified = cv.wait_for(lk, 1s, [&]{ return cb_count.load() >= 1; });
    coord.stop();

    ASSERT_TRUE(notified);
    ASSERT_EQ(last_eid.load(), static_cast<uint16_t>(2));
    ASSERT_EQ(coord.current_epoch(), static_cast<uint16_t>(2));
}

// TEST 4: current_not_before() se actualiza tras cambio de época
void test_coordinator_updates_not_before() {
    FakeEpochServer fake(19203);
    HttpEtcdRegistrar reg("http://127.0.0.1:19203", "etcd-server",
                          1000, 100);
    CryptoEpochCoordinator coord(reg, "etcd-server");

    std::mutex mtx;
    std::condition_variable cv;
    std::atomic<int> cb_count{0};

    coord.start([&](uint16_t, const std::string&) {
        cb_count++;
        cv.notify_one();
    });

    std::this_thread::sleep_for(300ms);
    fake.bump(3, "2026-08-01T00:00:00Z");

    std::unique_lock<std::mutex> lk(mtx);
    cv.wait_for(lk, 1s, [&]{ return cb_count.load() >= 1; });
    coord.stop();

    ASSERT_EQ(coord.current_not_before(), std::string("2026-08-01T00:00:00Z"));
}

// TEST 5: stop() es idempotente
void test_coordinator_stop_idempotent() {
    FakeEpochServer fake(19204);
    HttpEtcdRegistrar reg("http://127.0.0.1:19204", "etcd-server",
                          1000, 100);
    CryptoEpochCoordinator coord(reg, "etcd-server");
    coord.start([](uint16_t, const std::string&) {});
    std::this_thread::sleep_for(200ms);
    coord.stop();
    coord.stop(); // segunda llamada no debe crashear
    ASSERT_TRUE(true);
}

// ── main ──────────────────────────────────────────────────────────────────────
int main() {
    std::cout << "\n══════════════════════════════════════════════\n";
    std::cout <<   "  test_crypto_epoch_coordinator — DAY 164\n";
    std::cout <<   "══════════════════════════════════════════════\n";

    RUN_TEST(test_coordinator_starts_connected);
    RUN_TEST(test_coordinator_initial_epoch);
    RUN_TEST(test_coordinator_triggers_callback_on_epoch_change);
    RUN_TEST(test_coordinator_updates_not_before);
    RUN_TEST(test_coordinator_stop_idempotent);

    std::cout << "\n──────────────────────────────────────────────\n";
    std::cout << "  Passed: " << passed << "  Failed: " << failed << "\n";
    std::cout << "══════════════════════════════════════════════\n\n";
    return failed == 0 ? 0 : 1;
}
