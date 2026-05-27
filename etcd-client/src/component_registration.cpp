// etcd-client/src/component_registration.cpp
#include "etcd_client/etcd_client.hpp"
#include <nlohmann/json.hpp>
#include <iostream>
#include <chrono>

using json = nlohmann::json;

namespace etcd_client {
namespace component {

// Get current timestamp in milliseconds
uint64_t get_timestamp_ms() {
    auto now = std::chrono::system_clock::now();
    auto duration = now.time_since_epoch();
    return std::chrono::duration_cast<std::chrono::milliseconds>(duration).count();
}

// Build registration JSON payload
std::string build_registration_payload(const Config& config) {
    json payload = {
        {"component", config.component_name},
        {"config_path", config.component_config_path},
        {"timestamp", get_timestamp_ms()},
        {"status", "active"},
        {"capabilities", {
            {"encryption", config.encryption_enabled},
            {"compression", config.compression_enabled},
            {"heartbeat", config.heartbeat_enabled}
        }}
    };
    
    return payload.dump();
}

    // Build heartbeat JSON payload
    std::string build_heartbeat_payload(const Config& /*config*/) {
    // Get timestamp in SECONDS (not milliseconds)
    auto now = std::chrono::system_clock::now();
    auto duration = now.time_since_epoch();
    uint64_t timestamp_seconds = std::chrono::duration_cast<std::chrono::seconds>(duration).count();

    json payload = {
        {"timestamp", timestamp_seconds},  // ✅ SEGUNDOS (unix timestamp)
        {"status", "active"}
    };

    return payload.dump();
}

// Build unregister JSON payload
std::string build_unregister_payload(const Config& config) {
    json payload = {
        {"component", config.component_name},
        {"timestamp", get_timestamp_ms()},
        {"status", "inactive"}
    };
    
    return payload.dump();
}

// Parse component info from JSON response
ComponentInfo parse_component_info(const std::string& json_str) {
    ComponentInfo info;
    
    try {
        json j = json::parse(json_str);
        
        if (j.contains("component")) {
            info.name = j["component"].get<std::string>();
        }
        
        if (j.contains("status")) {
            info.status = j["status"].get<std::string>();
        }
        
        if (j.contains("config_path")) {
            info.config_path = j["config_path"].get<std::string>();
        }
        
        if (j.contains("timestamp")) {
            info.last_heartbeat_ms = j["timestamp"].get<uint64_t>();
        }
        
        // Store full JSON as metadata
        info.metadata_json = json_str;
        
    } catch (const json::exception& e) {
        std::cerr << "⚠️  Failed to parse component info: " << e.what() << std::endl;
    }
    
    return info;
}

// Parse list of components from JSON array
std::vector<ComponentInfo> parse_component_list(const std::string& json_str) {
    std::vector<ComponentInfo> components;
    
    try {
        json j = json::parse(json_str);
        
        if (j.is_array()) {
            for (const auto& item : j) {
                ComponentInfo info = parse_component_info(item.dump());
                components.push_back(info);
            }
        } else if (j.is_object() && j.contains("components")) {
            // Handle wrapped format: {"components": [...]}
            for (const auto& item : j["components"]) {
                ComponentInfo info = parse_component_info(item.dump());
                components.push_back(info);
            }
        }
        
    } catch (const json::exception& e) {
        std::cerr << "⚠️  Failed to parse component list: " << e.what() << std::endl;
    }
    
    return components;
}

} // namespace component
} // namespace etcd_client
