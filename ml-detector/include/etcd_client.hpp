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
         * @brief Initialize connection and verify server availability
         * @return true if initialization successful
         */
        bool initialize();

        /**
         * @brief Register service with etcd-server and upload config
         * @return true if registration successful
         */
        bool registerService();

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