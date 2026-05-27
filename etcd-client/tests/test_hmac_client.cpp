// etcd-client/tests/test_hmac_client.cpp
/**
 * Unit Tests for EtcdClient HMAC Utilities
 *
 * Tests the HMAC helper methods without requiring etcd-server connection.
 */

#include "etcd_client/etcd_client.hpp"
#include <iostream>
#include <cassert>
#include <vector>

using namespace etcd_client;

// ANSI colors
#define GREEN "\033[32m"
#define RED "\033[31m"
#define RESET "\033[0m"

void log_test(const std::string& test_name, bool passed) {
    if (passed) {
        std::cout << GREEN << "✅ PASS" << RESET << ": " << test_name << std::endl;
    } else {
        std::cout << RED << "❌ FAIL" << RESET << ": " << test_name << std::endl;
    }
}

// Test 1: bytes_to_hex conversion
bool test_bytes_to_hex() {
    std::vector<uint8_t> bytes = {0x12, 0x34, 0x56, 0x78, 0x9a, 0xbc, 0xde, 0xf0};
    std::string hex = EtcdClient::bytes_to_hex(bytes);

    std::string expected = "123456789abcdef0";
    return hex == expected;
}

// Test 2: hex_to_bytes conversion
bool test_hex_to_bytes() {
    std::string hex = "123456789abcdef0";
    std::vector<uint8_t> bytes = EtcdClient::hex_to_bytes(hex);

    std::vector<uint8_t> expected = {0x12, 0x34, 0x56, 0x78, 0x9a, 0xbc, 0xde, 0xf0};
    return bytes == expected;
}

// Test 3: Round-trip hex conversion
bool test_hex_roundtrip() {
    std::vector<uint8_t> original = {0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0xFF, 0x00, 0x11};

    std::string hex = EtcdClient::bytes_to_hex(original);
    std::vector<uint8_t> decoded = EtcdClient::hex_to_bytes(hex);

    return original == decoded;
}

// Test 4: Invalid hex string (odd length)
bool test_invalid_hex() {
    try {
        EtcdClient::hex_to_bytes("abc");  // Odd length
        return false;  // Should have thrown
    } catch (const std::invalid_argument&) {
        return true;   // Expected exception
    }
}

// Test 5: Empty conversions
bool test_empty_conversions() {
    std::vector<uint8_t> empty_bytes;
    std::string hex = EtcdClient::bytes_to_hex(empty_bytes);

    if (!hex.empty()) {
        return false;
    }

    std::vector<uint8_t> bytes = EtcdClient::hex_to_bytes("");
    return bytes.empty();
}

// Test 6: HMAC computation produces consistent results
bool test_hmac_consistency() {
    // Create a temporary config to construct EtcdClient
    Config config;
    config.component_name = "test";
    config.encryption_enabled = false;  // Not needed for HMAC tests

    EtcdClient client(config);

    std::vector<uint8_t> key(32, 0xAA);  // 32-byte key filled with 0xAA
    std::string data = "test data for HMAC";

    // Compute HMAC twice
    std::string hmac1 = client.compute_hmac_sha256(data, key);
    std::string hmac2 = client.compute_hmac_sha256(data, key);

    // Should produce identical results
    return hmac1 == hmac2;
}

// Test 7: Different data produces different HMACs
bool test_hmac_different_data() {
    Config config;
    config.component_name = "test";
    config.encryption_enabled = false;

    EtcdClient client(config);

    std::vector<uint8_t> key(32, 0xBB);

    std::string hmac1 = client.compute_hmac_sha256("data1", key);
    std::string hmac2 = client.compute_hmac_sha256("data2", key);

    // Different data should produce different HMACs
    return hmac1 != hmac2;
}

// Test 8: Different keys produce different HMACs
bool test_hmac_different_keys() {
    Config config;
    config.component_name = "test";
    config.encryption_enabled = false;

    EtcdClient client(config);

    std::vector<uint8_t> key1(32, 0xCC);
    std::vector<uint8_t> key2(32, 0xDD);

    std::string data = "same data";

    std::string hmac1 = client.compute_hmac_sha256(data, key1);
    std::string hmac2 = client.compute_hmac_sha256(data, key2);

    // Different keys should produce different HMACs
    return hmac1 != hmac2;
}

// Test 9: HMAC validation - valid case
bool test_hmac_validation_valid() {
    Config config;
    config.component_name = "test";
    config.encryption_enabled = false;

    EtcdClient client(config);

    std::vector<uint8_t> key(32, 0xEE);
    std::string data = "validation test data";

    // Compute HMAC
    std::string hmac = client.compute_hmac_sha256(data, key);

    // Validate should return true
    return client.validate_hmac_sha256(data, hmac, key);
}

// Test 10: HMAC validation - invalid HMAC
bool test_hmac_validation_invalid() {
    Config config;
    config.component_name = "test";
    config.encryption_enabled = false;

    EtcdClient client(config);

    std::vector<uint8_t> key(32, 0xFF);
    std::string data = "validation test";

    std::string fake_hmac = "0000000000000000000000000000000000000000000000000000000000000000";

    // Validation should return false for fake HMAC
    return !client.validate_hmac_sha256(data, fake_hmac, key);
}

// Test 11: HMAC validation - tampered data
bool test_hmac_validation_tampered() {
    Config config;
    config.component_name = "test";
    config.encryption_enabled = false;

    EtcdClient client(config);

    std::vector<uint8_t> key(32, 0x11);
    std::string original_data = "original data";

    // Compute HMAC for original data
    std::string hmac = client.compute_hmac_sha256(original_data, key);

    // Try to validate with tampered data
    std::string tampered_data = "tampered data";

    // Should fail validation
    return !client.validate_hmac_sha256(tampered_data, hmac, key);
}

// Test 12: HMAC length check (SHA256 produces 64 hex chars)
bool test_hmac_length() {
    Config config;
    config.component_name = "test";
    config.encryption_enabled = false;

    EtcdClient client(config);

    std::vector<uint8_t> key(32, 0x22);
    std::string data = "test";

    std::string hmac = client.compute_hmac_sha256(data, key);

    // SHA256 = 32 bytes = 64 hex characters
    return hmac.length() == 64;
}

int main() {
    std::cout << "═══════════════════════════════════════════════════════════" << std::endl;
    std::cout << "  EtcdClient HMAC Utilities - Unit Tests" << std::endl;
    std::cout << "═══════════════════════════════════════════════════════════" << std::endl;
    std::cout << std::endl;

    int passed = 0;
    int total = 0;

    #define RUN_TEST(test_func) \
        do { \
            total++; \
            bool result = test_func(); \
            log_test(#test_func, result); \
            if (result) passed++; \
        } while(0)

    RUN_TEST(test_bytes_to_hex);
    RUN_TEST(test_hex_to_bytes);
    RUN_TEST(test_hex_roundtrip);
    RUN_TEST(test_invalid_hex);
    RUN_TEST(test_empty_conversions);
    RUN_TEST(test_hmac_consistency);
    RUN_TEST(test_hmac_different_data);
    RUN_TEST(test_hmac_different_keys);
    RUN_TEST(test_hmac_validation_valid);
    RUN_TEST(test_hmac_validation_invalid);
    RUN_TEST(test_hmac_validation_tampered);
    RUN_TEST(test_hmac_length);

    std::cout << std::endl;
    std::cout << "═══════════════════════════════════════════════════════════" << std::endl;
    std::cout << "  Results: " << passed << "/" << total << " tests passed" << std::endl;
    std::cout << "═══════════════════════════════════════════════════════════" << std::endl;

    if (passed == total) {
        std::cout << GREEN << "🎉 ALL TESTS PASSED!" << RESET << std::endl;
        return 0;
    } else {
        std::cout << RED << "❌ SOME TESTS FAILED" << RESET << std::endl;
        return 1;
    }
}