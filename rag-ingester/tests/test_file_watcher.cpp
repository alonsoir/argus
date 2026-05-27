// test_file_watcher.cpp
// RAG Ingester - FileWatcher Unit Tests
// Day 36: Verify inotify-based file monitoring

#include "file_watcher.hpp"
#include <iostream>
#include <fstream>
#include <thread>
#include <chrono>
#include <atomic>
#include <cassert>
#include <filesystem>

namespace fs = std::filesystem;
using namespace rag_ingester;

// Test directory
const std::string TEST_DIR = "/tmp/rag_ingester_test/";

// ============================================================================
// Test Utilities
// ============================================================================

void setup_test_dir() {
    // Create test directory
    fs::create_directories(TEST_DIR);
    
    // Clean any existing .pb files
    for (const auto& entry : fs::directory_iterator(TEST_DIR)) {
        if (entry.path().extension() == ".pb") {
            fs::remove(entry.path());
        }
    }
}

void cleanup_test_dir() {
    // Remove test directory
    if (fs::exists(TEST_DIR)) {
        fs::remove_all(TEST_DIR);
    }
}

void create_test_file(const std::string& filename, const std::string& content) {
    std::string filepath = TEST_DIR + filename;
    std::ofstream file(filepath);
    file << content;
    file.close();  // Ensure IN_CLOSE_WRITE is triggered
}

// ============================================================================
// Test Cases
// ============================================================================

bool test_construction() {
    std::cout << "[TEST] FileWatcher construction... ";
    
    try {
        FileWatcher watcher(TEST_DIR, "*.pb");
        assert(!watcher.is_running());
        assert(watcher.get_files_detected() == 0);
        
        std::cout << "✓ PASS" << std::endl;
        return true;
    } catch (const std::exception& e) {
        std::cout << "✗ FAIL: " << e.what() << std::endl;
        return false;
    }
}

bool test_single_file_detection() {
    std::cout << "[TEST] Single .pb file detection... ";
    
    std::atomic<int> callback_count{0};
    std::string detected_file;
    
    auto callback = [&](const std::string& filepath) {
        callback_count++;
        detected_file = filepath;
        std::cout << "\n  [CALLBACK] Detected: " << filepath << std::endl;
    };
    
    try {
        FileWatcher watcher(TEST_DIR, "*.pb");
        watcher.start(callback);
        
        // Give watcher time to initialize
        std::this_thread::sleep_for(std::chrono::milliseconds(50));
        
        // Create test file
        create_test_file("test_event.pb", "dummy protobuf data");
        
        // Wait for detection (up to 1 second)
        int max_waits = 10;
        while (callback_count == 0 && max_waits-- > 0) {
            std::this_thread::sleep_for(std::chrono::milliseconds(100));
        }
        
        watcher.stop();
        
        // Verify detection
        assert(callback_count == 1);
        assert(detected_file == TEST_DIR + "test_event.pb");
        assert(watcher.get_files_detected() == 1);
        
        std::cout << "✓ PASS" << std::endl;
        return true;
        
    } catch (const std::exception& e) {
        std::cout << "✗ FAIL: " << e.what() << std::endl;
        return false;
    }
}

bool test_pattern_filtering() {
    std::cout << "[TEST] Pattern filtering (*.pb only)... ";
    
    std::atomic<int> callback_count{0};
    
    auto callback = [&](const std::string& filepath) {
        callback_count++;
        std::cout << "\n  [CALLBACK] Detected: " << filepath << std::endl;
    };
    
    try {
        FileWatcher watcher(TEST_DIR, "*.pb");
        watcher.start(callback);
        
        std::this_thread::sleep_for(std::chrono::milliseconds(50));
        
        // Create .pb file (should be detected)
        create_test_file("event1.pb", "data");
        std::this_thread::sleep_for(std::chrono::milliseconds(150));
        
        // Create .txt file (should be ignored)
        create_test_file("event2.txt", "data");
        std::this_thread::sleep_for(std::chrono::milliseconds(150));
        
        // Create another .pb file (should be detected)
        create_test_file("event3.pb", "data");
        std::this_thread::sleep_for(std::chrono::milliseconds(150));
        
        watcher.stop();
        
        // Should detect exactly 2 .pb files
        assert(callback_count == 2);
        assert(watcher.get_files_detected() == 2);
        
        std::cout << "✓ PASS" << std::endl;
        return true;
        
    } catch (const std::exception& e) {
        std::cout << "✗ FAIL: " << e.what() << std::endl;
        return false;
    }
}

bool test_multiple_files_rapid() {
    std::cout << "[TEST] Multiple files rapid detection... ";
    
    std::atomic<int> callback_count{0};
    
    auto callback = [&](const std::string& /*filepath*/) {
        callback_count++;
    };
    
    try {
        FileWatcher watcher(TEST_DIR, "*.pb");
        watcher.start(callback);
        
        std::this_thread::sleep_for(std::chrono::milliseconds(50));
        
        // Create 5 files rapidly
        const int num_files = 5;
        for (int i = 0; i < num_files; i++) {
            create_test_file("rapid_" + std::to_string(i) + ".pb", "data");
        }
        
        // Wait for all detections
        int max_waits = 20;
        while (callback_count < num_files && max_waits-- > 0) {
            std::this_thread::sleep_for(std::chrono::milliseconds(100));
        }
        
        watcher.stop();
        
        // Should detect all files
        assert(callback_count == num_files);
        assert(watcher.get_files_detected() == num_files);
        
        std::cout << "✓ PASS" << std::endl;
        return true;
        
    } catch (const std::exception& e) {
        std::cout << "✗ FAIL: " << e.what() << std::endl;
        return false;
    }
}

bool test_graceful_shutdown() {
    std::cout << "[TEST] Graceful shutdown... ";
    
    try {
        FileWatcher watcher(TEST_DIR, "*.pb");
        
        auto callback = [](const std::string&) {
            std::this_thread::sleep_for(std::chrono::milliseconds(10));
        };
        
        watcher.start(callback);
        assert(watcher.is_running());
        
        // Create file during operation
        create_test_file("shutdown_test.pb", "data");
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
        
        // Stop should complete cleanly
        watcher.stop();
        assert(!watcher.is_running());
        
        std::cout << "✓ PASS" << std::endl;
        return true;
        
    } catch (const std::exception& e) {
        std::cout << "✗ FAIL: " << e.what() << std::endl;
        return false;
    }
}

// ============================================================================
// Test Runner
// ============================================================================

int main() {
    std::cout << "\n=== FileWatcher Unit Tests ===" << std::endl;
    std::cout << "Test directory: " << TEST_DIR << "\n" << std::endl;

    int passed = 0;
    int total  = 0;

    auto run = [&](bool (*fn)()) {
        setup_test_dir();
        if (fn()) ++passed;
        ++total;
        cleanup_test_dir();
    };

    run(test_construction);
    run(test_single_file_detection);
    run(test_pattern_filtering);
    run(test_multiple_files_rapid);
    run(test_graceful_shutdown);

    // Summary
    std::cout << "\n=== Test Summary ===" << std::endl;
    std::cout << "Passed: " << passed << "/" << total << std::endl;

    if (passed == total) {
        std::cout << "✓ All tests passed!" << std::endl;
        return 0;
    } else {
        std::cout << "✗ Some tests failed!" << std::endl;
        return 1;
    }
}
