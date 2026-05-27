// crypto-transport/tests/test_compression.cpp
#include "crypto_transport/compression.hpp"
#include <iostream>
#include <cassert>
#include <string>
#include <cstring>

using namespace crypto_transport;

void test_compress_decompress_basic() {
    std::cout << "TEST: Basic compress/decompress... ";

    std::string text = "Hello, compression! This text should compress well. "
                       "Repeated patterns help compression ratios.";
    std::vector<uint8_t> data(text.begin(), text.end());
    size_t original_size = data.size();

    // Compress
    auto compressed = compress(data);
    assert(!compressed.empty());
    assert(compressed.size() < data.size());  // Should be smaller

    // Decompress
    auto decompressed = decompress(compressed, original_size);
    assert(decompressed == data);

    std::string result(decompressed.begin(), decompressed.end());
    assert(result == text);

    std::cout << "✅ PASS" << std::endl;
}

void test_empty_data() {
    std::cout << "TEST: Empty data handling... ";

    std::vector<uint8_t> empty;

    auto compressed = compress(empty);
    assert(compressed.empty());

    auto decompressed = decompress(empty, 0);
    assert(decompressed.empty());

    std::cout << "✅ PASS" << std::endl;
}

void test_compression_ratio() {
    std::cout << "TEST: Compression ratio calculation... ";

    // Create highly compressible data (repeated pattern)
    std::vector<uint8_t> data(1000, 'A');  // 1000 bytes of 'A'

    auto compressed = compress(data);

    double ratio = get_compression_ratio(data.size(), compressed.size());
    assert(ratio < 0.1);  // Should compress to < 10% (very good ratio)

    std::cout << "  Original: " << data.size()
              << " -> Compressed: " << compressed.size()
              << " (ratio: " << ratio << ")" << std::endl;
    std::cout << "✅ PASS" << std::endl;
}

void test_should_compress_threshold() {
    std::cout << "TEST: Should compress threshold... ";

    assert(should_compress(100, 256) == false);   // Below threshold
    assert(should_compress(256, 256) == true);    // At threshold
    assert(should_compress(1000, 256) == true);   // Above threshold
    assert(should_compress(128, 100) == true);    // Custom threshold

    std::cout << "✅ PASS" << std::endl;
}

void test_small_data() {
    std::cout << "TEST: Small data (may not compress)... ";

    std::vector<uint8_t> small = {1, 2, 3, 4, 5};

    auto compressed = compress(small);
    auto decompressed = decompress(compressed, small.size());

    assert(decompressed == small);

    // Note: Small random data often doesn't compress well
    std::cout << "  Original: " << small.size()
              << " -> Compressed: " << compressed.size() << std::endl;
    std::cout << "✅ PASS" << std::endl;
}

void test_large_data() {
    std::cout << "TEST: Large data (1MB)... ";

    // Create 1MB of semi-compressible data
    std::vector<uint8_t> large_data(1024 * 1024);
    for (size_t i = 0; i < large_data.size(); ++i) {
        large_data[i] = static_cast<uint8_t>((i / 4) % 256);  // Some repetition
    }

    auto compressed = compress(large_data);
    assert(compressed.size() < large_data.size());

    auto decompressed = decompress(compressed, large_data.size());
    assert(decompressed == large_data);

    double ratio = get_compression_ratio(large_data.size(), compressed.size());
    std::cout << "  Original: " << large_data.size()
              << " -> Compressed: " << compressed.size()
              << " (ratio: " << ratio << ")" << std::endl;
    std::cout << "✅ PASS" << std::endl;
}

void test_wrong_original_size() {
    std::cout << "TEST: Wrong original size detection... ";

    std::vector<uint8_t> data(100, 'X');
    auto compressed = compress(data);

    bool caught_exception = false;
    try {
        decompress(compressed, 200);  // Wrong size (too large)
    } catch (const std::runtime_error& e) {
        caught_exception = true;
        assert(std::string(e.what()).find("mismatch") != std::string::npos);
    }
    assert(caught_exception);

    std::cout << "✅ PASS" << std::endl;
}

void test_zero_original_size() {
    std::cout << "TEST: Zero original size validation... ";

    std::vector<uint8_t> compressed = {1, 2, 3, 4};

    bool caught_exception = false;
    try {
        decompress(compressed, 0);  // Invalid: original_size = 0
    } catch (const std::runtime_error& e) {
        caught_exception = true;
        assert(std::string(e.what()).find("must be > 0") != std::string::npos);
    }
    assert(caught_exception);

    std::cout << "✅ PASS" << std::endl;
}

void test_corrupted_data() {
    std::cout << "TEST: Corrupted compressed data detection... ";

    std::vector<uint8_t> data(100, 'Y');
    auto compressed = compress(data);

    // Corrupt the compressed data
    if (!compressed.empty()) {
        compressed[0] ^= 0xFF;
    }

    bool caught_exception = false;
    try {
        decompress(compressed, data.size());
    } catch (const std::runtime_error& e) {
        caught_exception = true;
        assert(std::string(e.what()).find("failed") != std::string::npos);
    }
    assert(caught_exception);

    std::cout << "✅ PASS" << std::endl;
}

void test_binary_data() {
    std::cout << "TEST: Binary data (non-text)... ";

    std::vector<uint8_t> binary(256);
    for (size_t i = 0; i < binary.size(); ++i) {
        binary[i] = static_cast<uint8_t>(i);
    }

    auto compressed = compress(binary);
    auto decompressed = decompress(compressed, binary.size());

    assert(decompressed == binary);

    std::cout << "✅ PASS" << std::endl;
}

int main() {
    std::cout << "========================================" << std::endl;
    std::cout << "crypto-transport: Compression Tests" << std::endl;
    std::cout << "========================================" << std::endl;

    try {
        test_compress_decompress_basic();
        test_empty_data();
        test_compression_ratio();
        test_should_compress_threshold();
        test_small_data();
        test_large_data();
        test_wrong_original_size();
        test_zero_original_size();
        test_corrupted_data();
        test_binary_data();

        std::cout << "========================================" << std::endl;
        std::cout << "✅ All compression tests PASSED!" << std::endl;
        std::cout << "========================================" << std::endl;
        return 0;

    } catch (const std::exception& e) {
        std::cerr << "❌ TEST FAILED: " << e.what() << std::endl;
        return 1;
    }
}