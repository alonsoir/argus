// zeek-adapter/src/to_row.cpp
// aRGus NDR — Zeek conn.log (TSV) -> CorrelationV1Row.
//
// ⚠️ Zeek es TELEMETRÍA (F1 0.042, DAY 85-143), no clasificador. Cada fila de conn.log
//    es una CONEXIÓN -> TelemetryEvent. Cols de veredicto VACÍAS (D6): texto "" y scores 0.0.
//
// Decisiones (puerta-diseno-multisensor.md):
//   D3  event_id = "zeek:" + base64(BLAKE2b-256(community_id ‖ ts)).
//       NO usa el `uid` de Zeek: MEDIDO DAY 235, inestable entre replays del mismo pcap.
//   D4  flow_start = `ts` (inicio de conexión). Epoch double, NO ISO8601.
//   D5  descarte explícito con motivo.  D6  ausencia documentada (scores 0.0, texto "").
//
// TSV, NO JSON: este componente no toca nlohmann. Campos por nombre del `#fields`.

#include "zeek_adapter/to_row.hpp"

#include <sodium.h>

#include <cstdint>
#include <string>
#include <vector>

namespace zeek_adapter {
namespace {

constexpr char kFieldSep = '\x1f';  // separador inyectivo de la preimagen (igual que Suricata)

std::vector<std::string> split_tab(const std::string& line) {
    std::vector<std::string> out;
    std::size_t start = 0, tab;
    while ((tab = line.find('\t', start)) != std::string::npos) {
        out.push_back(line.substr(start, tab - start));
        start = tab + 1;
    }
    out.push_back(line.substr(start));
    return out;
}

// "1027" -> uint32; 0 si vacío/no numérico. Para ICMP, Zeek codifica type/code aquí
// (igual que Suricata); se copian tal cual como puertos.
std::uint32_t to_u32(const std::string& s) {
    std::uint32_t v = 0;
    for (char c : s) { if (c < '0' || c > '9') return 0; v = v * 10 + std::uint32_t(c - '0'); }
    return v;
}

}  // namespace

bool ConnFieldIndex::get(const std::vector<std::string>& cols,
                         const std::string& name, std::string& out) const {
    auto it = pos.find(name);
    if (it == pos.end() || it->second >= cols.size()) return false;
    const std::string& v = cols[it->second];
    if (v == ZEEK_UNSET_FIELD) return false;   // '-' = escalar ausente
    out = v;
    return true;
}

ConnFieldIndex parse_conn_fields(const std::string& fields_line) {
    ConnFieldIndex idx;
    const std::vector<std::string> toks = split_tab(fields_line);
    if (toks.empty() || toks[0] != "#fields") return idx;       // vacío -> el driver lo detecta
    for (std::size_t i = 1; i < toks.size(); ++i) idx.pos[toks[i]] = i - 1;  // -1: descarta `#fields`
    return idx;
}

ToRowResult ToRowResult::ok(correlation_v1::CorrelationV1Row r) { ToRowResult t; t.status = Status::Ok; t.row = std::move(r); return t; }
ToRowResult ToRowResult::skip(std::string why)  { ToRowResult t; t.status = Status::Skip;  t.reason = std::move(why);  return t; }
ToRowResult ToRowResult::error(std::string what){ ToRowResult t; t.status = Status::Error; t.reason = std::move(what); return t; }

// "1312967066.683089" -> secs=1312967066, nanos=683089000.
bool parse_zeek_ts(const std::string& ts, int64_t& secs, int32_t& nanos) {
    if (ts.empty()) return false;
    const std::size_t dot = ts.find('.');
    const std::string sec_part = (dot == std::string::npos) ? ts : ts.substr(0, dot);
    if (sec_part.empty()) return false;

    int64_t s = 0;
    for (char c : sec_part) { if (c < '0' || c > '9') return false; s = s * 10 + (c - '0'); }

    int64_t frac = 0; int digits = 0;
    if (dot != std::string::npos) {
        for (std::size_t i = dot + 1; i < ts.size() && digits < 9; ++i) {
            const char c = ts[i]; if (c < '0' || c > '9') return false;
            frac = frac * 10 + (c - '0'); ++digits;
        }
        for (int i = digits; i < 9; ++i) frac *= 10;  // pad a nanos
    }
    secs = s; nanos = static_cast<int32_t>(frac);
    return true;
}

// D3. Determinista: mismo conn.log -> mismo event_id -> reprocesar no duplica nodos.
std::string make_event_id(const std::string& community_id, const std::string& ts) {
    std::string preimage;
    preimage.reserve(community_id.size() + ts.size() + 1);
    preimage.append(community_id); preimage.push_back(kFieldSep); preimage.append(ts);

    unsigned char digest[32];
    crypto_generichash(digest, sizeof(digest),
                       reinterpret_cast<const unsigned char*>(preimage.data()), preimage.size(),
                       nullptr, 0);

    char b64[sodium_base64_ENCODED_LEN(sizeof(digest), sodium_base64_VARIANT_ORIGINAL)];
    sodium_bin2base64(b64, sizeof(b64), digest, sizeof(digest), sodium_base64_VARIANT_ORIGINAL);
    return std::string(EVENT_ID_PREFIX) + b64;
}

ToRowResult to_row(const std::string& line, const ConnFieldIndex& fields, const std::string& node_id) {
    if (line.empty())    return ToRowResult::skip("linea vacia");
    if (line[0] == '#')  return ToRowResult::skip("linea de preambulo");  // defensivo

    const std::vector<std::string> cols = split_tab(line);

    // D5 — sin community_id no hay identidad. MEDIDO DAY 235: 31.735/31.735 lo traen
    // (skip cuenta 0 hoy; existe por contrato, no por costumbre).
    std::string community_id;
    if (!fields.get(cols, "community_id", community_id)) return ToRowResult::skip("sin community_id");

    // D4 — flow_start = ts (epoch double).
    std::string ts;
    if (!fields.get(cols, "ts", ts)) return ToRowResult::error("fila sin ts");
    int64_t secs = 0; int32_t nanos = 0;
    if (!parse_zeek_ts(ts, secs, nanos)) return ToRowResult::error("ts no parseable: " + ts);

    std::string src_ip, dst_ip, src_port, dst_port, proto;
    fields.get(cols, "id.orig_h", src_ip);
    fields.get(cols, "id.resp_h", dst_ip);
    fields.get(cols, "id.orig_p", src_port);
    fields.get(cols, "id.resp_p", dst_port);
    fields.get(cols, "proto",     proto);

    correlation_v1::CorrelationV1Row r;
    r.schema_version  = SCHEMA_VERSION;                  // 0
    r.source_sensor   = CORRELATION_SOURCE_SENSOR;       // 1
    r.event_id        = make_event_id(community_id, ts); // 2
    r.node_id         = node_id;                         // 3
    r.community_id    = community_id;                    // 4
    r.flow_start_sec  = secs;                            // 5
    r.flow_start_nano = nanos;                           // 6
    r.src_ip          = src_ip;                          // 7
    r.dst_ip          = dst_ip;                          // 8
    r.src_port        = to_u32(src_port);                // 9
    r.dst_port        = to_u32(dst_port);                // 10
    r.protocol        = proto;                           // 11  ⚠️ minúsculas (ver D-proto-case)

    // D6 — Zeek NO clasifica.
    r.final_classification = "";                         // 12
    r.threat_category      = "";                         // 13
    r.fast_detector_score  = 0.0;                        // 14
    r.ml_detector_score    = 0.0;                        // 15
    r.overall_threat_score = 0.0;                        // 16

    r.authoritative_source = AUTHORITATIVE_SOURCE;       // 17
    // col 18 (HMAC) la calcula serialize(); no vive en el Row.

    return ToRowResult::ok(std::move(r));
}

}  // namespace zeek_adapter