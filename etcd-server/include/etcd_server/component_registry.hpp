#pragma once

#include <memory>
#include <string>
#include <nlohmann/json.hpp>
#include <seed_client/seed_client.hpp>
#include <crypto_transport/transport.hpp>
#include "etcd_server/registro_componentes.hpp"

//etcd-server/include/etcd_server/component_registry.hpp
// [ETCD-REGISTRO-D313] El registro (documentos, latidos, época) vive en RegistroComponentes sobre un IRegistryStore
// (etcd real, o memoria en la transición del defender). Aquí queda la criptografía del canal (/v1/config cifrado) y la
// validación global. Fuera (DAY313): el unordered_map sin mutex, el monitor que desregistraba, auto_restart + system(),
// y los métodos que ya no hacían nada (get_encryption_seed/key, set_compression/encryption_mode,
// rotate_encryption_key, get_dead_components).

using json = nlohmann::json;

class ComponentRegistry {
public:
    ComponentRegistry(const std::string& config_path, std::unique_ptr<argus::almacen::IRegistryStore> almacen,
                      int heartbeat_interval_seconds, int timeout_multiplier, int check_interval_seconds,
                      int aviso_intervalo_s, bool modo_memoria);
    ~ComponentRegistry();

    argus::registro::RegistroComponentes& registro() { return *registro_; }

    // Cifrado del canal (PUT /v1/config con application/octet-stream)
    std::string decrypt_data(const std::string& ciphertext);

    // Validación global (GET /validate)
    std::string validate_configuration();

private:
    std::unique_ptr<ml_defender::SeedClient>             seed_client_;
    std::unique_ptr<crypto_transport::CryptoTransport>   tx_;
    std::unique_ptr<crypto_transport::CryptoTransport>   rx_;
    std::unique_ptr<argus::registro::RegistroComponentes> registro_;
};
