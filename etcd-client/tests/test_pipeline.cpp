// etcd-client/tests/test_pipeline.cpp
#include <crypto_transport/crypto.hpp>
#include <crypto_transport/compression.hpp>
#include <crypto_transport/utils.hpp>
#include <iostream>
#include <string>
#include <cassert>
#include <vector>
#include <cstdint>

using namespace crypto_transport;

// Helper functions for string <-> vector conversion
namespace {
    inline std::vector<uint8_t> string_to_bytes(const std::string& str) {
        return std::vector<uint8_t>(str.begin(), str.end());
    }

    inline std::string bytes_to_string(const std::vector<uint8_t>& bytes) {
        return std::string(bytes.begin(), bytes.end());
    }
}

void test_pipeline_small_data() {
    std::cout << "\n🧪 Test 1: Small data pipeline (Compress → Encrypt → Decrypt → Decompress)" << std::endl;

    std::string original = "Hello, World! This is a test of the complete pipeline.";
    std::cout << "Original: " << original.size() << " bytes" << std::endl;

    auto data = string_to_bytes(original);

    // Step 1: Compress
    auto compressed = compress(data);
    std::cout << "  [1] Compressed: " << data.size() << " → " << compressed.size() << " bytes" << std::endl;

    // Step 2: Encrypt
    auto key = generate_key();
    auto encrypted = encrypt(compressed, key);
    std::cout << "  [2] Encrypted: " << compressed.size() << " → " << encrypted.size() << " bytes" << std::endl;

    // Step 3: Decrypt
    auto decrypted = decrypt(encrypted, key);
    std::cout << "  [3] Decrypted: " << encrypted.size() << " → " << decrypted.size() << " bytes" << std::endl;
    assert(decrypted == compressed);

    // Step 4: Decompress
    auto final = decompress(decrypted, original.size());
    std::cout << "  [4] Decompressed: " << decrypted.size() << " → " << final.size() << " bytes" << std::endl;

    // Verify
    std::string result = bytes_to_string(final);
    assert(result == original);
    std::cout << "✅ Test 1 PASSED: Pipeline works correctly" << std::endl;
}

void test_pipeline_large_data() {
    std::cout << "\n🧪 Test 2: Large data pipeline (100KB repetitive)" << std::endl;

    // Generate 100KB of repetitive data (compresses VERY well)
    std::string original;
    for (int i = 0; i < 10000; ++i) {
        original += "0123456789";
    }
    std::cout << "Original: " << original.size() << " bytes" << std::endl;

    auto data = string_to_bytes(original);

    // Compress
    auto compressed = compress(data);
    std::cout << "  [1] Compressed: " << data.size() << " → " << compressed.size()
              << " bytes (" << (compressed.size() * 100.0 / data.size()) << "%)" << std::endl;

    // Encrypt
    auto key = generate_key();
    auto encrypted = encrypt(compressed, key);
    std::cout << "  [2] Encrypted: " << compressed.size() << " → " << encrypted.size()
              << " bytes (+40 bytes overhead)" << std::endl;

    // Decrypt
    auto decrypted = decrypt(encrypted, key);
    assert(decrypted == compressed);

    // Decompress
    auto final = decompress(decrypted, original.size());
    std::string result = bytes_to_string(final);
    assert(result == original);

    std::cout << "✅ Test 2 PASSED: Large data pipeline works" << std::endl;

    // Show total size reduction
    double total_ratio = (encrypted.size() * 100.0) / data.size();
    std::cout << "📊 Total size: " << data.size() << " → " << encrypted.size()
              << " bytes (" << total_ratio << "% of original)" << std::endl;
}

void test_pipeline_json_config() {
    std::cout << "\n🧪 Test 3: JSON config data (realistic use case)" << std::endl;

    // Simulate a realistic JSON config
    std::string original = R"({
  "component": "ml-detector",
  "thresholds": {
    "ddos": 0.85,
    "ransomware": 0.90,
    "traffic": 0.75,
    "internal": 0.80
  },
  "features": [
    "packet_size", "inter_arrival_time", "protocol_distribution",
    "port_scan_score", "syn_flood_score", "connection_rate"
  ],
  "logging": {
    "level": "INFO",
    "output": "/var/log/ml-defender/detector.log",
    "rotation": "daily",
    "max_size_mb": 100
  },
  "performance": {
    "batch_size": 1000,
    "inference_timeout_ms": 500,
    "max_queue_size": 10000
  }
})";

    std::cout << "Original JSON: " << original.size() << " bytes" << std::endl;

    auto data = string_to_bytes(original);

    // Pipeline
    auto compressed = compress(data);
    auto key = generate_key();
    auto encrypted = encrypt(compressed, key);

    std::cout << "  Compressed: " << data.size() << " → " << compressed.size() << " bytes" << std::endl;
    std::cout << "  Encrypted: " << compressed.size() << " → " << encrypted.size() << " bytes" << std::endl;

    // Reverse
    auto decrypted = decrypt(encrypted, key);
    auto final = decompress(decrypted, original.size());

    std::string result = bytes_to_string(final);
    assert(result == original);
    std::cout << "✅ Test 3 PASSED: JSON config survives pipeline" << std::endl;

    double total_ratio = (encrypted.size() * 100.0) / data.size();
    std::cout << "📊 Storage efficiency: " << total_ratio << "% of original size" << std::endl;
}

int main() {
    std::cout << "╔════════════════════════════════════════════════════════════╗" << std::endl;
    std::cout << "║  Complete Pipeline Tests (crypto-transport)                ║" << std::endl;
    std::cout << "╚════════════════════════════════════════════════════════════╝" << std::endl;

    // Note: libsodium initialization is automatic in crypto-transport
    std::cout << "✅ crypto-transport initialized" << std::endl;

    try {
        test_pipeline_small_data();
        test_pipeline_large_data();
        test_pipeline_json_config();

        std::cout << "\n╔════════════════════════════════════════════════════════════╗" << std::endl;
        std::cout << "║  ✅ ALL PIPELINE TESTS PASSED                             ║" << std::endl;
        std::cout << "║                                                            ║" << std::endl;
        std::cout << "║  Pipeline validated:                                       ║" << std::endl;
        std::cout << "║  Data → Compress → Encrypt → Decrypt → Decompress → Data  ║" << std::endl;
        std::cout << "╚════════════════════════════════════════════════════════════╝" << std::endl;

        return 0;

    } catch (const std::exception& e) {
        std::cerr << "\n❌ TEST FAILED: " << e.what() << std::endl;
        return 1;
    }
}