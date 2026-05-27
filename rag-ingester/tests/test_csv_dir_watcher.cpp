// tests/test_csv_dir_watcher.cpp
// Day 69 — Integration test for CsvDirWatcher
//
// AUTHORS: Alonso Isidoro Roman + Claude (Anthropic)

#include "csv_dir_watcher.hpp"
#include <cassert>
#include <iostream>
#include <fstream>
#include <filesystem>
#include <chrono>
#include <thread>
#include <vector>
#include <mutex>
#include <ctime>
#include <sstream>
#include <iomanip>

namespace fs = std::filesystem;
using namespace rag_ingester;

static std::string today_filename() {
    auto now = std::chrono::system_clock::now();
    std::time_t t = std::chrono::system_clock::to_time_t(now);
    std::tm tm{};
    localtime_r(&t, &tm);
    std::ostringstream ss;
    ss << std::put_time(&tm, "%Y-%m-%d") << ".csv";
    return ss.str();
}

int main() {
    fs::path tmpdir = fs::temp_directory_path() / "test_csv_dir_watcher";
    fs::create_directories(tmpdir);

    std::vector<std::string> received;
    std::mutex mtx;

    auto callback = [&](const std::string& line) {
        std::lock_guard<std::mutex> lk(mtx);
        received.push_back(line);
    };

    CsvDirWatcher watcher(tmpdir.string(), callback);
    watcher.start();
    std::this_thread::sleep_for(std::chrono::milliseconds(100));

    // Write lines to today's file
    fs::path csv_path = tmpdir / today_filename();
    {
        std::ofstream f(csv_path, std::ios::app);
        f << "1771404108582,111.182.236.62,58.122.96.132,RANSOMWARE,BLOCKED,0.9586,hmac1\n";
        f << "1771404108999,10.0.0.1,10.0.0.2,DDOS,BLOCKED,0.8100,hmac2\n";
        f.flush();
    }

    std::this_thread::sleep_for(std::chrono::milliseconds(500));
    watcher.stop();

    {
        std::lock_guard<std::mutex> lk(mtx);
        std::cout << "Lines received: " << received.size() << "\n";
        for (auto& l : received) std::cout << "  -> " << l << "\n";
        assert(received.size() == 2);
        assert(received[0].find("RANSOMWARE") != std::string::npos);
        assert(received[1].find("DDOS")       != std::string::npos);
    }

    assert(watcher.lines_detected() == 2);

    fs::remove_all(tmpdir);

    std::cout << "\n[Day69] csv_dir_watcher: all tests passed\n";
    return 0;
}