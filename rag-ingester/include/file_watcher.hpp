// file_watcher.hpp
// RAG Ingester - FileWatcher Component
// Day 36: inotify-based file monitoring for .pb events
// Via Appia Quality - Foundation for event ingestion

#ifndef FILE_WATCHER_HPP
#define FILE_WATCHER_HPP

#include <string>
#include <functional>
#include <atomic>
#include <thread>
#include <memory>
#include <vector>

namespace rag_ingester {

/**
 * @brief Callback function type for file detection events
 * @param filepath Absolute path to the detected file
 */
using FileCallback = std::function<void(const std::string& filepath)>;

/**
 * @brief inotify-based file watcher for monitoring .pb event files
 * 
 * Monitors a directory for new .pb files using Linux inotify.
 * Detects IN_CLOSE_WRITE events to ensure files are fully written.
 * Thread-safe callback invocation for event processing.
 * 
 * Design Constraints:
 * - Non-blocking read with configurable timeout
 * - Pattern-based filtering (*.pb)
 * - Graceful shutdown with thread join
 * - Memory-efficient (single buffer reuse)
 */
class FileWatcher {
public:
    /**
     * @brief Construct FileWatcher for specified directory
     * @param directory Path to watch (e.g., /vagrant/logs/rag/events)
     * @param pattern File pattern to match (e.g., "*.pb")
     */
    FileWatcher(const std::string& directory, const std::string& pattern = "*.pb");
    
    /**
     * @brief Destructor - ensures clean shutdown
     */
    ~FileWatcher();
    
    // Non-copyable
    FileWatcher(const FileWatcher&) = delete;
    FileWatcher& operator=(const FileWatcher&) = delete;
    
    /**
     * @brief Start watching directory in background thread
     * @param callback Function to call when matching file is detected
     * @throws std::runtime_error if inotify initialization fails
     */
    void start(FileCallback callback);
    
    /**
     * @brief Stop watching and join worker thread
     */
    void stop();
    
    /**
     * @brief Check if watcher is currently running
     */
    bool is_running() const noexcept;
    
    /**
     * @brief Get count of files detected since start
     */
    uint64_t get_files_detected() const noexcept;

private:
    // Configuration
    std::string directory_;
    std::string pattern_;
    
    // inotify file descriptors
    int inotify_fd_;
    int watch_descriptor_;
    
    // Threading
    std::atomic<bool> running_;
    std::unique_ptr<std::thread> worker_thread_;
    FileCallback callback_;
    
    // Statistics
    std::atomic<uint64_t> files_detected_;
    
    /**
     * @brief Worker thread main loop
     */
    void worker_loop();
    
    /**
     * @brief Process inotify events from buffer
     * @param buffer Event buffer from inotify_read
     * @param length Number of bytes read
     */
    void process_events(const char* buffer, ssize_t length);
    
    /**
     * @brief Check if filename matches pattern
     * @param filename File name (not full path)
     * @return true if matches pattern
     */
    bool matches_pattern(const std::string& filename) const;

    /**
     * @brief Process files that already exist in directory (Day 38 fix)
     */
    void process_existing_files();

    /**
     * @brief Initialize inotify file descriptors
     * @throws std::runtime_error on failure
     */
    void init_inotify();
    
    /**
     * @brief Cleanup inotify file descriptors
     */
    void cleanup_inotify() noexcept;
};

} // namespace rag_ingester

#endif // FILE_WATCHER_HPP
