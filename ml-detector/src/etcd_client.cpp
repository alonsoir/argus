#include "etcd_client.hpp"
#include <etcd_client/etcd_client.hpp>
#include <nlohmann/json.hpp>
#include <sstream>
#include <iomanip>
#include <fstream>
#include <iostream>

namespace ml_detector {

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
        // M6 (DAY316): el cifrado ya no se deduce del esquema de la URL; lo trae base (defecto true)
        config.compression_enabled = true;
        // component_config_path solo cuando encryption activo (seed no disponible en tests)
        if (config.encryption_enabled) {
            config.component_config_path = "/etc/ml-defender/ml-detector/ml_detector_config.json";
        }
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
        client_ = std::make_unique<etcd_client::EtcdClient>(config);  // [ETCD-CLIENTE-B1-D316] sin connect(): no espera
    }


    std::string get_hmac_key() {
        if (!client_) {
            std::cerr << "[etcd] Client not initialized" << std::endl;
            return "";
        }
        std::string key_path = "/secrets/" + component_name_;
        auto result = client_->get_hmac_key(key_path);
        if (!result.has_value() || result->empty()) {
            std::cerr << "[etcd] Failed to get HMAC key from " << key_path << std::endl;
            return "";
        }
        // Convertir vector<uint8_t> a hex string
        std::ostringstream hex;
        hex << std::hex << std::setfill('0');
        for (uint8_t b : result.value()) {
            hex << std::setw(2) << static_cast<unsigned int>(b);
        }
        // [BRONCE-CLAVE-D310] sin linea de exito: se pide cada intervalo y la recepcion la registra ZMQHandler
        // ([BRONCE-CLAVE], con la huella). El fallo sigue saliendo por cerr.
        return hex.str();
    }
};  // ← cierre de struct Impl

// ============================================================================
// Implementación pública del Adapter
// ============================================================================

EtcdClient::EtcdClient(const etcd_client::Config& base, const std::string& component_name)
    : pImpl(std::make_unique<Impl>(base, component_name)) {
    std::cout << "🔧 [ml-detector] EtcdClient adapter created for: " << component_name << std::endl;
}

EtcdClient::~EtcdClient() = default;

// [ETCD-CLIENTE-B1-D316] G1-G3: el mantenedor de la librería se registra (y se vuelve a registrar) solo, sube este JSON
// en cada registro y nunca hace esperar ni salir al proceso
void EtcdClient::arrancar(const std::string& ruta_config) {
    if (pImpl->client_) pImpl->client_->iniciar(ruta_config, "ml-detector");
}

std::string EtcdClient::get_hmac_key() const {
    return pImpl->get_hmac_key();
}

} // namespace ml_detector