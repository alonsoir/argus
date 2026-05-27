// crypto-transport/tests/test_integration.cpp
#include "crypto_transport/crypto.hpp"
#include "crypto_transport/compression.hpp"
#include "crypto_transport/utils.hpp"
#include <iostream>
#include <cassert>
#include <string>
#include <cstring>

using namespace crypto_transport;

void test_compress_then_encrypt() {
    std::cout << "TEST: Compress → Encrypt → Decrypt → Decompress... ";

    auto key = generate_key();
    std::string plaintext = "This is a test message that should compress well! "
                           "Repeated patterns help. Repeated patterns help.";
    std::vector<uint8_t> data(plaintext.begin(), plaintext.end());
    size_t original_size = data.size();

    // Step 1: Compress
    auto compressed = compress(data);
    size_t compressed_size = compressed.size();

    // Step 2: Encrypt
    auto encrypted = encrypt(compressed, key);

    std::cout << std::endl;
    std::cout << "  Original:   " << original_size << " bytes" << std::endl;
    std::cout << "  Compressed: " << compressed_size << " bytes" << std::endl;
    std::cout << "  Encrypted:  " << encrypted.size() << " bytes" << std::endl;

    // Step 3: Decrypt
    auto decrypted = decrypt(encrypted, key);
    assert(decrypted == compressed);

    // Step 4: Decompress
    auto decompressed = decompress(decrypted, original_size);
    assert(decompressed == data);

    std::string result(decompressed.begin(), decompressed.end());
    assert(result == plaintext);

    std::cout << "✅ PASS" << std::endl;
}

void test_encrypt_then_compress() {
    std::cout << "TEST: Encrypt → Compress (bad order)... ";

    auto key = generate_key();
    std::string plaintext = "Test data";
    std::vector<uint8_t> data(plaintext.begin(), plaintext.end());

    // Step 1: Encrypt (adds randomness via nonce)
    auto encrypted = encrypt(data, key);

    // Step 2: Try to compress encrypted data (won't compress well)
    auto compressed = compress(encrypted);

    // Encrypted data is essentially random, so compression is ineffective
    double ratio = get_compression_ratio(encrypted.size(), compressed.size());

    std::cout << std::endl;
    std::cout << "  Encrypted:  " << encrypted.size() << " bytes" << std::endl;
    std::cout << "  Compressed: " << compressed.size() << " bytes" << std::endl;
    std::cout << "  Ratio:      " << ratio << " (>0.9 = bad compression)" << std::endl;
    std::cout << "  ⚠️  Note: Encrypting before compression is inefficient!" << std::endl;

    std::cout << "✅ PASS" << std::endl;
}

void test_json_config_workflow() {
    std::cout << "TEST: JSON config workflow (etcd-client simulation)... ";

    // Simulate component config JSON
    std::string json_config = R"({
        "component": "sniffer",
        "interface": "eth0",
        "transport": {
            "encryption": {
                "enabled": true,
                "algorithm": "chacha20-poly1305"
            },
            "compression": {
                "enabled": true,
                "algorithm": "lz4",
                "min_size": 256
            }
        },
        "capture": {
            "buffer_size": 65536,
            "timeout_ms": 100
        }
    })";

    std::vector<uint8_t> config_data(json_config.begin(), json_config.end());
    size_t original_size = config_data.size();

    // Get key from etcd-server (simulated as hex)
    auto key = generate_key();
    std::string key_hex = bytes_to_hex(key);

    // Component processes config for upload
    auto compressed = compress(config_data);
    auto encrypted = encrypt(compressed, key);

    std::cout << std::endl;
    std::cout << "  JSON config: " << original_size << " bytes" << std::endl;
    std::cout << "  After compress+encrypt: " << encrypted.size() << " bytes" << std::endl;

    // Server receives and processes
    auto decrypted = decrypt(encrypted, hex_to_bytes(key_hex));
    auto decompressed = decompress(decrypted, original_size);

    std::string recovered_json(decompressed.begin(), decompressed.end());
    assert(recovered_json == json_config);

    std::cout << "✅ PASS" << std::endl;
}

void test_zmq_payload_workflow() {
    std::cout << "TEST: ZMQ payload workflow (sniffer→detector simulation)... ";

    // Simulate packet event payload (protobuf-like binary data)
    std::vector<uint8_t> event_data(512);
    for (size_t i = 0; i < event_data.size(); ++i) {
        event_data[i] = static_cast<uint8_t>(i % 256);
    }
    size_t original_size = event_data.size();

    auto key = generate_key();

    // Sniffer: compress + encrypt before ZMQ send
    auto compressed = compress(event_data);
    auto encrypted = encrypt(compressed, key);

    std::cout << std::endl;
    std::cout << "  Event payload: " << original_size << " bytes" << std::endl;
    std::cout << "  Sent over ZMQ: " << encrypted.size() << " bytes" << std::endl;

    // Detector: decrypt + decompress after ZMQ recv
    auto decrypted = decrypt(encrypted, key);
    auto decompressed = decompress(decrypted, original_size);

    assert(decompressed == event_data);

    std::cout << "✅ PASS" << std::endl;
}

void test_large_config_performance() {
    std::cout << "TEST: Large config (10KB JSON)... ";

    // Create large config with repeated sections
    std::string large_json = "{\"rules\": [";
    for (int i = 0; i < 100; ++i) {
        if (i > 0) large_json += ",";
        large_json += R"({"id": )" + std::to_string(i) +
                     R"(, "action": "block", "protocol": "tcp"})";
    }
    large_json += "]}";

    std::vector<uint8_t> data(large_json.begin(), large_json.end());
    size_t original_size = data.size();

    auto key = generate_key();

    // Process
    auto compressed = compress(data);
    auto encrypted = encrypt(compressed, key);

    double compression_ratio = get_compression_ratio(original_size, compressed.size());
    double total_ratio = get_compression_ratio(original_size, encrypted.size());

    std::cout << std::endl;
    std::cout << "  Original:     " << original_size << " bytes" << std::endl;
    std::cout << "  Compressed:   " << compressed.size() << " bytes (ratio: "
              << compression_ratio << ")" << std::endl;
    std::cout << "  Final size:   " << encrypted.size() << " bytes (ratio: "
              << total_ratio << ")" << std::endl;

    // Verify round-trip
    auto decrypted = decrypt(encrypted, key);
    auto decompressed = decompress(decrypted, original_size);

    std::string result(decompressed.begin(), decompressed.end());
    assert(result == large_json);

    std::cout << "✅ PASS" << std::endl;
}

void test_conditional_compression() {
    std::cout << "TEST: Conditional compression (small data)... ";

    std::string small_data = "tiny";
    std::vector<uint8_t> data(small_data.begin(), small_data.end());
    size_t original_size = data.size();

    auto key = generate_key();

    // Check if should compress
    if (should_compress(data.size(), 256)) {
        std::cout << std::endl << "  Compressing..." << std::endl;
        auto compressed = compress(data);
        auto encrypted = encrypt(compressed, key);
        // Would decompress on other end
    } else {
        std::cout << std::endl << "  Skipping compression (too small)..." << std::endl;
        auto encrypted = encrypt(data, key);
        auto decrypted = decrypt(encrypted, key);
        assert(decrypted == data);
    }

    std::cout << "✅ PASS" << std::endl;
}

void test_error_propagation() {
    std::cout << "TEST: Error propagation in pipeline... ";

    auto key = generate_key();
    std::vector<uint8_t> data = {1, 2, 3, 4, 5};

    auto compressed = compress(data);
    auto encrypted = encrypt(compressed, key);

    // Corrupt encrypted data
    encrypted[encrypted.size() / 2] ^= 0xFF;

    bool caught_exception = false;
    try {
        auto decrypted = decrypt(encrypted, key);  // Should fail here
        decompress(decrypted, data.size());
    } catch (const std::runtime_error& e) {
        caught_exception = true;
        std::cout << std::endl << "  Expected error: " << e.what() << std::endl;
    }
    assert(caught_exception);

    std::cout << "✅ PASS" << std::endl;
}

int main() {
    std::cout << "========================================" << std::endl;
    std::cout << "crypto-transport: Integration Tests" << std::endl;
    std::cout << "========================================" << std::endl;

    try {
        test_compress_then_encrypt();
        test_encrypt_then_compress();
        test_json_config_workflow();
        test_zmq_payload_workflow();
        test_large_config_performance();
        test_conditional_compression();
        test_error_propagation();

        std::cout << "========================================" << std::endl;
        std::cout << "✅ All integration tests PASSED!" << std::endl;
        std::cout << "========================================" << std::endl;
        std::cout << std::endl;
        std::cout << "🎯 Key Insights:" << std::endl;
        std::cout << "  • Always compress BEFORE encrypt" << std::endl;
        std::cout << "  • Encrypted data doesn't compress well" << std::endl;
        std::cout << "  • Skip compression for data < 256 bytes" << std::endl;
        std::cout << "  • Errors propagate properly (fail-fast)" << std::endl;
        std::cout << "========================================" << std::endl;
        return 0;

    } catch (const std::exception& e) {
        std::cerr << "❌ TEST FAILED: " << e.what() << std::endl;
        return 1;
    }
}