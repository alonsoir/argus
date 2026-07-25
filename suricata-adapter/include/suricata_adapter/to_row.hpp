// suricata-adapter/include/suricata_adapter/to_row.hpp
// aRGus NDR — suricata -> CorrelationV1Row. Capa PURA del adapter.
//
// ESPEJO de ml-detector/src/correlation_writer.cpp::to_correlation_v1_row (el ORÁCULO).
// Misma forma, misma semántica de tres estados. Lo que cambia es la fuente de datos.
//
// PURA: sin fichero, sin reloj, sin red, sin fetch de clave. Eso permite que el test
// le pase una línea literal y compruebe el Row campo a campo sin montar nada.
#pragma once

#include <string>

#include <correlation_v1/correlation_v1.hpp>

namespace suricata_adapter {

// Constantes del contrato para este productor.
// D-C (correlation_v1.hpp): schema_version y source_sensor son CAMPOS del Row,
// no constantes de la librería. Cada adapter fija los suyos.
inline constexpr const char* SCHEMA_VERSION           = "1";
inline constexpr const char* CORRELATION_SOURCE_SENSOR = "suricata";

// Col 17. ⚠️ El guard D-D está DIFERIDO en validate() v1: hoy NO se exige que este
// símbolo sea un DetectorSource legal. Cuando se active (commit de contrato),
// "suricata" tendrá que ser símbolo legal o estas filas empezarán a rechazarse.
inline constexpr const char* AUTHORITATIVE_SOURCE      = "suricata";

// Prefijo del event_id (D3): espacio de nombres propio, sin colisión con aRGus.
inline constexpr const char* EVENT_ID_PREFIX           = "suricata:";

// ---------------------------------------------------------------------------
// Resultado de tres estados. NO se reutiliza ml-detector::ToRowResult porque
// arrastra protobuf; se IMITA exactamente para que D5 (descarte explícito) sea
// el mismo mecanismo que ya usa aRGus, no una convención nueva de este adapter.
//
//   Ok    -> hay fila
//   Skip  -> descarte LEGÍTIMO (no es pérdida). Sin línea y sin fallo, pero con
//            motivo, para el contador ruidoso de D5.
//   Error -> bug del productor. Ruidoso.
// ---------------------------------------------------------------------------
struct [[nodiscard]] ToRowResult {
    enum class Status { Ok, Skip, Error };

    Status status = Status::Error;
    correlation_v1::CorrelationV1Row row{};
    std::string reason;   // motivo del Skip o diagnóstico del Error; vacío si Ok

    static ToRowResult ok(correlation_v1::CorrelationV1Row r);
    static ToRowResult skip(std::string why);
    static ToRowResult error(std::string what);
};

// ---------------------------------------------------------------------------
// to_row — una línea de la salida nativa de suricata -> Row.
//
// node_id: punto de OBSERVACIÓN (D2), no el host que ejecuta el sensor. Viene de
// la config; dos sensores con el mismo node_id declaran que observan lo mismo.
// ---------------------------------------------------------------------------
[[nodiscard]] ToRowResult to_row(const std::string& line, const std::string& node_id);

// Expuesta para el test: "2011-08-10T09:04:32.432327+0000" -> (secs, nanos).
// Respeta el offset DEL EVENTO, no el de la máquina que ejecuta el adapter.
[[nodiscard]] bool parse_iso8601(const std::string& ts, int64_t& secs, int32_t& nanos);

// Expuesta para el test: event_id determinista (D3).
[[nodiscard]] std::string make_event_id(const std::string& timestamp,
                                        const std::string& flow_id,
                                        const std::string& signature_id,
                                        const std::string& community_id);

}  // namespace suricata_adapter
