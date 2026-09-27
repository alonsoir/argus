//===----------------------------------------------------------------------===//
// ML Defender - Firewall ACL Agent
#include "network_security.pb.h"  // Protobuf generated header
// batch_processor.hpp - Detection Batch Processing and IP Accumulation
//
// Design Philosophy:
//   - Accumulate detections in memory (std::unordered_set)
//   - Automatic deduplication within batch
//   - Flush based on time (100ms) OR size (1000 IPs)
//   - Thread-safe with single mutex
//   - Zero-copy when possible
//
// Performance Model:
//   Attack Rate    Batch Size    Flush Freq    Latency    Throughput
//   100 IPs/sec    100 IPs       100ms         100ms      1K IPs/sec
//   1K IPs/sec     1000 IPs      100ms         100ms      10K IPs/sec
//   10K IPs/sec    1000 IPs      10ms          10ms       100K IPs/sec
//   100K IPs/sec   1000 IPs      1ms           1ms        1M IPs/sec
//
// Via Appia Quality: Simple accumulator, let kernel do the heavy lifting
//===----------------------------------------------------------------------===//

#pragma once
#include "firewall/config_loader.hpp"
// alert_client.hpp movido al .cpp (DEBT-FIREWALL-HTTPLIB-ODR-001 — pimpl)
#include <nlohmann/json.hpp>
#include <memory>

#include "firewall/ipset_wrapper.hpp"
#include "network_security.pb.h"

#include <string>
#include <unordered_set>
#include <unordered_map>
#include <vector>
#include <chrono>
#include <mutex>
#include <atomic>
#include <functional>

#include <optional>  // DAY277-NEVER-PERMANENT

namespace mldefender::firewall {

//===----------------------------------------------------------------------===//
// Recidivism escalation (RECIDIVISM-D276)
//===----------------------------------------------------------------------===//

/// Estado de reincidencia por IP
struct StrikeState {
    uint32_t strikes{0};
    std::chrono::steady_clock::time_point last_seen;
};

/// Configuracion de escalado de castigo por reincidencia. Vive en firewall,
/// no en los detectores: firewall es la unica fuente de verdad del ipset.
struct RecidivismConfig {
    bool enabled{true};
    /// Duracion en segundos por nivel de reincidencia (indice 0 = 1a vez)
    std::vector<uint32_t> strike_durations_sec{60, 300, 3600, 86400, 604800};
    /// A partir de este numero de reincidencias se aplica max_penalty_sec.
    /// NUNCA bloqueo permanente (DAY277-NEVER-PERMANENT): las IPs de botnets
    /// suelen ser victimas (equipos comprometidos, CGNAT compartido). El drop
    /// permanente es una accion manual del admin, fuera de este camino.
    uint32_t max_penalty_after_strikes{6};
    /// Castigo maximo en segundos. Rango valido [1, kIpsetMaxTimeoutSec].
    uint32_t max_penalty_sec{2073600};  // 24 dias
    /// Si ha pasado mas de esto sin verla, se resetea el contador de esa IP
    std::chrono::seconds quiet_period_reset{std::chrono::hours(72)};
    /// Cota de memoria: IPs distintas trackeadas como maximo
    size_t max_tracked_ips{100000};
    /// Fichero donde se vuelca strike_states_ antes de resetear por overflow.
    /// Si no se puede escribir, NO se resetea (no se pierde evidencia).
    std::string overflow_log_path{"/vagrant/logs/lab/firewall_strike_overflow.log"};
};

//===----------------------------------------------------------------------===//
// Configuration
//===----------------------------------------------------------------------===//

/// Batch processor configuration
struct BatchProcessorConfig {
    // Batching thresholds
    size_t batch_size_threshold{1000};        ///< Flush when batch reaches N IPs
    std::chrono::milliseconds batch_time_threshold{100};  ///< Flush every N ms

    // IPSet names
    std::string blacklist_ipset{"ml_defender_blacklist"};
    std::string whitelist_ipset{"ml_defender_whitelist"};

    // Performance tuning
    size_t max_pending_ips{10000};           ///< Max IPs in queue before backpressure
    bool enable_metrics{true};                ///< Enable performance metrics

    // Filtering
    float confidence_threshold{0.8f};         ///< Minimum confidence to block
    bool block_low_confidence{false};         ///< Block IPs with low confidence
    nlohmann::json alerting_json{{"alerting", {{"enabled", false}}}};  ///< DEBT-ALERTING-EDGE-SOS-001
};

//===----------------------------------------------------------------------===//
// Statistics and Metrics
//===----------------------------------------------------------------------===//

/// Performance metrics for monitoring
struct BatchProcessorMetrics {
    // Throughput metrics
    std::atomic<uint64_t> detections_received{0};
    std::atomic<uint64_t> ips_blocked{0};
    std::atomic<uint64_t> ips_deduplicated{0};
    std::atomic<uint64_t> batches_flushed{0};

    // Queue metrics
    std::atomic<size_t> pending_ips_current{0};
    std::atomic<size_t> pending_ips_max{0};

    // Latency metrics (microseconds)
    std::atomic<uint64_t> last_flush_latency_us{0};
    std::atomic<uint64_t> total_flush_time_us{0};

    // Batch characteristics
    std::atomic<size_t> last_batch_size{0};
    std::atomic<size_t> total_batch_size{0};

    // Error tracking
    std::atomic<uint64_t> flush_errors{0};
    std::atomic<uint64_t> ipset_errors{0};

    /// Reset all metrics
    void reset() {
        detections_received = 0;
        ips_blocked = 0;
        ips_deduplicated = 0;
        batches_flushed = 0;
        pending_ips_current = 0;
        pending_ips_max = 0;
        last_flush_latency_us = 0;
        total_flush_time_us = 0;
        last_batch_size = 0;
        total_batch_size = 0;
        flush_errors = 0;
        ipset_errors = 0;
    }

    /// Get average batch size
    size_t get_average_batch_size() const {
        uint64_t batches = batches_flushed.load();
        if (batches == 0) return 0;
        return total_batch_size.load() / batches;
    }

    /// Get average flush latency (microseconds)
    uint64_t get_average_flush_latency_us() const {
        uint64_t batches = batches_flushed.load();
        if (batches == 0) return 0;
        return total_flush_time_us.load() / batches;
    }

    /// Get deduplication ratio (0.0 to 1.0)
    float get_dedup_ratio() const {
        uint64_t total = detections_received.load();
        if (total == 0) return 0.0f;
        return static_cast<float>(ips_deduplicated.load()) / total;
    }
};

//===----------------------------------------------------------------------===//
// Batch Processor
//===----------------------------------------------------------------------===//

/// High-performance batch processor for IP blocking
///
/// Accumulates malicious IPs from ML detections and flushes them to ipset
/// in batches for optimal performance. Provides automatic deduplication,
/// configurable batching strategy, and comprehensive metrics.
///
/// Thread-safety: All public methods are thread-safe.
///
/// Performance: Designed for 100K+ detections/sec with sub-millisecond latency.
///
class BatchProcessor {
public:
    /// Constructor
    /// @param ipset IPSet wrapper for kernel updates
    /// @param config Batching configuration
    explicit BatchProcessor(
        IPSetWrapper& ipset,
        const BatchProcessorConfig& config = BatchProcessorConfig{}
    );

    /// Destructor - flushes pending IPs
    ~BatchProcessor();

    // Non-copyable, non-movable
    BatchProcessor(const BatchProcessor&) = delete;
    BatchProcessor& operator=(const BatchProcessor&) = delete;
    BatchProcessor(BatchProcessor&&) = delete;
    BatchProcessor& operator=(BatchProcessor&&) = delete;

    //===------------------------------------------------------------------===//
    // Core API
    //===------------------------------------------------------------------===//

    /// Add a detection from ML detector
    /// @param detection Protobuf detection message
    /// @note Thread-safe, non-blocking
    /// @note Automatically flushes if thresholds exceeded
    void add_detection(const protobuf::Detection& detection);

    /// Add multiple detections (batch from ZMQ)
    /// @param detections Vector of detection messages
    /// @note More efficient than calling add_detection() repeatedly
    void add_detections(const std::vector<protobuf::Detection>& detections);

    /// Add raw IP address for blocking
    /// @param ip IP address (IPv4 or IPv6)
    /// @param confidence Detection confidence (0.0 to 1.0)
    /// @note Bypasses protobuf parsing
    void add_ip(const std::string& ip, float confidence = 1.0f);

    /// Force flush all pending IPs to kernel
    /// @return Number of IPs flushed
    /// @note Thread-safe, blocks until flush complete
    size_t flush();

    /// Check if flush is needed (based on thresholds)
    /// @return true if should flush
    bool should_flush() const;

    //===------------------------------------------------------------------===//
    // Configuration
    //===------------------------------------------------------------------===//

    /// Update batch size threshold
    void set_batch_size_threshold(size_t threshold);

    /// Update batch time threshold
    void set_batch_time_threshold(std::chrono::milliseconds threshold);

    /// Update confidence threshold
    void set_confidence_threshold(float threshold);

    /// Get current configuration
    const BatchProcessorConfig& get_config() const { return config_; }
    void set_irp_config(const IrpConfig& irp) { irp_config_ = irp; }
    // Testeable sin fork — lógica de decisión pura (ADR-042)
    bool should_auto_isolate(const protobuf::Detection& detection) const;
    void check_auto_isolate(const protobuf::Detection& detection);

    /// RECIDIVISM-D276 + DAY277-NEVER-PERMANENT: valida y sanea la config
    /// (ningun timeout puede ser 0 = permanente ni superar kIpsetMaxTimeoutSec;
    /// escalera vacia -> escalera por defecto). Loguea cada correccion. Toma mutex_.
    void set_recidivism_config(const RecidivismConfig& cfg);
    /// RECIDIVISM-D276: publico a proposito -- testeable sin IPSetWrapper real ni
    /// kernel, igual que should_auto_isolate. Calcula el timeout a aplicar a
    /// esta IP y actualiza su contador de reincidencia.
    /// DAY277-NEVER-PERMANENT: nullopt = reincidencia deshabilitada (se aplica
    /// el timeout por defecto del set, comportamiento pre-D276). Con valor,
    /// SIEMPRE en [1, max_penalty_sec]. Nunca 0.
    /// Requiere mutex_ tomado (lo llama flush_internal); los tests unitarios
    /// lo llaman sin concurrencia.
    std::optional<uint32_t> compute_penalty_timeout(const std::string& ip);

    //===------------------------------------------------------------------===//
    // Metrics and Monitoring
    //===------------------------------------------------------------------===//

    /// Get current metrics snapshot
    const BatchProcessorMetrics& get_metrics() const { return metrics_; }

    /// Reset metrics to zero
    void reset_metrics() { metrics_.reset(); }

    /// Get current pending IPs count
    size_t get_pending_count() const;

    /// Get time since last flush
    std::chrono::milliseconds get_time_since_last_flush() const;

    /// Check if queue is backing up (>80% of max)
    bool is_queue_backing_up() const;

    //===------------------------------------------------------------------===//
    // Advanced API
    //===------------------------------------------------------------------===//

    /// Set callback for flush events (for monitoring/logging)
    /// @param callback Function called after each flush
    void set_flush_callback(std::function<void(size_t /* ips_flushed */)> callback);

    /// Set callback for backpressure events
    /// @param callback Function called when queue backs up
    void set_backpressure_callback(std::function<void(size_t /* queue_size */)> callback);

private:
    //===------------------------------------------------------------------===//
    // Internal State
    //===------------------------------------------------------------------===//

    IPSetWrapper& ipset_;                    ///< IPSet wrapper
    BatchProcessorConfig config_;            ///< Configuration
    IrpConfig            irp_config_;         ///< ADR-042 auto-isolate config
    RecidivismConfig recidivism_config_;                          ///< RECIDIVISM-D276
    std::unordered_map<std::string, StrikeState> strike_states_;  ///< RECIDIVISM-D276, guardado por mutex_
    BatchProcessorMetrics metrics_;          ///< Performance metrics

    // Pending IPs accumulator
    std::unordered_set<std::string> pending_ips_;  ///< IPs waiting to flush
    /// DAY277-H6: penalty calculada UNA vez por IP pendiente; los reintentos de un
    /// flush fallido la reutilizan (no suman strikes). Se vacia con pending_ips_.
    /// Guardado por mutex_.
    std::unordered_map<std::string, std::optional<uint32_t>> pending_penalty_;
    std::chrono::steady_clock::time_point last_flush_;  ///< Last flush timestamp

    // Thread safety
    mutable std::mutex mutex_;               ///< Protects all mutable state

    // Callbacks
    std::function<void(size_t)> flush_callback_;
    std::function<void(size_t)> backpressure_callback_;

    //===------------------------------------------------------------------===//
    // Internal Methods
    //===------------------------------------------------------------------===//

    /// Internal flush implementation (assumes lock held)
    /// @return Number of IPs flushed
    size_t flush_internal();

    /// Check if detection should be blocked
    /// @param detection Detection message
    /// @return true if should block
    bool should_block(const protobuf::Detection& detection) const;

    /// Extract IP from detection message
    /// @param detection Detection message
    /// @return IP address or empty string if invalid
    std::string extract_ip(const protobuf::Detection& detection) const;

    /// Trigger backpressure callback if needed
    void check_backpressure();

    /// RECIDIVISM-D276: strike_states_ ha superado max_tracked_ips. Vuelca TODO
    /// su contenido a recidivism_config_.overflow_log_path. Solo si el
    /// volcado tiene exito se vacia strike_states_ -- si falla, se deja
    /// crecer en memoria antes que perder evidencia en silencio.
    void dump_and_reset_strike_states();
};

} // namespace mldefender::firewall