// test_trace_id.cpp
// ML Defender — RAG Ingester
// Day 72: Unit tests for trace_id_generator
//
// Compile standalone:
//   g++ -std=c++20 -I../include -o test_trace_id test_trace_id.cpp -lssl -lcrypto -lspdlog -lfmt
//
// AUTHORS: Alonso Isidoro Roman + Claude (Anthropic) + Qwen (Alibaba)
// Via Appia Quality — Built to last

#include "utils/trace_id_generator.hpp"

#include <iostream>
#include <cassert>
#include <string>

using namespace rag_ingester;

// ============================================================================
// Test helpers
// ============================================================================

static int tests_run    = 0;
static int tests_passed = 0;

#define PASS(name) do { \
    ++tests_run; ++tests_passed; \
    std::cout << "  ✅ PASS: " << (name) << "\n"; \
} while(0)

#define FAIL(name, msg) do { \
    ++tests_run; \
    std::cout << "  ❌ FAIL: " << (name) << " — " << (msg) << "\n"; \
} while(0)

#define CHECK(name, condition) do { \
    if (condition) PASS(name); \
    else FAIL(name, #condition); \
} while(0)

// ============================================================================
// Test 1 — Determinism
// ============================================================================

void test_deterministic() {
    std::cout << "\n[1] Determinism\n";
    TraceIdPolicy policy;

    auto id1 = generate_trace_id("192.168.1.100", "10.0.0.5", "ransomware", 1740000000000ULL, "", policy);
    auto id2 = generate_trace_id("192.168.1.100", "10.0.0.5", "ransomware", 1740000000000ULL, "", policy);
    auto id3 = generate_trace_id("192.168.1.100", "10.0.0.5", "ransomware", 1740000000000ULL, "", policy);

    CHECK("identical calls produce identical trace_id", id1 == id2 && id2 == id3);
    CHECK("trace_id length is 32 hex chars", id1.size() == 32);

    bool all_hex = true;
    for (char c : id1) {
        if (!std::isxdigit(static_cast<unsigned char>(c))) { all_hex = false; break; }
    }
    CHECK("trace_id contains only hex chars", all_hex);
}

// ============================================================================
// Test 2 — Canonicalization
// ============================================================================

void test_canonicalization() {
    std::cout << "\n[2] Canonicalization\n";
    TraceIdPolicy policy;

    const uint64_t ts  = 1740000000000ULL;
    const std::string src = "10.0.1.50";
    const std::string dst = "192.168.0.1";

    auto id_upper  = generate_trace_id(src, dst, "SSH_BRUTE",      ts, "", policy);
    auto id_lower  = generate_trace_id(src, dst, "ssh_brute",      ts, "", policy);
    auto id_hyphen = generate_trace_id(src, dst, "ssh-brute",      ts, "", policy);
    auto id_alias1 = generate_trace_id(src, dst, "ssh_bruteforce", ts, "", policy);
    auto id_alias2 = generate_trace_id(src, dst, "SSH_BRUTEFORCE", ts, "", policy);

    CHECK("SSH_BRUTE == ssh_brute",      id_upper  == id_lower);
    CHECK("ssh-brute == ssh_brute",      id_hyphen == id_lower);
    CHECK("ssh_bruteforce → ssh_brute",  id_alias1 == id_lower);
    CHECK("SSH_BRUTEFORCE → ssh_brute",  id_alias2 == id_lower);

    auto ddos1 = generate_trace_id(src, dst, "ddos",     ts, "", policy);
    auto ddos2 = generate_trace_id(src, dst, "ddos_syn", ts, "", policy);
    auto ddos3 = generate_trace_id(src, dst, "DDOS_SYN", ts, "", policy);
    auto ddos4 = generate_trace_id(src, dst, "flood",    ts, "", policy);

    CHECK("ddos_syn → ddos", ddos2 == ddos1);
    CHECK("DDOS_SYN → ddos", ddos3 == ddos1);
    CHECK("flood → ddos",    ddos4 == ddos1);

    CHECK("canonicalize uppercase",  canonicalize_attack_type("RANSOMWARE") == "ransomware");
    CHECK("canonicalize hyphen",     canonicalize_attack_type("port-scan")  == "scan");
    CHECK("canonicalize mapping",    canonicalize_attack_type("port_scan")  == "scan");
    CHECK("canonicalize trim",       canonicalize_attack_type("  ddos  ")   == "ddos");
}

// ============================================================================
// Test 3 — Window sensitivity
// ============================================================================

void test_window_sensitivity() {
    std::cout << "\n[3] Window sensitivity\n";
    TraceIdPolicy policy;

    const std::string src = "172.16.0.10";
    const std::string dst = "8.8.8.8";

    // ransomware window = 60000ms
    // Timestamps must be bucket-aligned: start at exact multiple of window_ms (60000)
    // so that [start, start+59999] are guaranteed to be in the same bucket.
    // 60000 * 1000 = 60000000 → bucket 1000; +59999 → bucket 1000; +60000 → bucket 1001
    uint64_t ts_bucket0_start = 60000000ULL;
    uint64_t ts_bucket0_end   = 60000000ULL + 59999;
    uint64_t ts_bucket1       = 60000000ULL + 60000;

    auto id_start = generate_trace_id(src, dst, "ransomware", ts_bucket0_start, "", policy);
    auto id_end   = generate_trace_id(src, dst, "ransomware", ts_bucket0_end,   "", policy);
    auto id_next  = generate_trace_id(src, dst, "ransomware", ts_bucket1,       "", policy);

    CHECK("same bucket → same trace_id",           id_start == id_end);
    CHECK("different bucket → different trace_id", id_start != id_next);

    // DDoS window = 10000ms
    uint64_t ddos_same  = 5000000ULL;
    uint64_t ddos_same2 = 5000000ULL + 9999;
    uint64_t ddos_diff  = 5000000ULL + 10000;

    auto ddos1 = generate_trace_id(src, dst, "ddos", ddos_same,  "", policy);
    auto ddos2 = generate_trace_id(src, dst, "ddos", ddos_same2, "", policy);
    auto ddos3 = generate_trace_id(src, dst, "ddos", ddos_diff,  "", policy);

    CHECK("DDoS: same 10s bucket → same trace_id",       ddos1 == ddos2);
    CHECK("DDoS: different 10s bucket → different trace_id", ddos1 != ddos3);

    auto ransomware_id = generate_trace_id(src, dst, "ransomware", ts_bucket0_start, "", policy);
    auto ddos_id       = generate_trace_id(src, dst, "ddos",       ts_bucket0_start, "", policy);
    CHECK("different attack_type → different trace_id", ransomware_id != ddos_id);
}

// ============================================================================
// Test 4 — Collision resistance
// ============================================================================

void test_collision_resistance() {
    std::cout << "\n[4] Collision resistance\n";
    TraceIdPolicy policy;

    const uint64_t ts = 1740000030000ULL;

    auto id_src1 = generate_trace_id("192.168.1.100", "10.0.0.5", "ransomware", ts, "", policy);
    auto id_src2 = generate_trace_id("192.168.1.101", "10.0.0.5", "ransomware", ts, "", policy);
    CHECK("different src_ip → different trace_id", id_src1 != id_src2);

    auto id_dst1 = generate_trace_id("192.168.1.100", "10.0.0.5", "ransomware", ts, "", policy);
    auto id_dst2 = generate_trace_id("192.168.1.100", "10.0.0.6", "ransomware", ts, "", policy);
    CHECK("different dst_ip → different trace_id", id_dst1 != id_dst2);

    // Separator prevents concatenation collisions
    auto id_sep1 = generate_trace_id("10.0.0.1",  "2.0.0.0", "ransomware", ts, "", policy);
    auto id_sep2 = generate_trace_id("10.0.0.12", "0.0.0.0", "ransomware", ts, "", policy);
    CHECK("separator prevents concatenation collision", id_sep1 != id_sep2);

    // Asymmetric by design (src != dst)
    auto id_fwd = generate_trace_id("192.168.1.100", "10.0.0.5", "ransomware", ts, "", policy);
    auto id_rev = generate_trace_id("10.0.0.5", "192.168.1.100", "ransomware", ts, "", policy);
    CHECK("src↔dst swap → different trace_id (asymmetric)", id_fwd != id_rev);
}

// ============================================================================
// Test 5 — Edge cases: empty fields and sentinels
// ============================================================================

void test_edge_cases() {
    std::cout << "\n[5] Edge cases — empty fields and sentinels\n";
    TraceIdPolicy policy;

    const uint64_t ts = 1740000000000ULL;

    // Empty src_ip → "0.0.0.0" sentinel (warn logged)
    auto meta_empty_src = generate_trace_id_with_metadata(
        "", "10.0.0.5", "ransomware", ts, "test-event-001", policy);
    CHECK("empty src_ip → sentinel 0.0.0.0",     meta_empty_src.effective_src_ip == "0.0.0.0");
    CHECK("empty src_ip → fallback_applied=true", meta_empty_src.fallback_applied);
    CHECK("trace_id still valid (32 chars)",       meta_empty_src.trace_id.size() == 32);

    // Empty dst_ip → "0.0.0.0" sentinel
    auto meta_empty_dst = generate_trace_id_with_metadata(
        "192.168.1.1", "", "ransomware", ts, "test-event-002", policy);
    CHECK("empty dst_ip → sentinel 0.0.0.0",     meta_empty_dst.effective_dst_ip == "0.0.0.0");
    CHECK("empty dst_ip → fallback_applied=true", meta_empty_dst.fallback_applied);

    // Whitespace-only IP → "0.0.0.0" sentinel
    auto meta_ws_ip = generate_trace_id_with_metadata(
        "   ", "10.0.0.5", "ddos", ts, "test-event-003", policy);
    CHECK("whitespace src_ip → sentinel 0.0.0.0", meta_ws_ip.effective_src_ip == "0.0.0.0");

    // Empty attack_type → "unknown" sentinel (warn logged)
    auto meta_empty_attack = generate_trace_id_with_metadata(
        "192.168.1.1", "10.0.0.5", "", ts, "test-event-004", policy);
    CHECK("empty attack_type → canonical 'unknown'",  meta_empty_attack.canonical_attack_type == "unknown");
    CHECK("empty attack_type → fallback_applied=true", meta_empty_attack.fallback_applied);
    CHECK("trace_id still valid (32 chars)",            meta_empty_attack.trace_id.size() == 32);

    // "MALICIOUS" generic label → "unknown"
    auto meta_malicious = generate_trace_id_with_metadata(
        "192.168.1.1", "10.0.0.5", "MALICIOUS", ts, "test-event-005", policy);
    CHECK("'MALICIOUS' → canonical 'unknown'",        meta_malicious.canonical_attack_type == "unknown");
    CHECK("'MALICIOUS' → fallback_applied=true",      meta_malicious.fallback_applied);

    // Both IPs empty → both sentinels, trace_id still deterministic
    auto meta_both_empty1 = generate_trace_id_with_metadata(
        "", "", "ddos", ts, "test-event-006a", policy);
    auto meta_both_empty2 = generate_trace_id_with_metadata(
        "", "", "ddos", ts, "test-event-006b", policy);
    CHECK("both IPs empty → deterministic trace_id", meta_both_empty1.trace_id == meta_both_empty2.trace_id);

    // Sentinel IPs distinct from real "0.0.0.0" input
    // (they produce the same hash — this is acceptable and documented)
    auto meta_real_zero = generate_trace_id_with_metadata(
        "0.0.0.0", "10.0.0.5", "ddos", ts, "test-event-007", policy);
    auto meta_sent_zero = generate_trace_id_with_metadata(
        "", "10.0.0.5", "ddos", ts, "test-event-008", policy);
    // These ARE equal — documented limitation of using 0.0.0.0 as sentinel.
    // The warn log in the empty case makes the distinction auditable.
    CHECK("empty src == '0.0.0.0' src produces same hash (documented)",
          meta_real_zero.trace_id == meta_sent_zero.trace_id);
    CHECK("empty case has fallback_applied=true, real case does not",
          meta_sent_zero.fallback_applied && !meta_real_zero.fallback_applied);
}

// ============================================================================
// Test 6 — TraceIdMetadata fields
// ============================================================================

void test_metadata_fields() {
    std::cout << "\n[6] TraceIdMetadata fields\n";
    TraceIdPolicy policy;

    auto meta = generate_trace_id_with_metadata(
        "10.0.0.1", "192.168.1.1", "SSH_BRUTE", 1740000015000ULL, "ev-001", policy);

    CHECK("trace_id length 32",                  meta.trace_id.size() == 32);
    CHECK("canonical_attack_type normalized",    meta.canonical_attack_type == "ssh_brute");
    CHECK("effective_src_ip preserved",          meta.effective_src_ip == "10.0.0.1");
    CHECK("effective_dst_ip preserved",          meta.effective_dst_ip == "192.168.1.1");
    CHECK("window_ms_used matches policy",       meta.window_ms_used == 30000);
    CHECK("policy_version == 1",                 meta.policy_version == 1);
    CHECK("no fallback for valid input",         !meta.fallback_applied);

    auto meta_ddos = generate_trace_id_with_metadata(
        "10.0.0.1", "192.168.1.1", "ddos_syn", 1740000015000ULL, "ev-002", policy);

    CHECK("DDoS canonical_attack_type",   meta_ddos.canonical_attack_type == "ddos");
    CHECK("DDoS window_ms_used == 10000", meta_ddos.window_ms_used == 10000);
}

// ============================================================================
// main
// ============================================================================

int main() {
    std::cout << "═══════════════════════════════════════════════════════\n";
    std::cout << "  ML Defender — trace_id unit tests (Day 72)\n";
    std::cout << "═══════════════════════════════════════════════════════\n";
    std::cout << "  NOTE: warn logs for sentinel substitutions are expected\n";
    std::cout << "        in test 5 — they confirm the audit trail works.\n";

    test_deterministic();
    test_canonicalization();
    test_window_sensitivity();
    test_collision_resistance();
    test_edge_cases();
    test_metadata_fields();

    std::cout << "\n═══════════════════════════════════════════════════════\n";
    std::cout << "  Results: " << tests_passed << "/" << tests_run << " passed\n";

    if (tests_passed == tests_run) {
        std::cout << "  ✅ ALL TESTS PASS\n";
    } else {
        std::cout << "  ❌ " << (tests_run - tests_passed) << " FAILED\n";
    }
    std::cout << "═══════════════════════════════════════════════════════\n";

    return (tests_passed == tests_run) ? 0 : 1;
}