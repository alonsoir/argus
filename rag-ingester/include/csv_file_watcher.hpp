// csv_file_watcher.hpp
// RAG Ingester - CsvFileWatcher Component
// Day 67: inotify-based tail watcher for append-only CSV files
// Semantics: IN_MODIFY + byte offset tracking (NOT IN_CLOSE_WRITE)
// AUTHORS: Alonso Isidoro Roman + Claude (Anthropic)
// Via Appia Quality - Built to last

#ifndef CSV_FILE_WATCHER_HPP
#define CSV_FILE_WATCHER_HPP

#include <string>
#include <functional>
#include <atomic>
#include <thread>
#include <memory>
#include <fstream>
#include <cstdint>

namespace rag_ingester {

/**
 * @brief Callback invoked with each new complete line detected in the CSV.
 * @param line  Raw CSV line (without trailing newline)
 * @param lineno  1-based line number within the file
 */
using CsvLineCallback = std::function<void(const std::string& line, uint64_t lineno)>;

/**
 * @brief inotify-based tail watcher for a single append-only CSV file.
 *
 * Design differences vs FileWatcher (*.pb):
 *  - Monitors ONE specific file, not a directory
 *  - Uses IN_MODIFY (not IN_CLOSE_WRITE) — the file is never "closed"
 *  - Tracks a read offset so only new bytes are processed each wake-up
 *  - Handles daily rotation: if the monitored file is replaced (IN_CREATE
 *    on the parent directory), automatically reopens the new file from offset 0
 *  - Skips header line (line 1) automatically — CSV schema has no header
 *    in the current schema but the flag is configurable for safety
 *
 * Thread model:
 *  - Single background worker thread
 *  - Callback is invoked from that thread — keep it fast or hand off
 *
 * Concurrency with FileWatcher:
 *  - Completely independent inotify_fd and watch_descriptor
 *  - No shared state — synchronisation is the caller's responsibility
 *    for downstream resources (FAISS, SQLite)
 */
class CsvFileWatcher {
public:
    /**
     * @param csv_path   Absolute path to the CSV file to tail
     * @param skip_header  If true, line 1 is silently skipped (default: false)
     * @param poll_timeout_ms  inotify poll timeout in ms (default: 500)
     */
    explicit CsvFileWatcher(const std::string& csv_path,
                            bool skip_header      = false,
                            int  poll_timeout_ms  = 500);

    ~CsvFileWatcher();

    // Non-copyable — owns inotify fds and a thread
    CsvFileWatcher(const CsvFileWatcher&) = delete;
    CsvFileWatcher& operator=(const CsvFileWatcher&) = delete;

    /**
     * @brief Start tailing in a background thread.
     * @param callback  Invoked for each new complete line (never called with
     *                  partial lines — only full \n-terminated rows)
     * @throws std::runtime_error if inotify init fails or file not found
     */
    void start(CsvLineCallback callback);

    /**
     * @brief Stop tailing and join the worker thread.
     */
    void stop();

    bool     is_running()       const noexcept;
    uint64_t lines_detected()   const noexcept;  ///< Total new lines delivered
    uint64_t bytes_consumed()   const noexcept;  ///< Total bytes read
    std::string watched_path()  const noexcept;

private:
    // Config
    std::string csv_path_;
    std::string watch_dir_;   // parent directory (for rotation detection)
    std::string filename_;    // basename of csv_path_
    bool        skip_header_;
    int         poll_timeout_ms_;

    // inotify fds
    int inotify_fd_     {-1};
    int wd_file_        {-1};  // watch on the file itself (IN_MODIFY)
    int wd_dir_         {-1};  // watch on the parent dir (IN_CREATE for rotation)

    // State
    std::atomic<bool>     running_       {false};
    std::atomic<uint64_t> lines_detected_{0};
    std::atomic<uint64_t> bytes_consumed_{0};

    std::streampos  read_offset_ {0};   // current byte position in the file
    uint64_t        line_count_  {0};   // lines emitted (1-based)

    std::ifstream       file_;
    std::string         line_buffer_;   // accumulates partial lines across reads

    std::unique_ptr<std::thread> worker_thread_;
    CsvLineCallback callback_;

    // Internal
    void worker_loop();
    void drain_new_lines();               // read from read_offset_ to EOF, emit lines
    void reopen_file();                   // handles rotation or initial open
    void init_inotify();
    void cleanup_inotify() noexcept;
    bool is_same_file() const;           // detects inode change (rotation)
};

} // namespace rag_ingester

#endif // CSV_FILE_WATCHER_HPP