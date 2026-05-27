// csv_event_writer.hpp
// ML Defender - CSV Event Writer for RAG Ingester pipeline
// Day 63: Initial implementation
// Day 64: Full schema — 127 columns covering all pipeline stages
// Authors: Alonso Isidoro Roman + Claude (Anthropic)
//
// CONTRACT: See FEATURE_SCHEMA.md for complete column definitions.
// CSV_SCHEMA_VERSION 1.0 — any column order change is a BREAKING CHANGE.
//
// SCHEMA SUMMARY (127 columns, no header row):
//   Section 1 —  14 cols (0–13)   Event metadata
//   Section 2 —  62 cols (14–75)  Raw NetworkFeatures from sniffer
//   Section 3 —  40 cols (76–115) Embedded detector features (ml-detector)
//   Section 4 —  10 cols (116–125) ML model decisions (prediction + confidence)
//   Section 5 —   1 col  (126)    HMAC-SHA256 integrity
//
// RATIONALE FOR NO ENCRYPTION:
//   CSV files are protected by per-row HMAC (integrity).
//   ChaCha20 encryption ties file lifetime to key rotation — files older
//   than the rotation window become permanently unreadable.
//   For RAG historical analysis we need multi-year durability.
//   Enterprise version will add at-rest encryption transparently.

#pragma once

#include <string>
#include <vector>
#include <fstream>
#include <mutex>
#include <atomic>
#include <memory>
#include <chrono>

#include <spdlog/spdlog.h>
#include <network_security.pb.h>

namespace ml_defender {

// ============================================================================
// Schema version — bump on any breaking change to column layout
// ============================================================================
static constexpr const char* CSV_SCHEMA_VERSION = "1.0";

// ============================================================================
// Configuration
// ============================================================================

struct CsvEventWriterConfig {
    std::string base_dir;           // e.g. /vagrant/logs/ml-detector/events
    std::string hmac_key_hex;       // 64-char hex key from etcd /secrets/ml-detector
    size_t max_events_per_file = 10000;  // rotate after N events
    float min_score_threshold  = 0.5f;  // only write events above this score
};

// ============================================================================
// CsvEventWriter
// ============================================================================

class CsvEventWriter {
public:
    explicit CsvEventWriter(const CsvEventWriterConfig& config,
                            std::shared_ptr<spdlog::logger> logger);
    ~CsvEventWriter();

    // Non-copyable
    CsvEventWriter(const CsvEventWriter&) = delete;
    CsvEventWriter& operator=(const CsvEventWriter&) = delete;

    /**
     * @brief Write one detection event as a 127-column CSV row.
     *
     * Reads all sections from the NetworkSecurityEvent proto:
     *   S1 — metadata fields
     *   S2 — NetworkFeatures scalars (sniffer output, passed through)
     *   S3 — Embedded detector sub-messages (ml-detector computed)
     *   S4 — TricapaMLAnalysis predictions (which model, what decision)
     *   S5 — HMAC-SHA256 over cols 0–125
     *
     * Events with overall_threat_score < min_score_threshold are skipped.
     * Thread-safe (mutex-protected).
     *
     * @param event  Complete NetworkSecurityEvent (post-classification)
     * @return true if written, false if filtered or error
     */
    bool write_event(const protobuf::NetworkSecurityEvent& event);

    void flush();

    struct Stats {
        uint64_t events_written;
        uint64_t events_skipped;
        uint64_t rows_failed;
        std::string current_file;
    };
    Stats get_stats() const noexcept;

private:
    // -------------------------------------------------------------------------
    // Section builders — each returns the columns for its section as a
    // comma-separated string fragment (no leading/trailing comma).
    // -------------------------------------------------------------------------

    /** Section 1: 14 metadata columns (0–13). */
    std::string build_section1(const protobuf::NetworkSecurityEvent& event) const;

    /** Section 2: 62 raw NetworkFeatures columns (14–75).
     *  All values read directly from event.network_features().
     *  Zero-fills any field not populated by the sniffer. */
    std::string build_section2(const protobuf::NetworkSecurityEvent& event) const;

    /** Section 3: 40 embedded detector feature columns (76–115).
     *  Reads DDoSFeatures, RansomwareEmbeddedFeatures, TrafficFeatures,
     *  InternalFeatures from network_features sub-messages.
     *  Zero-fills if the sub-message is absent. */
    std::string build_section3(const protobuf::NetworkSecurityEvent& event) const;

    /** Section 4: 10 ML model decision columns (116–125).
     *  Reads TricapaMLAnalysis level1/level2/level3 predictions.
     *  Empty string + 0.0 if a detector did not fire. */
    std::string build_section4(const protobuf::NetworkSecurityEvent& event) const;

    /**
     * @brief Compute HMAC-SHA256 over the complete row (sections 1–4).
     * @param row_content Comma-joined string of cols 0–125 (no trailing comma)
     * @return 64-char lowercase hex string
     */
    std::string compute_hmac(const std::string& row_content) const;

    // -------------------------------------------------------------------------
    // Helpers
    // -------------------------------------------------------------------------

    /** Format a float with 6 decimal places. Returns "0.000000" on NaN/Inf. */
    static std::string fmt_float(float v);
    static std::string fmt_double(double v);

    /** Quote a string field for CSV: wraps in double-quotes if it contains
     *  comma, double-quote, or newline. Escapes embedded double-quotes. */
    static std::string csv_string(const std::string& s);

    // File management
    void ensure_open();
    void rotate_if_needed();
    void rotate_locked();
    std::string get_date_string() const;
    std::string get_file_path(const std::string& date) const;

    // -------------------------------------------------------------------------
    // State
    // -------------------------------------------------------------------------
    CsvEventWriterConfig config_;
    std::shared_ptr<spdlog::logger> logger_;

    // HMAC key as raw bytes (decoded from hex at construction, 32 bytes)
    std::vector<uint8_t> hmac_key_;

    mutable std::mutex mutex_;
    std::ofstream current_file_;
    std::string current_date_;
    std::string current_file_path_;

    std::atomic<uint64_t> events_written_{0};
    std::atomic<uint64_t> events_skipped_{0};
    std::atomic<uint64_t> rows_failed_{0};
    std::atomic<size_t>   events_in_current_file_{0};
};

// ============================================================================
// Column count constants — used by CsvEventLoader in rag-ingester to
// validate rows at parse time, and by tests to assert schema correctness.
//
// Schema v1.0 layout:
//   cols   0–13  : Section 1 — Event metadata           (14 cols)
//   cols  14–75  : Section 2 — Raw sniffer features      (62 cols)
//   cols  76–115 : Section 3 — Embedded detector feats   (40 cols)
//   cols 116–125 : Section 4 — ML model decisions        (10 cols)
//   col  126     : Section 5 — HMAC                       (1 col)
// ============================================================================

static constexpr size_t CSV_S1_METADATA_START   =   0;
static constexpr size_t CSV_S1_METADATA_COUNT   =  14;

static constexpr size_t CSV_S2_SNIFFER_START    =  14;
static constexpr size_t CSV_S2_SNIFFER_COUNT    =  62;

static constexpr size_t CSV_S3_EMBEDDED_START   =  76;
static constexpr size_t CSV_S3_EMBEDDED_COUNT   =  40;

static constexpr size_t CSV_S4_DECISIONS_START  = 116;
static constexpr size_t CSV_S4_DECISIONS_COUNT  =  10;

static constexpr size_t CSV_S5_HMAC_COL         = 126;

static constexpr size_t CSV_TOTAL_COLS          = 127;

// Derived — convenient aliases for CsvEventLoader
static constexpr size_t CSV_FEATURE_COLS        =  // S2 + S3 = raw + embedded
    CSV_S2_SNIFFER_COUNT + CSV_S3_EMBEDDED_COUNT;  // = 102

static constexpr size_t CSV_ML_DECISION_COLS    = CSV_S4_DECISIONS_COUNT; // = 10

} // namespace ml_defender