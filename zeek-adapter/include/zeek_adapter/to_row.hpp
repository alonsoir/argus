// zeek-adapter/include/zeek_adapter/to_row.hpp
// aRGus NDR — Zeek conn.log (TSV) -> CorrelationV1Row. Capa PURA del adapter.
//
// Mismo Row y misma semántica de tres estados que el ORÁCULO (ml-detector).
// Lo que cambia es la FUENTE:
//   - Suricata: eve.json, JSON autodescriptivo por línea.
//   - Zeek: conn.log, TSV. Los nombres de campo viven en la cabecera `#fields`,
//     NO en cada fila -> el índice se pasa a to_row, no se hardcodea (esquiva el
//     off-by-one 23/24 medido DAY 235).
//
// PURA: sin fichero, sin reloj, sin red, sin fetch de clave. El driver lee el
// `#fields` una vez, construye el índice y se lo pasa a to_row por cada fila.
#pragma once

#include <cstdint>
#include <string>
#include <unordered_map>
#include <vector>

#include <correlation_v1/correlation_v1.hpp>

namespace zeek_adapter {

inline constexpr const char* SCHEMA_VERSION            = "1";
inline constexpr const char* CORRELATION_SOURCE_SENSOR = "zeek";
inline constexpr const char* AUTHORITATIVE_SOURCE      = "zeek";  // ⚠️ D-D diferido en validate() v1
inline constexpr const char* EVENT_ID_PREFIX           = "zeek:";

// Marcadores del preámbulo de conn.log (MEDIDO DAY 235).
inline constexpr const char* ZEEK_UNSET_FIELD = "-";
inline constexpr const char* ZEEK_EMPTY_FIELD = "(empty)";

// ConnFieldIndex — nombre de campo -> posición, parseado del `#fields`. Construido
// UNA vez por el driver; inmune a que Zeek reordene/añada columnas entre versiones.
struct ConnFieldIndex {
    std::unordered_map<std::string, std::size_t> pos;

    [[nodiscard]] bool empty() const { return pos.empty(); }
    // ANTES:  [[nodiscard]] bool get(const std::vector<std::string>& cols, ...) const;
    // AHORA (sin [[nodiscard]]):
    bool get(const std::vector<std::string>& cols,
             const std::string& name, std::string& out) const;
};

// Parsea "#fields\tts\tuid\t..." -> ConnFieldIndex. Descarta el token `#fields`.
// Índice vacío si la línea no empieza por `#fields`.
[[nodiscard]] ConnFieldIndex parse_conn_fields(const std::string& fields_line);

// ToRowResult — tres estados (imita ml-detector para que D5 sea el mismo mecanismo).
struct [[nodiscard]] ToRowResult {
    enum class Status { Ok, Skip, Error };
    Status status = Status::Error;
    correlation_v1::CorrelationV1Row row{};
    std::string reason;

    static ToRowResult ok(correlation_v1::CorrelationV1Row r);
    static ToRowResult skip(std::string why);
    static ToRowResult error(std::string what);
};

// to_row — una fila de DATOS de conn.log -> Row.
// node_id: punto de OBSERVACIÓN (D2), de la config. fields: índice del MISMO conn.log.
[[nodiscard]] ToRowResult to_row(const std::string& line,
                                 const ConnFieldIndex& fields,
                                 const std::string& node_id);

// Test: `ts` de Zeek = epoch double "1312967066.683089" -> (secs, nanos). El epoch ya es UTC.
[[nodiscard]] bool parse_zeek_ts(const std::string& ts, int64_t& secs, int32_t& nanos);

// Test: event_id determinista (D3). Preimagen = community_id ‖ ts. NO usa `uid` (inestable).
[[nodiscard]] std::string make_event_id(const std::string& community_id, const std::string& ts);

}  // namespace zeek_adapter