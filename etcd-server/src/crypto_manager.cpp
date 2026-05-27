// =============================================================================
// DEPRECATED DAY 98 — CryptoManager (etcd-server local)
// Sustituido por CryptoTransport (ADR-013 PHASE 2, ADR-020)
// NO usar en código nuevo. Pendiente de borrado en sesión futura.
// =============================================================================
#include "etcd_server/crypto_manager.hpp"
#include <random>
#include <iostream>
#include <iomanip>
#include <sstream>
#include <stdexcept>
#include <sodium.h>

CryptoManager::CryptoManager()
    : key_generation_time_(std::chrono::system_clock::now())
{
    // Initialize libsodium
    if (sodium_init() < 0) {
        throw std::runtime_error("Failed to initialize libsodium");
    }

    // Generate random seed
    seed_ = generate_random_seed();

    // Create crypto_transport manager
    crypto_ = std::make_unique<crypto::CryptoManager>(seed_);

    // Display seed in hex for logging
    std::cout << "[CRYPTO] 🔑 Clave derivada con HKDF desde seed" << std::endl;
    std::cout << "[CRYPTO]   Key: " << bytes_to_hex(seed_) << std::endl;
    std::cout << "[CRYPTO] ✅ Sistema de cifrado inicializado con seed: "
              << bytes_to_hex(seed_) << std::endl;
}

bool CryptoManager::should_rotate_key() const {
    auto now = std::chrono::system_clock::now();
    auto elapsed = std::chrono::duration_cast<std::chrono::hours>(
        now - key_generation_time_
    ).count();

    // Rotate every 24 hours
    return elapsed >= 24;
}

void CryptoManager::rotate_key() {
    seed_ = generate_random_seed();
    crypto_ = std::make_unique<crypto::CryptoManager>(seed_);
    key_generation_time_ = std::chrono::system_clock::now();

    std::cout << "[CRYPTO] 🔄 Clave de cifrado rotada" << std::endl;
}

std::string CryptoManager::encrypt(const std::string& plaintext) {
    try {
        // Use crypto-transport (returns binary)
        std::string ciphertext = crypto_->encrypt(plaintext);

        std::cout << "[CRYPTO] 🔒 Cifrado ChaCha20: " << plaintext.size()
                  << " bytes -> " << ciphertext.size() << " bytes" << std::endl;

        return ciphertext;
    } catch (const std::exception& e) {
        std::cerr << "[CRYPTO] ❌ Error cifrando: " << e.what() << std::endl;
        throw;
    }
}

std::string CryptoManager::decrypt(const std::string& ciphertext) {
    try {
        // Use crypto-transport (expects binary)
        std::string plaintext = crypto_->decrypt(ciphertext);

        std::cout << "[CRYPTO] 🔓 Descifrado ChaCha20: " << ciphertext.size()
                  << " bytes -> " << plaintext.size() << " bytes" << std::endl;

        return plaintext;
    } catch (const std::exception& e) {
        std::cerr << "[CRYPTO] ❌ Error descifrando: " << e.what() << std::endl;
        throw;
    }
}

bool CryptoManager::validate_ciphertext(const std::string& ciphertext) {
    // Minimum size: nonce (24) + MAC (16) = 40 bytes
    return ciphertext.size() >= 40;
}

std::string CryptoManager::generate_random_seed() {
    std::string seed;
    seed.resize(KEY_SIZE);

    // Use libsodium for cryptographically secure random
    randombytes_buf(reinterpret_cast<unsigned char*>(&seed[0]), KEY_SIZE);

    return seed;
}

std::string CryptoManager::bytes_to_hex(const std::string& bytes) const {
    std::ostringstream oss;
    oss << std::hex << std::setfill('0') << std::uppercase;

    for (unsigned char c : bytes) {
        oss << std::setw(2) << static_cast<int>(c);
    }

    return oss.str();
}

std::string CryptoManager::hex_to_bytes(const std::string& hex) const {
    if (hex.size() % 2 != 0) {
        throw std::runtime_error("Invalid hex string: odd length");
    }

    std::string bytes;
    bytes.reserve(hex.size() / 2);

    for (size_t i = 0; i < hex.size(); i += 2) {
        std::string byte_str = hex.substr(i, 2);
        char byte = static_cast<char>(std::stoi(byte_str, nullptr, 16));
        bytes.push_back(byte);
    }

    return bytes;
}