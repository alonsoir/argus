// crypto-transport/src/crypto.cpp
#include "crypto_transport/crypto.hpp"
#include "crypto_transport/utils.hpp"
#include <sodium.h>
#include <stdexcept>
#include <cstring>

namespace crypto_transport {

std::vector<uint8_t> encrypt(const std::vector<uint8_t>& data,
                              const std::vector<uint8_t>& key) {
    // Validate key size
    if (key.size() != crypto_secretbox_KEYBYTES) {
        throw std::runtime_error("Invalid key size for ChaCha20 (expected " +
                                 std::to_string(crypto_secretbox_KEYBYTES) +
                                 " bytes, got " + std::to_string(key.size()) + ")");
    }

    // Handle empty data
    if (data.empty()) {
        return {};
    }

    // Generate random nonce (24 bytes for XSalsa20)
    std::vector<uint8_t> nonce(crypto_secretbox_NONCEBYTES);
    randombytes_buf(nonce.data(), nonce.size());

    // Allocate buffer for ciphertext (plaintext + 16-byte MAC)
    std::vector<uint8_t> ciphertext(data.size() + crypto_secretbox_MACBYTES);

    // Encrypt with ChaCha20-Poly1305
    int ret = crypto_secretbox_easy(
        ciphertext.data(),
        data.data(),
        data.size(),
        nonce.data(),
        key.data()
    );

    if (ret != 0) {
        throw std::runtime_error("ChaCha20 encryption failed");
    }

    // Return: nonce (24) + ciphertext (N + 16)
    std::vector<uint8_t> result;
    result.reserve(nonce.size() + ciphertext.size());
    result.insert(result.end(), nonce.begin(), nonce.end());
    result.insert(result.end(), ciphertext.begin(), ciphertext.end());

    return result;
}

std::vector<uint8_t> decrypt(const std::vector<uint8_t>& encrypted_data,
                              const std::vector<uint8_t>& key) {
    // Validate key size
    if (key.size() != crypto_secretbox_KEYBYTES) {
        throw std::runtime_error("Invalid key size for ChaCha20 (expected " +
                                 std::to_string(crypto_secretbox_KEYBYTES) +
                                 " bytes, got " + std::to_string(key.size()) + ")");
    }

    // Handle empty data
    if (encrypted_data.empty()) {
        return {};
    }

    // Minimum size: nonce (24) + MAC (16)
    const size_t min_size = crypto_secretbox_NONCEBYTES + crypto_secretbox_MACBYTES;
    if (encrypted_data.size() < min_size) {
        throw std::runtime_error("Encrypted data too short (expected at least " +
                                 std::to_string(min_size) + " bytes, got " +
                                 std::to_string(encrypted_data.size()) +
                                 " - corrupted?)");
    }

    // Extract nonce (first 24 bytes)
    const uint8_t* nonce = encrypted_data.data();

    // Extract ciphertext (remaining bytes)
    const uint8_t* ciphertext = encrypted_data.data() + crypto_secretbox_NONCEBYTES;
    size_t ciphertext_len = encrypted_data.size() - crypto_secretbox_NONCEBYTES;

    // Allocate buffer for plaintext (ciphertext - MAC)
    std::vector<uint8_t> plaintext(ciphertext_len - crypto_secretbox_MACBYTES);

    // Decrypt and verify MAC
    int ret = crypto_secretbox_open_easy(
        plaintext.data(),
        ciphertext,
        ciphertext_len,
        nonce,
        key.data()
    );

    if (ret != 0) {
        throw std::runtime_error("ChaCha20 decryption failed (wrong key or corrupted data)");
    }

    return plaintext;
}

std::vector<uint8_t> generate_key() {
    std::vector<uint8_t> key(crypto_secretbox_KEYBYTES);
    randombytes_buf(key.data(), key.size());
    return key;
}

} // namespace crypto_transport