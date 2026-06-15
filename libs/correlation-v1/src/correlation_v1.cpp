// correlation_v1.cpp
// aRGus NDR — libcorrelation_v1: implementación de la capa de serialización bronce.
// Authors: Alonso Isidoro Roman + Claude (Anthropic)
//
// CANDIDATO DE MIGRACIÓN (DAY 185). Transcripción byte-fiel del tramo de
// serialización de ml-detector/correlation_writer.cpp (build_row + compute_hmac +
// fmt_double + csv_string), reparametrizada de NetworkSecurityEvent -> CorrelationV1Row.
//
// GREEN NO lo declara este fichero. Lo declara el golden de caracterización del PASO B
// (capturado contra el binario actual, en el working tree con 4e221ede/112b9df1):
//     serialize(to_row(event)).line  ==  golden_bytes(event)   // byte a byte
//
// ÚNICA DESVIACIÓN INTENCIONADA vs oráculo: imbue(std::locale::classic()) en los
// streams (D-E). No-op sobre el golden (locale global ya classic); cierra el bug
// latente bajo es_ES (millares / decimal con coma).

#include "correlation_v1/correlation_v1.hpp"

#include <cmath>
#include <iomanip>
#include <locale>
#include <sstream>
#include <string>

#include <openssl/hmac.h>
#include <openssl/evp.h>

namespace correlation_v1 {

namespace {

// --- csv_string — COPIA VERBATIM del oráculo (manipulación de chars, locale-safe) --
std::string csv_string(const std::string& s) {
    bool needs_quote = s.find_first_of(",\"\n") != std::string::npos;
    if (!needs_quote) return s;
    std::string out = "\"";
    for (char c : s) { if (c == '"') out += "\"\""; else out += c; }
    out += "\"";
    return out;
}

// --- fmt_double — oráculo + imbue(classic) (D-E: garantiza '.' decimal, sin millares) -
std::string fmt_double(double v) {
    if (std::isnan(v) || std::isinf(v)) return "0.000000";
    std::ostringstream ss;
    ss.imbue(std::locale::classic());                  // D-E
    ss << std::fixed << std::setprecision(6) << v;
    return ss.str();
}

// --- compute_hmac — COPIA VERBATIM del oráculo; key pasa a parámetro (no member) -----
// Hex de bytes < 256: sin agrupación numpunct posible, locale-safe -> sin imbue,
// idéntico al oráculo (que tampoco lo imbuía).
std::string compute_hmac(const std::string& content, const std::vector<uint8_t>& key) {
    unsigned char digest[EVP_MAX_MD_SIZE];
    unsigned int digest_len = 0;
    HMAC(EVP_sha256(), key.data(), static_cast<int>(key.size()),
         reinterpret_cast<const unsigned char*>(content.data()), content.size(),
         digest, &digest_len);
    std::ostringstream ss;
    ss << std::hex << std::setfill('0');
    for (unsigned int i = 0; i < digest_len; ++i)
        ss << std::setw(2) << static_cast<unsigned int>(digest[i]);
    return ss.str();
}

// --- build_cols_0_17 — réplica exacta del orden/separadores/quoting del oráculo ------
// cols 0,1,5,6,9,10 en CRUDO (como el oráculo). Meterles csv_string sería
// endurecimiento -> commit de contrato, no este refactor byte-idéntico.
std::string build_cols_0_17(const CorrelationV1Row& r) {
    std::ostringstream ss;
    ss.imbue(std::locale::classic());                            // D-E
    ss << r.schema_version                                       // 0  (crudo)
       << ',' << r.source_sensor                                 // 1  (crudo)
       << ',' << csv_string(r.event_id)                          // 2
       << ',' << csv_string(r.node_id)                           // 3
       << ',' << csv_string(r.community_id)                      // 4  clave de join
       << ',' << r.flow_start_sec                                // 5  (crudo int64)
       << ',' << r.flow_start_nano                               // 6  (crudo int32)
       << ',' << csv_string(r.src_ip)                            // 7
       << ',' << csv_string(r.dst_ip)                            // 8
       << ',' << r.src_port                                      // 9  (crudo uint32)
       << ',' << r.dst_port                                      // 10 (crudo uint32)
       << ',' << csv_string(r.protocol)                          // 11
       << ',' << csv_string(r.final_classification)              // 12
       << ',' << csv_string(r.threat_category)                   // 13
       << ',' << fmt_double(r.fast_detector_score)               // 14
       << ',' << fmt_double(r.ml_detector_score)                 // 15
       << ',' << fmt_double(r.overall_threat_score)              // 16
       << ',' << csv_string(r.authoritative_source);             // 17 (símbolo ya resuelto)
    return ss.str();
}

} // anonymous namespace

// ----------------------------------------------------------------------------
// validate — NOTARIO ÚNICO (P3). v1: solo invariantes pre-existentes del oráculo.
// ----------------------------------------------------------------------------
ValidationResult validate(const CorrelationV1Row& row) noexcept {
    // D-F (defensa en profundidad): community_id vacío = clave de join ausente.
    // to_row debió emitir SKIP; si una fila así llega aquí, es bug del productor.
    // No toca el golden: el oráculo ya saltaba (no escribía) estas filas.
    if (row.community_id.empty()) {
        return ValidationResult{
            false, "community_id vacío: clave de join ausente (to_row debió hacer SKIP)"};
    }

    // D-D — DIFERIDO al commit de contrato. v1 NO exige símbolo legal en col 17,
    // para preservar byte-identidad con el oráculo sobre el dominio drift.
    // En el commit de contrato, añadir aquí:
    //   if (!es_simbolo_DetectorSource_legal(row.authoritative_source))
    //       return {false, "col 17: símbolo DetectorSource desconocido (drift de contrato)"};

    return ValidationResult{true, ""};
}

// ----------------------------------------------------------------------------
// serialize — Row -> línea bronce (cols 0-18). PURA: (row, hmac_key) y nada más.
// Embuda por validate() primero (P3). Sin newline final: lo añade la capa de I/O.
// ----------------------------------------------------------------------------
SerializeResult serialize(const CorrelationV1Row& row,
                          const std::vector<uint8_t>& hmac_key) {
    // P3 — notario único: lo que validate rechaza, serialize no emite.
    if (auto v = validate(row); !v) {
        return SerializeResult{false, "", v.error};
    }

    // Ausencia/longitud incorrecta de clave = error RUIDOSO (plan DAY 185).
    // Contrato: 32 bytes (decodificados de 64 hex chars por el caller).
    if (hmac_key.size() != 32) {
        return SerializeResult{
            false, "",
            "hmac_key debe ser 32 bytes (got " + std::to_string(hmac_key.size()) +
            "): clave ausente o incorrecta"};
    }

    const std::string cols_0_17 = build_cols_0_17(row);          // cols 0-17
    const std::string hmac      = compute_hmac(cols_0_17, hmac_key); // col 18
    return SerializeResult{true, cols_0_17 + "," + hmac, ""};
}

} // namespace correlation_v1