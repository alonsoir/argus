#pragma once
#ifndef FIREWALL_ETCD_CLIENT_HPP
#define FIREWALL_ETCD_CLIENT_HPP

#include <etcd_client/etcd_client.hpp>  // ✅ Day 59: For ServicePaths
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
         * @param endpoint etcd server endpoint (e.g., "localhost:2379")
         * @param component_name Component identifier (e.g., "firewall-acl-agent")
         */
        EtcdClient(const std::string& endpoint, const std::string& component_name);

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
        * @brief Get crypto seed from etcd-server
        * @return Crypto seed in hex format (64 chars)
        */
        std::string get_crypto_seed() const;

        /**
     * @brief Get HMAC key from etcd-server (Day 58)
     * @param key_path Path to key in etcd (e.g., "/secrets/firewall/log_hmac_key")
     * @return HMAC key as bytes (32 bytes), or nullopt if not found
     */
        std::optional<std::vector<uint8_t>> get_hmac_key(const std::string& key_path);

        /**
         * @brief Compute HMAC-SHA256 signature (Day 58)
         * @param data Data to sign (e.g., CSV line)
         * @param key HMAC key (32 bytes)
         * @return HMAC signature as hex string (64 chars)
         */
        std::string compute_hmac_sha256(const std::string& data,
                                        const std::vector<uint8_t>& key);

        /**
         * @brief Convert bytes to hex string (Day 58)
         * @param bytes Binary data
         * @return Hex-encoded string
         */
        std::string bytes_to_hex(const std::vector<uint8_t>& bytes);

        // ============================================================================
        // Day 59: Service Discovery
        // ============================================================================

        /**
         * @brief Get service discovery paths from etcd-server
         *
         * Returns paths where this component should find HMAC keys, crypto tokens, etc.
         * These paths are received during component registration and owned by etcd-server.
         *
         * @return ServicePaths structure with paths, or invalid paths if not registered
         */
        etcd_client::ServicePaths get_service_paths() const;
    private:
        struct Impl;
        std::unique_ptr<Impl> pImpl;
    };

} // namespace mldefender::firewall
#endif