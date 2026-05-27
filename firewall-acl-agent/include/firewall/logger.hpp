//===----------------------------------------------------------------------===//
// ML Defender - Firewall ACL Agent
// logger.hpp - Asynchronous Structured Logger + Payload Storage
//
// Purpose: Log every blocked IP with full context for RAG analysis
// Output:  JSON metadata + Protobuf payload (same timestamp)
// Storage: /vagrant/logs/blocked/TIMESTAMP.{json,proto}
//
// Design Philosophy:
//   - Async by design (non-blocking for detection pipeline)
//   - Filesystem as queue (simple, reliable)
//   - Timestamp-based unique naming (no collisions)
//   - Complete payload preservation (forensic analysis)
//
// Via Appia Quality: Built for decades of log analysis
//===----------------------------------------------------------------------===//

#ifndef FIREWALL_LOGGER_HPP
#define FIREWALL_LOGGER_HPP

#include <string>
#include <atomic>
#include <thread>
#include <queue>
#include <mutex>
#include <condition_variable>
#include <chrono>
#include <memory>

#include "network_security.pb.h"  // Unified protobuf

namespace mldefender {
namespace firewall {

//===----------------------------------------------------------------------===//
// Blocked Event - Full context for logging
//===----------------------------------------------------------------------===//

struct BlockedEvent {
    // Temporal context
    uint64_t timestamp_ms;              // Epoch millis (unique ID)
    std::string timestamp_iso;          // ISO 8601 for human readability

    // Network context
    std::string src_ip;
    std::string dst_ip;
    uint16_t src_port;
    uint16_t dst_port;
    std::string protocol;

    // Detection context
    std::string threat_type;            // DDOS_ATTACK, RANSOMWARE, etc.
    double confidence;                  // 0.0 - 1.0
    std::string detector_name;          // RandomForest_DDoS

    // Action context
    std::string action;                 // BLOCKED, ALLOWED, MONITORED
    std::string ipset_name;             // ml_defender_blacklist_test
    int timeout_sec;                    // -1 for permanent

    // Features summary (key metrics)
    uint64_t packets_per_sec;
    uint64_t bytes_per_sec;
    uint64_t flow_duration_ms;

    // Full payload (protobuf serialized)
    std::shared_ptr<protobuf::NetworkSecurityEvent> payload;

    BlockedEvent()
        : timestamp_ms(0), src_port(0), dst_port(0),
          confidence(0.0), timeout_sec(0),
          packets_per_sec(0), bytes_per_sec(0), flow_duration_ms(0) {}
};

    // ============================================================================
    // CSV + HMAC Support (Day 58 - Pioneer Pattern)
    // ============================================================================

    /**
     * @brief CSV log entry with HMAC signature
     *
     * Format: timestamp_ms,src_ip,dst_ip,threat_type,action,confidence,hmac_sig
     * Example: 1739548800000,192.168.1.100,10.0.0.50,DDOS_ATTACK,BLOCK,0.95,a3f5c2d8...
     */
    struct CSVLogEntry {
        uint64_t timestamp_ms;
        std::string src_ip;
        std::string dst_ip;
        std::string threat_type;
        std::string action;
        double confidence;
        std::string hmac_signature;  // 64-char hex
    };
//===----------------------------------------------------------------------===//
// Firewall Logger - Asynchronous Writer
//===----------------------------------------------------------------------===//

class FirewallLogger {
public:
    /**
     * Constructor
     * @param output_dir Directory for logs (e.g., /vagrant/logs/blocked)
     * @param max_queue_size Max events in memory before backpressure (default: 10000)
     */
    explicit FirewallLogger(const std::string& output_dir,
                           size_t max_queue_size = 10000);

    ~FirewallLogger();

    // Prevent copying
    FirewallLogger(const FirewallLogger&) = delete;
    FirewallLogger& operator=(const FirewallLogger&) = delete;

    /**
     * Start async logging thread
     */
    void start();

    /**
     * Stop async logging (flush pending events)
     * @param timeout_ms Max time to wait for flush (0 = infinite)
     */
    void stop(int timeout_ms = 5000);

    /**
     * Log a blocked event (thread-safe, non-blocking)
     * @param event Event to log
     * @return true if queued, false if queue full
     */
    bool log_blocked_event(const BlockedEvent& event);

    /**
     * @brief Append CSV log with HMAC signature (Day 58 - synchronous, simple)
     *
     * Writes to: output_dir/firewall_blocks.csv
     * Format: timestamp,src_ip,dst_ip,threat_type,action,confidence,hmac
     *
     * @param event Event to log
     * @param hmac_key HMAC key (32 bytes) from etcd-server
     * @return true on success
     *
     * Note: This is synchronous (not queued) - for pioneer pattern simplicity.
     *       Can be optimized to async later if needed.
     */
    bool append_csv_log(const BlockedEvent& event,
                       const std::vector<uint8_t>& hmac_key);

    /**
     * Get current queue size (for monitoring)
     */
    size_t queue_size() const {
        return queue_size_.load();
    }

    /**
     * Get total events logged since start
     */
    uint64_t total_logged() const {
        return total_logged_.load();
    }

    /**
     * Get total events dropped (queue full)
     */
    uint64_t total_dropped() const {
        return total_dropped_.load();
    }

private:
    // Configuration
    std::string output_dir_;
    size_t max_queue_size_;

    // Async processing
    std::thread worker_thread_;
    std::atomic<bool> running_{false};

    // Event queue
    std::queue<BlockedEvent> event_queue_;
    std::mutex queue_mutex_;
    std::condition_variable queue_cv_;
    std::atomic<size_t> queue_size_{0};

    // Statistics
    std::atomic<uint64_t> total_logged_{0};
    std::atomic<uint64_t> total_dropped_{0};

    /**
     * Worker thread main loop
     */
    void worker_loop();

    /**
     * Write single event to disk (JSON + Proto)
     * @param event Event to write
     * @return true on success
     */
    bool write_event_to_disk(const BlockedEvent& event);

    /**
     * Generate JSON metadata for event
     * @param event Event to serialize
     * @return JSON string
     */
    std::string generate_json(const BlockedEvent& event);

    /**
     * Write protobuf payload to file
     * @param event Event with payload
     * @param filename Output filename
     * @return true on success
     */
    bool write_payload(const BlockedEvent& event, const std::string& filename);

    /**
     * Get current timestamp in milliseconds
     */
    static uint64_t get_timestamp_ms();

    /**
     * Convert timestamp to ISO 8601 string
     */
    static std::string timestamp_to_iso(uint64_t timestamp_ms);

    /**
     * Ensure output directory exists
     */
    bool ensure_directory_exists(const std::string& path);

    /**
     * @brief Generate CSV line from event (without HMAC)
     * @return CSV line ready for HMAC computation
     */
    std::string generate_csv_line(const BlockedEvent& event);

    /**
     * @brief Compute HMAC-SHA256 for CSV line
     * @param csv_line CSV line without HMAC
     * @param key HMAC key
     * @return HMAC signature as hex string (64 chars)
     */
    std::string compute_hmac_for_csv(const std::string& csv_line,
                                     const std::vector<uint8_t>& key);
};

//===----------------------------------------------------------------------===//
// Helper Functions
//===----------------------------------------------------------------------===//

/**
 * Create BlockedEvent from NetworkSecurityEvent
 * @param proto_event Protobuf event from ml-detector
 * @param action Action taken (BLOCKED, ALLOWED, etc.)
 * @param ipset_name IPSet where IP was added
 * @param timeout_sec Timeout for block (-1 = permanent)
 * @return BlockedEvent ready for logging
 */
BlockedEvent create_blocked_event_from_proto(
    const protobuf::NetworkSecurityEvent& proto_event,
    const std::string& action,
    const std::string& ipset_name,
    int timeout_sec
);

} // namespace firewall
} // namespace ml_defender

#endif // FIREWALL_LOGGER_HPP