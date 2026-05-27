// test_csv_file_watcher.cpp
// RAG Ingester - CsvFileWatcher Unit Tests
// Day 67: Verify inotify tail semantics for append-only CSV files
// AUTHORS: Alonso Isidoro Roman + Claude (Anthropic)

#include "csv_file_watcher.hpp"

#include <iostream>
#include <fstream>
#include <thread>
#include <chrono>
#include <atomic>
#include <cassert>
#include <filesystem>
#include <vector>
#include <string>

namespace fs = std::filesystem;
using namespace rag_ingester;

// ============================================================================
// Test infrastructure
// ============================================================================

const std::string TEST_DIR  = "/tmp/csv_watcher_test/";
const std::string TEST_CSV  = TEST_DIR + "test_events.csv";

void setup() {
    fs::create_directories(TEST_DIR);
    // Remove any leftover file from previous run
    if (fs::exists(TEST_CSV)) fs::remove(TEST_CSV);
}

void teardown() {
    if (fs::exists(TEST_DIR)) fs::remove_all(TEST_DIR);
}

// Append one or more lines to the CSV (simulates ml-detector writing)
void append_lines(const std::vector<std::string>& lines) {
    std::ofstream f(TEST_CSV, std::ios::app);
    for (const auto& l : lines) {
        f << l << '\n';
    }
    f.flush();
    // Do NOT close — ml-detector keeps the file open (append-only)
}

// Wait up to max_ms for condition to become true, checking every 50ms
bool wait_for(std::function<bool()> cond, int max_ms = 2000) {
    for (int elapsed = 0; elapsed < max_ms; elapsed += 50) {
        if (cond()) return true;
        std::this_thread::sleep_for(std::chrono::milliseconds(50));
    }
    return false;
}

// ============================================================================
// Tests
// ============================================================================

bool test_construction() {
    std::cout << "[TEST] CsvFileWatcher construction... ";
    try {
        CsvFileWatcher w(TEST_CSV);
        assert(!w.is_running());
        assert(w.lines_detected() == 0);
        assert(w.bytes_consumed() == 0);
        assert(w.watched_path() == TEST_CSV);
        std::cout << "✓ PASS\n";
        return true;
    } catch (const std::exception& e) {
        std::cout << "✗ FAIL: " << e.what() << "\n";
        return false;
    }
}

bool test_detects_lines_on_start_existing_file() {
    std::cout << "[TEST] Detects pre-existing lines on start... ";

    // Write 3 lines BEFORE starting the watcher
    append_lines({"line_one", "line_two", "line_three"});

    std::atomic<int> count{0};
    std::vector<std::string> received;

    CsvFileWatcher w(TEST_CSV);
    w.start([&](const std::string& line, uint64_t /*lineno*/) {
        received.push_back(line);
        ++count;
    });

    bool ok = wait_for([&]{ return count.load() >= 3; });
    w.stop();

    assert(ok);
    assert(count.load() == 3);
    assert(received[0] == "line_one");
    assert(received[2] == "line_three");
    assert(w.lines_detected() == 3);

    std::cout << "✓ PASS\n";
    return true;
}

bool test_detects_appended_lines() {
    std::cout << "[TEST] Detects lines appended after start... ";
    if (fs::exists(TEST_CSV)) fs::remove(TEST_CSV);

    std::atomic<int> count{0};

    CsvFileWatcher w(TEST_CSV);
    w.start([&](const std::string& /*line*/, uint64_t /*lineno*/) {
        ++count;
    });

    // Give watcher time to initialize inotify
    std::this_thread::sleep_for(std::chrono::milliseconds(100));

    append_lines({"event_a", "event_b"});
    bool ok1 = wait_for([&]{ return count.load() >= 2; });
    assert(ok1);
    assert(count.load() == 2);

    append_lines({"event_c"});
    bool ok2 = wait_for([&]{ return count.load() >= 3; });
    w.stop();

    assert(ok2);
    assert(count.load() == 3);
    assert(w.lines_detected() == 3);

    std::cout << "✓ PASS\n";
    return true;
}

bool test_skip_header() {
    std::cout << "[TEST] Skip header line (skip_header=true)... ";
    if (fs::exists(TEST_CSV)) fs::remove(TEST_CSV);

    std::atomic<int> count{0};
    std::vector<std::string> received;

    // skip_header=true: line 1 should not trigger callback
    CsvFileWatcher w(TEST_CSV, /*skip_header=*/true);
    w.start([&](const std::string& line, uint64_t /*lineno*/) {
        received.push_back(line);
        ++count;
    });

    std::this_thread::sleep_for(std::chrono::milliseconds(100));
    append_lines({"HEADER_LINE", "data_line_1", "data_line_2"});

    bool ok = wait_for([&]{ return count.load() >= 2; });
    w.stop();

    assert(ok);
    assert(count.load() == 2);
    assert(received[0] == "data_line_1");
    assert(received[1] == "data_line_2");

    std::cout << "✓ PASS\n";
    return true;
}

bool test_lineno_increments_correctly() {
    std::cout << "[TEST] Line numbers increment correctly... ";
    if (fs::exists(TEST_CSV)) fs::remove(TEST_CSV);

    std::vector<uint64_t> linenos;

    CsvFileWatcher w(TEST_CSV);
    w.start([&](const std::string& /*line*/, uint64_t lineno) {
        linenos.push_back(lineno);
    });

    std::this_thread::sleep_for(std::chrono::milliseconds(100));
    append_lines({"a", "b", "c", "d", "e"});

    bool ok = wait_for([&]{ return linenos.size() >= 5; });
    w.stop();

    assert(ok);
    assert(linenos.size() == 5);
    // Lines should be 1-based and sequential
    for (size_t i = 0; i < linenos.size(); ++i) {
        assert(linenos[i] == i + 1);
    }

    std::cout << "✓ PASS\n";
    return true;
}

bool test_rapid_appends() {
    std::cout << "[TEST] Rapid appends (50 lines)... ";
    if (fs::exists(TEST_CSV)) fs::remove(TEST_CSV);

    std::atomic<int> count{0};

    CsvFileWatcher w(TEST_CSV);
    w.start([&](const std::string& /*line*/, uint64_t /*lineno*/) {
        ++count;
    });

    std::this_thread::sleep_for(std::chrono::milliseconds(100));

    // Write 50 lines in rapid bursts of 10
    for (int burst = 0; burst < 5; ++burst) {
        std::vector<std::string> batch;
        for (int i = 0; i < 10; ++i) {
            batch.push_back("event_" + std::to_string(burst * 10 + i));
        }
        append_lines(batch);
        std::this_thread::sleep_for(std::chrono::milliseconds(20));
    }

    bool ok = wait_for([&]{ return count.load() >= 50; }, 3000);
    w.stop();

    assert(ok);
    assert(count.load() == 50);

    std::cout << "✓ PASS\n";
    return true;
}

bool test_graceful_shutdown() {
    std::cout << "[TEST] Graceful shutdown... ";
    if (fs::exists(TEST_CSV)) fs::remove(TEST_CSV);

    CsvFileWatcher w(TEST_CSV);
    w.start([](const std::string& /*line*/, uint64_t /*lineno*/) {});

    assert(w.is_running());
    std::this_thread::sleep_for(std::chrono::milliseconds(100));

    w.stop();
    assert(!w.is_running());

    std::cout << "✓ PASS\n";
    return true;
}

bool test_bytes_consumed_tracking() {
    std::cout << "[TEST] bytes_consumed tracking... ";
    if (fs::exists(TEST_CSV)) fs::remove(TEST_CSV);

    std::atomic<int> count{0};

    CsvFileWatcher w(TEST_CSV);
    w.start([&](const std::string& /*line*/, uint64_t /*lineno*/) { ++count; });

    std::this_thread::sleep_for(std::chrono::milliseconds(100));

    // "hello\n" = 6 bytes, "world\n" = 6 bytes → 12 bytes total
    append_lines({"hello", "world"});
    bool ok = wait_for([&]{ return count.load() >= 2; });
    w.stop();

    assert(ok);
    // bytes_consumed counts content + '\n' per line
    assert(w.bytes_consumed() == 12);  // 5+1 + 5+1

    std::cout << "✓ PASS\n";
    return true;
}

// ============================================================================
// Main
// ============================================================================

int main() {
    std::cout << "\n=== CsvFileWatcher Unit Tests (Day 67) ===\n";
    std::cout << "Test directory: " << TEST_DIR << "\n\n";

    int passed = 0, total = 0;

    auto run = [&](bool (*fn)()) {
        setup();
        if (fn()) ++passed;
        ++total;
        teardown();
    };

    run(test_construction);
    run(test_detects_lines_on_start_existing_file);
    run(test_detects_appended_lines);
    run(test_skip_header);
    run(test_lineno_increments_correctly);
    run(test_rapid_appends);
    run(test_graceful_shutdown);
    run(test_bytes_consumed_tracking);

    std::cout << "\n=== Summary ===\n";
    std::cout << "Passed: " << passed << "/" << total << "\n";
    if (passed == total) {
        std::cout << "✓ All tests passed!\n";
        return 0;
    }
    std::cout << "✗ Some tests failed!\n";
    return 1;
}