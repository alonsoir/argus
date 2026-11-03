#pragma once
#include <memory>
#include <string>

// Forward declaration de la librería etcd-client
namespace etcd_client {
    class EtcdClient;
    struct Config;
}

namespace sniffer {

    /**
     * Adapter para etcd_client library
     * Patrón PIMPL para mantener API limpia y usar la biblioteca con encryption + compression
     */
    class EtcdClient {
    public:
        EtcdClient(const etcd_client::Config& base, const std::string& component_name);  // [ETCD-CLIENTE-D316]
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

        // ADR-013 PHASE 2: semilla de crypto-transport leída de seed.bin local. [ETCD-CLIENTE-D316] C3: antes se llamaba
        // get_encryption_seed() y el log decía que venía del etcd-server; nunca vino de ahí desde DAY98.
        std::string leer_semilla_local() const;

    private:
        struct Impl;
        std::unique_ptr<Impl> pImpl;
    };

} // namespace sniffer