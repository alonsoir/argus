cmake_minimum_required(VERSION 3.20)
project(correlation_engine VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
add_compile_options(-Wall -Wextra -Werror)

find_package(PkgConfig REQUIRED)
pkg_check_modules(LIBSODIUM REQUIRED libsodium)
message(STATUS "libsodium: ${LIBSODIUM_VERSION}")
find_package(OpenSSL REQUIRED)   # HMAC del reader (mismo OpenSSL que ml-detector/firewall)

# nlohmann_json: find_package -> fallback header-only vendoreado (patrón del proyecto)
find_package(nlohmann_json 3.11.0 QUIET)
if(NOT nlohmann_json_FOUND)
    find_path(NLOHMANN_JSON_INCLUDE_DIR nlohmann/json.hpp
            PATHS /usr/include /usr/local/include
            ${CMAKE_CURRENT_SOURCE_DIR}/../third_party/json/include)
    if(NLOHMANN_JSON_INCLUDE_DIR)
        message(STATUS "nlohmann/json (header-only): ${NLOHMANN_JSON_INCLUDE_DIR}")
        add_library(nlohmann_json INTERFACE)
        target_include_directories(nlohmann_json INTERFACE ${NLOHMANN_JSON_INCLUDE_DIR})
        add_library(nlohmann_json::nlohmann_json ALIAS nlohmann_json)
    else()
        message(FATAL_ERROR "nlohmann/json no encontrado. Vendorear en ../third_party/json/include o instalar nlohmann-json3-dev")
    endif()
else()
    message(STATUS "nlohmann/json: ${nlohmann_json_VERSION}")
endif()

# ── Kuzu v0.11.3 embebido (backend IGraphSink, DAY 180) ──────────────────────
# Lib precompilada instalada en /usr/local por el provisioning (libkuzu.so + kuzu.hpp).
# NO hay paquete apt (upstream archivado 10-oct-2025); pin por SHA256 en el Vagrantfile.
# find_library, NO add_subdirectory: misma lección que ntp_utils.
find_library(KUZU_LIB NAMES kuzu PATHS /usr/local/lib REQUIRED)
find_path(KUZU_INC kuzu.hpp PATHS /usr/local/include REQUIRED)
message(STATUS "libkuzu: ${KUZU_LIB}")

# ── avro-c + Arrow/Parquet (DAY 207: bronze_to_gold_converter graduado a produccion) ──
# Fallback defensivo: en shells no-interactivos (p.ej. `vagrant ssh -c`, o CI),
# .bashrc puede no cargarse -- y si se carga, puede apuntar a una ruta erronea
# (lib64 vs lib/x86_64-linux-gnu en Debian/Ubuntu). Lección DAY 207: no asumir,
# anadir la ruta real como fallback sin pisar un PKG_CONFIG_PATH ya correcto.
if(EXISTS "/usr/lib/x86_64-linux-gnu/pkgconfig")
    set(ENV{PKG_CONFIG_PATH} "/usr/lib/x86_64-linux-gnu/pkgconfig:$ENV{PKG_CONFIG_PATH}")
endif()
pkg_check_modules(AVROC REQUIRED avro-c)
pkg_check_modules(ARROW REQUIRED arrow)
pkg_check_modules(PARQUET REQUIRED parquet)
message(STATUS "avro-c: ${AVROC_VERSION} | arrow: ${ARROW_VERSION} | parquet: ${PARQUET_VERSION}")

# ── librería del engine: flow_uid (header-only) + reader + sinks ──
add_library(correlation_engine STATIC
        src/correlation_reader.cpp
        src/logging_graph_sink.cpp
        src/kuzu_graph_sink.cpp
        src/config_loader.cpp
        src/bronze_dir_watcher.cpp
        src/segment_processor.cpp)
target_include_directories(correlation_engine PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_include_directories(correlation_engine PUBLIC ${LIBSODIUM_INCLUDE_DIRS})
target_include_directories(correlation_engine PRIVATE ${KUZU_INC})  # solo el .cpp incluye kuzu.hpp
target_link_libraries(correlation_engine PUBLIC
        ${LIBSODIUM_LIBRARIES} OpenSSL::Crypto ${KUZU_LIB})  # KUZU_LIB PUBLIC -> se propaga a bin+tests
target_link_libraries(correlation_engine PRIVATE nlohmann_json::nlohmann_json)  # DAY 202: config_loader.cpp


# ── binario del engine (DAY 179: consumidor F1 bronce -> grafo) ──
find_package(spdlog REQUIRED)
# ntp_utils (ADR-046 P0): .a instalada por el build de common.
# (find_library, NO subdir-include: este ultimo contaminaria el ctest del engine.)
find_library(NTP_UTILS_LIB NAMES ntp_utils PATHS /usr/local/lib REQUIRED)
find_path(NTP_UTILS_INC ntp_health_check.hpp PATHS /usr/local/include/vault_client REQUIRED)
add_executable(correlation_engine_bin src/main.cpp)
target_include_directories(correlation_engine_bin PRIVATE ${NTP_UTILS_INC})
target_link_libraries(correlation_engine_bin PRIVATE correlation_engine spdlog::spdlog ${NTP_UTILS_LIB})

# ── tests (GoogleTest) ──
enable_testing()
find_package(GTest REQUIRED)

add_executable(test_flow_uid tests/test_flow_uid.cpp)
target_link_libraries(test_flow_uid PRIVATE correlation_engine nlohmann_json::nlohmann_json GTest::gtest_main)
target_compile_definitions(test_flow_uid PRIVATE
        VECTORS_PATH="${CMAKE_CURRENT_SOURCE_DIR}/tests/vectors/correlation_vectors.json")
add_test(NAME test_flow_uid COMMAND test_flow_uid)

add_executable(test_correlation_reader tests/test_correlation_reader.cpp)
target_link_libraries(test_correlation_reader PRIVATE correlation_engine GTest::gtest_main)
add_test(NAME test_correlation_reader COMMAND test_correlation_reader)

add_executable(test_graph_sink_loop tests/test_graph_sink_loop.cpp)
target_link_libraries(test_graph_sink_loop PRIVATE correlation_engine spdlog::spdlog GTest::gtest_main)
add_test(NAME test_graph_sink_loop COMMAND test_graph_sink_loop)

# ── H-1: escape de literales Cypher resistente a backslash (anti-inyeccion) ──
add_executable(test_cypher_injection tests/test_cypher_injection.cpp)
target_link_libraries(test_cypher_injection PRIVATE correlation_engine GTest::gtest_main)
add_test(NAME test_cypher_injection COMMAND test_cypher_injection)

# ── test del backend Kuzu (DAY 180): materializacion real en BD efimera ──
add_executable(test_kuzu_graph_sink tests/test_kuzu_graph_sink.cpp)
target_include_directories(test_kuzu_graph_sink PRIVATE ${KUZU_INC})  # el test reabre la BD para verificar
target_link_libraries(test_kuzu_graph_sink PRIVATE correlation_engine spdlog::spdlog GTest::gtest_main)
target_compile_definitions(test_kuzu_graph_sink PRIVATE
        SCHEMA_PATH="${CMAKE_CURRENT_SOURCE_DIR}/schema/schema.cypher")
add_test(NAME test_kuzu_graph_sink COMMAND test_kuzu_graph_sink)

# ── DAY 183: path PARAMETRIZADO (ADR-057) — prepare + bind_params + execute ──
# Verifica VERIFY-1/2/3 + H-1 estructural en BD efimera. NO toca el sink de produccion.
add_executable(test_cypher_prepared tests/test_cypher_prepared.cpp)
target_include_directories(test_cypher_prepared PRIVATE ${KUZU_INC})
target_link_libraries(test_cypher_prepared PRIVATE correlation_engine spdlog::spdlog GTest::gtest_main)
target_compile_definitions(test_cypher_prepared PRIVATE
        SCHEMA_PATH="${CMAKE_CURRENT_SOURCE_DIR}/schema/schema.cypher")
add_test(NAME test_cypher_prepared COMMAND test_cypher_prepared)

# ── SMOKE concurrencia Kuzu (ADR-057 F0, DEBT-KUZU-CONCURRENCY-SMOKE-001) ──
# Medicion, NO test: se corre a mano. correlation_engine ya propaga KUZU_LIB (PUBLIC).
find_package(Threads REQUIRED)
add_executable(kuzu_concurrency_smoke experiments/kuzu_concurrency_smoke.cpp)
target_include_directories(kuzu_concurrency_smoke PRIVATE ${KUZU_INC})
target_link_libraries(kuzu_concurrency_smoke PRIVATE correlation_engine Threads::Threads)

# ── DAY 207 — bronze_to_gold_converter: graduado de prototipo a produccion ──
# Eslabon 1, Flujo A (ADR-058 §3, ratificado 9/9 DAY 205). Lee bronce real,
# escribe AVRO (bronce, copia exacta) + Parquet oro (cols D, 0-21). Enlaza
# contra correlation_engine (hereda libsodium+OpenSSL::Crypto PUBLIC) +
# avro-c/Arrow/Parquet. NO es un test -- sin add_test, se ejecuta a mano
# (mismo patron que kuzu_concurrency_smoke: medicion/herramienta, no test CI).
add_executable(bronze_to_gold_converter tools/bronze_to_gold_converter.cpp)
target_include_directories(bronze_to_gold_converter PRIVATE
        ${AVROC_INCLUDE_DIRS} ${ARROW_INCLUDE_DIRS} ${PARQUET_INCLUDE_DIRS})
target_link_libraries(bronze_to_gold_converter PRIVATE
        correlation_engine
        ${AVROC_LIBRARIES} ${ARROW_LIBRARIES} ${PARQUET_LIBRARIES})

# ── DAY 208 — parquet_to_kuzu_loader: Flujo B (ADR-058 §6, Eslabón 2) ──
# Ratificado por el Consejo 9/9 (DAY 207). Lee Parquet oro (Flujo A), escribe
# a Kuzu reusando KuzuGraphSink sin cambios. Alcance v1: esquema mono-fuente
# correlation_v1 (DEBT-PARQUET-GOLD-SCHEMA-MULTISENSOR-001 queda fuera).
# NO usa avro-c (Flujo B no toca AVRO) -- solo Arrow/Parquet + correlation_engine.
add_executable(parquet_to_kuzu_loader tools/parquet_to_kuzu_loader.cpp)
target_include_directories(parquet_to_kuzu_loader PRIVATE
        ${ARROW_INCLUDE_DIRS} ${PARQUET_INCLUDE_DIRS} ${KUZU_INC})
target_link_libraries(parquet_to_kuzu_loader PRIVATE
        correlation_engine
        ${ARROW_LIBRARIES} ${PARQUET_LIBRARIES}
        spdlog::spdlog)
# ── DAY 204 — emecas+++: circuito completo bronce->Kuzu, un solo proceso, FS puro ──
# ADR-058 §1: inyectar evento sintetico -> verificar HMAC en bronce -> verificar
# MATCH en Kuzu. Cruza a ml-detector (CorrelationWriter real), mismo patron que
# ml-detector/tests/test_correlation_roundtrip.cpp usa en sentido inverso.
find_package(Protobuf REQUIRED)
find_library(CORRELATION_V1_LIB NAMES correlation_v1 PATHS /usr/local/lib REQUIRED)

add_executable(test_bronze_to_kuzu_circuit
        tests/test_bronze_to_kuzu_circuit.cpp
        ${CMAKE_CURRENT_SOURCE_DIR}/../ml-detector/src/correlation_writer.cpp
        ${CMAKE_CURRENT_SOURCE_DIR}/../protobuf/network_security.pb.cc)
target_include_directories(test_bronze_to_kuzu_circuit PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/../ml-detector/include
        ${CMAKE_CURRENT_SOURCE_DIR}/../protobuf
        ${KUZU_INC}
        /usr/local/include)
target_link_libraries(test_bronze_to_kuzu_circuit PRIVATE
        correlation_engine
        ${CORRELATION_V1_LIB}
        ${Protobuf_LIBRARIES}
        spdlog::spdlog
        OpenSSL::SSL
        OpenSSL::Crypto
        GTest::gtest_main)
target_compile_definitions(test_bronze_to_kuzu_circuit PRIVATE
        SCHEMA_PATH="${CMAKE_CURRENT_SOURCE_DIR}/schema/schema.cypher")
add_test(NAME test_bronze_to_kuzu_circuit COMMAND test_bronze_to_kuzu_circuit)

# ── DAY 208 — test_flujo_b_end_to_end: verificación de Kuzu dentro de EMECAS+++ ──
# Invoca los binarios REALES (bronze_to_gold_converter, parquet_to_kuzu_loader)
# como subprocesos -- caja negra, sin refactorizar el converter. Petición de
# Alonso: confirmar que Kuzu funciona bien como parte del gate de calidad.
add_executable(test_flujo_b_end_to_end tests/test_flujo_b_end_to_end.cpp
        ${CMAKE_CURRENT_SOURCE_DIR}/../ml-detector/src/correlation_writer.cpp
        ${CMAKE_CURRENT_SOURCE_DIR}/../protobuf/network_security.pb.cc)
target_include_directories(test_flujo_b_end_to_end PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/../ml-detector/include
        ${CMAKE_CURRENT_SOURCE_DIR}/../protobuf
        ${KUZU_INC}
        /usr/local/include)
target_link_libraries(test_flujo_b_end_to_end PRIVATE
        correlation_engine
        ${CORRELATION_V1_LIB}
        ${Protobuf_LIBRARIES}
        spdlog::spdlog
        OpenSSL::SSL
        OpenSSL::Crypto
        GTest::gtest_main)
target_compile_definitions(test_flujo_b_end_to_end PRIVATE
        SCHEMA_PATH="${CMAKE_CURRENT_SOURCE_DIR}/schema/schema.cypher"
        CONVERTER_BIN_PATH="$<TARGET_FILE:bronze_to_gold_converter>"
        LOADER_BIN_PATH="$<TARGET_FILE:parquet_to_kuzu_loader>")
add_dependencies(test_flujo_b_end_to_end bronze_to_gold_converter parquet_to_kuzu_loader)
add_test(NAME test_flujo_b_end_to_end COMMAND test_flujo_b_end_to_end)