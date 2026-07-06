// test_flujo_a_b_equivalence.cpp — DAY 209
// ADR-058 §3.1: predicado de EQUIVALENCIA  Camino-0 ≡ Flujo-A+B.
//
// MISMO bronce -> dos materializaciones independientes del grafo:
//   Camino 0  : process_segment + KuzuGraphSink  (enlace directo, in-process)
//               -- cuerpo de test_bronze_to_kuzu_circuit.cpp.
//   Flujo A+B : bronze_to_gold_converter + parquet_to_kuzu_loader (subprocesos,
//               binarios REALES) -- cuerpo de test_flujo_b_end_to_end.cpp.
// Luego: assert  grafo(C0) == grafo(A+B).  Dos Kuzu de test AISLADOS y
// DESECHABLES en /tmp guest-native (vboxsf rompe mmap), borrados al final.
//
// Los dos caminos escriben el MISMO modelo via cypher_builder.hpp; lo que este
// test verifica es que el round-trip bronce -> AVRO -> Parquet gold -> loader
// preserva bit a bit lo que process_segment mete directo desde bronce.
//
// ── EXCLUSIONES (ADR-058 v3) ─────────────────────────────────────────────────
//   ingested_at      : reloj de pared, capturado en el MOMENTO de ingesta.
//                      Camino 0 y Flujo A+B ingieren en instantes distintos ->
//                      DIVERGEN POR DISEÑO. Excluido.
//   temporal_anomaly : derivado de ingested_at (make_bindings) -> tambien
//                      divergiria. Excluido.
//   Se excluyen POR CONSTRUCCION: no aparecen en NINGUN WHERE de abajo.
//
// ── COMPARACION SIN EXTRACCION TIPADA DE KUZU ────────────────────────────────
//   Unica API de lectura probada en el repo: count_query (query/getNext/toString/
//   stoll). No cribamos getValue<double> de ningun sitio (sink y loader son
//   write-path). En su lugar: MISMA query con literales en el WHERE sobre AMBOS
//   grafos; exigimos que coincidan entre si (equivalencia) Y con el esperado del
//   fixture (medir, no votar -> atrapa el caso "ambos caminos pierden igual").
//   Los double (scores) se comparan con `=` de Cypher = igualdad EXACTA (bit).
//   NOTA (honestidad): esto asume que el parser de literales double de Kuzu
//   produce los mismos bits que C++ para "0.91"/"0.87"/"0.89" (ambos IEEE-754
//   round-to-nearest -> mismos bits). Si alguna linea de score PARPADEA en
//   emecas+++, NO relajar a epsilon: es un hop con perdida real -> nuevo DEBT.
//
// Authors: Alonso Isidoro Roman + Claude (Anthropic)

#include <gtest/gtest.h>

#include "correlation_writer.hpp"
#include "correlation_engine/segment_processor.hpp"   // process_segment
#include "correlation_engine/kuzu_graph_sink.hpp"      // KuzuGraphSink
#include "correlation_engine/flow_uid.hpp"             // window_micros, compute_flow_uid

#include <network_security.pb.h>
#include <google/protobuf/timestamp.pb.h>

#include <kuzu.hpp>

#include <spdlog/spdlog.h>
#include <spdlog/sinks/null_sink.h>

#include <filesystem>
#include <string>
#include <memory>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <vector>

#ifndef SCHEMA_PATH
#  error "SCHEMA_PATH no definido (ver CMakeLists: target_compile_definitions)"
#endif
#ifndef CONVERTER_BIN_PATH
#  error "CONVERTER_BIN_PATH no definido (ver CMakeLists: target_compile_definitions)"
#endif
#ifndef LOADER_BIN_PATH
#  error "LOADER_BIN_PATH no definido (ver CMakeLists: target_compile_definitions)"
#endif

namespace fs = std::filesystem;
using namespace argus::correlation;

namespace {

const std::string KEY_HEX =
    "abababababababababababababababababababababababababababababababab";

std::vector<uint8_t> hex_to_bytes(const std::string& hex) {
    std::vector<uint8_t> out;
    out.reserve(hex.size() / 2);
    for (size_t i = 0; i < hex.size(); i += 2) {
        unsigned int b;
        std::sscanf(hex.c_str() + i, "%02x", &b);
        out.push_back(static_cast<uint8_t>(b));
    }
    return out;
}

std::shared_ptr<spdlog::logger> null_logger(const std::string& name) {
    return std::make_shared<spdlog::logger>(
        name, std::make_shared<spdlog::sinks::null_sink_mt>());
}

// Identico a test_flujo_b_end_to_end.cpp (node_id parametrizado -> 2 flujos distintos).
protobuf::NetworkSecurityEvent make_event(const std::string& event_id,
                                           const std::string& node_id,
                                           const std::string& community_id,
                                           const std::string& classification) {
    protobuf::NetworkSecurityEvent event;
    event.set_event_id(event_id);
    event.set_originating_node_id(node_id);
    event.set_final_classification(classification);
    event.set_threat_category(classification == "MALICIOUS" ? "RANSOMWARE" : "NORMAL");
    event.set_fast_detector_score(0.91);
    event.set_ml_detector_score(0.87);
    event.set_overall_threat_score(0.89);
    event.set_authoritative_source(::protobuf::DETECTOR_SOURCE_ML_PRIORITY);
    auto* nf = event.mutable_network_features();
    nf->set_community_id(community_id);
    nf->set_source_ip("10.10.10.10");
    nf->set_destination_ip("10.10.10.20");
    nf->set_source_port(4444u);
    nf->set_destination_port(443u);
    nf->set_protocol_name("tcp");
    nf->mutable_flow_start_time()->set_seconds(1717480800);
    nf->mutable_flow_start_time()->set_nanos(123456000);
    return event;
}

int64_t count_q(kuzu::main::Connection& c, const std::string& q) {
    auto r = c.query(q);
    if (!r->isSuccess() || !r->hasNext()) return -1;
    return std::stoll(r->getNext()->toString());
}

// Escalar unico como texto (para strings: toString es exacto, sin riesgo de precision).
std::string one_scalar(kuzu::main::Connection& c, const std::string& q) {
    auto r = c.query(q);
    if (!r->isSuccess() || !r->hasNext()) return "<none>";
    return r->getNext()->toString();
}

// Corre la MISMA query en ambos grafos. Exige:
//   (1) C0  == esperado   (ancla a fichero: medir, no votar)
//   (2) A+B == esperado
//   (3) C0  == A+B        (equivalencia -- redundante con 1+2 pero da un fallo
//                          explicito "DIVERGENCIA" cuando se rompe)
void expect_equiv(kuzu::main::Connection& c0, kuzu::main::Connection& ab,
                  const std::string& q, int64_t expected, const std::string& what) {
    const int64_t n0  = count_q(c0, q);
    const int64_t nab = count_q(ab, q);
    EXPECT_EQ(n0,  expected) << "[Camino 0]  " << what;
    EXPECT_EQ(nab, expected) << "[Flujo A+B] " << what;
    EXPECT_EQ(n0,  nab)      << "DIVERGENCIA C0 vs A+B: " << what << "\n  " << q;
}

}  // namespace

// ── Equivalencia Camino-0 ≡ Flujo-A+B (ADR-058 §3.1) ─────────────────────────
TEST(FlujoABEquivalence, Camino0EqualsFlujoAB) {
    const std::string pid = std::to_string(::getpid());

    // Datos del fixture: mismos que test_flujo_b_end_to_end (2 flujos distintos,
    // 1 MALICIOUS -> Alert, 1 BENIGN -> TelemetryEvent).
    const std::string node_id_alert   = "node-e2e-alert";
    const std::string node_id_benign  = "node-e2e-benign";
    const std::string community_alert = "1:e2eAlertFlow==";
    const std::string community_benign= "1:e2eBenignFlow==";
    const std::string evt_alert       = "evt-e2e-alert";
    const std::string evt_benign      = "evt-e2e-benign";

    // ── 1. Escribir bronce REAL UNA sola vez (alimenta AMBOS caminos) ────────
    const std::string bronze_base =
        (fs::temp_directory_path() / ("flujo_equiv_bronze_" + pid)).string();
    fs::remove_all(bronze_base);

    ml_defender::CorrelationWriterConfig cfg;
    cfg.base_dir     = bronze_base;
    cfg.hmac_key_hex = KEY_HEX;

    std::string bronze_final_path;
    {
        ml_defender::CorrelationWriter writer(cfg, null_logger("equiv-writer"));
        auto ev_a = make_event(evt_alert,  node_id_alert,  community_alert,  "MALICIOUS");
        auto ev_b = make_event(evt_benign, node_id_benign, community_benign, "BENIGN");
        ASSERT_TRUE(writer.write_record(ev_a));
        ASSERT_TRUE(writer.write_record(ev_b));
        writer.flush();
        bronze_final_path = writer.get_stats().current_final_path;
    }  // destructor -> finalize_segment_locked() -> rename .tmp -> .csv
    ASSERT_FALSE(bronze_final_path.empty());
    ASSERT_TRUE(fs::exists(bronze_final_path));

    // ── 2. Camino 0: process_segment + KuzuGraphSink (enlace directo) ────────
    const std::string db_c0 =
        (fs::temp_directory_path() / ("flujo_equiv_c0_" + pid + ".kuzu")).string();
    fs::remove_all(db_c0);
    {
        const auto hmac_key = hex_to_bytes(KEY_HEX);
        KuzuGraphSink sink(db_c0, SCHEMA_PATH, null_logger("equiv-c0-sink"));
        auto res = process_segment(bronze_final_path, hmac_key, sink);
        EXPECT_EQ(res.total, 2u);
        EXPECT_EQ(res.discarded, 0u);
        const auto fr = sink.flush();
        EXPECT_TRUE(fr);
        EXPECT_EQ(fr.rows_flushed, 2u);
    }  // cierra el sink -> libera db_c0 antes de reabrir para lectura

    // ── 3. Flujo A+B: converter REAL -> loader REAL (subprocesos) ────────────
    const std::string avro_path =
        (fs::temp_directory_path() / ("flujo_equiv_" + pid + ".avro")).string();
    const std::string parquet_path =
        (fs::temp_directory_path() / ("flujo_equiv_" + pid + ".parquet")).string();
    const std::string db_ab =
        (fs::temp_directory_path() / ("flujo_equiv_ab_" + pid + ".kuzu")).string();
    fs::remove_all(db_ab);

    const std::string converter_cmd =
        "ARGUS_BRONZE_HMAC_KEY_HEX=" + KEY_HEX + " " +
        std::string(CONVERTER_BIN_PATH) + " " +
        bronze_final_path + " " + avro_path + " " + parquet_path + " > /dev/null 2>&1";
    ASSERT_EQ(std::system(converter_cmd.c_str()), 0)
        << "bronze_to_gold_converter fallo: " << converter_cmd;
    ASSERT_TRUE(fs::exists(parquet_path));

    const std::string loader_cmd =
        std::string(LOADER_BIN_PATH) + " " +
        parquet_path + " " + db_ab + " " + std::string(SCHEMA_PATH) + " > /dev/null 2>&1";
    ASSERT_EQ(std::system(loader_cmd.c_str()), 0)
        << "parquet_to_kuzu_loader fallo: " << loader_cmd;

    // ── 4. Abrir AMBOS grafos para comparar ──────────────────────────────────
    kuzu::main::SystemConfig db_cfg;
    auto database_c0 = std::make_unique<kuzu::main::Database>(db_c0, db_cfg);
    auto conn_c0     = std::make_unique<kuzu::main::Connection>(database_c0.get());
    auto database_ab = std::make_unique<kuzu::main::Database>(db_ab, db_cfg);
    auto conn_ab     = std::make_unique<kuzu::main::Connection>(database_ab.get());

    // flow_uid calculado independientemente (mismo flow_uid.hpp que usan ambos caminos).
    const uint64_t window = window_micros(1717480800, 123456000);
    const std::string fuid_alert  = compute_flow_uid(node_id_alert,  community_alert,  window);
    const std::string fuid_benign = compute_flow_uid(node_id_benign, community_benign, window);
    const std::string w = std::to_string(window);

    // ── 5a. Conteos totales: estructura + "sin extras" ───────────────────────
    expect_equiv(*conn_c0, *conn_ab,
        "MATCH (f:NetworkFlow) RETURN count(*)", 2, "total NetworkFlow");
    expect_equiv(*conn_c0, *conn_ab,
        "MATCH (a:Alert) RETURN count(*)", 1, "total Alert");
    expect_equiv(*conn_c0, *conn_ab,
        "MATCH (t:TelemetryEvent) RETURN count(*)", 1, "total TelemetryEvent");
    expect_equiv(*conn_c0, *conn_ab,
        "MATCH (:Alert)-[:ALERT_ABOUT]->(:NetworkFlow) RETURN count(*)", 1,
        "total aristas ALERT_ABOUT");
    expect_equiv(*conn_c0, *conn_ab,
        "MATCH (:TelemetryEvent)-[:TELEMETRY_ABOUT]->(:NetworkFlow) RETURN count(*)", 1,
        "total aristas TELEMETRY_ABOUT");

    // ── 5b. NetworkFlow: match exacto por flow_uid (excl. ingested_at/temporal_anomaly)
    auto nf_match = [&](const std::string& fuid, const std::string& node,
                        const std::string& comm) {
        return "MATCH (f:NetworkFlow {flow_uid:'" + fuid + "'}) "
               "WHERE f.node_id='" + node + "' "
               "AND f.community_id='" + comm + "' "
               "AND f.flow_start_window=" + w + " "
               "AND f.seq_in_window=0 "
               "RETURN count(*)";
    };
    expect_equiv(*conn_c0, *conn_ab,
        nf_match(fuid_alert, node_id_alert, community_alert), 1, "NetworkFlow MALICIOUS props");
    expect_equiv(*conn_c0, *conn_ab,
        nf_match(fuid_benign, node_id_benign, community_benign), 1, "NetworkFlow BENIGN props");

    // ── 5c. Alert / TelemetryEvent: match exacto por event_id ────────────────
    //   Scores como literal double = igualdad EXACTA (bit).
    //   authoritative_source e ingested_at EXCLUIDOS del WHERE (ver 5e / exclusiones).
    auto ev_match = [&](const std::string& label, const std::string& evt,
                        const std::string& fuid, const std::string& node,
                        const std::string& comm, const std::string& fclass,
                        const std::string& threat) {
        return "MATCH (e:" + label + " {event_id:'" + evt + "'}) "
               "WHERE e.node_id='" + node + "' "
               "AND e.flow_uid='" + fuid + "' "
               "AND e.community_id='" + comm + "' "
               "AND e.final_classification='" + fclass + "' "
               "AND e.threat_category='" + threat + "' "
               "AND e.fast_detector_score=0.91 "
               "AND e.ml_detector_score=0.87 "
               "AND e.overall_threat_score=0.89 "
               "RETURN count(*)";
    };
    expect_equiv(*conn_c0, *conn_ab,
        ev_match("Alert", evt_alert, fuid_alert, node_id_alert, community_alert,
                 "MALICIOUS", "RANSOMWARE"), 1, "Alert props (incl. scores bit-exactos)");
    expect_equiv(*conn_c0, *conn_ab,
        ev_match("TelemetryEvent", evt_benign, fuid_benign, node_id_benign, community_benign,
                 "BENIGN", "NORMAL"), 1, "TelemetryEvent props (incl. scores bit-exactos)");

    // ── 5d. Aristas: match exacto por (event_id, rel, flow_uid) ──────────────
    expect_equiv(*conn_c0, *conn_ab,
        "MATCH (:Alert {event_id:'" + evt_alert + "'})-[:ALERT_ABOUT]->"
        "(:NetworkFlow {flow_uid:'" + fuid_alert + "'}) RETURN count(*)", 1,
        "arista ALERT_ABOUT concreta");
    expect_equiv(*conn_c0, *conn_ab,
        "MATCH (:TelemetryEvent {event_id:'" + evt_benign + "'})-[:TELEMETRY_ABOUT]->"
        "(:NetworkFlow {flow_uid:'" + fuid_benign + "'}) RETURN count(*)", 1,
        "arista TELEMETRY_ABOUT concreta");

    // ── 5e. authoritative_source: no pinamos el literal (forma serializada del enum
    //   no conocida por el test) -> exigimos acuerdo C0 vs A+B (string -> toString exacto).
    EXPECT_EQ(
        one_scalar(*conn_c0, "MATCH (e:Alert {event_id:'" + evt_alert + "'}) RETURN e.authoritative_source"),
        one_scalar(*conn_ab, "MATCH (e:Alert {event_id:'" + evt_alert + "'}) RETURN e.authoritative_source"))
        << "authoritative_source (Alert) diverge C0 vs A+B";
    EXPECT_EQ(
        one_scalar(*conn_c0, "MATCH (e:TelemetryEvent {event_id:'" + evt_benign + "'}) RETURN e.authoritative_source"),
        one_scalar(*conn_ab, "MATCH (e:TelemetryEvent {event_id:'" + evt_benign + "'}) RETURN e.authoritative_source"))
        << "authoritative_source (TelemetryEvent) diverge C0 vs A+B";

    // ── 6. Limpieza — ambos Kuzu desechables, nunca persisten ────────────────
    conn_c0.reset();  database_c0.reset();
    conn_ab.reset();  database_ab.reset();
    fs::remove_all(bronze_base);
    fs::remove(avro_path);
    fs::remove(parquet_path);
    fs::remove_all(db_c0);
    fs::remove_all(db_ab);
}