// test_cypher_prepared.cpp — DAY 183. Verifica el path PARAMETRIZADO (ADR-057):
//   prepare(plantilla) + execute(pares nombrados), contra el schema REAL, en BD efimera.
// Authors: Alonso Isidoro Roman + Claude (Anthropic).
//
// Zanja de una sola fila (medir, no votar):
//   VERIFY-1  UINT64/UINT32 integros (sentinela > 2^63 -> caza colapso a INT64).
//   VERIFY-2  RESUELTO: el unico overload en 0.11.3 es el variadico
//             execute(PreparedStatement*, std::pair<std::string,Args>...). Map NO existe.
//   VERIFY-3  $flow_uid reusado en MERGE(f) y en e.flow_uid -> mismo valor.
//   H-1       node_id/community_id con  '  y  \  vuelven byte-identicos -> inyeccion
//             Cypher cerrada ESTRUCTURALMENTE por el param tipado (no por esc()).
//
// CICLO DE VIDA KUZU (lo que costo un SIGSEGV en DAY 183): los QueryResult y los
// PreparedStatement sostienen referencias al BufferManager de la Database. DEBEN
// destruirse ANTES que Connection y Database. -> todo el trabajo va en un bloque
// interno; el orden natural inverso de destruccion (QueryResults -> conn -> db) es
// correcto. NUNCA db.reset() mientras viva un QueryResult. cleanup_db tras cerrar el bloque.
//
// Lectura via Value::toString() (primitivo probado en test_kuzu_graph_sink); el getter
// templado value->getValue<T>() no parsea en este build de Kuzu.
//
// AISLADO: NO incluye kuzu_graph_sink.hpp ni toca el sink de produccion. La forma de
// 'execute con 14 pares' que se valida aqui es la que migrara a kuzu_graph_sink.cpp.
#include <gtest/gtest.h>

#include "correlation_engine/cypher_builder.hpp"
#include "correlation_engine/correlation_record.hpp"
#include "correlation_engine/flow_uid.hpp"

#include <kuzu.hpp>

#include <cctype>
#include <cstdio>
#include <fstream>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

using namespace argus::correlation;
using kuzu::main::Connection;
using kuzu::main::Database;
using kuzu::main::SystemConfig;

namespace {

#ifndef SCHEMA_PATH
#  error "SCHEMA_PATH no definido (ver CMakeLists: target_compile_definitions)"
#endif

constexpr const char* kDbPath = "/tmp/test_cypher_prepared.kuzu";

void cleanup_db(const std::string& p) {
    for (const char* sfx : {"", ".wal", ".wal.shadow", ".shadow", ".lock", ".tmp"})
        std::remove((p + sfx).c_str());
}

// Splitter de schema.cypher (replica del de kuzu_graph_sink.cpp; su anon-ns no se exporta).
std::vector<std::string> split_statements(const std::string& path) {
    std::ifstream in(path);
    if (!in) throw std::runtime_error("no puedo abrir schema: " + path);
    std::ostringstream clean;
    std::string line;
    while (std::getline(in, line)) {
        const auto pos = line.find("//");
        clean << (pos == std::string::npos ? line : line.substr(0, pos)) << '\n';
    }
    std::vector<std::string> out;
    std::istringstream parts(clean.str());
    std::string seg;
    while (std::getline(parts, seg, ';')) {
        const auto b = seg.find_first_not_of(" \t\r\n");
        if (b == std::string::npos) continue;
        const auto e = seg.find_last_not_of(" \t\r\n");
        out.push_back(seg.substr(b, e - b + 1));
    }
    return out;
}

std::string lower(std::string s) {
    for (char& c : s) c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
    return s;
}

}  // namespace

TEST(CypherPrepared, RoundTripUint64AndAdversarialStrings) {
    cleanup_db(kDbPath);

    // ── Bloque interno: TODO QueryResult/PreparedStatement muere ANTES que conn/db ──
    {
        SystemConfig cfg;
        auto db   = std::make_unique<Database>(kDbPath, cfg);
        auto conn = std::make_unique<Connection>(db.get());

        // DDL real (schema.cypher) -> las 5 tablas existen como las espera la plantilla.
        for (const auto& stmt : split_statements(SCHEMA_PATH)) {
            auto r = conn->query(stmt);
            ASSERT_TRUE(r->isSuccess()) << "DDL: " << r->getErrorMessage() << " | " << stmt;
        }

        // Record adversarial: node_id/community_id/event_id con  '  y  \  (vector H-1).
        CorrelationRecord r;
        r.schema_version = "1";
        r.source_sensor  = "argus";
        r.event_id       = "ev'1\\x";          // comilla + backslash en la PK del evento
        r.node_id        = "a'b\\c";           // <-- H-1
        r.community_id   = "1:cm\\'x";         // <-- H-1
        r.flow_start_sec = 1700000000;
        r.flow_start_nano = 123456;
        r.final_classification = "MALICIOUS";  // -> plantilla Alert
        r.threat_category      = "RANSOMWARE";
        r.fast_detector_score  = 0.91;
        r.ml_detector_score    = 0.97;
        r.overall_threat_score = 0.95;
        r.authoritative_source = "DETECTOR_SOURCE_CONSENSUS";

        const std::string fuid = compute_flow_uid(
            r.node_id, r.community_id, window_micros(r.flow_start_sec, r.flow_start_nano));

        // ingested_at: sentinela > 2^63. Si Kuzu colapsa a INT64, o execute falla, o el
        // round-trip devuelve un decimal distinto. Test DURO de VERIFY-1.
        const uint64_t kIngestedSentinel = 0xFEDCBA9876543210ULL;  // ~1.836e19 > 2^63
        const CypherBindings b = make_bindings(r, fuid, kIngestedSentinel);
        ASSERT_TRUE(b.is_alert);

        // VERIFY-2: prepare + execute con el variadico de pares (unico overload en 0.11.3).
        // Las claves DEBEN ser std::string (la firma es pair<std::string, Args>).
        auto prep = conn->prepare(std::string(cypher_template(b.is_alert)));
        ASSERT_TRUE(prep->isSuccess()) << "prepare: " << prep->getErrorMessage();
        auto res = conn->execute(prep.get(),
            std::make_pair(std::string("flow_uid"),             std::string(b.flow_uid)),
            std::make_pair(std::string("node_id"),              std::string(b.node_id)),
            std::make_pair(std::string("community_id"),         std::string(b.community_id)),
            std::make_pair(std::string("event_id"),             std::string(b.event_id)),
            std::make_pair(std::string("final_classification"), std::string(b.final_classification)),
            std::make_pair(std::string("threat_category"),      std::string(b.threat_category)),
            std::make_pair(std::string("authoritative_source"), std::string(b.authoritative_source)),
            std::make_pair(std::string("flow_start_window"),    b.flow_start_window),  // uint64_t -> UINT64
            std::make_pair(std::string("seq_in_window"),        b.seq_in_window),      // uint32_t -> UINT32
            std::make_pair(std::string("ingested_at"),          b.ingested_at),        // uint64_t -> UINT64
            std::make_pair(std::string("temporal_anomaly"),     b.temporal_anomaly),   // bool -> BOOL
            std::make_pair(std::string("fast_detector_score"),  b.fast_detector_score),
            std::make_pair(std::string("ml_detector_score"),    b.ml_detector_score),
            std::make_pair(std::string("overall_threat_score"), b.overall_threat_score));
        ASSERT_TRUE(res->isSuccess()) << "execute: " << res->getErrorMessage();

        // Read-back PARAMETRIZADO del NetworkFlow (no interpolo el fuid adversarial).
        auto rprep = conn->prepare(
            "MATCH (f:NetworkFlow {flow_uid:$u}) "
            "RETURN f.node_id, f.community_id, f.flow_start_window, f.seq_in_window, "
            "f.ingested_at, f.temporal_anomaly");
        ASSERT_TRUE(rprep->isSuccess()) << rprep->getErrorMessage();
        auto rr = conn->execute(rprep.get(), std::make_pair(std::string("u"), fuid));
        ASSERT_TRUE(rr->isSuccess()) << rr->getErrorMessage();
        ASSERT_TRUE(rr->hasNext());
        auto t = rr->getNext();

        EXPECT_EQ(t->getValue(0)->toString(), r.node_id);                       // H-1: '  \  intactos
        EXPECT_EQ(t->getValue(1)->toString(), r.community_id);                  // H-1
        EXPECT_EQ(t->getValue(2)->toString(), std::to_string(b.flow_start_window));  // UINT64
        EXPECT_EQ(t->getValue(3)->toString(), std::to_string(b.seq_in_window));      // UINT32
        EXPECT_EQ(t->getValue(4)->toString(), std::to_string(kIngestedSentinel));    // UINT64 > 2^63 (VERIFY-1)
        EXPECT_EQ(lower(t->getValue(5)->toString()), b.temporal_anomaly ? "true" : "false");  // BOOL

        // VERIFY-3: $flow_uid se uso en MERGE(f) y en e.flow_uid -> mismo valor en el evento.
        auto eprep = conn->prepare(
            "MATCH (e:Alert {event_id:$e}) RETURN e.flow_uid, e.community_id, e.final_classification");
        ASSERT_TRUE(eprep->isSuccess()) << eprep->getErrorMessage();
        auto er = conn->execute(eprep.get(), std::make_pair(std::string("e"), r.event_id));
        ASSERT_TRUE(er->isSuccess()) << er->getErrorMessage();
        ASSERT_TRUE(er->hasNext());
        auto et = er->getNext();
        EXPECT_EQ(et->getValue(0)->toString(), fuid);                  // $flow_uid reusado
        EXPECT_EQ(et->getValue(1)->toString(), r.community_id);
        EXPECT_EQ(et->getValue(2)->toString(), r.final_classification);

        // Arista (evento)-[:ALERT_ABOUT]->(flujo) materializada en el mismo statement.
        auto edge = conn->query(
            "MATCH (:Alert)-[:ALERT_ABOUT]->(:NetworkFlow) RETURN count(*)");
        ASSERT_TRUE(edge->isSuccess()) << edge->getErrorMessage();
        ASSERT_TRUE(edge->hasNext());
        EXPECT_EQ(std::stoll(edge->getNext()->toString()), 1);
    }  // <-- aqui mueren, en orden: QueryResults -> PreparedStatements -> conn -> db

    cleanup_db(kDbPath);  // db ya cerrada -> lock liberado, seguro borrar
}