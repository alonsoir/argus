//===----------------------------------------------------------------------===//
// ML Defender - Firewall ACL Agent
// test_ipset_wrapper.cpp - Comprehensive Unit Tests
//
// Test Coverage:
//   - Set lifecycle (create, destroy, exists)
//   - Batch operations (add, delete, deduplication)
//   - Single operations (add, delete, test)
//   - Error handling (invalid IPs, missing sets)
//   - Performance benchmarks (target: 1000 IPs in <10ms)
//   - Statistics and monitoring
//   - Advanced operations (rename, swap, save/restore)
//
// Requirements:
//   - Must run as root (ipset kernel operations)
//   - Clean slate (no existing ml_defender_* sets)
//
// Via Appia Quality: Thorough testing for decade-lasting code
//===----------------------------------------------------------------------===//

#include "firewall/ipset_wrapper.hpp"

#include <gtest/gtest.h>
#include <unistd.h>
#include <chrono>
#include <random>
#include <sstream>

using namespace mldefender::firewall;
using namespace std::chrono;

//===----------------------------------------------------------------------===//
// Test Fixture
//===----------------------------------------------------------------------===//

class IPSetWrapperTest : public ::testing::Test {
protected:
    void SetUp() override {
        // Verify root privileges
        if (geteuid() != 0) {
            GTEST_SKIP() << "⚠️  Tests require root privileges (sudo)";
        }

        // Clean up any leftover test sets
        cleanup_test_sets();

        wrapper_ = std::make_unique<IPSetWrapper>();
    }

    void TearDown() override {
        // Cleanup test sets
        cleanup_test_sets();
        wrapper_.reset();
    }

    void cleanup_test_sets() {
        IPSetWrapper temp_wrapper;
        auto sets = temp_wrapper.list_sets();

        for (const auto& set : sets) {
            if (set.find("test_") == 0) {
                temp_wrapper.destroy_set(set);
            }
        }
    }

    std::string generate_random_ip() {
        static std::random_device rd;
        static std::mt19937 gen(rd());
        static std::uniform_int_distribution<> dist(1, 254);

        std::ostringstream oss;
        oss << dist(gen) << "." << dist(gen) << "."
            << dist(gen) << "." << dist(gen);
        return oss.str();
    }

    std::vector<IPSetEntry> generate_random_ips(size_t count) {
        std::vector<IPSetEntry> ips;
        ips.reserve(count);

        for (size_t i = 0; i < count; ++i) {
            ips.emplace_back(generate_random_ip());
        }

        return ips;
    }

    std::unique_ptr<IPSetWrapper> wrapper_;

    // Standard test set configurations
    static constexpr const char* TEST_SET_NAME = "test_ipset";
    static constexpr const char* TEST_SET_NAME_2 = "test_ipset_2";
};

//===----------------------------------------------------------------------===//
// Basic Set Management Tests
//===----------------------------------------------------------------------===//

TEST_F(IPSetWrapperTest, CreateAndDestroySet) {
    auto config = make_blacklist_config(TEST_SET_NAME);

    // Create set
    auto result = wrapper_->create_set(config);
    ASSERT_TRUE(result) << "Failed to create set: " << result.get_error().message;

    // Verify exists
    EXPECT_TRUE(wrapper_->set_exists(TEST_SET_NAME));

    // Destroy set
    result = wrapper_->destroy_set(TEST_SET_NAME);
    ASSERT_TRUE(result) << "Failed to destroy set: " << result.get_error().message;

    // Verify doesn't exist
    EXPECT_FALSE(wrapper_->set_exists(TEST_SET_NAME));
}

TEST_F(IPSetWrapperTest, CreateSetTwiceFails) {
    auto config = make_blacklist_config(TEST_SET_NAME);

    // First create should succeed
    auto result = wrapper_->create_set(config);
    ASSERT_TRUE(result);

    // Second create should fail
    result = wrapper_->create_set(config);
    EXPECT_FALSE(result);
    EXPECT_EQ(result.get_error().code, IPSetErrorCode::SET_ALREADY_EXISTS);
}

TEST_F(IPSetWrapperTest, ListSets) {
    auto config1 = make_blacklist_config(TEST_SET_NAME);
    auto config2 = make_blacklist_config(TEST_SET_NAME_2);

    wrapper_->create_set(config1);
    wrapper_->create_set(config2);

    auto sets = wrapper_->list_sets();

    bool found1 = false, found2 = false;
    for (const auto& set : sets) {
        if (set == TEST_SET_NAME) found1 = true;
        if (set == TEST_SET_NAME_2) found2 = true;
    }

    EXPECT_TRUE(found1) << "Test set 1 not found in list";
    EXPECT_TRUE(found2) << "Test set 2 not found in list";
}

//===----------------------------------------------------------------------===//
// Batch Operations Tests - CRITICAL FOR PERFORMANCE
//===----------------------------------------------------------------------===//

TEST_F(IPSetWrapperTest, BatchAddIPs) {
    auto config = make_blacklist_config(TEST_SET_NAME);
    wrapper_->create_set(config);

    std::vector<IPSetEntry> entries = {
        IPSetEntry{"192.168.1.1"},
        IPSetEntry{"192.168.1.2"},
        IPSetEntry{"192.168.1.3"},
        IPSetEntry{"10.0.0.1", 300},  // With timeout
        IPSetEntry{"10.0.0.2", 600, "Test comment"}  // With timeout and comment
    };

    auto result = wrapper_->add_batch(TEST_SET_NAME, entries);
    ASSERT_TRUE(result) << "Batch add failed: " << result.get_error().message;

    // Verify all IPs exist
    for (const auto& entry : entries) {
        EXPECT_TRUE(wrapper_->test(TEST_SET_NAME, entry.ip))
            << "IP " << entry.ip << " not found after batch add";
    }
}

TEST_F(IPSetWrapperTest, BatchAddPerformance) {
    auto config = make_blacklist_config(TEST_SET_NAME);
    wrapper_->create_set(config);

    // Generate 1000 random IPs
    auto entries = generate_random_ips(1000);

    // Measure batch add time
    auto start = high_resolution_clock::now();
    auto result = wrapper_->add_batch(TEST_SET_NAME, entries);
    auto end = high_resolution_clock::now();

    ASSERT_TRUE(result) << "Batch add failed: " << result.get_error().message;

    auto duration_ms = duration_cast<milliseconds>(end - start).count();

    std::cout << "📊 Batch add 1000 IPs: " << duration_ms << "ms\n";

    // Performance target: <10ms for 1000 IPs
    EXPECT_LT(duration_ms, 10)
        << "⚠️  Batch add too slow! Target: <10ms, Actual: " << duration_ms << "ms";

    // Verify count
    EXPECT_EQ(wrapper_->get_entry_count(TEST_SET_NAME), 1000);
}

TEST_F(IPSetWrapperTest, BatchAddDeduplication) {
    auto config = make_blacklist_config(TEST_SET_NAME);
    wrapper_->create_set(config);

    // Add IPs with duplicates
    std::vector<IPSetEntry> entries = {
        IPSetEntry{"192.168.1.1"},
        IPSetEntry{"192.168.1.2"},
        IPSetEntry{"192.168.1.1"},  // Duplicate
        IPSetEntry{"192.168.1.3"},
        IPSetEntry{"192.168.1.2"},  // Duplicate
    };

    auto result = wrapper_->add_batch(TEST_SET_NAME, entries);
    ASSERT_TRUE(result);

    // Should have only 3 unique IPs
    EXPECT_EQ(wrapper_->get_entry_count(TEST_SET_NAME), 3);
}

TEST_F(IPSetWrapperTest, BatchDeleteIPs) {
    auto config = make_blacklist_config(TEST_SET_NAME);
    wrapper_->create_set(config);

    // Add IPs
    std::vector<IPSetEntry> entries = {
        IPSetEntry{"192.168.1.1"},
        IPSetEntry{"192.168.1.2"},
        IPSetEntry{"192.168.1.3"},
        IPSetEntry{"192.168.1.4"},
        IPSetEntry{"192.168.1.5"},
    };
    wrapper_->add_batch(TEST_SET_NAME, entries);

    // Delete some IPs
    std::vector<std::string> to_delete = {
        "192.168.1.2",
        "192.168.1.4"
    };

    auto result = wrapper_->delete_batch(TEST_SET_NAME, to_delete);
    ASSERT_TRUE(result);

    // Verify deletions
    EXPECT_TRUE(wrapper_->test(TEST_SET_NAME, "192.168.1.1"));
    EXPECT_FALSE(wrapper_->test(TEST_SET_NAME, "192.168.1.2"));  // Deleted
    EXPECT_TRUE(wrapper_->test(TEST_SET_NAME, "192.168.1.3"));
    EXPECT_FALSE(wrapper_->test(TEST_SET_NAME, "192.168.1.4"));  // Deleted
    EXPECT_TRUE(wrapper_->test(TEST_SET_NAME, "192.168.1.5"));

    EXPECT_EQ(wrapper_->get_entry_count(TEST_SET_NAME), 3);
}

//===----------------------------------------------------------------------===//
// Single Operation Tests
//===----------------------------------------------------------------------===//

TEST_F(IPSetWrapperTest, AddAndTestSingleIP) {
    auto config = make_blacklist_config(TEST_SET_NAME);
    wrapper_->create_set(config);

    IPSetEntry entry{"192.168.1.100", 300, "Test entry"};

    auto result = wrapper_->add(TEST_SET_NAME, entry);
    ASSERT_TRUE(result);

    EXPECT_TRUE(wrapper_->test(TEST_SET_NAME, "192.168.1.100"));
    EXPECT_FALSE(wrapper_->test(TEST_SET_NAME, "192.168.1.101"));
}

TEST_F(IPSetWrapperTest, DeleteSingleIP) {
    auto config = make_blacklist_config(TEST_SET_NAME);
    wrapper_->create_set(config);

    wrapper_->add(TEST_SET_NAME, IPSetEntry{"192.168.1.100"});
    EXPECT_TRUE(wrapper_->test(TEST_SET_NAME, "192.168.1.100"));

    auto result = wrapper_->delete_ip(TEST_SET_NAME, "192.168.1.100");
    ASSERT_TRUE(result);

    EXPECT_FALSE(wrapper_->test(TEST_SET_NAME, "192.168.1.100"));
}

TEST_F(IPSetWrapperTest, TestPerformance) {
    auto config = make_blacklist_config(TEST_SET_NAME);
    wrapper_->create_set(config);

    // Add 10000 IPs
    auto entries = generate_random_ips(10000);
    wrapper_->add_batch(TEST_SET_NAME, entries);

    // Test lookup performance (should be O(1))
    auto start = high_resolution_clock::now();

    constexpr int NUM_TESTS = 1000;
    for (int i = 0; i < NUM_TESTS; ++i) {
        wrapper_->test(TEST_SET_NAME, entries[i % entries.size()].ip);
    }

    auto end = high_resolution_clock::now();
    auto duration_us = duration_cast<microseconds>(end - start).count();
    auto avg_us = duration_us / NUM_TESTS;

    std::cout << "📊 Average lookup time (10K entries): " << avg_us << "μs\n";

    // Should be <1μs for kernel hash lookup
    EXPECT_LT(avg_us, 1)
        << "⚠️  Lookup too slow! Expected <1μs, got " << avg_us << "μs";
}

//===----------------------------------------------------------------------===//
// Error Handling Tests
//===----------------------------------------------------------------------===//

TEST_F(IPSetWrapperTest, AddToNonexistentSet) {
    auto result = wrapper_->add("nonexistent_set", IPSetEntry{"192.168.1.1"});

    EXPECT_FALSE(result);
    EXPECT_EQ(result.get_error().code, IPSetErrorCode::SET_NOT_FOUND);
}

TEST_F(IPSetWrapperTest, InvalidIPFormat) {
    auto config = make_blacklist_config(TEST_SET_NAME);
    wrapper_->create_set(config);

    std::vector<IPSetEntry> entries = {
        IPSetEntry{"192.168.1.1"},      // Valid
        IPSetEntry{"999.999.999.999"},  // Invalid
        IPSetEntry{"not.an.ip.addr"},   // Invalid
    };

    auto result = wrapper_->add_batch(TEST_SET_NAME, entries);

    EXPECT_FALSE(result);
    EXPECT_EQ(result.get_error().code, IPSetErrorCode::INVALID_IP_FORMAT);
    EXPECT_EQ(result.get_error().failed_ips.size(), 2);
}

//===----------------------------------------------------------------------===//
// Statistics and Monitoring Tests
//===----------------------------------------------------------------------===//

TEST_F(IPSetWrapperTest, GetStatistics) {
    auto config = make_blacklist_config(TEST_SET_NAME);
    wrapper_->create_set(config);

    // Add some IPs
    wrapper_->add_batch(TEST_SET_NAME, generate_random_ips(100));

    auto result = wrapper_->get_stats(TEST_SET_NAME, false);
    ASSERT_TRUE(result);

    const auto& stats = (*result);
    EXPECT_EQ(stats.name, TEST_SET_NAME);
    EXPECT_EQ(stats.entry_count, 100);
    EXPECT_GT(stats.size_in_memory, 0);
}

TEST_F(IPSetWrapperTest, ListEntries) {
    auto config = make_blacklist_config(TEST_SET_NAME);
    wrapper_->create_set(config);

    std::vector<IPSetEntry> entries = {
        IPSetEntry{"192.168.1.1"},
        IPSetEntry{"192.168.1.2"},
        IPSetEntry{"192.168.1.3"},
    };
    wrapper_->add_batch(TEST_SET_NAME, entries);

    auto list = wrapper_->list_entries(TEST_SET_NAME);

    EXPECT_EQ(list.size(), 3);

    // Verify all IPs present
    for (const auto& entry : entries) {
        bool found = std::find(list.begin(), list.end(), entry.ip) != list.end();
        EXPECT_TRUE(found) << "IP " << entry.ip << " not in list";
    }
}

//===----------------------------------------------------------------------===//
// Advanced Operations Tests
//===----------------------------------------------------------------------===//

TEST_F(IPSetWrapperTest, FlushSet) {
    auto config = make_blacklist_config(TEST_SET_NAME);
    wrapper_->create_set(config);

    wrapper_->add_batch(TEST_SET_NAME, generate_random_ips(50));
    EXPECT_EQ(wrapper_->get_entry_count(TEST_SET_NAME), 50);

    auto result = wrapper_->flush_set(TEST_SET_NAME);
    ASSERT_TRUE(result);

    EXPECT_EQ(wrapper_->get_entry_count(TEST_SET_NAME), 0);
}

TEST_F(IPSetWrapperTest, RenameSet) {
    auto config = make_blacklist_config(TEST_SET_NAME);
    wrapper_->create_set(config);

    wrapper_->add_batch(TEST_SET_NAME, generate_random_ips(10));

    auto result = wrapper_->rename_set(TEST_SET_NAME, TEST_SET_NAME_2);
    ASSERT_TRUE(result);

    EXPECT_FALSE(wrapper_->set_exists(TEST_SET_NAME));
    EXPECT_TRUE(wrapper_->set_exists(TEST_SET_NAME_2));
    EXPECT_EQ(wrapper_->get_entry_count(TEST_SET_NAME_2), 10);
}

TEST_F(IPSetWrapperTest, SwapSets) {
    auto config1 = make_blacklist_config(TEST_SET_NAME);
    auto config2 = make_blacklist_config(TEST_SET_NAME_2);

    wrapper_->create_set(config1);
    wrapper_->create_set(config2);

    // Set1: 10 IPs, Set2: 20 IPs
    wrapper_->add_batch(TEST_SET_NAME, generate_random_ips(10));
    wrapper_->add_batch(TEST_SET_NAME_2, generate_random_ips(20));

    auto result = wrapper_->swap_sets(TEST_SET_NAME, TEST_SET_NAME_2);
    ASSERT_TRUE(result);

    // Counts should be swapped
    EXPECT_EQ(wrapper_->get_entry_count(TEST_SET_NAME), 20);
    EXPECT_EQ(wrapper_->get_entry_count(TEST_SET_NAME_2), 10);
}

TEST_F(IPSetWrapperTest, SaveAndRestore) {
    const char* backup_file = "/tmp/test_ipset_backup.txt";

    auto config = make_blacklist_config(TEST_SET_NAME);
    wrapper_->create_set(config);

    auto entries = generate_random_ips(50);
    wrapper_->add_batch(TEST_SET_NAME, entries);

    // Save
    auto result = wrapper_->save(backup_file);
    ASSERT_TRUE(result);

    // Destroy set
    wrapper_->destroy_set(TEST_SET_NAME);
    EXPECT_FALSE(wrapper_->set_exists(TEST_SET_NAME));

    // Restore
    result = wrapper_->restore(backup_file);
    ASSERT_TRUE(result);

    // Verify restored
    EXPECT_TRUE(wrapper_->set_exists(TEST_SET_NAME));
    EXPECT_EQ(wrapper_->get_entry_count(TEST_SET_NAME), 50);

    // Cleanup
    std::remove(backup_file);
}

//===----------------------------------------------------------------------===//
// Subnet Tests
//===----------------------------------------------------------------------===//

TEST_F(IPSetWrapperTest, SubnetSupport) {
    auto config = make_subnet_config(TEST_SET_NAME, 600);
    wrapper_->create_set(config);

    std::vector<IPSetEntry> subnets = {
        IPSetEntry{"192.168.1.0/24"},
        IPSetEntry{"10.0.0.0/16"},
        IPSetEntry{"172.16.0.0/12"},
    };

    auto result = wrapper_->add_batch(TEST_SET_NAME, subnets);
    ASSERT_TRUE(result);

    EXPECT_EQ(wrapper_->get_entry_count(TEST_SET_NAME), 3);
}

//===----------------------------------------------------------------------===//
// Stress Tests
//===----------------------------------------------------------------------===//

TEST_F(IPSetWrapperTest, StressTestLargeSet) {
    auto config = make_blacklist_config(TEST_SET_NAME);
    wrapper_->create_set(config);

    // Add 100K IPs in batches of 1000
    constexpr size_t TOTAL_IPS = 100'000;
    constexpr size_t BATCH_SIZE = 1000;

    auto start = high_resolution_clock::now();

    for (size_t i = 0; i < TOTAL_IPS; i += BATCH_SIZE) {
        auto batch = generate_random_ips(BATCH_SIZE);
        auto result = wrapper_->add_batch(TEST_SET_NAME, batch);
        ASSERT_TRUE(result) << "Batch " << i/BATCH_SIZE << " failed";
    }

    auto end = high_resolution_clock::now();
    auto duration_ms = duration_cast<milliseconds>(end - start).count();

    std::cout << "📊 Added 100K IPs in " << duration_ms << "ms "
              << "(" << (TOTAL_IPS * 1000.0 / duration_ms) << " IPs/sec)\n";

    // Verify count
    auto count = wrapper_->get_entry_count(TEST_SET_NAME);
    std::cout << "📊 Final count: " << count << " IPs\n";

    // Should be close to 100K (some duplicates expected in random IPs)
    EXPECT_GT(count, 95'000);
}

//===----------------------------------------------------------------------===//
// Main
//===----------------------------------------------------------------------===//

int main(int argc, char** argv) {
    ::testing::InitGoogleTest(&argc, argv);

    std::cout << "\n";
    std::cout << "╔════════════════════════════════════════════════════════╗\n";
    std::cout << "║  ML Defender - IPSet Wrapper Unit Tests              ║\n";
    std::cout << "╚════════════════════════════════════════════════════════╝\n";
    std::cout << "\n";

    if (geteuid() != 0) {
        std::cout << "⚠️  WARNING: Tests require root privileges\n";
        std::cout << "   Run: sudo ./firewall_tests\n";
        std::cout << "\n";
    }

    int result = RUN_ALL_TESTS();

    std::cout << "\n";
    std::cout << "════════════════════════════════════════════════════════\n";
    std::cout << "\n";

    return result;
}