// test_bronze_to_kuzu_circuit.cpp — DAY 204, emecas+++ (circuito completo FS).
// ADR-058 §1: inyectar evento sintetico -> verificar HMAC en bronce -> verificar
// MATCH en Kuzu. Un solo proceso, filesystem puro (sin ZMQ -- ese tramo aun no
// existe, Eslabon 1+). Reutiliza produccion real en cada eslabon:
//   CorrelationWriter (ml-detector, real)          -> escribe bronce segmentado
//   ac::process_segment (correlation-engine, real) -> parse_and_verify + sink
//   KuzuGraphSink (correlation-engine, real)       -> materializa en Kuzu
// Cero reimplementacion: si produccion cambia, este test se entera.
// Authors: Alonso Isidoro Roman + Claude (Anthropic)
#include <gtest/gtest.h>

#include "correlation_writer.hpp"
#include "correlation_engine/segment_processor.hpp"
#include "correlation_engine/kuzu_graph_sink.hpp"

#include <network_security.pb.h>
#include <google/protobuf/timestamp.pb.h>

#include <kuzu.hpp>

#include <spdlog/spdlog.h>
#include <spdlog/sinks/null_sink.h>

#include <filesystem>
#include <fstream>
#include <string>
#include <vector>
#include <cstdint>
#include <cstdio>
#include <memory>

namespace fs = std::filesystem;
using namespace argus::correlation;

namespace {

#ifndef SCHEMA_PATH
#  error "SCHEMA_PATH no definido (ver CMakeLists: target_compile_definitions)"
#endif

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

protobuf::NetworkSecurityEvent make_event(const std::string& event_id,
const std::string& community_id,
const std::string& classification) {
protobuf::NetworkSecurityEvent event;
event.set_event_id(event_id);
event.set_originating_node_id("node-emecas-plus-plus");
event.set_final_classification(classification);
event.set_threat_category("RANSOMWARE");
event.set_fast_detector_score(0.91);
event.set_ml_detector_score(0.97);
event.set_overall_threat_score(0.95);
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

int64_t count_query(kuzu::main::Connection& c, const std::string& q) {
auto r = c.query(q);
if (!r->isSuccess() || !r->hasNext()) return -1;
return std::stoll(r->getNext()->toString());
}

}  // namespace

// ── Circuito completo, camino feliz: bronce -> Kuzu MATCH ────────────────────
TEST(EmecasPlusPlus, BronzeToKuzuCircuitHappyPath) {
const auto hmac_key = hex_to_bytes(KEY_HEX);

    // 1. Escribe con el CorrelationWriter REAL (ml-detector).
    const std::string base = (fs::temp_directory_path() /
        ("emecas_ppp_" + std::to_string(::getpid()))).string();
    fs::remove_all(base);

    ml_defender::CorrelationWriterConfig cfg;
    cfg.base_dir     = base;
    cfg.hmac_key_hex = KEY_HEX;

    std::string final_path;
    {
        ml_defender::CorrelationWriter writer(cfg, null_logger("emecas-writer"));
        auto event = make_event("evt-emecas-001", "1:emecasCircuit==", "MALICIOUS");
        ASSERT_TRUE(writer.write_record(event));
        writer.flush();
        final_path = writer.get_stats().current_final_path;
    }  // destructor: finalize_segment_locked() -> rename atomico .tmp -> .csv
    ASSERT_FALSE(final_path.empty());
    ASSERT_TRUE(fs::exists(final_path));

    // 2. Lee con process_segment REAL (correlation-engine, produccion).
    const std::string db_path = "/tmp/test_emecas_ppp_happy.kuzu";
    std::remove(db_path.c_str());
    {
        KuzuGraphSink sink(db_path, SCHEMA_PATH, null_logger("emecas-sink"));
        auto result = process_segment(final_path, hmac_key, sink);
        EXPECT_EQ(result.total, 1u);
        EXPECT_EQ(result.discarded, 0u);
        const auto fr = sink.flush();
        EXPECT_TRUE(fr);
        EXPECT_EQ(fr.rows_flushed, 1u);
    }

    // 3. Verifica MATCH en Kuzu (ADR-058 §1). El HMAC en bronce ya lo
    //    garantiza parse_and_verify dentro de process_segment (test siguiente).
    kuzu::main::SystemConfig db_cfg;
    auto db   = std::make_unique<kuzu::main::Database>(db_path, db_cfg);
    auto conn = std::make_unique<kuzu::main::Connection>(db.get());
    EXPECT_EQ(count_query(*conn, "MATCH (f:NetworkFlow) RETURN count(*)"), 1);
    EXPECT_EQ(count_query(*conn, "MATCH (a:Alert) RETURN count(*)"), 1);
    EXPECT_EQ(count_query(*conn,
        "MATCH (:Alert)-[:ALERT_ABOUT]->(:NetworkFlow) RETURN count(*)"), 1);

    fs::remove_all(base);
    std::remove(db_path.c_str());
}

// ── Circuito completo, fila manipulada: descartada ANTES de Kuzu ─────────────
// Cierra ADR-058 §1 desde el otro lado: si el HMAC no verifica, el evento NUNCA
// llega al grafo -- ni un nodo NetworkFlow huerfano, ni una fila fantasma.
TEST(EmecasPlusPlus, TamperedRowNeverReachesKuzu) {
const auto hmac_key = hex_to_bytes(KEY_HEX);

    const std::string base = (fs::temp_directory_path() /
        ("emecas_ppp_tamper_" + std::to_string(::getpid()))).string();
    fs::remove_all(base);

    ml_defender::CorrelationWriterConfig cfg;
    cfg.base_dir     = base;
    cfg.hmac_key_hex = KEY_HEX;

    std::string final_path;
    {
        ml_defender::CorrelationWriter writer(cfg, null_logger("emecas-writer-tamper"));
        auto event = make_event("evt-emecas-tamper", "1:emecasTamper==", "MALICIOUS");
        ASSERT_TRUE(writer.write_record(event));
        writer.flush();
        final_path = writer.get_stats().current_final_path;
    }
    ASSERT_TRUE(fs::exists(final_path));

    // Manipula el segmento YA CERRADO (simula bit-flip en transito/disco):
    // altera final_classification sin recalcular el HMAC -> debe rechazarse.
    {
        std::ifstream in(final_path);
        std::string line;
        std::getline(in, line);
        in.close();
        auto pos = line.find("MALICIOUS");
        ASSERT_NE(pos, std::string::npos);
        line.replace(pos, 9, "BENIGN!!!");  // misma longitud, HMAC ya no cuadra
        std::ofstream out(final_path, std::ios::trunc);
        out << line << "\n";
    }

    const std::string db_path = "/tmp/test_emecas_ppp_tamper.kuzu";
    std::remove(db_path.c_str());
    {
        KuzuGraphSink sink(db_path, SCHEMA_PATH, null_logger("emecas-sink-tamper"));
        auto result = process_segment(final_path, hmac_key, sink);
        EXPECT_EQ(result.total, 0u);
        EXPECT_EQ(result.discarded, 1u);
        const auto fr = sink.flush();
        EXPECT_TRUE(fr);
        EXPECT_EQ(fr.rows_flushed, 0u);
    }

    kuzu::main::SystemConfig db_cfg;
    auto db   = std::make_unique<kuzu::main::Database>(db_path, db_cfg);
    auto conn = std::make_unique<kuzu::main::Connection>(db.get());
    EXPECT_EQ(count_query(*conn, "MATCH (f:NetworkFlow) RETURN count(*)"), 0);

    fs::remove_all(base);
    std::remove(db_path.c_str());
}
