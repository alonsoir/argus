// test_csv_event_loader.cpp
// RAG Ingester - CsvEventLoader Unit Tests
// Day 67: Verify 127-column CSV parsing + HMAC-SHA256 verification
// AUTHORS: Alonso Isidoro Roman + Claude (Anthropic)

#include "csv_event_loader.hpp"

#include <openssl/hmac.h>
#include <openssl/evp.h>
#include <algorithm>   // ADD THIS — para std::find_if
#include <iostream>
#include <sstream>
#include <iomanip>
#include <cassert>
#include <string>
#include <vector>
#include <numeric>

using namespace rag_ingester;

// ============================================================================
// Test HMAC key (32 bytes, all 0xAB) — hex: "abab...ab" (64 chars)
// ============================================================================

const std::string TEST_KEY_HEX(64, '0');   // 64 zeros → 32 zero bytes

// ============================================================================
// Helpers
// ============================================================================

// Compute HMAC-SHA256 over content using the test key
std::string compute_test_hmac(const std::string& content,
                               const std::string& key_hex = TEST_KEY_HEX)
{
    std::vector<uint8_t> key;
    key.reserve(32);
    for (size_t i = 0; i < key_hex.size(); i += 2) {
        unsigned int b = 0;
        std::sscanf(key_hex.c_str() + i, "%02x", &b);
        key.push_back(static_cast<uint8_t>(b));
    }

    unsigned char digest[EVP_MAX_MD_SIZE];
    unsigned int  dlen = 0;
    HMAC(EVP_sha256(), key.data(), static_cast<int>(key.size()),
         reinterpret_cast<const unsigned char*>(content.data()),
         content.size(), digest, &dlen);

    std::ostringstream ss;
    ss << std::hex << std::setfill('0');
    for (unsigned int i = 0; i < dlen; ++i)
        ss << std::setw(2) << static_cast<unsigned int>(digest[i]);
    return ss.str();
}

// Build a minimal valid 127-column CSV line.
// Columns 0-13: metadata, 14-75: S2 features, 76-115: embedded (zeros),
// 116-125: ML decisions (empty), 126: HMAC.
std::string build_valid_line(
    const std::string& event_id    = "synthetic-0",
    const std::string& final_class = "MALICIOUS",
    float fast_score = 0.9f,
    float ml_score   = 0.21f,
    bool  bad_hmac   = false)
{
    std::ostringstream ss;

    // Section 1 (cols 0-13)
    ss << "1740390192000000000";     // 0  timestamp_ns
    ss << ',' << event_id;           // 1  event_id
    ss << ',' << "192.168.1.1";      // 2  src_ip
    ss << ',' << "10.0.0.1";         // 3  dst_ip
    ss << ',' << "54321";            // 4  src_port
    ss << ',' << "445";              // 5  dst_port
    ss << ',' << "TCP";              // 6  protocol
    ss << ',' << final_class;        // 7  final_class
    ss << ',' << "0.900000";         // 8  confidence
    ss << ',' << "";                 // 9  threat_category
    ss << ',' << std::fixed << std::setprecision(6) << fast_score; // 10 fast_score
    ss << ',' << std::fixed << std::setprecision(6) << ml_score;   // 11 ml_score
    ss << ',' << "0.679000";         // 12 divergence
    ss << ',' << "MALICIOUS";        // 13 final_decision

    // Section 2 (cols 14-75): 62 synthetic feature values
    for (int i = 0; i < 62; ++i) {
        ss << ',' << (i % 7 == 0 ? "1234" : "0");
    }

    // Section 3 (cols 76-115): 40 embedded zeros
    for (int i = 0; i < 40; ++i) ss << ',' << "0.000000";

    // Section 4 (cols 116-125): ML decisions
    ss << ',' << "MALICIOUS";  // 116 l1_pred
    ss << ',' << "0.779000";   // 117 l1_conf
    ss << ',' << "";            // 118 l2d_pred
    ss << ',' << "0.000000";   // 119 l2d_conf
    ss << ',' << "";            // 120 l2r_pred
    ss << ',' << "0.000000";   // 121 l2r_conf
    ss << ',' << "";            // 122 l3t_pred
    ss << ',' << "0.000000";   // 123 l3t_conf
    ss << ',' << "";            // 124 l3i_pred
    ss << ',' << "0.000000";   // 125 l3i_conf

    // Section 5 (col 126): HMAC
    std::string content = ss.str();  // cols 0-125 joined
    std::string hmac = bad_hmac ? std::string(64, 'f')
                                : compute_test_hmac(content);
    ss << ',' << hmac;

    return ss.str();
}

// Count commas in a line (should be 126 for 127 columns)
int count_columns(const std::string& line) {
    int commas = 0;
    bool in_quotes = false;
    for (char c : line) {
        if (c == '"') in_quotes = !in_quotes;
        else if (c == ',' && !in_quotes) ++commas;
    }
    return commas + 1;  // columns = commas + 1
}

// ============================================================================
// Tests
// ============================================================================

bool test_construction_valid_key() {
    std::cout << "[TEST] Construction with valid 64-char key... ";
    try {
        CsvEventLoaderConfig cfg;
        cfg.hmac_key_hex  = TEST_KEY_HEX;
        cfg.verify_hmac   = true;
        CsvEventLoader loader(cfg);
        std::cout << "✓ PASS\n";
        return true;
    } catch (const std::exception& e) {
        std::cout << "✗ FAIL: " << e.what() << "\n";
        return false;
    }
}

bool test_construction_invalid_key_length() {
    std::cout << "[TEST] Construction rejects key != 64 chars... ";
    try {
        CsvEventLoaderConfig cfg;
        cfg.hmac_key_hex = "deadbeef";  // too short
        cfg.verify_hmac  = true;
        CsvEventLoader loader(cfg);
        std::cout << "✗ FAIL: should have thrown\n";
        return false;
    } catch (const std::invalid_argument&) {
        std::cout << "✓ PASS\n";
        return true;
    } catch (const std::exception& e) {
        std::cout << "✗ FAIL: wrong exception: " << e.what() << "\n";
        return false;
    }
}

bool test_parse_valid_line() {
    std::cout << "[TEST] Parse valid 127-column line with HMAC... ";

    CsvEventLoaderConfig cfg;
    cfg.hmac_key_hex = TEST_KEY_HEX;
    cfg.verify_hmac  = true;
    CsvEventLoader loader(cfg);

    std::string line = build_valid_line("synthetic-42", "MALICIOUS", 0.9f, 0.21f);

    assert(count_columns(line) == 127);

    auto result = loader.parse(line, 1);

    if (result.status != CsvParseStatus::OK) {
        std::cout << "✗ FAIL: " << result.error << "\n";
        return false;
    }

    const Event& ev = result.event;
    assert(ev.event_id    == "synthetic-42");
    assert(ev.final_class == "MALICIOUS");
    assert(ev.confidence  > 0.8f);
    assert(ev.features.size() == 62);
    assert(!ev.verdicts.empty());

    auto stats = loader.get_stats();
    assert(stats.parsed_ok == 1);
    assert(stats.hmac_failures == 0);

    std::cout << "✓ PASS\n";
    return true;
}

bool test_wrong_column_count() {
    std::cout << "[TEST] Rejects line with wrong column count... ";

    CsvEventLoaderConfig cfg;
    cfg.hmac_key_hex = TEST_KEY_HEX;
    cfg.verify_hmac  = false;
    CsvEventLoader loader(cfg);

    // Only 10 columns
    auto result = loader.parse("a,b,c,d,e,f,g,h,i,j", 1);

    assert(result.status == CsvParseStatus::WRONG_COLUMN_COUNT);
    assert(loader.get_stats().column_errors == 1);

    std::cout << "✓ PASS\n";
    return true;
}

bool test_hmac_mismatch() {
    std::cout << "[TEST] Rejects line with bad HMAC... ";

    CsvEventLoaderConfig cfg;
    cfg.hmac_key_hex = TEST_KEY_HEX;
    cfg.verify_hmac  = true;
    CsvEventLoader loader(cfg);

    std::string line = build_valid_line("bad-event", "MALICIOUS",
                                        0.9f, 0.21f, /*bad_hmac=*/true);
    auto result = loader.parse(line, 5);

    assert(result.status == CsvParseStatus::HMAC_MISMATCH);
    assert(loader.get_stats().hmac_failures == 1);

    std::cout << "✓ PASS\n";
    return true;
}

bool test_verify_hmac_disabled() {
    std::cout << "[TEST] verify_hmac=false skips HMAC check... ";

    CsvEventLoaderConfig cfg;
    cfg.hmac_key_hex = TEST_KEY_HEX;
    cfg.verify_hmac  = false;
    CsvEventLoader loader(cfg);

    // Build line with intentionally bad HMAC
    std::string line = build_valid_line("no-hmac-check", "BENIGN",
                                        0.1f, 0.08f, /*bad_hmac=*/true);
    auto result = loader.parse(line, 1);

    assert(result.status == CsvParseStatus::OK);
    assert(result.event.event_id == "no-hmac-check");

    std::cout << "✓ PASS\n";
    return true;
}

bool test_feature_vector_s2() {
    std::cout << "[TEST] Feature vector (S2, 62 cols) correctly populated... ";

    CsvEventLoaderConfig cfg;
    cfg.hmac_key_hex = TEST_KEY_HEX;
    cfg.verify_hmac  = true;
    CsvEventLoader loader(cfg);

    std::string line = build_valid_line();
    auto result = loader.parse(line, 1);

    assert(result.status == CsvParseStatus::OK);
    assert(result.event.features.size() == FEATURE_VECTOR_SIZE);

    // In build_valid_line, cols 14,21,28,35,42,49,56,63,70 (multiples of 7
    // within S2) were set to 1234, rest to 0.
    // Col 14 → features[0] should be 1234
    assert(result.event.features[0] == 1234.0f);
    // Col 15 → features[1] should be 0
    assert(result.event.features[1] == 0.0f);

    std::cout << "✓ PASS\n";
    return true;
}

bool test_verdicts_populated() {
    std::cout << "[TEST] EngineVerdicts populated from S1 + S4... ";

    CsvEventLoaderConfig cfg;
    cfg.hmac_key_hex = TEST_KEY_HEX;
    cfg.verify_hmac  = true;
    CsvEventLoader loader(cfg);

    std::string line = build_valid_line("ev-verdicts", "MALICIOUS", 0.9f, 0.21f);
    auto result = loader.parse(line, 1);

    assert(result.status == CsvParseStatus::OK);

    const auto& verdicts = result.event.verdicts;
    // Expect: fast-detector, ml-detector-l1 (from S1), l1-general (from S4)
    assert(verdicts.size() >= 2);

    // fast-detector verdict
    auto it_fast = std::find_if(verdicts.begin(), verdicts.end(),
        [](const EngineVerdict& v){ return v.engine_name == "fast-detector"; });
    assert(it_fast != verdicts.end());
    assert(it_fast->confidence > 0.8f);

    // ml-detector-l1 verdict
    auto it_ml = std::find_if(verdicts.begin(), verdicts.end(),
        [](const EngineVerdict& v){ return v.engine_name == "ml-detector-l1"; });
    assert(it_ml != verdicts.end());
    assert(it_ml->confidence < 0.5f);  // ml_score=0.21

    std::cout << "✓ PASS\n";
    return true;
}

bool test_stats_accumulate() {
    std::cout << "[TEST] Stats accumulate correctly across multiple parse() calls... ";

    CsvEventLoaderConfig cfg;
    cfg.hmac_key_hex = TEST_KEY_HEX;
    cfg.verify_hmac  = true;
    CsvEventLoader loader(cfg);

    // 3 valid, 1 bad HMAC, 1 wrong columns
    for (int i = 0; i < 3; ++i)
        loader.parse(build_valid_line("ev-" + std::to_string(i)), i + 1);

    loader.parse(build_valid_line("bad", "X", 0.9f, 0.2f, true), 10);  // HMAC fail
    loader.parse("short,line", 11);                                      // column fail

    auto s = loader.get_stats();
    assert(s.parsed_ok     == 3);
    assert(s.hmac_failures == 1);
    assert(s.column_errors == 1);

    loader.reset_stats();
    auto s2 = loader.get_stats();
    assert(s2.parsed_ok == 0);

    std::cout << "✓ PASS\n";
    return true;
}

bool test_partial_flag() {
    std::cout << "[TEST] is_partial flag set when S2 mostly zeros... ";

    CsvEventLoaderConfig cfg;
    cfg.hmac_key_hex = TEST_KEY_HEX;
    cfg.verify_hmac  = false;
    CsvEventLoader loader(cfg);

    // build_valid_line only sets ~9 non-zero values out of 62 — majority zeros
    // → is_partial should be true
    std::string line = build_valid_line();
    auto result = loader.parse(line, 1);

    assert(result.status == CsvParseStatus::OK);
    // 9 non-zero out of 62 → majority are zero → is_partial = true
    assert(result.event.is_partial == true);

    std::cout << "✓ PASS\n";
    return true;
}

// ============================================================================
// Main
// ============================================================================

int main() {
    std::cout << "\n=== CsvEventLoader Unit Tests (Day 67) ===\n\n";

    int passed = 0, total = 0;

    auto run = [&](bool (*fn)()) {
        if (fn()) ++passed;
        ++total;
    };

    run(test_construction_valid_key);
    run(test_construction_invalid_key_length);
    run(test_parse_valid_line);
    run(test_wrong_column_count);
    run(test_hmac_mismatch);
    run(test_verify_hmac_disabled);
    run(test_feature_vector_s2);
    run(test_verdicts_populated);
    run(test_stats_accumulate);
    run(test_partial_flag);

    std::cout << "\n=== Summary ===\n";
    std::cout << "Passed: " << passed << "/" << total << "\n";
    if (passed == total) {
        std::cout << "✓ All tests passed!\n";
        return 0;
    }
    std::cout << "✗ Some tests failed!\n";
    return 1;
}