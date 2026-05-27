// crash_diagnostics.hpp
// Day 50 - Crash Diagnosis and State Dumps
// Signal handlers + backtrace + atomic counters

#ifndef CRASH_DIAGNOSTICS_HPP
#define CRASH_DIAGNOSTICS_HPP

#include <atomic>
#include <csignal>
#include <cstring>
#include <execinfo.h>
#include <chrono>
#include "firewall_observability_logger.hpp"

namespace mldefender {
namespace firewall {
namespace diagnostics {

/**
 * SystemState - Global atomic counters for crash diagnostics
 * Thread-safe counters that survive until crash
 */
struct SystemState {
    std::atomic<uint64_t> events_processed{0};
    std::atomic<uint64_t> batches_flushed{0};
    std::atomic<uint64_t> ipset_successes{0};
    std::atomic<uint64_t> ipset_failures{0};
    std::atomic<uint64_t> zmq_recv_count{0};
    std::atomic<uint64_t> zmq_recv_bytes{0};  // Total bytes received via ZMQ
    std::atomic<uint64_t> protobuf_parse_errors{0};
    std::atomic<uint64_t> crypto_errors{0};
    std::atomic<uint64_t> decompression_errors{0};
    std::atomic<uint64_t> detections_received{0};
    std::atomic<uint64_t> ips_blocked{0};
    std::atomic<uint64_t> ips_deduplicated{0};
    std::atomic<uint64_t> flush_errors{0};
    std::atomic<uint64_t> events_dropped{0};  // Events filtered/rejected
    std::atomic<bool> is_running{false};

    // Max queue depth tracking
    std::atomic<size_t> max_queue_depth{0};

    // Latency tracking (microseconds)
    std::atomic<uint64_t> total_flush_latency_us{0};
    std::atomic<uint64_t> flush_count_for_avg{0};
};

// Global system state (defined in main.cpp)
extern std::unique_ptr<SystemState> g_system_state;

/**
 * dump_state - Dump current system state to logs
 * Called on crashes or periodic checkpoints
 */
inline void dump_state(const char* context) {
    if (!g_system_state) return;

    FIREWALL_LOG_CRASH("System State Dump",
        "context", context,
        "events_processed", g_system_state->events_processed.load(),
        "events_dropped", g_system_state->events_dropped.load(),
        "batches_flushed", g_system_state->batches_flushed.load(),
        "ipset_successes", g_system_state->ipset_successes.load(),
        "ipset_failures", g_system_state->ipset_failures.load(),
        "zmq_recv_count", g_system_state->zmq_recv_count.load(),
        "zmq_recv_bytes", g_system_state->zmq_recv_bytes.load(),
        "protobuf_parse_errors", g_system_state->protobuf_parse_errors.load(),
        "crypto_errors", g_system_state->crypto_errors.load(),
        "decompression_errors", g_system_state->decompression_errors.load(),
        "detections_received", g_system_state->detections_received.load(),
        "ips_blocked", g_system_state->ips_blocked.load(),
        "ips_deduplicated", g_system_state->ips_deduplicated.load(),
        "flush_errors", g_system_state->flush_errors.load(),
        "max_queue_depth", g_system_state->max_queue_depth.load(),
        "is_running", g_system_state->is_running.load());
}

/**
 * print_backtrace - Print stack backtrace to logs
 * Uses execinfo.h for backtrace capture
 */
inline void print_backtrace(int max_frames = 64) {
    void* buffer[64];
    int nptrs = backtrace(buffer, max_frames);

    FIREWALL_LOG_CRASH("Backtrace", "frames", nptrs);

    char** symbols = backtrace_symbols(buffer, nptrs);
    if (symbols == nullptr) {
        FIREWALL_LOG_CRASH("Failed to get backtrace symbols");
        return;
    }

    for (int i = 0; i < nptrs; i++) {
        FIREWALL_LOG_CRASH("Frame", "index", i, "symbol", symbols[i]);
    }

    free(symbols);
}

/**
 * crash_handler - Signal handler for crashes
 * Dumps state + backtrace before terminating
 */
inline void crash_handler(int signum) {
    FIREWALL_LOG_CRASH("=== CRASH DETECTED ===", "signal", signum);

    const char* signal_name = "UNKNOWN";
    switch (signum) {
        case SIGSEGV: signal_name = "SIGSEGV (Segmentation fault)"; break;
        case SIGABRT: signal_name = "SIGABRT (Abort)"; break;
        case SIGFPE:  signal_name = "SIGFPE (Floating point exception)"; break;
        case SIGILL:  signal_name = "SIGILL (Illegal instruction)"; break;
        case SIGBUS:  signal_name = "SIGBUS (Bus error)"; break;
    }

    FIREWALL_LOG_CRASH("Signal name", "signal", signal_name);

    print_backtrace();
    dump_state("crash_handler");

    // Reset to default handler and re-raise
    signal(signum, SIG_DFL);
    raise(signum);
}

/**
 * install_crash_handlers - Install signal handlers for common crashes
 * Call this early in main()
 */
inline void install_crash_handlers() {
    signal(SIGSEGV, crash_handler);
    signal(SIGABRT, crash_handler);
    signal(SIGFPE, crash_handler);
    signal(SIGILL, crash_handler);
    signal(SIGBUS, crash_handler);

    FIREWALL_LOG_INFO("Crash handlers installed",
        "signals", "SIGSEGV, SIGABRT, SIGFPE, SIGILL, SIGBUS");
}

/**
 * OperationTracker - RAII timer for operations
 * Automatically logs operation duration on destruction
 */
class OperationTracker {
public:
    explicit OperationTracker(const char* operation_name)
        : operation_(operation_name)
        , start_(std::chrono::steady_clock::now()) {
        FIREWALL_LOG_DEBUG("Operation started", "name", operation_);
    }

    ~OperationTracker() {
        auto end = std::chrono::steady_clock::now();
        auto duration_us = std::chrono::duration_cast<std::chrono::microseconds>(
            end - start_).count();

        FIREWALL_LOG_DEBUG("Operation completed",
            "name", operation_,
            "duration_us", duration_us);
    }

private:
    const char* operation_;
    std::chrono::steady_clock::time_point start_;
};

} // namespace diagnostics
} // namespace firewall
} // namespace mldefender

// Convenience macros
#define TRACK_OPERATION(name) \
    mldefender::firewall::diagnostics::OperationTracker __tracker_##__LINE__(name)

#define INCREMENT_COUNTER(counter) \
    if (mldefender::firewall::diagnostics::g_system_state) { \
        mldefender::firewall::diagnostics::g_system_state->counter.fetch_add(1); \
    }

#define ADD_COUNTER(counter, value) \
    if (mldefender::firewall::diagnostics::g_system_state) { \
        mldefender::firewall::diagnostics::g_system_state->counter.fetch_add(value); \
    }

#define DUMP_STATE_ON_ERROR(context) \
    mldefender::firewall::diagnostics::dump_state(context)

#endif // CRASH_DIAGNOSTICS_HPP