#pragma once
#include <memory>
#include <string>

namespace etcd_client {
    struct Config;
}

namespace ml_detector {
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
         * @param base Config from etcd_client::leer_bloque_etcd() (endpoints https, TLS, tiempos) [ETCD-CLIENTE-D316]
         * @param component_name Component identifier (e.g., "ml-detector") = CN of its client certificate
         */
        EtcdClient(const etcd_client::Config& base, const std::string& component_name);  // [ETCD-CLIENTE-D316]
        ~EtcdClient();

        // Disable copy/move to simplify PIMPL
        EtcdClient(const EtcdClient&) = delete;
        EtcdClient& operator=(const EtcdClient&) = delete;

        /**
         * @brief [ETCD-CLIENTE-B1-D316] Arranca el mantenedor de la librería y vuelve enseguida (G1-G3, DAY316)
         * @param ruta_config JSON con el que arrancó el ml-detector; se sube al etcd-server en cada registro
         */
        void arrancar(const std::string& ruta_config);

        /**
         * @brief Get the bronze HMAC key from etcd-server
         *
         * Calls GET /secrets/ml-detector — returns 64-char hex key (32 bytes).
         * Called at startup and every bronze_key.check_interval_seconds (ZMQHandler); the key signs the bronze.
         *
         * @return 64-char hex string, empty string on failure
         */
        std::string get_hmac_key() const;

    private:
        struct Impl;
        std::unique_ptr<Impl> pImpl;
    };
} // namespace ml_detector