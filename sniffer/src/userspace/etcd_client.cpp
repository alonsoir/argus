// sniffer/src/userspace/etcd_client.cpp - Adapter para etcd_client library
#include "etcd_client.hpp"
#include "etcd_client/etcd_client.hpp"
#include <iostream>

namespace sniffer {

// ============================================================================
// Implementación del Adapter (PIMPL)
// ============================================================================

struct EtcdClient::Impl {
    std::unique_ptr<etcd_client::EtcdClient> client_;
    std::string component_name_;

    // [ETCD-CLIENTE-D316] base = lo que devuelve etcd_client::leer_bloque_etcd() del bloque etcd del JSON
    Impl(const etcd_client::Config& base, const std::string& component_name)
        : component_name_(component_name) {


        // Configurar etcd-client
        etcd_client::Config config = base;  // endpoints, TLS y tiempos del JSON
        config.component_name = component_name;
        // encryption_enabled: lo trae base (defecto true)
        config.compression_enabled = true;
        config.compression_min_size = 0;
        config.component_config_path = "/etc/ml-defender/sniffer/sniffer.json";
        // INVARIANT (ADR-027): encryption_enabled requiere component_config_path.
        // Sin él, SeedClient no inicializa, datos van en claro → MAC failure garantizado.
        if (config.encryption_enabled && config.component_config_path.empty()) {
            if (getenv("MLD_ALLOW_UNCRYPTED")) {
                std::cerr << "FATAL[DEV]: encryption_enabled pero component_config_path vacio. "
                          << "MLD_ALLOW_UNCRYPTED activo - continuando sin cifrado. "
                          << "NUNCA en produccion.\n";
                return; // constructor: continuar sin cifrado en dev mode
            } else {
                std::terminate(); // FATAL: produccion - fallo total garantizado
            }
        }
        client_ = std::make_unique<etcd_client::EtcdClient>(config);
    }

};

// ============================================================================
// Implementación pública del Adapter
// ============================================================================

EtcdClient::EtcdClient(const etcd_client::Config& base, const std::string& component_name)
    : pImpl(std::make_unique<Impl>(base, component_name)) {
    std::cout << "🔧 [Sniffer] EtcdClient adapter created for: " << component_name << std::endl;
}

EtcdClient::~EtcdClient() = default;

// [ETCD-CLIENTE-B1-D316] G1-G3: el mantenedor de la librería se registra (y se vuelve a registrar) solo, sube este JSON
// en cada registro y nunca hace esperar ni salir al proceso
void EtcdClient::arrancar(const std::string& ruta_config) {
    if (pImpl->client_) pImpl->client_->iniciar(ruta_config, "packet-sniffer");
}

} // namespace sniffer
