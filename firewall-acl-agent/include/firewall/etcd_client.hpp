#pragma once
#ifndef FIREWALL_ETCD_CLIENT_HPP
#define FIREWALL_ETCD_CLIENT_HPP

#include <etcd_client/etcd_client.hpp>  // etcd_client::Config
#include <string>
#include <memory>
#include <optional>
#include <vector>

namespace mldefender::firewall {

    /**
     * @brief PIMPL Adapter for etcd-client library
     *
     * Wraps etcd_client::EtcdClient to avoid exposing implementation details
     * and maintain zero breaking changes to main.cpp
     */
    class EtcdClient {
    public:
        /**
         * @brief Construct etcd client adapter
         * @param base bloque etcd ya leído por etcd_client::leer_bloque_etcd() (direcciones https y TLS)
         * @param component_name Component identifier (e.g., "firewall-acl-agent")
         */
        EtcdClient(const etcd_client::Config& base, const std::string& component_name);  // [ETCD-CLIENTE-D316]

        ~EtcdClient();

        // Disable copy/move to simplify PIMPL
        EtcdClient(const EtcdClient&) = delete;
        EtcdClient& operator=(const EtcdClient&) = delete;

        /**
         * @brief [ETCD-CLIENTE-B1-D316] Arranca el mantenedor de la librería y vuelve enseguida (G1-G3, DAY316)
         * @param ruta_config JSON con el que arrancó el firewall (-c); se sube al etcd-server en cada registro
         */
        void arrancar(const std::string& ruta_config);

        /**
         * @brief Clave HMAC del etcd-server
         * @param key_path p. ej. "/secrets/firewall-acl-agent" (solo exige el certificado con ese CN, no el registro)
         * @return 32 bytes, o nullopt si no hay clave o no responde ningún etcd-server
         */
        std::optional<std::vector<uint8_t>> get_hmac_key(const std::string& key_path);
    private:
        struct Impl;
        std::unique_ptr<Impl> pImpl;
    };

} // namespace mldefender::firewall
#endif