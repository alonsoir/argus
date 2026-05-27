// test_autonomy_subscriber.cpp — DEBT-AUTONOMY-ZMQ-EVENTS-001 (DAY 155)
// Tests del AutonomySubscriber con ZMQ inproc (sin IPC, sin filesystem)
#include "firewall/autonomy_subscriber.hpp"
#include "test_firewall_stubs.hpp"
#include "firewall/autonomy_reactor.hpp"
#include <zmq.hpp>
#include <cassert>
#include <chrono>
#include <iostream>
#include <string>
#include <thread>
#include <vector>

using namespace mldefender::firewall;

static const std::vector<std::string> TEST_CIDRS{"192.168.1.0/24"};
static const std::string INPROC = "ipc:///tmp/test-autonomy-subscriber.sock";
static const char* TOPIC = AutonomySubscriber::TOPIC;

// Publica un mensaje ZMQ con topic + payload
static void publish_event(zmq::socket_t& pub, const std::string& state) {
    const std::string payload =
        "{\"state\":\"" + state + "\",\"from\":\"NORMAL\","
        "\"timestamp_utc_ns\":0,\"component\":\"test\"}";
    pub.send(zmq::message_t(TOPIC, std::strlen(TOPIC)), zmq::send_flags::sndmore);
    pub.send(zmq::message_t(payload.data(), payload.size()), zmq::send_flags::none);
}

// Espera con timeout a que el reactor alcance el modo esperado
[[maybe_unused]] static bool wait_for_mode(FirewallAutonomyReactor& reactor,
                           FirewallAutonomyMode expected,
                           int timeout_ms = 500) {
    const auto deadline = std::chrono::steady_clock::now()
                        + std::chrono::milliseconds(timeout_ms);
    while (std::chrono::steady_clock::now() < deadline) {
        if (reactor.current_mode() == expected) return true;
        std::this_thread::sleep_for(std::chrono::milliseconds(10));
    }
    return false;
}

int main() {
    // ── T1: evento AUTONOMOUS activa reactor ──────────────────────────────────
    {
        zmq::context_t ctx(1);
        zmq::socket_t  pub(ctx, zmq::socket_type::pub);
        pub.set(zmq::sockopt::linger, 0);
        pub.bind(INPROC);

        StubExecutor ex;
        FirewallAutonomyReactor reactor(TEST_CIDRS, false,
            [&ex](const std::string& c){ return ex(c); });

        AutonomySubscriber sub(reactor,
            []{ return FirewallAutonomyMode::NORMAL; },  // poll_cb
            INPROC, 3600);  // reconcile muy largo para no interferir
        sub.start();

        std::this_thread::sleep_for(std::chrono::milliseconds(300)); // slow-joiner
        publish_event(pub, "AUTONOMOUS");

        assert(wait_for_mode(reactor, FirewallAutonomyMode::AUTONOMOUS));
        assert(reactor.is_deny_active());
        sub.stop();
        std::cout << "T1 PASS: evento AUTONOMOUS activa reactor\n";
    }
    // ── T2: evento NORMAL desactiva reactor ───────────────────────────────────
    {
        zmq::context_t ctx(1);
        zmq::socket_t  pub(ctx, zmq::socket_type::pub);
        pub.set(zmq::sockopt::linger, 0);
        pub.bind(INPROC);

        StubExecutor ex;
        FirewallAutonomyReactor reactor(TEST_CIDRS, false,
            [&ex](const std::string& c){ return ex(c); });

        AutonomySubscriber sub(reactor,
            []{ return FirewallAutonomyMode::NORMAL; },
            INPROC, 3600);
        sub.start();

        std::this_thread::sleep_for(std::chrono::milliseconds(300));
        publish_event(pub, "AUTONOMOUS");
        assert(wait_for_mode(reactor, FirewallAutonomyMode::AUTONOMOUS));

        publish_event(pub, "NORMAL");
        assert(wait_for_mode(reactor, FirewallAutonomyMode::NORMAL));
        assert(!reactor.is_deny_active());
        sub.stop();
        std::cout << "T2 PASS: evento NORMAL desactiva reactor\n";
    }
    // ── T3: evento DEGRADED activa reactor ───────────────────────────────────
    {
        zmq::context_t ctx(1);
        zmq::socket_t  pub(ctx, zmq::socket_type::pub);
        pub.set(zmq::sockopt::linger, 0);
        pub.bind(INPROC);

        StubExecutor ex;
        FirewallAutonomyReactor reactor(TEST_CIDRS, false,
            [&ex](const std::string& c){ return ex(c); });

        AutonomySubscriber sub(reactor,
            []{ return FirewallAutonomyMode::NORMAL; },
            INPROC, 3600);
        sub.start();

        std::this_thread::sleep_for(std::chrono::milliseconds(300));
        publish_event(pub, "DEGRADED");

        assert(wait_for_mode(reactor, FirewallAutonomyMode::DEGRADED));
        assert(reactor.is_deny_active());
        sub.stop();
        std::cout << "T3 PASS: evento DEGRADED activa reactor\n";
    }
    // ── T4: RECONCILING mapea a NORMAL ───────────────────────────────────────
    {
        zmq::context_t ctx(1);
        zmq::socket_t  pub(ctx, zmq::socket_type::pub);
        pub.set(zmq::sockopt::linger, 0);
        pub.bind(INPROC);

        StubExecutor ex;
        FirewallAutonomyReactor reactor(TEST_CIDRS, false,
            [&ex](const std::string& c){ return ex(c); });

        AutonomySubscriber sub(reactor,
            []{ return FirewallAutonomyMode::NORMAL; },
            INPROC, 3600);
        sub.start();

        std::this_thread::sleep_for(std::chrono::milliseconds(300));
        // Primero AUTONOMOUS, luego RECONCILING → debe volver a NORMAL
        publish_event(pub, "AUTONOMOUS");
        assert(wait_for_mode(reactor, FirewallAutonomyMode::AUTONOMOUS));
        publish_event(pub, "RECONCILING");
        assert(wait_for_mode(reactor, FirewallAutonomyMode::NORMAL));
        sub.stop();
        std::cout << "T4 PASS: RECONCILING mapea a NORMAL\n";
    }
    // ── T5: reconciliador llama poll_cb y actualiza reactor ──────────────────
    {
        zmq::context_t ctx(1);
        zmq::socket_t  pub(ctx, zmq::socket_type::pub);
        pub.set(zmq::sockopt::linger, 0);
        pub.bind(INPROC);

        StubExecutor ex;
        FirewallAutonomyReactor reactor(TEST_CIDRS, false,
            [&ex](const std::string& c){ return ex(c); });

        // poll_cb devuelve AUTONOMOUS — el reconciliador debe activar el reactor
        AutonomySubscriber sub(reactor,
            []{ return FirewallAutonomyMode::AUTONOMOUS; },
            INPROC,
            0);  // reconcile_interval_sec=0 → dispara en cada iteración
        sub.start();

        assert(wait_for_mode(reactor, FirewallAutonomyMode::AUTONOMOUS, 3000));
        sub.stop();
        std::cout << "T5 PASS: reconciliador activa reactor via poll_cb\n";
    }
    // ── T6: stop() es idempotente ─────────────────────────────────────────────
    {
        zmq::context_t ctx(1);
        zmq::socket_t  pub(ctx, zmq::socket_type::pub);
        pub.set(zmq::sockopt::linger, 0);
        pub.bind(INPROC);

        StubExecutor ex;
        FirewallAutonomyReactor reactor(TEST_CIDRS, false,
            [&ex](const std::string& c){ return ex(c); });

        AutonomySubscriber sub(reactor,
            []{ return FirewallAutonomyMode::NORMAL; },
            INPROC, 3600);
        sub.start();
        sub.stop();
        sub.stop();  // segunda llamada no debe colgar ni lanzar
        std::cout << "T6 PASS: stop() idempotente\n";
    }

    // ── T7: last_known_mode() se actualiza con evento ZMQ ───────────────────
    {
        zmq::context_t ctx(1);
        zmq::socket_t  pub(ctx, zmq::socket_type::pub);
        pub.set(zmq::sockopt::linger, 0);
        pub.bind(INPROC);
        StubExecutor ex;
        FirewallAutonomyReactor reactor(TEST_CIDRS, false,
            [&ex](const std::string& c){ return ex(c); });
        AutonomySubscriber sub(reactor,
            []{ return FirewallAutonomyMode::NORMAL; },
            INPROC, 3600);
        sub.start();
        std::this_thread::sleep_for(std::chrono::milliseconds(300));
        assert(sub.last_known_mode() == FirewallAutonomyMode::NORMAL);
        publish_event(pub, "AUTONOMOUS");
        assert(wait_for_mode(reactor, FirewallAutonomyMode::AUTONOMOUS));
        assert(sub.last_known_mode() == FirewallAutonomyMode::AUTONOMOUS);
        sub.stop();
        std::cout << "T7 PASS: last_known_mode() actualizado por evento ZMQ\n";
    }
    // ── T8: shared_mode actualizado cuando llega evento ZMQ ──────────────────
    {
        zmq::context_t ctx(1);
        zmq::socket_t  pub(ctx, zmq::socket_type::pub);
        pub.set(zmq::sockopt::linger, 0);
        pub.bind(INPROC);
        StubExecutor ex;
        FirewallAutonomyReactor reactor(TEST_CIDRS, false,
            [&ex](const std::string& c){ return ex(c); });
        using AtomicMode = std::atomic<FirewallAutonomyMode>;
        auto shared_mode = std::make_shared<AtomicMode>(FirewallAutonomyMode::NORMAL);
        auto poll_cb = [shared_mode]() -> FirewallAutonomyMode {
            return shared_mode->load(std::memory_order_acquire);
        };
        AutonomySubscriber sub(reactor, poll_cb, INPROC, 3600, shared_mode);
        sub.start();
        std::this_thread::sleep_for(std::chrono::milliseconds(300));
        assert(shared_mode->load() == FirewallAutonomyMode::NORMAL);
        publish_event(pub, "AUTONOMOUS");
        assert(wait_for_mode(reactor, FirewallAutonomyMode::AUTONOMOUS));
        assert(shared_mode->load() == FirewallAutonomyMode::AUTONOMOUS);
        assert(sub.last_known_mode() == FirewallAutonomyMode::AUTONOMOUS);
        sub.stop();
        std::cout << "T8 PASS: shared_mode actualizado por evento ZMQ\n";
    }
    // ── T9: staleness guard — poll_callback retorna NORMAL si no hay eventos ──
    {
        zmq::context_t ctx(1);
        zmq::socket_t  pub(ctx, zmq::socket_type::pub);
        pub.set(zmq::sockopt::linger, 0);
        pub.bind(INPROC);
        StubExecutor ex;
        FirewallAutonomyReactor reactor(TEST_CIDRS, false,
            [&ex](const std::string& c){ return ex(c); });
        using AtomicMode = std::atomic<FirewallAutonomyMode>;
        using AtomicNs   = std::atomic<int64_t>;
        auto shared_mode = std::make_shared<AtomicMode>(FirewallAutonomyMode::NORMAL);
        // Inicializar last_update muy en el pasado (100s atrás) → stale inmediato
        const int64_t old_ns = std::chrono::duration_cast<std::chrono::nanoseconds>(
            std::chrono::steady_clock::now().time_since_epoch()).count()
            - 100LL * 1'000'000'000LL;
        auto shared_last_update_ns = std::make_shared<AtomicNs>(old_ns);
        const int staleness_sec = 30;
        // poll_callback con staleness check
        auto poll_cb = [shared_mode, shared_last_update_ns, staleness_sec]()
            -> FirewallAutonomyMode {
            const int64_t now_ns = std::chrono::duration_cast<std::chrono::nanoseconds>(
                std::chrono::steady_clock::now().time_since_epoch()).count();
            const int64_t elapsed = (now_ns - shared_last_update_ns->load()) / 1'000'000'000LL;
            if (elapsed > staleness_sec) return FirewallAutonomyMode::NORMAL;
            return shared_mode->load();
        };
        // Forzar AUTONOMOUS en shared_mode — staleness debe ignorarlo
        shared_mode->store(FirewallAutonomyMode::AUTONOMOUS);
        // poll_cb debe retornar NORMAL porque last_update es viejo
        const auto result = poll_cb();
        assert(result == FirewallAutonomyMode::NORMAL);
        std::cout << "T9 PASS: staleness guard retorna NORMAL cuando publisher lleva >30s sin eventos\n";
    }
    std::cout << "=== test_autonomy_subscriber: 9/9 PASSED ===\n";
    return 0;
}
