// Unit Test Example for ML Defender Detectors
// Compile: g++ -std=c++20 -O3 test_detectors.cpp ddos_detector.cpp traffic_detector.cpp internal_detector.cpp -o test_detectors

#include "ml_defender/ddos_detector.hpp"
#include "ml_defender/traffic_detector.hpp"
#include "ml_defender/internal_detector.hpp"
#include <iostream>
#include <iomanip>
#include <chrono>
#include <cassert>

using namespace ml_defender;
using namespace std::chrono;

// ANSI colors for output
#define GREEN "\033[32m"
#define RED "\033[31m"
#define YELLOW "\033[33m"
#define BLUE "\033[34m"
#define RESET "\033[0m"

// ============================================================================
// TEST HELPERS
// ============================================================================

template<typename Func>
double benchmark_latency_us(Func&& func, int iterations = 10000) {
    auto start = high_resolution_clock::now();
    for (int i = 0; i < iterations; ++i) {
        func();
    }
    auto end = high_resolution_clock::now();
    auto duration = duration_cast<nanoseconds>(end - start).count();
    return (duration / static_cast<double>(iterations)) / 1000.0; // Convert to μs
}

void print_prediction(const char* detector_name, int class_id,
                      const char* class_name, float probability,
                      const char* confidence) {
    std::cout << BLUE << "[" << detector_name << "]" << RESET
              << " Class: " << class_id << " (" << class_name << ") "
              << "Prob: " << std::fixed << std::setprecision(4) << probability
              << " Confidence: " << confidence << "\n";
}

// ============================================================================
// TEST 1: DDOS DETECTOR
// ============================================================================

void test_ddos_detector() {
    std::cout << "\n" << GREEN << "=== TEST 1: DDoS Detector ===" << RESET << "\n";

    DDoSDetector detector;

    // Test metadata
    assert(detector.num_trees() == 100);
    assert(detector.num_features() == 9);
    std::cout << "✓ Metadata: " << detector.num_trees() << " trees, "
              << detector.num_features() << " features\n";

    // Test case 1: Normal traffic (low anomaly scores)
    DDoSDetector::Features normal_features{
        0.01f,  // syn_ack_ratio
        0.95f,  // packet_symmetry
        0.80f,  // source_ip_dispersion
        0.05f,  // protocol_anomaly_score
        0.40f,  // packet_size_entropy
        0.10f,  // traffic_amplification_factor
        0.90f,  // flow_completion_rate
        0.02f,  // traffic_escalation_rate
        0.10f   // resource_saturation_score
    };

    auto normal_pred = detector.predict(normal_features);
    print_prediction("DDoS", normal_pred.class_id,
                     normal_pred.is_normal() ? "NORMAL" : "DDOS",
                     normal_pred.probability, normal_pred.confidence_level());

    // Test case 2: DDoS attack (high anomaly scores)
    DDoSDetector::Features ddos_features{
        0.85f,  // syn_ack_ratio (SYN flood)
        0.15f,  // packet_symmetry (asymmetric)
        0.95f,  // source_ip_dispersion (many sources)
        0.90f,  // protocol_anomaly_score
        0.85f,  // packet_size_entropy
        0.95f,  // traffic_amplification_factor
        0.20f,  // flow_completion_rate (incomplete flows)
        0.95f,  // traffic_escalation_rate (sudden spike)
        0.90f   // resource_saturation_score
    };

    auto ddos_pred = detector.predict(ddos_features);
    print_prediction("DDoS", ddos_pred.class_id,
                     ddos_pred.is_ddos() ? "DDOS" : "NORMAL",
                     ddos_pred.probability, ddos_pred.confidence_level());

    // Benchmark latency
    auto latency = benchmark_latency_us([&]() {
        detector.predict(normal_features);
    });

    std::cout << "⏱  Latency: " << std::fixed << std::setprecision(2)
              << latency << " μs ";
    if (latency < 100.0) {
        std::cout << GREEN << "✓ (<100μs)" << RESET << "\n";
    } else {
        std::cout << RED << "✗ (>100μs)" << RESET << "\n";
    }
}

// ============================================================================
// TEST 2: TRAFFIC DETECTOR
// ============================================================================

void test_traffic_detector() {
    std::cout << "\n" << GREEN << "=== TEST 2: Traffic Detector ===" << RESET << "\n";

    TrafficDetector detector;

    // Test metadata
    assert(detector.num_trees() == 100);
    assert(detector.num_features() == 10);
    std::cout << "✓ Metadata: " << detector.num_trees() << " trees, "
              << detector.num_features() << " features\n";

    // Test case 1: Internet traffic (high entropy, diverse ports)
    TrafficDetector::Features internet_features{
        0.70f,  // packet_rate
        0.60f,  // connection_rate
        0.50f,  // tcp_udp_ratio
        0.55f,  // avg_packet_size
        0.85f,  // port_entropy (many ports)
        0.40f,  // flow_duration_std
        0.90f,  // src_ip_entropy (diverse sources)
        0.20f,  // dst_ip_concentration (spread destinations)
        0.75f,  // protocol_variety
        0.60f   // temporal_consistency
    };

    auto internet_pred = detector.predict(internet_features);
    print_prediction("Traffic", internet_pred.class_id,
                     internet_pred.is_internet() ? "INTERNET" : "INTERNAL",
                     internet_pred.probability, internet_pred.confidence_level());

    // Test case 2: Internal traffic (low entropy, few ports)
    TrafficDetector::Features internal_features{
        0.30f,  // packet_rate
        0.25f,  // connection_rate
        0.90f,  // tcp_udp_ratio (mostly TCP)
        0.45f,  // avg_packet_size
        0.20f,  // port_entropy (few ports: 22, 3306, 5432)
        0.15f,  // flow_duration_std
        0.15f,  // src_ip_entropy (few internal IPs)
        0.85f,  // dst_ip_concentration (concentrated)
        0.30f,  // protocol_variety
        0.85f   // temporal_consistency (regular patterns)
    };

    auto internal_pred = detector.predict(internal_features);
    print_prediction("Traffic", internal_pred.class_id,
                     internal_pred.is_internal() ? "INTERNAL" : "INTERNET",
                     internal_pred.probability, internal_pred.confidence_level());

    // Benchmark latency
    auto latency = benchmark_latency_us([&]() {
        detector.predict(internet_features);
    });

    std::cout << "⏱  Latency: " << std::fixed << std::setprecision(2)
              << latency << " μs ";
    if (latency < 100.0) {
        std::cout << GREEN << "✓ (<100μs)" << RESET << "\n";
    } else {
        std::cout << RED << "✗ (>100μs)" << RESET << "\n";
    }
}

// ============================================================================
// TEST 3: INTERNAL DETECTOR
// ============================================================================

void test_internal_detector() {
    std::cout << "\n" << GREEN << "=== TEST 3: Internal Detector ===" << RESET << "\n";

    InternalDetector detector;

    // Test metadata
    assert(detector.num_trees() == 100);
    assert(detector.num_features() == 10);
    std::cout << "✓ Metadata: " << detector.num_trees() << " trees, "
              << detector.num_features() << " features\n";

    // Test case 1: Benign internal traffic (database queries)
    InternalDetector::Features benign_features{
        0.40f,  // internal_connection_rate
        0.95f,  // service_port_consistency (port 3306)
        0.90f,  // protocol_regularity
        0.85f,  // packet_size_consistency
        0.20f,  // connection_duration_std (stable)
        0.05f,  // lateral_movement_score (no lateral)
        0.10f,  // service_discovery_patterns
        0.05f,  // data_exfiltration_indicators
        0.10f,  // temporal_anomaly_score
        0.15f   // access_pattern_entropy (regular)
    };

    auto benign_pred = detector.predict(benign_features);
    print_prediction("Internal", benign_pred.class_id,
                     benign_pred.is_benign() ? "BENIGN" : "SUSPICIOUS",
                     benign_pred.probability, benign_pred.confidence_level());

    // Test case 2: Suspicious internal traffic (lateral movement + data exfil)
    InternalDetector::Features suspicious_features{
        0.85f,  // internal_connection_rate (scanning)
        0.30f,  // service_port_consistency (random ports)
        0.25f,  // protocol_regularity (unusual protocols)
        0.40f,  // packet_size_consistency (varied sizes)
        0.75f,  // connection_duration_std (irregular)
        0.90f,  // lateral_movement_score (SMB/RDP scanning)
        0.85f,  // service_discovery_patterns
        0.95f,  // data_exfiltration_indicators (large outbound)
        0.90f,  // temporal_anomaly_score (3am activity)
        0.80f   // access_pattern_entropy (random access)
    };

    auto suspicious_pred = detector.predict(suspicious_features);
    print_prediction("Internal", suspicious_pred.class_id,
                     suspicious_pred.is_suspicious() ? "SUSPICIOUS" : "BENIGN",
                     suspicious_pred.probability, suspicious_pred.confidence_level());

    // Benchmark latency
    auto latency = benchmark_latency_us([&]() {
        detector.predict(benign_features);
    });

    std::cout << "⏱  Latency: " << std::fixed << std::setprecision(2)
              << latency << " μs ";
    if (latency < 100.0) {
        std::cout << GREEN << "✓ (<100μs)" << RESET << "\n";
    } else {
        std::cout << RED << "✗ (>100μs)" << RESET << "\n";
    }
}

// ============================================================================
// TEST 4: BATCH PREDICTION
// ============================================================================

void test_batch_prediction() {
    std::cout << "\n" << GREEN << "=== TEST 4: Batch Prediction ===" << RESET << "\n";

    DDoSDetector detector;

    // Create batch of 1000 samples
    std::vector<DDoSDetector::Features> batch(1000);
    for (auto& features : batch) {
        features = {
            0.5f, 0.5f, 0.5f, 0.5f, 0.5f,
            0.5f, 0.5f, 0.5f, 0.5f
        };
    }

    // Benchmark batch prediction
    auto start = high_resolution_clock::now();
    auto predictions = detector.predict_batch(batch);
    auto end = high_resolution_clock::now();

    auto duration_ms = duration_cast<milliseconds>(end - start).count();
    double throughput = (batch.size() * 1000.0) / duration_ms;

    std::cout << "✓ Batch size: " << batch.size() << " samples\n";
    std::cout << "⏱  Duration: " << duration_ms << " ms\n";
    std::cout << "🚀 Throughput: " << std::fixed << std::setprecision(0)
              << throughput << " predictions/sec ";

    if (throughput > 10000) {
        std::cout << GREEN << "✓ (>10k/sec)" << RESET << "\n";
    } else {
        std::cout << YELLOW << "⚠ (<10k/sec)" << RESET << "\n";
    }
}

// ============================================================================
// MAIN
// ============================================================================

int main() {
    std::cout << BLUE << R"(
╔══════════════════════════════════════════════════════════════╗
║     ML DEFENDER - DETECTOR UNIT TESTS                        ║
║     Via Appia Quality - Fase 0                               ║
╚══════════════════════════════════════════════════════════════╝
)" << RESET << "\n";

    try {
        test_ddos_detector();
        test_traffic_detector();
        test_internal_detector();
        test_batch_prediction();

        std::cout << "\n" << GREEN << "✓ All tests passed!" << RESET << "\n\n";
        return 0;

    } catch (const std::exception& e) {
        std::cout << "\n" << RED << "✗ Test failed: " << e.what() << RESET << "\n\n";
        return 1;
    }
}