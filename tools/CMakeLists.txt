# /vagrant/tools/CMakeLists.txt
# Synthetic Event Generator & Validator
# Via Appia Quality - Testing Tools
# Authors: Alonso Isidoro Roman + Claude (Anthropic)

cmake_minimum_required(VERSION 3.20)
project(ml-defender-tools VERSION 1.0.0 LANGUAGES CXX)

# ============================================================================
# C++20 STANDARD
# ============================================================================
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# ============================================================================
# COMPILER FLAGS - CONTROLLED BY ROOT MAKEFILE
# ============================================================================
# ⚠️  NO HARDCODED FLAGS - All flags come from root Makefile via CMAKE_CXX_FLAGS
# ⚠️  DO NOT set CMAKE_CXX_FLAGS_DEBUG, CMAKE_CXX_FLAGS_RELEASE here
# ⚠️  DO NOT set -O, -g, -march, -fsanitize flags here
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
# Dependencies
# ============================================================================

# PkgConfig (needed for LZ4)
find_package(PkgConfig REQUIRED)

# LZ4 (compression — needed by rag_logger.cpp)
pkg_check_modules(LZ4 REQUIRED liblz4)

# Protobuf
find_package(Protobuf REQUIRED)
include_directories(${Protobuf_INCLUDE_DIRS})

# spdlog
find_package(spdlog REQUIRED)

# nlohmann_json
find_package(nlohmann_json REQUIRED)

# Threads
find_package(Threads REQUIRED)

# OpenSSL (for SHA256 in RAGLogger)
find_package(OpenSSL REQUIRED)

# CURL (for etcd_client HTTP)
find_package(CURL REQUIRED)

# ============================================================================
# System Libraries
# ============================================================================

# etcd-client (from local build)
set(ETCD_CLIENT_LIB /vagrant/etcd-client/build/libetcd_client.so)
set(ETCD_CLIENT_INCLUDE_DIR /vagrant/etcd-client/include)
if(EXISTS ${ETCD_CLIENT_LIB})
    message(STATUS "✅ Found etcd-client library: ${ETCD_CLIENT_LIB}")
    include_directories(${ETCD_CLIENT_INCLUDE_DIR})
else()
    message(FATAL_ERROR "❌ etcd-client library not found at ${ETCD_CLIENT_LIB}
    Run: make etcd-client-build")
endif()

# crypto-transport (search /usr/local first, then local build)
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
else()
    message(FATAL_ERROR "❌ crypto-transport not found
    Library: ${CRYPTO_TRANSPORT_LIB}
    Headers: ${CRYPTO_TRANSPORT_INCLUDE_DIR}
    Run: make crypto-transport-build")
endif()

# ============================================================================
# Include Directories
# ============================================================================

include_directories(
        ${CMAKE_CURRENT_SOURCE_DIR}/../protobuf
        ${CMAKE_CURRENT_SOURCE_DIR}/../common/include
        ${CMAKE_CURRENT_SOURCE_DIR}/../ml-detector/include
        ${CMAKE_CURRENT_SOURCE_DIR}/../crypto-transport/include
        ${CMAKE_CURRENT_SOURCE_DIR}/../etcd-client/include
        /usr/local/include
        ${OPENSSL_INCLUDE_DIR}
        ${CURL_INCLUDE_DIRS}
)

# ============================================================================
# Protobuf Sources
# ============================================================================

# Protobuf sources (compile directly, not as library)
set(PROTO_SOURCES ${CMAKE_CURRENT_SOURCE_DIR}/../protobuf/network_security.pb.cc)
set(PROTO_HEADERS ${CMAKE_CURRENT_SOURCE_DIR}/../protobuf/network_security.pb.h)

# ============================================================================
# 1. Synthetic Event Generator
# ============================================================================

add_executable(generate_synthetic_events
        generate_synthetic_events.cpp
        ${PROTO_SOURCES}
        ${CMAKE_CURRENT_SOURCE_DIR}/../ml-detector/src/rag_logger.cpp
        ${CMAKE_CURRENT_SOURCE_DIR}/../ml-detector/src/csv_event_writer.cpp
        ${CMAKE_CURRENT_SOURCE_DIR}/../ml-detector/src/etcd_client.cpp
)

target_include_directories(generate_synthetic_events
        PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/../ml-detector/include
        ${CMAKE_CURRENT_SOURCE_DIR}/../common/include
        ${CMAKE_CURRENT_SOURCE_DIR}/../protobuf
        ${Protobuf_INCLUDE_DIRS}
        /usr/local/include
)

# ============================================================================
# 2. Synthetic Sniffer Injector (sniffer → ml-detector)
# ============================================================================

add_executable(synthetic_sniffer_injector
        synthetic_sniffer_injector.cpp
        ${PROTO_SOURCES}
)

target_include_directories(synthetic_sniffer_injector
        PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/../protobuf
        ${CMAKE_CURRENT_SOURCE_DIR}/../etcd-client/include
        ${CMAKE_CURRENT_SOURCE_DIR}/../crypto-transport/include
        ${CMAKE_CURRENT_SOURCE_DIR}/../libs/seed-client/include
        /usr/local/include
        ${Protobuf_INCLUDE_DIRS}
)

target_compile_options(synthetic_sniffer_injector
        PRIVATE
        -Wall
        -Wextra
        -Wpedantic
)

target_link_libraries(synthetic_sniffer_injector
        PRIVATE
        ${Protobuf_LIBRARIES}
        ${CRYPTO_TRANSPORT_LIB}
        ${ETCD_CLIENT_LIB}
        zmq
        Threads::Threads
        OpenSSL::SSL
        OpenSSL::Crypto
        ${CURL_LIBRARIES}
        ${LZ4_LIBRARIES}
        seed_client
)

# ============================================================================
# 3. Synthetic ML Output Injector (ml-detector → firewall)
# ============================================================================

add_executable(synthetic_ml_output_injector
        synthetic_ml_output_injector.cpp
        ${PROTO_SOURCES}
)

target_include_directories(synthetic_ml_output_injector
        PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/../protobuf
        ${CMAKE_CURRENT_SOURCE_DIR}/../etcd-client/include
        ${CMAKE_CURRENT_SOURCE_DIR}/../crypto-transport/include
        ${CMAKE_CURRENT_SOURCE_DIR}/../libs/seed-client/include
        /usr/local/include
        ${Protobuf_INCLUDE_DIRS}
)

target_compile_options(synthetic_ml_output_injector
        PRIVATE
        -Wall
        -Wextra
        -Wpedantic
)

target_link_libraries(synthetic_ml_output_injector
        PRIVATE
        ${Protobuf_LIBRARIES}
        ${CRYPTO_TRANSPORT_LIB}
        ${ETCD_CLIENT_LIB}
        zmq
        Threads::Threads
        OpenSSL::SSL
        OpenSSL::Crypto
        ${CURL_LIBRARIES}
        ${LZ4_LIBRARIES}
        seed_client
)

# ============================================================================
# COMPILER OPTIONS - Warnings Only
# ============================================================================
# ⚠️  Optimization flags (-O3, -g, -march, -fsanitize) are controlled by root Makefile
# ⚠️  Only warnings are set here

target_compile_options(generate_synthetic_events
        PRIVATE
        -Wall
        -Wextra
        -Wpedantic
)

# ============================================================================
# Link Libraries
# ============================================================================

target_link_libraries(generate_synthetic_events
        PRIVATE
        ${Protobuf_LIBRARIES}
        ${CRYPTO_TRANSPORT_LIB}
        ${LZ4_LIBRARIES}
        /usr/local/lib/libseed_client.so
        ${ETCD_CLIENT_LIB}
        spdlog::spdlog
        nlohmann_json::nlohmann_json
        Threads::Threads
        OpenSSL::SSL
        OpenSSL::Crypto
        ${CURL_LIBRARIES}
)

# ============================================================================
# Installation
# ============================================================================

install(TARGETS
        generate_synthetic_events
        synthetic_sniffer_injector
        synthetic_ml_output_injector
        RUNTIME DESTINATION ${CMAKE_CURRENT_SOURCE_DIR}/build
)

# ============================================================================
# Print Configuration
# ============================================================================

message(STATUS "==========================================================")
message(STATUS "ML Defender Tools Configuration")
message(STATUS "==========================================================")
message(STATUS "Build type: ${CMAKE_BUILD_TYPE}")
message(STATUS "C++ Compiler: ${CMAKE_CXX_COMPILER}")
message(STATUS "C++ Standard: ${CMAKE_CXX_STANDARD}")
message(STATUS "CXX Flags: ${CMAKE_CXX_FLAGS}")
message(STATUS "Protobuf: ${Protobuf_VERSION}")
message(STATUS "crypto-transport: ${CRYPTO_TRANSPORT_LIB}")
message(STATUS "etcd-client: ${ETCD_CLIENT_LIB}")
message(STATUS "")
message(STATUS "🎯 Single Source of Truth:")
message(STATUS "  Compiler Flags: Controlled by root Makefile via PROFILE")
message(STATUS "==========================================================")