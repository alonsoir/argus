// common/tests/test_http_etcd_registrar.cpp
// DEBT-ETCD-REGISTRAR-REAL-001 — DAY 164
// TDH: tests RED — HttpEtcdRegistrar contra servidor httplib inline
// ============================================================================
#include "http_etcd_registrar.h"
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

// ── Framework mínimo ─────────────────────────────────────────────────────────
static int passed = 0;
static int failed = 0;

#define ASSERT_TRUE(expr) \
    do { \
        if (!(expr)) { \
            std::cerr << "❌ FAIL: " << __func__ << " — " #expr \
                      << " (" << __FILE__ << ":" << __LINE__ << ")\n"; \
            failed++; return; \
        } \
    } while (0)

#define ASSERT_EQ(a, b) \
    do { \
        if ((a) != (b)) { \
            std::cerr << "❌ FAIL: " << __func__ << " — " #a "=" << (a) \
                      << " != " #b "=" << (b) \
                      << " (" << __FILE__ << ":" << __LINE__ << ")\n"; \
            failed++; return; \
        } \
    } while (0)

#define ASSERT_GE(a, b) \
    do { \
        if ((a) < (b)) { \
            std::cerr << "❌ FAIL: " << __func__ << " — " #a "=" << (a) \
                      << " < " #b "=" << (b) \
                      << " (" << __FILE__ << ":" << __LINE__ << ")\n"; \
            failed++; return; \
        } \
    } while (0)

#define RUN_TEST(name) \
    do { \
        std::cout << "  🔵 " #name "..."; \
        name(); \
        if (failed == prev_failed) { \
            std::cout << " ✅\n"; passed++; \
        } else { \
            std::cout << "\n"; \
        } \
        prev_failed = failed; \
    } while (0)

// ── FakeEtcdServer ────────────────────────────────────────────────────────────
struct FakeEtcdServer {
    httplib::Server      svr;
    std::thread          thread;
    int                  port;
    std::atomic<int>     register_calls{0};
    std::atomic<int>     heartbeat_calls{0};
    std::atomic<uint16_t> epoch_id{1};
    std::atomic<int64_t>  revision{1};
    std::string           not_before{"2026-01-01T00:00:00Z"};
    std::mutex            nb_mutex;
    std::atomic<bool>     simulate_timeout{false};

    explicit FakeEtcdServer(int p) : port(p) {
        svr.Post("/register", [this](const httplib::Request&,
                                      httplib::Response& res) {
            register_calls++;
            res.set_content(R"({"status":"ok"})", "application/json");
        });
        svr.Post(R"(/v1/heartbeat/.*)", [this](const httplib::Request&,
                                               httplib::Response& res) {
            heartbeat_calls++;
            res.set_content(R"({"status":"ok"})", "application/json");
        });
        svr.Get("/v1/epoch", [this](const httplib::Request&,
                                    httplib::Response& res) {
            if (simulate_timeout) {
                std::this_thread::sleep_for(10s);
                return;
            }
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

    void bump_epoch(uint16_t new_id, const std::string& nb) {
        { std::lock_guard<std::mutex> lk(nb_mutex); not_before = nb; }
        epoch_id = new_id;
        revision++;
    }

    ~FakeEtcdServer() {
        svr.stop();
        if (thread.joinable()) thread.join();
    }
};

static CryptoMaterial make_material() {
    CryptoMaterial m{};
    m.family      = "A";
    m.key_version = 1;
    return m;
}

// ── Tests ─────────────────────────────────────────────────────────────────────

// TEST 1: register_status hace POST /register y devuelve true
void test_register_posts_to_server() {
    FakeEtcdServer fake(19100);
    HttpEtcdRegistrar reg("http://127.0.0.1:19100", "sniffer");

    bool ok = reg.register_status(make_material(), "sniffer");

    ASSERT_TRUE(ok);
    ASSERT_EQ(fake.register_calls.load(), 1);
}

// TEST 2: start_keepalive hace POST /v1/heartbeat periódicamente
void test_keepalive_posts_heartbeat() {
    FakeEtcdServer fake(19101);
    HttpEtcdRegistrar reg("http://127.0.0.1:19101", "sniffer",
                          /*keepalive_interval_ms=*/100);

    reg.register_status(make_material(), "sniffer");
    reg.start_keepalive();
    std::this_thread::sleep_for(600ms);
    reg.stop_keepalive();

    ASSERT_GE(fake.heartbeat_calls.load(), 3);
}

// TEST 3: watch_epoch llama callback cuando revision cambia
void test_watch_epoch_detects_change() {
    FakeEtcdServer fake(19102);
    HttpEtcdRegistrar reg("http://127.0.0.1:19102", "etcd-server",
                          /*keepalive_interval_ms=*/1000,
                          /*poll_interval_ms=*/100);

    std::atomic<int>      cb_count{0};
    std::atomic<uint16_t> last_epoch{0};
    std::mutex mtx;
    std::condition_variable cv;

    reg.watch_epoch([&](uint16_t eid, const std::string&) {
        last_epoch = eid;
        cb_count++;
        cv.notify_one();
    });

    std::this_thread::sleep_for(200ms);
    fake.bump_epoch(2, "2026-06-01T00:00:00Z");

    std::unique_lock<std::mutex> lk(mtx);
    bool notified = cv.wait_for(lk, 1s, [&]{ return cb_count.load() >= 1; });
    reg.stop_watch();

    ASSERT_TRUE(notified);
    ASSERT_EQ(last_epoch.load(), static_cast<uint16_t>(2));
}

// TEST 4: watch NO llama callback si revision no cambia
void test_watch_skips_same_revision() {
    FakeEtcdServer fake(19103);
    HttpEtcdRegistrar reg("http://127.0.0.1:19103", "etcd-server",
                          /*keepalive_interval_ms=*/1000,
                          /*poll_interval_ms=*/100);

    std::atomic<int> cb_count{0};
    reg.watch_epoch([&](uint16_t, const std::string&) { cb_count++; });

    std::this_thread::sleep_for(500ms);
    reg.stop_watch();

    ASSERT_EQ(cb_count.load(), 0);
}

// TEST 5: watch_state() transiciona a DEGRADED cuando servidor no responde
void test_watch_state_degraded_on_timeout() {
    FakeEtcdServer fake(19104);
    HttpEtcdRegistrar reg("http://127.0.0.1:19104", "etcd-server",
                          /*keepalive_interval_ms=*/1000,
                          /*poll_interval_ms=*/100,
                          /*request_timeout_ms=*/200,
                          /*degraded_threshold=*/2);

    reg.watch_epoch([](uint16_t, const std::string&) {});
    std::this_thread::sleep_for(200ms);
    ASSERT_EQ(static_cast<int>(reg.watch_state()), static_cast<int>(WatchState::CONNECTED));

    fake.simulate_timeout = true;
    std::this_thread::sleep_for(700ms);
    ASSERT_EQ(static_cast<int>(reg.watch_state()), static_cast<int>(WatchState::DEGRADED));

    reg.stop_watch();
}

// ── main ──────────────────────────────────────────────────────────────────────
int main() {
    std::cout << "\n══════════════════════════════════════════════\n";
    std::cout <<   "  test_http_etcd_registrar — DAY 164\n";
    std::cout <<   "══════════════════════════════════════════════\n";

    int prev_failed = 0;
    RUN_TEST(test_register_posts_to_server);
    RUN_TEST(test_keepalive_posts_heartbeat);
    RUN_TEST(test_watch_epoch_detects_change);
    RUN_TEST(test_watch_skips_same_revision);
    RUN_TEST(test_watch_state_degraded_on_timeout);

    std::cout << "\n──────────────────────────────────────────────\n";
    std::cout << "  Passed: " << passed << "  Failed: " << failed << "\n";
    std::cout << "══════════════════════════════════════════════\n\n";
    return failed == 0 ? 0 : 1;
}
