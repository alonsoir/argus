// =============================================================================
// DEPRECATED DAY 98 — CryptoManager (etcd-server local)
// Sustituido por CryptoTransport (ADR-013 PHASE 2, ADR-020)
// NO usar en código nuevo. Pendiente de borrado en sesión futura.
// Usar: SeedClient + crypto_transport::CryptoTransport
// =============================================================================
#pragma once

#include <string>
#include <memory>
#include <chrono>
#include <crypto_transport/crypto_manager.hpp>

/**
 * @brief Wrapper around crypto::CryptoManager for etcd-server
 * Compatible with existing component_registry interface
 */
class CryptoManager {
private:
    std::unique_ptr<crypto::CryptoManager> crypto_;
    std::string seed_;  // Binary seed (32 bytes)
    std::chrono::system_clock::time_point key_generation_time_;

    static constexpr size_t KEY_SIZE = 32;  // 256 bits

public:
    /**
     * @brief Default constructor - generates random seed
     */
    CryptoManager();

    // Seed management - returns HEX for JSON compatibility
    std::string get_current_seed() const {
        return bytes_to_hex(seed_);
    }

    std::string get_encryption_key() const {
        return bytes_to_hex(seed_);
    }

    bool should_rotate_key() const;
    void rotate_key();

    // Encryption/Decryption (binary format, NOT hex)
    std::string encrypt(const std::string& plaintext);
    std::string decrypt(const std::string& ciphertext);

    // Validation
    bool validate_ciphertext(const std::string& ciphertext);

private:
    std::string generate_random_seed();
    std::string bytes_to_hex(const std::string& bytes) const;
    std::string hex_to_bytes(const std::string& hex) const;
};