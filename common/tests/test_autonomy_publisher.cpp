// test_autonomy_publisher.cpp — DEBT-AUTONOMY-ZMQ-EVENTS-001 (DAY 155)
// Tests del AutonomyPublisher — verifica payload y topic ZMQ
#include "autonomy_publisher.h"
#include "crypto_autonomy.h"
#include <zmq.hpp>
#include <cassert>
#include <chrono>
#include <iostream>
#include <string>
#include <thread>

using namespace ml_defender::common;
using namespace ml_defender;

static const std::string INPROC = "ipc:///tmp/test-autonomy-publisher.sock";

// Recibe dos frames (topic + payload) con timeout
static bool recv_two(zmq::socket_t& sub,
                     std::string& topic_out,
                     std::string& payload_out,
                     int timeout_ms = 500) {
    sub.set(zmq::sockopt::rcvtimeo, timeout_ms);
    zmq::message_t t, p;
    if (!sub.recv(t)) return false;
    if (!sub.recv(p)) return false;
    topic_out   = std::string(static_cast<char*>(t.data()), t.size());
    payload_out = std::string(static_cast<char*>(p.data()), p.size());
    return true;
}

int main() {
    // ── T1: publish() emite topic correcto ───────────────────────────────────
    {
        zmq::context_t ctx(1);
        zmq::socket_t  sub(ctx, zmq::socket_type::sub);
        sub.set(zmq::sockopt::linger, 0);
        sub.set(zmq::sockopt::subscribe, AutonomyPublisher::TOPIC);
        sub.connect(INPROC);

        AutonomyPublisher pub(INPROC, "test-component", 0);
        std::this_thread::sleep_for(std::chrono::milliseconds(300));

        pub.publish(OperationalMode::NORMAL, OperationalMode::AUTONOMOUS);

        std::string topic, payload;
        assert(recv_two(sub, topic, payload));
        assert(topic == AutonomyPublisher::TOPIC);
        std::cout << "T1 PASS: topic correcto — " << topic << "\n";
    }
    // ── T2: payload contiene state AUTONOMOUS ────────────────────────────────
    {
        zmq::context_t ctx(1);
        zmq::socket_t  sub(ctx, zmq::socket_type::sub);
        sub.set(zmq::sockopt::linger, 0);
        sub.set(zmq::sockopt::subscribe, AutonomyPublisher::TOPIC);
        sub.connect(INPROC);

        AutonomyPublisher pub(INPROC, "test-component", 0);
        std::this_thread::sleep_for(std::chrono::milliseconds(300));

        pub.publish(OperationalMode::NORMAL, OperationalMode::AUTONOMOUS);

        std::string topic, payload;
        assert(recv_two(sub, topic, payload));
        assert(payload.find("\"state\":\"AUTONOMOUS\"") != std::string::npos);
        assert(payload.find("\"from\":\"NORMAL\"")      != std::string::npos);
        assert(payload.find("\"component\":\"test-component\"") != std::string::npos);
        assert(payload.find("\"timestamp_utc_ns\":")    != std::string::npos);
        std::cout << "T2 PASS: payload contiene campos correctos\n";
    }
    // ── T3: make_callback() integra con CryptoAutonomyStateMachine ───────────
    {
        zmq::context_t ctx(1);
        zmq::socket_t  sub(ctx, zmq::socket_type::sub);
        sub.set(zmq::sockopt::linger, 0);
        sub.set(zmq::sockopt::subscribe, AutonomyPublisher::TOPIC);
        sub.connect(INPROC);

        AutonomyPublisher pub(INPROC, "vault-daemon", 0);
        std::this_thread::sleep_for(std::chrono::milliseconds(300));

        CryptoAutonomyStateMachine<> sm("vault-daemon", pub.make_callback());
        sm.on_vault_unreachable();  // NORMAL → AUTONOMOUS

        std::string topic, payload;
        assert(recv_two(sub, topic, payload));
        assert(payload.find("\"state\":\"AUTONOMOUS\"") != std::string::npos);
        std::cout << "T3 PASS: make_callback() publica en transición de SM\n";
    }
    // ── T4: payload DEGRADED correcto ────────────────────────────────────────
    {
        zmq::context_t ctx(1);
        zmq::socket_t  sub(ctx, zmq::socket_type::sub);
        sub.set(zmq::sockopt::linger, 0);
        sub.set(zmq::sockopt::subscribe, AutonomyPublisher::TOPIC);
        sub.connect(INPROC);

        AutonomyPublisher pub(INPROC, "test-component", 0);
        std::this_thread::sleep_for(std::chrono::milliseconds(300));

        pub.publish(OperationalMode::AUTONOMOUS, OperationalMode::DEGRADED);

        std::string topic, payload;
        assert(recv_two(sub, topic, payload));
        assert(payload.find("\"state\":\"DEGRADED\"")   != std::string::npos);
        assert(payload.find("\"from\":\"AUTONOMOUS\"")  != std::string::npos);
        std::cout << "T4 PASS: payload DEGRADED correcto\n";
    }

    std::cout << "=== test_autonomy_publisher: 4/4 PASSED ===\n";
    return 0;
}
