// sniffer/include/dual_nic_manager.hpp
// Phase 1, Day 7 - Dual-NIC Deployment Manager
#pragma once

#include <string>
#include <vector>
#include <map>
#include <cstdint>
#include <json/json.h>

namespace sniffer {

    // Interface deployment modes (must match eBPF definitions)
    enum class InterfaceMode : uint8_t {
        DISABLED = 0,
        HOST_BASED = 1,   // Capture only traffic destined to this host
        GATEWAY = 2       // Capture ALL transit traffic (inline inspection)
    };

    // Interface configuration
    struct InterfaceConfig {
        std::string name;           // "eth0", "eth1"
        uint32_t ifindex;           // Network interface index
        InterfaceMode mode;         // Host-based or Gateway
        bool is_wan;                // true=WAN-facing, false=LAN-facing
        std::string role;           // "wan" or "lan"
        std::string description;
    };

    class DualNICManager {
    public:
        explicit DualNICManager(const Json::Value& config);
        ~DualNICManager() = default;

        // Initialize and configure interfaces
        void initialize();
        void configure_bpf_map(int interface_configs_fd);

        // Getters
        const std::vector<InterfaceConfig>& get_interfaces() const { return interfaces_; }
        InterfaceConfig get_interface_by_name(const std::string& name) const;
        bool is_dual_mode() const { return deployment_mode_ == "dual"; }
        std::string get_deployment_mode() const { return deployment_mode_; }

        // Network setup (optional - for gateway mode)
        void enable_ip_forwarding();
        void setup_nat_rules();

        // Validation
        bool validate_interfaces();

    private:
        std::string deployment_mode_;  // "host-only", "gateway-only", "dual"
        std::vector<InterfaceConfig> interfaces_;
        Json::Value config_;

        // Helpers
        uint32_t get_interface_index(const std::string& iface_name);
        void parse_deployment_config();
        void log_configuration() const;
    };

} // namespace sniffer