// /vagrant/etcd-client/tests/test_etcd_client_hmac_grace_period.cpp
// Day 57: etcd Client HMAC Tests (Updated for new API)
//
// Co-authored-by: Claude (Anthropic)
// Co-authored-by: Alonso

#include <gtest/gtest.h>
#include "etcd_client/etcd_client.hpp"
#include <vector>
#include <string>

using namespace etcd_client;

/**
 * @brief Test fixture for EtcdClient HMAC tests
 */
class EtcdClientHMACTest : public ::testing::Test {
protected:
    void SetUp() override {
        client = std::make_unique<EtcdClient>("localhost:2380");

        // Sample data for testing
        test_data = "Sample log entry for HMAC testing";

        // Generate test keys (hex strings → convert to bytes)
        std::string key_active_hex = "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2";
        std::string key_grace_hex = "b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3";
        std::string key_expired_hex = "c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4";

        test_key_active = EtcdClient::hex_to_bytes(key_active_hex);
        test_key_grace = EtcdClient::hex_to_bytes(key_grace_hex);
        test_key_expired = EtcdClient::hex_to_bytes(key_expired_hex);
    }

    std::unique_ptr<EtcdClient> client;
    std::string test_data;
    std::vector<uint8_t> test_key_active;
    std::vector<uint8_t> test_key_grace;
    std::vector<uint8_t> test_key_expired;
};

// ============================================================================
// HMAC Computation Tests
// ============================================================================

TEST_F(EtcdClientHMACTest, ComputeHMAC_ProducesValidOutput) {
    std::string hmac = client->compute_hmac_sha256(test_data, test_key_active);

    // HMAC-SHA256 produces 32 bytes = 64 hex chars
    EXPECT_EQ(hmac.length(), 64);

    // Should be hex string (only 0-9, a-f)
    for (char c : hmac) {
        EXPECT_TRUE((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f'));
    }
}

TEST_F(EtcdClientHMACTest, ComputeHMAC_DeterministicOutput) {
    std::string hmac1 = client->compute_hmac_sha256(test_data, test_key_active);
    std::string hmac2 = client->compute_hmac_sha256(test_data, test_key_active);

    // Same input → same output
    EXPECT_EQ(hmac1, hmac2);
}

TEST_F(EtcdClientHMACTest, ComputeHMAC_DifferentKeyDifferentOutput) {
    std::string hmac1 = client->compute_hmac_sha256(test_data, test_key_active);
    std::string hmac2 = client->compute_hmac_sha256(test_data, test_key_grace);

    // Different key → different output
    EXPECT_NE(hmac1, hmac2);
}

// ============================================================================
// Single Key Validation Tests
// ============================================================================

TEST_F(EtcdClientHMACTest, ValidateSingleKey_ValidHMAC) {
    std::string hmac = client->compute_hmac_sha256(test_data, test_key_active);

    bool result = client->validate_hmac_sha256(test_data, hmac, test_key_active);
    EXPECT_TRUE(result);
}

TEST_F(EtcdClientHMACTest, ValidateSingleKey_InvalidHMAC) {
    std::string hmac = client->compute_hmac_sha256(test_data, test_key_active);

    // Try to validate with wrong key
    bool result = client->validate_hmac_sha256(test_data, hmac, test_key_grace);
    EXPECT_FALSE(result);
}

TEST_F(EtcdClientHMACTest, ValidateSingleKey_TamperedData) {
    std::string hmac = client->compute_hmac_sha256(test_data, test_key_active);

    // Tamper with data
    std::string tampered_data = test_data + " TAMPERED";

    bool result = client->validate_hmac_sha256(tampered_data, hmac, test_key_active);
    EXPECT_FALSE(result);
}

// ============================================================================
// Hex Encoding Tests
// ============================================================================

TEST_F(EtcdClientHMACTest, HexEncoding_Roundtrip) {
    std::vector<uint8_t> original = {0xDE, 0xAD, 0xBE, 0xEF, 0xCA, 0xFE};

    std::string hex = EtcdClient::bytes_to_hex(original);
    EXPECT_EQ(hex, "deadbeefcafe");

    std::vector<uint8_t> decoded = EtcdClient::hex_to_bytes(hex);
    EXPECT_EQ(decoded, original);
}

TEST_F(EtcdClientHMACTest, HexEncoding_InvalidInput) {
    // Odd length hex string
    EXPECT_THROW(EtcdClient::hex_to_bytes("abc"), std::invalid_argument);
}

// ============================================================================
// Main
// ============================================================================

int main(int argc, char** argv) {
    ::testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
}
