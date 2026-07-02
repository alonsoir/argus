// correlation_writer.hpp
// aRGus NDR — Correlation Writer (zona BRONCE, contrato correlation_v1)
// Authors: Alonso Isidoro Roman + Claude (Anthropic)
//
// Registro mínimo de correlación: lo que el grafo Kuzu necesita para materializar
// :NetworkFlow + :Alert, nada más. Un contrato, una responsabilidad. NO toca el
// CSV de 127 columnas del RAG (csv_event_writer, contrato sellado v1.0).
//
// CONTRATO correlation_v1 — 19 columnas, sin header (validación por fila):
//    0 schema_version       1 source_sensor        2 event_id
//    3 node_id              4 community_id          5 flow_start_sec
//    6 flow_start_nano      7 src_ip                8 dst_ip
//    9 src_port            10 dst_port             11 protocol
//   12 final_classification 13 threat_category     14 fast_detector_score
//   15 ml_detector_score   16 overall_threat_score 17 authoritative_source
//   18 HMAC-SHA256 (sobre cols 0-17)
//
// FILOSOFÍA: bronce PRESERVA, gold DECIDE. Se escriben los 4 scores + la fuente
// autoritativa; Kuzu elige la confianza de la :Alert con todas las señales (aRGus
// hoy; Suricata/Zeek/Wazuh mañana). Versionado desde el día 1 (col 0).
//
// REGLA DE ESCRITURA: si community_id == "" (ICMP/no-IP diferido), el HOOK no llama
// a write_record (sin clave de join no sirve al grafo). El writer queda puro.
// ESCRITURA (DAY 203): segmentada + atomica. Cada segmento se escribe a
// <basename>.csv.tmp y se cierra+renombra a <basename>.csv al rotar (por tiempo
// absoluto desde apertura, config correlation_writer.rotation_seconds, o por
// max_events_per_file). El lector aguas abajo (BronzeDirWatcher, IN_MOVED_TO)
// SOLO ve el nombre final tras el rename -- nunca una linea a medias.
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
#include <correlation_v1/correlation_v1.hpp>

namespace ml_defender {

static constexpr const char* CORRELATION_SCHEMA_VERSION = "1";
static constexpr const char* CORRELATION_SOURCE_SENSOR  = "argus";
static constexpr size_t CORRELATION_TOTAL_COLS = 19;

struct CorrelationWriterConfig {
    std::string base_dir;                 // p.ej. /vagrant/logs/correlation/argus
    std::string hmac_key_hex;             // 64-char hex (32 bytes), igual que CsvEventWriter
    size_t      max_events_per_file = 10000;
    int         rotation_seconds    = 30;  // DAY 203 -- cierre por tiempo absoluto desde
                                            // apertura (no desde ultima escritura).
};

class CorrelationWriter {
public:
    explicit CorrelationWriter(const CorrelationWriterConfig& config,
                               std::shared_ptr<spdlog::logger> logger);
    ~CorrelationWriter();

    CorrelationWriter(const CorrelationWriter&) = delete;
    CorrelationWriter& operator=(const CorrelationWriter&) = delete;

    // Escribe un registro de correlación. PRECONDICIÓN del caller: community_id no vacío.
    // Devuelve false si community_id == "" (defensa en profundidad) o error de E/S.
    bool write_record(const protobuf::NetworkSecurityEvent& event);

    void flush();

    struct Stats {
        uint64_t records_written;
        uint64_t records_skipped;   // community_id vacío
        uint64_t rows_failed;
        std::string current_file;        // .tmp del segmento actualmente abierto (DAY 203)
        std::string current_final_path;  // path final post-rename (DAY 204, DEBT-CORRELATION-ROUNDTRIP-ORPHANED-001)
    };
    Stats get_stats() const noexcept;

private:
    // build_row / compute_hmac / fmt_double / csv_string: RETIRADOS DAY187
    // (Camino A). Serialización movida a libcorrelation_v1 (serialize, NOTARIO P3).

    // DAY 203 -- segmentacion + escritura atomica (DEBT-CIRCUIT-BRONZE-ROTATION-FOLLOW-001):
    // cada segmento se abre como <basename>.csv.tmp en modo trunc (fichero nuevo,
    // nunca append cross-segmento) y al rotar se cierra y se renombra atomicamente
    // (mismo filesystem) a <basename>.csv. El reader SOLO ve el nombre final tras
    // el rename -- nunca un fichero a medio escribir.
    void ensure_open();              // mutex_ held by caller
    void rotate_if_needed();         // mutex_ held by caller
    void rotate_locked();            // mutex_ held by caller
    void finalize_segment_locked();  // cierra + rename .tmp->final si hay segmento abierto
    std::string get_date_string() const;
    std::string get_time_string() const;   // HHMMSS, hora de apertura del segmento
    std::string get_basename() const;      // <date>-<HHMMSS>, fijado al abrir el segmento

    CorrelationWriterConfig config_;
    std::shared_ptr<spdlog::logger> logger_;
    std::vector<uint8_t> hmac_key_;

    mutable std::mutex mutex_;
    std::ofstream current_file_;
    std::string current_basename_;
    std::string current_tmp_path_;     // <base_dir>/<basename>.csv.tmp
    std::string current_final_path_;   // <base_dir>/<basename>.csv
    std::chrono::steady_clock::time_point segment_opened_at_;

    std::atomic<uint64_t> records_written_{0};
    std::atomic<uint64_t> records_skipped_{0};
    std::atomic<uint64_t> rows_failed_{0};
    std::atomic<size_t>   events_in_current_file_{0};
};

// ── to_row — capa protobuf→Row (DAY 185, extracción libcorrelation_v1) ────────
// Mapea NetworkSecurityEvent → CorrelationV1Row; la lib serializa el Row.
// Tri-estado: Ok(row) | Skip (community_id vacío = filtrado legítimo, D-F) | Error.
// v1 (refactor byte-idéntico): SIN caso Error — el guard D-D es commit aparte.
// Función LIBRE (no método) para que el test de oráculo la invoque directamente.
struct ToRowResult {
    enum class Status { Ok, Skip, Error };
    Status status = Status::Error;
    correlation_v1::CorrelationV1Row row{};
    std::string error;

    static ToRowResult ok(correlation_v1::CorrelationV1Row r) {
        return {Status::Ok, std::move(r), ""};
    }
    static ToRowResult skip() { return {Status::Skip, {}, ""}; }
    static ToRowResult err(std::string e) {
        return {Status::Error, {}, std::move(e)};
    }
};

ToRowResult to_correlation_v1_row(const protobuf::NetworkSecurityEvent& event);

} // namespace ml_defender