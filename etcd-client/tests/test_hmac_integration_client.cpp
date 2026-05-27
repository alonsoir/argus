// etcd-client/tests/test_hmac_integration_client.cpp
/**
 * Integration Tests for EtcdClient HMAC Workflow
 *
 * REQUIRES: etcd-server running with SecretsManager initialized
 *
 * These tests demonstrate the complete HMAC workflow:
 * 1. etcd-client retrieves HMAC key from etcd-server
 * 2. etcd-client computes HMAC over log data
 * 3. etcd-client validates HMAC
 *
 * This simulates how rag-ingester will use HMAC for log validation.
 */

#include "etcd_client/etcd_client.hpp"
#include <iostream>
#include <cassert>

using namespace etcd_client;

// ANSI colors
#define GREEN "\033[32m"
#define RED "\033[31m"
#define BLUE "\033[34m"
#define YELLOW "\033[33m"
#define RESET "\033[0m"

void log_test(const std::string& test_name, bool passed) {
    if (passed) {
        std::cout << GREEN << "✅ PASS" << RESET << ": " << test_name << std::endl;
    } else {
        std::cout << RED << "❌ FAIL" << RESET << ": " << test_name << std::endl;
    }
}

// Test 1: Retrieve HMAC key from etcd-server
bool test_retrieve_hmac_key() {
    std::cout << std::endl;
    std::cout << BLUE << "─────────────────────────────────────────────────────" << RESET << std::endl;
    std::cout << BLUE << "Test: Retrieve HMAC Key from etcd-server" << RESET << std::endl;
    std::cout << BLUE << "─────────────────────────────────────────────────────" << RESET << std::endl;

    try {
        // Create client (no encryption needed for this test)
        Config config;
        config.component_name = "test-hmac-client";
        config.encryption_enabled = false;
        config.host = "127.0.0.1";
        config.port = 2379;

        EtcdClient client(config);

        std::cout << "1️⃣  Connecting to etcd-server..." << std::endl;
        if (!client.connect()) {
            std::cout << "   ❌ Failed to connect to etcd-server" << std::endl;
            std::cout << "   ⚠️  Make sure etcd-server is running: sudo ./etcd-server" << std::endl;
            return false;
        }
        std::cout << "   ✅ Connected to etcd-server" << std::endl;

        std::cout << "2️⃣  Retrieving HMAC key from /secrets/rag/log_hmac_key..." << std::endl;
        auto key_opt = client.get_hmac_key("/secrets/rag/log_hmac_key");

        if (!key_opt.has_value()) {
            std::cout << "   ❌ Failed to retrieve HMAC key" << std::endl;
            std::cout << "   ⚠️  Make sure etcd-server has SecretsManager initialized" << std::endl;
            return false;
        }

        std::vector<uint8_t> key = *key_opt;
        std::cout << "   ✅ Retrieved HMAC key (" << key.size() << " bytes)" << std::endl;

        // Verify key length (should be 32 bytes for HMAC-SHA256)
        if (key.size() != 32) {
            std::cout << "   ❌ Unexpected key length: " << key.size() << " (expected 32)" << std::endl;
            return false;
        }
        std::cout << "   ✅ Key length verified (32 bytes)" << std::endl;

        std::cout << BLUE << "─────────────────────────────────────────────────────" << RESET << std::endl;
        return true;

    } catch (const std::exception& e) {
        std::cout << "   ❌ Exception: " << e.what() << std::endl;
        return false;
    }
}

// Test 2: Complete HMAC workflow (retrieve key, compute, validate)
bool test_complete_hmac_workflow() {
    std::cout << std::endl;
    std::cout << BLUE << "─────────────────────────────────────────────────────" << RESET << std::endl;
    std::cout << BLUE << "Test: Complete HMAC Workflow" << RESET << std::endl;
    std::cout << BLUE << "─────────────────────────────────────────────────────" << RESET << std::endl;

    try {
        Config config;
        config.component_name = "test-workflow";
        config.encryption_enabled = false;

        EtcdClient client(config);

        std::cout << "1️⃣  Connecting and retrieving HMAC key..." << std::endl;
        if (!client.connect()) {
            std::cout << "   ❌ Connection failed" << std::endl;
            return false;
        }

        auto key_opt = client.get_hmac_key("/secrets/rag/log_hmac_key");
        if (!key_opt.has_value()) {
            std::cout << "   ❌ Key retrieval failed" << std::endl;
            return false;
        }
        std::vector<uint8_t> key = *key_opt;
        std::cout << "   ✅ HMAC key retrieved" << std::endl;

        std::cout << "2️⃣  Creating log entry..." << std::endl;
        std::string log_entry = R"({"timestamp":"2026-02-09T10:00:00Z","ip":"192.168.1.100","confidence":0.95,"detector":"ransomware"})";
        std::cout << "   Log: " << log_entry << std::endl;

        std::cout << "3️⃣  Computing HMAC-SHA256..." << std::endl;
        std::string hmac = client.compute_hmac_sha256(log_entry, key);
        std::cout << "   HMAC: " << hmac.substr(0, 16) << "..." << std::endl;

        std::cout << "4️⃣  Validating HMAC (should pass)..." << std::endl;
        bool valid = client.validate_hmac_sha256(log_entry, hmac, key);
        if (!valid) {
            std::cout << "   ❌ Validation failed (should have passed)" << std::endl;
            return false;
        }
        std::cout << "   ✅ HMAC validation successful" << std::endl;

        std::cout << "5️⃣  Testing tampering detection..." << std::endl;
        std::string tampered_entry = log_entry;
        tampered_entry[50] = 'X';  // Modify one character

        bool should_fail = client.validate_hmac_sha256(tampered_entry, hmac, key);
        if (should_fail) {
            std::cout << "   ❌ Tampered data passed validation (should have failed)" << std::endl;
            return false;
        }
        std::cout << "   ✅ Tampering detected successfully" << std::endl;

        std::cout << BLUE << "─────────────────────────────────────────────────────" << RESET << std::endl;
        return true;

    } catch (const std::exception& e) {
        std::cout << "   ❌ Exception: " << e.what() << std::endl;
        return false;
    }
}

// Test 3: Simulate rag-ingester validating multiple log entries
bool test_rag_ingester_simulation() {
    std::cout << std::endl;
    std::cout << BLUE << "─────────────────────────────────────────────────────" << RESET << std::endl;
    std::cout << BLUE << "Test: RAG-Ingester Simulation (10 Log Entries)" << RESET << std::endl;
    std::cout << BLUE << "─────────────────────────────────────────────────────" << RESET << std::endl;

    try {
        Config config;
        config.component_name = "rag-ingester-sim";
        config.encryption_enabled = false;

        EtcdClient client(config);

        std::cout << "🏗️  Simulating rag-ingester startup..." << std::endl;
        if (!client.connect()) {
            return false;
        }

        std::cout << "📥 Retrieving HMAC key for log validation..." << std::endl;
        auto key_opt = client.get_hmac_key("/secrets/rag/log_hmac_key");
        if (!key_opt.has_value()) {
            return false;
        }
        std::vector<uint8_t> key = *key_opt;
        std::cout << "   ✅ HMAC key loaded" << std::endl;

        std::cout << "📝 Processing 10 log entries..." << std::endl;
        int valid_count = 0;
        int tampered_count = 0;

        for (int i = 0; i < 10; ++i) {
            // Create log entry
            std::string log_entry = R"({"id":)" + std::to_string(i) +
                                   R"(,"timestamp":"2026-02-09T10:00:0)" + std::to_string(i) +
                                   R"(Z","ip":"192.168.1.)" + std::to_string(100 + i) + R"("})";

            // Compute HMAC
            std::string hmac = client.compute_hmac_sha256(log_entry, key);

            // Tamper with 20% of logs (indices 0, 5)
            if (i % 5 == 0) {
                log_entry[10] = 'X';  // Tamper
            }

            // Validate
            if (client.validate_hmac_sha256(log_entry, hmac, key)) {
                valid_count++;
            } else {
                tampered_count++;
            }
        }

        std::cout << "   ✅ Valid entries: " << valid_count << std::endl;
        std::cout << "   🚨 Tampered entries detected: " << tampered_count << std::endl;

        // We expect 8 valid, 2 tampered
        if (valid_count == 8 && tampered_count == 2) {
            std::cout << "   ✅ RAG-ingester simulation successful" << std::endl;
            std::cout << BLUE << "─────────────────────────────────────────────────────" << RESET << std::endl;
            return true;
        } else {
            std::cout << "   ❌ Unexpected validation results" << std::endl;
            std::cout << "      Expected: 8 valid, 2 tampered" << std::endl;
            std::cout << "      Got: " << valid_count << " valid, " << tampered_count << " tampered" << std::endl;
            return false;
        }

    } catch (const std::exception& e) {
        std::cout << "   ❌ Exception: " << e.what() << std::endl;
        return false;
    }
}

// Test 4: Key not found handling
bool test_key_not_found() {
    std::cout << std::endl;
    std::cout << BLUE << "─────────────────────────────────────────────────────" << RESET << std::endl;
    std::cout << BLUE << "Test: Graceful Handling of Non-Existent Key" << RESET << std::endl;
    std::cout << BLUE << "─────────────────────────────────────────────────────" << RESET << std::endl;

    try {
        Config config;
        config.component_name = "test-not-found";
        config.encryption_enabled = false;

        EtcdClient client(config);

        if (!client.connect()) {
            return false;
        }

        std::cout << "1️⃣  Attempting to retrieve non-existent key..." << std::endl;
        auto key_opt = client.get_hmac_key("/secrets/nonexistent/key");

        if (key_opt.has_value()) {
            std::cout << "   ❌ Key retrieval should have failed" << std::endl;
            return false;
        }

        std::cout << "   ✅ Correctly returned nullopt for non-existent key" << std::endl;
        std::cout << BLUE << "─────────────────────────────────────────────────────" << RESET << std::endl;
        return true;

    } catch (const std::exception& e) {
        std::cout << "   ❌ Exception: " << e.what() << std::endl;
        return false;
    }
}

int main() {
    std::cout << "═══════════════════════════════════════════════════════════" << std::endl;
    std::cout << "  EtcdClient HMAC Integration Tests" << std::endl;
    std::cout << "═══════════════════════════════════════════════════════════" << std::endl;
    std::cout << std::endl;
    std::cout << YELLOW << "⚠️  REQUIREMENTS:" << RESET << std::endl;
    std::cout << "  - etcd-server must be running: cd /vagrant/etcd-server/build && sudo ./etcd-server" << std::endl;
    std::cout << "  - SecretsManager must be initialized with /secrets/rag/log_hmac_key" << std::endl;
    std::cout << std::endl;

    int passed = 0;
    int total = 0;

    #define RUN_INTEGRATION_TEST(test_func) \
        do { \
            total++; \
            bool result = test_func(); \
            log_test(#test_func, result); \
            if (result) passed++; \
        } while(0)

    RUN_INTEGRATION_TEST(test_retrieve_hmac_key);
    RUN_INTEGRATION_TEST(test_complete_hmac_workflow);
    RUN_INTEGRATION_TEST(test_rag_ingester_simulation);
    RUN_INTEGRATION_TEST(test_key_not_found);

    std::cout << std::endl;
    std::cout << "═══════════════════════════════════════════════════════════" << std::endl;
    std::cout << "  Results: " << passed << "/" << total << " tests passed" << std::endl;
    std::cout << "═══════════════════════════════════════════════════════════" << std::endl;

    if (passed == total) {
        std::cout << GREEN << "🎉 ALL INTEGRATION TESTS PASSED!" << RESET << std::endl;
        std::cout << YELLOW << "✅ Ready for Phase 3: rag-ingester EventLoader HMAC validation" << RESET << std::endl;
        return 0;
    } else {
        std::cout << RED << "❌ SOME TESTS FAILED" << RESET << std::endl;
        std::cout << YELLOW << "⚠️  Check that etcd-server is running with SecretsManager" << RESET << std::endl;
        return 1;
    }
}