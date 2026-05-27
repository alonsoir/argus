#pragma once
// sniffer/include/fast_detector_config.hpp
// Fast Detector configuration (externalized from ring_consumer.cpp)
// Day 12 - ML Validation Architecture

namespace sniffer {

    struct FastDetectorRansomwareScores {
        double high_threat = 0.95;
        double suspicious = 0.70;
        double alert = 0.75;
    };

    struct FastDetectorRansomwareThresholds {
        int external_ips_30s = 15;
        int smb_diversity = 10;
        double dns_entropy = 2.5;
        double failed_dns_ratio = 0.3;
        double upload_download_ratio = 3.0;
        int burst_connections = 50;
        int unique_destinations_30s = 30;
    };

    struct FastDetectorRansomware {
        FastDetectorRansomwareScores scores;
        FastDetectorRansomwareThresholds activation_thresholds;
    };

    struct FastDetectorLogging {
        bool log_activations = true;
        bool log_features = true;
        bool log_decisions = true;
        int log_frequency_seconds = 60;
    };

    struct FastDetectorPerformance {
        int max_latency_us = 10;
        bool enable_metrics = true;
        bool track_activation_rate = true;
    };

    struct FastDetectorConfig {
        bool enabled = true;
        FastDetectorRansomware ransomware;
        FastDetectorLogging logging;
        FastDetectorPerformance performance;
    };

} // namespace sniffer