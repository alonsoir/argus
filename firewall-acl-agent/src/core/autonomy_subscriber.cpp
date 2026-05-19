// ============================================================================
// autonomy_subscriber.cpp — DEBT-AUTONOMY-ZMQ-EVENTS-001 (DAY 155)
// ============================================================================
#include "firewall/autonomy_subscriber.hpp"
#include <chrono>
#include <iostream>
#include <string>

namespace mldefender::firewall {

AutonomySubscriber::AutonomySubscriber(
        FirewallAutonomyReactor& reactor,
        PollCallback             poll_cb,
        std::string              endpoint,
        int                      reconcile_interval_sec,
        std::shared_ptr<std::atomic<FirewallAutonomyMode>> shared_mode,
        std::shared_ptr<std::atomic<int64_t>> shared_last_update_ns,
        int                      staleness_timeout_sec)
    : reactor_(reactor)
    , poll_cb_(std::move(poll_cb))
    , endpoint_(std::move(endpoint))
    , reconcile_interval_sec_(reconcile_interval_sec)
    , shared_mode_(std::move(shared_mode))
    , shared_last_update_ns_(std::move(shared_last_update_ns))
    , staleness_timeout_sec_(staleness_timeout_sec)
    , context_(1)
    , socket_(context_, zmq::socket_type::sub)
{
    socket_.set(zmq::sockopt::rcvtimeo,          RECV_TIMEOUT_MS);
    socket_.set(zmq::sockopt::linger,            0);
    socket_.set(zmq::sockopt::rcvhwm,            1000);   // conservador — canal control
    socket_.set(zmq::sockopt::reconnect_ivl,     100);    // 100ms base
    socket_.set(zmq::sockopt::reconnect_ivl_max, 5000);   // 5s max
    socket_.set(zmq::sockopt::subscribe,         TOPIC);
    socket_.connect(endpoint_);
    std::cerr << "[autonomy_subscriber] SUB connected to " << endpoint_ << "\n";
}

AutonomySubscriber::~AutonomySubscriber() {
    stop();
}

void AutonomySubscriber::start() {
    if (running_.exchange(true)) return;  // ya arrancado
    thread_ = std::thread([this]{ run(); });
}

void AutonomySubscriber::stop() {
    running_.store(false);
    if (thread_.joinable()) thread_.join();
}

void AutonomySubscriber::run() {
    std::cerr << "[autonomy_subscriber] loop arrancado\n";

    auto last_reconcile = std::chrono::steady_clock::now();

    while (running_.load()) {
        // ── 1. Recibir frame de topic ─────────────────────────────────────
        zmq::message_t topic_frame;
        const auto rc = socket_.recv(topic_frame, zmq::recv_flags::none);

        if (!rc) {
            // EAGAIN — timeout, sin mensaje. Comprobar reconciliador.
        } else {
            // ── 2. Recibir frame de payload ───────────────────────────────
            zmq::message_t payload_frame;
            if (socket_.recv(payload_frame, zmq::recv_flags::none)) {
                const std::string payload(
                    static_cast<char*>(payload_frame.data()),
                    payload_frame.size()
                );
                handle_message(payload);
                last_event_ns_.store(
                    std::chrono::duration_cast<std::chrono::nanoseconds>(
                        std::chrono::system_clock::now().time_since_epoch()
                    ).count()
                );
            }
        }

        // ── 3. Reconciliador — safety net cada reconcile_interval_sec ─────
        const auto now = std::chrono::steady_clock::now();
        const auto elapsed = std::chrono::duration_cast<std::chrono::seconds>(
            now - last_reconcile).count();

        if (elapsed >= reconcile_interval_sec_) {
            last_reconcile = now;
            if (poll_cb_) {
                const auto polled_mode = poll_cb_();
                std::cerr << "[autonomy_subscriber] reconcile → "
                          << autonomy_mode_str(polled_mode) << "\n";
                last_known_mode_.store(polled_mode, std::memory_order_release);
                if (shared_mode_) shared_mode_->store(polled_mode, std::memory_order_release);
                reactor_.set_mode(polled_mode);
            }
        }
    }

    std::cerr << "[autonomy_subscriber] loop detenido\n";
}

void AutonomySubscriber::handle_message(const std::string& payload) {
    const auto mode = parse_state(payload);
    std::cerr << "[autonomy_subscriber] evento → "
              << autonomy_mode_str(mode) << " payload=" << payload << "\n";
    last_known_mode_.store(mode, std::memory_order_release);
    if (shared_mode_) shared_mode_->store(mode, std::memory_order_release);
    // STALENESS GUARD: actualizar timestamp de último evento recibido
    const int64_t now_ns = std::chrono::duration_cast<std::chrono::nanoseconds>(
        std::chrono::steady_clock::now().time_since_epoch()).count();
    if (shared_last_update_ns_) shared_last_update_ns_->store(now_ns, std::memory_order_release);
    reactor_.set_mode(mode);
}

FirewallAutonomyMode AutonomySubscriber::parse_state(
        const std::string& payload) const {
    // Parser JSON mínimo — busca "state":"VALOR"
    // Sin dependencia de jsoncpp en este módulo.
    const auto key = std::string("\"state\":\"");
    const auto pos = payload.find(key);
    if (pos == std::string::npos) {
        std::cerr << "[autonomy_subscriber] WARN: campo 'state' no encontrado"
                     " — fallback NORMAL\n";
        return FirewallAutonomyMode::NORMAL;
    }
    const auto start = pos + key.size();
    const auto end   = payload.find('"', start);
    if (end == std::string::npos) return FirewallAutonomyMode::NORMAL;

    const auto state = payload.substr(start, end - start);

    if (state == "AUTONOMOUS")  return FirewallAutonomyMode::AUTONOMOUS;
    if (state == "DEGRADED")    return FirewallAutonomyMode::DEGRADED;
    if (state == "RECONCILING") return FirewallAutonomyMode::NORMAL;  // Vault recuperado
    return FirewallAutonomyMode::NORMAL;
}

} // namespace mldefender::firewall
