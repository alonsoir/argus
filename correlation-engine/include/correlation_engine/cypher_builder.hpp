// cypher_builder.hpp — generacion de Cypher compartida por todos los IGraphSink.
// aRGus NDR — DAY 180. Authors: Alonso Isidoro Roman + Claude (Anthropic).
//
// Emite el modelo del schema.cypher (ADR-052):
//   (NetworkFlow identidad pura) <-[:ALERT_ABOUT|TELEMETRY_ABOUT {method,confidence}]- (Alert|TelemetryEvent con veredicto)
//
// INVARIANTE "bronce PRESERVA, gold DECIDE": el sink NO recalcula veredicto, lo LEE.
//   is_alert == (final_classification == "MALICIOUS"), ya decidido por el ml-detector
//   (zmq_handler.cpp:438: final_score >= malicious_threshold ? "MALICIOUS" : "BENIGN").
//
// La 5-tupla y los scores NO van en NetworkFlow: viven en bronce + Parquet ORO.
// El veredicto SI va en Alert/TelemetryEvent (intrinseco a la entidad -> nodo);
// method/confidence describen la relacion evento<->flujo -> arista.
#pragma once
#include "correlation_engine/correlation_record.hpp"
#include "correlation_engine/flow_uid.hpp"

#include <cstdint>
#include <locale>
#include <sstream>
#include <string>
#include <string_view>

namespace argus::correlation {

// Enrutado Alert vs TelemetryEvent. final_classification es binario y siempre poblado.
inline bool is_alert(const CorrelationRecord& r) noexcept {
    return r.final_classification == "MALICIOUS";
}

namespace detail {
// Escapa comilla simple para literal Cypher. node_id/community_id son opacos.
inline std::string esc(std::string_view s) {
    std::string out;
    out.reserve(s.size());
    for (char c : s) { if (c == '\'') out += "\\'"; else out += c; }
    return out;
}
}  // namespace detail

// Construye el Cypher de materializacion para un registro de bronce YA verificado.
// flow_uid se calcula server-side (compute_flow_uid) ANTES de llamar.
// flow_start_window se recomputa aqui desde el record (mismo valor que alimento flow_uid).
// seq_in_window = 0 hoy (DEBT-FLOWUID-SEQ-COLLISION-001).
//
// DIALECTO KUZU: MERGE {pk} ON CREATE SET. Las propiedades son deterministas sobre el
// mismo input, asi que la re-llegada por dedup (ON MATCH) no necesita re-SET. Un solo
// statement con 3 MERGE encadenados -> escritura atomica por registro (auto-commit Kuzu).
inline std::string build_cypher(const CorrelationRecord& r, std::string_view flow_uid) {
    using detail::esc;
    const uint64_t window  = window_micros(r.flow_start_sec, r.flow_start_nano);
    const uint32_t seq     = 0;  // DEBT-FLOWUID-SEQ-COLLISION-001
    const bool alert       = is_alert(r);
    const char* evt_label  = alert ? "Alert"       : "TelemetryEvent";
    const char* rel_label  = alert ? "ALERT_ABOUT" : "TELEMETRY_ABOUT";
    const std::string fuid = esc(flow_uid);

    std::ostringstream q;
    q.imbue(std::locale::classic());   // CRITICO: locale es_ES del guest -> coma decimal en doubles
    q.precision(17);                   // round-trip de double

    // 1. NetworkFlow — identidad pura.
    q << "MERGE (f:NetworkFlow {flow_uid:'" << fuid << "'}) "
      << "ON CREATE SET "
      << "f.node_id='" << esc(r.node_id) << "', "
      << "f.community_id='" << esc(r.community_id) << "', "
      << "f.flow_start_window=" << window << ", "
      << "f.seq_in_window=" << seq << " ";

    // 2. Alert | TelemetryEvent — veredicto (cols 12-17 del contrato correlation_v1).
    q << "MERGE (e:" << evt_label << " {event_id:'" << esc(r.event_id) << "'}) "
      << "ON CREATE SET "
      << "e.node_id='" << esc(r.node_id) << "', "
      << "e.flow_uid='" << fuid << "', "
      << "e.community_id='" << esc(r.community_id) << "', "
      << "e.final_classification='" << esc(r.final_classification) << "', "
      << "e.threat_category='" << esc(r.threat_category) << "', "
      << "e.fast_detector_score=" << r.fast_detector_score << ", "
      << "e.ml_detector_score=" << r.ml_detector_score << ", "
      << "e.overall_threat_score=" << r.overall_threat_score << ", "
      << "e.authoritative_source='" << esc(r.authoritative_source) << "' ";

    // 3. (evento)-[*_ABOUT {method,confidence}]->(flujo). F1 single-node: direct/1.0.
    //    Metodos NAT/cross-nodo (confidence<1) -> multi-nodo (ADR-054).
    q << "MERGE (e)-[rel:" << rel_label << "]->(f) "
      << "ON CREATE SET rel.method='direct', rel.confidence=1.0";

    return q.str();
}

}  // namespace argus::correlation