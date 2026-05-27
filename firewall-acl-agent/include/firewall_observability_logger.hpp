// firewall_observability_logger.hpp
// Day 50 - Comprehensive Observability for Firewall ACL Agent
// Structured logging with microsecond precision + key-value pairs

#ifndef FIREWALL_OBSERVABILITY_LOGGER_HPP
#define FIREWALL_OBSERVABILITY_LOGGER_HPP

#include <string>
#include <fstream>
#include <sstream>
#include <chrono>
#include <mutex>
#include <iomanip>
#include <ctime>

namespace mldefender {
namespace firewall {
namespace observability {

// Forward declarations for external linkage
extern std::unique_ptr<class ObservabilityLogger> g_logger;

/**
 * ObservabilityLogger - Structured logging for firewall operations
 *
 * Features:
 * - Microsecond-precision timestamps
 * - Key-value pair logging
 * - Multiple log levels (DEBUG, INFO, BATCH, IPSET, WARN, ERROR, CRASH)
 * - Thread-safe file output
 * - Verbose mode control
 */
class ObservabilityLogger {
public:
    // Log levels - renamed to avoid conflicts with protobuf DEBUG macro
    enum class Level {
        LOG_DEBUG,   // Detailed diagnostic info
        LOG_INFO,    // General informational messages
        LOG_BATCH,   // Batch processing events
        LOG_IPSET,   // IPSet operations
        LOG_WARN,    // Warning conditions
        LOG_ERROR,   // Error conditions
        LOG_CRASH    // Critical crashes
    };

    ObservabilityLogger(const std::string& log_path, bool verbose = true)
        : verbose_mode_(verbose) {
        log_file_.open(log_path, std::ios::app);
        if (!log_file_.is_open()) {
            throw std::runtime_error("Failed to open log file: " + log_path);
        }
    }

    ~ObservabilityLogger() {
        if (log_file_.is_open()) {
            log_file_.close();
        }
    }

    // Get current timestamp with microsecond precision
    static std::string get_timestamp() {
        auto now = std::chrono::system_clock::now();
        auto us = std::chrono::duration_cast<std::chrono::microseconds>(
            now.time_since_epoch()) % 1000000;
        auto timer = std::chrono::system_clock::to_time_t(now);
        std::tm bt{};
        localtime_r(&timer, &bt);

        std::ostringstream oss;
        oss << std::put_time(&bt, "%Y-%m-%d %H:%M:%S");
        oss << '.' << std::setfill('0') << std::setw(6) << us.count();
        return oss.str();
    }

    // ANSI color codes for terminal output
    static const char* get_color(Level level) {
        switch (level) {
            case Level::LOG_DEBUG:  return "\033[0;36m";  // Cyan
            case Level::LOG_INFO:   return "\033[0;32m";  // Green
            case Level::LOG_BATCH:  return "\033[0;35m";  // Magenta
            case Level::LOG_IPSET:  return "\033[0;34m";  // Blue
            case Level::LOG_WARN:   return "\033[1;33m";  // Yellow
            case Level::LOG_ERROR:  return "\033[0;31m";  // Red
            case Level::LOG_CRASH:  return "\033[1;31m";  // Bold Red
            default:                return "\033[0m";     // Reset
        }
    }

    static const char* level_str(Level level) {
        switch (level) {
            case Level::LOG_DEBUG:  return "DEBUG";
            case Level::LOG_INFO:   return "INFO ";
            case Level::LOG_BATCH:  return "BATCH";
            case Level::LOG_IPSET:  return "IPSET";
            case Level::LOG_WARN:   return "WARN ";
            case Level::LOG_ERROR:  return "ERROR";
            case Level::LOG_CRASH:  return "CRASH";
            default:                return "UNKNOWN";
        }
    }

    // Variadic template for key-value pairs
    template<typename... Args>
    void log(Level level, const std::string& message, Args&&... args) {
        std::lock_guard<std::mutex> lock(log_mutex_);

        std::ostringstream oss;

        // Timestamp and level
        oss << get_timestamp() << " [" << level_str(level) << "] " << message;

        // Append key-value pairs
        append_kvp(oss, std::forward<Args>(args)...);

        std::string log_line = oss.str();

        // Write to file
        log_file_ << log_line << std::endl;
        log_file_.flush();

        // Console output (if verbose)
        if (verbose_mode_) {
            std::cout << get_color(level) << log_line << "\033[0m" << std::endl;
        }
    }

private:
    std::ofstream log_file_;
    std::mutex log_mutex_;
    bool verbose_mode_;

    // Base case: no more arguments
    void append_kvp(std::ostringstream&) {}

    // Recursive case: process key-value pairs
    template<typename Key, typename Value, typename... Rest>
    void append_kvp(std::ostringstream& oss, Key&& key, Value&& value, Rest&&... rest) {
        oss << " | " << key << "=" << value;
        append_kvp(oss, std::forward<Rest>(rest)...);
    }
};

// Global logger instance (defined in main.cpp)
extern std::unique_ptr<ObservabilityLogger> g_logger;

} // namespace observability
} // namespace firewall
} // namespace mldefender

// Convenience macros for logging
#define FIREWALL_LOG_DEBUG(msg, ...) \
    if (mldefender::firewall::observability::g_logger) { \
        mldefender::firewall::observability::g_logger->log( \
            mldefender::firewall::observability::ObservabilityLogger::Level::LOG_DEBUG, msg, ##__VA_ARGS__); \
    }

#define FIREWALL_LOG_INFO(msg, ...) \
    if (mldefender::firewall::observability::g_logger) { \
        mldefender::firewall::observability::g_logger->log( \
            mldefender::firewall::observability::ObservabilityLogger::Level::LOG_INFO, msg, ##__VA_ARGS__); \
    }

#define FIREWALL_LOG_BATCH(msg, ...) \
    if (mldefender::firewall::observability::g_logger) { \
        mldefender::firewall::observability::g_logger->log( \
            mldefender::firewall::observability::ObservabilityLogger::Level::LOG_BATCH, msg, ##__VA_ARGS__); \
    }

#define FIREWALL_LOG_IPSET(msg, ...) \
    if (mldefender::firewall::observability::g_logger) { \
        mldefender::firewall::observability::g_logger->log( \
            mldefender::firewall::observability::ObservabilityLogger::Level::LOG_IPSET, msg, ##__VA_ARGS__); \
    }

#define FIREWALL_LOG_WARN(msg, ...) \
    if (mldefender::firewall::observability::g_logger) { \
        mldefender::firewall::observability::g_logger->log( \
            mldefender::firewall::observability::ObservabilityLogger::Level::LOG_WARN, msg, ##__VA_ARGS__); \
    }

#define FIREWALL_LOG_ERROR(msg, ...) \
    if (mldefender::firewall::observability::g_logger) { \
        mldefender::firewall::observability::g_logger->log( \
            mldefender::firewall::observability::ObservabilityLogger::Level::LOG_ERROR, msg, ##__VA_ARGS__); \
    }

#define FIREWALL_LOG_CRASH(msg, ...) \
    if (mldefender::firewall::observability::g_logger) { \
        mldefender::firewall::observability::g_logger->log( \
            mldefender::firewall::observability::ObservabilityLogger::Level::LOG_CRASH, msg, ##__VA_ARGS__); \
    }

#endif // FIREWALL_OBSERVABILITY_LOGGER_HPP