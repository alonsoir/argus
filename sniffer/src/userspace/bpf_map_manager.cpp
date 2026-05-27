//sniffer/src/userspace/bpf_map_manager.cpp
// BPF Map Manager Implementation

#include "bpf_map_manager.h"
#include <bpf/libbpf.h>
#include <bpf/bpf.h>
#include <iostream>
#include <cstring>
#include <cerrno>
#include <unistd.h>
#include <algorithm>

namespace sniffer {

int BPFMapManager::get_map_fd(const std::string& map_name) {
    // Try pinned map first
    std::string map_path = "/sys/fs/bpf/" + map_name;
    int fd = bpf_obj_get(map_path.c_str());
    
    if (fd < 0) {
        std::cerr << "❌ Failed to get BPF map: " << map_name 
                  << " (errno: " << errno << " - " << strerror(errno) << ")" << std::endl;
        std::cerr << "   Ensure the eBPF program is loaded and maps are pinned" << std::endl;
    }
    
    return fd;
}

bool BPFMapManager::update_port_map(
    const std::string& map_name,
    const std::vector<uint16_t>& ports,
    bool clear_first
) {
    int map_fd = get_map_fd(map_name);
    if (map_fd < 0) return false;

    // Optional: Clear existing entries
    if (clear_first) {
        uint16_t key, next_key;
        if (bpf_map_get_next_key(map_fd, NULL, &key) == 0) {
            do {
                bpf_map_delete_elem(map_fd, &key);
            } while (bpf_map_get_next_key(map_fd, &key, &next_key) == 0 && (key = next_key));
        }
    }

    // Add new entries
    int success_count = 0;
    for (uint16_t port : ports) {
        uint8_t value = 1;
        
        if (bpf_map_update_elem(map_fd, &port, &value, BPF_ANY) == 0) {
            success_count++;
        } else {
            std::cerr << "⚠️  Failed to add port " << port 
                      << " to " << map_name << std::endl;
        }
    }

    close(map_fd);
    return success_count == static_cast<int>(ports.size());
}

bool BPFMapManager::load_filter_config(
    const std::vector<uint16_t>& excluded_ports,
    const std::vector<uint16_t>& included_ports,
    uint8_t default_action
) {
    std::cout << "\n🔧 Loading BPF filter configuration..." << std::endl;

    // Validate input
    if (!validate_port_lists(excluded_ports, included_ports)) {
        return false;
    }

    // Load excluded ports
    std::cout << "📤 Loading " << excluded_ports.size() << " excluded ports..." << std::endl;
    if (!update_port_map("excluded_ports", excluded_ports, true)) {
        std::cerr << "❌ Failed to load excluded ports" << std::endl;
        return false;
    }
    std::cout << "✅ Excluded ports loaded: ";
    for (size_t i = 0; i < std::min(excluded_ports.size(), size_t(10)); ++i) {
        std::cout << excluded_ports[i];
        if (i < excluded_ports.size() - 1) std::cout << ", ";
    }
    if (excluded_ports.size() > 10) std::cout << " ... (+" << (excluded_ports.size() - 10) << " more)";
    std::cout << std::endl;

    // Load included ports
    std::cout << "📥 Loading " << included_ports.size() << " included ports..." << std::endl;
    if (!update_port_map("included_ports", included_ports, true)) {
        std::cerr << "❌ Failed to load included ports" << std::endl;
        return false;
    }
    std::cout << "✅ Included ports loaded: ";
    for (size_t i = 0; i < std::min(included_ports.size(), size_t(10)); ++i) {
        std::cout << included_ports[i];
        if (i < included_ports.size() - 1) std::cout << ", ";
    }
    if (included_ports.size() > 10) std::cout << " ... (+" << (included_ports.size() - 10) << " more)";
    std::cout << std::endl;

    // Load filter settings (default_action)
    int settings_fd = get_map_fd("filter_settings");
    if (settings_fd < 0) {
        std::cerr << "❌ Failed to access filter_settings map" << std::endl;
        return false;
    }

    FilterConfig config;
    memset(&config, 0, sizeof(config));
    config.default_action = default_action;

    uint32_t key = 0;
    if (bpf_map_update_elem(settings_fd, &key, &config, BPF_ANY) != 0) {
        std::cerr << "❌ Failed to update filter settings" << std::endl;
        close(settings_fd);
        return false;
    }
    close(settings_fd);

    std::cout << "✅ Default action: " << (default_action ? "CAPTURE" : "DROP") << std::endl;
    std::cout << "✅ Filter configuration loaded successfully\n" << std::endl;

    return true;
}

bool BPFMapManager::add_excluded_port(uint16_t port) {
    int map_fd = get_map_fd("excluded_ports");
    if (map_fd < 0) return false;

    uint8_t value = 1;
    int ret = bpf_map_update_elem(map_fd, &port, &value, BPF_ANY);
    close(map_fd);
    
    if (ret == 0) {
        std::cout << "✅ Added port " << port << " to exclusion filter" << std::endl;
        return true;
    } else {
        std::cerr << "❌ Failed to add port " << port << " to exclusion filter" << std::endl;
        return false;
    }
}

bool BPFMapManager::remove_excluded_port(uint16_t port) {
    int map_fd = get_map_fd("excluded_ports");
    if (map_fd < 0) return false;

    int ret = bpf_map_delete_elem(map_fd, &port);
    close(map_fd);
    
    if (ret == 0) {
        std::cout << "✅ Removed port " << port << " from exclusion filter" << std::endl;
        return true;
    } else {
        std::cerr << "❌ Failed to remove port " << port << " from exclusion filter" << std::endl;
        return false;
    }
}

bool BPFMapManager::add_included_port(uint16_t port) {
    int map_fd = get_map_fd("included_ports");
    if (map_fd < 0) return false;

    uint8_t value = 1;
    int ret = bpf_map_update_elem(map_fd, &port, &value, BPF_ANY);
    close(map_fd);
    
    if (ret == 0) {
        std::cout << "✅ Added port " << port << " to inclusion filter (high priority)" << std::endl;
        return true;
    } else {
        std::cerr << "❌ Failed to add port " << port << " to inclusion filter" << std::endl;
        return false;
    }
}

bool BPFMapManager::remove_included_port(uint16_t port) {
    int map_fd = get_map_fd("included_ports");
    if (map_fd < 0) return false;

    int ret = bpf_map_delete_elem(map_fd, &port);
    close(map_fd);
    
    if (ret == 0) {
        std::cout << "✅ Removed port " << port << " from inclusion filter" << std::endl;
        return true;
    } else {
        std::cerr << "❌ Failed to remove port " << port << " from inclusion filter" << std::endl;
        return false;
    }
}

std::vector<uint16_t> BPFMapManager::get_excluded_ports() {
    std::vector<uint16_t> ports;
    int map_fd = get_map_fd("excluded_ports");
    if (map_fd < 0) return ports;

    uint16_t key, next_key;
    uint8_t value;
    
    if (bpf_map_get_next_key(map_fd, NULL, &key) == 0) {
        do {
            if (bpf_map_lookup_elem(map_fd, &key, &value) == 0 && value == 1) {
                ports.push_back(key);
            }
        } while (bpf_map_get_next_key(map_fd, &key, &next_key) == 0 && (key = next_key));
    }

    close(map_fd);
    std::sort(ports.begin(), ports.end());
    return ports;
}

std::vector<uint16_t> BPFMapManager::get_included_ports() {
    std::vector<uint16_t> ports;
    int map_fd = get_map_fd("included_ports");
    if (map_fd < 0) return ports;

    uint16_t key, next_key;
    uint8_t value;
    
    if (bpf_map_get_next_key(map_fd, NULL, &key) == 0) {
        do {
            if (bpf_map_lookup_elem(map_fd, &key, &value) == 0 && value == 1) {
                ports.push_back(key);
            }
        } while (bpf_map_get_next_key(map_fd, &key, &next_key) == 0 && (key = next_key));
    }

    close(map_fd);
    std::sort(ports.begin(), ports.end());
    return ports;
}

uint8_t BPFMapManager::get_default_action() {
    int map_fd = get_map_fd("filter_settings");
    if (map_fd < 0) return 1;  // Default: capture

    FilterConfig config;
    uint32_t key = 0;
    
    if (bpf_map_lookup_elem(map_fd, &key, &config) == 0) {
        close(map_fd);
        return config.default_action;
    }

    close(map_fd);
    return 1;  // Default: capture
}

bool BPFMapManager::validate_port_lists(
    const std::vector<uint16_t>& excluded,
    const std::vector<uint16_t>& included
) {
    // Check for invalid ports
    for (uint16_t port : excluded) {
        if (port == 0) {
            std::cerr << "❌ Invalid excluded port: 0 (ports must be 1-65535)" << std::endl;
            return false;
        }
    }

    for (uint16_t port : included) {
        if (port == 0) {
            std::cerr << "❌ Invalid included port: 0 (ports must be 1-65535)" << std::endl;
            return false;
        }
    }

    // Check for conflicts (port in both lists)
    std::set<uint16_t> excluded_set(excluded.begin(), excluded.end());
    std::set<uint16_t> included_set(included.begin(), included.end());
    
    std::vector<uint16_t> conflicts;
    std::set_intersection(
        excluded_set.begin(), excluded_set.end(),
        included_set.begin(), included_set.end(),
        std::back_inserter(conflicts)
    );

    if (!conflicts.empty()) {
        std::cout << "⚠️  Warning: Ports in BOTH excluded and included lists "
                  << "(included_ports takes precedence): ";
        for (size_t i = 0; i < conflicts.size(); ++i) {
            std::cout << conflicts[i];
            if (i < conflicts.size() - 1) std::cout << ", ";
        }
        std::cout << std::endl;
    }

    // Check map size limits
    if (excluded.size() > 1024) {
        std::cerr << "❌ Too many excluded ports: " << excluded.size() 
                  << " (max: 1024)" << std::endl;
        return false;
    }

    if (included.size() > 1024) {
        std::cerr << "❌ Too many included ports: " << included.size() 
                  << " (max: 1024)" << std::endl;
        return false;
    }

    return true;
}

bool BPFMapManager::clear_all_filters() {
    std::cout << "🧹 Clearing all BPF filters..." << std::endl;

    bool success = true;

    // Clear excluded ports
    if (!update_port_map("excluded_ports", {}, true)) {
        std::cerr << "⚠️  Warning: Failed to clear excluded_ports" << std::endl;
        success = false;
    }

    // Clear included ports
    if (!update_port_map("included_ports", {}, true)) {
        std::cerr << "⚠️  Warning: Failed to clear included_ports" << std::endl;
        success = false;
    }

    // Reset filter settings to default
    int settings_fd = get_map_fd("filter_settings");
    if (settings_fd >= 0) {
        FilterConfig config;
        memset(&config, 0, sizeof(config));
        config.default_action = 1;  // Default: capture

        uint32_t key = 0;
        bpf_map_update_elem(settings_fd, &key, &config, BPF_ANY);
        close(settings_fd);
    }

    if (success) {
        std::cout << "✅ All filters cleared" << std::endl;
    }

    return success;
}

// PATCH FOR bpf_map_manager.cpp
// Add these implementations at the end of the file (before the closing namespace):

bool BPFMapManager::update_port_map_with_fd(
    int map_fd,
    const std::string& map_name,
    const std::vector<uint16_t>& ports,
    bool clear_first
) {
    if (map_fd < 0) {
        std::cerr << "❌ Invalid FD for " << map_name << std::endl;
        return false;
    }

    // Optional: Clear existing entries
    if (clear_first) {
        uint16_t key, next_key;
        if (bpf_map_get_next_key(map_fd, NULL, &key) == 0) {
            do {
                bpf_map_delete_elem(map_fd, &key);
            } while (bpf_map_get_next_key(map_fd, &key, &next_key) == 0 && (key = next_key));
        }
    }

    // Add new entries
    int success_count = 0;
    for (uint16_t port : ports) {
        uint8_t value = 1;

        if (bpf_map_update_elem(map_fd, &port, &value, BPF_ANY) == 0) {
            success_count++;
        } else {
            std::cerr << "⚠️  Failed to add port " << port
                      << " to " << map_name << " (errno: " << errno << ")" << std::endl;
        }
    }

    return success_count == static_cast<int>(ports.size());
}

bool BPFMapManager::load_filter_config_with_fds(
    int excluded_ports_fd,
    int included_ports_fd,
    int filter_settings_fd,
    const std::vector<uint16_t>& excluded_ports,
    const std::vector<uint16_t>& included_ports,
    uint8_t default_action
) {
    std::cout << "\n🔧 Loading BPF filter configuration (using FDs)..." << std::endl;

    // Validate input
    if (!validate_port_lists(excluded_ports, included_ports)) {
        return false;
    }

    // Validate FDs
    if (excluded_ports_fd < 0 || included_ports_fd < 0 || filter_settings_fd < 0) {
        std::cerr << "❌ Invalid filter map file descriptors" << std::endl;
        std::cerr << "   excluded_ports_fd: " << excluded_ports_fd << std::endl;
        std::cerr << "   included_ports_fd: " << included_ports_fd << std::endl;
        std::cerr << "   filter_settings_fd: " << filter_settings_fd << std::endl;
        return false;
    }

    // Load excluded ports
    std::cout << "📤 Loading " << excluded_ports.size() << " excluded ports..." << std::endl;
    if (!update_port_map_with_fd(excluded_ports_fd, "excluded_ports", excluded_ports, true)) {
        std::cerr << "❌ Failed to load excluded ports" << std::endl;
        return false;
    }

    std::cout << "✅ Excluded ports loaded: ";
    for (size_t i = 0; i < std::min(excluded_ports.size(), size_t(5)); ++i) {
        std::cout << excluded_ports[i];
        if (i < excluded_ports.size() - 1) std::cout << ", ";
    }
    if (excluded_ports.size() > 5) std::cout << " ... (+" << (excluded_ports.size() - 5) << " more)";
    std::cout << std::endl;

    // Load included ports
    std::cout << "📥 Loading " << included_ports.size() << " included ports..." << std::endl;
    if (!update_port_map_with_fd(included_ports_fd, "included_ports", included_ports, true)) {
        std::cerr << "❌ Failed to load included ports" << std::endl;
        return false;
    }

    std::cout << "✅ Included ports loaded: ";
    for (size_t i = 0; i < std::min(included_ports.size(), size_t(5)); ++i) {
        std::cout << included_ports[i];
        if (i < included_ports.size() - 1) std::cout << ", ";
    }
    if (included_ports.size() > 5) std::cout << " ... (+" << (included_ports.size() - 5) << " more)";
    std::cout << std::endl;

    // Load filter settings
    std::cout << "⚙️  Loading filter settings..." << std::endl;
    uint32_t settings_key = 0;

    struct filter_settings_t {
        uint8_t default_action;
        uint8_t reserved[3];
    } settings;

    settings.default_action = default_action;
    memset(settings.reserved, 0, sizeof(settings.reserved));

    if (bpf_map_update_elem(filter_settings_fd, &settings_key, &settings, BPF_ANY) != 0) {
        std::cerr << "❌ Failed to update filter settings (errno: " << errno << ")" << std::endl;
        return false;
    }

    std::cout << "✅ Filter settings loaded (default_action: "
              << (default_action == 1 ? "CAPTURE" : "DROP") << ")" << std::endl;

    std::cout << "✅ All filter configuration loaded successfully to kernel" << std::endl;

    return true;
}

} // namespace sniffer