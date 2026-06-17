// correlation_v1.hpp
// aRGus NDR — libcorrelation_v1: serialización PURA del contrato bronce correlation_v1
// Authors: Alonso Isidoro Roman + Claude (Anthropic)
//
// PROCEDENCIA (DAY 185): capa de serialización extraída de
// ml-detector/correlation_writer.cpp. Esta lib contiene SOLO el tramo
// (CorrelationV1Row -> bytes), compartido por los 5 productores del contrato bronce
// (aRGus/ml-detector, Suricata, Zeek, Wazuh, Andrés).
// CERO protobuf · CERO red · CERO I/O de fichero · CERO fetch de clave.
//
// CORTE EN TRES CAPAS (la struct es la frontera donde el protobuf muere):
//   [protobuf -> Row]  to_row()           — ml-detector, EXCLUSIVO. DetectorSource_Name,
//                                            skip por community_id vacío, guard D-D.
//                                            Solo ml-detector habla NetworkSecurityEvent.
//   [Row -> bytes]     serialize()         — ESTA LIB. Notario único de los bytes (P3):
//                                            aRGus/Suricata/Zeek/Wazuh/Andrés embudan aquí.
//   [bytes -> disco]   CorrelationWriter   — ml-detector. Rotación + ofstream + reloj.
//
// CONTRATO correlation_v1 — 19 columnas (0-17 datos, 18 HMAC-SHA256 sobre cols 0-17):
//    0 schema_version       1 source_sensor        2 event_id
//    3 node_id              4 community_id          5 flow_start_sec
//    6 flow_start_nano      7 src_ip                8 dst_ip
//    9 src_port            10 dst_port             11 protocol
//   12 final_classification 13 threat_category     14 fast_detector_score
//   15 ml_detector_score   16 overall_threat_score 17 authoritative_source
//   18 HMAC-SHA256 (sobre cols 0-17)
//
// DECISIONES CONGELADAS (DAY 185):
//   D-A  Error como valor TIPADO, nunca excepción ni línea silenciosa. [[nodiscard]]
//        sobre el TIPO (mismo espíritu que FlushResult, DAY 184): el fallo de validez
//        no se puede descartar bajo -Werror.
//   D-C  schema_version / source_sensor son CAMPOS del Row, no constantes. El to_row de
//        aRGus los fija a "1"/"argus"; el de Suricata fijará "suricata". La lib no los
//        conoce. (Antes eran constantes en build_row -> impedían otra fuente.)
//   D-D  El símbolo de col 17 ya llega RESUELTO como string (to_row hizo el mapeo enum).
//        El guard de "símbolo legal" es CAMBIO DE CONTRATO, DIFERIDO a commit posterior
//        al refactor byte-idéntico. v1 de validate() NO lo incluye (preserva bytes).
//   D-E  imbue(std::locale::classic()) en CADA stream, dentro de la lib. Hallazgo P0:
//        bajo es_ES los enteros/decimales saldrían con separador de millares/coma y los
//        bytes se romperían. Hoy solo se salva por el locale global classic del proceso.
//        Defensa en profundidad: la lib no confía en el locale ambiental.
//   D-F  community_id vacío = SKIP (filtrado legítimo), lo gestiona to_row y NO llega
//        a la lib. Defensa en profundidad: si un Row con community_id vacío llega aquí,
//        validate() lo trata como Error (bug del productor), no como dato válido.
#pragma once

#include <cstdint>
#include <string>
#include <vector>

namespace correlation_v1 {

inline constexpr size_t TOTAL_COLS = 19;   // 0-17 datos + 18 HMAC

// ----------------------------------------------------------------------------
// CorrelationV1Row — lingua franca entre los 5 productores. Datos cols 0-17.
// La col 18 (HMAC) la calcula serialize(); no se almacena en el Row.
// Tipos trazados 1:1 contra el oráculo (correlation_writer.cpp build_row):
//   - texto: std::string  - secs/nanos: int64/int32  - ports: uint32  - scores: double
// authoritative_source: string YA resuelto por to_row (DetectorSource_Name en aRGus,
// lógica propia en cada adapter). La lib lo serializa fielmente; quién es legal es
// asunto de validate() (P3), no de la serialización.
// ----------------------------------------------------------------------------
struct CorrelationV1Row {
    std::string schema_version;        // 0   (D-C: campo, no constante)
    std::string source_sensor;         // 1   (D-C: campo, no constante)
    std::string event_id;              // 2
    std::string node_id;               // 3   (originating_node_id en el evento)
    std::string community_id;          // 4   clave de join
    int64_t     flow_start_sec = 0;    // 5   (ts.seconds())
    int32_t     flow_start_nano = 0;   // 6   (ts.nanos())
    std::string src_ip;                // 7
    std::string dst_ip;                // 8
    uint32_t    src_port = 0;          // 9
    uint32_t    dst_port = 0;          // 10
    std::string protocol;              // 11  (protocol_name)
    std::string final_classification;  // 12
    std::string threat_category;       // 13
    double      fast_detector_score = 0.0;    // 14
    double      ml_detector_score = 0.0;      // 15
    double      overall_threat_score = 0.0;   // 16
    std::string authoritative_source;  // 17  (símbolo DetectorSource ya resuelto)
};

// ----------------------------------------------------------------------------
// Resultados tipados (D-A). [[nodiscard]] sobre el TIPO: ni este ni ningún
// productor futuro puede descartar el fallo bajo -Werror.
// ----------------------------------------------------------------------------
struct [[nodiscard]] ValidationResult {
    bool ok = false;
    std::string error;                 // diagnóstico ruidoso si !ok; vacío si ok
    explicit operator bool() const noexcept { return ok; }
};

struct [[nodiscard]] SerializeResult {
    bool ok = false;
    std::string line;                  // cols 0-18 listas para append; vacío si !ok
    std::string error;                 // diagnóstico ruidoso si !ok; vacío si ok
    explicit operator bool() const noexcept { return ok; }
};

// ----------------------------------------------------------------------------
// validate — NOTARIO ÚNICO del contrato (P3). Invariantes ESTRUCTURALES que TODO
// productor debe cumplir, independientes de quién construyó el Row.
//
//   v1 (REFACTOR byte-idéntico, este commit): solo invariantes que el código de
//       DAY 184 YA exigía implícitamente. NO añade el guard de col 17 -> los bytes
//       sobre todo el dominio del golden quedan idénticos al oráculo.
//   v2 (COMMIT DE CONTRATO, diferido — D-D): añade exigencia de símbolo legal en
//       col 17 (DetectorSource ∈ {7 símbolos}). Esto DIVERGE del oráculo a propósito
//       sobre el dominio drift; por eso va en su propio commit con su propio test (P2),
//       no mezclado con la afirmación "reubicación byte-idéntica".
// ----------------------------------------------------------------------------
[[nodiscard]] ValidationResult validate(const CorrelationV1Row& row) noexcept;

// ----------------------------------------------------------------------------
// serialize — Row -> línea bronce completa (cols 0-18 incl. HMAC sobre 0-17).
//
// PURA: función de (row, hmac_key) y NADA más.
//   · sin reloj           (flow_start_* son datos del Row; ingested_at NO vive aquí,
//                          eso era la capa grafo del KuzuGraphSink, DAY 184)
//   · sin locale ambiental (imbue classic interno — D-E)
//   · sin red, sin fichero
//   · sin fetch de clave  (hmac_key es INPUT — el caller la trae de donde sea:
//                          ARGUS_BRONZE_HMAC_KEY_HEX en test, etcd-server en el adapter)
//
// Llama a validate() primero (P3): un Row que validate rechaza, serialize NO lo emite.
// hmac_key: 32 bytes (decodificados de los 64 hex chars por el caller).
// ----------------------------------------------------------------------------
[[nodiscard]] SerializeResult serialize(const CorrelationV1Row& row,
                                        const std::vector<uint8_t>& hmac_key);

} // namespace correlation_v1