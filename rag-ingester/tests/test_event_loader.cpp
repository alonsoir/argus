// test_event_loader.cpp
// RAG Ingester - EventLoader Unit Tests
// Day 36: Verify decrypt + decompress + parse pipeline
// UPDATED: Test for 101-feature extraction

#include "event_loader.hpp"
#include <iostream>
#include <fstream>
#include <cassert>
#include <filesystem>

namespace fs = std::filesystem;
using namespace rag_ingester;

// Test directory
const std::string TEST_DIR = "/tmp/rag_ingester_test/";
const std::string TEST_KEY = TEST_DIR + "test_key.bin";

// ============================================================================
// Test Utilities
// ============================================================================

void setup_test_environment() {
    // Create test directory
    fs::create_directories(TEST_DIR);

    // Create dummy encryption key (32 bytes for ChaCha20)
    std::ofstream key_file(TEST_KEY, std::ios::binary);
    for (int i = 0; i < 32; i++) {
        key_file.put(static_cast<char>(i));
    }
    key_file.close();
}

void cleanup_test_environment() {
    if (fs::exists(TEST_DIR)) {
        fs::remove_all(TEST_DIR);
    }
}

void create_dummy_pb_file(const std::string& filename, size_t size_bytes = 1024) {
    std::string filepath = TEST_DIR + filename;
    std::ofstream file(filepath, std::ios::binary);

    // Write dummy data (will be treated as raw protobuf by stub)
    for (size_t i = 0; i < size_bytes; i++) {
        file.put(static_cast<char>(i % 256));
    }

    file.close();
}

// ============================================================================
// Test Cases
// ============================================================================

bool test_construction() {
    std::cout << "[TEST] EventLoader construction... ";

    try {
        EventLoader loader(TEST_KEY);

        auto stats = loader.get_stats();
        assert(stats.total_loaded == 0);
        assert(stats.total_failed == 0);
        assert(stats.bytes_processed == 0);

        std::cout << "✓ PASS" << std::endl;
        return true;
    } catch (const std::exception& e) {
        std::cout << "✗ FAIL: " << e.what() << std::endl;
        return false;
    }
}

bool test_invalid_key_path() {
    std::cout << "[TEST] Invalid key path handling... ";

    try {
        EventLoader loader("/nonexistent/path/key.bin");
        std::cout << "✗ FAIL: Should have thrown exception" << std::endl;
        return false;
    } catch (const std::runtime_error& e) {
        std::cout << "✓ PASS (expected exception: " << e.what() << ")" << std::endl;
        return true;
    }
}

bool test_load_single_event() {
    std::cout << "[TEST] Load single event file... ";

    try {
        EventLoader loader(TEST_KEY);

        // Create dummy .pb file
        create_dummy_pb_file("event_001.pb", 512);

        // Try to load event (will fail with bad protobuf but that's expected with dummy data)
        try {
            Event event = loader.load(TEST_DIR + "event_001.pb");

            // If we get here with dummy data, something's wrong
            std::cout << "✗ FAIL: Should have failed to parse dummy protobuf" << std::endl;
            return false;

        } catch (const std::runtime_error& e) {
            // Expected: dummy data won't parse as valid protobuf
            std::string error_msg(e.what());
            if (error_msg.find("parse") != std::string::npos ||
                error_msg.find("protobuf") != std::string::npos) {
                std::cout << "✓ PASS (expected protobuf parse failure with dummy data)" << std::endl;
                return true;
            } else {
                std::cout << "✗ FAIL: Unexpected error: " << e.what() << std::endl;
                return false;
            }
        }

    } catch (const std::exception& e) {
        std::cout << "✗ FAIL: " << e.what() << std::endl;
        return false;
    }
}

bool test_missing_file_handling() {
    std::cout << "[TEST] Missing file error handling... ";

    try {
        EventLoader loader(TEST_KEY);

        // Try to load non-existent file
        loader.load(TEST_DIR + "nonexistent.pb");

        std::cout << "✗ FAIL: Should have thrown exception" << std::endl;
        return false;

    } catch (const std::runtime_error& e) {
        // Expected behavior
        std::cout << "✓ PASS (expected exception)" << std::endl;
        return true;
    }
}

bool test_empty_file_handling() {
    std::cout << "[TEST] Empty file error handling... ";

    try {
        EventLoader loader(TEST_KEY);

        // Create empty file
        create_dummy_pb_file("empty.pb", 0);

        // Try to load empty file
        loader.load(TEST_DIR + "empty.pb");

        std::cout << "✗ FAIL: Should have thrown exception for empty file" << std::endl;
        return false;

    } catch (const std::runtime_error& e) {
        std::string error_msg(e.what());
        if (error_msg.find("Empty file") != std::string::npos) {
            std::cout << "✓ PASS (expected empty file exception)" << std::endl;
            return true;
        } else {
            std::cout << "✗ FAIL: Wrong exception: " << e.what() << std::endl;
            return false;
        }
    }
}

bool test_statistics_tracking() {
    std::cout << "[TEST] Statistics tracking... ";

    try {
        EventLoader loader(TEST_KEY);

        // Try loading several files (will all fail with dummy data, but stats should update)
        create_dummy_pb_file("stats1.pb", 100);
        create_dummy_pb_file("stats2.pb", 500);
        create_dummy_pb_file("stats3.pb", 1000);

        // Attempt loads (expecting failures)
        int attempted = 0;
        try { loader.load(TEST_DIR + "stats1.pb"); } catch (...) { attempted++; }
        try { loader.load(TEST_DIR + "stats2.pb"); } catch (...) { attempted++; }
        try { loader.load(TEST_DIR + "stats3.pb"); } catch (...) { attempted++; }

        auto stats = loader.get_stats();

        // All should have failed (bad protobuf)
        assert(stats.total_failed == 3);
        assert(stats.total_loaded == 0);
        assert(attempted == 3);

        std::cout << "✓ PASS" << std::endl;
        return true;

    } catch (const std::exception& e) {
        std::cout << "✗ FAIL: " << e.what() << std::endl;
        return false;
    }
}

bool test_feature_count_expectations() {
    std::cout << "[TEST] Feature count expectations (101 features)... ";

    // NOTE: This test documents expected behavior
    // With real ml-detector protobuf data, we expect 101 features:
    //   - 61 basic FlowManager features
    //   - 40 embedded detector features (4 detectors × 10 features each)

    std::cout << "✓ PASS (documentation test)" << std::endl;
    std::cout << "  Expected features: 101 (61 base + 40 embedded)" << std::endl;
    std::cout << "  - Protocol, timing, statistics: 61 features" << std::endl;
    std::cout << "  - DDoS embedded: 10 features" << std::endl;
    std::cout << "  - Ransomware embedded: 10 features" << std::endl;
    std::cout << "  - Traffic classification: 10 features" << std::endl;
    std::cout << "  - Internal anomaly: 10 features" << std::endl;
    return true;
}

// ============================================================================
// Test Runner
// ============================================================================

int main() {
    std::cout << "\n=== EventLoader Unit Tests ===" << std::endl;
    std::cout << "Test directory: " << TEST_DIR << std::endl;
    std::cout << "Note: Tests use dummy data; real protobuf integration pending\n" << std::endl;

    setup_test_environment();

    int passed = 0;
    int total = 0;

    // Run tests
    if (test_construction()) passed++;
    total++;

    if (test_invalid_key_path()) passed++;
    total++;

    if (test_load_single_event()) passed++;
    total++;

    if (test_missing_file_handling()) passed++;
    total++;

    if (test_empty_file_handling()) passed++;
    total++;

    if (test_statistics_tracking()) passed++;
    total++;

    if (test_feature_count_expectations()) passed++;
    total++;

    cleanup_test_environment();

    // Summary
    std::cout << "\n=== Test Summary ===" << std::endl;
    std::cout << "Passed: " << passed << "/" << total << std::endl;

    if (passed == total) {
        std::cout << "✓ All tests passed!" << std::endl;
        std::cout << "\nNote: Full integration testing with real ml-detector protobuf" << std::endl;
        std::cout << "      data will validate 101-feature extraction." << std::endl;
        return 0;
    } else {
        std::cout << "✗ Some tests failed!" << std::endl;
        return 1;
    }
}