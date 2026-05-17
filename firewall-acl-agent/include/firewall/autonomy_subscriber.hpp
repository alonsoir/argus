#pragma once
// ============================================================================
// autonomy_subscriber.hpp — DEBT-AUTONOMY-ZMQ-EVENTS-001 (DAY 155)
// ============================================================================
// Suscribe a eventos ZMQ PUB de CryptoAutonomyStateMachine y llama
// FirewallAutonomyReactor::set_mode() en cada transición.
//
// Mecanismo principal: ZMQ SUB (event-driven)
// Safety net:          polling reconciliador cada reconcile_interval_sec
//
// Topic: argus.crypto.autonomy
// Transport: ipc:///run/argus/autonomy.sock
//
// Payload JSON esperado:
//   {"state":"AUTONOMOUS","from":"NORMAL","timestamp_utc_ns":...,"component":"..."}
// ============================================================================
#include "firewall/autonomy_reactor.hpp"
#include <zmq.hpp>
#include <atomic>
#include <functional>
#include <string>
#include <thread>

namespace mldefender::firewall {

class AutonomySubscriber {
public:
    static constexpr const char* TOPIC            = "argus.crypto.autonomy";
    static constexpr const char* DEFAULT_ENDPOINT = "ipc:///run/argus/autonomy.sock";
    static constexpr int         RECV_TIMEOUT_MS  = 1000;  // para parada limpia

    // poll_callback: consultado por el reconciliador para obtener el modo actual.
    // En producción llama al health-check de Vault/etcd.
    // En tests: lambda inyectable.
    using PollCallback = std::function<FirewallAutonomyMode()>;

    explicit AutonomySubscriber(
        FirewallAutonomyReactor& reactor,
        PollCallback             poll_cb,
        std::string              endpoint            = DEFAULT_ENDPOINT,
        int                      reconcile_interval_sec = 90
    );

    ~AutonomySubscriber();

    AutonomySubscriber(const AutonomySubscriber&)            = delete;
    AutonomySubscriber& operator=(const AutonomySubscriber&) = delete;

    // Arranca el loop en un hilo dedicado.
    void start();

    // Detiene el loop y espera a que el hilo termine.
    void stop();

    bool is_running() const noexcept { return running_.load(); }

    // Acceso para tests
    const std::string& endpoint() const noexcept { return endpoint_; }

private:
    void run();
    void handle_message(const std::string& payload);
    FirewallAutonomyMode parse_state(const std::string& payload) const;

    FirewallAutonomyReactor& reactor_;
    PollCallback             poll_cb_;
    std::string              endpoint_;
    int                      reconcile_interval_sec_;

    zmq::context_t           context_;
    zmq::socket_t            socket_;

    std::atomic<bool>        running_{false};
    std::thread              thread_;

    // Reconciliador: timestamp de último evento recibido
    std::atomic<int64_t>     last_event_ns_{0};
};

} // namespace mldefender::firewall
