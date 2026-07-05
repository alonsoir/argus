// test_flujo_b_end_to_end.cpp — DAY 208
// Flujo B, verificación de extremo a extremo para EMECAS+++.
//
// A diferencia de test_bronze_to_kuzu_circuit.cpp (que enlaza directamente
// contra process_segment/KuzuGraphSink), este test invoca los BINARIOS REALES
// ya compilados (bronze_to_gold_converter, parquet_to_kuzu_loader) como
// subprocesos -- es la forma en que un operador los usaría de verdad, y evita
// tener que extraer las funciones internas del converter a una librería
// (bloqueo que dejamos pendiente en test_parquet_to_kuzu_loader.cpp DAY 208 --
// este fichero lo resuelve por la vía de la caja negra, no por refactorización).
//
// Escribe con CorrelationWriter REAL (ml-detector) -> ejecuta converter REAL
// (Flujo A) -> ejecuta loader REAL (Flujo B) -> verifica MATCH en Kuzu REAL.
// Cero reimplementación en ningún tramo.
//
// Kuzu de test AISLADO y DESECHABLE (path temporal, borrado al final) --
// nunca compartido con nada de producción (Alonso, DAY 207).

#include <gtest/gtest.h>

#include "correlation_writer.hpp"
#include "correlation_engine/flow_uid.hpp"

#include <kuzu.hpp>

#include <network_security.pb.h>
#include <google/protobuf/timestamp.pb.h>

#include <spdlog/spdlog.h>
#include <spdlog/sinks/null_sink.h>

#include <filesystem>
#include <fstream>
#include <string>
#include <cstdio>
#include <cstdlib>
#include <memory>

#ifndef CONVERTER_BIN_PATH
#  error "CONVERTER_BIN_PATH no definido (ver CMakeLists: target_compile_definitions)"
#endif
#ifndef LOADER_BIN_PATH
#  error "LOADER_BIN_PATH no definido (ver CMakeLists: target_compile_definitions)"
#endif
#ifndef SCHEMA_PATH
#  error "SCHEMA_PATH no definido (ver CMakeLists: target_compile_definitions)"
#endif

namespace fs = std::filesystem;
using namespace argus::correlation;

namespace {

const std::string KEY_HEX =
    "abababababababababababababababababababababababababababababababab";

std::shared_ptr<spdlog::logger> null_logger(const std::string& name) {
    return std::make_shared<spdlog::logger>(
        name, std::make_shared<spdlog::sinks::null_sink_mt>());
}

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

int64_t count_query(kuzu::main::Connection& c, const std::string& q) {
    auto r = c.query(q);
    if (!r->isSuccess() || !r->hasNext()) return -1;
    return std::stoll(r->getNext()->toString());
}

}  // namespace

TEST(FlujoBEndToEnd, ConverterAndLoaderRealBinaries) {
    const std::string pid_suffix = std::to_string(::getpid());

    // 1. Escribir bronce REAL con CorrelationWriter REAL — 2 filas conocidas,
    //    una MALICIOUS y otra BENIGN, en flujos (community_id) distintos.
    const std::string bronze_base =
        (fs::temp_directory_path() / ("flujo_b_e2e_bronze_" + pid_suffix)).string();
    fs::remove_all(bronze_base);

    ml_defender::CorrelationWriterConfig cfg;
    cfg.base_dir     = bronze_base;
    cfg.hmac_key_hex = KEY_HEX;

    const std::string node_id_alert = "node-e2e-alert";
    const std::string node_id_benign = "node-e2e-benign";
    const std::string community_alert = "1:e2eAlertFlow==";
    const std::string community_benign = "1:e2eBenignFlow==";

    std::string bronze_final_path;
    {
        ml_defender::CorrelationWriter writer(cfg, null_logger("e2e-writer"));
        auto ev_alert  = make_event("evt-e2e-alert", node_id_alert, community_alert, "MALICIOUS");
        auto ev_benign = make_event("evt-e2e-benign", node_id_benign, community_benign, "BENIGN");
        ASSERT_TRUE(writer.write_record(ev_alert));
        ASSERT_TRUE(writer.write_record(ev_benign));
        writer.flush();
        bronze_final_path = writer.get_stats().current_final_path;
    }  // destructor -> finalize_segment_locked() -> rename .tmp -> .csv
    ASSERT_FALSE(bronze_final_path.empty());
    ASSERT_TRUE(fs::exists(bronze_final_path));

    // 2. Ejecutar bronze_to_gold_converter REAL (subproceso, binario ya compilado).
    const std::string avro_path =
        (fs::temp_directory_path() / ("flujo_b_e2e_" + pid_suffix + ".avro")).string();
    const std::string parquet_path =
        (fs::temp_directory_path() / ("flujo_b_e2e_" + pid_suffix + ".parquet")).string();

    std::string converter_cmd = "ARGUS_BRONZE_HMAC_KEY_HEX=" + KEY_HEX + " " +
        std::string(CONVERTER_BIN_PATH) + " " +
        bronze_final_path + " " + avro_path + " " + parquet_path +
        " > /dev/null 2>&1";
    int converter_rc = std::system(converter_cmd.c_str());
    ASSERT_EQ(converter_rc, 0) << "bronze_to_gold_converter falló, cmd: " << converter_cmd;
    ASSERT_TRUE(fs::exists(parquet_path));

    // 3. Ejecutar parquet_to_kuzu_loader REAL (subproceso, binario ya compilado).
    const std::string kuzu_db_path =
        (fs::temp_directory_path() / ("flujo_b_e2e_" + pid_suffix + ".kuzu")).string();
    fs::remove_all(kuzu_db_path);  // aislado, desechable — nunca compartido (DAY 207)

    std::string loader_cmd = std::string(LOADER_BIN_PATH) + " " +
        parquet_path + " " + kuzu_db_path + " " + std::string(SCHEMA_PATH) +
        " > /dev/null 2>&1";
    int loader_rc = std::system(loader_cmd.c_str());
    ASSERT_EQ(loader_rc, 0) << "parquet_to_kuzu_loader falló, cmd: " << loader_cmd;

    // 4. Verificar el grafo Kuzu resultante.
    kuzu::main::SystemConfig db_cfg;
    auto db   = std::make_unique<kuzu::main::Database>(kuzu_db_path, db_cfg);
    auto conn = std::make_unique<kuzu::main::Connection>(db.get());

    EXPECT_EQ(count_query(*conn, "MATCH (f:NetworkFlow) RETURN count(*)"), 2);
    EXPECT_EQ(count_query(*conn, "MATCH (a:Alert) RETURN count(*)"), 1);
    EXPECT_EQ(count_query(*conn, "MATCH (t:TelemetryEvent) RETURN count(*)"), 1);
    EXPECT_EQ(count_query(*conn,
        "MATCH (:Alert)-[:ALERT_ABOUT]->(:NetworkFlow) RETURN count(*)"), 1);
    EXPECT_EQ(count_query(*conn,
        "MATCH (:TelemetryEvent)-[:TELEMETRY_ABOUT]->(:NetworkFlow) RETURN count(*)"), 1);

    // 5. flow_uid bit-exacto: calculado independientemente aquí (mismo flow_uid.hpp
    //    que usan Camino 0 y Flujo A+B), comparado contra lo que Kuzu materializó
    //    de verdad tras pasar por el converter + loader reales.
    const uint64_t window = window_micros(1717480800, 123456000);
    const std::string expected_flow_uid_alert =
        compute_flow_uid(node_id_alert, community_alert, window);
    const std::string expected_flow_uid_benign =
        compute_flow_uid(node_id_benign, community_benign, window);

    EXPECT_EQ(count_query(*conn,
        "MATCH (f:NetworkFlow {flow_uid: '" + expected_flow_uid_alert + "'}) RETURN count(*)"), 1)
        << "flow_uid del flujo MALICIOUS no coincide con el calculado independientemente";
    EXPECT_EQ(count_query(*conn,
        "MATCH (f:NetworkFlow {flow_uid: '" + expected_flow_uid_benign + "'}) RETURN count(*)"), 1)
        << "flow_uid del flujo BENIGN no coincide con el calculado independientemente";

    // Limpieza — Kuzu de test desechable, nunca persiste entre ejecuciones.
    fs::remove_all(bronze_base);
    fs::remove(avro_path);
    fs::remove(parquet_path);
    fs::remove_all(kuzu_db_path);
}