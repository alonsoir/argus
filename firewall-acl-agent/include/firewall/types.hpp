#pragma once

#include <string>
#include <chrono>
#include <cstdint>

namespace firewall {

enum class Action {
    ACCEPT,
    DROP,
    REJECT,
    LOG
};

enum class Protocol {
    TCP,
    UDP,
    ICMP,
    ALL
};

struct IPAddress {
    std::string address;
    uint32_t cidr_mask = 32;
    
    [[nodiscard]] std::string to_string() const {
        return address + "/" + std::to_string(cidr_mask);
    }
};

struct Rule {
    std::string id;
    IPAddress source_ip;
    IPAddress dest_ip;
    uint16_t source_port = 0;
    uint16_t dest_port = 0;
    Protocol protocol = Protocol::ALL;
    Action action = Action::DROP;
    std::chrono::seconds duration{0};
    std::chrono::system_clock::time_point created_at;
    std::string reason;
    bool temporal = false;
    
    [[nodiscard]] bool is_expired() const {
        if (!temporal || duration.count() == 0) {
            return false;
        }
        auto now = std::chrono::system_clock::now();
        return (now - created_at) > duration;
    }
};

struct Detection {
    std::string type;  // "DDOS", "RANSOMWARE", "SUSPICIOUS"
    IPAddress source_ip;
    uint16_t source_port;
    float confidence;
    std::string details;
};

} // namespace firewall
