// crypto-transport/src/utils.cpp
#include "crypto_transport/utils.hpp"
#include <sodium.h>
#include <stdexcept>
#include <iomanip>
#include <sstream>

namespace crypto_transport {

    // Initialize libsodium (thread-safe, called automatically)
    namespace {
        struct SodiumInitializer {
            SodiumInitializer() {
                if (sodium_init() < 0) {
                    throw std::runtime_error("Failed to initialize libsodium");
                }
            }
        };

        // Global initializer (runs once at program startup)
        static SodiumInitializer g_sodium_init;
    }

    std::vector<uint8_t> hex_to_bytes(const std::string& hex) {
        if (hex.empty()) {
            return {};
        }

        if (hex.length() % 2 != 0) {
            throw std::runtime_error("Hex string must have even length");
        }

        std::vector<uint8_t> bytes;
        bytes.reserve(hex.length() / 2);

        for (size_t i = 0; i < hex.length(); i += 2) {
            std::string byte_str = hex.substr(i, 2);
            try {
                uint8_t byte = static_cast<uint8_t>(std::stoi(byte_str, nullptr, 16));
                bytes.push_back(byte);
            } catch (const std::exception& e) {
                throw std::runtime_error("Invalid hex character at position " +
                                         std::to_string(i) + ": " + e.what());
            }
        }

        return bytes;
    }

    std::string bytes_to_hex(const std::vector<uint8_t>& bytes) {
        if (bytes.empty()) {
            return "";
        }

        std::ostringstream oss;
        oss << std::hex << std::setfill('0');

        for (uint8_t byte : bytes) {
            oss << std::setw(2) << static_cast<int>(byte);
        }

        return oss.str();
    }

    size_t get_key_size() {
        return crypto_secretbox_KEYBYTES;  // 32 bytes for ChaCha20-Poly1305
    }

} // namespace crypto_transport