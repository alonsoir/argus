// etcd-client/src/config_loader.cpp
#include "etcd_client/etcd_client.hpp"
#include <nlohmann/json.hpp>
#include <fstream>
#include <stdexcept>
#include <iostream>

using json = nlohmann::json;

namespace etcd_client {

// Load config from JSON file
Config Config::from_json_file(const std::string& json_path) {
    std::ifstream file(json_path);
    if (!file.is_open()) {
        throw std::runtime_error("Failed to open config file: " + json_path);
    }
    
    json j;
    try {
        file >> j;
    } catch (const json::exception& e) {
        throw std::runtime_error("Failed to parse JSON config: " + std::string(e.what()));
    }
    
    return from_json(j);
}

// Load config from JSON object
Config Config::from_json(const nlohmann::json& j) {
    Config config;
    
    try {
        // Navigate to etcd_client section
        if (!j.contains("etcd_client")) {
            throw std::runtime_error("Missing 'etcd_client' section in config");
        }
        
        const auto& ec = j["etcd_client"];
        
        // Server settings
        if (ec.contains("server")) {
            const auto& server = ec["server"];
            config.host = server.value("host", "127.0.0.1");
            config.port = server.value("port", 2379);
            config.timeout_seconds = server.value("timeout_seconds", 5);
        }
        
        // Component identity
        if (ec.contains("component")) {
            const auto& comp = ec["component"];
            config.component_name = comp.value("name", "");
            config.component_config_path = comp.value("config_path", "");
            
            if (config.component_name.empty()) {
                throw std::runtime_error("component.name is required");
            }
        } else {
            throw std::runtime_error("Missing 'component' section");
        }
        
        // Encryption settings
        if (ec.contains("encryption")) {
            const auto& enc = ec["encryption"];
            config.encryption_enabled = enc.value("enabled", true);
            config.encryption_algorithm = enc.value("algorithm", "chacha20-poly1305");
        }
        
        // Compression settings
        if (ec.contains("compression")) {
            const auto& comp = ec["compression"];
            config.compression_enabled = comp.value("enabled", true);
            config.compression_algorithm = comp.value("algorithm", "lz4");
            config.compression_min_size = comp.value("min_size_bytes", 256);
        }
        
        // Heartbeat settings
        if (ec.contains("heartbeat")) {
            const auto& hb = ec["heartbeat"];
            config.heartbeat_enabled = hb.value("enabled", true);
            config.heartbeat_interval_seconds = hb.value("interval_seconds", 30);
        }
        
        // Retry settings
        if (ec.contains("retry")) {
            const auto& retry = ec["retry"];
            config.max_retry_attempts = retry.value("max_attempts", 3);
            config.retry_backoff_seconds = retry.value("backoff_seconds", 2);
        }
        
        // Validation
        if (config.port < 1 || config.port > 65535) {
            throw std::runtime_error("Invalid port number: " + std::to_string(config.port));
        }
        
        if (config.timeout_seconds < 1) {
            throw std::runtime_error("timeout_seconds must be >= 1");
        }
        
        std::cout << "✅ Config loaded successfully for component: " 
                  << config.component_name << std::endl;
        
    } catch (const json::exception& e) {
        throw std::runtime_error("JSON parsing error: " + std::string(e.what()));
    }
    
    return config;
}

} // namespace etcd_client
