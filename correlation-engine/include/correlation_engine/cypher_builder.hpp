// cypher_builder.hpp — generacion de Cypher compartida por todos los IGraphSink.
// aRGus NDR — DAY 180 / refactor DAY 183 (ADR-057: prepared statements parametrizados).
// Authors: Alonso Isidoro Roman + Claude (Anthropic).
//
// Emite el modelo del schema.cypher (ADR-052):
//   (NetworkFlow identidad pura) <-[:ALERT_ABOUT|TELEMETRY_ABOUT {method,confidence}]- (Alert|TelemetryEvent con veredicto)
//
// INVARIANTE "bronce PRESERVA, gold DECIDE": el sink NO recalcula veredicto, lo LEE.
//   is_alert == (final_classification == "MALICIOUS"), ya decidido por el ml-detector.
//
// DAY 183 — DOS CAMINOS, MISMO MODELO, MISMOS VALORES DERIVADOS:
//   (a) make_bindings()  -> valores derivados (window, temporal_anomaly) en tipos C++ planos.
//                           FUENTE UNICA. Kuzu-free (este header lo incluye LoggingGraphSink).
//   (b) kAlert/kTelemetryCypherTemplate -> plantillas PARAMETRIZADAS ($param), preparadas
//                           una vez por el KuzuGraphSink. Labels/rel-types LITERALES (Cypher
//                           no parametriza estructura). El marshaling record->kuzu::Value vive
//                           en kuzu_graph_sink.cpp (NO aqui: este header no arrastra Kuzu).
//   (c) build_cypher()   -> path de LOGGING. Rebasado sobre make_bindings() para que los
//                           valores derivados sean IDENTICOS a (b). La interpolacion (esc +
//                           locale::classic) vive SOLO aqui: es vista de depuracion, NO se
//                           ejecuta. H-1 se cierra en el path EJECUTADO via (b), no via esc.
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

// ADR-057 F0: anomalia temporal UNILATERAL (solo futuro): el flujo dice empezar TRAS su
// propia ingesta -> firma de clock-injection. kTemporalMarginNs absorbe skew NTP
// sensor<->engine -> A CALIBRAR con dato real (medir, no votar). DEBT: 2s es placeholder.
inline constexpr uint64_t kTemporalMarginNs = 2'000'000'000ULL;  // 2s placeholder

// Valores derivados de un registro de bronce YA verificado, en tipos C++ planos.
// FUENTE UNICA de los derivados (window, temporal_anomaly): la consumen el binder Kuzu
// (kuzu_graph_sink.cpp) y el path de logging (build_cypher) -> imposible que diverjan.
// Los string_view apuntan al record + flow_uid del llamante: deben seguir vivos mientras
// se construyen los kuzu::Value (lo estan: es el record que se esta escribiendo).
struct CypherBindings {
    bool             is_alert;
    std::string_view flow_uid;
    std::string_view node_id;
    std::string_view community_id;
    std::string_view source_sensor;
    std::string_view event_id;
    std::string_view final_classification;
    std::string_view threat_category;
    std::string_view authoritative_source;
    uint64_t         flow_start_window;
    uint32_t         seq_in_window;
    uint64_t         ingested_at;
    bool             temporal_anomaly;
    double           fast_detector_score;
    double           ml_detector_score;
    double           overall_threat_score;
};

// flow_uid se calcula server-side (compute_flow_uid) ANTES de llamar.
// flow_start_window se recomputa aqui desde el record (mismo valor que alimento flow_uid).
// seq_in_window = 0 hoy (DEBT-FLOWUID-SEQ-COLLISION-001).
inline CypherBindings make_bindings(const CorrelationRecord& r, std::string_view flow_uid,
                                    uint64_t ingested_at_ns) {
    const uint64_t window = window_micros(r.flow_start_sec, r.flow_start_nano);
    return CypherBindings{
        /* is_alert             */ is_alert(r),
        /* flow_uid             */ flow_uid,
        /* node_id              */ r.node_id,
        /* community_id         */ r.community_id,
        /* source_sensor        */ r.source_sensor,
        /* event_id             */ r.event_id,
        /* final_classification */ r.final_classification,
        /* threat_category      */ r.threat_category,
        /* authoritative_source */ r.authoritative_source,
        /* flow_start_window    */ window,
        /* seq_in_window        */ 0u,  // DEBT-FLOWUID-SEQ-COLLISION-001
        /* ingested_at          */ ingested_at_ns,
        // ADR-057 F0: window=epoch-us, ingested_at=epoch-ns -> comparo en ns.
        /* temporal_anomaly     */ window_to_epoch_nanos(window) > (ingested_at_ns + kTemporalMarginNs),
        /* fast_detector_score  */ r.fast_detector_score,
        /* ml_detector_score    */ r.ml_detector_score,
        /* overall_threat_score */ r.overall_threat_score,
    };
}

// ── Plantillas PARAMETRIZADas (ADR-057: cero interpolacion de datos de red) ──────────
// UN solo statement con 3 MERGE encadenados (e, f cruzan el statement) = escritura
// atomica por registro. Labels y rel-types LITERALES (no parametrizables). method y
// confidence LITERALES (constantes F1; ADR-054 los hara params con metodos NAT).
// $flow_uid/$node_id/$community_id/$ingested_at se referencian 2 veces (f y e): se
// bindean una vez, se usan N. Las dos plantillas solo difieren en label + rel-type.
inline constexpr std::string_view kAlertCypherTemplate = R"CYPHER(
MERGE (f:NetworkFlow {flow_uid:$flow_uid})
ON CREATE SET f.node_id=$node_id, f.community_id=$community_id, f.flow_start_window=$flow_start_window, f.seq_in_window=$seq_in_window, f.ingested_at=$ingested_at, f.temporal_anomaly=$temporal_anomaly
MERGE (e:Alert {event_id:$event_id})
ON CREATE SET e.node_id=$node_id, e.flow_uid=$flow_uid, e.community_id=$community_id, e.source_sensor=$source_sensor, e.final_classification=$final_classification, e.threat_category=$threat_category, e.fast_detector_score=$fast_detector_score, e.ml_detector_score=$ml_detector_score, e.overall_threat_score=$overall_threat_score, e.authoritative_source=$authoritative_source, e.ingested_at=$ingested_at
MERGE (e)-[rel:ALERT_ABOUT]->(f)
ON CREATE SET rel.method='direct', rel.confidence=1.0
)CYPHER";

inline constexpr std::string_view kTelemetryCypherTemplate = R"CYPHER(
MERGE (f:NetworkFlow {flow_uid:$flow_uid})
ON CREATE SET f.node_id=$node_id, f.community_id=$community_id, f.flow_start_window=$flow_start_window, f.seq_in_window=$seq_in_window, f.ingested_at=$ingested_at, f.temporal_anomaly=$temporal_anomaly
MERGE (e:TelemetryEvent {event_id:$event_id})
ON CREATE SET e.node_id=$node_id, e.flow_uid=$flow_uid, e.community_id=$community_id, e.source_sensor=$source_sensor, e.final_classification=$final_classification, e.threat_category=$threat_category, e.fast_detector_score=$fast_detector_score, e.ml_detector_score=$ml_detector_score, e.overall_threat_score=$overall_threat_score, e.authoritative_source=$authoritative_source, e.ingested_at=$ingested_at
MERGE (e)-[rel:TELEMETRY_ABOUT]->(f)
ON CREATE SET rel.method='direct', rel.confidence=1.0
)CYPHER";

inline std::string_view cypher_template(bool alert) noexcept {
    return alert ? kAlertCypherTemplate : kTelemetryCypherTemplate;
}

namespace detail {
// Escapa literal Cypher. SOLO para el path de LOGGING (build_cypher): NO es la defensa
// H-1 del path ejecutado (eso son los prepared statements de arriba). Se mantiene para
// que el Cypher logueado sea fiel. Backslash ANTES que comilla (clase backslash).
inline std::string esc(std::string_view s) {
    std::string out;
    out.reserve(s.size());
    for (char c : s) {
        if (c == '\\')      out += "\\\\";   // backslash primero
        else if (c == '\'') out += "\\'";
        else                out += c;
    }
    return out;
}
}  // namespace detail

// build_cypher — PATH DE LOGGING. Rebasado sobre make_bindings(): valores derivados
// identicos al path parametrizado. Interpolacion (esc + locale::classic) vive SOLO aqui;
// este string NO se ejecuta contra Kuzu (lo emite LoggingGraphSink como vista de debug).
// Salida byte-identica a la version DAY 180 -> LoggingGraphSink no cambia de comportamiento.
inline std::string build_cypher(const CorrelationRecord& r, std::string_view flow_uid,
                                uint64_t ingested_at_ns) {
    using detail::esc;
    const CypherBindings b = make_bindings(r, flow_uid, ingested_at_ns);
    const char* evt_label = b.is_alert ? "Alert"       : "TelemetryEvent";
    const char* rel_label = b.is_alert ? "ALERT_ABOUT" : "TELEMETRY_ABOUT";
    const std::string fuid = esc(b.flow_uid);

    std::ostringstream q;
    q.imbue(std::locale::classic());   // CRITICO en interpolacion: es_ES -> coma decimal / separador de miles
    q.precision(17);                   // round-trip de double

    // 1. NetworkFlow — identidad pura.
    q << "MERGE (f:NetworkFlow {flow_uid:'" << fuid << "'}) "
      << "ON CREATE SET "
      << "f.node_id='" << esc(b.node_id) << "', "
      << "f.community_id='" << esc(b.community_id) << "', "
      << "f.flow_start_window=" << b.flow_start_window << ", "
      << "f.seq_in_window=" << b.seq_in_window << ", "
      << "f.ingested_at=" << b.ingested_at << ", "
      << "f.temporal_anomaly=" << (b.temporal_anomaly ? "true" : "false") << " ";

    // 2. Alert | TelemetryEvent — veredicto (cols 12-17 del contrato correlation_v1).
    q << "MERGE (e:" << evt_label << " {event_id:'" << esc(b.event_id) << "'}) "
      << "ON CREATE SET "
      << "e.node_id='" << esc(b.node_id) << "', "
      << "e.flow_uid='" << fuid << "', "
      << "e.community_id='" << esc(b.community_id) << "', "
      << "e.source_sensor='" << esc(b.source_sensor) << "', "
      << "e.final_classification='" << esc(b.final_classification) << "', "
      << "e.threat_category='" << esc(b.threat_category) << "', "
      << "e.fast_detector_score=" << b.fast_detector_score << ", "
      << "e.ml_detector_score=" << b.ml_detector_score << ", "
      << "e.overall_threat_score=" << b.overall_threat_score << ", "
      << "e.authoritative_source='" << esc(b.authoritative_source) << "', "
      << "e.ingested_at=" << b.ingested_at << " ";

    // 3. (evento)-[*_ABOUT {method,confidence}]->(flujo). F1 single-node: direct/1.0.
    q << "MERGE (e)-[rel:" << rel_label << "]->(f) "
      << "ON CREATE SET rel.method='direct', rel.confidence=1.0";

    return q.str();
}

}  // namespace argus::correlation