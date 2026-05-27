// sniffer/include/ransomware_feature_extractor.hpp
// Ransomware-specific feature extraction
// Uses TimeWindowAggregator to extract 20 ransomware detection features

#pragma once

#include "time_window_aggregator.hpp"
#include "flow_tracker.hpp"
#include "dns_analyzer.hpp"
#include "ip_whitelist.hpp"
#include <memory>

namespace sniffer {

/**
 * RansomwareFeatureExtractor: Specialized feature extractor for ransomware detection
 *
 * Extracts 20 ransomware-specific features organized in phases:
 * - Phase 1A (3 critical): DNS entropy, new external IPs, SMB diversity
 * - Phase 1B (7 high priority): DNS rates, internal connections, ratios
 * - Phase 1C (10 medium priority): TLS, RDP, port scanning, etc.
 *
 * Architecture:
 * - Uses TimeWindowAggregator internally for time-based feature aggregation
 * - References FlowTracker, DNSAnalyzer, IPWhitelist (owned by sniffer)
 * - Thread-safe (delegates to thread-safe components)
 *
 * Separation from FeatureExtractor (83 features):
 * - FeatureExtractor: General attack detection (Level 1 RF model)
 * - RansomwareFeatureExtractor: Ransomware-specific (Level 2 model)
 * - Different features, different models, different purposes
 *
 * Usage:
 *   FlowTracker flow_tracker;
 *   DNSAnalyzer dns_analyzer;
 *   IPWhitelist ip_whitelist;
 *
 *   RansomwareFeatureExtractor extractor(
 *       flow_tracker, dns_analyzer, ip_whitelist);
 *
 *   auto features = extractor.extract_features_phase1a();
 *   // features.dns_query_entropy, features.new_external_ips_30s, etc.
 */
class RansomwareFeatureExtractor {
public:
    /**
     * Constructor
     * @param flow_tracker Reference to flow tracker (owned by sniffer)
     * @param dns_analyzer Reference to DNS analyzer (owned by sniffer)
     * @param ip_whitelist Reference to IP whitelist (owned by sniffer)
     * @param max_events Maximum events in time window ring buffer
     */
    explicit RansomwareFeatureExtractor(
        FlowTracker& flow_tracker,
        DNSAnalyzer& dns_analyzer,
        IPWhitelist& ip_whitelist,
        size_t max_events = 10000);

    // Destructor
    ~RansomwareFeatureExtractor() = default;

    // Disable copy (references cannot be copied safely)
    RansomwareFeatureExtractor(const RansomwareFeatureExtractor&) = delete;
    RansomwareFeatureExtractor& operator=(const RansomwareFeatureExtractor&) = delete;

    // Allow move
    RansomwareFeatureExtractor(RansomwareFeatureExtractor&&) = default;
    RansomwareFeatureExtractor& operator=(RansomwareFeatureExtractor&&) = default;

    // ========== EVENT TRACKING ==========

    /**
     * Add network event for time-windowed analysis
     * Call this for each packet/flow to enable temporal feature extraction
     *
     * @param event Event to track
     */
    void add_event(const TimeWindowEvent& event);

    /**
     * Cleanup old events (call periodically, e.g., every minute)
     * @param retention_ns Retention time in nanoseconds (default: 10 minutes)
     * @return Number of events removed
     */
    size_t cleanup_old_events(uint64_t retention_ns = 600'000'000'000ULL);

    // ========== PHASE 1A: Critical Features (3) ==========

    /**
     * Extract Phase 1A ransomware features (3 critical features)
     *
     * Features extracted:
     * 1. dns_query_entropy - Shannon entropy of DNS queries (DGA detection)
     * 2. new_external_ips_30s - New external IPs in 30s window (C&C detection)
     * 3. smb_connection_diversity - Unique SMB destinations (lateral movement)
     *
     * Expected behavior:
     * - Benign traffic: entropy ~3.0, new_ips ~2, smb_diversity ~0-1
     * - Ransomware: entropy >6.0, new_ips >10, smb_diversity >5
     *
     * @param window_start_ns Optional window start (default: 30s ago)
     * @param window_end_ns Optional window end (default: now)
     * @return RansomwareWindowFeatures with Phase 1A populated
     */
    RansomwareWindowFeatures extract_features_phase1a(
        uint64_t window_start_ns = 0,
        uint64_t window_end_ns = 0);

    // ========== FUTURE PHASES ==========

    /**
     * Extract Phase 1B features (7 high priority)
     * To be implemented after Phase 1A validation
     */
    RansomwareWindowFeatures extract_features_phase1b(
        uint64_t window_start_ns = 0,
        uint64_t window_end_ns = 0);

    /**
     * Extract all 20 ransomware features (complete)
     * To be implemented after Phase 1A + 1B validation
     */
    RansomwareWindowFeatures extract_features_complete(
        uint64_t window_start_ns = 0,
        uint64_t window_end_ns = 0);

    // ========== INDIVIDUAL FEATURE EXTRACTORS ==========

    /**
     * Extract DNS query entropy (Feature 1)
     * High entropy (>6.0) indicates DGA (Domain Generation Algorithm)
     * @return Entropy value (0.0 to 8.0)
     */
    float extract_dns_query_entropy() const;

    /**
     * Extract new external IPs in 30s window (Feature 2)
     * High count (>10) indicates C&C contact attempts
     * @param window_start_ns Window start (default: 30s ago)
     * @param window_end_ns Window end (default: now)
     * @return Count of new external IPs
     */
    int32_t extract_new_external_ips_30s(
        uint64_t window_start_ns = 0,
        uint64_t window_end_ns = 0) const;

    /**
     * Extract SMB connection diversity (Feature 7)
     * High count (>5) indicates lateral movement
     * @param window_start_ns Window start (default: 60s ago)
     * @param window_end_ns Window end (default: now)
     * @return Count of unique SMB destinations
     */
    int32_t extract_smb_connection_diversity(
        uint64_t window_start_ns = 0,
        uint64_t window_end_ns = 0) const;

    // ========== UTILITY ==========

    /**
     * Get current event count in time window buffer
     */
    size_t get_event_count() const noexcept;

    /**
     * Clear all events (for testing)
     */
    void clear();

    /**
     * Get statistics about time window
     * @param window_start_ns Window start
     * @param window_end_ns Window end
     * @return Window statistics
     */
    WindowStats get_window_stats(
        uint64_t window_start_ns,
        uint64_t window_end_ns) const;

private:
    // Time window aggregator (owned by this class)
    TimeWindowAggregator aggregator_;

    // References to external components (owned by sniffer)
    FlowTracker& flow_tracker_;
    DNSAnalyzer& dns_analyzer_;
    IPWhitelist& ip_whitelist_;
};

} // namespace sniffer