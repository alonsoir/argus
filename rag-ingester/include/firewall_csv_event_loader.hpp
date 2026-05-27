// firewall_csv_event_loader.hpp
// Day 69 — Parser for firewall-acl-agent CSV output
//
// Format (7 columns, no header row):
//   timestamp_ms, src_ip, dst_ip, classification, action, score, hmac
//   1771404108582,111.182.236.62,58.122.96.132,RANSOMWARE,BLOCKED,0.9586,c3ddc9c8...
//
// Responsibility: parse + HMAC validate + provide FirewallEvent struct
// Does NOT embed into FAISS — rag-ingester main.cpp uses this to UPDATE MetadataDB
//
// AUTHORS: Alonso Isidoro Roman + Claude (Anthropic)
// DATE: Day 69

#pragma once

#include <string>
#include <optional>
#include <atomic>
#include <cstdint>

namespace ml_defender {

struct FirewallEvent {
    uint64_t    timestamp_ms    = 0;
    std::string source_ip;
    std::string dest_ip;
    std::string classification;   // RANSOMWARE | DDOS | BENIGN ...
    std::string action;           // BLOCKED | ALLOWED | DROPPED
    float       score            = 0.0f;
    std::string hmac_hex;         // raw field from CSV, validated internally
    std::string trace_id;         // empty until trace_id propagation is wired (Day 7z)
};

enum class FirewallParseResult {
    OK,
    MALFORMED,       // wrong number of columns or parse error
    HMAC_FAILURE,    // HMAC present but does not match
    EMPTY_LINE       // blank or comment line — skip silently
};

class FirewallCsvEventLoader {
public:
    // hmac_key_hex: empty string disables HMAC verification
    explicit FirewallCsvEventLoader(const std::string& hmac_key_hex = "");

    // Parse a single CSV line. Stateless — safe to call from any thread.
    FirewallParseResult parse(const std::string& line, FirewallEvent& out) const;

    // Stats
    uint64_t parsed_ok()     const;
    uint64_t hmac_failures() const;
    uint64_t parse_errors()  const;

private:
    // Declaration order must match constructor initializer list order
    std::string hmac_key_hex_;
    bool        hmac_enabled_;

    mutable std::atomic<uint64_t> parsed_ok_     {0};
    mutable std::atomic<uint64_t> hmac_failures_ {0};
    mutable std::atomic<uint64_t> parse_errors_  {0};

    bool verify_hmac(const std::string& payload,
                     const std::string& expected_hmac) const;

    static constexpr int EXPECTED_COLS = 7;
};

} // namespace ml_defender