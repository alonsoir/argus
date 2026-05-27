// crypto-transport/tests/test_crypto.cpp
#include "crypto_transport/crypto.hpp"
#include "crypto_transport/utils.hpp"
#include <iostream>
#include <cassert>
#include <string>
#include <cstring>

using namespace crypto_transport;

void test_key_size() {
    std::cout << "TEST: Key size validation... ";

    size_t expected_size = get_key_size();
    assert(expected_size == 32);  // ChaCha20 uses 32-byte keys

    std::cout << "✅ PASS" << std::endl;
}

void test_generate_key() {
    std::cout << "TEST: Generate random key... ";

    auto key1 = generate_key();
    auto key2 = generate_key();

    assert(key1.size() == 32);
    assert(key2.size() == 32);
    assert(key1 != key2);  // Keys should be different (random)

    std::cout << "✅ PASS" << std::endl;
}

void test_encrypt_decrypt_basic() {
    std::cout << "TEST: Basic encrypt/decrypt... ";

    auto key = generate_key();
    std::string plaintext = "Hello, crypto-transport!";
    std::vector<uint8_t> data(plaintext.begin(), plaintext.end());

    // Encrypt
    auto encrypted = encrypt(data, key);
    assert(!encrypted.empty());
    assert(encrypted.size() > data.size());  // nonce + MAC overhead

    // Decrypt
    auto decrypted = decrypt(encrypted, key);
    assert(decrypted == data);

    std::string result(decrypted.begin(), decrypted.end());
    assert(result == plaintext);

    std::cout << "✅ PASS" << std::endl;
}

void test_empty_data() {
    std::cout << "TEST: Empty data handling... ";

    auto key = generate_key();
    std::vector<uint8_t> empty;

    auto encrypted = encrypt(empty, key);
    assert(encrypted.empty());

    auto decrypted = decrypt(empty, key);
    assert(decrypted.empty());

    std::cout << "✅ PASS" << std::endl;
}

void test_invalid_key_size() {
    std::cout << "TEST: Invalid key size detection... ";

    std::vector<uint8_t> data = {1, 2, 3, 4, 5};
    std::vector<uint8_t> bad_key = {1, 2, 3};  // Too small

    bool caught_exception = false;
    try {
        encrypt(data, bad_key);
    } catch (const std::runtime_error& e) {
        caught_exception = true;
        assert(std::string(e.what()).find("Invalid key size") != std::string::npos);
    }
    assert(caught_exception);

    std::cout << "✅ PASS" << std::endl;
}

void test_wrong_key() {
    std::cout << "TEST: Wrong key detection... ";

    auto key1 = generate_key();
    auto key2 = generate_key();
    std::vector<uint8_t> data = {1, 2, 3, 4, 5};

    auto encrypted = encrypt(data, key1);

    bool caught_exception = false;
    try {
        decrypt(encrypted, key2);  // Wrong key
    } catch (const std::runtime_error& e) {
        caught_exception = true;
        assert(std::string(e.what()).find("decryption failed") != std::string::npos);
    }
    assert(caught_exception);

    std::cout << "✅ PASS" << std::endl;
}

void test_corrupted_data() {
    std::cout << "TEST: Corrupted data detection... ";

    auto key = generate_key();
    std::vector<uint8_t> data = {1, 2, 3, 4, 5};

    auto encrypted = encrypt(data, key);

    // Corrupt the data
    if (!encrypted.empty()) {
        encrypted[encrypted.size() / 2] ^= 0xFF;
    }

    bool caught_exception = false;
    try {
        decrypt(encrypted, key);
    } catch (const std::runtime_error& e) {
        caught_exception = true;
    }
    assert(caught_exception);

    std::cout << "✅ PASS" << std::endl;
}

void test_hex_conversion() {
    std::cout << "TEST: Hex conversion integration... ";

    // Generate key and convert to hex
    auto key = generate_key();
    std::string hex = bytes_to_hex(key);
    assert(hex.length() == 64);  // 32 bytes = 64 hex chars

    // Convert back
    auto key_restored = hex_to_bytes(hex);
    assert(key_restored == key);

    // Test encrypt/decrypt with hex-converted key
    std::vector<uint8_t> data = {1, 2, 3, 4, 5};
    auto encrypted = encrypt(data, key_restored);
    auto decrypted = decrypt(encrypted, key);
    assert(decrypted == data);

    std::cout << "✅ PASS" << std::endl;
}

void test_large_data() {
    std::cout << "TEST: Large data (1MB)... ";

    auto key = generate_key();

    // Create 1MB of data
    std::vector<uint8_t> large_data(1024 * 1024);
    for (size_t i = 0; i < large_data.size(); ++i) {
        large_data[i] = static_cast<uint8_t>(i % 256);
    }

    auto encrypted = encrypt(large_data, key);
    auto decrypted = decrypt(encrypted, key);

    assert(decrypted == large_data);

    std::cout << "✅ PASS" << std::endl;
}

int main() {
    std::cout << "========================================" << std::endl;
    std::cout << "crypto-transport: Crypto Tests" << std::endl;
    std::cout << "========================================" << std::endl;

    try {
        test_key_size();
        test_generate_key();
        test_encrypt_decrypt_basic();
        test_empty_data();
        test_invalid_key_size();
        test_wrong_key();
        test_corrupted_data();
        test_hex_conversion();
        test_large_data();

        std::cout << "========================================" << std::endl;
        std::cout << "✅ All crypto tests PASSED!" << std::endl;
        std::cout << "========================================" << std::endl;
        return 0;

    } catch (const std::exception& e) {
        std::cerr << "❌ TEST FAILED: " << e.what() << std::endl;
        return 1;
    }
}