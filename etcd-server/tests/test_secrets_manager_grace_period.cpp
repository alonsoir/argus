// /vagrant/etcd-server/tests/test_secrets_manager_grace_period.cpp
// Day 54: Grace Period Tests
//
// Co-authored-by: Claude (Anthropic)
// Co-authored-by: Alonso

#include <gtest/gtest.h>
#include "etcd_server/secrets_manager.hpp"
#include <nlohmann/json.hpp>
#include <thread>
#include <chrono>

using namespace etcd_server;
using json = nlohmann::json;

/**
 * @brief Test fixture for SecretsManager grace period tests
 */
class SecretsManagerGracePeriodTest : public ::testing::Test {
protected:
    void SetUp() override {
        // Create config with 5 second grace period (for fast testing)
        config = {
            {"secrets", {
                {"grace_period_seconds", 5},
                {"rotation_interval_hours", 168},
                {"default_key_length_bytes", 32}
            }}
        };

        secrets_mgr = std::make_unique<SecretsManager>(config);
    }

    json config;
    std::unique_ptr<SecretsManager> secrets_mgr;
};

// ============================================================================
// Config Loading Tests
// ============================================================================

TEST_F(SecretsManagerGracePeriodTest, Config_LoadedFromJSON) {
    EXPECT_EQ(secrets_mgr->get_grace_period_seconds(), 5);
}

TEST(SecretsManagerTest, Config_DefaultGracePeriod) {
    json config = {
        {"secrets", {
            {"grace_period_seconds", -1},  // Invalid
            {"rotation_interval_hours", 168},
            {"default_key_length_bytes", 32}
        }}
    };

    SecretsManager mgr(config);
    EXPECT_EQ(mgr.get_grace_period_seconds(), 300);  // Default 5 minutes
}

// ============================================================================
// Key Generation Tests
// ============================================================================

TEST_F(SecretsManagerGracePeriodTest, GenerateKey_CreatesActiveKey) {
    auto key = secrets_mgr->generate_hmac_key("test-component");

    EXPECT_FALSE(key.key_data.empty());
    EXPECT_TRUE(key.is_active);
    EXPECT_EQ(key.component, "test-component");
    EXPECT_EQ(key.key_data.length(), 64);  // 32 bytes = 64 hex chars
}

// ============================================================================
// Grace Period Tests
// ============================================================================

TEST_F(SecretsManagerGracePeriodTest, GracePeriod_OldKeyValidDuringGrace) {
    // Generate initial key
    auto key1 = secrets_mgr->generate_hmac_key("test-component");

    // Rotate (old key should enter grace period)
    auto key2 = secrets_mgr->rotate_hmac_key("test-component");

    // Check that old key is still valid (within grace period)
    auto now = std::chrono::system_clock::now();
    EXPECT_TRUE(secrets_mgr->is_key_valid(key1, now));
    EXPECT_FALSE(key1.is_active);  // Not active anymore

    // Check that new key is valid and active
    EXPECT_TRUE(secrets_mgr->is_key_valid(key2, now));
    EXPECT_TRUE(key2.is_active);
}

TEST_F(SecretsManagerGracePeriodTest, GracePeriod_OldKeyExpiredAfterGrace) {
    // Generate and rotate key
    auto key1 = secrets_mgr->generate_hmac_key("test-component");
    auto key2 = secrets_mgr->rotate_hmac_key("test-component");

    // Check validity after grace period (5s + 1s margin)
    auto future_time = std::chrono::system_clock::now() + std::chrono::seconds(6);
    EXPECT_FALSE(secrets_mgr->is_key_valid(key1, future_time));
    EXPECT_TRUE(secrets_mgr->is_key_valid(key2, future_time));  // New key still valid
}

TEST_F(SecretsManagerGracePeriodTest, GetValidKeys_ReturnsActiveAndGrace) {
    // Generate and rotate
    auto key1 = secrets_mgr->generate_hmac_key("test-component");
    auto key2 = secrets_mgr->rotate_hmac_key("test-component");

    // Get valid keys (should include key2 [active] + key1 [grace period])
    auto now = std::chrono::system_clock::now();
    auto valid_keys = secrets_mgr->get_valid_keys("test-component", now);

    // Should have 2 valid keys: key2 (active) + key1 (grace)
    EXPECT_EQ(valid_keys.size(), 2);
}

TEST_F(SecretsManagerGracePeriodTest, GetValidKeys_SortedCorrectly) {
    // Generate and rotate
    auto key1 = secrets_mgr->generate_hmac_key("test-component");
    auto key2 = secrets_mgr->rotate_hmac_key("test-component");

    // Get valid keys
    auto now = std::chrono::system_clock::now();
    auto valid_keys = secrets_mgr->get_valid_keys("test-component", now);

    ASSERT_GE(valid_keys.size(), 1);

    // First key should be active
    EXPECT_TRUE(valid_keys[0].is_active);
    EXPECT_EQ(valid_keys[0].key_data, key2.key_data);
}

TEST_F(SecretsManagerGracePeriodTest, GetValidKeys_FiltersExpired) {
    // Generate and rotate
    auto key1 = secrets_mgr->generate_hmac_key("test-component");
    auto key2 = secrets_mgr->rotate_hmac_key("test-component");

    // Check valid keys in the future (after grace period)
    auto future_time = std::chrono::system_clock::now() + std::chrono::seconds(10);
    auto valid_keys = secrets_mgr->get_valid_keys("test-component", future_time);

    // Only key2 should be valid (key1 expired)
    EXPECT_EQ(valid_keys.size(), 1);
    EXPECT_EQ(valid_keys[0].key_data, key2.key_data);
}

// ============================================================================
// Integration Test: Real Rotation Scenario
// ============================================================================

TEST_F(SecretsManagerGracePeriodTest, Integration_RealRotationScenario) {
    // Simulate real-world scenario:
    // T0: Generate key1
    // T1: Rotate to key2 (key1 enters grace period)
    // T2: Writer still using key1 (should be valid)
    // T3: Reader validates with both keys (should succeed)

    auto t0 = std::chrono::system_clock::now();
    auto key1 = secrets_mgr->generate_hmac_key("rag-ingester");

    // Small delay to simulate time passing
    std::this_thread::sleep_for(std::chrono::milliseconds(100));

    auto t1 = std::chrono::system_clock::now();
    auto key2 = secrets_mgr->rotate_hmac_key("rag-ingester");

    // At T2 (within grace period), key1 should still be valid
    auto t2 = t1 + std::chrono::seconds(2);
    EXPECT_TRUE(secrets_mgr->is_key_valid(key1, t2));
    EXPECT_FALSE(key1.is_active);

    // At T3, get all valid keys (should include both)
    auto valid_keys = secrets_mgr->get_valid_keys("rag-ingester", t2);
    EXPECT_EQ(valid_keys.size(), 2);

    // Active key should be first
    EXPECT_TRUE(valid_keys[0].is_active);
    EXPECT_EQ(valid_keys[0].key_data, key2.key_data);
}

// ============================================================================
// Multiple Rotations Test
// ============================================================================

TEST_F(SecretsManagerGracePeriodTest, MultipleRotations_GracePeriodOverlap) {
    // Generate initial key
    auto key1 = secrets_mgr->generate_hmac_key("test-component");

    // Wait and rotate (key1 in grace)
    std::this_thread::sleep_for(std::chrono::milliseconds(500));
    auto key2 = secrets_mgr->rotate_hmac_key("test-component");

    // Wait and rotate again (key2 in grace, key1 might still be in grace)
    std::this_thread::sleep_for(std::chrono::milliseconds(500));
    auto key3 = secrets_mgr->rotate_hmac_key("test-component");

    // Check valid keys now
    auto now = std::chrono::system_clock::now();
    auto valid_keys = secrets_mgr->get_valid_keys("test-component", now);

    // Should have at least 2 keys (key3 active + key2 in grace)
    // Might have 3 if key1 still in grace (depends on timing)
    EXPECT_GE(valid_keys.size(), 2);
    EXPECT_LE(valid_keys.size(), 3);
}

// ============================================================================
// Main
// ============================================================================

int main(int argc, char** argv) {
    ::testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
}