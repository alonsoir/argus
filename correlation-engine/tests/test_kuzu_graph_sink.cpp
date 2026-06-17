// test_kuzu_graph_sink.cpp — DAY 180. Backend Kuzu de IGraphSink.
// Valida: carga de schema idempotente, enrutado MALICIOUS->Alert / BENIGN->TelemetryEvent,
// materializacion real (reabriendo la BD efimera) y guard de node_id/flow_uid.
// Authors: Alonso Isidoro Roman + Claude (Anthropic).
#include <gtest/gtest.h>

#include "correlation_engine/kuzu_graph_sink.hpp"
#include "correlation_engine/correlation_record.hpp"
#include "correlation_engine/flow_uid.hpp"
#include "correlation_engine/cypher_builder.hpp"
#include <kuzu.hpp>

#include <spdlog/spdlog.h>
#include <spdlog/sinks/null_sink.h>

#include <cstdio>
#include <utility>
#include <memory>
#include <string>

using namespace argus::correlation;

namespace {

#ifndef SCHEMA_PATH
#  error "SCHEMA_PATH no definido (ver CMakeLists: target_compile_definitions)"
#endif

constexpr const char* kDbPath = "/tmp/test_kuzu_graph_sink.kuzu";

std::shared_ptr<spdlog::logger> null_logger() {
    return std::make_shared<spdlog::logger>(
        "test-kuzu", std::make_shared<spdlog::sinks::null_sink_mt>());
}

CorrelationRecord make_record(const std::string& event_id,
                              const std::string& community_id,
                              const std::string& classification,
                              const std::string& category) {
    CorrelationRecord r;
    r.schema_version  = "1";
    r.source_sensor   = "argus";
    r.event_id        = event_id;
    r.node_id         = "node-test";
    r.community_id    = community_id;
    r.flow_start_sec  = 1700000000;
    r.flow_start_nano = 123456;
    r.final_classification = classification;
    r.threat_category      = category;
    r.fast_detector_score  = 0.91;
    r.ml_detector_score    = 0.97;
    r.overall_threat_score = 0.95;
    r.authoritative_source = "DETECTOR_SOURCE_CONSENSUS";
    return r;
}

std::string fuid_of(const CorrelationRecord& r) {
    return compute_flow_uid(r.node_id, r.community_id,
                            window_micros(r.flow_start_sec, r.flow_start_nano));
}

// count(*) de una query, via toString() (evita depender del getter tipado de Kuzu).
int64_t count_query(kuzu::main::Connection& c, const std::string& q) {
    auto r = c.query(q);
    if (!r->isSuccess() || !r->hasNext()) return -1;
    return std::stoll(r->getNext()->toString());
}

}  // namespace

// ── Enrutado + materializacion real ─────────────────────────────────────────
TEST(KuzuGraphSink, WritesRouteAndMaterialize) {
    std::remove(kDbPath);
    const auto mal = make_record("ev-mal", "1:commMal", "MALICIOUS", "RANSOMWARE");
    const auto ben = make_record("ev-ben", "1:commBen", "BENIGN", "NORMAL");
    {
        KuzuGraphSink sink(kDbPath, SCHEMA_PATH, null_logger());
        EXPECT_TRUE(sink.write(mal, fuid_of(mal)));
        EXPECT_TRUE(sink.write(ben, fuid_of(ben)));
        // DAY 184: write() ACEPTA (acumula); aun NO durable -> writes()==0, 2 pendientes.
        EXPECT_EQ(sink.writes(),  0u);
        EXPECT_EQ(sink.pending(), 2u);
        // flush() materializa el batch en 1 tx y reporta durabilidad.
        const auto fr = sink.flush();
        EXPECT_TRUE(fr);                       // ok
        EXPECT_EQ(fr.rows_flushed, 2u);        // 2 committeadas en este flush
        EXPECT_EQ(fr.rows_pending, 0u);        // buffer vaciado
        EXPECT_EQ(sink.writes(),  2u);         // total durable
        EXPECT_EQ(sink.pending(), 0u);
    }  // dtor: buffer vacio -> NO grita (guard de durabilidad satisfecho)
    // Reabrir y verificar materializacion + enrutado.
    kuzu::main::SystemConfig cfg;
    auto db   = std::make_unique<kuzu::main::Database>(kDbPath, cfg);
    auto conn = std::make_unique<kuzu::main::Connection>(db.get());
    EXPECT_EQ(count_query(*conn, "MATCH (n:NetworkFlow) RETURN count(*)"), 2);
    EXPECT_EQ(count_query(*conn, "MATCH (a:Alert) RETURN count(*)"), 1);
    EXPECT_EQ(count_query(*conn, "MATCH (t:TelemetryEvent) RETURN count(*)"), 1);
    EXPECT_EQ(count_query(*conn,
        "MATCH (:Alert)-[:ALERT_ABOUT]->(:NetworkFlow) RETURN count(*)"), 1);
    EXPECT_EQ(count_query(*conn,
        "MATCH (:TelemetryEvent)-[:TELEMETRY_ABOUT]->(:NetworkFlow) RETURN count(*)"), 1);
    std::remove(kDbPath);
}

// ── Idempotencia: re-escribir el mismo registro no duplica (MERGE) ──────────
// DAY 184: flush ENTRE los dos writes -> el 2º MERGE ve el nodo ya COMMITTEADO
// (idempotencia entre transacciones, que es el caso real de re-llegada por dedup).
TEST(KuzuGraphSink, MergeIsIdempotent) {
    std::remove(kDbPath);
    const auto mal = make_record("ev-dup", "1:commDup", "MALICIOUS", "ATTACK");
    {
        KuzuGraphSink sink(kDbPath, SCHEMA_PATH, null_logger());
        EXPECT_TRUE(sink.write(mal, fuid_of(mal)));
        EXPECT_TRUE(sink.flush());                   // 1ª tx: crea el nodo
        EXPECT_TRUE(sink.write(mal, fuid_of(mal)));  // re-llegada por dedup (otra tx)
        EXPECT_TRUE(sink.flush());                   // 2ª tx: MERGE no duplica
        EXPECT_EQ(sink.writes(), 2u);                // 2 filas committeadas...
    }
    kuzu::main::SystemConfig cfg;
    auto db   = std::make_unique<kuzu::main::Database>(kDbPath, cfg);
    auto conn = std::make_unique<kuzu::main::Connection>(db.get());
    EXPECT_EQ(count_query(*conn, "MATCH (n:NetworkFlow) RETURN count(*)"), 1);  // ...1 solo nodo
    EXPECT_EQ(count_query(*conn, "MATCH (a:Alert) RETURN count(*)"), 1);
    std::remove(kDbPath);
}

// ── Guard de invariante: nodo sin node_id o sin flow_uid se RECHAZA ─────────
TEST(KuzuGraphSink, RejectsEmptyNodeIdOrFlowUid) {
    std::remove(kDbPath);
    auto bad = make_record("ev-bad", "1:comm", "MALICIOUS", "ATTACK");
    bad.node_id.clear();  // viola invariante de engine

    KuzuGraphSink sink(kDbPath, SCHEMA_PATH, null_logger());
    EXPECT_FALSE(sink.write(bad, "some-flow-uid"));                                // node_id vacio
    EXPECT_FALSE(sink.write(make_record("ev-ok", "1:c", "MALICIOUS", "ATTACK"), ""));  // flow_uid vacio
    EXPECT_EQ(sink.writes(), 0u);

    std::remove(kDbPath);
}

// ── Durabilidad: flush() vacia el buffer; sin flush, el dtor avisa y NADA se materializa ──
TEST(KuzuGraphSink, UnflushedBufferIsNotDurable) {
    std::remove(kDbPath);
    const auto r = make_record("ev-noflush", "1:commNF", "MALICIOUS", "ATTACK");
    {
        KuzuGraphSink sink(kDbPath, SCHEMA_PATH, null_logger());
        EXPECT_TRUE(sink.write(r, fuid_of(r)));
        EXPECT_EQ(sink.pending(), 1u);
        EXPECT_EQ(sink.writes(),  0u);
        // SIN flush a proposito: el dtor logea el error de durabilidad (no se puede surface).
    }  // dtor con buffer no vacio -> guard salta (verificable por log; aqui basta no-crash)
    // La fila NO se materializo: reabrir muestra grafo vacio.
    kuzu::main::SystemConfig cfg;
    auto db   = std::make_unique<kuzu::main::Database>(kDbPath, cfg);
    auto conn = std::make_unique<kuzu::main::Connection>(db.get());
    EXPECT_EQ(count_query(*conn, "MATCH (n:NetworkFlow) RETURN count(*)"), 0);
    std::remove(kDbPath);
}

// Replica del binder de produccion (exec_row, anon-ns en kuzu_graph_sink.cpp).
// El test es spec INDEPENDIENTE: si el binder de produccion deriva, este sigue clavando
// los 14 params a mano. std::string materializado (Value no tiene ctor desde string_view).
bool exec_alert_row_raw(kuzu::main::Connection& conn,
                        kuzu::main::PreparedStatement* prep,
                        const CypherBindings& b) {
    auto r = conn.execute(prep,
        std::pair{std::string("flow_uid"),             std::string(b.flow_uid)},
        std::pair{std::string("node_id"),              std::string(b.node_id)},
        std::pair{std::string("community_id"),         std::string(b.community_id)},
        std::pair{std::string("flow_start_window"),    b.flow_start_window},
        std::pair{std::string("seq_in_window"),        b.seq_in_window},
        std::pair{std::string("ingested_at"),          b.ingested_at},
        std::pair{std::string("temporal_anomaly"),     b.temporal_anomaly},
        std::pair{std::string("event_id"),             std::string(b.event_id)},
        std::pair{std::string("final_classification"), std::string(b.final_classification)},
        std::pair{std::string("threat_category"),      std::string(b.threat_category)},
        std::pair{std::string("fast_detector_score"),  b.fast_detector_score},
        std::pair{std::string("ml_detector_score"),    b.ml_detector_score},
        std::pair{std::string("overall_threat_score"), b.overall_threat_score},
        std::pair{std::string("authoritative_source"), std::string(b.authoritative_source)});
    return r->isSuccess();  // QueryResult muere aqui, antes de cerrar nada
}

// ── VERIFY-3 (DAY 184): BEGIN/execute×N/{COMMIT|ROLLBACK} es UNA transaccion real ──
// La API de 0.11.3 NO expone metodo tipado de tx: control manual por string. Esto prueba
// que ese control AGRUPA los execute(prepared) = amortizacion de 1 checkpoint por batch,
// premisa sobre la que descansa la medicion de la tortura E2E (punto 3).

TEST(KuzuGraphSink, ExplicitCommitPersistsBatch) {
    std::remove(kDbPath);
    { KuzuGraphSink sink(kDbPath, SCHEMA_PATH, null_logger()); }  // crea BD + persiste schema
    kuzu::main::SystemConfig cfg;
    auto db   = std::make_unique<kuzu::main::Database>(kDbPath, cfg);
    auto conn = std::make_unique<kuzu::main::Connection>(db.get());
    auto prep = conn->prepare(kAlertCypherTemplate);
    ASSERT_TRUE(prep && prep->isSuccess());

    const auto r1 = make_record("ev-c1", "1:commC1", "MALICIOUS", "ATTACK");
    const auto r2 = make_record("ev-c2", "1:commC2", "MALICIOUS", "ATTACK");
    const auto b1 = make_bindings(r1, fuid_of(r1), 1'000);
    const auto b2 = make_bindings(r2, fuid_of(r2), 2'000);

    ASSERT_TRUE(conn->query("BEGIN TRANSACTION")->isSuccess());
    EXPECT_TRUE(exec_alert_row_raw(*conn, prep.get(), b1));
    EXPECT_TRUE(exec_alert_row_raw(*conn, prep.get(), b2));
    ASSERT_TRUE(conn->query("COMMIT")->isSuccess());

    EXPECT_EQ(count_query(*conn, "MATCH (n:NetworkFlow) RETURN count(*)"), 2);  // durable
    std::remove(kDbPath);
}

TEST(KuzuGraphSink, ExplicitRollbackRevertsBatch) {
    std::remove(kDbPath);
    { KuzuGraphSink sink(kDbPath, SCHEMA_PATH, null_logger()); }  // mismo schema persistido
    kuzu::main::SystemConfig cfg;
    auto db   = std::make_unique<kuzu::main::Database>(kDbPath, cfg);
    auto conn = std::make_unique<kuzu::main::Connection>(db.get());
    auto prep = conn->prepare(kAlertCypherTemplate);
    ASSERT_TRUE(prep && prep->isSuccess());

    const auto r1 = make_record("ev-r1", "1:commR1", "MALICIOUS", "ATTACK");
    const auto r2 = make_record("ev-r2", "1:commR2", "MALICIOUS", "ATTACK");
    const auto b1 = make_bindings(r1, fuid_of(r1), 1'000);
    const auto b2 = make_bindings(r2, fuid_of(r2), 2'000);

    ASSERT_TRUE(conn->query("BEGIN TRANSACTION")->isSuccess());
    EXPECT_TRUE(exec_alert_row_raw(*conn, prep.get(), b1));
    EXPECT_TRUE(exec_alert_row_raw(*conn, prep.get(), b2));
    ASSERT_TRUE(conn->query("ROLLBACK")->isSuccess());

    // DECISIVO: mismas 2 filas que el test de arriba; SOLO cambia ROLLBACK por COMMIT.
    // 0 => estaban dentro de la tx => agrupadas. !=0 => auto-commit por fila => batching roto.
    EXPECT_EQ(count_query(*conn, "MATCH (n:NetworkFlow) RETURN count(*)"), 0);
    std::remove(kDbPath);
}

