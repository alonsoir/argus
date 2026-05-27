#include <mutex>
#include <string>
#pragma once

#include <memory>
#include <thread>
#include <atomic>
#include <unordered_map>

// Forward declaration for SecretsManager
namespace etcd_server {
    class SecretsManager;
}

//etcd-server/include/etcd_server/etcd_server.hpp
class ComponentRegistry;

class EtcdServer {
private:
    std::unique_ptr<ComponentRegistry> component_registry_;
    etcd_server::SecretsManager* secrets_manager_ = nullptr;  // Non-owning pointer
    std::atomic<bool> running_{false};
    int port_;
    std::thread server_thread_;

public:
    EtcdServer(int port = 2379);
    ~EtcdServer();

    void set_secrets_manager(etcd_server::SecretsManager* manager) {
        secrets_manager_ = manager;
    }
    bool initialize();
    void start();
    void stop();
    bool is_running() const { return running_; }

    // Gestión de componentes
    bool register_component(const std::string& component_name, const std::string& config_json);
    std::string get_component_config(const std::string& component_name);
    bool update_component_config(const std::string& component_name, const std::string& config_path, const std::string& value);

    // Validación
    std::string validate_configuration();

    // Epoch management (ADR-045 v2 — DAY 164)
    struct EpochInfo {
        uint16_t    epoch_id{1};
        std::string not_before{"2026-01-01T00:00:00Z"};
        int64_t     revision{1};
    };
    void        set_epoch(uint16_t epoch_id, const std::string& not_before);
    EpochInfo   get_epoch() const;

private:
    void run_server();
    std::string handle_request(const std::string& method, const std::string& path, const std::string& body);
    EpochInfo           epoch_;
    mutable std::mutex  epoch_mutex_;
};