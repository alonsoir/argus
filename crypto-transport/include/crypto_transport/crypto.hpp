#pragma once

#include <vector>
#include <cstdint>

namespace crypto_transport {

    /**
     * Encrypt data using ChaCha20-Poly1305 AEAD
     * @param data Plaintext data to encrypt
     * @param key Encryption key (must be 32 bytes, use get_key_size())
     * @return Encrypted data: [nonce(24) || ciphertext(N) || mac(16)]
     * @throws std::runtime_error if encryption fails or key size is invalid
     *
     * Note: Returns empty vector if input is empty
     * Format: Random nonce + authenticated ciphertext
     * Security: MAC provides authentication and integrity
     */
    std::vector<uint8_t> encrypt(const std::vector<uint8_t>& data,
                                  const std::vector<uint8_t>& key);

    /**
     * Decrypt ChaCha20-Poly1305 encrypted data
     * @param encrypted_data Encrypted data from encrypt()
     * @param key Decryption key (must be 32 bytes)
     * @return Decrypted plaintext data
     * @throws std::runtime_error if decryption fails, wrong key, or corrupted data
     *
     * Note: Returns empty vector if input is empty
     * Security: MAC verification ensures data integrity and authenticity
     * Fail-fast: Throws immediately on MAC verification failure
     */
    std::vector<uint8_t> decrypt(const std::vector<uint8_t>& encrypted_data,
                                  const std::vector<uint8_t>& key);

    /**
     * Generate a cryptographically secure random encryption key
     * @return Random 32-byte key suitable for ChaCha20-Poly1305
     *
     * Note: Uses libsodium's secure random number generator
     * Warning: Key generation is for testing only - production keys come from etcd-server
     */
    std::vector<uint8_t> generate_key();

} // namespace crypto_transport