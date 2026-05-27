#pragma once
// ============================================================================
// autonomy_publisher.h — DEBT-AUTONOMY-ZMQ-EVENTS-001 (DAY 155)
// ============================================================================
// Publica eventos de transición de CryptoAutonomyStateMachine via ZMQ PUB.
// Se pasa como TransitionCallback al constructor de CryptoAutonomyStateMachine.
//
// Uso:
//   auto pub = std::make_shared<AutonomyPublisher>("ipc:///run/argus/autonomy.sock");
//   CryptoAutonomy sm("firewall", pub->make_callback());
//
// Payload JSON:
//   {"state":"AUTONOMOUS","from":"NORMAL","timestamp_utc_ns":...,"component":"..."}
//
// Topic: argus.crypto.autonomy
// Transport: ipc:///run/argus/autonomy.sock (procesos separados)
// ============================================================================
#include <zmq.hpp>
#include <string>
#include <functional>
#include "crypto_autonomy.h"

namespace ml_defender::common {

class AutonomyPublisher {
public:
    static constexpr const char* TOPIC            = "argus.crypto.autonomy";
    static constexpr const char* DEFAULT_ENDPOINT = "ipc:///run/argus/autonomy.sock";

    explicit AutonomyPublisher(
        std::string endpoint  = DEFAULT_ENDPOINT,
        std::string component = "unknown",
        int linger_ms         = 0
    );

    ~AutonomyPublisher();

    AutonomyPublisher(const AutonomyPublisher&)            = delete;
    AutonomyPublisher& operator=(const AutonomyPublisher&) = delete;
    AutonomyPublisher(AutonomyPublisher&&)                 = default;
    AutonomyPublisher& operator=(AutonomyPublisher&&)      = default;

    // Devuelve TransitionCallback listo para CryptoAutonomyStateMachine.
    ml_defender::CryptoAutonomyStateMachine<>::TransitionCallback make_callback();

    // Publicación directa — también usable desde tests.
    void publish(ml_defender::OperationalMode from,
                 ml_defender::OperationalMode to);

    const std::string& endpoint() const noexcept { return endpoint_; }

private:
    std::string    endpoint_;
    std::string    component_;
    zmq::context_t context_;
    zmq::socket_t  socket_;
};

} // namespace ml_defender::common
