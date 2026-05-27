// /vagrant/etcd-server/src/secrets_manager.cpp
// Day 54: HMAC Secrets Manager Implementation
//
// Co-authored-by: Claude (Anthropic)
// Co-authored-by: Alonso

#include "etcd_server/secrets_manager.hpp"
#include <openssl/rand.h>
#include <iomanip>
#include <sstream>
#include <algorithm>

namespace etcd_server {

    SecretsManager::SecretsManager(const nlohmann::json& config)
        : logger_(spdlog::get("etcd_server") ? spdlog::get("etcd_server") : spdlog::default_logger()),
          grace_period_seconds_(config["secrets"]["grace_period_seconds"].get<int>()),
          rotation_interval_hours_(config["secrets"]["rotation_interval_hours"].get<int>()),
          default_key_length_bytes_(config["secrets"]["default_key_length_bytes"].get<int>()),
          min_rotation_interval_seconds_(config["secrets"]["min_rotation_interval_seconds"].get<int>())
    {
        // Validación CRÍTICA (ADR-004)
        if (min_rotation_interval_seconds_ < grace_period_seconds_) {
            logger_->critical("UNSAFE CONFIG: min_rotation_interval ({}) < grace_period ({}) - Risk of key accumulation!",
                              min_rotation_interval_seconds_, grace_period_seconds_);
            throw std::runtime_error("Invalid config: min_rotation_interval must be >= grace_period");
        }

        // Validate grace period
        if (grace_period_seconds_ <= 0) {
            logger_->warn("Invalid grace_period_seconds: {}, using default: 300s",
                          grace_period_seconds_);
            const_cast<int&>(grace_period_seconds_) = 300;
        }

        logger_->info("SecretsManager initialized from JSON config:");
        logger_->info("  - Grace period: {}s (system-wide)", grace_period_seconds_);
        logger_->info("  - min_rotation_interval_seconds: {}s (system-wide)", min_rotation_interval_seconds_);
        logger_->info("  - Rotation interval: {}h", rotation_interval_hours_);
        logger_->info("  - Default key length: {} bytes", default_key_length_bytes_);
}

HMACKey SecretsManager::generate_hmac_key(const std::string& component) {
    logger_->info("Generating new HMAC key for component: {}", component);

    // Generate random key material
    auto random_bytes = generate_random_bytes(default_key_length_bytes_);

    // Hex encode
    std::string key_data = bytes_to_hex(random_bytes);

    // Create key structure
    HMACKey key;
    key.key_data = key_data;
    key.created_at = std::chrono::system_clock::now();
    key.expires_at = std::chrono::system_clock::time_point::max();  // Never expires (active key)
    key.is_active = true;
    key.component = component;

    // Store in memory
    store_key(key);

    logger_->info("Generated HMAC key for {}: {} bytes, created at {}",
                  component, default_key_length_bytes_, format_time(key.created_at));

    return key;
}

HMACKey SecretsManager::rotate_hmac_key(const std::string& component, bool force) {
    auto now = std::chrono::system_clock::now();

    logger_->info("Rotation requested for component: {} (force={})", component, force);

    // ADR-004: Cooldown enforcement
    if (!force && last_rotation_.count(component)) {
        auto elapsed = now - last_rotation_[component];
        auto min_interval = std::chrono::seconds(min_rotation_interval_seconds_);

        if (elapsed < min_interval) {
            auto remaining = std::chrono::duration_cast<std::chrono::seconds>(min_interval - elapsed);
            logger_->warn("Rotation REJECTED for {} - cooldown active ({}s remaining)",
                          component, remaining.count());
            throw std::runtime_error("Rotation too soon, retry in " +
                                     std::to_string(remaining.count()) + "s");
        }
    }

    if (force) {
        logger_->warn("EMERGENCY rotation for {} (force=true) - cooldown bypassed", component);
    }

    // Get current active key (if exists)
    auto existing_keys = list_hmac_keys(component);

    if (!existing_keys.empty()) {
        // Mark old active key with expiry time
        for (auto& old_key : existing_keys) {
            if (old_key.is_active) {
                old_key.is_active = false;
                old_key.expires_at = now + std::chrono::seconds(grace_period_seconds_);

                logger_->info("Old key marked for grace period expiry at: {}",
                              format_time(old_key.expires_at));

                // Update in storage
                store_key(old_key);
                break;
            }
        }
    }

    // Generate new active key
    auto new_key = generate_hmac_key(component);

    // Update last rotation timestamp
    last_rotation_[component] = now;

    logger_->info("Key rotation complete for {}: old key valid until {}",
                  component,
                  existing_keys.empty() ? "N/A" : format_time(existing_keys[0].expires_at));

    return new_key;
}

HMACKey SecretsManager::get_hmac_key(const std::string& component) {
    auto keys = list_hmac_keys(component);

    // Find active key
    for (const auto& key : keys) {
        if (key.is_active) {
            return key;
        }
    }

    // No active key found - generate one
    logger_->warn("No active HMAC key found for {}, generating new key", component);
    return generate_hmac_key(component);
}

std::vector<HMACKey> SecretsManager::list_hmac_keys(const std::string& component) {
    std::lock_guard<std::mutex> lock(storage_mutex_);

    auto it = keys_storage_.find(component);
    if (it != keys_storage_.end()) {
        return it->second;
    }

    return {};
}

std::vector<HMACKey> SecretsManager::get_valid_keys(
    const std::string& component,
    std::chrono::system_clock::time_point now
) {
    auto all_keys = list_hmac_keys(component);
    std::vector<HMACKey> valid_keys;

    // Filter for valid keys (not expired)
    for (const auto& key : all_keys) {
        if (is_key_valid(key, now)) {
            valid_keys.push_back(key);
        }
    }

    // Sort: active key first, then by creation time descending
    std::sort(valid_keys.begin(), valid_keys.end(),
        [](const HMACKey& a, const HMACKey& b) {
            if (a.is_active != b.is_active) {
                return a.is_active;  // Active keys first
            }
            return a.created_at > b.created_at;  // Newer keys first
        });

    logger_->debug("Found {} valid keys for {} (active + grace period)",
                   valid_keys.size(), component);

    return valid_keys;
}

bool SecretsManager::is_key_valid(
    const HMACKey& key,
    std::chrono::system_clock::time_point now
) {
    return now < key.expires_at;
}

void SecretsManager::store_key(const HMACKey& key) {
    std::lock_guard<std::mutex> lock(storage_mutex_);

    auto& keys = keys_storage_[key.component];

    // Check if key already exists (update case)
    bool found = false;
    for (auto& existing : keys) {
        if (existing.created_at == key.created_at) {
            existing = key;
            found = true;
            break;
        }
    }

    // Add new key
    if (!found) {
        keys.push_back(key);
    }

    // Sort by creation time (newest first)
    std::sort(keys.begin(), keys.end(),
        [](const HMACKey& a, const HMACKey& b) {
            return a.created_at > b.created_at;
        });

    logger_->debug("Stored key for component: {}", key.component);
}

std::vector<uint8_t> SecretsManager::generate_random_bytes(size_t length) {
    std::vector<uint8_t> bytes(length);

    if (RAND_bytes(bytes.data(), static_cast<int>(length)) != 1) {
        logger_->error("RAND_bytes failed");
        throw std::runtime_error("Failed to generate random bytes");
    }

    return bytes;
}

std::string SecretsManager::format_time(std::chrono::system_clock::time_point tp) {
    auto time_t_val = std::chrono::system_clock::to_time_t(tp);
    std::ostringstream oss;
    oss << std::put_time(std::gmtime(&time_t_val), "%Y-%m-%dT%H:%M:%SZ");
    return oss.str();
}

std::chrono::system_clock::time_point SecretsManager::parse_time(const std::string& time_str) {
    std::tm tm = {};
    std::istringstream ss(time_str);
    ss >> std::get_time(&tm, "%Y-%m-%dT%H:%M:%SZ");

    if (ss.fail()) {
        logger_->error("Failed to parse time string: {}", time_str);
        return std::chrono::system_clock::now();
    }

    return std::chrono::system_clock::from_time_t(std::mktime(&tm));
}

std::string SecretsManager::bytes_to_hex(const std::vector<uint8_t>& bytes) {
    std::ostringstream oss;
    oss << std::hex << std::setfill('0');

    for (uint8_t byte : bytes) {
        oss << std::setw(2) << static_cast<int>(byte);
    }

    return oss.str();
}

} // namespace etcd_server