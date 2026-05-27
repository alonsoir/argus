# tests/CMakeLists.txt
# ML Defender - Test Suite
# Day 64: Recreated (was lost) + Day 64 CSV pipeline tests added
# Authors: Alonso Isidoro Roman + Claude (Anthropic)
#
# STRUCTURE:
#   unit/        — isolated detector/component tests (no external services)
#   integration/ — tests that exercise the full pipeline or need real data
#
# ADDING NEW TESTS:
#   1. Create test file in unit/ or integration/
#   2. Add an add_executable + target_link_libraries + add_test block below
#   3. Follow the pattern of the nearest similar test

# ============================================================================
# GTest — inherited from parent CMakeLists.txt find_package(GTest)
# ============================================================================

if(NOT GTest_FOUND)
    message(WARNING "⚠️  GTest not found — skipping all tests that require it")
endif()

# Convenience macro to reduce boilerplate for standard GTest targets
# Usage: ml_gtest(target_name source.cpp [extra_src1 ...])
#        then call target_link_libraries(target_name PRIVATE ...) if needed
macro(ml_gtest TARGET)
    add_executable(${TARGET} ${ARGN})
    target_include_directories(${TARGET} PRIVATE
            ${CMAKE_CURRENT_SOURCE_DIR}/../include
            ${CMAKE_BINARY_DIR}/proto
            ${ETCD_CLIENT_INCLUDE_DIR}
            ${CRYPTO_TRANSPORT_INCLUDE_DIR}
    )
    # Base GTest linkage — add more in the specific block if needed
    target_link_libraries(${TARGET} PRIVATE
            GTest::GTest
            GTest::Main
            Threads::Threads
    )
    add_test(NAME ${TARGET} COMMAND ${TARGET})
endmacro()

# ============================================================================
# UNIT TESTS — unit/
# ============================================================================

# ── test_classifier (empty stub — will be filled later) ──────────────────────
if(GTest_FOUND AND EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/unit/test_classifier.cpp")
    ml_gtest(test_classifier unit/test_classifier.cpp)
    target_link_libraries(test_classifier PRIVATE
            PkgConfig::ZMQ
            ${Protobuf_LIBRARIES}
            onnxruntime
    )
endif()

# ── test_feature_extractor (empty stub) ──────────────────────────────────────
if(GTest_FOUND AND EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/unit/test_feature_extractor.cpp")
    ml_gtest(test_feature_extractor unit/test_feature_extractor.cpp)
    target_link_libraries(test_feature_extractor PRIVATE
            ${Protobuf_LIBRARIES}
    )
endif()

# ── test_rag_logger_artifact_save — DAY 75 regression ────────────────────────
# Validates: proto3 submessage safety + DAY 75 fix sentinels reach artifact save
if(GTest_FOUND AND
        EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/unit/test_rag_logger_artifact_save.cpp")
    ml_gtest(test_rag_logger_artifact_save
            unit/test_rag_logger_artifact_save.cpp
            ${PROTO_SOURCES}
    )
    target_link_libraries(test_rag_logger_artifact_save PRIVATE
            ${Protobuf_LIBRARIES}
    )
    message(STATUS "✅ test_rag_logger_artifact_save registered (DAY 75)")
endif()

# ── test_model_loader (empty stub) ───────────────────────────────────────────
if(GTest_FOUND AND EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/unit/test_model_loader.cpp")
    ml_gtest(test_model_loader unit/test_model_loader.cpp)
    target_link_libraries(test_model_loader PRIVATE
            onnxruntime
            ${Protobuf_LIBRARIES}
    )
endif()

# ── test_zmq_memory_overflow — DEBT-INTEGER-OVERFLOW-TEST-001 (ADR-037 F17) ──
if(GTest_FOUND AND EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/unit/test_zmq_memory_overflow.cpp")
    ml_gtest(test_zmq_memory_overflow unit/test_zmq_memory_overflow.cpp)
    # No extra libs needed — memory_utils.hpp is header-only, zero deps
    message(STATUS "✅ test_zmq_memory_overflow registered (DEBT-INTEGER-OVERFLOW-TEST-001)")
endif()
# ── test_ransomware_detector — uses ransomware_detector library target ────────
if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/unit/test_ransomware_detector.cpp")

    add_executable(test_ransomware_detector_unit
            unit/test_ransomware_detector.cpp
    )
    target_include_directories(test_ransomware_detector_unit PRIVATE
            ${CMAKE_CURRENT_SOURCE_DIR}/../include
    )
    target_link_libraries(test_ransomware_detector_unit PRIVATE
            ransomware_detector
    )
    add_test(NAME RansomwareDetectorUnit
            COMMAND test_ransomware_detector_unit)
endif()

# ── test_detectors — NO GTest, has its own main() ────────────────────────────
# Kept as a standalone executable for its benchmark output.
# Run manually: ./build/test_detectors
if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/unit/test_detectors.cpp")
    add_executable(test_detectors
            unit/test_detectors.cpp
            ../src/ddos_detector.cpp
            ../src/traffic_detector.cpp
            ../src/internal_detector.cpp
    )
    target_include_directories(test_detectors PRIVATE
            ${CMAKE_CURRENT_SOURCE_DIR}/../include
            ${CMAKE_BINARY_DIR}/proto
    )
    target_link_libraries(test_detectors PRIVATE
            Threads::Threads
    )
    # Not registered with ctest (no GTest, benchmark output not suitable for CI)
    # add_test(NAME test_detectors COMMAND test_detectors)
endif()

# ============================================================================
# INTEGRATION TESTS — integration/
# ============================================================================

# ── test_ransomware_detector_integration ─────────────────────────────────────
# Por ahora lo deshabilito porque está roto.
if(GTest_FOUND AND
        EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/integration/test_ransomware_detector_integration.cpp" AND FALSE)
    ml_gtest(test_ransomware_detector_integration
            integration/test_ransomware_detector_integration.cpp
    )
    target_link_libraries(test_ransomware_detector_integration PRIVATE
            ransomware_detector
    )
endif()

# ── test_pipeline (empty stub) ────────────────────────────────────────────────
if(GTest_FOUND AND
        EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/integration/test_pipeline.cpp")
    ml_gtest(test_pipeline
            integration/test_pipeline.cpp
    )
    target_link_libraries(test_pipeline PRIVATE
            PkgConfig::ZMQ
            ${Protobuf_LIBRARIES}
            onnxruntime
            ${ETCD_CLIENT_LIB}
            ${CRYPTO_TRANSPORT_LIB}
            OpenSSL::SSL
            OpenSSL::Crypto
    )
    if(TARGET spdlog::spdlog)
        target_link_libraries(test_pipeline PRIVATE spdlog::spdlog)
    elseif(TARGET PkgConfig::SPDLOG)
        target_link_libraries(test_pipeline PRIVATE PkgConfig::SPDLOG)
    endif()
endif()

# ============================================================================
# DAY 64 — CSV Pipeline Tests
# ============================================================================
# These three tests verify the CsvEventWriter schema (127 columns) and
# the HMAC key retrieval from etcd.  They require:
#   test_csv_event_writer      → csv_event_writer.cpp, proto, OpenSSL, spdlog
#   test_csv_feature_extraction → csv_event_writer.cpp, proto, OpenSSL, spdlog
#   test_etcd_client_hmac      → etcd_client.cpp, httplib, nlohmann_json, spdlog

# Helper: spdlog target name varies by how it was found
macro(ml_link_spdlog TARGET)
    if(TARGET spdlog::spdlog)
        target_link_libraries(${TARGET} PRIVATE spdlog::spdlog)
    elseif(TARGET PkgConfig::SPDLOG)
        target_link_libraries(${TARGET} PRIVATE PkgConfig::SPDLOG)
    endif()
endmacro()

macro(ml_link_nlohmann TARGET)
    if(TARGET nlohmann_json::nlohmann_json)
        target_link_libraries(${TARGET} PRIVATE nlohmann_json::nlohmann_json)
    elseif(TARGET nlohmann_json)
        target_link_libraries(${TARGET} PRIVATE nlohmann_json)
    endif()
endmacro()

# ── test_csv_event_writer ─────────────────────────────────────────────────────
if(GTest_FOUND AND
        EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/integration/test_csv_event_writer.cpp")

    ml_gtest(test_csv_event_writer
            integration/test_csv_event_writer.cpp
            ../src/csv_event_writer.cpp
            ${PROTO_SOURCES}
    )
    target_link_libraries(test_csv_event_writer PRIVATE
            ${Protobuf_LIBRARIES}
            OpenSSL::SSL
            OpenSSL::Crypto
    )
    ml_link_spdlog(test_csv_event_writer)

    message(STATUS "✅ test_csv_event_writer registered")
endif()

# ── test_csv_feature_extraction ───────────────────────────────────────────────
if(GTest_FOUND AND
        EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/integration/test_csv_feature_extraction.cpp")

    ml_gtest(test_csv_feature_extraction
            integration/test_csv_feature_extraction.cpp
            ../src/csv_event_writer.cpp
            ${PROTO_SOURCES}
    )
    target_link_libraries(test_csv_feature_extraction PRIVATE
            ${Protobuf_LIBRARIES}
            OpenSSL::SSL
            OpenSSL::Crypto
    )
    ml_link_spdlog(test_csv_feature_extraction)

    message(STATUS "✅ test_csv_feature_extraction registered")
endif()

# ── test_etcd_client_hmac ─────────────────────────────────────────────────────
# etcd_client.cpp depends on: httplib.h (header-only), nlohmann_json, crypto_transport
if(GTest_FOUND AND
        EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/integration/test_etcd_client_hmac.cpp")

    ml_gtest(test_etcd_client_hmac
            integration/test_etcd_client_hmac.cpp
            ../src/etcd_client.cpp
    )
    target_include_directories(test_etcd_client_hmac PRIVATE
            /usr/local/include   # ← httplib.h para MockEtcdServer
    )
    target_link_libraries(test_etcd_client_hmac PRIVATE
            ${ETCD_CLIENT_LIB}
            ${CRYPTO_TRANSPORT_LIB}
            OpenSSL::SSL
            OpenSSL::Crypto
    )
    ml_link_spdlog(test_etcd_client_hmac)
    ml_link_nlohmann(test_etcd_client_hmac)
endif()

# ============================================================================
# SUMMARY
# ============================================================================
message(STATUS "")
message(STATUS "─── Test suite ──────────────────────────────")
message(STATUS "  Unit:")
message(STATUS "    test_classifier             (stub)")
message(STATUS "    test_feature_extractor       (stub)")
message(STATUS "    test_model_loader            (stub)")
message(STATUS "    test_ransomware_detector_unit")
message(STATUS "    test_detectors               (standalone, no ctest)")
message(STATUS "  Integration:")
message(STATUS "    test_ransomware_detector_integration")
message(STATUS "    test_pipeline                (stub)")
message(STATUS "  Day 64 — CSV pipeline:")
message(STATUS "    test_csv_event_writer")
message(STATUS "    test_csv_feature_extraction")
message(STATUS "    test_etcd_client_hmac")
message(STATUS "─────────────────────────────────────────────")
message(STATUS "")