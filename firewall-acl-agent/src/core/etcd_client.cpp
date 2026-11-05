#include "firewall/etcd_client.hpp"
#include <etcd_client/etcd_client.hpp>
#include <iostream>
#include <optional>
#include <vector>

namespace mldefender::firewall {

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
        config.component_config_path = "/etc/ml-defender/firewall-acl-agent/firewall.json";
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
    std::cout << "🔧 [firewall-acl-agent] EtcdClient adapter created for: " << component_name << std::endl;
}

EtcdClient::~EtcdClient() = default;

// [ETCD-CLIENTE-B1-D316] G1-G3: el mantenedor de la librería se registra (y se vuelve a registrar) solo, sube este JSON
// en cada registro y nunca hace esperar ni salir al proceso
void EtcdClient::arrancar(const std::string& ruta_config) {
    if (pImpl->client_) pImpl->client_->iniciar(ruta_config, "firewall");
}

std::optional<std::vector<uint8_t>> EtcdClient::get_hmac_key(const std::string& key_path) {
    if (!pImpl->client_) {
        std::cerr << "❌ [firewall-acl-agent] get_hmac_key() sin cliente etcd" << std::endl;
        return std::nullopt;
    }

    auto key = pImpl->client_->get_hmac_key(key_path);

    if (key) {
        std::cout << "🔑 [firewall-acl-agent] Retrieved HMAC key from: " << key_path
                  << " (" << key->size() << " bytes)" << std::endl;
    } else {
        std::cerr << "⚠️ [firewall-acl-agent] HMAC key not found: " << key_path << std::endl;
    }

    return key;
}

// [PROTEGIDOS-MANIFIESTO-D318] ADR-060 8e.3c
int EtcdClient::get_protegidos(std::string& cuerpo) {
    if (!pImpl->client_) {
        cuerpo = "sin cliente etcd";
        return -1;
    }
    return pImpl->client_->get_protegidos(cuerpo);
}

} // namespace mldefender::firewall