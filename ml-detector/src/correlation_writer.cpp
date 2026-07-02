// correlation_writer.cpp
// aRGus NDR — Correlation Writer implementation (zona BRONCE, contrato correlation_v1)
// Clona el patrón probado de csv_event_writer.cpp (HMAC OpenSSL, rotación fecha+tamaño,
// append no-atómico, thread-safe). Authors: Alonso Isidoro Roman + Claude (Anthropic)

#include "correlation_writer.hpp"

#include <filesystem>
#include <system_error>
#include <sstream>
#include <iomanip>
#include <stdexcept>
#include <cmath>
#include <cstdio>

#include <openssl/hmac.h>
#include <openssl/evp.h>

namespace fs = std::filesystem;

namespace ml_defender {

namespace {

// Idéntico a csv_event_writer: 64 hex chars -> 32 bytes.
std::vector<uint8_t> hex_decode(const std::string& hex) {
    if (hex.size() != 64) {
        throw std::invalid_argument(
            "HMAC key must be 64 hex chars (32 bytes), got " + std::to_string(hex.size()));
    }
    std::vector<uint8_t> out;
    out.reserve(32);
    for (size_t i = 0; i < hex.size(); i += 2) {
        unsigned int byte;
        if (std::sscanf(hex.c_str() + i, "%02x", &byte) != 1) {
            throw std::invalid_argument("Invalid hex char at position " + std::to_string(i));
        }
        out.push_back(static_cast<uint8_t>(byte));
    }
    return out;
}

} // anonymous namespace

// ----------------------------------------------------------------------------
// Formatting helpers
// fmt_double / csv_string: RETIRADOS DAY187 (Camino A). Eran helpers EXCLUSIVOS
// de build_row (el árbitro). La serialización vive ahora en libcorrelation_v1.

// ----------------------------------------------------------------------------
// Construction
// ----------------------------------------------------------------------------
CorrelationWriter::CorrelationWriter(const CorrelationWriterConfig& config,
                                     std::shared_ptr<spdlog::logger> logger)
    : config_(config), logger_(std::move(logger)) {
    hmac_key_ = hex_decode(config_.hmac_key_hex);
    fs::create_directories(config_.base_dir);
    if (logger_) logger_->info("CorrelationWriter: base_dir={}, rotation_seconds={}",
                                config_.base_dir, config_.rotation_seconds);
}

CorrelationWriter::~CorrelationWriter() {
    std::lock_guard<std::mutex> lock(mutex_);
    finalize_segment_locked();
}

// compute_hmac / build_row: RETIRADOS DAY187 (Camino A). Eran EL ÁRBITRO del
// refactor byte-idéntico. Su sucesor: el fuzz diferencial de DAY187 (240k casos)
// + serialize() en libcorrelation_v1, que es ahora el NOTARIO ÚNICO (P3).
//
// to_row — protobuf -> CorrelationV1Row. La serialización (incl. entrecomillado
// y HMAC) la hace serialize() en la lib. Solo ml-detector habla NetworkSecurityEvent.
ToRowResult to_correlation_v1_row(const protobuf::NetworkSecurityEvent& event) {
    const auto& nf = event.network_features();

    // D-F: community_id vacío = SKIP legítimo (no es pérdida). Igual que el
    // guard de defensa en profundidad de write_record.
    if (nf.community_id().empty()) {
        return ToRowResult::skip();
    }

    const auto& ts = nf.flow_start_time();
    correlation_v1::CorrelationV1Row r;
    r.schema_version       = CORRELATION_SCHEMA_VERSION;                       // 0  "1"
    r.source_sensor        = CORRELATION_SOURCE_SENSOR;                        // 1  "argus"
    r.event_id             = event.event_id();                                // 2
    r.node_id              = event.originating_node_id();                     // 3
    r.community_id         = nf.community_id();                               // 4
    r.flow_start_sec       = ts.seconds();                                    // 5
    r.flow_start_nano      = ts.nanos();                                      // 6
    r.src_ip               = nf.source_ip();                                  // 7
    r.dst_ip               = nf.destination_ip();                             // 8
    r.src_port             = nf.source_port();                               // 9
    r.dst_port             = nf.destination_port();                          // 10
    r.protocol             = nf.protocol_name();                             // 11
    r.final_classification = event.final_classification();                   // 12
    r.threat_category      = event.threat_category();                        // 13
    r.fast_detector_score  = event.fast_detector_score();                    // 14
    r.ml_detector_score    = event.ml_detector_score();                      // 15
    r.overall_threat_score = event.overall_threat_score();                   // 16
    r.authoritative_source = protobuf::DetectorSource_Name(                   // 17
                                 event.authoritative_source());
    return ToRowResult::ok(std::move(r));
}

// ----------------------------------------------------------------------------
// write_record
// ----------------------------------------------------------------------------
bool CorrelationWriter::write_record(const protobuf::NetworkSecurityEvent& event) {
    // DAY187 — NOTARIO ÚNICO (P3): protobuf -> Row -> bytes embuda por serialize(),
    // que llama a validate() primero. build_row/compute_hmac RETIRADOS (el fuzz
    // diferencial de DAY187 garantizó byte-identidad sobre 240k casos aleatorios).
    auto tr = to_correlation_v1_row(event);

    // SKIP: community_id vacío (D-F, filtrado legítimo). Sin línea, sin fallo.
    if (tr.status == ToRowResult::Status::Skip) {
        records_skipped_.fetch_add(1, std::memory_order_relaxed);
        return false;
    }
    // ERROR de mapeo (v1 no lo emite; D-D diferido). Defensa en profundidad.
    if (tr.status == ToRowResult::Status::Error) {
        rows_failed_.fetch_add(1, std::memory_order_relaxed);
        if (logger_) logger_->warn("correlation_v1 to_row error [{}]: {}",
                                   event.event_id(), tr.error);
        return false;
    }

    // serialize() = validate() + cols 0-17 + HMAC col 18. Rechaza \n/\r (Camino A)
    // y clave HMAC mal formada. Lo que rechaza, NO se emite (frontera de confianza).
    auto sr = serialize(tr.row, hmac_key_);
    if (!sr) {
        rows_failed_.fetch_add(1, std::memory_order_relaxed);
        if (logger_) logger_->warn("correlation_v1 serialize rechazó [{}]: {}",
                                   event.event_id(), sr.error);
        return false;
    }

    std::lock_guard<std::mutex> lock(mutex_);
    rotate_if_needed();
    ensure_open();
    if (!current_file_.is_open()) {
        rows_failed_.fetch_add(1, std::memory_order_relaxed);
        return false;
    }
    current_file_ << sr.line << "\n";
    if (!current_file_) {
        rows_failed_.fetch_add(1, std::memory_order_relaxed);
        return false;
    }
    events_in_current_file_.fetch_add(1, std::memory_order_relaxed);
    records_written_.fetch_add(1, std::memory_order_relaxed);
    return true;
}

void CorrelationWriter::flush() {
    std::lock_guard<std::mutex> lock(mutex_);
    if (current_file_.is_open()) current_file_.flush();
}

CorrelationWriter::Stats CorrelationWriter::get_stats() const noexcept {
    return Stats{ records_written_.load(), records_skipped_.load(),
                 rows_failed_.load(), current_tmp_path_, current_final_path_ };
}

// ----------------------------------------------------------------------------
// File management — DAY 203: segmentacion + escritura atomica .tmp->rename
// (DEBT-CIRCUIT-BRONZE-ROTATION-FOLLOW-001). Cierre por TIEMPO ABSOLUTO desde
// apertura del segmento (segment_opened_at_), no desde la ultima escritura --
// un sensor mudo no deja un segmento abierto para siempre.
// ----------------------------------------------------------------------------
std::string CorrelationWriter::get_date_string() const {
    auto now    = std::chrono::system_clock::now();
    auto time_t = std::chrono::system_clock::to_time_t(now);
    std::tm tm{};
    localtime_r(&time_t, &tm);
    std::ostringstream ss;
    ss << std::put_time(&tm, "%Y-%m-%d");
    return ss.str();
}

std::string CorrelationWriter::get_time_string() const {
    auto now    = std::chrono::system_clock::now();
    auto time_t = std::chrono::system_clock::to_time_t(now);
    std::tm tm{};
    localtime_r(&time_t, &tm);
    std::ostringstream ss;
    ss << std::put_time(&tm, "%H%M%S");
    return ss.str();
}

std::string CorrelationWriter::get_basename() const {
    return get_date_string() + "-" + get_time_string();
}

void CorrelationWriter::ensure_open() {
    // PRECONDITION: mutex_ held by caller
    if (current_file_.is_open()) return;
    current_basename_   = get_basename();
    current_tmp_path_   = config_.base_dir + "/" + current_basename_ + ".csv.tmp";
    current_final_path_ = config_.base_dir + "/" + current_basename_ + ".csv";
    // Segmento NUEVO -> trunc (nunca append cross-segmento; el nombre ya es
    // unico por hora de apertura -- no puede colisionar con uno anterior).
    current_file_.open(current_tmp_path_, std::ios::out | std::ios::trunc);
    events_in_current_file_.store(0, std::memory_order_relaxed);
    segment_opened_at_ = std::chrono::steady_clock::now();
    if (!current_file_.is_open() && logger_)
        logger_->error("CorrelationWriter: failed to open segment: {}", current_tmp_path_);
}

void CorrelationWriter::rotate_if_needed() {
    // PRECONDITION: mutex_ held by caller
    if (!current_file_.is_open()) return;  // nada que rotar todavia
    auto elapsed = std::chrono::duration_cast<std::chrono::seconds>(
        std::chrono::steady_clock::now() - segment_opened_at_).count();
    bool time_exceeded = (elapsed >= config_.rotation_seconds);
    bool size_exceeded = (events_in_current_file_.load() >= config_.max_events_per_file);
    if (time_exceeded || size_exceeded) {
        rotate_locked();
    }
}

void CorrelationWriter::rotate_locked() {
    // PRECONDITION: mutex_ held by caller
    finalize_segment_locked();
    // El siguiente write_record() llama ensure_open(), que abre el segmento
    // nuevo con nombre fijado a la hora actual.
}

void CorrelationWriter::finalize_segment_locked() {
    // PRECONDITION: mutex_ held by caller
    if (!current_file_.is_open()) return;
    current_file_.flush();
    current_file_.close();
    std::error_code ec;
    fs::rename(current_tmp_path_, current_final_path_, ec);
    if (ec) {
        if (logger_) logger_->error(
            "CorrelationWriter: rename atomico fallo {} -> {}: {}",
            current_tmp_path_, current_final_path_, ec.message());
    } else if (logger_) {
        logger_->info("CorrelationWriter: segmento cerrado {}", current_final_path_);
    }
}

} // namespace ml_defender