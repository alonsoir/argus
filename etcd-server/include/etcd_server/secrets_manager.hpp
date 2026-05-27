// /vagrant/etcd-server/include/etcd_server/secrets_manager.hpp
// Day 54: HMAC Secrets Manager with Grace Period Support
//
// Co-authored-by: Claude (Anthropic)
// Co-authored-by: Alonso

#pragma once

#include <string>
#include <vector>
#include <memory>
#include <chrono>
#include <nlohmann/json.hpp>
#include "spdlog/spdlog.h"

namespace etcd_server {

/**
 * @brief HMAC Key structure with grace period metadata
 */
struct HMACKey {
    std::string key_data;                              // Hex-encoded key bytes
    std::chrono::system_clock::time_point created_at;  // Creation timestamp
    std::chrono::system_clock::time_point expires_at;  // Expiration timestamp (created_at + grace_period after rotation)
    bool is_active;                                     // true = current key, false = grace period only
    std::string component;                              // Component name (e.g., "rag-ingester")
};

/**
 * @brief Manages HMAC secrets for log integrity with zero-downtime rotation
 *
 * Features:
 * - HMAC-SHA256 key generation (256-bit)
 * - Key rotation with configurable grace period
 * - System-wide grace period (NO per-component override)
 * - All config from JSON (zero hardcoding)
 *
 * Architecture:
 * - Reads config from nlohmann::json (etcd_server.json)
 * - Grace period applies to ALL components
 * - Old keys valid for grace_period_seconds after rotation
 *
 * Via Appia Quality: Piano piano, cada fase 100% testeada
 */
class SecretsManager {
public:
    /**
     * @brief Constructor with nlohmann::json configuration
     *
     * @param config JSON object from etcd_server.json
     *
     * Required config structure:
     * {
     *   "secrets": {
     *     "grace_period_seconds": 300,
     *     "rotation_interval_hours": 168,
     *     "default_key_length_bytes": 32
     *   }
     * }
     */
    struct Config {
        bool enabled = true;
        int default_key_length = 32;
        int rotation_interval_hours = 168;
        bool auto_generate_on_startup = true;

        // Day 54: AÑADIR ESTA LÍNEA
        int grace_period_seconds = 300;
		// Day 56: Cooldown window (ADR-004)
    	int min_rotation_interval_seconds = 300;
    };

    explicit SecretsManager(const nlohmann::json& config);

    /**
     * @brief Generate new HMAC key for component
     *
     * @param component Component name (e.g., "rag-ingester")
     * @return HMACKey Generated key with metadata
     */
    HMACKey generate_hmac_key(const std::string& component);

    /**
 	* @brief Rotate HMAC key with grace period and cooldown enforcement
 	*
 	* Old key marked with:
 	* - is_active = false
 	* - expires_at = now + grace_period_seconds
 	*
 	* Cooldown: Rotation rejected if last rotation < min_rotation_interval_seconds ago
 	*
 	* @param component Component name
 	* @param force Emergency override (bypasses cooldown, requires logging)
 	* @return HMACKey New active key
 	* @throws std::runtime_error if cooldown not elapsed and force=false
 	*/
	HMACKey rotate_hmac_key(const std::string& component, bool force = false);

    /**
     * @brief Get current active key for component
     *
     * @param component Component name
     * @return HMACKey Active key (is_active = true)
     */
    HMACKey get_hmac_key(const std::string& component);

    /**
     * @brief List all keys for component (active + grace + expired)
     *
     * @param component Component name
     * @return std::vector<HMACKey> All keys, sorted by creation time (newest first)
     */
    std::vector<HMACKey> list_hmac_keys(const std::string& component);

    /**
     * @brief Get all valid keys (active + grace period, excluding expired)
     *
     * @param component Component name
     * @param now Current time (for testing)
     * @return std::vector<HMACKey> Valid keys, sorted (active first, then by age)
     */
    std::vector<HMACKey> get_valid_keys(
        const std::string& component,
        std::chrono::system_clock::time_point now = std::chrono::system_clock::now()
    );

    /**
     * @brief Check if key is still valid (not expired)
     *
     * @param key Key to check
     * @param now Current time (for testing)
     * @return bool True if now < expires_at
     */
    bool is_key_valid(
        const HMACKey& key,
        std::chrono::system_clock::time_point now = std::chrono::system_clock::now()
    );

    /**
     * @brief Get configured grace period
     *
     * @return int Grace period in seconds
     */
    int get_grace_period_seconds() const { return grace_period_seconds_; }

	/**
     * @brief Format time_point to ISO8601 string
     */
    std::string format_time(std::chrono::system_clock::time_point tp);

private:
    std::shared_ptr<spdlog::logger> logger_;

    // Configuration (immutable after construction, from JSON)
    const int grace_period_seconds_;       // System-wide grace period
    const int rotation_interval_hours_;
    const int default_key_length_bytes_;
    const int min_rotation_interval_seconds_;


    // In-memory storage (TODO Day 55: Integrate with actual etcd)
    std::map<std::string, std::vector<HMACKey>> keys_storage_;
    std::mutex storage_mutex_;
    std::map<std::string, std::chrono::system_clock::time_point> last_rotation_;


    /**
     * @brief Store key in memory (TODO: Replace with etcd)
     */
    void store_key(const HMACKey& key);

    /**
     * @brief Generate random bytes for key material
     */
    std::vector<uint8_t> generate_random_bytes(size_t length);

    /**
     * @brief Parse ISO8601 string to time_point
     */
    std::chrono::system_clock::time_point parse_time(const std::string& time_str);

    /**
     * @brief Convert bytes to hex string
     */
    static std::string bytes_to_hex(const std::vector<uint8_t>& bytes);
};

} // namespace etcd_server