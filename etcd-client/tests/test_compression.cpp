// etcd-client/tests/test_compression.cpp
#include <crypto_transport/compression.hpp>
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

void test_compress_decompress_simple() {
    std::cout << "\n🧪 Test 1: Simple compress/decompress" << std::endl;

    std::string original = "Hello, World! This is a test string for LZ4 compression.";
    std::cout << "Original: \"" << original << "\" (" << original.size() << " bytes)" << std::endl;

    auto data = string_to_bytes(original);

    // Compress
    auto compressed = compress(data);
    std::cout << "Compressed: " << compressed.size() << " bytes" << std::endl;

    // Decompress
    auto decompressed = decompress(compressed, original.size());
    std::cout << "Decompressed: " << decompressed.size() << " bytes" << std::endl;

    // Verify
    std::string result = bytes_to_string(decompressed);
    assert(original == result);
    std::cout << "✅ Test 1 PASSED: Data matches after compress/decompress" << std::endl;

    // Show compression ratio
    double ratio = get_compression_ratio(original.size(), compressed.size());
    std::cout << "📊 Compression ratio: " << (ratio * 100.0) << "%" << std::endl;
}

void test_compress_large_data() {
    std::cout << "\n🧪 Test 2: Large data compression" << std::endl;

    // Generate 10KB of repetitive data (compresses well)
    std::string original;
    for (int i = 0; i < 1000; ++i) {
        original += "0123456789";
    }
    std::cout << "Original: " << original.size() << " bytes (10KB repetitive data)" << std::endl;

    auto data = string_to_bytes(original);

    // Compress
    auto compressed = compress(data);
    std::cout << "Compressed: " << compressed.size() << " bytes" << std::endl;

    // Decompress
    auto decompressed = decompress(compressed, original.size());

    // Verify
    std::string result = bytes_to_string(decompressed);
    assert(original == result);
    std::cout << "✅ Test 2 PASSED: Large data matches" << std::endl;

    // Show compression ratio
    double ratio = get_compression_ratio(original.size(), compressed.size());
    std::cout << "📊 Compression ratio: " << (ratio * 100.0) << "% (should be very small)" << std::endl;
}

void test_compress_random_data() {
    std::cout << "\n🧪 Test 3: Random data (poor compression)" << std::endl;

    // Generate pseudo-random data (compresses poorly)
    std::string original;
    for (int i = 0; i < 1000; ++i) {
        original += static_cast<char>((i * 7 + 13) % 256);
    }
    std::cout << "Original: " << original.size() << " bytes (pseudo-random)" << std::endl;

    auto data = string_to_bytes(original);

    // Compress
    auto compressed = compress(data);
    std::cout << "Compressed: " << compressed.size() << " bytes" << std::endl;

    // Decompress
    auto decompressed = decompress(compressed, original.size());

    // Verify
    std::string result = bytes_to_string(decompressed);
    assert(original == result);
    std::cout << "✅ Test 3 PASSED: Random data matches" << std::endl;

    // Show compression ratio
    double ratio = get_compression_ratio(original.size(), compressed.size());
    std::cout << "📊 Compression ratio: " << (ratio * 100.0) << "% (should be close to 100%)" << std::endl;
}

void test_should_compress() {
    std::cout << "\n🧪 Test 4: Compression threshold logic" << std::endl;

    assert(should_compress(100, 256) == false);  // 100 < 256
    assert(should_compress(256, 256) == true);   // 256 >= 256
    assert(should_compress(1000, 256) == true);  // 1000 >= 256

    std::cout << "✅ Test 4 PASSED: Threshold logic works" << std::endl;
}

void test_empty_data() {
    std::cout << "\n🧪 Test 5: Empty data handling" << std::endl;

    std::vector<uint8_t> empty;
    auto compressed = compress(empty);

    assert(compressed.empty());
    std::cout << "✅ Test 5 PASSED: Empty data handled correctly" << std::endl;
}

int main() {
    std::cout << "╔════════════════════════════════════════════════════════════╗" << std::endl;
    std::cout << "║  LZ4 Compression Tests (crypto-transport)                 ║" << std::endl;
    std::cout << "╚════════════════════════════════════════════════════════════╝" << std::endl;

    try {
        test_compress_decompress_simple();
        test_compress_large_data();
        test_compress_random_data();
        test_should_compress();
        test_empty_data();

        std::cout << "\n╔════════════════════════════════════════════════════════════╗" << std::endl;
        std::cout << "║  ✅ ALL COMPRESSION TESTS PASSED                          ║" << std::endl;
        std::cout << "╚════════════════════════════════════════════════════════════╝" << std::endl;

        return 0;

    } catch (const std::exception& e) {
        std::cerr << "\n❌ TEST FAILED: " << e.what() << std::endl;
        return 1;
    }
}