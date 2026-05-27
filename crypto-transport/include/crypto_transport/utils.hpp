#pragma once

#include <string>
#include <vector>
#include <cstdint>

namespace crypto_transport {

    /**
     * Convert hexadecimal string to bytes
     * @param hex Hexadecimal string (must have even length)
     * @return Binary data as vector of bytes
     * @throws std::runtime_error if hex string is invalid
     */
    std::vector<uint8_t> hex_to_bytes(const std::string& hex);

    /**
     * Convert bytes to hexadecimal string
     * @param bytes Binary data
     * @return Hexadecimal string representation
     */
    std::string bytes_to_hex(const std::vector<uint8_t>& bytes);

    /**
     * Get required encryption key size for ChaCha20-Poly1305
     * @return Key size in bytes (32 for ChaCha20)
     */
    size_t get_key_size();

} // namespace crypto_transport