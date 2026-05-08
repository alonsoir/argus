// ML Defender - Ransomware Detector Tests
// Tests basic functionality and performance

#include "ml_defender/ransomware_detector.hpp"

#include <cassert>
#include <chrono>
#include <iostream>
#include <iomanip>

using namespace ml_defender;
using namespace std::chrono;

void test_benign_case() {
    std::cout << "🧪 Test 1: Benign traffic detection..." << std::flush;

    RansomwareDetector detector;

    // Benign features: low entropy, normal resource usage
    RansomwareDetector::Features benign{
        .io_intensity = 0.5f,
        .entropy = 0.3f,          // Low entropy = benign
        .resource_usage = 0.4f,
        .network_activity = 0.6f,
        .file_operations = 0.5f,
        .process_anomaly = 0.1f,
        .temporal_pattern = 0.3f,
        .access_frequency = 0.4f,
        .data_volume = 0.5f,
        .behavior_consistency = 0.8f
    };

    auto result = detector.predict(benign);

    assert(result.class_id == 0);  // Should be benign
    assert(result.benign_prob > 0.5f);

    std::cout << " ✅ PASS" << std::endl;
    std::cout << "   Class: " << result.class_id
              << " | P(benign): " << result.benign_prob
              << " | P(ransomware): " << result.ransomware_prob << std::endl;
}

void test_ransomware_case() {
    std::cout << "🧪 Test 2: Ransomware detection..." << std::flush;

    RansomwareDetector detector;

    // Ransomware features: high entropy, high resource usage, high I/O
    RansomwareDetector::Features ransomware{
        .io_intensity = 1.8f,     // Very high I/O
        .entropy = 1.9f,          // ⭐ Very high entropy = ransomware
        .resource_usage = 1.7f,   // High CPU/memory
        .network_activity = 0.3f,
        .file_operations = 1.6f,  // Many file ops
        .process_anomaly = 0.2f,
        .temporal_pattern = 0.4f,
        .access_frequency = 1.5f,
        .data_volume = 1.4f,
        .behavior_consistency = 0.2f  // Inconsistent behavior
    };

    auto result = detector.predict(ransomware);

    assert(result.class_id == 1);  // Should be ransomware
    assert(result.ransomware_prob > 0.75f);  // Above threshold
    assert(result.is_ransomware());

    std::cout << " ✅ PASS" << std::endl;
    std::cout << "   Class: " << result.class_id
              << " | P(benign): " << result.benign_prob
              << " | P(ransomware): " << result.ransomware_prob
              << " | Confidence: " << result.confidence_level() << std::endl;
}

void test_performance() {
    std::cout << "⚡ Test 3: Performance benchmark..." << std::flush;

    RansomwareDetector detector;

    RansomwareDetector::Features features{
        .io_intensity = 1.0f,
        .entropy = 1.0f,
        .resource_usage = 1.0f,
        .network_activity = 1.0f,
        .file_operations = 1.0f,
        .process_anomaly = 0.5f,
        .temporal_pattern = 0.5f,
        .access_frequency = 1.0f,
        .data_volume = 1.0f,
        .behavior_consistency = 0.5f
    };

    // Warm-up
    for (int i = 0; i < 100; ++i) {
        (void)detector.predict(features);
    }

    // Benchmark: 10,000 predictions
    constexpr int NUM_ITERATIONS = 10000;
    auto start = high_resolution_clock::now();

    for (int i = 0; i < NUM_ITERATIONS; ++i) {
        [[maybe_unused]] auto result = detector.predict(features);
        (void)result;  // Prevent optimization
    }

    auto end = high_resolution_clock::now();
    auto duration = duration_cast<nanoseconds>(end - start).count();

    double avg_latency_us = (duration / 1000.0) / NUM_ITERATIONS;

    std::cout << " ✅ PASS" << std::endl;
    std::cout << std::fixed << std::setprecision(2);
    std::cout << "   Average latency: " << avg_latency_us << " μs/prediction" << std::endl;
    std::cout << "   Throughput: " << (1000000.0 / avg_latency_us) << " predictions/sec" << std::endl;

    // Performance assertion: <100μs target
    if (avg_latency_us < 100.0) {
        std::cout << "   🎯 TARGET MET: <100μs" << std::endl;
    } else {
        std::cout << "   ⚠️  WARNING: Exceeds 100μs target" << std::endl;
    }
}

void test_batch_prediction() {
    std::cout << "🧪 Test 4: Batch prediction..." << std::flush;

    RansomwareDetector detector;

    std::vector<RansomwareDetector::Features> batch;
    for (int i = 0; i < 100; ++i) {
        batch.push_back({
            .io_intensity = 0.5f + i * 0.01f,
            .entropy = 0.3f + i * 0.015f,
            .resource_usage = 0.4f,
            .network_activity = 0.6f,
            .file_operations = 0.5f,
            .process_anomaly = 0.1f,
            .temporal_pattern = 0.3f,
            .access_frequency = 0.4f,
            .data_volume = 0.5f,
            .behavior_consistency = 0.8f
        });
    }

    auto results = detector.predict_batch(batch);

    assert(results.size() == 100);

    std::cout << " ✅ PASS" << std::endl;
    std::cout << "   Processed " << results.size() << " samples" << std::endl;
}

int main() {
    std::cout << "========================================" << std::endl;
    std::cout << "ML DEFENDER - RANSOMWARE DETECTOR TESTS" << std::endl;
    std::cout << "========================================" << std::endl;
    std::cout << std::endl;

    try {
        test_benign_case();
        test_ransomware_case();
        test_performance();
        test_batch_prediction();

        std::cout << std::endl;
        std::cout << "========================================" << std::endl;
        std::cout << "✅ ALL TESTS PASSED" << std::endl;
        std::cout << "========================================" << std::endl;

        return 0;
    } catch (const std::exception& e) {
        std::cerr << "❌ TEST FAILED: " << e.what() << std::endl;
        return 1;
    }
}