#pragma once

#include <string>
#include <unordered_map>
#include <thread>
#include <atomic>
#include <mutex>
#include <ctime>
#include <nlohmann/json.hpp>
// DEPRECATED DAY 98 — #include "crypto_manager.hpp" — usar CryptoTransport
#include <seed_client/seed_client.hpp>
#include <crypto_transport/transport.hpp>

//etcd-server/include/etcd_server/component_registry.hpp

using json = nlohmann::json;

class ComponentRegistry {
private:
    std::unordered_map<std::string, json> components_;
    // DEPRECATED DAY 98 — crypto_manager_ reemplazado por seed_client_ + tx_ + rx_
    std::unique_ptr<ml_defender::SeedClient>             seed_client_;
    std::unique_ptr<crypto_transport::CryptoTransport>   tx_;
    std::unique_ptr<crypto_transport::CryptoTransport>   rx_;
    bool compression_enabled_ = true;
    bool encryption_enabled_ = true;

    // Heartbeat tracking
    struct ComponentHeartbeat {
        std::time_t last_heartbeat;
        std::string status;  // "active", "dead", "restarting"
        int restart_attempts;

        ComponentHeartbeat()
            : last_heartbeat(std::time(nullptr))
            , status("active")
            , restart_attempts(0) {}
    };

    std::unordered_map<std::string, ComponentHeartbeat> heartbeats_;
    std::thread monitor_thread_;
    std::atomic<bool> monitor_running_{false};
    mutable std::mutex heartbeat_mutex_;  // mutable para permitir lock en métodos const

    // Heartbeat config (hardcoded por ahora, refactor después)
    int heartbeat_interval_seconds_ = 30;
    int timeout_multiplier_ = 3;
    int check_interval_seconds_ = 10;
    bool auto_restart_enabled_ = false;  // Default false hasta implementar restart
    int max_restart_attempts_ = 3;
    int restart_delay_seconds_ = 5;

public:
    ComponentRegistry();
    ~ComponentRegistry();

    // Gestión de componentes
    bool register_component(const std::string& name, const std::string& config_json);
    bool unregister_component(const std::string& name);
    bool update_component_config(const std::string& name, const std::string& path, const std::string& value);
    std::string get_component_config(const std::string& name) const;

    // Cifrado
    std::string get_encryption_seed() const;
    std::string get_encryption_key() const;
    std::string encrypt_data(const std::string& plaintext);
    std::string decrypt_data(const std::string& ciphertext);

    // Configuración global
    bool set_compression_mode(bool enabled);
    bool set_encryption_mode(bool enabled);
    void rotate_encryption_key();

    // Validación
    std::string validate_configuration() const;
    std::vector<std::string> detect_configuration_anomalies() const;

    // Información del sistema
    size_t get_component_count() const;
    std::vector<std::string> get_registered_components() const;

    // Heartbeat management
    bool update_heartbeat(const std::string& component_name);
    std::vector<std::string> get_dead_components();
    void start_heartbeat_monitor();
    void stop_heartbeat_monitor();
    std::time_t get_last_heartbeat(const std::string& component_name) const;

private:
    bool validate_component_config(const json& config) const;

    // Heartbeat monitoring
    void monitor_heartbeats();
    bool is_component_dead(const std::string& component_name);
    void handle_dead_component(const std::string& component_name);
};