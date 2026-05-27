// ============================================================================
// PayloadAnalyzer Unit Test - No GTest version (compatible with sniffer)
// ============================================================================

#include "payload_analyzer.hpp"
#include <iostream>
#include <vector>
#include <chrono>
#include <random>
#include <cstring>
#include <cassert>

using namespace sniffer;

// ============================================================================
// Test Helpers
// ============================================================================

int g_test_count = 0;
int g_test_passed = 0;
int g_test_failed = 0;

#define TEST_START(name) \
    do { \
        ++g_test_count; \
        std::cout << "[TEST " << g_test_count << "] " << name << "... "; \
    } while(0)

#define TEST_PASS() \
    do { \
        ++g_test_passed; \
        std::cout << "✅ PASS" << std::endl; \
    } while(0)

#define TEST_FAIL(reason) \
    do { \
        ++g_test_failed; \
        std::cout << "❌ FAIL: " << reason << std::endl; \
    } while(0)

#define EXPECT_TRUE(condition) \
    do { \
        if (!(condition)) { \
            TEST_FAIL("Expected true but got false"); \
            return false; \
        } \
    } while(0)

#define EXPECT_FALSE(condition) \
    do { \
        if (condition) { \
            TEST_FAIL("Expected false but got true"); \
            return false; \
        } \
    } while(0)

#define EXPECT_EQ(expected, actual) \
    do { \
        if ((expected) != (actual)) { \
            TEST_FAIL("Expected " << (expected) << " but got " << (actual)); \
            return false; \
        } \
    } while(0)

#define EXPECT_FLOAT_EQ(expected, actual) \
    do { \
        if (std::abs((expected) - (actual)) > 0.01f) { \
            TEST_FAIL("Expected " << (expected) << " but got " << (actual)); \
            return false; \
        } \
    } while(0)

#define EXPECT_GT(val, threshold) \
    do { \
        if ((val) <= (threshold)) { \
            TEST_FAIL("Expected " << (val) << " > " << (threshold)); \
            return false; \
        } \
    } while(0)

#define EXPECT_LT(val, threshold) \
    do { \
        if ((val) >= (threshold)) { \
            TEST_FAIL("Expected " << (val) << " < " << (threshold)); \
            return false; \
        } \
    } while(0)

// ============================================================================
// Helper Functions
// ============================================================================

std::vector<uint8_t> create_random_payload(size_t len, unsigned int seed = 42) {
    std::mt19937 gen(seed);
    std::uniform_int_distribution<> dis(0, 255);
    
    std::vector<uint8_t> payload(len);
    for (size_t i = 0; i < len; ++i) {
        payload[i] = static_cast<uint8_t>(dis(gen));
    }
    return payload;
}

std::vector<uint8_t> create_text_payload(const std::string& text) {
    return std::vector<uint8_t>(text.begin(), text.end());
}

std::vector<uint8_t> create_pe_header() {
    std::vector<uint8_t> pe(512, 0);
    
    // DOS Header
    pe[0] = 'M';
    pe[1] = 'Z';
    
    // PE offset at 0x3C (pointing to offset 128)
    uint32_t pe_offset = 128;
    pe[0x3C] = pe_offset & 0xFF;
    pe[0x3D] = (pe_offset >> 8) & 0xFF;
    pe[0x3E] = (pe_offset >> 16) & 0xFF;
    pe[0x3F] = (pe_offset >> 24) & 0xFF;
    
    // PE Signature at offset 128
    pe[128] = 'P';
    pe[129] = 'E';
    pe[130] = 0;
    pe[131] = 0;
    
    // COFF Header (Machine Type: x64 = 0x8664)
    pe[132] = 0x64;
    pe[133] = 0x86;
    
    // Timestamp (example: 0x12345678)
    pe[136] = 0x78;
    pe[137] = 0x56;
    pe[138] = 0x34;
    pe[139] = 0x12;
    
    return pe;
}

// ============================================================================
// Test Cases
// ============================================================================

bool test_null_payload() {
    TEST_START("Null payload returns zero features");
    
    PayloadAnalyzer analyzer;
    auto features = analyzer.analyze(nullptr, 0);
    
    EXPECT_FALSE(features.is_pe_executable);
    EXPECT_FLOAT_EQ(features.entropy, 0.0f);
    EXPECT_FALSE(features.high_entropy);
    EXPECT_FALSE(features.ransom_note_pattern);
    EXPECT_EQ(features.analyzed_bytes, 0);
    
    TEST_PASS();
    return true;
}

bool test_empty_payload() {
    TEST_START("Empty payload returns zero features");
    
    PayloadAnalyzer analyzer;
    std::vector<uint8_t> empty;
    auto features = analyzer.analyze(empty.data(), 0);
    
    EXPECT_FALSE(features.is_pe_executable);
    EXPECT_FLOAT_EQ(features.entropy, 0.0f);
    EXPECT_EQ(features.analyzed_bytes, 0);
    
    TEST_PASS();
    return true;
}

bool test_valid_pe_header() {
    TEST_START("Valid PE header detected");
    
    PayloadAnalyzer analyzer;
    auto pe = create_pe_header();
    auto features = analyzer.analyze(pe.data(), pe.size());
    
    EXPECT_TRUE(features.is_pe_executable);
    EXPECT_EQ(features.pe_machine_type, 0x8664);
    EXPECT_EQ(features.pe_timestamp, 0x12345678);
    
    TEST_PASS();
    return true;
}

bool test_invalid_mz_signature() {
    TEST_START("Invalid MZ signature not detected");
    
    PayloadAnalyzer analyzer;
    auto pe = create_pe_header();
    pe[0] = 'X';  // Corrupt MZ
    
    auto features = analyzer.analyze(pe.data(), pe.size());
    EXPECT_FALSE(features.is_pe_executable);
    
    TEST_PASS();
    return true;
}

bool test_invalid_pe_signature() {
    TEST_START("Invalid PE signature not detected");
    
    PayloadAnalyzer analyzer;
    auto pe = create_pe_header();
    pe[128] = 'X';  // Corrupt PE
    
    auto features = analyzer.analyze(pe.data(), pe.size());
    EXPECT_FALSE(features.is_pe_executable);
    
    TEST_PASS();
    return true;
}

bool test_truncated_pe_header() {
    TEST_START("Truncated PE header not detected");
    
    PayloadAnalyzer analyzer;
    auto pe = create_pe_header();
    
    auto features = analyzer.analyze(pe.data(), 32);  // Too short
    EXPECT_FALSE(features.is_pe_executable);
    
    TEST_PASS();
    return true;
}

bool test_plain_text_low_entropy() {
    TEST_START("Plain text has low entropy");
    
    PayloadAnalyzer analyzer;
    auto text = create_text_payload("Hello World! This is a plain text message.");
    auto features = analyzer.analyze(text.data(), text.size());
    
    EXPECT_LT(features.entropy, 5.0f);
    EXPECT_FALSE(features.high_entropy);
    
    TEST_PASS();
    return true;
}

bool test_random_data_high_entropy() {
    TEST_START("Random data has high entropy");
    
    PayloadAnalyzer analyzer;
    auto random = create_random_payload(512);
    auto features = analyzer.analyze(random.data(), random.size());
    
    EXPECT_GT(features.entropy, 7.0f);
    EXPECT_TRUE(features.high_entropy);
    
    TEST_PASS();
    return true;
}

bool test_all_zeros_entropy() {
    TEST_START("All same byte has zero entropy");
    
    PayloadAnalyzer analyzer;
    std::vector<uint8_t> zeros(100, 0);
    auto features = analyzer.analyze(zeros.data(), zeros.size());
    
    EXPECT_FLOAT_EQ(features.entropy, 0.0f);
    EXPECT_FALSE(features.high_entropy);
    
    TEST_PASS();
    return true;
}

bool test_ransom_note_detection() {
    TEST_START("Ransom note pattern detected");
    
    PayloadAnalyzer analyzer;
    auto text = create_text_payload(
        "YOUR FILES HAVE BEEN ENCRYPTED! "
        "Pay 0.5 BITCOIN to wallet: bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh"
    );
    
    auto features = analyzer.analyze(text.data(), text.size());
    
    EXPECT_TRUE(features.ransom_note_pattern);
    EXPECT_GT(features.suspicious_strings, 3);
    
    TEST_PASS();
    return true;
}

bool test_crypto_api_detection() {
    TEST_START("Crypto API pattern detected");
    
    PayloadAnalyzer analyzer;
    auto text = create_text_payload("Calling CryptEncrypt with AES-256 algorithm");
    
    auto features = analyzer.analyze(text.data(), text.size());
    
    EXPECT_TRUE(features.crypto_api_pattern);
    EXPECT_GT(features.suspicious_strings, 1);
    
    TEST_PASS();
    return true;
}

bool test_onion_address_detection() {
    TEST_START("Onion address detected");
    
    PayloadAnalyzer analyzer;
    auto text = create_text_payload("Visit http://3g2upl4pq6kufc4m.onion for instructions");
    
    auto features = analyzer.analyze(text.data(), text.size());
    
    EXPECT_TRUE(features.ransom_note_pattern);
    
    TEST_PASS();
    return true;
}

bool test_case_insensitive_matching() {
    TEST_START("Case-insensitive pattern matching");
    
    PayloadAnalyzer analyzer;
    
    auto upper = create_text_payload("YOUR FILES ARE ENCRYPTED");
    auto lower = create_text_payload("your files are encrypted");
    auto mixed = create_text_payload("YoUr FiLeS aRe EnCrYpTeD");
    
    EXPECT_TRUE(analyzer.analyze(upper.data(), upper.size()).ransom_note_pattern);
    EXPECT_TRUE(analyzer.analyze(lower.data(), lower.size()).ransom_note_pattern);
    EXPECT_TRUE(analyzer.analyze(mixed.data(), mixed.size()).ransom_note_pattern);
    
    TEST_PASS();
    return true;
}

bool test_no_false_positives() {
    TEST_START("No false positives on normal data");
    
    PayloadAnalyzer analyzer;
    auto text = create_text_payload(
        "GET /index.html HTTP/1.1\r\n"
        "Host: example.com\r\n"
        "User-Agent: Mozilla/5.0\r\n"
    );
    
    auto features = analyzer.analyze(text.data(), text.size());
    
    EXPECT_FALSE(features.ransom_note_pattern);
    EXPECT_FALSE(features.crypto_api_pattern);
    EXPECT_EQ(features.suspicious_strings, 0);
    
    TEST_PASS();
    return true;
}

bool test_performance_under_10us() {
    TEST_START("Performance under 10 microseconds");
    
    PayloadAnalyzer analyzer;
    auto payload = create_random_payload(512);
    
    // Warm-up
    for (int i = 0; i < 100; ++i) {
        analyzer.analyze(payload.data(), payload.size());
    }
    
    // Benchmark
    const int iterations = 10000;
    auto start = std::chrono::high_resolution_clock::now();
    
    for (int i = 0; i < iterations; ++i) {
        auto features = analyzer.analyze(payload.data(), payload.size());
        volatile auto dummy = features.entropy;
        (void)dummy;
    }
    
    auto end = std::chrono::high_resolution_clock::now();
    auto duration_us = std::chrono::duration_cast<std::chrono::microseconds>(end - start).count();
    
    double avg_us = static_cast<double>(duration_us) / iterations;
    
    std::cout << std::endl;
    std::cout << "      [PERF] Average: " << avg_us << " μs" << std::endl;
    std::cout << "      ";
    
    if (avg_us >= 10.0) {
        TEST_FAIL("Performance too slow: " << avg_us << " μs (target: <10 μs)");
        return false;
    }
    
    TEST_PASS();
    return true;
}

bool test_thread_local_isolation() {
    TEST_START("Thread-local state isolated");
    
    PayloadAnalyzer analyzer;
    
    auto payload1 = create_random_payload(256, 111);
    auto payload2 = create_random_payload(256, 222);
    
    auto f1_first = analyzer.analyze(payload1.data(), payload1.size());
    auto f2 = analyzer.analyze(payload2.data(), payload2.size());
    auto f1_second = analyzer.analyze(payload1.data(), payload1.size());
    
    // Same payload should give same results
    if (std::abs(f1_first.entropy - f1_second.entropy) > 0.01f) {
        TEST_FAIL("Entropy changed for same payload");
        return false;
    }
    
    if (f1_first.suspicious_strings != f1_second.suspicious_strings) {
        TEST_FAIL("Suspicious strings changed for same payload");
        return false;
    }
    
    TEST_PASS();
    return true;
}

bool test_single_byte_payload() {
    TEST_START("Single byte payload");
    
    PayloadAnalyzer analyzer;
    uint8_t single = 0x42;
    auto features = analyzer.analyze(&single, 1);
    
    EXPECT_EQ(features.analyzed_bytes, 1);
    EXPECT_FLOAT_EQ(features.entropy, 0.0f);
    
    TEST_PASS();
    return true;
}

bool test_max_payload_size() {
    TEST_START("Max payload size (512 bytes)");
    
    PayloadAnalyzer analyzer;
    auto large = create_random_payload(512);
    auto features = analyzer.analyze(large.data(), large.size());
    
    EXPECT_EQ(features.analyzed_bytes, 512);
    EXPECT_GT(features.entropy, 7.0f);
    
    TEST_PASS();
    return true;
}

// ============================================================================
// Main Test Runner
// ============================================================================

int main() {
    std::cout << std::endl;
    std::cout << "╔═══════════════════════════════════════════════════════════╗" << std::endl;
    std::cout << "║  PayloadAnalyzer Unit Tests                              ║" << std::endl;
    std::cout << "╚═══════════════════════════════════════════════════════════╝" << std::endl;
    std::cout << std::endl;
    
    // Run all tests
    test_null_payload();
    test_empty_payload();
    test_valid_pe_header();
    test_invalid_mz_signature();
    test_invalid_pe_signature();
    test_truncated_pe_header();
    test_plain_text_low_entropy();
    test_random_data_high_entropy();
    test_all_zeros_entropy();
    test_ransom_note_detection();
    test_crypto_api_detection();
    test_onion_address_detection();
    test_case_insensitive_matching();
    test_no_false_positives();
    test_performance_under_10us();
    test_thread_local_isolation();
    test_single_byte_payload();
    test_max_payload_size();
    
    // Summary
    std::cout << std::endl;
    std::cout << "═══════════════════════════════════════════════════════════" << std::endl;
    std::cout << "📊 TEST SUMMARY" << std::endl;
    std::cout << "═══════════════════════════════════════════════════════════" << std::endl;
    std::cout << "Total:  " << g_test_count << std::endl;
    std::cout << "Passed: " << g_test_passed << " ✅" << std::endl;
    std::cout << "Failed: " << g_test_failed << " ❌" << std::endl;
    std::cout << "═══════════════════════════════════════════════════════════" << std::endl;
    std::cout << std::endl;
    
    if (g_test_failed == 0) {
        std::cout << "🎉 ALL TESTS PASSED! ✅" << std::endl;
        std::cout << std::endl;
        return 0;
    } else {
        std::cout << "❌ SOME TESTS FAILED" << std::endl;
        std::cout << std::endl;
        return 1;
    }
}
