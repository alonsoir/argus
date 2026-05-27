// etcd-client/tests/test_encryption.cpp
#include <crypto_transport/crypto.hpp>
#include <crypto_transport/utils.hpp>
#include <iostream>
#include <string>
#include <cassert>
#include <vector>
#include <cstdint>

using namespace crypto_transport;

// Helper functions for string <-> vector conversion
namespace {
    inline std::vector<uint8_t> string_to_bytes(const std::string& str) {
        return std::vector<uint8_t>(str.begin(), str.end());
    }

    inline std::string bytes_to_string(const std::vector<uint8_t>& bytes) {
        return std::string(bytes.begin(), bytes.end());
    }
}

void test_encrypt_decrypt_simple() {
    std::cout << "\n🧪 Test 1: Simple encrypt/decrypt" << std::endl;

    // Generate key
    auto key = generate_key();
    std::cout << "Key size: " << key.size() << " bytes (expected: " << get_key_size() << ")" << std::endl;
    assert(key.size() == get_key_size());

    std::string plaintext = "Hello, World! This is a secret message.";
    std::cout << "Plaintext: \"" << plaintext << "\" (" << plaintext.size() << " bytes)" << std::endl;

    auto data = string_to_bytes(plaintext);

    // Encrypt
    auto encrypted = encrypt(data, key);
    std::cout << "Encrypted: " << encrypted.size() << " bytes (plaintext + nonce + MAC)" << std::endl;

    // Verify encrypted data is larger (nonce + MAC overhead)
    assert(encrypted.size() > data.size());

    // Decrypt
    auto decrypted = decrypt(encrypted, key);
    std::cout << "Decrypted: " << decrypted.size() << " bytes" << std::endl;

    // Verify
    std::string result = bytes_to_string(decrypted);
    assert(plaintext == result);
    std::cout << "✅ Test 1 PASSED: Plaintext matches after encrypt/decrypt" << std::endl;
}

void test_encrypt_large_data() {
    std::cout << "\n🧪 Test 2: Large data encryption (10KB)" << std::endl;

    auto key = generate_key();

    // Generate 10KB of data
    std::string plaintext;
    for (int i = 0; i < 10240; ++i) {
        plaintext += static_cast<char>('A' + (i % 26));
    }
    std::cout << "Plaintext: " << plaintext.size() << " bytes" << std::endl;

    auto data = string_to_bytes(plaintext);

    // Encrypt
    auto encrypted = encrypt(data, key);
    std::cout << "Encrypted: " << encrypted.size() << " bytes" << std::endl;

    // Decrypt
    auto decrypted = decrypt(encrypted, key);

    // Verify
    std::string result = bytes_to_string(decrypted);
    assert(plaintext == result);
    std::cout << "✅ Test 2 PASSED: Large data matches" << std::endl;
}

void test_wrong_key_fails() {
    std::cout << "\n🧪 Test 3: Wrong key should fail decryption" << std::endl;

    auto key1 = generate_key();
    auto key2 = generate_key();

    std::string plaintext = "Secret message";
    auto data = string_to_bytes(plaintext);

    // Encrypt with key1
    auto encrypted = encrypt(data, key1);

    // Try to decrypt with key2 (should fail)
    bool exception_thrown = false;
    try {
        auto decrypted = decrypt(encrypted, key2);
        std::cout << "❌ ERROR: Decryption should have failed with wrong key!" << std::endl;
    } catch (const std::exception& e) {
        std::cout << "Expected exception caught: " << e.what() << std::endl;
        exception_thrown = true;
    }

    assert(exception_thrown);
    std::cout << "✅ Test 3 PASSED: Wrong key correctly rejected" << std::endl;
}

void test_corrupted_data_fails() {
    std::cout << "\n🧪 Test 4: Corrupted ciphertext should fail" << std::endl;

    auto key = generate_key();
    std::string plaintext = "Important data";
    auto data = string_to_bytes(plaintext);

    // Encrypt
    auto encrypted = encrypt(data, key);

    // Corrupt the ciphertext (flip a bit)
    if (!encrypted.empty()) {
        encrypted[encrypted.size() / 2] ^= 0x01;
    }

    // Try to decrypt corrupted data (should fail)
    bool exception_thrown = false;
    try {
        auto decrypted = decrypt(encrypted, key);
        std::cout << "❌ ERROR: Decryption should have failed with corrupted data!" << std::endl;
    } catch (const std::exception& e) {
        std::cout << "Expected exception caught: " << e.what() << std::endl;
        exception_thrown = true;
    }

    assert(exception_thrown);
    std::cout << "✅ Test 4 PASSED: Corrupted data correctly rejected" << std::endl;
}

void test_empty_plaintext() {
    std::cout << "\n🧪 Test 5: Empty plaintext" << std::endl;

    auto key = generate_key();
    std::vector<uint8_t> empty;

    // Encrypt empty data
    auto encrypted = encrypt(empty, key);

    assert(encrypted.empty());
    std::cout << "✅ Test 5 PASSED: Empty plaintext handled correctly" << std::endl;
}

void test_multiple_encryptions_different() {
    std::cout << "\n🧪 Test 6: Multiple encryptions of same data produce different ciphertexts" << std::endl;

    auto key = generate_key();
    std::string plaintext = "Same message";
    auto data = string_to_bytes(plaintext);

    // Encrypt twice
    auto encrypted1 = encrypt(data, key);
    auto encrypted2 = encrypt(data, key);

    // Ciphertexts should be different (different random nonces)
    assert(encrypted1 != encrypted2);
    std::cout << "Encrypted1: " << encrypted1.size() << " bytes" << std::endl;
    std::cout << "Encrypted2: " << encrypted2.size() << " bytes" << std::endl;
    std::cout << "Ciphertexts are different: ✓ (due to random nonces)" << std::endl;

    // But both should decrypt to same plaintext
    auto decrypted1 = decrypt(encrypted1, key);
    auto decrypted2 = decrypt(encrypted2, key);

    std::string result1 = bytes_to_string(decrypted1);
    std::string result2 = bytes_to_string(decrypted2);

    assert(result1 == plaintext);
    assert(result2 == plaintext);

    std::cout << "✅ Test 6 PASSED: Multiple encryptions work correctly" << std::endl;
}

int main() {
    std::cout << "╔════════════════════════════════════════════════════════════╗" << std::endl;
    std::cout << "║  ChaCha20-Poly1305 Encryption Tests (crypto-transport)    ║" << std::endl;
    std::cout << "╚════════════════════════════════════════════════════════════╝" << std::endl;

    // Note: libsodium initialization is automatic in crypto-transport
    std::cout << "✅ crypto-transport initialized" << std::endl;

    try {
        test_encrypt_decrypt_simple();
        test_encrypt_large_data();
        test_wrong_key_fails();
        test_corrupted_data_fails();
        test_empty_plaintext();
        test_multiple_encryptions_different();

        std::cout << "\n╔════════════════════════════════════════════════════════════╗" << std::endl;
        std::cout << "║  ✅ ALL ENCRYPTION TESTS PASSED                           ║" << std::endl;
        std::cout << "╚════════════════════════════════════════════════════════════╝" << std::endl;

        return 0;

    } catch (const std::exception& e) {
        std::cerr << "\n❌ TEST FAILED: " << e.what() << std::endl;
        return 1;
    }
}