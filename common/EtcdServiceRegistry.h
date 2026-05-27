#pragma once

#include <string>
#include <memory>
#include <chrono>
#include <thread>
#include <atomic>
#include <mutex>
#include <map>
#include <vector>
#include <curl/curl.h>

class EtcdServiceRegistry {
private:
    static std::unique_ptr<EtcdServiceRegistry> instance_;
    static std::mutex instance_mutex_;

    CURL* curl_handle_;
    std::string etcd_base_url_;

    std::atomic<bool> running_;
    std::thread heartbeat_thread_;
    std::string service_name_;
    std::string node_id_;
    int64_t lease_id_;

    // Constructor privado para singleton
    EtcdServiceRegistry(const std::string& etcd_endpoint = "http://etcd:2379");

    // HTTP response callback
    static size_t WriteCallback(void* contents, size_t size, size_t nmemb, void* userp);

    // Método interno para heartbeat
    void heartbeatLoop();

    // HTTP operations
    bool httpPut(const std::string& key, const std::string& value, int64_t lease_id = 0);
    std::string httpGet(const std::string& key);
    std::vector<std::pair<std::string, std::string>> httpGetWithPrefix(const std::string& prefix);
    int64_t createLease(int64_t ttl);
    bool keepAliveLease(int64_t lease_id);

    // Helpers
    std::string generateServiceKey(const std::string& service_name, const std::string& suffix = "");
    std::string generateHeartbeatKey(const std::string& service_name);
    std::string generateConfigKey(const std::string& service_name, const std::string& config_key);
    std::string base64Encode(const std::string& input);
    std::string base64Decode(const std::string& input);

public:
    // Destructor
    ~EtcdServiceRegistry();

    // Eliminar copy constructor y assignment operator
    EtcdServiceRegistry(const EtcdServiceRegistry&) = delete;
    EtcdServiceRegistry& operator=(const EtcdServiceRegistry&) = delete;

    // Método estático para obtener la instancia singleton
    static EtcdServiceRegistry& getInstance(const std::string& etcd_endpoint = "http://etcd:2379");

    // API pública (idéntica a la versión gRPC)
    bool registerService(const std::string& service_name,
                        const std::string& node_id,
                        const std::string& json_config,
                        int heartbeat_ttl = 30);

    bool registerServiceWithMultipleConfigs(const std::string& service_name,
                                           const std::string& node_id,
                                           const std::map<std::string, std::string>& json_configs,
                                           int heartbeat_ttl = 30);

    std::string getServiceConfig(const std::string& service_name, const std::string& config_key = "config");
    std::vector<std::string> listServices();
    bool isServiceActive(const std::string& service_name);
    bool updateServiceConfig(const std::string& service_name,
                           const std::string& json_config,
                           const std::string& config_key = "config");
    std::string getServiceHealth(const std::string& service_name);
    void shutdown();
};