//sniffer/include/bpf_map_manager.h
// BPF Map Manager - Hybrid filtering system (v3.2)

#ifndef BPF_MAP_MANAGER_H
#define BPF_MAP_MANAGER_H

#include <cstdint>
#include <vector>
#include <string>
#include <set>

namespace sniffer {

    // Filter configuration (matches filter_config in sniffer.bpf.c)
    struct FilterConfig {
        uint8_t default_action;  // 0 = drop, 1 = capture
        uint8_t reserved[7];
    } __attribute__((packed));

    class BPFMapManager {
    public:
        BPFMapManager() = default;
        ~BPFMapManager() = default;

        // Load filter configuration from JSON to BPF maps
        bool load_filter_config(
            const std::vector<uint16_t>& excluded_ports,
            const std::vector<uint16_t>& included_ports,
            uint8_t default_action  // 0 = drop, 1 = capture
        );

        // Load filter configuration using provided file descriptors
        bool load_filter_config_with_fds(
            int excluded_ports_fd,
            int included_ports_fd,
            int filter_settings_fd,
            const std::vector<uint16_t>& excluded_ports,
            const std::vector<uint16_t>& included_ports,
            uint8_t default_action
        );

        // Individual port operations (for dynamic updates)
        bool add_excluded_port(uint16_t port);
        bool remove_excluded_port(uint16_t port);
        bool add_included_port(uint16_t port);
        bool remove_included_port(uint16_t port);

        // Query current filter state
        std::vector<uint16_t> get_excluded_ports();
        std::vector<uint16_t> get_included_ports();
        uint8_t get_default_action();

        // Validation
        bool validate_port_lists(
            const std::vector<uint16_t>& excluded,
            const std::vector<uint16_t>& included
        );

        // Clear all filters
        bool clear_all_filters();

    private:
        int get_map_fd(const std::string& map_name);

        bool update_port_map(
            const std::string& map_name,
            const std::vector<uint16_t>& ports,
            bool clear_first = true
        );

        bool update_port_map_with_fd(
        int map_fd,
        const std::string& map_name,
        const std::vector<uint16_t>& ports,
        bool clear_first
        );

    };

} // namespace sniffer

#endif // BPF_MAP_MANAGER_H