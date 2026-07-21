// suricata-adapter/src/to_row.cpp
// aRGus NDR — eve.json (Suricata) -> CorrelationV1Row.
//
// ⚠️ ÚNICO FICHERO DEL COMPONENTE QUE TOCA JSON. Es deliberado: si el repo no usa
//    nlohmann sino rapidjson/simdjson, se reescribe este fichero y nada más.
//
// Decisiones aplicadas (docs/design/multisensor-graph-identity/puerta-diseno-multisensor.md):
//   D3  event_id = "suricata:" + base64(BLAKE2b-256(timestamp ‖ flow_id ‖ sid ‖ community_id))
//   D5  descarte explícito con motivo (stats, decoder sin flujo, telemetría)
//   D6  los 3 scores quedan a 0.0 = ausencia documentada; el consumidor filtra por
//       source_sensor. Los de TEXTO sí se mapean:
//         final_classification <- alert.signature
//         threat_category      <- alert.category
//       alert.severity SE PIERDE (ordinal 1-3, no probabilidad). Rederivable desde
//       la signature.

#include "suricata_adapter/to_row.hpp"

#include <cstring>
#include <ctime>
#include <string>

#include <nlohmann/json.hpp>
#include <sodium.h>

namespace suricata_adapter {

namespace {

// Separador de campos en la preimagen del event_id. Marca de campo no imprimible
// para que la concatenación sea inyectiva ante valores con caracteres raros.
// ⚠️ DECISIÓN NO RATIFICADA (DAY 226): la puerta de diseño dice "timestamp ‖ flow_id ‖
//    signature_id ‖ community_id" sin fijar la codificación. flow_uid.hpp usa
//    length-prefix canónico; aquí se usa separador. Unificar o documentar la diferencia.
constexpr char kFieldSep = '\x1f';

std::string json_str(const nlohmann::json& j, const char* key) {
    auto it = j.find(key);
    if (it == j.end() || it->is_null()) return {};
    if (it->is_string()) return it->get<std::string>();
    return it->dump();  // números (flow_id, signature_id) -> su representación
}

}  // namespace

// ---------------------------------------------------------------------------
ToRowResult ToRowResult::ok(correlation_v1::CorrelationV1Row r) {
    ToRowResult t;
    t.status = Status::Ok;
    t.row = std::move(r);
    return t;
}

ToRowResult ToRowResult::skip(std::string why) {
    ToRowResult t;
    t.status = Status::Skip;
    t.reason = std::move(why);
    return t;
}

ToRowResult ToRowResult::error(std::string what) {
    ToRowResult t;
    t.status = Status::Error;
    t.reason = std::move(what);
    return t;
}

// ---------------------------------------------------------------------------
// parse_iso8601 — "2011-08-10T09:04:32.432327+0000" (formato MEDIDO en DAY 225).
// Tolera 'Z', offset con y sin dos puntos, y fracción de 0 a 9 dígitos.
// ---------------------------------------------------------------------------
bool parse_iso8601(const std::string& ts, int64_t& secs, int32_t& nanos) {
    if (ts.size() < 19) return false;

    std::tm tm{};
    const char* rest = strptime(ts.c_str(), "%Y-%m-%dT%H:%M:%S", &tm);
    if (rest == nullptr) return false;

    // Fracción de segundo.
    int64_t frac_ns = 0;
    if (*rest == '.') {
        ++rest;
        int digits = 0;
        int64_t value = 0;
        while (digits < 9 && *rest >= '0' && *rest <= '9') {
            value = value * 10 + (*rest - '0');
            ++digits;
            ++rest;
        }
        while (*rest >= '0' && *rest <= '9') ++rest;  // exceso: se descarta
        for (int i = digits; i < 9; ++i) value *= 10;
        frac_ns = value;
    }

    // Offset del EVENTO (no el de esta máquina).
    int64_t offset_sec = 0;
    if (*rest == '+' || *rest == '-') {
        const int sign = (*rest == '-') ? -1 : 1;
        ++rest;
        if (std::strlen(rest) < 4) return false;
        const int hh = (rest[0] - '0') * 10 + (rest[1] - '0');
        const int mm_off = (rest[2] == ':') ? (rest[3] - '0') * 10 + (rest[4] - '0')
                                            : (rest[2] - '0') * 10 + (rest[3] - '0');
        offset_sec = sign * (hh * 3600 + mm_off * 60);
    } else if (*rest != 'Z' && *rest != '\0') {
        return false;
    }

    const time_t utc = timegm(&tm);          // interpreta tm como UTC
    secs  = static_cast<int64_t>(utc) - offset_sec;
    nanos = static_cast<int32_t>(frac_ns);
    return true;
}

// ---------------------------------------------------------------------------
// make_event_id — D3. Determinista: el mismo eve.json da el mismo event_id en
// cada replay, así que reprocesar no duplica nodos en el grafo.
// NO usa pcap_cnt (existe en replay offline, no garantizado en vivo).
// ---------------------------------------------------------------------------
std::string make_event_id(const std::string& timestamp,
                          const std::string& flow_id,
                          const std::string& signature_id,
                          const std::string& community_id) {
    std::string preimage;
    preimage.reserve(timestamp.size() + flow_id.size() +
                     signature_id.size() + community_id.size() + 3);
    preimage.append(timestamp);    preimage.push_back(kFieldSep);
    preimage.append(flow_id);      preimage.push_back(kFieldSep);
    preimage.append(signature_id); preimage.push_back(kFieldSep);
    preimage.append(community_id);

    unsigned char digest[32];
    crypto_generichash(digest, sizeof(digest),
                       reinterpret_cast<const unsigned char*>(preimage.data()),
                       preimage.size(), nullptr, 0);

    char b64[sodium_base64_ENCODED_LEN(sizeof(digest), sodium_base64_VARIANT_ORIGINAL)];
    sodium_bin2base64(b64, sizeof(b64), digest, sizeof(digest),
                      sodium_base64_VARIANT_ORIGINAL);

    return std::string(EVENT_ID_PREFIX) + b64;
}

// ---------------------------------------------------------------------------
// to_row
// ---------------------------------------------------------------------------
ToRowResult to_row(const std::string& line, const std::string& node_id) {
    if (line.empty()) return ToRowResult::skip("linea vacia");

    nlohmann::json j;
    try {
        j = nlohmann::json::parse(line);
    } catch (const nlohmann::json::parse_error& e) {
        return ToRowResult::error(std::string("json ilegible: ") + e.what());
    }

    const std::string event_type = json_str(j, "event_type");

    // D5 — descarte explícito. `stats` no es un evento de red (medido DAY 225: 2
    // eventos, sin community_id ni flow_id).
    if (event_type == "stats") return ToRowResult::skip("event_type=stats");

    // Hoy solo alertas. La telemetría (dns/http/tls/... = 98,7% del volumen) trae
    // community_id pero flow.start = 0 en los NUEVE tipos (medido DAY 225): cuelga
    // de la conversación por community_id (D4) y necesita su propia ruta.
    if (event_type != "alert") return ToRowResult::skip("event_type=" + event_type);

    // D-F / D5 — sin community_id no hay identidad. Mismo SKIP que el oráculo.
    // (validate() lo rechazaría igual: la política está reforzada por el contrato.)
    const std::string community_id = json_str(j, "community_id");
    if (community_id.empty()) {
        return ToRowResult::skip("sin community_id (decoder sin flujo)");
    }

    // flow.start — MEDIDO DAY 225: presente en 2.870 de 2.872 alertas. NO usar el
    // `timestamp` del evento: en una alerta es la hora de la alerta, no del flujo.
    const auto flow_it = j.find("flow");
    if (flow_it == j.end()) return ToRowResult::skip("alerta sin objeto flow");

    const std::string flow_start = json_str(*flow_it, "start");
    int64_t secs = 0;
    int32_t nanos = 0;
    if (flow_start.empty() || !parse_iso8601(flow_start, secs, nanos)) {
        return ToRowResult::error("flow.start no parseable: " + flow_start);
    }

    const auto alert_it = j.find("alert");
    if (alert_it == j.end()) return ToRowResult::error("event_type=alert sin objeto alert");

    correlation_v1::CorrelationV1Row r;
    r.schema_version  = SCHEMA_VERSION;                                    // 0
    r.source_sensor   = CORRELATION_SOURCE_SENSOR;                         // 1
    r.event_id        = make_event_id(json_str(j, "timestamp"),            // 2
                                      json_str(j, "flow_id"),
                                      json_str(*alert_it, "signature_id"),
                                      community_id);
    r.node_id         = node_id;                                           // 3
    r.community_id    = community_id;                                      // 4
    r.flow_start_sec  = secs;                                              // 5
    r.flow_start_nano = nanos;                                             // 6
    // Cols 7-10 — DEL OBJETO `flow`, NO del nivel superior. MEDIDO DAY 226 sobre
    // las 2.872 alertas del Neris: 2.870 traen flow.src_ip (las 2 que no son
    // exactamente las de decoder, ya descartadas arriba) y **2.853 de 2.870 (99,4%)
    // están INVERTIDAS respecto al nivel superior**.
    //
    // Por qué: el par de nivel superior es el del PAQUETE que disparó la alerta y
    // depende de `direction`; el de `flow` es el del ORIGINADOR del flujo. Copiar el
    // de arriba dejaría src/dst intercambiados entre alertas del MISMO community_id,
    // y con D1 el nodo del grafo ES la conversación.
    //
    // El fallback al nivel superior no se dispara en la práctica; existe para no
    // depender de que `flow` traiga siempre estos campos en otras versiones/capturas.
    const nlohmann::json& ep = flow_it->contains("src_ip") ? *flow_it : j;

    r.src_ip          = json_str(ep, "src_ip");                            // 7
    r.dst_ip          = json_str(ep, "dest_ip");                           // 8
    r.src_port        = ep.value("src_port", 0u);                          // 9
    r.dst_port        = ep.value("dest_port", 0u);                         // 10
    r.protocol        = json_str(j, "proto");                              // 11  (solo nivel superior)

    // D6 — el veredicto propio de Suricata va a los campos de TEXTO. Dejarlos
    // vacíos tiraría a la basura el valor de integrar Suricata.
    r.final_classification = json_str(*alert_it, "signature");             // 12
    r.threat_category      = json_str(*alert_it, "category");              // 13

    // D6 — los 3 scores son `double`: "vacío" NO es representable. Quedan a 0.0
    // como AUSENCIA DOCUMENTADA. El consumidor filtra SIEMPRE por source_sensor.
    // (Opción C, NaN, era la semánticamente correcta; descartada por round-trip
    // sin probar en CSV/Parquet/Kuzu.)
    r.fast_detector_score  = 0.0;                                          // 14
    r.ml_detector_score    = 0.0;                                          // 15
    r.overall_threat_score = 0.0;                                          // 16

    r.authoritative_source = AUTHORITATIVE_SOURCE;                         // 17
    // col 18 (HMAC) la calcula serialize(); no vive en el Row.

    return ToRowResult::ok(std::move(r));
}

}  // namespace suricata_adapter
