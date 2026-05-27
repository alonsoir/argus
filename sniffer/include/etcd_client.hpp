#pragma once
#include <memory>
#include <string>

// Forward declaration de la librería etcd-client
namespace etcd_client {
    class EtcdClient;
}

namespace sniffer {

    /**
     * Adapter para etcd_client library
     * Patrón PIMPL para mantener API limpia y usar la biblioteca con encryption + compression
     */
    class EtcdClient {
    public:
        EtcdClient(const std::string& endpoint, const std::string& component_name);
        ~EtcdClient();

        // Core API
        bool initialize();
        bool is_connected() const;
        bool registerService();
        bool unregisterService();

        // Configuration management
        bool upload_full_config(const std::string& config_json);
        bool get_component_config(const std::string& component_name);

        // Status and monitoring
        bool get_pipeline_status();
        std::string get_encryption_status();

        // 🎯 DAY 29: Get encryption seed for crypto-transport
        std::string get_encryption_seed() const;

    private:
        struct Impl;
        std::unique_ptr<Impl> pImpl;
    };

} // namespace sniffer