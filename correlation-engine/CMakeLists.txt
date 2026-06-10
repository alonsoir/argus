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

# ── librería del engine: flow_uid (header-only) + reader + sinks ──
add_library(correlation_engine STATIC
        src/correlation_reader.cpp
        src/logging_graph_sink.cpp
        src/kuzu_graph_sink.cpp)
target_include_directories(correlation_engine PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_include_directories(correlation_engine PUBLIC ${LIBSODIUM_INCLUDE_DIRS})
target_include_directories(correlation_engine PRIVATE ${KUZU_INC})  # solo el .cpp incluye kuzu.hpp
target_link_libraries(correlation_engine PUBLIC
        ${LIBSODIUM_LIBRARIES} OpenSSL::Crypto ${KUZU_LIB})  # KUZU_LIB PUBLIC -> se propaga a bin+tests


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

# ── test del backend Kuzu (DAY 180): materializacion real en BD efimera ──
add_executable(test_kuzu_graph_sink tests/test_kuzu_graph_sink.cpp)
target_include_directories(test_kuzu_graph_sink PRIVATE ${KUZU_INC})  # el test reabre la BD para verificar
target_link_libraries(test_kuzu_graph_sink PRIVATE correlation_engine spdlog::spdlog GTest::gtest_main)
target_compile_definitions(test_kuzu_graph_sink PRIVATE
        SCHEMA_PATH="${CMAKE_CURRENT_SOURCE_DIR}/schema/schema.cypher")
add_test(NAME test_kuzu_graph_sink COMMAND test_kuzu_graph_sink)