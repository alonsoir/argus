cmake_minimum_required(VERSION 3.20)
project(cpp_evolutionary_sniffer VERSION 3.1.0 LANGUAGES C CXX)

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
# ⚠️  DO NOT set CMAKE_BUILD_TYPE, -O flags, -march, -fsanitize here
# ⚠️  DO NOT set CMAKE_INTERPROCEDURAL_OPTIMIZATION here
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
# Threading Support
# ============================================================================
set(CMAKE_THREAD_PREFER_PTHREAD TRUE)
set(THREADS_PREFER_PTHREAD_FLAG TRUE)

# ============================================================================
# DEPENDENCIES DISCOVERY
# ============================================================================

# Required programs
find_program(CLANG clang REQUIRED)
find_program(LLVM_STRIP llvm-strip REQUIRED)


# ADR-029 Variant B — capture backend selection
option(USE_LIBPCAP "Use libpcap instead of eBPF/XDP (Variant B)" OFF)
if(NOT USE_LIBPCAP)
  find_program(BPFTOOL bpftool REQUIRED)
endif()

# Required packages
find_package(PkgConfig REQUIRED)
find_package(Protobuf REQUIRED)
find_package(Threads REQUIRED)

# Core eBPF and networking dependencies (REQUIRED)
if(USE_LIBPCAP)
  message(STATUS "ADR-029 Variant B: libpcap backend — skipping libbpf")
  find_package(PkgConfig REQUIRED)
  pkg_check_modules(LIBPCAP REQUIRED libpcap)
else()
  pkg_check_modules(LIBBPF REQUIRED libbpf>=0.8)
endif()
pkg_check_modules(ZMQ REQUIRED libzmq>=4.3)
pkg_check_modules(JSONCPP REQUIRED jsoncpp>=1.9)

# Compression libraries (MANDATORY for security sniffer)
pkg_check_modules(LZ4 REQUIRED liblz4>=1.8)
pkg_check_modules(ZSTD REQUIRED libzstd>=1.4)

# Optional compression
pkg_check_modules(SNAPPY libsnappy)

# Optional libraries for advanced features
find_library(CURL_LIBRARY curl)
find_library(NUMA_LIBRARY numa)

# etcd-client library (for encrypted config management)
message(STATUS "🔍 Buscando etcd-client library...")
set(ETCD_CLIENT_LIB /vagrant/etcd-client/build/libetcd_client.so)
set(ETCD_CLIENT_INCLUDE_DIR /vagrant/etcd-client/include)

if(EXISTS ${ETCD_CLIENT_LIB})
    message(STATUS "✅ Found etcd-client library: ${ETCD_CLIENT_LIB}")
else()
    message(FATAL_ERROR "❌ etcd-client library not found at ${ETCD_CLIENT_LIB}")
endif()

# ============================================================================
# CRYPTO-TRANSPORT ECOSYSTEM
# ============================================================================
# crypto-transport library (unified crypto ecosystem)
message(STATUS "🔍 Buscando crypto-transport library...")
find_library(CRYPTO_TRANSPORT_LIB
        NAMES crypto_transport
        PATHS /usr/local/lib /usr/lib
)
find_path(CRYPTO_TRANSPORT_INCLUDE
        NAMES crypto_transport/crypto_manager.hpp
        PATHS /usr/local/include /usr/include
)

if(CRYPTO_TRANSPORT_LIB)
    message(STATUS "✅ Found crypto-transport library: ${CRYPTO_TRANSPORT_LIB}")
    message(STATUS "✅ Found crypto-transport includes: ${CRYPTO_TRANSPORT_INCLUDE}")
else()
    message(FATAL_ERROR "❌ crypto-transport library not found - install from /vagrant/crypto-transport")
endif()

# libsodium (base crypto library)
find_library(SODIUM_LIB sodium REQUIRED)
if(SODIUM_LIB)
    message(STATUS "✅ Found libsodium: ${SODIUM_LIB}")
else()
    message(FATAL_ERROR "❌ libsodium not found - install: sudo apt install libsodium-dev")
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
else()
    message(FATAL_ERROR "❌ seed-client not found. Run make seed-client-build from project root")
endif()
# ============================================================================
# ADR-012 PHASE 1b — plugin-loader (DAY 100)
# ============================================================================
find_library(PLUGIN_LOADER_LIB
        NAMES plugin_loader
        PATHS /usr/local/lib
        NO_DEFAULT_PATH
)
find_path(PLUGIN_LOADER_INCLUDE_DIR
        NAMES plugin_loader/plugin_loader.hpp
        PATHS /usr/local/include
        NO_DEFAULT_PATH
)
if(PLUGIN_LOADER_LIB AND PLUGIN_LOADER_INCLUDE_DIR)
    message(STATUS "✅ Found plugin-loader: ${PLUGIN_LOADER_LIB}")
else()
    message(WARNING "⚠️  plugin-loader not found — plugins disabled (non-fatal)")
    set(PLUGIN_LOADER_LIB "")
endif()

# ============================================================================
# CONFIGURATION VALIDATION
# ============================================================================

# Validate critical dependencies
if(NOT LZ4_FOUND)
    message(FATAL_ERROR "❌ LZ4 es obligatorio para el sniffer - ejecuta: sudo apt install liblz4-dev")
endif()

if(NOT ZSTD_FOUND)
    message(FATAL_ERROR "❌ Zstd es obligatorio para el sniffer - ejecuta: sudo apt install libzstd-dev")
endif()

# ============================================================================
# INCLUDE DIRECTORIES
# ============================================================================
include_directories(${CMAKE_SOURCE_DIR}/include)
include_directories(${CMAKE_SOURCE_DIR}/src)
include_directories(${CMAKE_BINARY_DIR}/proto)
include_directories(${CMAKE_BINARY_DIR})

# ML Defender Phase 1 - Embedded C++20 Detectors
set(ML_DEFENDER_DIR "${CMAKE_SOURCE_DIR}/../ml-detector")
include_directories(${ML_DEFENDER_DIR}/include)

# Common headers (reason codes, shared types)
include_directories(/vagrant/common/include)

# Core dependencies includes
if(USE_LIBPCAP)
  include_directories(${LIBPCAP_INCLUDE_DIRS})
  add_definitions(-DUSE_LIBPCAP)
else()
  include_directories(${LIBBPF_INCLUDE_DIRS})
endif()
include_directories(${ZMQ_INCLUDE_DIRS})
include_directories(${JSONCPP_INCLUDE_DIRS})

# Compression includes (always present since they're mandatory)
include_directories(${LZ4_INCLUDE_DIRS})
include_directories(${ZSTD_INCLUDE_DIRS})

if(SNAPPY_FOUND)
    include_directories(${SNAPPY_INCLUDE_DIRS})
endif()

# etcd-client includes
if(ETCD_CLIENT_LIB)
    include_directories(${ETCD_CLIENT_INCLUDE_DIR})
endif()

# crypto-transport includes
if(CRYPTO_TRANSPORT_LIB)
    include_directories(${CRYPTO_TRANSPORT_INCLUDE})
endif()

# ============================================================================
# eBPF PROGRAM COMPILATION — Variant A only (USE_LIBPCAP=OFF)
# ============================================================================

if(NOT USE_LIBPCAP)
  set(BPF_SOURCE ${CMAKE_SOURCE_DIR}/src/kernel/sniffer.bpf.c)
  set(BPF_OBJECT ${CMAKE_BINARY_DIR}/sniffer.bpf.o)
  
  add_custom_command(
          OUTPUT ${BPF_OBJECT}
          COMMAND ${CLANG}
          -O2 -target bpf -D__TARGET_ARCH_x86 -g
          -I${LIBBPF_INCLUDE_DIRS}  # Variant A only
          -I/usr/include/x86_64-linux-gnu
          -I/usr/include/bpf
          -c ${BPF_SOURCE}
          -o ${BPF_OBJECT}
          DEPENDS ${BPF_SOURCE}
          COMMENT "Compiling eBPF program with BTF support"
  )
else()
  set(BPF_OBJECT "")  # Variant B: no eBPF object
endif()

if(NOT USE_LIBPCAP)
  add_custom_target(bpf_program DEPENDS ${BPF_OBJECT})
else()
  add_custom_target(bpf_program)  # empty target en Variant B
endif()

# ============================================================================
# PROTOBUF - USAR ARCHIVOS UNIFICADOS
# ============================================================================

# Verificar que los archivos protobuf unificados existen
if(NOT EXISTS "${CMAKE_BINARY_DIR}/proto/network_security.pb.cc")
    message(FATAL_ERROR "❌ Protobuf unificado no encontrado. Ejecuta: cd /vagrant/protobuf && ./generate.sh")
else()
    message(STATUS "✅ Protobuf unificado encontrado: ${CMAKE_BINARY_DIR}/proto/network_security.pb.cc")
endif()

set(PROTO_SOURCES ${CMAKE_BINARY_DIR}/proto/network_security.pb.cc)
set(PROTO_HEADERS ${CMAKE_BINARY_DIR}/proto/network_security.pb.h)

# ============================================================================
# ML DEFENDER SOURCES
# ============================================================================
# ML Defender Phase 1 sources
set(ML_DEFENDER_SOURCES
        src/userspace/ml_defender_features.cpp
        ../ml-detector/src/ddos_detector.cpp
        ../ml-detector/src/ransomware_detector.cpp
        ../ml-detector/src/traffic_detector.cpp
        ../ml-detector/src/internal_detector.cpp
)

# ============================================================================
# SOURCE FILES CONFIGURATION
# ============================================================================

set(SNIFFER_SOURCES
        src/userspace/main.cpp
        src/userspace/config_manager.cpp
        src/userspace/config_types.cpp
        src/userspace/ebpf_loader.cpp
        src/userspace/ring_consumer.cpp
        src/userspace/zmq_pool_manager.cpp
        src/userspace/thread_manager.cpp
        src/userspace/compression_handler.cpp
        src/userspace/etcd_client.cpp
        src/userspace/flow_manager.cpp
        src/userspace/feature_extractor.cpp
        src/userspace/time_window_manager.cpp
        src/userspace/feature_logger.cpp
        src/userspace/dual_nic_manager.cpp
        # ====================================================================
        # RANSOMWARE DETECTION SYSTEM - Phase 1A (3 Critical Features)
        # ====================================================================
        src/userspace/flow_tracker.cpp
        src/userspace/dns_analyzer.cpp
        src/userspace/ip_whitelist.cpp
        src/userspace/time_window_aggregator.cpp
        src/userspace/ransomware_feature_extractor.cpp
        src/userspace/ransomware_feature_processor.cpp
        src/userspace/fast_detector.cpp
        src/userspace/payload_analyzer.cpp
        # ====================================================================

        src/userspace/bpf_map_manager.cpp
        ${PROTO_SOURCES}
        ${ML_DEFENDER_SOURCES}
)

# ShardedFlowManager (Day 43)
set(SHARDED_FLOW_SOURCES
        src/flow/sharded_flow_manager.cpp
)

# Feature-specific sources
set(SNIFFER_FEATURE_SOURCES "")

# Compression handler (always included - mandatory)
list(APPEND SNIFFER_FEATURE_SOURCES src/userspace/compression_handler.cpp)

# ZMQ Pool manager (always included for performance)
list(APPEND SNIFFER_FEATURE_SOURCES src/userspace/zmq_pool_manager.cpp)

# etcd client (optional)
if(CURL_LIBRARY)
    list(APPEND SNIFFER_FEATURE_SOURCES src/userspace/etcd_client.cpp)
endif()

# ============================================================================
# EXECUTABLE TARGET
# ============================================================================

if(NOT USE_LIBPCAP)  # Variant A only — Variant B usa sniffer-libpcap
add_executable(sniffer
        ${SNIFFER_SOURCES}
        ${SHARDED_FLOW_SOURCES})

add_dependencies(sniffer bpf_program)

target_include_directories(sniffer PRIVATE
        # Core directories
        ${CMAKE_SOURCE_DIR}/include
        ${CMAKE_SOURCE_DIR}/include/flow
        ${CMAKE_SOURCE_DIR}/src
        ${CMAKE_BINARY_DIR}/proto
        ${CMAKE_BINARY_DIR}

        # ML Defender Phase 1 - Embedded C++20 Detectors
        ${ML_DEFENDER_DIR}/include

        # Common headers (reason codes, shared types)
        /vagrant/common/include

        # Core dependencies includes
        $<$<NOT:$<BOOL:${USE_LIBPCAP}>>:${LIBBPF_INCLUDE_DIRS}>
        ${ZMQ_INCLUDE_DIRS}
        ${JSONCPP_INCLUDE_DIRS}
        ${Protobuf_INCLUDE_DIRS}

        # Compression includes (mandatory)
        ${LZ4_INCLUDE_DIRS}
        ${ZSTD_INCLUDE_DIRS}
)

# Optional includes
if(SNAPPY_FOUND)
    target_include_directories(sniffer PRIVATE ${SNAPPY_INCLUDE_DIRS})
endif()

if(ETCD_CLIENT_LIB)
    target_include_directories(sniffer PRIVATE ${ETCD_CLIENT_INCLUDE_DIR})
endif()

if(CRYPTO_TRANSPORT_LIB)
    target_include_directories(sniffer PRIVATE ${CRYPTO_TRANSPORT_INCLUDE})
endif()

if(SEED_CLIENT_LIB)
    target_include_directories(sniffer PRIVATE ${SEED_CLIENT_INCLUDE_DIR})
endif()

if(PLUGIN_LOADER_LIB)
    target_include_directories(sniffer PRIVATE ${PLUGIN_LOADER_INCLUDE_DIR})
endif()

# ============================================================================
# COMPILER OPTIONS - Warnings Only
# ============================================================================
# ⚠️  Optimization flags (-O3, -march, -mavx2, -ffast-math, LTO)
# ⚠️  are controlled by root Makefile
# ⚠️  Only warnings are set here

target_compile_options(sniffer PRIVATE
        -Wall
        -Wextra
        -Wpedantic
)

# ============================================================================
# LIBRARIES CONFIGURATION
# ============================================================================

# Core libraries (always linked)
set(SNIFFER_CORE_LIBRARIES
        $<IF:$<BOOL:${USE_LIBPCAP}>,${LIBPCAP_LIBRARIES},${LIBBPF_LIBRARIES}>
        ${ZMQ_LIBRARIES}
        ${JSONCPP_LIBRARIES}
        ${Protobuf_LIBRARIES}
        ${LZ4_LIBRARIES}
        ${ZSTD_LIBRARIES}
        Threads::Threads
        elf
        z
)

# Optional libraries
set(SNIFFER_OPTIONAL_LIBRARIES "")

if(SNAPPY_FOUND)
    list(APPEND SNIFFER_OPTIONAL_LIBRARIES ${SNAPPY_LIBRARIES})
endif()

if(CURL_LIBRARY)
    list(APPEND SNIFFER_OPTIONAL_LIBRARIES ${CURL_LIBRARY})
endif()

if(NUMA_LIBRARY)
    list(APPEND SNIFFER_OPTIONAL_LIBRARIES ${NUMA_LIBRARY})
endif()

if(ETCD_CLIENT_LIB)
    list(APPEND SNIFFER_OPTIONAL_LIBRARIES ${ETCD_CLIENT_LIB})
endif()

# crypto-transport + libsodium + seed-client
if(CRYPTO_TRANSPORT_LIB)
    list(APPEND SNIFFER_OPTIONAL_LIBRARIES ${CRYPTO_TRANSPORT_LIB})
    list(APPEND SNIFFER_OPTIONAL_LIBRARIES ${SODIUM_LIB})
endif()

if(SEED_CLIENT_LIB)
    list(APPEND SNIFFER_OPTIONAL_LIBRARIES ${SEED_CLIENT_LIB})
endif()

# ADR-012 PHASE 1b — plugin-loader
if(PLUGIN_LOADER_LIB)
    list(APPEND SNIFFER_OPTIONAL_LIBRARIES ${PLUGIN_LOADER_LIB})
    target_compile_definitions(sniffer PRIVATE PLUGIN_LOADER_ENABLED)
endif()

# Link all libraries
target_link_libraries(sniffer ${SNIFFER_CORE_LIBRARIES} ${SNIFFER_OPTIONAL_LIBRARIES})

# ============================================================================
# LINK DIRECTORIES
# ============================================================================

set(SNIFFER_LINK_DIRECTORIES
        $<IF:$<BOOL:${USE_LIBPCAP}>,${LIBPCAP_LIBRARY_DIRS},${LIBBPF_LIBRARY_DIRS}>
        ${ZMQ_LIBRARY_DIRS}
        ${JSONCPP_LIBRARY_DIRS}
        ${LZ4_LIBRARY_DIRS}
        ${ZSTD_LIBRARY_DIRS}
)

if(SNAPPY_FOUND)
    list(APPEND SNIFFER_LINK_DIRECTORIES ${SNAPPY_LIBRARY_DIRS})
endif()

target_link_directories(sniffer PRIVATE ${SNIFFER_LINK_DIRECTORIES})

# ============================================================================
# COMPILE OPTIONS
# ============================================================================

set(SNIFFER_COMPILE_OPTIONS
        $<$<NOT:$<BOOL:${USE_LIBPCAP}>>:${LIBBPF_CFLAGS_OTHER}>
        ${ZMQ_CFLAGS_OTHER}
        ${JSONCPP_CFLAGS_OTHER}
        ${LZ4_CFLAGS_OTHER}
        ${ZSTD_CFLAGS_OTHER}
)

if(SNAPPY_FOUND)
    list(APPEND SNIFFER_COMPILE_OPTIONS ${SNAPPY_CFLAGS_OTHER})
endif()

target_compile_options(sniffer PRIVATE ${SNIFFER_COMPILE_OPTIONS})

# ============================================================================
# COMPILE DEFINITIONS
# ============================================================================

# Core feature definitions
target_compile_definitions(sniffer PRIVATE
        COMPRESSION_SUPPORT
        HAVE_LZ4
        HAVE_ZSTD
)

# Optional feature definitions
if(SNAPPY_FOUND)
    target_compile_definitions(sniffer PRIVATE HAVE_SNAPPY)
endif()

if(CURL_LIBRARY)
    target_compile_definitions(sniffer PRIVATE ETCD_SUPPORT)
endif()

if(NUMA_LIBRARY)
    target_compile_definitions(sniffer PRIVATE NUMA_SUPPORT)
endif()

# ============================================================================
# DIRECTORY STRUCTURE SETUP
# ============================================================================

# Create necessary directories
file(MAKE_DIRECTORY ${CMAKE_BINARY_DIR}/config)
file(MAKE_DIRECTORY ${CMAKE_BINARY_DIR}/config/features)
file(MAKE_DIRECTORY ${CMAKE_BINARY_DIR}/logs)

# Copy configuration files
configure_file(
        ${CMAKE_SOURCE_DIR}/config/sniffer.json
        ${CMAKE_BINARY_DIR}/config/sniffer.json
        COPYONLY
)

# Create feature group placeholder files
set(FEATURE_GROUPS ddos_83 ransomware_83 rf_23 internal_4)
foreach(GROUP ${FEATURE_GROUPS})
    file(WRITE ${CMAKE_BINARY_DIR}/config/features/${GROUP}_features.json "[]")
endforeach()

# ============================================================================
# INSTALL RULES
# ============================================================================

install(TARGETS sniffer DESTINATION bin)
endif()  # NOT USE_LIBPCAP — Variant A target

# ============================================================================
# ADR-029 Variant B — sniffer-libpcap (libpcap, sin eBPF/XDP)
# Target completamente independiente — cero #ifdef en código existente
# DEBT-VARIANT-B-PCAP-IMPL-001: stub compilable, poll loop pendiente
# DAY 137 — 2026-04-30
# ============================================================================
if(USE_LIBPCAP)
  find_package(PkgConfig REQUIRED)
  pkg_check_modules(LIBPCAP REQUIRED libpcap)

  add_executable(sniffer-libpcap
    ${CMAKE_SOURCE_DIR}/src/userspace/main_libpcap.cpp
    ${CMAKE_SOURCE_DIR}/src/userspace/pcap_backend.cpp
    ${CMAKE_BINARY_DIR}/proto/network_security.pb.cc
  )

  target_include_directories(sniffer-libpcap PRIVATE
    ${CMAKE_SOURCE_DIR}/include
    ${LIBPCAP_INCLUDE_DIRS}
    ${CMAKE_BINARY_DIR}/proto
    /usr/local/include
  )

  target_compile_definitions(sniffer-libpcap PRIVATE USE_LIBPCAP)

  target_link_libraries(sniffer-libpcap PRIVATE
    ${LIBPCAP_LIBRARIES}
    lz4
    zmq
    protobuf
    crypto_transport
    seed_client
    etcd_client
    ${CMAKE_DL_LIBS}
  )

  message(STATUS "ADR-029 Variant B: sniffer-libpcap target configured")
endif()

install(FILES ${BPF_OBJECT} DESTINATION lib/sniffer)
install(FILES ${CMAKE_BINARY_DIR}/config/sniffer.json DESTINATION etc/sniffer)

# ============================================================================
# BUILD SUMMARY
# ============================================================================

message(STATUS "")
message(STATUS "=== ⚡ Enhanced Sniffer Configuration ===")
message(STATUS "📋 Build Info:")
message(STATUS "   Type: ${CMAKE_BUILD_TYPE}")
message(STATUS "   C++ standard: ${CMAKE_CXX_STANDARD}")
message(STATUS "   Compiler: ${CMAKE_CXX_COMPILER_ID} ${CMAKE_CXX_COMPILER_VERSION}")
message(STATUS "   CXX Flags: ${CMAKE_CXX_FLAGS}")

message(STATUS "")
message(STATUS "🔧 Core Dependencies:")
if(USE_LIBPCAP)
  message(STATUS "   libpcap: ${LIBPCAP_VERSION} (Variant B)")
else()
  message(STATUS "   libbpf: ${LIBBPF_VERSION} (Variant A)")
endif()
message(STATUS "   ZeroMQ: ${ZMQ_VERSION}")
message(STATUS "   jsoncpp: ${JSONCPP_VERSION}")
message(STATUS "   Protobuf: ${Protobuf_VERSION}")

message(STATUS "")
message(STATUS "🗜️ Compression Support (MANDATORY):")
message(STATUS "   ✅ LZ4: ${LZ4_VERSION} (required)")
message(STATUS "   ✅ Zstandard: ${ZSTD_VERSION} (required)")
if(SNAPPY_FOUND)
    message(STATUS "   ✅ Snappy: available (optional)")
else()
    message(STATUS "   ⚪ Snappy: not available (optional)")
endif()

message(STATUS "")
message(STATUS "🚀 Optional Features:")
if(CURL_LIBRARY)
    message(STATUS "   ✅ etcd client: enabled")
else()
    message(STATUS "   ⚪ etcd client: disabled (libcurl not found)")
endif()

if(NUMA_LIBRARY)
    message(STATUS "   ✅ NUMA optimization: enabled")
else()
    message(STATUS "   ⚪ NUMA optimization: disabled (libnuma not found)")
endif()

message(STATUS "")
message(STATUS "📦 Build Artifacts:")
message(STATUS "   Binary: ${CMAKE_BINARY_DIR}/sniffer")
message(STATUS "   eBPF program: ${BPF_OBJECT}")
message(STATUS "   Configuration: ${CMAKE_BINARY_DIR}/config/sniffer.json")

message(STATUS "")
message(STATUS "🎯 Sniffer Capabilities:")
message(STATUS "   ✅ Multi-threading support")
message(STATUS "   ✅ eBPF/XDP high-performance packet capture")
message(STATUS "   ✅ Mandatory LZ4/Zstd compression")
message(STATUS "   ✅ Protobuf serialization")
message(STATUS "   ✅ ZeroMQ communication")
if(ETCD_CLIENT_LIB)
    message(STATUS "   ✅ etcd-client library: enabled")
else()
    message(STATUS "   ⚪ etcd-client library: disabled")
endif()
if(CRYPTO_TRANSPORT_LIB)
    message(STATUS "   ✅ crypto-transport library: enabled")
    message(STATUS "   ✅ libsodium: enabled")
else()
    message(STATUS "   ⚪ crypto-transport library: disabled")
endif()
if(PLUGIN_LOADER_LIB)
    message(STATUS "   ✅ plugin-loader: enabled (ADR-012 PHASE 1b)")
else()
    message(STATUS "   ⚪ plugin-loader: disabled")
endif()
message(STATUS "   🔐 Encryption ready (via etcd tokens)")
message(STATUS "")
message(STATUS "🎯 Single Source of Truth:")
message(STATUS "   Compiler Flags: Controlled by root Makefile via PROFILE")
message(STATUS "========================================")
message(STATUS "")

# ============================================================================
# UNIT TESTS
# ============================================================================
enable_testing()


add_executable(test_payload_analyzer
        tests/test_payload_analyzer.cpp
        src/userspace/payload_analyzer.cpp
)

target_include_directories(test_payload_analyzer PRIVATE
        ${CMAKE_SOURCE_DIR}/include
)

target_link_libraries(test_payload_analyzer
        Threads::Threads
)

message(STATUS "🧪 Unit Test: test_payload_analyzer configured")

# ============================================================================
# SHARDED FLOW MANAGER FULL CONTRACT TEST - Day 46 (ISSUE-003 Validation)
# ============================================================================

add_executable(test_sharded_flow_full_contract
        tests/test_sharded_flow_full_contract.cpp

        # ShardedFlowManager components
        src/flow/sharded_flow_manager.cpp
        src/userspace/flow_manager.cpp
        src/userspace/time_window_manager.cpp
        src/userspace/time_window_aggregator.cpp

        src/userspace/flow_tracker.cpp
        src/userspace/dns_analyzer.cpp
        src/userspace/ip_whitelist.cpp
)

target_include_directories(test_sharded_flow_full_contract PRIVATE
        ${CMAKE_SOURCE_DIR}/include
        ${CMAKE_SOURCE_DIR}/include/flow
        ${CMAKE_SOURCE_DIR}/src
)

target_link_libraries(test_sharded_flow_full_contract
        Threads::Threads
        gtest
        gtest_main
)

message(STATUS "🧪 Unit Test: test_sharded_flow_full_contract configured (Day 46 - ISSUE-003)")

# ============================================================================
# RING CONSUMER PROTOBUF PIPELINE TEST - Day 46 (40 features validation)
# ============================================================================

add_executable(test_ring_consumer_protobuf
        tests/test_ring_consumer_protobuf.cpp

        # ShardedFlowManager + ML Defender extractor
        src/flow/sharded_flow_manager.cpp
        src/userspace/flow_manager.cpp
        src/userspace/time_window_manager.cpp
        src/userspace/time_window_aggregator.cpp
        src/userspace/ml_defender_features.cpp

        src/userspace/flow_tracker.cpp
        src/userspace/dns_analyzer.cpp
        src/userspace/ip_whitelist.cpp

        # Protobuf
        ${PROTO_SOURCES}
)

target_include_directories(test_ring_consumer_protobuf PRIVATE
        ${CMAKE_SOURCE_DIR}/include
        ${CMAKE_SOURCE_DIR}/include/flow
        ${CMAKE_SOURCE_DIR}/src
        ${CMAKE_BINARY_DIR}/proto
        ${ML_DEFENDER_DIR}/include
)

target_link_libraries(test_ring_consumer_protobuf
        Threads::Threads
        ${Protobuf_LIBRARIES}
        gtest
        gtest_main
)

message(STATUS "🧪 Unit Test: test_ring_consumer_protobuf configured (Day 46 - 40 features)")

# ============================================================================
# PROTO3 EMBEDDED SERIALIZATION TEST — DAY 75 regression
# Validates: all-zero float submessage trap + sentinel fix for send_ransomware_features
# ============================================================================
add_executable(test_proto3_embedded_serialization
        tests/test_proto3_embedded_serialization.cpp
        ${PROTO_SOURCES}
)
target_include_directories(test_proto3_embedded_serialization PRIVATE
        ${CMAKE_SOURCE_DIR}/include
        ${CMAKE_BINARY_DIR}/proto
)
target_link_libraries(test_proto3_embedded_serialization
        Threads::Threads
        ${Protobuf_LIBRARIES}
        gtest
        gtest_main
)
message(STATUS "🧪 Unit Test: test_proto3_embedded_serialization configured (DAY 75 regression)")

# ============================================================================
# SMB SCAN FEATURES TEST — DAY 92 (SYN-1, SYN-2)
# Validates: rst_ratio + syn_ack_ratio extractor + sentinel for zero SYN
# ============================================================================
add_executable(test_smb_scan_features
        tests/test_smb_scan_features.cpp
        ${PROTO_SOURCES}
)
target_include_directories(test_smb_scan_features PRIVATE
        ${CMAKE_SOURCE_DIR}/include
        ${CMAKE_BINARY_DIR}/proto
)
target_link_libraries(test_smb_scan_features
        Threads::Threads
        ${Protobuf_LIBRARIES}
        gtest
        gtest_main
)
add_test(NAME test_smb_scan_features COMMAND test_smb_scan_features)
message(STATUS "🧪 Unit Test: test_smb_scan_features configured (DAY 92 - SYN-1, SYN-2)")

# ============================================================================
# SHARDED FLOW MANAGER MULTITHREAD TEST - Day 46 (Concurrency validation)
# ============================================================================

add_executable(test_sharded_flow_multithread
        tests/test_sharded_flow_multithread.cpp

        # ShardedFlowManager + ML Defender extractor
        src/flow/sharded_flow_manager.cpp
        src/userspace/flow_manager.cpp
        src/userspace/time_window_manager.cpp
        src/userspace/time_window_aggregator.cpp
        src/userspace/ml_defender_features.cpp

        src/userspace/flow_tracker.cpp
        src/userspace/dns_analyzer.cpp
        src/userspace/ip_whitelist.cpp

        # Protobuf
        ${PROTO_SOURCES}
)

target_include_directories(test_sharded_flow_multithread PRIVATE
        ${CMAKE_SOURCE_DIR}/include
        ${CMAKE_SOURCE_DIR}/include/flow
        ${CMAKE_SOURCE_DIR}/src
        ${CMAKE_BINARY_DIR}/proto
        ${ML_DEFENDER_DIR}/include
)

target_link_libraries(test_sharded_flow_multithread
        Threads::Threads
        ${Protobuf_LIBRARIES}
        gtest
        gtest_main
)

message(STATUS "🧪 Unit Test: test_sharded_flow_multithread configured (Day 46 - Concurrency)")

# ============================================================================
# ADR-029 VARIANT B — PcapBackend Test Suite (DAY 138)
# 8 tests: unit, integration, stress, regression
# ============================================================================

# Fuente proto compartida para tests que usan NetworkSecurityEvent
set(PCAP_PROTO_SRC ${CMAKE_BINARY_DIR}/proto/network_security.pb.cc)

# --- Unit: lifecycle ---
add_executable(test_pcap_backend_lifecycle
    tests/test_pcap_backend_lifecycle.cpp
    src/userspace/pcap_backend.cpp
)
target_include_directories(test_pcap_backend_lifecycle PRIVATE
    ${CMAKE_SOURCE_DIR}/include
    ${CMAKE_BINARY_DIR}/proto
)
pkg_check_modules(LIBPCAP REQUIRED libpcap)
target_link_libraries(test_pcap_backend_lifecycle PRIVATE
    ${LIBPCAP_LIBRARIES} gtest gtest_main
)
add_test(NAME test_pcap_backend_lifecycle COMMAND test_pcap_backend_lifecycle)
message(STATUS "🧪 Variant B Test: test_pcap_backend_lifecycle configured")

# --- Unit: poll con handle nulo ---
add_executable(test_pcap_backend_poll_null
    tests/test_pcap_backend_poll_null.cpp
    src/userspace/pcap_backend.cpp
)
target_include_directories(test_pcap_backend_poll_null PRIVATE
    ${CMAKE_SOURCE_DIR}/include
    ${CMAKE_BINARY_DIR}/proto
)
target_link_libraries(test_pcap_backend_poll_null PRIVATE
    ${LIBPCAP_LIBRARIES} gtest gtest_main
)
add_test(NAME test_pcap_backend_poll_null COMMAND test_pcap_backend_poll_null)
message(STATUS "🧪 Variant B Test: test_pcap_backend_poll_null configured")

# --- Unit: callback ---
add_executable(test_pcap_backend_callback
    tests/test_pcap_backend_callback.cpp
    src/userspace/pcap_backend.cpp
)
target_include_directories(test_pcap_backend_callback PRIVATE
    ${CMAKE_SOURCE_DIR}/include
    ${CMAKE_BINARY_DIR}/proto
)
target_link_libraries(test_pcap_backend_callback PRIVATE
    ${LIBPCAP_LIBRARIES} gtest gtest_main
)
add_test(NAME test_pcap_backend_callback COMMAND test_pcap_backend_callback)
message(STATUS "🧪 Variant B Test: test_pcap_backend_callback configured")

# --- Unit: error handling ---
add_executable(test_pcap_backend_error
    tests/test_pcap_backend_error.cpp
    src/userspace/pcap_backend.cpp
)
target_include_directories(test_pcap_backend_error PRIVATE
    ${CMAKE_SOURCE_DIR}/include
    ${CMAKE_BINARY_DIR}/proto
)
target_link_libraries(test_pcap_backend_error PRIVATE
    ${LIBPCAP_LIBRARIES} gtest gtest_main
)
add_test(NAME test_pcap_backend_error COMMAND test_pcap_backend_error)
message(STATUS "🧪 Variant B Test: test_pcap_backend_error configured")

# --- Integration: proto parse TCP ---
add_executable(test_pcap_proto_parse_tcp
    tests/test_pcap_proto_parse_tcp.cpp
    ${PCAP_PROTO_SRC}
)
target_include_directories(test_pcap_proto_parse_tcp PRIVATE
    ${CMAKE_SOURCE_DIR}/include
    ${CMAKE_BINARY_DIR}/proto
    /usr/local/include
)
target_link_libraries(test_pcap_proto_parse_tcp PRIVATE
    protobuf gtest gtest_main
)
add_test(NAME test_pcap_proto_parse_tcp COMMAND test_pcap_proto_parse_tcp)
message(STATUS "🧪 Variant B Test: test_pcap_proto_parse_tcp configured")

# --- Integration: proto parse UDP ---
add_executable(test_pcap_proto_parse_udp
    tests/test_pcap_proto_parse_udp.cpp
    ${PCAP_PROTO_SRC}
)
target_include_directories(test_pcap_proto_parse_udp PRIVATE
    ${CMAKE_SOURCE_DIR}/include
    ${CMAKE_BINARY_DIR}/proto
    /usr/local/include
)
target_link_libraries(test_pcap_proto_parse_udp PRIVATE
    protobuf gtest gtest_main
)
add_test(NAME test_pcap_proto_parse_udp COMMAND test_pcap_proto_parse_udp)
message(STATUS "🧪 Variant B Test: test_pcap_proto_parse_udp configured")

# --- Stress: N callbacks, count exacto ---
add_executable(test_pcap_backend_stress
    tests/test_pcap_backend_stress.cpp
    src/userspace/pcap_backend.cpp
)
target_include_directories(test_pcap_backend_stress PRIVATE
    ${CMAKE_SOURCE_DIR}/include
    ${CMAKE_BINARY_DIR}/proto
)
target_link_libraries(test_pcap_backend_stress PRIVATE
    ${LIBPCAP_LIBRARIES} gtest gtest_main Threads::Threads
)
add_test(NAME test_pcap_backend_stress COMMAND test_pcap_backend_stress)
message(STATUS "🧪 Variant B Test: test_pcap_backend_stress configured")

# --- Regression: estado limpio tras ciclos ---
add_executable(test_pcap_backend_regression
    tests/test_pcap_backend_regression.cpp
    src/userspace/pcap_backend.cpp
)
target_include_directories(test_pcap_backend_regression PRIVATE
    ${CMAKE_SOURCE_DIR}/include
    ${CMAKE_BINARY_DIR}/proto
)
target_link_libraries(test_pcap_backend_regression PRIVATE
    ${LIBPCAP_LIBRARIES} gtest gtest_main
)
add_test(NAME test_pcap_backend_regression COMMAND test_pcap_backend_regression)
message(STATUS "🧪 Variant B Test: test_pcap_backend_regression configured")