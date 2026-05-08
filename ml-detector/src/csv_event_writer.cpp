// csv_event_writer.cpp
// ML Defender - CSV Event Writer Implementation
// Day 64: Full 127-column schema, schema v1.0
// Authors: Alonso Isidoro Roman + Claude (Anthropic)
//
// Column layout — see FEATURE_SCHEMA.md for authoritative reference:
//   Section 1 (cols   0–13 ):  14  event metadata
//   Section 2 (cols  14–75 ):  62  raw NetworkFeatures from sniffer
//   Section 3 (cols  76–115):  40  embedded detector features (ml-detector)
//   Section 4 (cols 116–125):  10  ML model decisions
//   Section 5 (col  126    ):   1  HMAC-SHA256

#include "csv_event_writer.hpp"

#include <filesystem>
#include <sstream>
#include <iomanip>
#include <stdexcept>
#include <cmath>
#include <algorithm>

#include <openssl/hmac.h>
#include <openssl/evp.h>

namespace fs = std::filesystem;

namespace ml_defender {

// ============================================================================
// Helpers — static, file-local
// ============================================================================

namespace {

/** Decode a 64-char hex string into 32 raw bytes.
 *  Throws std::invalid_argument on bad input. */
std::vector<uint8_t> hex_decode(const std::string& hex) {
    if (hex.size() != 64) {
        throw std::invalid_argument(
            "HMAC key must be 64 hex chars (32 bytes), got " +
            std::to_string(hex.size()));
    }
    std::vector<uint8_t> out;
    out.reserve(32);
    for (size_t i = 0; i < hex.size(); i += 2) {
        unsigned int byte;
        if (std::sscanf(hex.c_str() + i, "%02x", &byte) != 1) {
            throw std::invalid_argument("Invalid hex char at position " +
                                        std::to_string(i));
        }
        out.push_back(static_cast<uint8_t>(byte));
    }
    return out;
}

} // anonymous namespace

// ============================================================================
// Static formatting helpers
// ============================================================================

std::string CsvEventWriter::fmt_float(float v) {
    if (!std::isfinite(v)) return "0.000000";
    std::ostringstream ss;
    ss << std::fixed << std::setprecision(6) << v;
    return ss.str();
}

std::string CsvEventWriter::fmt_double(double v) {
    if (!std::isfinite(v)) return "0.000000";
    std::ostringstream ss;
    ss << std::fixed << std::setprecision(6) << v;
    return ss.str();
}

std::string CsvEventWriter::csv_string(const std::string& s) {
    bool needs_quoting = (s.find(',')  != std::string::npos ||
                          s.find('"')  != std::string::npos ||
                          s.find('\n') != std::string::npos);
    if (!needs_quoting) return s;

    std::string out;
    out.reserve(s.size() + 2);
    out += '"';
    for (char c : s) {
        if (c == '"') out += '"';  // escape embedded double-quote
        out += c;
    }
    out += '"';
    return out;
}

// ============================================================================
// Constructor / Destructor
// ============================================================================

CsvEventWriter::CsvEventWriter(const CsvEventWriterConfig& config,
                               std::shared_ptr<spdlog::logger> logger)
    : config_(config)
    , logger_(logger)
{
    // Decode HMAC key — fail fast at construction, not at first write
    if (config_.hmac_key_hex.empty()) {
        throw std::invalid_argument("CsvEventWriter: hmac_key_hex is empty");
    }
    hmac_key_ = hex_decode(config_.hmac_key_hex);

    // Ensure output directory exists
    fs::create_directories(config_.base_dir);

    // Open the initial daily file
    current_date_      = get_date_string();
    current_file_path_ = get_file_path(current_date_);
    current_file_.open(current_file_path_, std::ios::app);

    if (!current_file_.is_open()) {
        throw std::runtime_error("CsvEventWriter: cannot open " +
                                 current_file_path_);
    }

    logger_->info("✅ CsvEventWriter ready");
    logger_->info("   Schema version : {}", CSV_SCHEMA_VERSION);
    logger_->info("   Total columns  : {}", CSV_TOTAL_COLS);
    logger_->info("   Output file    : {}", current_file_path_);
}

CsvEventWriter::~CsvEventWriter() {
    flush();
}

// ============================================================================
// Public interface
// ============================================================================

bool CsvEventWriter::write_event(const protobuf::NetworkSecurityEvent& event) {
    // Score filter — applied outside the lock for performance
    if (static_cast<float>(event.overall_threat_score()) <=
        config_.min_score_threshold) {
        events_skipped_.fetch_add(1, std::memory_order_relaxed);
        return false;
    }

    try {
        // Build sections 1–4 (the content HMAC will cover)
        std::string s1 = build_section1(event);
        std::string s2 = build_section2(event);
        std::string s3 = build_section3(event);
        std::string s4 = build_section4(event);

        // Row content = sections 1–4 joined (HMAC computed over this)
        std::string row_content;
        row_content.reserve(s1.size() + s2.size() + s3.size() + s4.size() + 3);
        row_content += s1; row_content += ',';
        row_content += s2; row_content += ',';
        row_content += s3; row_content += ',';
        row_content += s4;

        // Section 5: HMAC
        std::string hmac = compute_hmac(row_content);

        // Full row = content + HMAC
        std::string full_row;
        full_row.reserve(row_content.size() + 1 + hmac.size() + 1);
        full_row += row_content;
        full_row += ',';
        full_row += hmac;
        full_row += '\n';

        // Write under lock
        {
            std::lock_guard<std::mutex> lock(mutex_);
            rotate_if_needed();

            if (!current_file_.is_open()) {
                logger_->error("CsvEventWriter: file not open");
                rows_failed_.fetch_add(1, std::memory_order_relaxed);
                return false;
            }

            current_file_.write(full_row.data(),
                                static_cast<std::streamsize>(full_row.size()));
            current_file_.flush();
            events_in_current_file_.fetch_add(1, std::memory_order_relaxed);
        }

        events_written_.fetch_add(1, std::memory_order_relaxed);
        return true;

    } catch (const std::exception& e) {
        logger_->error("CsvEventWriter::write_event failed: {}", e.what());
        rows_failed_.fetch_add(1, std::memory_order_relaxed);
        return false;
    }
}

void CsvEventWriter::flush() {
    std::lock_guard<std::mutex> lock(mutex_);
    if (current_file_.is_open()) current_file_.flush();
}

CsvEventWriter::Stats CsvEventWriter::get_stats() const noexcept {
    std::lock_guard<std::mutex> lock(mutex_);
    return Stats{
        events_written_.load(),
        events_skipped_.load(),
        rows_failed_.load(),
        current_file_path_
    };
}

// ============================================================================
// Section 1 — Event metadata (cols 0–13)
// ============================================================================

std::string CsvEventWriter::build_section1(
    const protobuf::NetworkSecurityEvent& event) const
{
    const auto& nf = event.network_features();

    // col 0: timestamp_ns
    uint64_t ts_ns = event.has_event_timestamp()
        ? static_cast<uint64_t>(event.event_timestamp().seconds()) * UINT64_C(1000000000)
          + static_cast<uint64_t>(event.event_timestamp().nanos())
        : 0ULL;

    // col 12: divergence (prefer provenance, fallback to decision_metadata)
    double divergence = 0.0;
    if (event.has_provenance()) {
        divergence = event.provenance().discrepancy_score();
    } else if (event.has_decision_metadata()) {
        divergence = event.decision_metadata().score_divergence();
    }

    // col 13: final_decision from DetectionProvenance
    std::string final_decision;
    if (event.has_provenance()) {
        final_decision = event.provenance().final_decision();
    }

    // col 8: ensemble_confidence from TricapaMLAnalysis
    double confidence = 0.0;
    if (event.has_ml_analysis()) {
        confidence = event.ml_analysis().ensemble_confidence();
    }

    std::ostringstream ss;
    ss << ts_ns                                            // 0  timestamp_ns
       << ',' << csv_string(event.event_id())             // 1  event_id
       << ',' << csv_string(nf.source_ip())               // 2  src_ip
       << ',' << csv_string(nf.destination_ip())          // 3  dst_ip
       << ',' << nf.source_port()                         // 4  src_port
       << ',' << nf.destination_port()                    // 5  dst_port
       << ',' << csv_string(nf.protocol_name())           // 6  protocol
       << ',' << csv_string(event.final_classification()) // 7  final_class
       << ',' << fmt_double(confidence)                   // 8  confidence
       << ',' << csv_string(event.threat_category())      // 9  threat_category
       << ',' << fmt_double(event.fast_detector_score())  // 10 fast_score
       << ',' << fmt_double(event.ml_detector_score())    // 11 ml_score
       << ',' << fmt_double(divergence)                   // 12 divergence
       << ',' << csv_string(final_decision);              // 13 final_decision

    return ss.str();
}

// ============================================================================
// Section 2 — Raw NetworkFeatures from sniffer (cols 14–75, 62 cols)
// ============================================================================

std::string CsvEventWriter::build_section2(
    const protobuf::NetworkSecurityEvent& event) const
{
    // If the sniffer did not populate network_features, zero-fill all 62 cols.
    if (!event.has_network_features()) {
        std::string zeros;
        zeros.reserve(62 * 2);
        for (int i = 0; i < 62; ++i) {
            if (i > 0) zeros += ',';
            zeros += '0';
        }
        return zeros;
    }

    const auto& nf = event.network_features();

    std::ostringstream ss;

    // ── 2.1 Packet counts (14–17) ────────────────────────────────────────────
    ss << nf.total_forward_packets()                // 14
       << ',' << nf.total_backward_packets()        // 15
       << ',' << nf.total_forward_bytes()           // 16
       << ',' << nf.total_backward_bytes()          // 17

    // ── 2.2 Forward packet length stats (18–21) ──────────────────────────────
       << ',' << nf.forward_packet_length_max()     // 18
       << ',' << nf.forward_packet_length_min()     // 19
       << ',' << fmt_double(nf.forward_packet_length_mean()) // 20
       << ',' << fmt_double(nf.forward_packet_length_std())  // 21

    // ── 2.3 Backward packet length stats (22–25) ─────────────────────────────
       << ',' << nf.backward_packet_length_max()    // 22
       << ',' << nf.backward_packet_length_min()    // 23
       << ',' << fmt_double(nf.backward_packet_length_mean()) // 24
       << ',' << fmt_double(nf.backward_packet_length_std())  // 25

    // ── 2.4 Flow speeds and ratios (26–33) ───────────────────────────────────
       << ',' << fmt_double(nf.flow_bytes_per_second())          // 26
       << ',' << fmt_double(nf.flow_packets_per_second())        // 27
       << ',' << fmt_double(nf.forward_packets_per_second())     // 28
       << ',' << fmt_double(nf.backward_packets_per_second())    // 29
       << ',' << fmt_double(nf.download_upload_ratio())          // 30
       << ',' << fmt_double(nf.average_packet_size())            // 31
       << ',' << fmt_double(nf.average_forward_segment_size())   // 32
       << ',' << fmt_double(nf.average_backward_segment_size())  // 33

    // ── 2.5 Flow IAT (34–37) ─────────────────────────────────────────────────
       << ',' << fmt_double(nf.flow_inter_arrival_time_mean())   // 34
       << ',' << fmt_double(nf.flow_inter_arrival_time_std())    // 35
       << ',' << nf.flow_inter_arrival_time_max()                // 36
       << ',' << nf.flow_inter_arrival_time_min()                // 37

    // ── 2.6 Forward IAT (38–42) ──────────────────────────────────────────────
       << ',' << fmt_double(nf.forward_inter_arrival_time_total()) // 38
       << ',' << fmt_double(nf.forward_inter_arrival_time_mean())  // 39
       << ',' << fmt_double(nf.forward_inter_arrival_time_std())   // 40
       << ',' << nf.forward_inter_arrival_time_max()               // 41
       << ',' << nf.forward_inter_arrival_time_min()               // 42

    // ── 2.7 Backward IAT (43–47) ─────────────────────────────────────────────
       << ',' << fmt_double(nf.backward_inter_arrival_time_total()) // 43
       << ',' << fmt_double(nf.backward_inter_arrival_time_mean())  // 44
       << ',' << fmt_double(nf.backward_inter_arrival_time_std())   // 45
       << ',' << nf.backward_inter_arrival_time_max()               // 46
       << ',' << nf.backward_inter_arrival_time_min()               // 47

    // ── 2.8 TCP flag counts (48–55) ──────────────────────────────────────────
       << ',' << nf.fin_flag_count()                // 48
       << ',' << nf.syn_flag_count()                // 49
       << ',' << nf.rst_flag_count()                // 50
       << ',' << nf.psh_flag_count()                // 51
       << ',' << nf.ack_flag_count()                // 52
       << ',' << nf.urg_flag_count()                // 53
       << ',' << nf.cwe_flag_count()                // 54
       << ',' << nf.ece_flag_count()                // 55

    // ── 2.9 Directional TCP flags (56–59) ────────────────────────────────────
       << ',' << nf.forward_psh_flags()             // 56
       << ',' << nf.backward_psh_flags()            // 57
       << ',' << nf.forward_urg_flags()             // 58
       << ',' << nf.backward_urg_flags()            // 59

    // ── 2.10 Headers and bulk transfer (60–67) ───────────────────────────────
       << ',' << fmt_double(nf.forward_header_length())            // 60
       << ',' << fmt_double(nf.backward_header_length())           // 61
       << ',' << fmt_double(nf.forward_average_bytes_bulk())       // 62
       << ',' << fmt_double(nf.forward_average_packets_bulk())     // 63
       << ',' << fmt_double(nf.forward_average_bulk_rate())        // 64
       << ',' << fmt_double(nf.backward_average_bytes_bulk())      // 65
       << ',' << fmt_double(nf.backward_average_packets_bulk())    // 66
       << ',' << fmt_double(nf.backward_average_bulk_rate())       // 67

    // ── 2.11 Global packet length stats (68–72) ──────────────────────────────
       << ',' << nf.minimum_packet_length()         // 68
       << ',' << nf.maximum_packet_length()         // 69
       << ',' << fmt_double(nf.packet_length_mean())     // 70
       << ',' << fmt_double(nf.packet_length_std())      // 71
       << ',' << fmt_double(nf.packet_length_variance()) // 72

    // ── 2.12 Active / idle (73–74) ───────────────────────────────────────────
       << ',' << fmt_double(nf.active_mean())        // 73
       << ',' << fmt_double(nf.idle_mean())          // 74

    // ── 2.13 Flow duration (75) ──────────────────────────────────────────────
       << ',' << nf.flow_duration_microseconds();    // 75

    return ss.str();
}

// ============================================================================
// Section 3 — Embedded detector features (cols 76–115, 40 cols)
// ============================================================================

std::string CsvEventWriter::build_section3(
    const protobuf::NetworkSecurityEvent& event) const
{
    std::ostringstream ss;
    bool first = true;

    auto sep = [&]() -> std::ostringstream& {
        if (!first) ss << ',';
        first = false;
        return ss;
    };

    // ── 3.1 DDoS embedded (76–85) ────────────────────────────────────────────
    if (event.has_network_features() &&
        event.network_features().has_ddos_embedded()) {
        const auto& d = event.network_features().ddos_embedded();
        sep() << fmt_float(d.syn_ack_ratio());              // 76
        sep() << fmt_float(d.packet_symmetry());            // 77
        sep() << fmt_float(d.source_ip_dispersion());       // 78
        sep() << fmt_float(d.protocol_anomaly_score());     // 79
        sep() << fmt_float(d.packet_size_entropy());        // 80
        sep() << fmt_float(d.traffic_amplification_factor()); // 81
        sep() << fmt_float(d.flow_completion_rate());       // 82
        sep() << fmt_float(d.geographical_concentration()); // 83
        sep() << fmt_float(d.traffic_escalation_rate());    // 84
        sep() << fmt_float(d.resource_saturation_score());  // 85
    } else {
        for (int i = 0; i < 10; ++i) sep() << '0';
    }

    // ── 3.2 Ransomware embedded (86–95) ──────────────────────────────────────
    if (event.has_network_features() &&
        event.network_features().has_ransomware_embedded()) {
        const auto& r = event.network_features().ransomware_embedded();
        sep() << fmt_float(r.io_intensity());           // 86
        sep() << fmt_float(r.entropy());                // 87
        sep() << fmt_float(r.resource_usage());         // 88
        sep() << fmt_float(r.network_activity());       // 89
        sep() << fmt_float(r.file_operations());        // 90
        sep() << fmt_float(r.process_anomaly());        // 91
        sep() << fmt_float(r.temporal_pattern());       // 92
        sep() << fmt_float(r.access_frequency());       // 93
        sep() << fmt_float(r.data_volume());            // 94
        sep() << fmt_float(r.behavior_consistency());   // 95
    } else {
        for (int i = 0; i < 10; ++i) sep() << '0';
    }

    // ── 3.3 Traffic classification (96–105) ──────────────────────────────────
    if (event.has_network_features() &&
        event.network_features().has_traffic_classification()) {
        const auto& t = event.network_features().traffic_classification();
        sep() << fmt_float(t.packet_rate());              // 96
        sep() << fmt_float(t.connection_rate());          // 97
        sep() << fmt_float(t.tcp_udp_ratio());            // 98
        sep() << fmt_float(t.avg_packet_size());          // 99
        sep() << fmt_float(t.port_entropy());             // 100
        sep() << fmt_float(t.flow_duration_std());        // 101
        sep() << fmt_float(t.src_ip_entropy());           // 102
        sep() << fmt_float(t.dst_ip_concentration());     // 103
        sep() << fmt_float(t.protocol_variety());         // 104
        sep() << fmt_float(t.temporal_consistency());     // 105
    } else {
        for (int i = 0; i < 10; ++i) sep() << '0';
    }

    // ── 3.4 Internal anomaly (106–115) ───────────────────────────────────────
    if (event.has_network_features() &&
        event.network_features().has_internal_anomaly()) {
        const auto& ia = event.network_features().internal_anomaly();
        sep() << fmt_float(ia.internal_connection_rate());      // 106
        sep() << fmt_float(ia.service_port_consistency());      // 107
        sep() << fmt_float(ia.protocol_regularity());           // 108
        sep() << fmt_float(ia.packet_size_consistency());       // 109
        sep() << fmt_float(ia.connection_duration_std());       // 110
        sep() << fmt_float(ia.lateral_movement_score());        // 111
        sep() << fmt_float(ia.service_discovery_patterns());    // 112
        sep() << fmt_float(ia.data_exfiltration_indicators());  // 113
        sep() << fmt_float(ia.temporal_anomaly_score());        // 114
        sep() << fmt_float(ia.access_pattern_entropy());        // 115
    } else {
        for (int i = 0; i < 10; ++i) sep() << '0';
    }

    return ss.str();
}

// ============================================================================
// Section 4 — ML model decisions (cols 116–125, 10 cols)
// ============================================================================

std::string CsvEventWriter::build_section4(
    const protobuf::NetworkSecurityEvent& event) const
{
    // Defaults: all empty / zero
    std::string l1_pred, l2d_pred, l2r_pred, l3t_pred, l3i_pred;
    double l1_conf = 0.0, l2d_conf = 0.0, l2r_conf = 0.0,
           l3t_conf = 0.0, l3i_conf = 0.0;

    if (event.has_ml_analysis()) {
        const auto& ml = event.ml_analysis();

        // Level 1 — general detection
        if (ml.has_level1_general_detection()) {
            l1_pred = ml.level1_general_detection().prediction_class();
            l1_conf = ml.level1_general_detection().confidence_score();
        }

        // Level 2 — specialized predictions (positional: 0=DDoS, 1=Ransomware)
        // See FEATURE_SCHEMA.md note: positional indexing may change in v1.1
        if (ml.level2_specialized_predictions_size() > 0) {
            l2d_pred = ml.level2_specialized_predictions(0).prediction_class();
            l2d_conf = ml.level2_specialized_predictions(0).confidence_score();
        }
        if (ml.level2_specialized_predictions_size() > 1) {
            l2r_pred = ml.level2_specialized_predictions(1).prediction_class();
            l2r_conf = ml.level2_specialized_predictions(1).confidence_score();
        }

        // Level 3 — specialized predictions (positional: 0=Traffic, 1=Internal)
        if (ml.level3_specialized_predictions_size() > 0) {
            l3t_pred = ml.level3_specialized_predictions(0).prediction_class();
            l3t_conf = ml.level3_specialized_predictions(0).confidence_score();
        }
        if (ml.level3_specialized_predictions_size() > 1) {
            l3i_pred = ml.level3_specialized_predictions(1).prediction_class();
            l3i_conf = ml.level3_specialized_predictions(1).confidence_score();
        }
    }

    std::ostringstream ss;
    ss << csv_string(l1_pred)      << ',' << fmt_double(l1_conf)   // 116-117
       << ',' << csv_string(l2d_pred) << ',' << fmt_double(l2d_conf) // 118-119
       << ',' << csv_string(l2r_pred) << ',' << fmt_double(l2r_conf) // 120-121
       << ',' << csv_string(l3t_pred) << ',' << fmt_double(l3t_conf) // 122-123
       << ',' << csv_string(l3i_pred) << ',' << fmt_double(l3i_conf);// 124-125

    return ss.str();
}

// ============================================================================
// Section 5 — HMAC-SHA256 (col 126)
// ============================================================================

std::string CsvEventWriter::compute_hmac(const std::string& row_content) const {
    unsigned char digest[EVP_MAX_MD_SIZE];
    unsigned int digest_len = 0;

    HMAC(EVP_sha256(),
         hmac_key_.data(),
         static_cast<int>(hmac_key_.size()),
         reinterpret_cast<const unsigned char*>(row_content.data()),
         row_content.size(),
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
// File management
// ============================================================================

std::string CsvEventWriter::get_date_string() const {
    auto now     = std::chrono::system_clock::now();
    auto time_t  = std::chrono::system_clock::to_time_t(now);
    std::tm tm{};
    localtime_r(&time_t, &tm);

    std::ostringstream ss;
    ss << std::put_time(&tm, "%Y-%m-%d");
    return ss.str();
}

std::string CsvEventWriter::get_file_path(const std::string& date) const {
    return config_.base_dir + "/" + date + ".csv";
}

void CsvEventWriter::rotate_if_needed() {
    // PRECONDITION: mutex_ is held by caller

    std::string new_date = get_date_string();
    bool date_changed    = (new_date != current_date_);
    bool size_exceeded   = (events_in_current_file_.load() >=
                            config_.max_events_per_file);

    if (date_changed || size_exceeded) {
        rotate_locked();
        if (date_changed) current_date_ = new_date;
    }
}

void CsvEventWriter::rotate_locked() {
    // PRECONDITION: mutex_ is held by caller

    if (current_file_.is_open()) {
        current_file_.flush();
        current_file_.close();
    }

    current_date_      = get_date_string();
    current_file_path_ = get_file_path(current_date_);
    current_file_.open(current_file_path_, std::ios::app);
    events_in_current_file_.store(0, std::memory_order_relaxed);

    if (!current_file_.is_open()) {
        logger_->error("CsvEventWriter: failed to open rotated file: {}",
                       current_file_path_);
    } else {
        logger_->info("CsvEventWriter: rotated to {}", current_file_path_);
    }
}

} // namespace ml_defender