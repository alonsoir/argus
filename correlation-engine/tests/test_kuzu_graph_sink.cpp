// test_kuzu_graph_sink.cpp — DAY 180. Backend Kuzu de IGraphSink.
// Valida: carga de schema idempotente, enrutado MALICIOUS->Alert / BENIGN->TelemetryEvent,
// materializacion real (reabriendo la BD efimera) y guard de node_id/flow_uid.
// Authors: Alonso Isidoro Roman + Claude (Anthropic).
#include <gtest/gtest.h>

#include "correlation_engine/kuzu_graph_sink.hpp"
#include "correlation_engine/correlation_record.hpp"
#include "correlation_engine/flow_uid.hpp"

#include <kuzu.hpp>

#include <spdlog/spdlog.h>
#include <spdlog/sinks/null_sink.h>

#include <cstdio>
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
        EXPECT_EQ(sink.writes(), 2u);
    }  // sink fuera de scope -> libera el lock de la BD single-file

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
TEST(KuzuGraphSink, MergeIsIdempotent) {
    std::remove(kDbPath);
    const auto mal = make_record("ev-dup", "1:commDup", "MALICIOUS", "ATTACK");
    {
        KuzuGraphSink sink(kDbPath, SCHEMA_PATH, null_logger());
        EXPECT_TRUE(sink.write(mal, fuid_of(mal)));
        EXPECT_TRUE(sink.write(mal, fuid_of(mal)));  // re-llegada por dedup
        EXPECT_EQ(sink.writes(), 2u);                // 2 writes...
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