// csv_dir_watcher.hpp
// Day 69 — Directory watcher for daily-rotating CSV files (ml-detector output)
//
// Watches a directory for new YYYY-MM-DD.csv files (IN_CREATE) and for
// modifications to the currently active file (IN_MODIFY). Automatically
// transitions to the new file at midnight rotation.
//
// Single background thread — callbacks fire on that thread.
//
// Day 70: replay_on_start — si true, procesa el contenido existente del
// fichero activo al arrancar (offset=0). Default false mantiene comportamiento
// anterior (seek to EOF, solo eventos nuevos).
//
// AUTHORS: Alonso Isidoro Roman + Claude (Anthropic)
// DATE: Day 69 / Day 70
#pragma once
#include <string>
#include <functional>
#include <thread>
#include <atomic>
#include <cstdint>
namespace rag_ingester {
    class CsvDirWatcher {
    public:
        using LineCallback = std::function<void(const std::string& line)>;

        explicit CsvDirWatcher(const std::string& dir_path,
                               LineCallback callback,
                               bool replay_on_start = false);
        ~CsvDirWatcher();

        // Throws std::runtime_error if dir_path does not exist.
        void start();
        void stop();

        uint64_t lines_detected() const;
        uint64_t files_rotated()  const;

    private:
        std::string   dir_path_;
        LineCallback  callback_;
        bool          replay_on_start_ {false};

        std::thread        thread_;
        std::atomic<bool>  running_ {false};
        std::atomic<uint64_t> lines_detected_ {0};
        std::atomic<uint64_t> files_rotated_  {0};

        static std::string today_filename();
        std::string today_filepath() const;
        void run();
        off_t drain_new_lines(const std::string& filepath, off_t offset);
    };
} // namespace rag_ingester