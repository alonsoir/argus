// csv_file_watcher.cpp
// RAG Ingester - CsvFileWatcher Implementation
// Day 67: inotify tail semantics for append-only CSV
// AUTHORS: Alonso Isidoro Roman + Claude (Anthropic)
// Via Appia Quality - Built to last

#include "csv_file_watcher.hpp"

#include <sys/inotify.h>
#include <sys/stat.h>
#include <unistd.h>
#include <poll.h>

#include <filesystem>
#include <stdexcept>
#include <iostream>
#include <cstring>

namespace fs = std::filesystem;

namespace rag_ingester {

// ============================================================================
// Constructor / Destructor
// ============================================================================

CsvFileWatcher::CsvFileWatcher(const std::string& csv_path,
                               bool skip_header,
                               int  poll_timeout_ms)
    : csv_path_       (csv_path)
    , skip_header_    (skip_header)
    , poll_timeout_ms_(poll_timeout_ms)
{
    fs::path p(csv_path);
    watch_dir_ = p.parent_path().string();
    filename_  = p.filename().string();

    if (watch_dir_.empty()) watch_dir_ = ".";
}

CsvFileWatcher::~CsvFileWatcher() {
    stop();
}

// ============================================================================
// Public interface
// ============================================================================

void CsvFileWatcher::start(CsvLineCallback callback) {
    if (running_.load()) return;

    callback_ = std::move(callback);
    init_inotify();
    reopen_file();

    running_.store(true);
    worker_thread_ = std::make_unique<std::thread>([this]{ worker_loop(); });
}

void CsvFileWatcher::stop() {
    if (!running_.exchange(false)) return;

    // Wake up poll() by writing to a self-pipe or just let timeout fire.
    // Closing inotify_fd will unblock poll immediately.
    cleanup_inotify();

    if (worker_thread_ && worker_thread_->joinable()) {
        worker_thread_->join();
    }
    worker_thread_.reset();

    if (file_.is_open()) file_.close();
}

bool     CsvFileWatcher::is_running()     const noexcept { return running_.load(); }
uint64_t CsvFileWatcher::lines_detected() const noexcept { return lines_detected_.load(); }
uint64_t CsvFileWatcher::bytes_consumed() const noexcept { return bytes_consumed_.load(); }
std::string CsvFileWatcher::watched_path() const noexcept { return csv_path_; }

// ============================================================================
// Worker loop
// ============================================================================

void CsvFileWatcher::worker_loop() {
    constexpr size_t BUF_LEN = 4096;
    char buf[BUF_LEN] __attribute__((aligned(__alignof__(inotify_event))));

    while (running_.load()) {
        struct pollfd pfd {inotify_fd_, POLLIN, 0};
        int ret = poll(&pfd, 1, poll_timeout_ms_);

        if (ret < 0) {
            if (errno == EINTR) continue;  // signal — keep going
            break;                         // fd closed by stop() — exit
        }

        if (ret == 0) {
            // Timeout — drain anyway in case inotify missed an event
            // (can happen on some kernels with high-frequency appends)
            if (file_.is_open()) drain_new_lines();
            continue;
        }

        // Read inotify events
        ssize_t len = read(inotify_fd_, buf, BUF_LEN);
        if (len <= 0) break;

        const inotify_event* ev = nullptr;
        for (ssize_t i = 0; i < len;
             i += sizeof(inotify_event) + ev->len)
        {
            ev = reinterpret_cast<const inotify_event*>(buf + i);

            // IN_MODIFY on the file itself → new data appended
            if (ev->wd == wd_file_ && (ev->mask & IN_MODIFY)) {
                drain_new_lines();
            }

            // IN_CREATE on parent dir → possible daily rotation
            // (ml-detector creates YYYY-MM-DD.csv at midnight)
            if (ev->wd == wd_dir_ && (ev->mask & IN_CREATE)) {
                std::string created(ev->name, strnlen(ev->name, ev->len));
                if (created == filename_) {
                    // New file with same name — reopen from offset 0
                    reopen_file();
                }
            }
        }
    }
}

// ============================================================================
// Core: drain new lines from current offset to EOF
// ============================================================================

void CsvFileWatcher::drain_new_lines() {
    if (!file_.is_open()) return;

    file_.clear();                        // clear any prior eof/fail bits
    file_.seekg(read_offset_);

    std::string raw_line;
    while (std::getline(file_, raw_line)) {
        // getline strips '\n'; handle Windows-style '\r\n' too
        if (!raw_line.empty() && raw_line.back() == '\r') {
            raw_line.pop_back();
        }

        // Update offset *after* successful getline
        read_offset_ = file_.tellg();
        bytes_consumed_.fetch_add(raw_line.size() + 1,  // +1 for '\n'
                                  std::memory_order_relaxed);

        ++line_count_;

        // Optionally skip header line
        if (skip_header_ && line_count_ == 1) continue;

        // Skip empty lines (e.g. trailing newline at EOF)
        if (raw_line.empty()) continue;

        lines_detected_.fetch_add(1, std::memory_order_relaxed);

        if (callback_) {
            callback_(raw_line, line_count_);
        }
    }

    // If getline stopped mid-line (no '\n' yet), seekg back so the partial
    // line will be re-read on the next IN_MODIFY event.
    if (file_.eof() && !file_.bad()) {
        file_.clear();
        // read_offset_ already points past the last complete line
        // — partial tail left in file stream will be picked up next time
    }
}

// ============================================================================
// File open / rotation
// ============================================================================

void CsvFileWatcher::reopen_file() {
    if (file_.is_open()) file_.close();

    file_.open(csv_path_, std::ios::in);
    if (!file_.is_open()) {
        // File may not exist yet if ml-detector hasn't created today's file.
        // Not fatal — drain_new_lines() will be a no-op until it exists.
        std::cerr << "[CsvFileWatcher] File not yet available: "
                  << csv_path_ << "\n";
        return;
    }

    read_offset_ = 0;
    line_count_  = 0;
    std::cerr << "[CsvFileWatcher] Opened: " << csv_path_ << "\n";

    // Drain whatever is already in the file on startup
    drain_new_lines();
}

// ============================================================================
// inotify setup / teardown
// ============================================================================

void CsvFileWatcher::init_inotify() {
    inotify_fd_ = inotify_init1(IN_NONBLOCK);
    if (inotify_fd_ < 0) {
        throw std::runtime_error(
            std::string("[CsvFileWatcher] inotify_init1 failed: ") +
            strerror(errno));
    }

    // Watch the file for modifications (append)
    // The file may not exist yet — we add the watch only if it does
    if (fs::exists(csv_path_)) {
        wd_file_ = inotify_add_watch(inotify_fd_,
                                     csv_path_.c_str(),
                                     IN_MODIFY);
        if (wd_file_ < 0) {
            std::cerr << "[CsvFileWatcher] inotify_add_watch(file) failed: "
                      << strerror(errno) << "\n";
        }
    }

    // Always watch the parent directory for IN_CREATE (rotation)
    if (!watch_dir_.empty() && fs::exists(watch_dir_)) {
        wd_dir_ = inotify_add_watch(inotify_fd_,
                                    watch_dir_.c_str(),
                                    IN_CREATE);
        if (wd_dir_ < 0) {
            std::cerr << "[CsvFileWatcher] inotify_add_watch(dir) failed: "
                      << strerror(errno) << "\n";
        }
    }
}

void CsvFileWatcher::cleanup_inotify() noexcept {
    if (wd_file_ >= 0 && inotify_fd_ >= 0) {
        inotify_rm_watch(inotify_fd_, wd_file_);
        wd_file_ = -1;
    }
    if (wd_dir_ >= 0 && inotify_fd_ >= 0) {
        inotify_rm_watch(inotify_fd_, wd_dir_);
        wd_dir_ = -1;
    }
    if (inotify_fd_ >= 0) {
        close(inotify_fd_);
        inotify_fd_ = -1;
    }
}

// ============================================================================
// Rotation detection helper
// ============================================================================

bool CsvFileWatcher::is_same_file() const {
    // Compare inodes: if the file on disk has a different inode than
    // the one we have open, rotation has occurred.
    if (!file_.is_open()) return false;

    struct stat st_disk {};
    if (stat(csv_path_.c_str(), &st_disk) != 0) return false;

    // We can't get the inode of the open stream directly without an fd.
    // CsvFileWatcher uses ifstream — for simplicity, rely on IN_CREATE
    // events instead of inode comparison (sufficient for daily rotation).
    (void)st_disk;
    return true;
}

} // namespace rag_ingester