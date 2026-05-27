cmake_minimum_required(VERSION 3.16)
project(common-rag-ingester VERSION 1.0.0 LANGUAGES CXX)

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
# ⚠️  DO NOT set CMAKE_CXX_FLAGS_RELEASE, CMAKE_CXX_FLAGS_DEBUG here
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
# FAISS Dependency
# ============================================================================

# Find FAISS manually (no pkg-config available)
find_path(FAISS_INCLUDE_DIR
        NAMES faiss/IndexFlat.h
        PATHS /usr/local/include /usr/include
        DOC "FAISS include directory"
)

find_library(FAISS_LIBRARY
        NAMES faiss
        PATHS /usr/local/lib /usr/lib /usr/lib/x86_64-linux-gnu
        DOC "FAISS library"
)

if(NOT FAISS_INCLUDE_DIR OR NOT FAISS_LIBRARY)
    message(FATAL_ERROR "FAISS not found. Please install FAISS library.")
endif()

message(STATUS "Found FAISS: ${FAISS_LIBRARY}")
message(STATUS "FAISS include: ${FAISS_INCLUDE_DIR}")

# ============================================================================
# Library: common-rag-ingester
# ============================================================================

add_library(common-rag-ingester SHARED
        src/dimensionality_reducer.cpp
)

target_include_directories(common-rag-ingester
        PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
        PRIVATE
        ${FAISS_INCLUDE_DIR}
)

target_link_libraries(common-rag-ingester
        PUBLIC
        ${FAISS_LIBRARY}
        pthread
)

# ============================================================================
# COMPILER OPTIONS - Warnings Only
# ============================================================================
# ⚠️  Optimization flags (-O3, -g, -march, -fsanitize) are controlled by root Makefile
# ⚠️  Only warnings are set here

target_compile_options(common-rag-ingester PRIVATE
        -Wall
        -Wextra
        -Wpedantic
)

# ============================================================================
# Library Properties
# ============================================================================

set_target_properties(common-rag-ingester PROPERTIES
        VERSION ${PROJECT_VERSION}
        SOVERSION 1
        PUBLIC_HEADER include/dimensionality_reducer.hpp
)

# ============================================================================
# Installation Rules
# ============================================================================

include(GNUInstallDirs)

install(TARGETS common-rag-ingester
        EXPORT common-rag-ingester-targets
        LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
        ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
        RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
        PUBLIC_HEADER DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/ml_defender/rag
)

# Export targets
install(EXPORT common-rag-ingester-targets
        FILE common-rag-ingester-targets.cmake
        NAMESPACE ml_defender::
        DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/common-rag-ingester
)

# Create config file
include(CMakePackageConfigHelpers)
configure_package_config_file(
        ${CMAKE_CURRENT_SOURCE_DIR}/cmake/common-rag-ingester-config.cmake.in
        ${CMAKE_CURRENT_BINARY_DIR}/common-rag-ingester-config.cmake
        INSTALL_DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/common-rag-ingester
)

write_basic_package_version_file(
        ${CMAKE_CURRENT_BINARY_DIR}/common-rag-ingester-config-version.cmake
        VERSION ${PROJECT_VERSION}
        COMPATIBILITY SameMajorVersion
)

install(FILES
        ${CMAKE_CURRENT_BINARY_DIR}/common-rag-ingester-config.cmake
        ${CMAKE_CURRENT_BINARY_DIR}/common-rag-ingester-config-version.cmake
        DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/common-rag-ingester
)

# ============================================================================
# Build Summary
# ============================================================================

message(STATUS "")
message(STATUS "=== common-rag-ingester Configuration ===")
message(STATUS "Version: ${PROJECT_VERSION}")
message(STATUS "C++ Standard: ${CMAKE_CXX_STANDARD}")
message(STATUS "Build Type: ${CMAKE_BUILD_TYPE}")
message(STATUS "CXX Flags: ${CMAKE_CXX_FLAGS}")
message(STATUS "FAISS Include: ${FAISS_INCLUDE_DIR}")
message(STATUS "FAISS Library: ${FAISS_LIBRARY}")
message(STATUS "Install Prefix: ${CMAKE_INSTALL_PREFIX}")
message(STATUS "")
message(STATUS "🎯 Single Source of Truth:")
message(STATUS "  Compiler Flags: Controlled by root Makefile via PROFILE")
message(STATUS "========================================")
message(STATUS "")