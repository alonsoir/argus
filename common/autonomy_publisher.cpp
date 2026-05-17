// ============================================================================
// autonomy_publisher.cpp — DEBT-AUTONOMY-ZMQ-EVENTS-001 (DAY 155)
// ============================================================================
#include "autonomy_publisher.h"
#include <chrono>
#include <iostream>
#include <sstream>

namespace ml_defender::common {

AutonomyPublisher::AutonomyPublisher(
        std::string endpoint,
        std::string component,
        int linger_ms)
    : endpoint_(std::move(endpoint))
    , component_(std::move(component))
    , context_(1)
    , socket_(context_, zmq::socket_type::pub)
{
    socket_.set(zmq::sockopt::linger, linger_ms);
    socket_.bind(endpoint_);
    std::cerr << "[autonomy_publisher] PUB bound to " << endpoint_ << "\n";
}

AutonomyPublisher::~AutonomyPublisher() {
    try { socket_.close(); } catch (...) {}
    try { context_.close(); } catch (...) {}
}

void AutonomyPublisher::publish(ml_defender::OperationalMode from,
                                 ml_defender::OperationalMode to) {
    const auto now_ns = std::chrono::duration_cast<std::chrono::nanoseconds>(
        std::chrono::system_clock::now().time_since_epoch()
    ).count();

    std::ostringstream payload;
    payload << "{"
            << "\"state\":\""        << operational_mode_str(to)   << "\","
            << "\"from\":\""         << operational_mode_str(from)  << "\","
            << "\"timestamp_utc_ns\":" << now_ns                   << ","
            << "\"component\":\""    << component_                  << "\""
            << "}";

    const std::string p = payload.str();

    try {
        socket_.send(zmq::message_t(TOPIC, std::strlen(TOPIC)),
                     zmq::send_flags::sndmore);
        socket_.send(zmq::message_t(p.data(), p.size()),
                     zmq::send_flags::none);
        std::cerr << "[autonomy_publisher] → "
                  << operational_mode_str(from) << " → "
                  << operational_mode_str(to)   << "\n";
    } catch (const zmq::error_t& e) {
        std::cerr << "[autonomy_publisher] ERROR send: " << e.what() << "\n";
    }
}

ml_defender::CryptoAutonomyStateMachine<>::TransitionCallback
AutonomyPublisher::make_callback() {
    return [this](ml_defender::OperationalMode from,
                  ml_defender::OperationalMode to) {
        this->publish(from, to);
    };
}

} // namespace ml_defender::common
