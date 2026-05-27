#pragma once

// trace_id_generator.hpp
// ML Defender — RAG Ingester
// Day 72: Deterministic multi-source event correlation
//
// DESIGN PRINCIPLE (Via Appia Quality):
//   trace_id = derived field, computed post-processing in rag-ingester.
//   Zero-coordination: ml-detector and firewall-acl-agent independently
//   generate identical trace_ids for the same incident without any shared state.
//   O(1), stateless, reproducible after restart.
//
// FORMULA:
//   bucket   = floor(timestamp_ms / window_ms)
//   trace_id = sha256_prefix_16bytes(src_ip | "|" | dst_ip | "|" | attack_type | "|" | bucket)
//
// CANONICALIZATION (CRITICAL for traceability):
//   All string fields are normalized before hashing.
//   Any variation in casing or separators silently breaks correlation.
//   Empty fields use explicit sentinels — logged as warnings so the operator
//   knows a fallback was applied.
//
//   Sentinel values:
//     source_ip / dest_ip empty → "0.0.0.0"  (logged as warn)
//     attack_type empty/unknown → "unknown"   (logged as warn)
//
//   NOTE on "0.0.0.0": semantically this means "universal external address"
//   in network terms, not "unknown". We accept this imprecision as the best
//   available sentinel. The warn log makes the fallback explicit and auditable.
//
// FOR THE PAPER:
//   "Correlation as a post-processing concern — multi-source event correlation
//    in real time, O(1), zero-coordination. Emergent property of the design,
//    not over-engineered distributed systems machinery."
//
// AUTHORS: Alonso Isidoro Roman + Claude (Anthropic) + Qwen (Alibaba) + Council of Wise
// Via Appia Quality — Built to last

#include <string>
#include <string_view>
#include <cstdint>
#include <algorithm>
#include <unordered_map>
#include <openssl/sha.h>
#include <spdlog/spdlog.h>

namespace rag_ingester {

// ============================================================================
// TraceIdPolicy — versioned window configuration per attack_type
//
// IMPORTANT: if you change window_ms values in production, historical
// trace_ids will recompute differently. Always increment policy_version
// and store window_ms_used per event for full reproducibility.
// ============================================================================

struct TraceIdPolicy {
    uint32_t version = 1;

    std::unordered_map<std::string, uint32_t> windows_ms = {
        {"ransomware", 60000},   // 1 minute  — slow-moving, broad window
        {"ddos",       10000},   // 10 seconds — high-rate, tight window
        {"ssh_brute",  30000},   // 30 seconds
        {"scan",       60000},   // 1 minute
        {"unknown",    60000},   // fallback for unrecognized/empty attack types
        {"default",    60000}    // explicit default
    };

    uint32_t get_window_ms(const std::string& canonical_attack_type) const {
        auto it = windows_ms.find(canonical_attack_type);
        if (it != windows_ms.end()) return it->second;
        auto def = windows_ms.find("default");
        return def != windows_ms.end() ? def->second : 60000;
    }
};

// ============================================================================
// normalize_ip()
//
// Strips whitespace. Returns "0.0.0.0" for empty or whitespace-only strings.
// Logs a warning when the fallback is applied so the operator has visibility.
//
// NOTE: "0.0.0.0" is a network sentinel meaning "universal external address",
// not literally "unknown IP". We use it as the best available placeholder.
// The warn log is the audit trail — do not suppress it.
// ============================================================================

inline std::string normalize_ip(const std::string& raw_ip, const std::string& event_id = "") {
    std::string result = raw_ip;

    // Trim leading/trailing whitespace
    const auto first = result.find_first_not_of(" \t\n\r\f\v");
    if (first == std::string::npos) {
        // Empty or whitespace-only
        spdlog::warn("[trace_id] empty IP field — using sentinel 0.0.0.0 (event={})", event_id);
        return "0.0.0.0";
    }
    result.erase(0, first);
    result.erase(result.find_last_not_of(" \t\n\r\f\v") + 1);

    return result;
}

// ============================================================================
// canonicalize_attack_type()
//
// Normalizes attack type strings before hashing. CRITICAL for traceability:
// "SSH_BRUTE" / "ssh_brute" / "ssh-brute" must produce the same trace_id.
//
// Steps: lowercase → replace '-' with '_' → trim → mapping table
// Returns "unknown" for empty/unrecognized types, with a warn log.
// ============================================================================

inline std::string canonicalize_attack_type(std::string_view raw,
                                             const std::string& event_id = "") {
    std::string result(raw);

    // 1. Lowercase
    std::transform(result.begin(), result.end(), result.begin(),
                   [](unsigned char c) { return static_cast<char>(std::tolower(c)); });

    // 2. Replace hyphens with underscores
    std::replace(result.begin(), result.end(), '-', '_');

    // 3. Trim leading/trailing whitespace
    const auto first = result.find_first_not_of(" \t\n\r\f\v");
    if (first == std::string::npos) {
        spdlog::warn("[trace_id] empty attack_type — using sentinel 'unknown' (event={})",
                     event_id);
        return "unknown";
    }
    result.erase(0, first);
    result.erase(result.find_last_not_of(" \t\n\r\f\v") + 1);

    // 4. Fixed mapping for known variants
    // Extend this table as new attack types appear in datasets.
    // All keys must already be lowercase with underscores (post steps 1-2).
    static const std::unordered_map<std::string, std::string> mappings = {
        // SSH brute force variants
        {"ssh_bruteforce",      "ssh_brute"},
        {"ssh_attack",          "ssh_brute"},
        {"brute_force",         "ssh_brute"},
        {"bruteforce",          "ssh_brute"},
        // DDoS variants
        {"ddos_syn",            "ddos"},
        {"ddos_udp",            "ddos"},
        {"flood",               "ddos"},
        {"syn_flood",           "ddos"},
        {"dos",                 "ddos"},
        // Ransomware variants
        {"ransomware_crypto",   "ransomware"},
        {"crypto_ransomware",   "ransomware"},
        // Scan variants
        {"port_scan",           "scan"},
        {"network_scan",        "scan"},
        {"portscan",            "scan"},
        // Generic labels — no specific window, use "unknown" bucket
        {"malicious",           "unknown"},
        {"attack",              "unknown"},
        // Benign — should not generate meaningful trace_id but handled gracefully
        {"benign",              "benign"},
        {"normal",              "benign"},
    };

    auto it = mappings.find(result);
    if (it != mappings.end()) {
        return it->second;
    }

    // Unrecognized type — keep as-is (lowercase+underscore normalized) but log it
    // so the operator can add it to the mapping table if needed.
    if (result == "unknown") {
        spdlog::warn("[trace_id] attack_type is 'unknown' — trace correlation will be broad "
                     "(event={})", event_id);
    } else {
        spdlog::debug("[trace_id] unrecognized attack_type='{}' — using as-is (event={})",
                      result, event_id);
    }

    return result;
}

// ============================================================================
// TraceIdMetadata — full audit trail per event
// Store window_ms_used + policy_version in MetadataDB for reproducibility.
// If any field used a sentinel, fallback_applied will be true.
// ============================================================================

struct TraceIdMetadata {
    std::string trace_id;               // 32 hex chars (128 bits of SHA256)
    std::string canonical_attack_type;  // after canonicalization
    std::string effective_src_ip;       // after normalization (may be "0.0.0.0")
    std::string effective_dst_ip;       // after normalization (may be "0.0.0.0")
    uint32_t    window_ms_used;         // window used to compute bucket
    uint32_t    policy_version;         // TraceIdPolicy::version at compute time
    bool        fallback_applied;       // true if any sentinel was substituted
};

// ============================================================================
// generate_trace_id_with_metadata() — main entry point
//
// All normalization and canonicalization happens here, before hashing.
// Fallback sentinels are logged at warn level. The resulting trace_id is
// always valid and deterministic — even for partial data — but the operator
// is notified when a sentinel was used.
//
// Field order in hash input is FIXED and must never change without
// incrementing policy_version, as it would silently break correlation of
// historical events.
//
// Format: "src_ip|dst_ip|attack_type|bucket"
// Separator "|" prevents concatenation collisions:
//   "10.0.0.1" + "2.0.0.0" vs "10.0.0.12" + "0.0.0.0" are distinct.
// ============================================================================

inline TraceIdMetadata generate_trace_id_with_metadata(
    const std::string&   src_ip,
    const std::string&   dst_ip,
    const std::string&   raw_attack_type,
    uint64_t             timestamp_ms,
    const std::string&   event_id = "",
    const TraceIdPolicy& policy   = TraceIdPolicy{})
{
    bool fallback = false;

    // 1. Normalize IPs — sentinels logged inside normalize_ip()
    // Fallback is set only when the ORIGINAL input was empty/whitespace,
    // NOT when the normalized result happens to be "0.0.0.0" (which is a
    // valid real IP). Checking the result would incorrectly flag real
    // "0.0.0.0" inputs (e.g., wildcard listeners) as fallbacks.
    auto is_empty_or_ws = [](const std::string& s) -> bool {
        if (s.empty()) return true;
        for (unsigned char c : s) if (!std::isspace(c)) return false;
        return true;
    };
    const std::string eff_src = normalize_ip(src_ip, event_id);
    const std::string eff_dst = normalize_ip(dst_ip, event_id);
    if (is_empty_or_ws(src_ip)) fallback = true;
    if (is_empty_or_ws(dst_ip)) fallback = true;

    // 2. Canonicalize attack_type — sentinel/warn logged inside canonicalize_attack_type()
    const std::string attack_type = canonicalize_attack_type(raw_attack_type, event_id);
    if (attack_type == "unknown") fallback = true;

    // 3. Get window for this attack_type
    const uint32_t window_ms = policy.get_window_ms(attack_type);

    // 4. Compute temporal bucket
    const uint64_t bucket = (window_ms > 0) ? (timestamp_ms / window_ms) : 0;

    // 5. Build hash input — fixed field order with "|" separator
    const std::string input =
        eff_src + "|" + eff_dst + "|" + attack_type + "|" + std::to_string(bucket);

    // 6. SHA256
    unsigned char hash[SHA256_DIGEST_LENGTH];
    SHA256(reinterpret_cast<const unsigned char*>(input.data()),
           input.size(),
           hash);

    // 7. Hex-encode first 16 bytes (128 bits) → 32 hex chars
    //    Collision probability for 10^12 events: ~1.5×10^-15 (Birthday paradox)
    char hex[33];
    hex[32] = '\0';
    for (int i = 0; i < 16; ++i) {
        snprintf(hex + i * 2, 3, "%02x", static_cast<unsigned int>(hash[i]));
    }

    return TraceIdMetadata{
        .trace_id              = std::string(hex, 32),
        .canonical_attack_type = attack_type,
        .effective_src_ip      = eff_src,
        .effective_dst_ip      = eff_dst,
        .window_ms_used        = window_ms,
        .policy_version        = policy.version,
        .fallback_applied      = fallback
    };
}

// ============================================================================
// generate_trace_id() — convenience overload (no metadata needed)
// ============================================================================

inline std::string generate_trace_id(
    const std::string&   src_ip,
    const std::string&   dst_ip,
    const std::string&   raw_attack_type,
    uint64_t             timestamp_ms,
    const std::string&   event_id = "",
    const TraceIdPolicy& policy   = TraceIdPolicy{})
{
    return generate_trace_id_with_metadata(
        src_ip, dst_ip, raw_attack_type, timestamp_ms, event_id, policy).trace_id;
}

} // namespace rag_ingester