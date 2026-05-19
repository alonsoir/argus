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
#include <memory>
#include <string>
#include <chrono>
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
        std::string              endpoint               = DEFAULT_ENDPOINT,
        int                      reconcile_interval_sec = 90,
        std::shared_ptr<std::atomic<FirewallAutonomyMode>> shared_mode = nullptr,
        std::shared_ptr<std::atomic<int64_t>> shared_last_update_ns = nullptr,
        int                      staleness_timeout_sec  = 30
    );

    ~AutonomySubscriber();

    AutonomySubscriber(const AutonomySubscriber&)            = delete;
    AutonomySubscriber& operator=(const AutonomySubscriber&) = delete;

    // Arranca el loop en un hilo dedicado.
    void start();

    // Detiene el loop y espera a que el hilo termine.
    void stop();

    bool is_running() const noexcept { return running_.load(); }

    // DEBT-CRYPTO-RECONCILIATION-001: modo conocido vía ZMQ + reconciliador.
    // Consultable desde poll_callback en main.cpp sin segundo socket.
    FirewallAutonomyMode last_known_mode() const noexcept {
        return last_known_mode_.load(std::memory_order_acquire);
    }

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

    // DEBT-CRYPTO-RECONCILIATION-001 (DAY 157)
    // Compartido con poll_callback via shared_ptr para resolver ordering.
    // Declarado antes de context_/socket_ para respetar orden de inicialización.
    std::shared_ptr<std::atomic<FirewallAutonomyMode>> shared_mode_;
    // STALENESS GUARD (DAY 157 — B1 post-Consejo)
    // Nanosegundos steady_clock del último evento ZMQ recibido.
    // poll_callback comprueba: si now - last_update > staleness_timeout → NORMAL.
    std::shared_ptr<std::atomic<int64_t>> shared_last_update_ns_;
    int                                  staleness_timeout_sec_;

    zmq::context_t           context_;
    zmq::socket_t            socket_;

    std::atomic<bool>        running_{false};
    std::thread              thread_;

    // Reconciliador: timestamp de último evento recibido
    std::atomic<int64_t>     last_event_ns_{0};

    // Último modo conocido — actualizado por ZMQ events y reconciliador.
    // Sin segundo socket. Feature flag use_dedicated_health_channel=false.
    std::atomic<FirewallAutonomyMode> last_known_mode_{FirewallAutonomyMode::NORMAL};
};

} // namespace mldefender::firewall
