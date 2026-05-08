//===----------------------------------------------------------------------===//
// ML Defender - Firewall ACL Agent
// batch_processor.cpp - Detection Batch Processing Implementation (Day 50)
//
// Performance Design:
//   - std::unordered_set for O(1) deduplication
//   - Single mutex (not lock-free yet - premature optimization)
//   - Batch flush via ipset restore (single syscall)
//   - Metrics collection with atomics (no lock contention)
//
// Day 50 Enhancements:
//   - Comprehensive observability logging
//   - Performance tracking with TRACK_OPERATION
//   - Diagnostic counters (INCREMENT_COUNTER, ADD_COUNTER)
//   - State dumps on errors (DUMP_STATE_ON_ERROR)
//   - Batch operation visibility (FIREWALL_LOG_BATCH, FIREWALL_LOG_IPSET)
//
// Via Appia Quality: Measure first, optimize later
// Day 50 Motto: Fiat Lux - Let there be light before optimization
//===----------------------------------------------------------------------===//

#include "firewall/batch_processor.hpp"
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>
#include "firewall_observability_logger.hpp"
#include "crash_diagnostics.hpp"

#include <algorithm>
#include <sstream>

namespace mldefender::firewall {

//===----------------------------------------------------------------------===//
// Constructor / Destructor (Day 50: Enhanced)
//===----------------------------------------------------------------------===//

BatchProcessor::BatchProcessor(
    IPSetWrapper& ipset,
    const BatchProcessorConfig& config
)
    : ipset_(ipset)
    , config_(config)
    , last_flush_(std::chrono::steady_clock::now())
{
    FIREWALL_LOG_INFO("Initializing BatchProcessor",
        "batch_size_threshold", config_.batch_size_threshold,
        "batch_time_threshold_ms", config_.batch_time_threshold.count(),
        "max_pending_ips", config_.max_pending_ips,
        "confidence_threshold", config_.confidence_threshold,
        "blacklist_ipset", config_.blacklist_ipset);

    // Reserve space for expected batch size to minimize rehashing
    pending_ips_.reserve(config_.batch_size_threshold);

    FIREWALL_LOG_INFO("BatchProcessor initialized successfully",
        "reserved_capacity", config_.batch_size_threshold);
}

BatchProcessor::~BatchProcessor() {
    FIREWALL_LOG_INFO("BatchProcessor destructor called");

    // Flush any remaining IPs before destruction
    try {
        size_t remaining = get_pending_count();
        if (remaining > 0) {
            FIREWALL_LOG_WARN("Flushing remaining IPs in destructor",
                "pending_count", remaining);
            flush();
        }

        FIREWALL_LOG_INFO("BatchProcessor final statistics",
            "detections_received", metrics_.detections_received.load(),
            "ips_blocked", metrics_.ips_blocked.load(),
            "batches_flushed", metrics_.batches_flushed.load(),
            "ips_deduplicated", metrics_.ips_deduplicated.load(),
            "flush_errors", metrics_.flush_errors.load());

    } catch (const std::exception& e) {
        FIREWALL_LOG_ERROR("Exception in destructor", "error", e.what());
    } catch (...) {
        FIREWALL_LOG_ERROR("Unknown exception in destructor");
    }

    FIREWALL_LOG_INFO("BatchProcessor destroyed");
}

//===----------------------------------------------------------------------===//
// Core API - Detection Processing (Day 50: Enhanced)
//===----------------------------------------------------------------------===//

void BatchProcessor::add_detection(const protobuf::Detection& detection) {
    TRACK_OPERATION("add_detection");

    // Update metrics (atomic, no lock needed)
    metrics_.detections_received.fetch_add(1, std::memory_order_relaxed);
    INCREMENT_COUNTER(events_processed);

    FIREWALL_LOG_DEBUG("Processing detection",
        "src_ip", detection.src_ip(),
        "confidence", detection.confidence(),
        "type", static_cast<int>(detection.type()));

    // ADR-042: auto-isolate multi-señal (antes de cualquier otra decisión)
    check_auto_isolate(detection);

    // Check if detection should be blocked
    if (!should_block(detection)) {
        FIREWALL_LOG_DEBUG("Detection does not meet blocking criteria",
            "src_ip", detection.src_ip(),
            "confidence", detection.confidence(),
            "threshold", config_.confidence_threshold);
        INCREMENT_COUNTER(events_dropped);
        return;
    }

    // Extract IP from detection
    std::string ip = extract_ip(detection);
    if (ip.empty()) {
        FIREWALL_LOG_WARN("Failed to extract IP from detection");
        INCREMENT_COUNTER(events_dropped);
        return;
    }

    // Add to batch (lock required)
    {
        std::lock_guard<std::mutex> lock(mutex_);

        // Check if IP already in pending set (deduplication)
        auto [iter, inserted] = pending_ips_.insert(ip);

        if (!inserted) {
            // IP was duplicate - update metrics
            metrics_.ips_deduplicated.fetch_add(1, std::memory_order_relaxed);
            INCREMENT_COUNTER(ips_deduplicated);

            FIREWALL_LOG_DEBUG("IP deduplicated",
                "ip", ip,
                "pending_count", pending_ips_.size());
        } else {
            FIREWALL_LOG_BATCH("Added IP to pending batch",
                "ip", ip,
                "confidence", detection.confidence(),
                "current_batch_size", pending_ips_.size(),
                "threshold", config_.batch_size_threshold);
        }

        // Update queue depth metrics
        size_t current_size = pending_ips_.size();
        metrics_.pending_ips_current.store(current_size, std::memory_order_relaxed);

        // Update max queue depth (global diagnostic counter)
        size_t current_max = metrics_.pending_ips_max.load(std::memory_order_relaxed);
        if (current_size > current_max) {
            metrics_.pending_ips_max.store(current_size, std::memory_order_relaxed);

            // Also update global diagnostic state
            if (diagnostics::g_system_state) {
                diagnostics::g_system_state->max_queue_depth.store(
                    current_size, std::memory_order_relaxed);
            }

            FIREWALL_LOG_DEBUG("New max queue depth",
                "max_depth", current_size);
        }

        // Check for backpressure
        check_backpressure();
    }

    // Check if flush needed (after releasing lock)
    if (should_flush()) {
        FIREWALL_LOG_BATCH("Batch threshold reached, triggering flush",
            "pending_count", get_pending_count());
        flush();
    }
}

void BatchProcessor::add_detections(
    const std::vector<protobuf::Detection>& detections
) {
    TRACK_OPERATION("add_detections_batch");

    FIREWALL_LOG_INFO("Processing detection batch",
        "count", detections.size());

    // Batch processing - minimize lock acquisitions

    // First pass: filter and extract IPs (no lock)
    std::vector<std::string> ips_to_add;
    ips_to_add.reserve(detections.size());

    for (const auto& detection : detections) {
        metrics_.detections_received.fetch_add(1, std::memory_order_relaxed);
        INCREMENT_COUNTER(events_processed);

        if (!should_block(detection)) {
            FIREWALL_LOG_DEBUG("Detection filtered out",
                "src_ip", detection.src_ip(),
                "confidence", detection.confidence());
            INCREMENT_COUNTER(events_dropped);
            continue;
        }

        std::string ip = extract_ip(detection);
        if (!ip.empty()) {
            ips_to_add.push_back(std::move(ip));
        } else {
            FIREWALL_LOG_WARN("Failed to extract IP from detection in batch");
            INCREMENT_COUNTER(events_dropped);
        }
    }

    if (ips_to_add.empty()) {
        FIREWALL_LOG_DEBUG("No IPs to add after filtering",
            "original_count", detections.size());
        return;
    }

    FIREWALL_LOG_BATCH("Filtered detections for batching",
        "original_count", detections.size(),
        "filtered_count", ips_to_add.size());

    // Second pass: add to pending set (single lock)
    {
        std::lock_guard<std::mutex> lock(mutex_);

        size_t dedup_count = 0;
        for (auto& ip : ips_to_add) {
            auto [iter, inserted] = pending_ips_.insert(std::move(ip));
            if (!inserted) {
                ++dedup_count;
            }
        }

        if (dedup_count > 0) {
            metrics_.ips_deduplicated.fetch_add(dedup_count, std::memory_order_relaxed);
            ADD_COUNTER(ips_deduplicated, dedup_count);

            FIREWALL_LOG_DEBUG("Deduplicated IPs in batch",
                "dedup_count", dedup_count,
                "unique_added", ips_to_add.size() - dedup_count);
        }

        // Update metrics
        size_t current_size = pending_ips_.size();
        metrics_.pending_ips_current.store(current_size, std::memory_order_relaxed);

        size_t current_max = metrics_.pending_ips_max.load(std::memory_order_relaxed);
        if (current_size > current_max) {
            metrics_.pending_ips_max.store(current_size, std::memory_order_relaxed);

            if (diagnostics::g_system_state) {
                diagnostics::g_system_state->max_queue_depth.store(
                    current_size, std::memory_order_relaxed);
            }
        }

        FIREWALL_LOG_BATCH("Batch added to pending queue",
            "ips_added", ips_to_add.size() - dedup_count,
            "current_batch_size", current_size,
            "threshold", config_.batch_size_threshold);

        check_backpressure();
    }

    // Check if flush needed
    if (should_flush()) {
        FIREWALL_LOG_BATCH("Batch threshold reached, triggering flush");
        flush();
    }
}

void BatchProcessor::add_ip(const std::string& ip, float confidence) {
    TRACK_OPERATION("add_ip_direct");

    FIREWALL_LOG_DEBUG("Direct IP addition",
        "ip", ip,
        "confidence", confidence,
        "threshold", config_.confidence_threshold);

    // Simple bypass for raw IP addition
    if (confidence < config_.confidence_threshold && !config_.block_low_confidence) {
        FIREWALL_LOG_DEBUG("IP rejected due to low confidence",
            "ip", ip,
            "confidence", confidence);
        INCREMENT_COUNTER(events_dropped);
        return;
    }

    metrics_.detections_received.fetch_add(1, std::memory_order_relaxed);
    INCREMENT_COUNTER(events_processed);

    {
        std::lock_guard<std::mutex> lock(mutex_);

        auto [iter, inserted] = pending_ips_.insert(ip);
        if (!inserted) {
            metrics_.ips_deduplicated.fetch_add(1, std::memory_order_relaxed);
            INCREMENT_COUNTER(ips_deduplicated);

            FIREWALL_LOG_DEBUG("IP deduplicated (direct add)",
                "ip", ip);
        } else {
            FIREWALL_LOG_BATCH("Added IP directly to batch",
                "ip", ip,
                "confidence", confidence,
                "current_batch_size", pending_ips_.size());
        }

        size_t current_size = pending_ips_.size();
        metrics_.pending_ips_current.store(current_size, std::memory_order_relaxed);

        size_t current_max = metrics_.pending_ips_max.load(std::memory_order_relaxed);
        if (current_size > current_max) {
            metrics_.pending_ips_max.store(current_size, std::memory_order_relaxed);

            if (diagnostics::g_system_state) {
                diagnostics::g_system_state->max_queue_depth.store(
                    current_size, std::memory_order_relaxed);
            }
        }

        check_backpressure();
    }

    if (should_flush()) {
        FIREWALL_LOG_BATCH("Batch threshold reached after direct add");
        flush();
    }
}

//===----------------------------------------------------------------------===//
// Flushing Logic (Day 50: Comprehensive Logging)
//===----------------------------------------------------------------------===//

size_t BatchProcessor::flush() {
    TRACK_OPERATION("batch_flush");

    std::lock_guard<std::mutex> lock(mutex_);
    return flush_internal();
}

size_t BatchProcessor::flush_internal() {
    // Assumes lock is already held

    if (pending_ips_.empty()) {
        FIREWALL_LOG_DEBUG("Flush called on empty batch");
        return 0;
    }

    auto flush_start = std::chrono::steady_clock::now();
    size_t batch_size = pending_ips_.size();

    FIREWALL_LOG_BATCH("Starting batch flush",
        "batch_size", batch_size,
        "ipset_name", config_.blacklist_ipset);

    // Convert to vector of IPSetEntry
    std::vector<IPSetEntry> entries;
    entries.reserve(batch_size);

    for (const auto& ip : pending_ips_) {
        entries.push_back(IPSetEntry{ip});
    }

    FIREWALL_LOG_DEBUG("Converted pending IPs to IPSetEntry vector",
        "entry_count", entries.size());

    // Flush to ipset - IPSetResult<void> has operator bool()
    bool flush_success = false;
    std::string error_msg;

    try {
        FIREWALL_LOG_IPSET("Executing ipset batch add",
            "ipset_name", config_.blacklist_ipset,
            "ip_count", batch_size);

        IPSetResult<void> result;
        {
            TRACK_OPERATION("ipset_add_batch");
            result = ipset_.add_batch(config_.blacklist_ipset, entries);
        }

        // Check success using operator bool()
        flush_success = static_cast<bool>(result);

        // Extract error message if failed
        if (!flush_success) {
            const auto& err = result.get_error();
            error_msg = err.message;
        }

    } catch (const std::exception& e) {
        FIREWALL_LOG_ERROR("Exception during ipset batch add",
            "error", e.what(),
            "ipset_name", config_.blacklist_ipset,
            "ip_count", batch_size);
        DUMP_STATE_ON_ERROR("ipset_batch_add_exception");

        flush_success = false;
        error_msg = e.what();
    }

    auto flush_end = std::chrono::steady_clock::now();
    auto flush_duration = std::chrono::duration_cast<std::chrono::microseconds>(
        flush_end - flush_start
    );

    // Update metrics based on flush_success
    if (flush_success) {
        metrics_.ips_blocked.fetch_add(batch_size, std::memory_order_relaxed);
        metrics_.batches_flushed.fetch_add(1, std::memory_order_relaxed);
        metrics_.last_batch_size.store(batch_size, std::memory_order_relaxed);
        metrics_.total_batch_size.fetch_add(batch_size, std::memory_order_relaxed);

        INCREMENT_COUNTER(batches_flushed);
        INCREMENT_COUNTER(ipset_successes);
        ADD_COUNTER(ips_blocked, batch_size);

        FIREWALL_LOG_BATCH("Batch flush successful",
            "batch_size", batch_size,
            "duration_us", flush_duration.count(),
            "ips_per_second", static_cast<double>(batch_size * 1000000) / flush_duration.count(),
            "total_ips_blocked", metrics_.ips_blocked.load(),
            "total_batches", metrics_.batches_flushed.load());

        // Clear pending set
        pending_ips_.clear();

        // Update last flush time
        last_flush_ = flush_end;

    } else {
        // Flush failed - keep IPs in pending set
        metrics_.flush_errors.fetch_add(1, std::memory_order_relaxed);
        metrics_.ipset_errors.fetch_add(1, std::memory_order_relaxed);

        INCREMENT_COUNTER(ipset_failures);
        INCREMENT_COUNTER(flush_errors);

        FIREWALL_LOG_ERROR("Batch flush failed",
            "batch_size", batch_size,
            "ipset_name", config_.blacklist_ipset,
            "duration_us", flush_duration.count(),
            "error", error_msg,
            "total_errors", metrics_.flush_errors.load());

        DUMP_STATE_ON_ERROR("batch_flush_failed");

        // IPs remain in pending_ips_ for retry
    }

    // Update latency metrics
    metrics_.last_flush_latency_us.store(
        flush_duration.count(),
        std::memory_order_relaxed
    );
    metrics_.total_flush_time_us.fetch_add(
        flush_duration.count(),
        std::memory_order_relaxed
    );

    // Update global diagnostic latency tracking
    if (diagnostics::g_system_state) {
        diagnostics::g_system_state->total_flush_latency_us.fetch_add(
            flush_duration.count(), std::memory_order_relaxed);
        diagnostics::g_system_state->flush_count_for_avg.fetch_add(
            1, std::memory_order_relaxed);
    }

    // Update current queue size
    metrics_.pending_ips_current.store(
        pending_ips_.size(),
        std::memory_order_relaxed
    );

    // Calculate average latency
    uint64_t total_batches = metrics_.batches_flushed.load();
    if (total_batches > 0) {
        uint64_t avg_latency = metrics_.total_flush_time_us.load() / total_batches;

        FIREWALL_LOG_DEBUG("Flush performance metrics",
            "avg_latency_us", avg_latency,
            "last_latency_us", flush_duration.count(),
            "total_batches", total_batches);
    }

    // Trigger callback if set
    if (flush_callback_ && flush_success) {
        try {
            flush_callback_(batch_size);
        } catch (const std::exception& e) {
            FIREWALL_LOG_WARN("Flush callback exception",
                "error", e.what());
        } catch (...) {
            FIREWALL_LOG_WARN("Unknown exception in flush callback");
        }
    }

    return flush_success ? batch_size : 0;
}

bool BatchProcessor::should_flush() const {
    std::lock_guard<std::mutex> lock(mutex_);

    // Check size threshold
    if (pending_ips_.size() >= config_.batch_size_threshold) {
        FIREWALL_LOG_DEBUG("Flush triggered by size threshold",
            "pending_count", pending_ips_.size(),
            "threshold", config_.batch_size_threshold);
        return true;
    }

    // Check time threshold
    auto now = std::chrono::steady_clock::now();
    auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(
        now - last_flush_
    );

    if (elapsed >= config_.batch_time_threshold && !pending_ips_.empty()) {
        FIREWALL_LOG_DEBUG("Flush triggered by time threshold",
            "elapsed_ms", elapsed.count(),
            "threshold_ms", config_.batch_time_threshold.count(),
            "pending_count", pending_ips_.size());
        return true;
    }

    return false;
}

//===----------------------------------------------------------------------===//
// Configuration Updates (Day 50: Enhanced)
//===----------------------------------------------------------------------===//

void BatchProcessor::set_batch_size_threshold(size_t threshold) {
    std::lock_guard<std::mutex> lock(mutex_);

    FIREWALL_LOG_INFO("Updating batch size threshold",
        "old_threshold", config_.batch_size_threshold,
        "new_threshold", threshold);

    config_.batch_size_threshold = threshold;
}

void BatchProcessor::set_batch_time_threshold(std::chrono::milliseconds threshold) {
    std::lock_guard<std::mutex> lock(mutex_);

    FIREWALL_LOG_INFO("Updating batch time threshold",
        "old_threshold_ms", config_.batch_time_threshold.count(),
        "new_threshold_ms", threshold.count());

    config_.batch_time_threshold = threshold;
}

void BatchProcessor::set_confidence_threshold(float threshold) {
    std::lock_guard<std::mutex> lock(mutex_);

    FIREWALL_LOG_INFO("Updating confidence threshold",
        "old_threshold", config_.confidence_threshold,
        "new_threshold", threshold);

    config_.confidence_threshold = threshold;
}

//===----------------------------------------------------------------------===//
// Metrics and Monitoring (Day 50: Enhanced)
//===----------------------------------------------------------------------===//

size_t BatchProcessor::get_pending_count() const {
    std::lock_guard<std::mutex> lock(mutex_);
    return pending_ips_.size();
}

std::chrono::milliseconds BatchProcessor::get_time_since_last_flush() const {
    std::lock_guard<std::mutex> lock(mutex_);
    auto now = std::chrono::steady_clock::now();
    return std::chrono::duration_cast<std::chrono::milliseconds>(now - last_flush_);
}

bool BatchProcessor::is_queue_backing_up() const {
    size_t current = metrics_.pending_ips_current.load(std::memory_order_relaxed);
    bool backing_up = current > (config_.max_pending_ips * 80 / 100);  // >80% of max

    if (backing_up) {
        FIREWALL_LOG_WARN("Queue backing up detected",
            "current_size", current,
            "max_size", config_.max_pending_ips,
            "threshold_80pct", config_.max_pending_ips * 80 / 100);
    }

    return backing_up;
}

//===----------------------------------------------------------------------===//
// Callbacks (Day 50: Enhanced)
//===----------------------------------------------------------------------===//

void BatchProcessor::set_flush_callback(std::function<void(size_t)> callback) {
    std::lock_guard<std::mutex> lock(mutex_);

    FIREWALL_LOG_INFO("Flush callback registered");
    flush_callback_ = std::move(callback);
}

void BatchProcessor::set_backpressure_callback(std::function<void(size_t)> callback) {
    std::lock_guard<std::mutex> lock(mutex_);

    FIREWALL_LOG_INFO("Backpressure callback registered");
    backpressure_callback_ = std::move(callback);
}

//===----------------------------------------------------------------------===//
// Internal Helper Methods (Day 50: Enhanced)
//===----------------------------------------------------------------------===//

// ── should_auto_isolate — lógica de decisión pura (testeable sin fork) ──
bool BatchProcessor::should_auto_isolate(const protobuf::Detection& detection) const {
    if (!irp_config_.auto_isolate) return false;
    std::string event_type;
    switch (detection.type()) {
        case protobuf::DetectionType::DETECTION_RANSOMWARE:
            event_type = "ransomware"; break;
        case protobuf::DetectionType::DETECTION_INTERNAL_THREAT:
            event_type = "lateral_movement"; break;
        case protobuf::DetectionType::DETECTION_SUSPICIOUS_TRAFFIC:
            event_type = "c2_beacon"; break;
        default:
            return false;
    }
    // Comparación con tolerancia: float confidence vs double threshold
    // static_cast<double>(0.95f) = 0.9499... por precisión IEEE 754
    if (static_cast<double>(detection.confidence()) < irp_config_.threat_score_threshold - 1e-6)
        return false;
    const auto& types = irp_config_.auto_isolate_event_types;
    return std::find(types.begin(), types.end(), event_type) != types.end();
}

// ── check_auto_isolate — ADR-042 IRP (DAY 143) ───────────────────────────
// fork()+execv(): el firewall NO puede morir — operación atómica
void BatchProcessor::check_auto_isolate(const protobuf::Detection& detection) {
    if (!should_auto_isolate(detection)) return;
    FIREWALL_LOG_WARN("IRP TRIGGER: auto-isolate activado",
        "src_ip",     detection.src_ip(),
        "score",      detection.confidence(),
        "type",       static_cast<int>(detection.type()),
        "interface",  irp_config_.isolate_interface);

    // ── fork()+execv(): el firewall sigue vivo ────────────────────────────
    pid_t pid = fork();
    if (pid < 0) {
        FIREWALL_LOG_ERROR("IRP fork() failed", "errno", errno);
        return;
    }
    if (pid == 0) {
        // Proceso hijo — execv argus-network-isolate
        const std::string& bin  = irp_config_.isolate_binary_path;
        const std::string& cfg  = irp_config_.isolate_config_path;
        const std::string& iface = irp_config_.isolate_interface;
        char* argv[] = {
            const_cast<char*>(bin.c_str()),
            const_cast<char*>("isolate"),
            const_cast<char*>("--interface"),
            const_cast<char*>(iface.c_str()),
            const_cast<char*>("--config"),
            const_cast<char*>(cfg.c_str()),
            nullptr
        };
        execv(bin.c_str(), argv);
        // execv solo retorna si falla
        _exit(127);
    }
    // Proceso padre — no wait(), no bloqueamos el pipeline
    // El hijo es recogido por el init process (SIGCHLD ignorado por defecto)
    FIREWALL_LOG_INFO("IRP: argus-network-isolate lanzado",
        "pid",       static_cast<int>(pid),
        "interface", irp_config_.isolate_interface);
}


bool BatchProcessor::should_block(const protobuf::Detection& detection) const {
    // Check detection type
    if (detection.type() == protobuf::DetectionType::DETECTION_UNKNOWN) {
        FIREWALL_LOG_DEBUG("Detection type is UNKNOWN, skipping",
            "src_ip", detection.src_ip());
        return false;
    }

    // Extract confidence score
    float confidence = detection.confidence();

    // Check confidence threshold
    if (confidence < config_.confidence_threshold) {
        if (!config_.block_low_confidence) {
            FIREWALL_LOG_DEBUG("Low confidence detection rejected",
                "src_ip", detection.src_ip(),
                "confidence", confidence,
                "threshold", config_.confidence_threshold);
            return false;
        } else {
            FIREWALL_LOG_DEBUG("Low confidence detection accepted (block_low_confidence=true)",
                "src_ip", detection.src_ip(),
                "confidence", confidence);
        }
    }

    return true;
}

std::string BatchProcessor::extract_ip(const protobuf::Detection& detection) const {
    // Extract source IP from detection
    if (!detection.src_ip().empty()) {
        return detection.src_ip();
    }

    FIREWALL_LOG_WARN("Detection missing src_ip field");
    return "";
}

void BatchProcessor::check_backpressure() {
    // Assumes lock is already held

    if (backpressure_callback_ && is_queue_backing_up()) {
        size_t queue_size = pending_ips_.size();

        FIREWALL_LOG_WARN("Backpressure detected, triggering callback",
            "queue_size", queue_size,
            "max_size", config_.max_pending_ips);

        try {
            backpressure_callback_(queue_size);
        } catch (const std::exception& e) {
            FIREWALL_LOG_ERROR("Backpressure callback exception",
                "error", e.what());
        } catch (...) {
            FIREWALL_LOG_ERROR("Unknown exception in backpressure callback");
        }
    }
}

} // namespace mldefender::firewall