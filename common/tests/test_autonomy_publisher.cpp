// test_autonomy_publisher.cpp — DEBT-AUTONOMY-ZMQ-EVENTS-001 (DAY 155)
// Tests del AutonomyPublisher — verifica payload y topic ZMQ
//
// DAY 218 — DEBT-TEST-AUTONOMY-PUBLISHER-FLAKY-001
// ─────────────────────────────────────────────────────────────────────────────
// El test original fallaba ~1/20 veces en T3. Dos causas, ambas reales:
//
//   1. VIOLABA LA REGLA DEL PROYECTO: el SUB hacia connect() ANTES de que el
//      PUB hiciera bind(). Sobre ipc://, connect() a un path inexistente no
//      falla: entra en bucle de reconexion (ZMQ_RECONNECT_IVL = 100ms).
//      El sleep(300ms) era una apuesta a que cabian 3 reintentos.
//
//   2. EL SLEEP NO ES UNA SINCRONIZACION. Aun con el connect() resuelto, la
//      suscripcion tarda en propagarse al PUB por el pipe de comandos. Hasta
//      que llega, el PUB descarta en silencio (no encola para suscriptores
//      que aun no conoce). No hay sleep correcto, solo sleeps afortunados.
//
// Por que fallaba T3 y no T1/T2/T4: en T1/T2/T4 el publish() es una llamada
// directa, repetible. En T3 el mensaje es efecto colateral de una transicion
// de estado (NORMAL -> AUTONOMOUS) que es IDEMPOTENTE: solo dispara una vez.
// Si ese unico mensaje cae en la ventana ciega, no hay segunda oportunidad.
// T3 no era mas fragil por azar: era el unico caso SIN REINTENTO POSIBLE.
// Los otros tres llevaban la misma bomba dentro.
//
// ARREGLO: bind() antes de connect(), y handshake real (sync_pub_sub) en vez
// de sleep. Publicamos warm-ups hasta que el SUB confirma recepcion, y
// entonces drenamos. Sin constantes magicas, sin apuestas.
// ─────────────────────────────────────────────────────────────────────────────
#include "autonomy_publisher.h"
#include "crypto_autonomy.h"
#include <zmq.hpp>
#include <cassert>
#include <chrono>
#include <cstdio>
#include <iostream>
#include <string>
#include <unistd.h>   // ::unlink

using namespace ml_defender::common;
using namespace ml_defender;

static const std::string ENDPOINT  = "ipc:///tmp/test-autonomy-publisher.sock";
static const char*       SOCK_PATH = "/tmp/test-autonomy-publisher.sock";

// ─── Recibe dos frames (topic + payload) con timeout ─────────────────────────
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

// ─── HANDSHAKE REAL — sustituye al sleep(300ms) ──────────────────────────────
//
// Publica transiciones de warm-up hasta que el SUB confirme que la suscripcion
// se ha propagado. Luego drena la cola: ZMQ garantiza orden FIFO por par de
// sockets, asi que una vez el canal queda en silencio, no hay warm-ups en
// vuelo y el siguiente mensaje que llegue sera el del test.
//
// NOTA: el warm-up usa una transicion REAL (DEGRADED -> NORMAL). No usamos
// NORMAL -> NORMAL por si publish() filtrase transiciones triviales.
static void sync_pub_sub(AutonomyPublisher& pub, zmq::socket_t& sub) {
    const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(5);
    std::string t, p;

    while (std::chrono::steady_clock::now() < deadline) {
        pub.publish(OperationalMode::DEGRADED, OperationalMode::NORMAL);  // warm-up
        if (recv_two(sub, t, p, 50)) {
            // Confirmado. Drenar hasta que el canal quede en silencio.
            while (recv_two(sub, t, p, 100)) { /* descartar warm-ups restantes */ }
            return;
        }
    }
    std::fprintf(stderr, "sync_pub_sub: la suscripcion nunca se propago (5s)\n");
    assert(false && "sync_pub_sub: timeout — el SUB nunca recibio el warm-up");
}

// ─── Fixture: bind() ANTES de connect(), sin estado heredado ─────────────────
//
// El socket ipc:// persiste en el filesystem entre ejecuciones. Lo borramos
// para no heredar estado de un run anterior.
struct Fixture {
    zmq::context_t     ctx;
    AutonomyPublisher  pub;      // 1. BIND primero (el ctor hace bind)
    zmq::socket_t      sub;

    explicit Fixture(const std::string& component)
        : ctx(1)
        , pub((::unlink(SOCK_PATH), ENDPOINT), component, 0)   // unlink, luego bind
        , sub(ctx, zmq::socket_type::sub)
    {
        sub.set(zmq::sockopt::linger, 0);
        sub.set(zmq::sockopt::subscribe, AutonomyPublisher::TOPIC);
        sub.connect(ENDPOINT);                                 // 2. CONNECT despues
        sync_pub_sub(pub, sub);                                // 3. Handshake, no sleep
    }
};

int main() {
    // ── T1: publish() emite topic correcto ───────────────────────────────────
    {
        Fixture fx("test-component");

        fx.pub.publish(OperationalMode::NORMAL, OperationalMode::AUTONOMOUS);

        std::string topic, payload;
        assert(recv_two(fx.sub, topic, payload));
        assert(topic == AutonomyPublisher::TOPIC);
        // Reforzado: sin esto, un warm-up superviviente pasaria T1 en falso.
        assert(payload.find("\"state\":\"AUTONOMOUS\"") != std::string::npos);
        std::cout << "T1 PASS: topic correcto — " << topic << "\n";
    }

    // ── T2: payload contiene state AUTONOMOUS ────────────────────────────────
    {
        Fixture fx("test-component");

        fx.pub.publish(OperationalMode::NORMAL, OperationalMode::AUTONOMOUS);

        std::string topic, payload;
        assert(recv_two(fx.sub, topic, payload));
        assert(payload.find("\"state\":\"AUTONOMOUS\"") != std::string::npos);
        assert(payload.find("\"from\":\"NORMAL\"")      != std::string::npos);
        assert(payload.find("\"component\":\"test-component\"") != std::string::npos);
        assert(payload.find("\"timestamp_utc_ns\":")    != std::string::npos);
        std::cout << "T2 PASS: payload contiene campos correctos\n";
    }

    // ── T3: make_callback() integra con CryptoAutonomyStateMachine ───────────
    //
    // EL CASO QUE FALLABA. El mensaje es efecto colateral de la transicion de
    // la SM: idempotente, dispara UNA vez, sin reintento posible. Con el
    // handshake hecho, la suscripcion ya esta propagada cuando la SM transita.
    {
        Fixture fx("vault-daemon");

        CryptoAutonomyStateMachine<> sm("vault-daemon", fx.pub.make_callback());
        sm.on_vault_unreachable();  // NORMAL → AUTONOMOUS

        std::string topic, payload;
        assert(recv_two(fx.sub, topic, payload));
        assert(topic == AutonomyPublisher::TOPIC);
        assert(payload.find("\"state\":\"AUTONOMOUS\"") != std::string::npos);
        assert(payload.find("\"from\":\"NORMAL\"")      != std::string::npos);
        assert(payload.find("\"component\":\"vault-daemon\"") != std::string::npos);
        std::cout << "T3 PASS: make_callback() publica en transición de SM\n";
    }

    // ── T4: payload DEGRADED correcto ────────────────────────────────────────
    {
        Fixture fx("test-component");

        fx.pub.publish(OperationalMode::AUTONOMOUS, OperationalMode::DEGRADED);

        std::string topic, payload;
        assert(recv_two(fx.sub, topic, payload));
        assert(payload.find("\"state\":\"DEGRADED\"")   != std::string::npos);
        assert(payload.find("\"from\":\"AUTONOMOUS\"")  != std::string::npos);
        std::cout << "T4 PASS: payload DEGRADED correcto\n";
    }

    std::cout << "=== test_autonomy_publisher: 4/4 PASSED ===\n";
    return 0;
}