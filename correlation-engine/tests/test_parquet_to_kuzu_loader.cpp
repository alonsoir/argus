// test_parquet_to_kuzu_loader.cpp — ESQUELETO, DAY 208
// Flujo B, test de integración. Mismo patrón que test_bronze_to_kuzu_circuit.cpp
// (Camino 0): escribir con producción real -> leer con producción real ->
// verificar MATCH en Kuzu. Cero reimplementación.
//
// IMPORTANTE (aclarado por Alonso, DAY 207): este Kuzu es DE TEST, AISLADO Y
// DESECHABLE (path temporal, borrado al final). Camino 0 NUNCA fue candidato
// a producción -- solo valida tecnología. Producción real (Camino 1) llegará
// por ZMQ, no por FS. Este test NUNCA debe compartir base de datos con nada
// persistente.
//
// TODO DAY 209 (o cuando se retome): completar los TODO marcados abajo.
// NO registrado todavía en CMakeLists.txt -- añadir add_executable/add_test
// solo cuando este fichero compile y pase.

#include <gtest/gtest.h>

// TODO: incluir bronze_to_gold_converter como librería o reusar su lógica de
// escritura AVRO+Parquet -- probablemente haga falta extraer read_bronze_segment/
// write_gold_parquet del converter a un header reusable, en vez de #include del
// .cpp directamente (el converter hoy es un main() standalone, no una librería).
// Ver bronze_to_gold_converter.cpp -- decidir si esto justifica una refactorización
// pequeña (extraer funciones a un .hpp) antes de escribir este test.

#include "correlation_writer.hpp"                        // CorrelationWriter real (ml-detector)
#include "correlation_engine/kuzu_graph_sink.hpp"         // KuzuGraphSink real

#include <network_security.pb.h>
#include <google/protobuf/timestamp.pb.h>

#include <spdlog/spdlog.h>
#include <spdlog/sinks/null_sink.h>

#include <filesystem>
#include <string>
#include <cstdio>
#include <memory>

namespace fs = std::filesystem;

namespace {

std::shared_ptr<spdlog::logger> null_logger(const std::string& name) {
    return std::make_shared<spdlog::logger>(
        name, std::make_shared<spdlog::sinks::null_sink_mt>());
}

// TODO: mismo make_event() que test_bronze_to_kuzu_circuit.cpp -- considerar
// extraer a un header de test compartido (tests/test_fixtures.hpp) para no
// duplicar la construcción de NetworkSecurityEvent en dos ficheros de test.

}  // namespace

// ── Circuito completo Flujo B: bronce -> converter -> Parquet -> loader -> Kuzu ──
TEST(FlujoB, ParquetToKuzuHappyPath) {
    // 1. TODO: escribir bronce con CorrelationWriter real (mismo patrón que
    //    test_bronze_to_kuzu_circuit.cpp, sección 1).

    // 2. TODO: convertir bronce -> Parquet oro con la lógica REAL del converter
    //    (bloqueado hasta decidir la refactorización de arriba -- extraer
    //    read_bronze_segment/write_gold_parquet a un header reusable).

    // 3. TODO: cargar el Parquet oro con parquet_to_kuzu_loader REAL contra un
    //    Kuzu de test AISLADO (path temporal, ej. /tmp/test_flujo_b_<pid>.kuzu).
    //    NUNCA reusar un path de Kuzu que pudiera solaparse con otro test o con
    //    cualquier instancia de desarrollo -- ver nota de aislamiento arriba.

    // 4. TODO: verificar MATCH en Kuzu (mismo patrón que
    //    test_bronze_to_kuzu_circuit.cpp, sección 3):
    //      MATCH (f:NetworkFlow) RETURN count(*)
    //      MATCH (a:Alert) RETURN count(*)
    //      MATCH (:Alert)-[:ALERT_ABOUT]->(:NetworkFlow) RETURN count(*)

    GTEST_SKIP() << "Esqueleto DAY 208 -- pendiente de completar. "
                    "Ver TODOs y la nota sobre refactorización del converter.";
}

// ── Test de equivalencia real: Camino 0 vs Flujo A+B sobre el MISMO input ──
// Este es el criterio de cierre del medallón (predicado §3.1, ADR-058) --
// la razón última de que Flujo B exista. Requiere:
//   (a) Procesar el MISMO segmento bronce sintético por Camino 0 (process_segment
//       + KuzuGraphSink directo, patrón test_bronze_to_kuzu_circuit.cpp) hacia
//       un Kuzu de test A.
//   (b) Procesar el MISMO segmento por Flujo A (converter) + Flujo B (este
//       loader) hacia un Kuzu de test B, DISTINTO del A.
//   (c) Comparar ambos grafos: mismo conteo de NetworkFlow/Alert, mismos
//       flow_uid, mismos scores (ya canonicalizados igual, DAY 207), mismas
//       aristas (igualdad de conjuntos, no solo subconjunto -- ver ADR-058 v3,
//       objeción GLM/DeepSeek/Mistral aceptada).
//   (d) EXCLUIR de la comparación: ingested_at, temporal_anomaly (ADR-058 v3
//       ya los excluye del predicado -- no son parte de esta aserción).
TEST(FlujoB, EquivalenceCamino0VsFlujoAB) {
    GTEST_SKIP() << "Esqueleto DAY 208 -- el test de equivalencia real del "
                    "predicado §3.1 depende de que ParquetToKuzuHappyPath "
                    "funcione primero. No implementar antes de tiempo.";
}