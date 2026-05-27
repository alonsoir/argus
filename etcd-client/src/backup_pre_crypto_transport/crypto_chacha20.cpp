// etcd-client/src/crypto_chacha20.cpp
#ifdef HAVE_LIBSODIUM

#include <sodium.h>
#include <string>
#include <vector>
#include <stdexcept>
#include <cstring>

namespace etcd_client {
namespace crypto {

// Initialize libsodium (call once at startup)
bool initialize_crypto() {
    static bool initialized = false;
    if (!initialized) {
        if (sodium_init() < 0) {
            return false;
        }
        initialized = true;
    }
    return true;
}

// Encrypt data using ChaCha20-Poly1305
// Returns: nonce (24 bytes) + ciphertext (plaintext_len + 16 MAC)
std::string encrypt_chacha20(const std::string& plaintext, const std::string& key) {
    if (!initialize_crypto()) {
        throw std::runtime_error("Failed to initialize libsodium");
    }
    
    if (key.size() != crypto_secretbox_KEYBYTES) {
        throw std::runtime_error("Invalid key size for ChaCha20 (expected " + 
                                 std::to_string(crypto_secretbox_KEYBYTES) + " bytes)");
    }
    
    if (plaintext.empty()) {
        return "";
    }
    
    // Generate random nonce
    std::vector<unsigned char> nonce(crypto_secretbox_NONCEBYTES);
    randombytes_buf(nonce.data(), nonce.size());
    
    // Allocate buffer for ciphertext (plaintext + MAC)
    std::vector<unsigned char> ciphertext(plaintext.size() + crypto_secretbox_MACBYTES);
    
    // Encrypt
    int ret = crypto_secretbox_easy(
        ciphertext.data(),
        reinterpret_cast<const unsigned char*>(plaintext.data()),
        plaintext.size(),
        nonce.data(),
        reinterpret_cast<const unsigned char*>(key.data())
    );
    
    if (ret != 0) {
        throw std::runtime_error("ChaCha20 encryption failed");
    }
    
    // Return: nonce + ciphertext
    std::string result;
    result.reserve(nonce.size() + ciphertext.size());
    result.append(reinterpret_cast<const char*>(nonce.data()), nonce.size());
    result.append(reinterpret_cast<const char*>(ciphertext.data()), ciphertext.size());
    
    return result;
}

// Decrypt data using ChaCha20-Poly1305
// Input: nonce (24 bytes) + ciphertext (plaintext_len + 16 MAC)
std::string decrypt_chacha20(const std::string& encrypted_data, const std::string& key) {
    if (!initialize_crypto()) {
        throw std::runtime_error("Failed to initialize libsodium");
    }
    
    if (key.size() != crypto_secretbox_KEYBYTES) {
        throw std::runtime_error("Invalid key size for ChaCha20 (expected " + 
                                 std::to_string(crypto_secretbox_KEYBYTES) + " bytes)");
    }
    
    if (encrypted_data.empty()) {
        return "";
    }
    
    // Minimum size: nonce + MAC
    size_t min_size = crypto_secretbox_NONCEBYTES + crypto_secretbox_MACBYTES;
    if (encrypted_data.size() < min_size) {
        throw std::runtime_error("Encrypted data too short (corrupted?)");
    }
    
    // Extract nonce
    const unsigned char* nonce = reinterpret_cast<const unsigned char*>(
        encrypted_data.data()
    );
    
    // Extract ciphertext
    const unsigned char* ciphertext = reinterpret_cast<const unsigned char*>(
        encrypted_data.data() + crypto_secretbox_NONCEBYTES
    );
    size_t ciphertext_len = encrypted_data.size() - crypto_secretbox_NONCEBYTES;
    
    // Allocate buffer for plaintext
    std::vector<unsigned char> plaintext(ciphertext_len - crypto_secretbox_MACBYTES);
    
    // Decrypt
    int ret = crypto_secretbox_open_easy(
        plaintext.data(),
        ciphertext,
        ciphertext_len,
        nonce,
        reinterpret_cast<const unsigned char*>(key.data())
    );
    
    if (ret != 0) {
        throw std::runtime_error("ChaCha20 decryption failed (wrong key or corrupted data)");
    }
    
    return std::string(reinterpret_cast<const char*>(plaintext.data()), plaintext.size());
}

// Generate a random encryption key
std::string generate_key() {
    if (!initialize_crypto()) {
        throw std::runtime_error("Failed to initialize libsodium");
    }
    
    std::vector<unsigned char> key(crypto_secretbox_KEYBYTES);
    randombytes_buf(key.data(), key.size());
    
    return std::string(reinterpret_cast<const char*>(key.data()), key.size());
}

// Get required key size
size_t get_key_size() {
    return crypto_secretbox_KEYBYTES;
}

} // namespace crypto
} // namespace etcd_client

#endif // HAVE_LIBSODIUM
