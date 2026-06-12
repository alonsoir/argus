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
// ESCRITURA: append no-atómico (igual patrón que CsvEventWriter). El lector aguas
// abajo valida HMAC por fila y descarta la última línea si está incompleta.
#pragma once

#include <string>
#include <vector>
#include <fstream>
#include <mutex>
#include <atomic>
#include <memory>

#include <spdlog/spdlog.h>
#include <network_security.pb.h>

namespace ml_defender {

static constexpr const char* CORRELATION_SCHEMA_VERSION = "1";
static constexpr const char* CORRELATION_SOURCE_SENSOR  = "argus";
static constexpr size_t CORRELATION_TOTAL_COLS = 19;

struct CorrelationWriterConfig {
    std::string base_dir;                 // p.ej. /vagrant/logs/correlation/argus
    std::string hmac_key_hex;             // 64-char hex (32 bytes), igual que CsvEventWriter
    size_t      max_events_per_file = 10000;
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
        std::string current_file;
    };
    Stats get_stats() const noexcept;

private:
    std::string build_row(const protobuf::NetworkSecurityEvent& event) const;
    std::string compute_hmac(const std::string& row_content) const;

    static std::string fmt_double(double v);
    static std::string csv_string(const std::string& s);

    void ensure_open();
    void rotate_if_needed();   // mutex_ held by caller
    void rotate_locked();      // mutex_ held by caller
    std::string get_date_string() const;
    std::string get_file_path(const std::string& date) const;

    CorrelationWriterConfig config_;
    std::shared_ptr<spdlog::logger> logger_;
    std::vector<uint8_t> hmac_key_;

    mutable std::mutex mutex_;
    std::ofstream current_file_;
    std::string current_date_;
    std::string current_file_path_;

    std::atomic<uint64_t> records_written_{0};
    std::atomic<uint64_t> records_skipped_{0};
    std::atomic<uint64_t> rows_failed_{0};
    std::atomic<size_t>   events_in_current_file_{0};
};

} // namespace ml_defender