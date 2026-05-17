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

    std::cout << "=== test_autonomy_subscriber: 6/6 PASSED ===\n";
    return 0;
}
