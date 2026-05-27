// csv_event_loader.hpp
// RAG Ingester - CsvEventLoader Component
// Day 67: Parse 127-column CSV lines into Event structs with HMAC verification
// Schema reference: ml-detector/FEATURE_SCHEMA.md (schema v1.0)
// AUTHORS: Alonso Isidoro Roman + Claude (Anthropic)
// Via Appia Quality - Built to last

#ifndef CSV_EVENT_LOADER_HPP
#define CSV_EVENT_LOADER_HPP

#include "event_loader.hpp"   // reuses Event + EngineVerdict structs

#include <string>
#include <vector>
#include <optional>
#include <cstdint>

namespace rag_ingester {

// ============================================================================
// CSV column layout (schema v1.0 — 127 columns)
// ============================================================================
//
//  Section 1  cols   0–13   14 cols   event metadata
//  Section 2  cols  14–75   62 cols   raw NetworkFeatures from sniffer
//  Section 3  cols  76–115  40 cols   embedded detector features
//  Section 4  cols 116–125  10 cols   ML model decisions
//  Section 5  col  126       1 col    HMAC-SHA256 (hex, 64 chars)
//
// ============================================================================

static constexpr int CSV_TOTAL_COLUMNS     = 127;
static constexpr int CSV_HMAC_COLUMN       = 126;  // last column
static constexpr int CSV_SECTION1_START    = 0;
static constexpr int CSV_SECTION2_START    = 14;
static constexpr int CSV_SECTION3_START    = 76;
static constexpr int CSV_SECTION4_START    = 116;

// Feature vector layout within Event::features (62 cols from S2)
// Callers can use these offsets to address specific features.
static constexpr int FEATURE_VECTOR_SIZE   = 62;  // S2 only — raw network features

// ============================================================================
// CsvEventLoaderConfig
// ============================================================================

struct CsvEventLoaderConfig {
    std::string hmac_key_hex;     ///< 64-char hex string (32 bytes) — REQUIRED
    bool        verify_hmac{true};///< Set false only in tests / offline analysis
};

// ============================================================================
// CsvParseResult — rich result to distinguish error types
// ============================================================================

enum class CsvParseStatus {
    OK,
    WRONG_COLUMN_COUNT,
    HMAC_MISMATCH,
    PARSE_ERROR,
};

struct CsvParseResult {
    CsvParseStatus status  {CsvParseStatus::OK};
    std::string    error   {};          ///< human-readable message on failure
    Event          event   {};          ///< populated on OK
};

// ============================================================================
// CsvEventLoader
// ============================================================================

/**
 * @brief Parse a single CSV line (delivered by CsvFileWatcher) into an Event.
 *
 * Responsibilities:
 *  1. Split the raw line into 127 columns
 *  2. Optionally verify HMAC-SHA256 over columns 0–125
 *  3. Map columns to the Event struct (reusing the same struct as EventLoader)
 *  4. Populate Event::features with Section 2 (62 raw NetworkFeature floats)
 *  5. Populate Event::verdicts from Section 4 ML model decisions
 *
 * Thread safety:
 *  - parse() is const and stateless — safe to call from multiple threads.
 *
 * Error handling:
 *  - Never throws. Returns CsvParseResult with status != OK on failure.
 *  - HMAC mismatch is a hard rejection (not a warning) when verify_hmac=true.
 */
class CsvEventLoader {
public:
    explicit CsvEventLoader(const CsvEventLoaderConfig& config);
    ~CsvEventLoader() = default;

    // Non-copyable — holds decoded key bytes
    CsvEventLoader(const CsvEventLoader&) = delete;
    CsvEventLoader& operator=(const CsvEventLoader&) = delete;

    /**
     * @brief Parse a single raw CSV line into an Event.
     * @param line  Complete CSV row without trailing newline.
     * @param lineno  1-based line number (stored in event for diagnostics).
     * @return CsvParseResult with status OK and populated event, or error.
     */
    CsvParseResult parse(const std::string& line, uint64_t lineno = 0) const;

    // Statistics — cumulative across all parse() calls
    struct Stats {
        uint64_t parsed_ok      {0};
        uint64_t hmac_failures  {0};
        uint64_t parse_errors   {0};
        uint64_t column_errors  {0};
    };

    Stats get_stats() const noexcept;
    void  reset_stats() noexcept;

private:
    CsvEventLoaderConfig config_;
    std::vector<uint8_t> hmac_key_;   ///< decoded from config_.hmac_key_hex

    // Mutable stats (parse() is logically const but updates counters)
    mutable Stats stats_;

    // ── Helpers ──────────────────────────────────────────────────────────────

    /**
     * @brief Split a CSV line into columns, respecting quoted fields.
     * Minimal quoting support: handles escaped double-quotes ("") and
     * comma-inside-quotes. IP addresses never need quoting in practice.
     */
    static std::vector<std::string> split_csv(const std::string& line);

    /**
     * @brief Recompose columns 0–125 as the HMAC input string.
     * The HMAC was computed over the joined content (see csv_event_writer.cpp).
     */
    static std::string recompose_content(const std::vector<std::string>& cols);

    /**
     * @brief Compute HMAC-SHA256 and return hex string.
     */
    std::string compute_hmac(const std::string& content) const;

    /**
     * @brief Populate Event from parsed columns.
     */
    static Event build_event(const std::vector<std::string>& cols,
                             uint64_t lineno);

    // Section parsers
    static void parse_section1(const std::vector<std::string>& cols, Event& ev);
    static void parse_section2(const std::vector<std::string>& cols, Event& ev);
    static void parse_section4(const std::vector<std::string>& cols, Event& ev);
};

} // namespace rag_ingester

#endif // CSV_EVENT_LOADER_HPP