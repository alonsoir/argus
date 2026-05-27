// file_watcher.cpp
// RAG Ingester - FileWatcher Implementation
// Day 36: inotify-based file monitoring for .pb events
// Via Appia Quality - Robust, efficient file detection

#include "file_watcher.hpp"
#include <sys/inotify.h>
#include <unistd.h>
#include <poll.h>
#include <cstring>
#include <stdexcept>
#include <iostream>
#include <algorithm>
#include <filesystem>

namespace rag_ingester {

// Buffer size for inotify events (4KB - enough for ~16 events)
constexpr size_t INOTIFY_BUFFER_SIZE = 4096;

// Poll timeout in milliseconds (100ms for responsive shutdown)
constexpr int POLL_TIMEOUT_MS = 100;

FileWatcher::FileWatcher(const std::string& directory, const std::string& pattern)
    : directory_(directory),
      pattern_(pattern),
      inotify_fd_(-1),
      watch_descriptor_(-1),
      running_(false),
      files_detected_(0) {
    
    // Validate directory path (basic check)
    if (directory_.empty()) {
        throw std::invalid_argument("Directory path cannot be empty");
    }
    
    // Ensure directory ends with /
    if (directory_.back() != '/') {
        directory_ += '/';
    }
}

FileWatcher::~FileWatcher() {
    stop();
}

void FileWatcher::start(FileCallback callback) {
    if (running_.load()) {
        throw std::runtime_error("FileWatcher already running");
    }
    
    if (!callback) {
        throw std::invalid_argument("Callback cannot be null");
    }
    
    callback_ = std::move(callback);

    // 🔧 FIX Day 38: Process existing files BEFORE watching new ones
    process_existing_files();

    // Initialize inotify
    init_inotify();
    
    // Start worker thread
    running_.store(true);
    worker_thread_ = std::make_unique<std::thread>(&FileWatcher::worker_loop, this);
    
    std::cout << "[INFO] FileWatcher started: " << directory_ 
              << " (pattern: " << pattern_ << ")" << std::endl;
}

void FileWatcher::stop() {
    if (!running_.load()) {
        return;
    }
    
    // Signal worker to stop
    running_.store(false);
    
    // Join worker thread
    if (worker_thread_ && worker_thread_->joinable()) {
        worker_thread_->join();
    }
    
    // Cleanup inotify resources
    cleanup_inotify();
    
    std::cout << "[INFO] FileWatcher stopped (detected " 
              << files_detected_.load() << " files)" << std::endl;
}

bool FileWatcher::is_running() const noexcept {
    return running_.load();
}

uint64_t FileWatcher::get_files_detected() const noexcept {
    return files_detected_.load();
}

void FileWatcher::init_inotify() {
    // Create inotify instance
    inotify_fd_ = inotify_init1(IN_NONBLOCK);
    if (inotify_fd_ == -1) {
        throw std::runtime_error("Failed to initialize inotify: " + 
                                 std::string(strerror(errno)));
    }
    
    // Add watch on directory
    // IN_CLOSE_WRITE: File closed after writing (ensures complete file)
    // IN_MOVED_TO: File moved into directory (e.g., atomic rename)
    uint32_t mask = IN_CLOSE_WRITE | IN_MOVED_TO;
    
    watch_descriptor_ = inotify_add_watch(inotify_fd_, directory_.c_str(), mask);
    if (watch_descriptor_ == -1) {
        close(inotify_fd_);
        inotify_fd_ = -1;
        throw std::runtime_error("Failed to add inotify watch on " + directory_ + 
                                 ": " + std::string(strerror(errno)));
    }
}

void FileWatcher::cleanup_inotify() noexcept {
    if (watch_descriptor_ != -1) {
        inotify_rm_watch(inotify_fd_, watch_descriptor_);
        watch_descriptor_ = -1;
    }
    
    if (inotify_fd_ != -1) {
        close(inotify_fd_);
        inotify_fd_ = -1;
    }
}

void FileWatcher::worker_loop() {
    // Event buffer (stack-allocated, reused)
    char buffer[INOTIFY_BUFFER_SIZE];
    
    // pollfd for non-blocking read with timeout
    struct pollfd pfd;
    pfd.fd = inotify_fd_;
    pfd.events = POLLIN;
    
    while (running_.load()) {
        // Wait for events with timeout (allows checking running_ flag)
        int poll_result = poll(&pfd, 1, POLL_TIMEOUT_MS);
        
        if (poll_result == -1) {
            if (errno == EINTR) {
                continue; // Interrupted by signal, retry
            }
            std::cerr << "[ERROR] FileWatcher poll failed: " 
                      << strerror(errno) << std::endl;
            break;
        }
        
        if (poll_result == 0) {
            // Timeout - no events, check running_ flag
            continue;
        }
        
        // Events available, read them
        ssize_t length = read(inotify_fd_, buffer, sizeof(buffer));
        
        if (length == -1) {
            if (errno == EAGAIN || errno == EWOULDBLOCK) {
                continue; // No data despite poll saying yes (race)
            }
            std::cerr << "[ERROR] FileWatcher read failed: " 
                      << strerror(errno) << std::endl;
            break;
        }
        
        if (length > 0) {
            process_events(buffer, length);
        }
    }
}

void FileWatcher::process_events(const char* buffer, ssize_t length) {
    ssize_t offset = 0;
    
    while (offset < length) {
        const struct inotify_event* event = 
            reinterpret_cast<const struct inotify_event*>(buffer + offset);
        
        // Check if event has a filename
        if (event->len > 0) {
            std::string filename(event->name);
            
            // Check if filename matches pattern
            if (matches_pattern(filename)) {
                std::string filepath = directory_ + filename;
                
                // Invoke callback (thread-safe)
                try {
                    callback_(filepath);
                    files_detected_.fetch_add(1);
                } catch (const std::exception& e) {
                    std::cerr << "[ERROR] FileWatcher callback exception: " 
                              << e.what() << std::endl;
                }
            }
        }
        
        // Move to next event in buffer
        offset += sizeof(struct inotify_event) + event->len;
    }
}

bool FileWatcher::matches_pattern(const std::string& filename) const {
    // Simple wildcard matching for "*.ext" pattern

    if (pattern_.empty() || pattern_ == "*") {
        return true; // Match all
    }

    // Check for "*.ext" pattern (supports double extensions like "*.pb.enc")
    if (pattern_.size() >= 2 && pattern_[0] == '*' && pattern_[1] == '.') {
        std::string suffix = pattern_.substr(1); // Skip "*", keep ".ext" (e.g., ".pb.enc")

        // Check if filename ends with suffix
        if (filename.size() < suffix.size()) {
            return false;
        }

        // Compare the end of filename with suffix
        return filename.compare(filename.size() - suffix.size(), suffix.size(), suffix) == 0;
    }

    // Fallback: exact match
    return filename == pattern_;
}

void FileWatcher::process_existing_files() {
    namespace fs = std::filesystem;

    if (!fs::exists(directory_)) {
        std::cout << "[WARN] Directory does not exist: " << directory_ << std::endl;
        return;
    }

    std::cout << "[INFO] Scanning for existing files in: " << directory_ << std::endl;

    size_t count = 0;
    try {
        for (const auto& entry : fs::directory_iterator(directory_)) {
            if (entry.is_regular_file()) {
                std::string filename = entry.path().filename().string();

                if (matches_pattern(filename)) {
                    std::string filepath = entry.path().string();

                    try {
                        callback_(filepath);
                        count++;
                    } catch (const std::exception& e) {
                        std::cerr << "[ERROR] Failed to process existing file "
                                  << filepath << ": " << e.what() << std::endl;
                    }
                }
            }
        }

        std::cout << "[INFO] Processed " << count << " existing files" << std::endl;
        files_detected_.fetch_add(count);

    } catch (const std::exception& e) {
        std::cerr << "[ERROR] Failed to scan directory: " << e.what() << std::endl;
    }
}

} // namespace rag_ingester
