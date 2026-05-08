// sniffer/src/userspace/dual_nic_manager.cpp
#include "dual_nic_manager.hpp"
#include <iostream>
#include <stdexcept>
#include <cstring>
#include <net/if.h>
#include <sys/ioctl.h>
#include <unistd.h>
#include <bpf/bpf.h>

namespace sniffer {

struct bpf_interface_config {
    uint32_t ifindex;
    uint8_t mode;
    uint8_t is_wan;
    uint8_t reserved[2];
};

DualNICManager::DualNICManager(const Json::Value& config)
    : deployment_mode_("host-only")
    , config_(config) {
}

void DualNICManager::initialize() {
    std::cout << "[DualNICManager] Initializing..." << std::endl;
    parse_deployment_config();
    if (!validate_interfaces()) {
        throw std::runtime_error("Interface validation failed");
    }
    log_configuration();
    std::cout << "[DualNICManager] ✅ Initialized successfully" << std::endl;
}

void DualNICManager::parse_deployment_config() {
    if (!config_.isMember("deployment")) {
        std::cout << "[DualNICManager] No deployment config, using legacy single-interface mode" << std::endl;

        if (config_.isMember("profiles") && config_.isMember("profile")) {
            std::string active_profile = config_["profile"].asString();
            if (config_["profiles"].isMember(active_profile)) {
                std::string iface = config_["profiles"][active_profile]["capture_interface"].asString();

                InterfaceConfig ic;
                ic.name = iface;
                ic.ifindex = get_interface_index(iface);
                ic.mode = InterfaceMode::HOST_BASED;
                ic.is_wan = true;
                ic.role = "wan";
                ic.description = "Legacy single-interface mode";

                interfaces_.push_back(ic);
                deployment_mode_ = "host-only";
            }
        }
        return;
    }

    auto& deployment = config_["deployment"];

    if (deployment.isMember("mode")) {
        deployment_mode_ = deployment["mode"].asString();
    }

    std::cout << "[DualNICManager] Deployment mode: " << deployment_mode_ << std::endl;

    if (deployment.isMember("host_interface")) {
        auto& host_if = deployment["host_interface"];

        InterfaceConfig ic;
        ic.name = host_if["name"].asString();
        ic.ifindex = get_interface_index(ic.name);
        ic.mode = InterfaceMode::HOST_BASED;
        ic.is_wan = (host_if["role"].asString() == "wan");
        ic.role = host_if["role"].asString();
        ic.description = host_if["description"].asString();

        interfaces_.push_back(ic);
    }

    if ((deployment_mode_ == "dual" || deployment_mode_ == "gateway-only") &&
        deployment.isMember("gateway_interface")) {

        auto& gateway_if = deployment["gateway_interface"];

        InterfaceConfig ic;
        ic.name = gateway_if["name"].asString();
        ic.ifindex = get_interface_index(ic.name);
        ic.mode = InterfaceMode::GATEWAY;
        ic.is_wan = (gateway_if["role"].asString() == "wan");
        ic.role = gateway_if["role"].asString();
        ic.description = gateway_if["description"].asString();

        interfaces_.push_back(ic);
    }
}

void DualNICManager::configure_bpf_map(int iface_configs_fd) {
    if (iface_configs_fd < 0) {
        throw std::runtime_error("Invalid BPF map file descriptor");
    }

    std::cout << "[DualNICManager] Configuring BPF iface_configs map..." << std::endl;

    for (const auto& iface : interfaces_) {
        bpf_interface_config kern_config = {
            .ifindex = iface.ifindex,
            .mode = static_cast<uint8_t>(iface.mode),
            .is_wan = iface.is_wan ? uint8_t(1) : uint8_t(0),
            .reserved = {0, 0}
        };

        int ret = bpf_map_update_elem(iface_configs_fd,
                                       &iface.ifindex,
                                       &kern_config,
                                       BPF_ANY);

        if (ret != 0) {
            std::cerr << "[ERROR] Failed to update BPF map for " << iface.name
                      << ": " << strerror(errno) << std::endl;
            throw std::runtime_error("BPF map update failed");
        }

        std::cout << "  ✅ Configured " << iface.name
                  << " (ifindex=" << iface.ifindex
                  << ", mode=" << (iface.mode == InterfaceMode::HOST_BASED ? "host-based" : "gateway")
                  << ", wan=" << iface.is_wan << ")" << std::endl;
    }

    std::cout << "[DualNICManager] ✅ BPF map configured successfully" << std::endl;
}

uint32_t DualNICManager::get_interface_index(const std::string& iface_name) {
    uint32_t ifindex = if_nametoindex(iface_name.c_str());

    if (ifindex == 0) {
        std::cerr << "[ERROR] Interface " << iface_name << " not found" << std::endl;
        throw std::runtime_error("Interface not found: " + iface_name);
    }

    return ifindex;
}

bool DualNICManager::validate_interfaces() {
    if (interfaces_.empty()) {
        std::cerr << "[ERROR] No interfaces configured" << std::endl;
        return false;
    }

    for (const auto& iface : interfaces_) {
        if (iface.ifindex == 0) {
            std::cerr << "[ERROR] Invalid ifindex for " << iface.name << std::endl;
            return false;
        }

        int sock = socket(AF_INET, SOCK_DGRAM, 0);
        if (sock < 0) continue;

        struct ifreq ifr;
        std::strncpy(ifr.ifr_name, iface.name.c_str(), IFNAMSIZ - 1);

        if (ioctl(sock, SIOCGIFFLAGS, &ifr) == 0) {
            if (!(ifr.ifr_flags & IFF_UP)) {
                std::cout << "[WARNING] Interface " << iface.name << " is DOWN" << std::endl;
            }
        }

        close(sock);
    }

    return true;
}

InterfaceConfig DualNICManager::get_interface_by_name(const std::string& name) const {
    for (const auto& iface : interfaces_) {
        if (iface.name == name) {
            return iface;
        }
    }
    throw std::runtime_error("Interface not found: " + name);
}

void DualNICManager::enable_ip_forwarding() {
    if (deployment_mode_ != "dual" && deployment_mode_ != "gateway-only") {
        std::cout << "[DualNICManager] IP forwarding not needed for " << deployment_mode_ << std::endl;
        return;
    }

    std::cout << "[DualNICManager] Enabling IP forwarding..." << std::endl;

    int ret = system("sysctl -w net.ipv4.ip_forward=1 > /dev/null 2>&1");
    if (ret == 0) {
        std::cout << "  ✅ IPv4 forwarding enabled" << std::endl;
    } else {
        std::cerr << "  ⚠️  Failed to enable IPv4 forwarding (may need sudo)" << std::endl;
    }

    ret = system("sysctl -w net.ipv6.conf.all.forwarding=1 > /dev/null 2>&1");
    if (ret == 0) {
        std::cout << "  ✅ IPv6 forwarding enabled" << std::endl;
    }
}

void DualNICManager::setup_nat_rules() {
    auto& deployment = config_["deployment"];

    if (!deployment.isMember("network_settings") ||
        !deployment["network_settings"]["enable_nat"].asBool()) {
        std::cout << "[DualNICManager] NAT disabled in configuration" << std::endl;
        return;
    }

    std::cout << "[DualNICManager] Setting up NAT rules..." << std::endl;
    std::cout << "  ⚠️  NAT setup requires manual iptables configuration" << std::endl;
    std::cout << "  Example:" << std::endl;
    std::cout << "    iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE" << std::endl;
}

void DualNICManager::log_configuration() const {
    std::cout << "\n╔════════════════════════════════════════════════════════════╗\n";
    std::cout << "║  Dual-NIC Deployment Configuration                         ║\n";
    std::cout << "╚════════════════════════════════════════════════════════════╝\n";
    std::cout << "\n📡 Deployment Mode: " << deployment_mode_ << "\n";
    std::cout << "🔧 Configured Interfaces:\n";

    for (const auto& iface : interfaces_) {
        std::cout << "  • " << iface.name
                  << " (ifindex=" << iface.ifindex << ")\n";
        std::cout << "    Mode: "
                  << (iface.mode == InterfaceMode::HOST_BASED ? "HOST-BASED" : "GATEWAY")
                  << "\n";
        std::cout << "    Role: " << (iface.is_wan ? "WAN" : "LAN") << "\n";
        std::cout << "    Description: " << iface.description << "\n";
    }

    std::cout << "╚════════════════════════════════════════════════════════════╝\n\n";
}

} // namespace sniffer