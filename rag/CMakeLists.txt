cmake_minimum_required(VERSION 3.20)
project(rag-security-system VERSION 1.0.0 LANGUAGES CXX)

# ============================================================================
# CONFIGURACIÓN BÁSICA
# ============================================================================
set(CMAKE_CXX_STANDARD 20)  # ← Changed to C++20 for FAISS tests
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE "Debug")
endif()

message(STATUS "Build type: ${CMAKE_BUILD_TYPE}")

# ============================================================================
# CONFIGURACIÓN DE RUTAS
# ============================================================================
set(CMAKE_INCLUDE_CURRENT_DIR ON)
set(THIRD_PARTY_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../third_party")

# ============================================================================
# LLAMA.CPP - CONFIGURACIÓN
# ============================================================================
set(LLAMA_CPP_DIR "${THIRD_PARTY_DIR}/llama.cpp")
set(LLAMA_BUILD_DIR "${LLAMA_CPP_DIR}/build")

if(EXISTS "${LLAMA_CPP_DIR}/CMakeLists.txt")
    message(STATUS "Found llama.cpp: ${LLAMA_CPP_DIR}")

    if(EXISTS "${LLAMA_BUILD_DIR}/bin/libllama.so")
        set(LLAMA_LIB_PATH "${LLAMA_BUILD_DIR}/bin/libllama.so")
        set(HAVE_LLAMA_CPP TRUE)
        message(STATUS "✅ Found llama shared library: ${LLAMA_LIB_PATH}")
    else()
        set(HAVE_LLAMA_CPP FALSE)
        message(WARNING "❌ llama shared library not found")
    endif()

    set(LLAMA_INCLUDE_DIRS
            ${LLAMA_CPP_DIR}/include
            ${LLAMA_CPP_DIR}/ggml/include
            ${LLAMA_CPP_DIR}
            ${LLAMA_CPP_DIR}/src
            ${LLAMA_CPP_DIR}/common
    )
else()
    message(WARNING "llama.cpp not found at: ${LLAMA_CPP_DIR}")
    set(HAVE_LLAMA_CPP FALSE)
endif()

# ============================================================================
# DEPENDENCIAS EXTERNAS - BUSCAR EN SISTEMA
# ============================================================================
message(STATUS "🔍 Buscando dependencias del sistema...")

# 1. HTTPLIB (header-only)
find_path(HTTPLIB_INCLUDE_DIR httplib.h
        PATHS /usr/include /usr/local/include
        REQUIRED
)

# 2. NLOHMANN JSON (header-only)
find_path(JSON_INCLUDE_DIR nlohmann/json.hpp
        PATHS /usr/include /usr/local/include
        REQUIRED
)

# 3. Threads
find_package(Threads REQUIRED)
find_package(SQLite3 REQUIRED)
# ============================================================================
# FAISS - CONFIGURACIÓN (Phase 2A)
# ============================================================================
message(STATUS "🔍 Buscando FAISS library...")

find_library(FAISS_LIB
        NAMES faiss
        PATHS /usr/local/lib /usr/lib
)

find_path(FAISS_INCLUDE_DIR
        NAMES faiss/IndexFlat.h
        PATHS /usr/local/include /usr/include
)

if(FAISS_LIB AND FAISS_INCLUDE_DIR)
    set(HAVE_FAISS TRUE)
    message(STATUS "✅ Found FAISS library: ${FAISS_LIB}")
    message(STATUS "✅ Found FAISS headers: ${FAISS_INCLUDE_DIR}")
else()
    set(HAVE_FAISS FALSE)
    message(WARNING "❌ FAISS not found - Phase 2A features disabled")
endif()

# BLAS (required by FAISS)
if(HAVE_FAISS)
    find_package(BLAS REQUIRED)
    message(STATUS "✅ Found BLAS: ${BLAS_LIBRARIES}")
endif()

# ============================================================================
# ONNX Runtime - CONFIGURACIÓN (Phase 2A)
# ============================================================================
message(STATUS "🔍 Buscando ONNX Runtime...")

find_library(ONNX_LIB
        NAMES onnxruntime
        PATHS /usr/local/lib /usr/lib
)

find_path(ONNX_INCLUDE_DIR
        NAMES onnxruntime_cxx_api.h
        PATHS /usr/local/include /usr/include
)

if(ONNX_LIB AND ONNX_INCLUDE_DIR)
    set(HAVE_ONNX TRUE)
    message(STATUS "✅ Found ONNX Runtime: ${ONNX_LIB}")
    message(STATUS "✅ Found ONNX headers: ${ONNX_INCLUDE_DIR}")
else()
    set(HAVE_ONNX FALSE)
    message(WARNING "❌ ONNX Runtime not found - Phase 2A features disabled")
endif()

# ============================================================================
# ETCD-CLIENT LIBRARY
# ============================================================================
message(STATUS "🔍 Buscando etcd-client library...")

find_library(ETCD_CLIENT_LIB
        NAMES etcd_client
        PATHS /vagrant/etcd-client/build
        REQUIRED
)

if(ETCD_CLIENT_LIB)
    message(STATUS "✅ Found etcd-client library: ${ETCD_CLIENT_LIB}")
    set(ETCD_CLIENT_INCLUDE_DIR /vagrant/etcd-client/include)
else()
    message(FATAL_ERROR "❌ etcd-client library not found")
endif()

# ============================================================================
# ARCHIVOS FUENTE - RAG SECURITY PRINCIPAL
# ============================================================================
set(SOURCES
        src/main.cpp
        src/etcd_client.cpp
        src/config_manager.cpp
        src/whitelist_manager.cpp
        src/rag_command_manager.cpp
        src/base_validator.cpp
        src/rag_validator.cpp
        src/llama_integration_real.cpp
        # NUEVOS: Embedders (Phase 2A)
        src/embedders/simple_embedder.cpp
        src/embedders/embedder_factory.cpp
        src/metadata_reader.cpp
)

# ============================================================================
# EJECUTABLE PRINCIPAL - RAG SECURITY
# ============================================================================
# Suppress deprecated-declarations for llama.cpp external API (llama_new_context_with_model)
# llama.cpp API change: use llama_init_from_model — tracked as future upgrade
set_source_files_properties(src/llama_integration_real.cpp
    PROPERTIES COMPILE_OPTIONS "-Wno-deprecated-declarations")

add_executable(rag-security ${SOURCES})

# ============================================================================
# CONFIGURACIÓN DE INCLUSIONES - RAG SECURITY
# ============================================================================
target_include_directories(rag-security PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/include
        ${HTTPLIB_INCLUDE_DIR}
        ${JSON_INCLUDE_DIR}
        ${ETCD_CLIENT_INCLUDE_DIR}
        # NUEVO: Para embedders
        ${CMAKE_CURRENT_SOURCE_DIR}/include/embedders
        ${CMAKE_CURRENT_SOURCE_DIR}/include/common
)

# ============================================================================
# LINKING - RAG SECURITY
# ============================================================================
target_link_libraries(rag-security PRIVATE
        Threads::Threads
        ${ETCD_CLIENT_LIB}
        SQLite::SQLite3)

if(HAVE_LLAMA_CPP AND LLAMA_LIB_PATH AND LLAMA_INCLUDE_DIRS)
    target_link_libraries(rag-security PRIVATE "${LLAMA_LIB_PATH}")
    target_include_directories(rag-security PRIVATE ${LLAMA_INCLUDE_DIRS})
    target_compile_definitions(rag-security PRIVATE HAVE_LLAMA_CPP)
    message(STATUS "✅ llama.cpp integration enabled")
else()
    message(STATUS "❌ llama.cpp not available - using simulation mode")
    target_compile_definitions(rag-security PRIVATE LLAMA_SIMULATION_MODE)
endif()

# NUEVO: Link FAISS si está disponible
if(HAVE_FAISS)
    target_link_libraries(rag-security PRIVATE
            ${FAISS_LIB}
            ${BLAS_LIBRARIES}
    )
    target_include_directories(rag-security PRIVATE ${FAISS_INCLUDE_DIR})
    message(STATUS "✅ FAISS linked to rag-security")
endif()

#===----------------------------------------------------------------------===//
# ADR-012 PHASE 1b — Plugin Loader (DAY 102)
#===----------------------------------------------------------------------===//
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
    message(STATUS "plugin-loader: ${PLUGIN_LOADER_LIB}")
    target_include_directories(rag-security PRIVATE ${PLUGIN_LOADER_INCLUDE_DIR})
    target_link_libraries(rag-security PRIVATE ${PLUGIN_LOADER_LIB} dl)
    target_compile_definitions(rag-security PRIVATE PLUGIN_LOADER_ENABLED)
else()
    message(WARNING "plugin-loader not found — PLUGIN_LOADER_ENABLED disabled")
endif()

# ============================================================================
# CONFIGURACIÓN DE COMPILACIÓN - RAG SECURITY
# ============================================================================
target_compile_options(rag-security PRIVATE
        -Wall
        -Wextra
)

if(CMAKE_BUILD_TYPE STREQUAL "Debug")
    target_compile_options(rag-security PRIVATE -g -O0)
else()
    target_compile_options(rag-security PRIVATE -O2)
endif()

# ============================================================================
# TESTS - PHASE 2A (FAISS + ONNX Runtime)
# ============================================================================
if(HAVE_FAISS)
    message(STATUS "🧪 Configurando tests FAISS...")

    # Test FAISS Basic
    add_executable(test_faiss_basic
            tests/test_faiss_basic.cpp
    )

    target_include_directories(test_faiss_basic PRIVATE
            ${FAISS_INCLUDE_DIR}
    )

    target_link_libraries(test_faiss_basic PRIVATE
            ${FAISS_LIB}
            ${BLAS_LIBRARIES}
    )

    target_compile_options(test_faiss_basic PRIVATE
            -Wall
            -Wextra
    )

    message(STATUS "✅ test_faiss_basic configured")
    add_executable(test_embedder
            tests/test_embedder.cpp
            src/embedders/simple_embedder.cpp
            src/embedders/embedder_factory.cpp
    )

    target_include_directories(test_embedder PRIVATE
            ${CMAKE_CURRENT_SOURCE_DIR}/include
            ${CMAKE_CURRENT_SOURCE_DIR}/include/embedders
            ${CMAKE_CURRENT_SOURCE_DIR}/include/common
    )

    target_link_libraries(test_embedder PRIVATE
            Threads::Threads
    )

    message(STATUS "✅ test_embedder configured")
endif()

# ONNX Runtime test
if(HAVE_ONNX)
    add_executable(test_onnx_basic tests/test_onnx_basic.cpp)
    target_include_directories(test_onnx_basic PRIVATE ${ONNX_INCLUDE_DIR})
    target_link_libraries(test_onnx_basic PRIVATE ${ONNX_LIB})
    # DEBT-COMPILER-WARNINGS-CLEANUP-001: assert() activo en tests independientemente del PROFILE
    target_compile_options(test_onnx_basic PRIVATE -UNDEBUG)

    message(STATUS "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    message(STATUS "✅ test_onnx_basic configured")
    message(STATUS "   ONNX include: ${ONNX_INCLUDE_DIR}")
    message(STATUS "   ONNX library: ${ONNX_LIB}")
    message(STATUS "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
else()
    message(STATUS "⚠️  test_onnx_basic skipped (ONNX Runtime not found)")
endif()

# ============================================================================
# VERIFICACIÓN FINAL
# ============================================================================
message(STATUS "")
message(STATUS "╔════════════════════════════════════════════════════════════╗")
message(STATUS "║  RAG Security System - Build Configuration                ║")
message(STATUS "╚════════════════════════════════════════════════════════════╝")
message(STATUS "")
message(STATUS "📦 Core Dependencies:")
message(STATUS "   - httplib: ${HTTPLIB_INCLUDE_DIR}")
message(STATUS "   - nlohmann/json: ${JSON_INCLUDE_DIR}")
message(STATUS "   - llama.cpp: ${HAVE_LLAMA_CPP}")
message(STATUS "   - etcd-client: ${ETCD_CLIENT_LIB}")
message(STATUS "   - threads: OK")
message(STATUS "")
message(STATUS "🔬 Phase 2A Dependencies:")
message(STATUS "   - FAISS: ${HAVE_FAISS}")
if(HAVE_FAISS)
    message(STATUS "     • Library: ${FAISS_LIB}")
    message(STATUS "     • Include: ${FAISS_INCLUDE_DIR}")
    message(STATUS "     • BLAS: ${BLAS_LIBRARIES}")
endif()
message(STATUS "   - ONNX Runtime: ${HAVE_ONNX}")
if(HAVE_ONNX)
    message(STATUS "     • Library: ${ONNX_LIB}")
    message(STATUS "     • Include: ${ONNX_INCLUDE_DIR}")
endif()
message(STATUS "")
message(STATUS "🎯 Targets:")
message(STATUS "   - rag-security (main executable)")
if(HAVE_FAISS)
    message(STATUS "   - test_faiss_basic (FAISS integration test)")
endif()
if(HAVE_ONNX)
    message(STATUS "   - test_onnx_basic (planned)")
endif()
message(STATUS "")
message(STATUS "═══════════════════════════════════════════════════════════")