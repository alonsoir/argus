cmake_minimum_required(VERSION 3.20)
project(ml-detector-tricapa VERSION 1.0.0 LANGUAGES CXX)

# ============================================================================
# C++20 STANDARD
# ============================================================================
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# ============================================================================
# BUILD OPTIONS
# ============================================================================
option(BUILD_TESTS "Build unit and integration tests" ON)
option(ENABLE_PROFILING "Enable profiling support" OFF)

# ============================================================================
# COMPILER FLAGS - CONTROLLED BY ROOT MAKEFILE
# ============================================================================
# ⚠️  NO HARDCODED FLAGS - All flags come from root Makefile via CMAKE_CXX_FLAGS
# ⚠️  DO NOT set CMAKE_CXX_FLAGS_DEBUG, CMAKE_CXX_FLAGS_RELEASE, etc.
# ⚠️  DO NOT set -fsanitize, -O, -g flags here
#
# The root Makefile controls all optimization and sanitizer flags via:
#   make PROFILE=production  → -O3 -march=native -DNDEBUG -flto
#   make PROFILE=debug       → -g -O0 -fno-omit-frame-pointer
#   make PROFILE=tsan        → -fsanitize=thread -g -O1
#   make PROFILE=asan        → -fsanitize=address -g -O1
# ============================================================================

message(STATUS "Build type: ${CMAKE_BUILD_TYPE}")
message(STATUS "C++ Standard: ${CMAKE_CXX_STANDARD}")
message(STATUS "CXX Flags (from Makefile): ${CMAKE_CXX_FLAGS}")

# ============================================================================
# FIND DEPENDENCIES
# ============================================================================

# PkgConfig for system libraries
find_package(PkgConfig REQUIRED)

# nlohmann_json
find_package(nlohmann_json REQUIRED)
message(STATUS "Found nlohmann_json")

# ZeroMQ
pkg_check_modules(ZMQ REQUIRED IMPORTED_TARGET libzmq)
message(STATUS "Found ZeroMQ: ${ZMQ_VERSION}")

# Protobuf
find_package(Protobuf REQUIRED)
message(STATUS "Found Protobuf: ${Protobuf_VERSION}")

# ONNX Runtime
find_package(onnxruntime QUIET)
if(NOT onnxruntime_FOUND)
    # Fallback: buscar manualmente
    find_path(ONNXRUNTIME_INCLUDE_DIR onnxruntime_cxx_api.h
            PATHS
            /usr/local/include/onnxruntime
            /usr/include/onnxruntime
            ${CMAKE_CURRENT_SOURCE_DIR}/../third_party/onnxruntime/include
    )
    find_library(ONNXRUNTIME_LIB onnxruntime
            PATHS
            /usr/local/lib
            /usr/lib
            ${CMAKE_CURRENT_SOURCE_DIR}/../third_party/onnxruntime/lib
    )
    if(ONNXRUNTIME_INCLUDE_DIR AND ONNXRUNTIME_LIB)
        message(STATUS "Found ONNX Runtime (manual): ${ONNXRUNTIME_LIB}")
        add_library(onnxruntime SHARED IMPORTED)
        set_target_properties(onnxruntime PROPERTIES
                IMPORTED_LOCATION ${ONNXRUNTIME_LIB}
                INTERFACE_INCLUDE_DIRECTORIES ${ONNXRUNTIME_INCLUDE_DIR}
        )
    else()
        message(FATAL_ERROR "ONNX Runtime not found. Install from: https://github.com/microsoft/onnxruntime/releases")
    endif()
endif()

# nlohmann/json
find_package(nlohmann_json 3.11.0 QUIET)
if(NOT nlohmann_json_FOUND)
    # Fallback: header-only
    find_path(NLOHMANN_JSON_INCLUDE_DIR nlohmann/json.hpp
            PATHS
            /usr/include
            /usr/local/include
            ${CMAKE_CURRENT_SOURCE_DIR}/../third_party/json/include
    )
    if(NLOHMANN_JSON_INCLUDE_DIR)
        message(STATUS "Found nlohmann/json (header-only): ${NLOHMANN_JSON_INCLUDE_DIR}")
        add_library(nlohmann_json INTERFACE)
        target_include_directories(nlohmann_json INTERFACE ${NLOHMANN_JSON_INCLUDE_DIR})
    else()
        message(FATAL_ERROR "nlohmann/json not found. Install: sudo apt-get install nlohmann-json3-dev")
    endif()
else()
    message(STATUS "Found nlohmann/json: ${nlohmann_json_VERSION}")
endif()

# spdlog
find_package(spdlog QUIET)
if(NOT spdlog_FOUND)
    pkg_check_modules(SPDLOG REQUIRED IMPORTED_TARGET spdlog)
    message(STATUS "Found spdlog (pkg-config): ${SPDLOG_VERSION}")
else()
    message(STATUS "Found spdlog: ${spdlog_VERSION}")
endif()

# etcd-cpp-apiv3 (optional)
find_package(etcd-cpp-api QUIET)
if(etcd-cpp-api_FOUND)
    message(STATUS "Found etcd-cpp-api: ${etcd-cpp-api_VERSION}")
    set(HAVE_ETCD_CPP_API TRUE)
else()
    message(STATUS "etcd-cpp-api not found - ETCD integration will be disabled")
    set(HAVE_ETCD_CPP_API FALSE)
endif()

# ============================================================================
# ETCD-CLIENT LIBRARY (Custom)
# ============================================================================
set(ETCD_CLIENT_LIB /vagrant/etcd-client/build/libetcd_client.so)
set(ETCD_CLIENT_INCLUDE_DIR /vagrant/etcd-client/include)

if(EXISTS ${ETCD_CLIENT_LIB})
    message(STATUS "✅ Found etcd-client library: ${ETCD_CLIENT_LIB}")
    include_directories(${ETCD_CLIENT_INCLUDE_DIR})
    set(HAVE_ETCD_CLIENT TRUE)
else()
    message(FATAL_ERROR "❌ etcd-client library not found - required for ml-detector")
endif()

# ============================================================================
# CRYPTO-TRANSPORT LIBRARY (Custom)
# ============================================================================
# Busca primero en /usr/local (instalación system-wide), luego en build local
find_library(CRYPTO_TRANSPORT_LIB
        NAMES crypto_transport
        PATHS
        /usr/local/lib
        /vagrant/crypto-transport/build
        NO_DEFAULT_PATH
)

find_path(CRYPTO_TRANSPORT_INCLUDE_DIR
        NAMES crypto_transport/crypto_manager.hpp
        PATHS
        /usr/local/include
        /vagrant/crypto-transport/include
        NO_DEFAULT_PATH
)

if(CRYPTO_TRANSPORT_LIB AND CRYPTO_TRANSPORT_INCLUDE_DIR)
    message(STATUS "✅ Found crypto-transport library: ${CRYPTO_TRANSPORT_LIB}")
    message(STATUS "✅ Found crypto-transport headers: ${CRYPTO_TRANSPORT_INCLUDE_DIR}")
    include_directories(${CRYPTO_TRANSPORT_INCLUDE_DIR})
    set(HAVE_CRYPTO_TRANSPORT TRUE)
else()
    message(FATAL_ERROR "❌ crypto-transport not found - required for ml-detector
    Library: ${CRYPTO_TRANSPORT_LIB}
    Headers: ${CRYPTO_TRANSPORT_INCLUDE_DIR}

    Fix: Run 'make crypto-transport-build' from project root")
endif()

# ADR-013 PHASE 2 — DAY 98: seed-client
find_library(SEED_CLIENT_LIB
        NAMES seed_client
        PATHS /usr/local/lib
        NO_DEFAULT_PATH
)
find_path(SEED_CLIENT_INCLUDE_DIR
        NAMES seed_client/seed_client.hpp
        PATHS /usr/local/include
        NO_DEFAULT_PATH
)
if(SEED_CLIENT_LIB AND SEED_CLIENT_INCLUDE_DIR)
    message(STATUS "✅ Found seed-client: ${SEED_CLIENT_LIB}")
    include_directories(${SEED_CLIENT_INCLUDE_DIR})
else()
    message(FATAL_ERROR "❌ seed-client not found. Run make seed-client-build from project root")
endif()

# LZ4 (para compresión directa — DAY 98)
pkg_check_modules(LZ4 REQUIRED liblz4)
if(NOT LZ4_FOUND)
    message(FATAL_ERROR "liblz4 not found. Install: sudo apt-get install liblz4-dev")
endif()
message(STATUS "✅ LZ4 found: ${LZ4_VERSION}")
include_directories(${LZ4_INCLUDE_DIRS})

# Threads
find_package(Threads REQUIRED)

# ============================================================================
# PROTOBUF UNIFICADO - VERIFICACIÓN Y CONFIGURACIÓN
# ============================================================================

# Verificar que los archivos protobuf unificados existen
if(NOT EXISTS "${CMAKE_BINARY_DIR}/proto/network_security.pb.cc")
    message(FATAL_ERROR "❌ Protobuf unificado no encontrado. Ejecuta: cd /vagrant/protobuf && ./generate.sh")
else()
    message(STATUS "✅ Protobuf unificado encontrado: ${CMAKE_BINARY_DIR}/proto/network_security.pb.cc")
endif()

set(PROTO_SOURCES ${CMAKE_BINARY_DIR}/proto/network_security.pb.cc)
set(PROTO_HEADERS ${CMAKE_BINARY_DIR}/proto/network_security.pb.h)
# Suprimir warnings en fichero generado por protobuf (no código nuestro)
set_source_files_properties(${PROTO_SOURCES} PROPERTIES
    COMPILE_OPTIONS "-Wno-sign-conversion;-Wno-conversion"
)
# Suprimir warnings en source files que incluyen árboles XGBoost generados
set_source_files_properties(
    ${CMAKE_CURRENT_SOURCE_DIR}/src/ddos_detector.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/src/traffic_detector.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/src/internal_detector.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/src/ransomware_detector.cpp
    PROPERTIES COMPILE_OPTIONS "-Wno-sign-conversion;-Wno-conversion"
)

# ============================================================================
# SOURCE FILES
# ============================================================================
set(SOURCES
        src/main.cpp
        src/classifier_tricapa.cpp
        src/feature_extractor.cpp
        src/rag_logger.cpp
        src/contract_validator.cpp
        src/zmq_handler.cpp
        src/model_loader.cpp
        src/onnx_model.cpp
        src/config_loader.cpp
        src/logger.cpp
        src/stats_collector.cpp
        src/ransomware_detector.cpp
        src/ddos_detector.cpp
        src/traffic_detector.cpp
        src/internal_detector.cpp
        src/etcd_client.cpp
        src/csv_event_writer.cpp
        ${PROTO_SOURCES}
)

# ML Defender - Ransomware Detector Library
add_library(ransomware_detector
        src/ransomware_detector.cpp
)

target_include_directories(ransomware_detector
        PUBLIC
        ${CMAKE_CURRENT_SOURCE_DIR}/include
        PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/src
)

target_compile_features(ransomware_detector
        PUBLIC cxx_std_20
)

# Warnings only (no optimization flags - controlled by Makefile)
target_compile_options(ransomware_detector PRIVATE
        -Wall
        -Wextra
        -Wpedantic
)

# Optional: Install headers
install(DIRECTORY include/ml_defender
        DESTINATION include
        FILES_MATCHING PATTERN "*.hpp"
)

set(HEADERS
        include/ml_detector.hpp
        include/classifier_tricapa.hpp
        include/feature_extractor.hpp
        include/model_loader.hpp
        include/onnx_model.hpp
        include/zmq_handler.hpp
        include/config_loader.hpp
        include/logger.hpp
        include/stats_collector.hpp
        include/concurrent_queue.hpp
        include/etcd_client.hpp
        ${PROTO_HEADERS}
)

# ============================================================================
# INCLUDE DIRECTORIES - ACTUALIZADO PARA PROTOBUF UNIFICADO y reason_codes
# ============================================================================
include_directories(
        ${CMAKE_CURRENT_SOURCE_DIR}/include
        ${CMAKE_BINARY_DIR}/proto  # Archivos protobuf unificados
        ${CMAKE_CURRENT_SOURCE_DIR}/../contrib/safe-path/include
        /vagrant/common/include # Se incluye reason_codes.hpp
)

# ============================================================================
# MODELS SYMLINK (Single Source of Truth)
# ============================================================================
message(STATUS "")
message(STATUS "🔗 Setting up models symlink...")
message(STATUS "   Source: ${CMAKE_SOURCE_DIR}/models")
message(STATUS "   Target: ${CMAKE_BINARY_DIR}/models")

# Remove existing symlink/directory if it exists
if(EXISTS ${CMAKE_BINARY_DIR}/models)
    file(REMOVE ${CMAKE_BINARY_DIR}/models)
endif()

# Create symlink
execute_process(
        COMMAND ${CMAKE_COMMAND} -E create_symlink
        ${CMAKE_SOURCE_DIR}/models
        ${CMAKE_BINARY_DIR}/models
        RESULT_VARIABLE SYMLINK_RESULT
)

if(SYMLINK_RESULT EQUAL 0)
    message(STATUS "✅ Models symlink created successfully")
    message(STATUS "   Config will use: models/production/")
    message(STATUS "   Points to:       ../models/production/")
else()
    message(WARNING "⚠️  Failed to create models symlink")
    message(WARNING "   Manual workaround: cp -r ${CMAKE_SOURCE_DIR}/models ${CMAKE_BINARY_DIR}/")
endif()

# ============================================================================
# CONFIG SYMLINK (Single Source of Truth)
# ============================================================================
message(STATUS "")
message(STATUS "🔗 Setting up config symlink...")
message(STATUS "   Source: ${CMAKE_SOURCE_DIR}/config")
message(STATUS "   Target: ${CMAKE_BINARY_DIR}/config")

# Remove existing symlink/directory if it exists
if(EXISTS ${CMAKE_BINARY_DIR}/config)
    file(REMOVE_RECURSE ${CMAKE_BINARY_DIR}/config)
endif()

# Create symlink
execute_process(
        COMMAND ${CMAKE_COMMAND} -E create_symlink
        ${CMAKE_SOURCE_DIR}/config
        ${CMAKE_BINARY_DIR}/config
        RESULT_VARIABLE CONFIG_SYMLINK_RESULT
)

if(CONFIG_SYMLINK_RESULT EQUAL 0)
    message(STATUS "✅ Config symlink created successfully")
else()
    message(WARNING "⚠️  Failed to create config symlink")
endif()

message(STATUS "")

# ============================================================================
# MAIN EXECUTABLE
# ============================================================================
add_executable(ml-detector ${SOURCES} ${HEADERS})

target_include_directories(ml-detector PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/include
        ${CMAKE_BINARY_DIR}/proto  # Archivos protobuf unificados
        ${CMAKE_CURRENT_SOURCE_DIR}/../contrib/safe-path/include
)

find_package(OpenSSL REQUIRED)
message(STATUS "Found OpenSSL: ${OPENSSL_VERSION}")

# ============================================================================
# LINK LIBRARIES
# ============================================================================
target_link_libraries(ml-detector PRIVATE
        PkgConfig::ZMQ
        ${Protobuf_LIBRARIES}
        onnxruntime
        Threads::Threads
        ransomware_detector
        nlohmann_json::nlohmann_json
        ${ETCD_CLIENT_LIB}
        ${CRYPTO_TRANSPORT_LIB}
        ${SEED_CLIENT_LIB}
        ${LZ4_LIBRARIES}
        OpenSSL::SSL          # Day 63: HMAC-SHA256 para CsvEventWriter
        OpenSSL::Crypto       # Day 63
)

# nlohmann/json
if(TARGET nlohmann_json::nlohmann_json)
    target_link_libraries(ml-detector PRIVATE nlohmann_json::nlohmann_json)
elseif(TARGET nlohmann_json)
    target_link_libraries(ml-detector PRIVATE nlohmann_json)
endif()

# spdlog
if(TARGET spdlog::spdlog)
    target_link_libraries(ml-detector PRIVATE spdlog::spdlog)
elseif(TARGET PkgConfig::SPDLOG)
    target_link_libraries(ml-detector PRIVATE PkgConfig::SPDLOG)
endif()

# etcd (optional)
if(HAVE_ETCD_CPP_API)
    target_link_libraries(ml-detector PRIVATE etcd-cpp-api)
    target_compile_definitions(ml-detector PRIVATE HAVE_ETCD_CPP_API)
endif()

# ============================================================================
# COMPILER OPTIONS - Warnings Only
# ============================================================================
# ⚠️  Optimization flags (-O3, -g, -fsanitize) are controlled by root Makefile
# ⚠️  Only warnings are set here

target_compile_options(ml-detector PRIVATE
        -Wall
        -Wextra
        -Wpedantic
        -Wconversion
        -Wsign-conversion
        -Wno-unused-parameter
)

# Position Independent Code
set_property(TARGET ml-detector PROPERTY POSITION_INDEPENDENT_CODE ON)

# ============================================================================
# TESTS
# ============================================================================
if(BUILD_TESTS)
    enable_testing()
    find_package(GTest QUIET)
    add_subdirectory(tests)
endif()


# ============================================================================
# ADR-012 PHASE 1b — plugin-loader (ml-detector)
# ============================================================================
find_library(PLUGIN_LOADER_LIB
        NAMES plugin_loader
        PATHS /usr/local/lib
        NO_DEFAULT_PATH)

find_path(PLUGIN_LOADER_INCLUDE_DIR
        NAMES plugin_loader/plugin_loader.hpp
        PATHS /usr/local/include
        NO_DEFAULT_PATH)

if(PLUGIN_LOADER_LIB AND PLUGIN_LOADER_INCLUDE_DIR)
    message(STATUS "✅ Found plugin-loader: ${PLUGIN_LOADER_LIB}")
else()
    message(WARNING "⚠️  plugin-loader not found — plugins disabled (non-fatal)")
    set(PLUGIN_LOADER_LIB "")
endif()

# ============================================================================
# INSTALLATION
# ============================================================================
install(TARGETS ml-detector
        RUNTIME DESTINATION bin
        COMPONENT runtime
)

install(DIRECTORY config/
        DESTINATION etc/ml-detector
        COMPONENT config
)

install(DIRECTORY models/
        DESTINATION share/ml-detector/models
        COMPONENT models
        PATTERN "*.onnx" EXCLUDE
        PATTERN "*.joblib" EXCLUDE
)

install(FILES README.md
        DESTINATION share/doc/ml-detector
        COMPONENT documentation
)


# ADR-012 PHASE 1b — plugin-loader
if(PLUGIN_LOADER_LIB)
    target_include_directories(ml-detector PRIVATE ${PLUGIN_LOADER_INCLUDE_DIR})
    target_link_libraries(ml-detector PRIVATE ${PLUGIN_LOADER_LIB})
    target_compile_definitions(ml-detector PRIVATE PLUGIN_LOADER_ENABLED)
endif()
# ============================================================================
# SUMMARY
# ============================================================================
message(STATUS "")
message(STATUS "======================================")
message(STATUS "ML Detector Tricapa - Configuration")
message(STATUS "======================================")
message(STATUS "Build type:        ${CMAKE_BUILD_TYPE}")
message(STATUS "C++ compiler:      ${CMAKE_CXX_COMPILER_ID} ${CMAKE_CXX_COMPILER_VERSION}")
message(STATUS "C++ standard:      ${CMAKE_CXX_STANDARD}")
message(STATUS "Install prefix:    ${CMAKE_INSTALL_PREFIX}")
message(STATUS "CXX Flags:         ${CMAKE_CXX_FLAGS}")
message(STATUS "")
message(STATUS "Dependencies:")
message(STATUS "  ZeroMQ:          ${ZMQ_VERSION}")
message(STATUS "  Protobuf:        ${Protobuf_VERSION}")
message(STATUS "  ONNX Runtime:    Found")
message(STATUS "  nlohmann/json:   Found")
message(STATUS "  spdlog:          Found")
message(STATUS "  etcd-client:     ${HAVE_ETCD_CLIENT}")
message(STATUS "  crypto-transport: ${HAVE_CRYPTO_TRANSPORT}")
message(STATUS "  etcd-cpp-api:    ${HAVE_ETCD_CPP_API}")
message(STATUS "")
message(STATUS "Options:")
message(STATUS "  Build tests:     ${BUILD_TESTS}")
message(STATUS "")
message(STATUS "🎯 Single Source of Truth:")
message(STATUS "  Models:          ${CMAKE_SOURCE_DIR}/models → build/models (symlink)")
message(STATUS "  Config:          ${CMAKE_SOURCE_DIR}/config → build/config (symlink)")
message(STATUS "  Protobuf:        ${CMAKE_BINARY_DIR}/proto/network_security.pb.cc (unificado)")
message(STATUS "  Compiler Flags:  Controlled by root Makefile via PROFILE")
message(STATUS "======================================")
message(STATUS "")