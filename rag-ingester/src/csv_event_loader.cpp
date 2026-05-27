// csv_event_loader.cpp
// RAG Ingester - CsvEventLoader Implementation
// Day 67: Parse 127-column CSV lines + HMAC-SHA256 verification
// AUTHORS: Alonso Isidoro Roman + Claude (Anthropic)
// Via Appia Quality - Built to last

#include "csv_event_loader.hpp"

#include <openssl/hmac.h>
#include <openssl/evp.h>

#include <sstream>
#include <iomanip>
#include <stdexcept>
#include <cstring>
#include <cmath>
#include <algorithm>
#include <iostream>

namespace rag_ingester {

// ============================================================================
// Constructor
// ============================================================================

CsvEventLoader::CsvEventLoader(const CsvEventLoaderConfig& config)
    : config_(config)
{
    if (config_.verify_hmac) {
        if (config_.hmac_key_hex.size() != 64) {
            throw std::invalid_argument(
                "CsvEventLoader: hmac_key_hex must be 64 hex chars, got " +
                std::to_string(config_.hmac_key_hex.size()));
        }
        hmac_key_.reserve(32);
        for (size_t i = 0; i < 64; i += 2) {
            unsigned int byte = 0;
            if (std::sscanf(config_.hmac_key_hex.c_str() + i, "%02x", &byte) != 1) {
                throw std::invalid_argument(
                    "CsvEventLoader: invalid hex in hmac_key_hex at pos " +
                    std::to_string(i));
            }
            hmac_key_.push_back(static_cast<uint8_t>(byte));
        }
    }
}

// ============================================================================
// Public: parse()
// ============================================================================

CsvParseResult CsvEventLoader::parse(const std::string& line,
                                     uint64_t lineno) const
{
    CsvParseResult result;

    // 1. Split
    auto cols = split_csv(line);

    if (static_cast<int>(cols.size()) != CSV_TOTAL_COLUMNS) {
        ++stats_.column_errors;
        result.status = CsvParseStatus::WRONG_COLUMN_COUNT;
        result.error  = "Expected " + std::to_string(CSV_TOTAL_COLUMNS) +
                        " columns, got " + std::to_string(cols.size()) +
                        " (line " + std::to_string(lineno) + ")";
        return result;
    }

    // 2. HMAC verification
    if (config_.verify_hmac) {
        std::string content  = recompose_content(cols);
        std::string expected = compute_hmac(content);
        const std::string& actual = cols[CSV_HMAC_COLUMN];

        // Case-insensitive hex compare
        std::string actual_lower = actual;
        std::transform(actual_lower.begin(), actual_lower.end(),
                       actual_lower.begin(), ::tolower);

        if (actual_lower != expected) {
            ++stats_.hmac_failures;
            result.status = CsvParseStatus::HMAC_MISMATCH;
            result.error  = "HMAC mismatch at line " + std::to_string(lineno) +
                            ": expected=" + expected +
                            " got=" + actual_lower;
            return result;
        }
    }

    // 3. Build Event
    try {
        result.event  = build_event(cols, lineno);
        result.status = CsvParseStatus::OK;
        ++stats_.parsed_ok;
    } catch (const std::exception& e) {
        ++stats_.parse_errors;
        result.status = CsvParseStatus::PARSE_ERROR;
        result.error  = std::string("Parse error at line ") +
                        std::to_string(lineno) + ": " + e.what();
    }

    return result;
}

// ============================================================================
// Stats
// ============================================================================

CsvEventLoader::Stats CsvEventLoader::get_stats() const noexcept {
    return stats_;
}

void CsvEventLoader::reset_stats() noexcept {
    stats_ = Stats{};
}

// ============================================================================
// CSV splitting — handles quoted fields
// ============================================================================

std::vector<std::string> CsvEventLoader::split_csv(const std::string& line) {
    std::vector<std::string> cols;
    cols.reserve(CSV_TOTAL_COLUMNS);

    std::string field;
    field.reserve(64);
    bool in_quotes = false;

    for (size_t i = 0; i < line.size(); ++i) {
        char c = line[i];

        if (in_quotes) {
            if (c == '"') {
                // Peek: escaped double-quote?
                if (i + 1 < line.size() && line[i + 1] == '"') {
                    field += '"';
                    ++i;  // skip second quote
                } else {
                    in_quotes = false;
                }
            } else {
                field += c;
            }
        } else {
            if (c == '"') {
                in_quotes = true;
            } else if (c == ',') {
                cols.push_back(std::move(field));
                field.clear();
            } else {
                field += c;
            }
        }
    }
    cols.push_back(std::move(field));  // last field

    return cols;
}

// ============================================================================
// Recompose HMAC input (cols 0–125 joined with commas)
// Must match exactly what csv_event_writer.cpp computed HMAC over.
// ============================================================================

std::string CsvEventLoader::recompose_content(
    const std::vector<std::string>& cols)
{
    // The HMAC was computed over row_content = s1 + ',' + s2 + ',' + s3 + ',' + s4
    // which is exactly cols[0..125] joined by commas — but we need to reproduce
    // the exact quoting that the writer used.
    //
    // Since the writer used csv_string() (quoting only if comma/quote/newline
    // present), and split_csv() strips the quotes, we must re-quote if needed.
    // However, in practice IP addresses and numeric fields are never quoted, so
    // for the current schema we can rejoin the raw original bytes:
    // The simplest correct approach is to rejoin cols[0..CSV_HMAC_COLUMN-1]
    // from the ORIGINAL line, before splitting.
    //
    // But we don't have the original line here — we have the split cols.
    // To avoid this ambiguity, we use a conservative approach: rejoin as-is
    // (no re-quoting), which works because the CSV schema has no embedded commas
    // in any field value (IPs, hex strings, floats, labels like "MALICIOUS").

    std::string content;
    content.reserve(4096);

    for (int i = 0; i < CSV_HMAC_COLUMN; ++i) {
        if (i > 0) content += ',';
        content += cols[i];
    }
    return content;
}

// ============================================================================
// HMAC-SHA256 computation
// ============================================================================

std::string CsvEventLoader::compute_hmac(const std::string& content) const {
    unsigned char digest[EVP_MAX_MD_SIZE];
    unsigned int  digest_len = 0;

    HMAC(EVP_sha256(),
         hmac_key_.data(),
         static_cast<int>(hmac_key_.size()),
         reinterpret_cast<const unsigned char*>(content.data()),
         content.size(),
         digest,
         &digest_len);

    std::ostringstream ss;
    ss << std::hex << std::setfill('0');
    for (unsigned int i = 0; i < digest_len; ++i) {
        ss << std::setw(2) << static_cast<unsigned int>(digest[i]);
    }
    return ss.str();
}

// ============================================================================
// Build Event from columns
// ============================================================================

Event CsvEventLoader::build_event(const std::vector<std::string>& cols,
                                  uint64_t lineno)
{
    Event ev;
    ev.filepath = "(csv:" + std::to_string(lineno) + ")";

    parse_section1(cols, ev);
    parse_section2(cols, ev);
    parse_section4(cols, ev);

    return ev;
}

// ============================================================================
// Section 1 — Event metadata (cols 0–13)
//
// Col layout (from csv_event_writer.cpp build_section1):
//   0  timestamp_ns
//   1  event_id
//   2  src_ip
//   3  dst_ip
//   4  src_port
//   5  dst_port
//   6  protocol
//   7  final_class
//   8  confidence
//   9  threat_category
//  10  fast_score
//  11  ml_score
//  12  divergence
//  13  final_decision
// ============================================================================

void CsvEventLoader::parse_section1(const std::vector<std::string>& cols,
                                    Event& ev)
{
    // col 0: timestamp_ns
    try { ev.timestamp_ns = std::stoull(cols[0]); }
    catch (...) { ev.timestamp_ns = 0; }

    // col 1: event_id
    ev.event_id = cols[1];

    // col 2: src_ip
    ev.source_ip = cols.size() > 2 ? cols[2] : "";

    // col 3: dst_ip
    ev.dest_ip = cols.size() > 3 ? cols[3] : "";

    // timestamp_ms (convert ns → ms)
    ev.timestamp_ms = ev.timestamp_ns / 1000000;

    // col 7: final_class
    ev.final_class = cols[7];

    // col 8: confidence
    try { ev.confidence = std::stof(cols[8]); }
    catch (...) { ev.confidence = 0.0f; }

    // col 12: divergence → discrepancy_score
    try { ev.discrepancy_score = std::stof(cols[12]); }
    catch (...) { ev.discrepancy_score = 0.0f; }

    // col 13: final_decision
    ev.final_decision = cols[13];

    // Populate fast + ml verdicts from cols 10 & 11
    float fast_score = 0.0f;
    float ml_score   = 0.0f;
    try { fast_score = std::stof(cols[10]); } catch (...) {}
    try { ml_score   = std::stof(cols[11]); } catch (...) {}

    EngineVerdict fast_v;
    fast_v.engine_name     = "fast-detector";
    fast_v.classification  = fast_score >= 0.5f ? "Attack" : "Benign";
    fast_v.confidence      = fast_score;
    fast_v.timestamp_ns    = ev.timestamp_ns;
    ev.verdicts.push_back(std::move(fast_v));

    EngineVerdict ml_v;
    ml_v.engine_name    = "ml-detector-l1";
    ml_v.classification = ml_score >= 0.5f ? "Attack" : "Benign";
    ml_v.confidence     = ml_score;
    ml_v.timestamp_ns   = ev.timestamp_ns;
    ev.verdicts.push_back(std::move(ml_v));

    // source_detector: synthetic events have "synthetic-" prefix
    ev.source_detector = "ml-detector";
}

// ============================================================================
// Section 2 — Raw NetworkFeatures (cols 14–75, 62 features)
//
// Stored as Event::features (float vector, 62 elements).
// Index within features[] matches (col - 14).
// ============================================================================

void CsvEventLoader::parse_section2(const std::vector<std::string>& cols,
                                    Event& ev)
{
    ev.features.clear();
    ev.features.reserve(FEATURE_VECTOR_SIZE);

    int zeros = 0;
    for (int i = CSV_SECTION2_START; i < CSV_SECTION3_START; ++i) {
        float v = 0.0f;
        try {
            v = std::stof(cols[i]);
        } catch (...) {
            v = 0.0f;
        }
        ev.features.push_back(v);
        if (v == 0.0f) ++zeros;
    }

    // Mark as partial if more than 50% of features are zero
    // (indicates sniffer did not populate S2 for this event)
    ev.is_partial = (zeros > FEATURE_VECTOR_SIZE / 2);
}

// ============================================================================
// Section 4 — ML model decisions (cols 116–125)
//
// Col layout:
//  116  l1_pred    (string)
//  117  l1_conf    (float)
//  118  l2d_pred   (string) — Level 2 DDoS
//  119  l2d_conf   (float)
//  120  l2r_pred   (string) — Level 2 Ransomware
//  121  l2r_conf   (float)
//  122  l3t_pred   (string) — Level 3 Traffic
//  123  l3t_conf   (float)
//  124  l3i_pred   (string) — Level 3 Internal
//  125  l3i_conf   (float)
// ============================================================================

void CsvEventLoader::parse_section4(const std::vector<std::string>& cols,
                                    Event& ev)
{
    struct ModelEntry {
        const char* name;
        int pred_col;
        int conf_col;
    };

    static constexpr ModelEntry models[] = {
        {"l1-general",      116, 117},
        {"l2-ddos",         118, 119},
        {"l2-ransomware",   120, 121},
        {"l3-traffic",      122, 123},
        {"l3-internal",     124, 125},
    };

    for (const auto& m : models) {
        const std::string& pred = cols[m.pred_col];
        if (pred.empty()) continue;  // model did not run

        float conf = 0.0f;
        try { conf = std::stof(cols[m.conf_col]); } catch (...) {}

        EngineVerdict v;
        v.engine_name    = m.name;
        v.classification = pred;
        v.confidence     = conf;
        v.timestamp_ns   = ev.timestamp_ns;
        ev.verdicts.push_back(std::move(v));
    }

    // Override final_class with L1 prediction if available and richer
    // (col 7 has the aggregate; col 116 has the ML-specific label)
    if (!cols[116].empty()) {
        // Keep the aggregate final_class from S1 but enrich if empty
        if (ev.final_class.empty()) {
            ev.final_class = cols[116];
        }
        // Use L1 confidence if S1 confidence was zero
        if (ev.confidence == 0.0f) {
            try { ev.confidence = std::stof(cols[117]); } catch (...) {}
        }
    }
}

} // namespace rag_ingester