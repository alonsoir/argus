cmake_minimum_required(VERSION 3.16)
project(crypto_transport VERSION 1.0.0 LANGUAGES CXX)

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
# ⚠️  DO NOT set CMAKE_BUILD_TYPE, CMAKE_CXX_FLAGS_RELEASE, CMAKE_CXX_FLAGS_DEBUG here
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
# FIND DEPENDENCIES
# ============================================================================
find_package(PkgConfig REQUIRED)

# libsodium 1.0.19 — priorizar /usr/local sobre sistema (Bookworm tiene 1.0.18)
find_library(LIBSODIUM_LIBRARIES NAMES sodium
             HINTS /usr/local/lib
             NO_DEFAULT_PATH)
if(NOT LIBSODIUM_LIBRARIES)
    # fallback al sistema si no está en /usr/local
    find_library(LIBSODIUM_LIBRARIES NAMES sodium REQUIRED)
endif()
find_path(LIBSODIUM_INCLUDE_DIRS sodium.h
          HINTS /usr/local/include
          NO_DEFAULT_PATH)
if(NOT LIBSODIUM_INCLUDE_DIRS)
    find_path(LIBSODIUM_INCLUDE_DIRS sodium.h REQUIRED)
endif()
message(STATUS "libsodium lib:     ${LIBSODIUM_LIBRARIES}")
message(STATUS "libsodium include: ${LIBSODIUM_INCLUDE_DIRS}")

# LZ4 (compression)
pkg_check_modules(LZ4 REQUIRED liblz4)
if(NOT LZ4_FOUND)
    message(FATAL_ERROR "liblz4 not found. Install: sudo apt-get install liblz4-dev")
endif()

# libseed_client (trust chain — ADR-013)
find_library(LIBSEED_CLIENT_LIB NAMES seed_client HINTS /usr/local/lib REQUIRED)
find_path(LIBSEED_CLIENT_INC seed_client/seed_client.hpp HINTS /usr/local/include REQUIRED)
if(NOT LIBSEED_CLIENT_LIB OR NOT LIBSEED_CLIENT_INC)
    message(FATAL_ERROR "libseed_client not found. Build libs/seed-client first.")
endif()
message(STATUS "libseed_client: ${LIBSEED_CLIENT_LIB}")

# ============================================================================
# SOURCES
# ============================================================================
set(SOURCES
        src/crypto.cpp
        src/compression.cpp
        src/utils.cpp
        src/transport.cpp
)

# Public headers that will be installed
set(PUBLIC_HEADERS
        include/crypto_transport/crypto.hpp
        include/crypto_transport/compression.hpp
        include/crypto_transport/utils.hpp
        include/crypto_transport/crypto_manager.hpp
        include/crypto_transport/transport.hpp
        include/crypto_transport/contexts.hpp
)

# ============================================================================
# LIBRARY TARGET
# ============================================================================
add_library(crypto_transport SHARED ${SOURCES})

# Include directories
target_include_directories(crypto_transport
        PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
        PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/src
        ${LIBSODIUM_INCLUDE_DIRS}
        ${LZ4_INCLUDE_DIRS}
        ${LIBSEED_CLIENT_INC}
)

# ============================================================================
# COMPILER OPTIONS - Warnings Only
# ============================================================================
# ⚠️  Optimization flags (-O3, -g, -march, -fsanitize) are controlled by root Makefile
# ⚠️  Only warnings are set here

target_compile_options(crypto_transport
        PRIVATE
        -Wall
        -Wextra
        -Wpedantic
)

# ============================================================================
# Link Libraries
# ============================================================================

# Link libraries
target_link_libraries(crypto_transport
        PRIVATE
        ${LIBSODIUM_LIBRARIES}
        ${LZ4_LIBRARIES}
        ${LIBSEED_CLIENT_LIB}
)

# Library properties
set_target_properties(crypto_transport PROPERTIES
        VERSION ${PROJECT_VERSION}
        SOVERSION 1
        POSITION_INDEPENDENT_CODE ON
)

# ============================================================================
# INSTALLATION
# ============================================================================
install(TARGETS crypto_transport
        LIBRARY DESTINATION lib
        ARCHIVE DESTINATION lib
        RUNTIME DESTINATION bin
)

# Install headers individually to ensure crypto_manager.hpp is included
install(FILES ${PUBLIC_HEADERS}
        DESTINATION include/crypto_transport
)

# ============================================================================
# TESTS (optional)
# ============================================================================
option(BUILD_TESTS "Build tests" ON)

if(BUILD_TESTS)
    enable_testing()
    add_subdirectory(tests)

    message(STATUS "========================================")
    message(STATUS "crypto-transport Tests Configuration")
    message(STATUS "========================================")
    message(STATUS "Test framework: Google Test")
    message(STATUS "Tests: test_crypto, test_compression, test_integration")
    message(STATUS "========================================")
endif()

# ============================================================================
# CONFIGURATION SUMMARY
# ============================================================================
message(STATUS "========================================")
message(STATUS "crypto-transport Library Configuration")
message(STATUS "========================================")
message(STATUS "Build type: ${CMAKE_BUILD_TYPE}")
message(STATUS "C++ Standard: ${CMAKE_CXX_STANDARD}")
message(STATUS "CXX Flags: ${CMAKE_CXX_FLAGS}")
message(STATUS "libsodium: ${LIBSODIUM_VERSION}")
message(STATUS "LZ4: ${LZ4_VERSION}")
message(STATUS "========================================")
message(STATUS "Public Headers:")
foreach(header ${PUBLIC_HEADERS})
    message(STATUS "  - ${header}")
endforeach()
message(STATUS "========================================")
message(STATUS "Install destinations:")
message(STATUS "  Library: ${CMAKE_INSTALL_PREFIX}/lib")
message(STATUS "  Headers: ${CMAKE_INSTALL_PREFIX}/include/crypto_transport")
message(STATUS "")
message(STATUS "🎯 Single Source of Truth:")
message(STATUS "  Compiler Flags: Controlled by root Makefile via PROFILE")
message(STATUS "========================================")