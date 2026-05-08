cmake_minimum_required(VERSION 3.16)
project(etcd-server VERSION 1.0.0)

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
# ⚠️  DO NOT set -O, -g, -march, -fsanitize flags here
#
# The root Makefile controls all optimization and sanitizer flags via:
#   make PROFILE=production  → -O3 -march=native -DNDEBUG -flto
#   make PROFILE=debug       → -g -O0 -fno-omit-frame-pointer
#   make PROFILE=tsan        → -fsanitize=thread -g -O1
#   make PROFILE=asan        → -fsanitize=address -g -O1
# ============================================================================

message(STATUS "========================================")
message(STATUS "etcd-server Configuration")
message(STATUS "========================================")
message(STATUS "Build type: ${CMAKE_BUILD_TYPE}")
message(STATUS "C++ Standard: ${CMAKE_CXX_STANDARD}")
message(STATUS "CXX Flags (from Makefile): ${CMAKE_CXX_FLAGS}")

# ============================================================================
# DEPENDENCIES
# ============================================================================
find_package(PkgConfig REQUIRED)
find_package(Threads REQUIRED)

# ============================================================================
# OPENSSL (for HMAC-SHA256 in tests)
# ============================================================================
find_package(OpenSSL REQUIRED)
if(OPENSSL_FOUND)
    message(STATUS "✅ OpenSSL found - HMAC support enabled")
    message(STATUS "   Version: ${OPENSSL_VERSION}")
    message(STATUS "   Include: ${OPENSSL_INCLUDE_DIR}")
    message(STATUS "   Libraries: ${OPENSSL_LIBRARIES}")
else()
    message(FATAL_ERROR "OpenSSL not found - Install: sudo apt-get install libssl-dev")
endif()

# ============================================================================
# LIBSODIUM (for crypto_manager.cpp direct usage + random number generation)
# ============================================================================
pkg_check_modules(LIBSODIUM REQUIRED libsodium)
if(LIBSODIUM_FOUND)
    message(STATUS "✅ libsodium found - Using ChaCha20-Poly1305 + randombytes")
else()
    message(FATAL_ERROR "libsodium not found - Install: sudo apt-get install libsodium-dev")
endif()

# ============================================================================
# LZ4 (for compression_lz4.cpp)
# ============================================================================
pkg_check_modules(LZ4 REQUIRED liblz4)
if(NOT LZ4_FOUND)
    message(FATAL_ERROR "liblz4 not found. Install: sudo apt-get install liblz4-dev")
endif()
message(STATUS "✅ LZ4 found - Compression enabled")

# ============================================================================
# CRYPTO-TRANSPORT LIBRARY (Unified cryptography)
# ============================================================================
# crypto-transport provides: ChaCha20-Poly1305 + utilities
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
else()
    message(FATAL_ERROR "❌ crypto-transport not found
    Library: ${CRYPTO_TRANSPORT_LIB}
    Headers: ${CRYPTO_TRANSPORT_INCLUDE_DIR}

    Fix: Run 'make crypto-transport-build' from project root")
endif()

# ============================================================================
# SEED-CLIENT LIBRARY (ADR-013 PHASE 2 — DAY 98)
# ============================================================================
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
    message(STATUS "✅ Found seed-client library: ${SEED_CLIENT_LIB}")
    message(STATUS "✅ Found seed-client headers: ${SEED_CLIENT_INCLUDE_DIR}")
else()
    message(FATAL_ERROR "❌ seed-client not found
    Library: ${SEED_CLIENT_LIB}
    Headers: ${SEED_CLIENT_INCLUDE_DIR}

    Fix: Run 'make seed-client-build' from project root")
endif()

# ============================================================================
# INCLUDE DIRECTORIES
# ============================================================================
include_directories(
        ${CMAKE_CURRENT_SOURCE_DIR}/include
        ${CRYPTO_TRANSPORT_INCLUDE_DIR}
        ${LIBSODIUM_INCLUDE_DIRS}
        ${LZ4_INCLUDE_DIRS}
        ${OPENSSL_INCLUDE_DIR}
        /usr/local/include
)

# ============================================================================
# SOURCES (Day 53: Added secrets_manager.cpp)
# ============================================================================
set(SOURCES
        src/main.cpp
        src/etcd_server.cpp
        src/component_registry.cpp
        src/crypto_manager.cpp
        src/compression_lz4.cpp
        src/secrets_manager.cpp
)

# ============================================================================
# EXECUTABLE
# ============================================================================
add_executable(etcd-server ${SOURCES})

# ============================================================================
# COMPILER OPTIONS - Warnings Only
# ============================================================================
# ⚠️  Optimization flags (-O2, -O3, -g, -march, -fsanitize)
# ⚠️  are controlled by root Makefile
# ⚠️  Only warnings are set here

target_compile_options(etcd-server
        PRIVATE
        -Wall
        -Wextra
        -Wpedantic
)

# ============================================================================
# LINK LIBRARIES
# ============================================================================
target_link_libraries(etcd-server
        PRIVATE
        crypto_transport
        seed_client
        sodium
        lz4
        ${OPENSSL_LIBRARIES}
        fmt
)

# ============================================================================
# INCLUDE DIRECTORIES (target-specific)
# ============================================================================
target_include_directories(etcd-server
        PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/include
        ${CRYPTO_TRANSPORT_INCLUDE_DIR}
        ${SEED_CLIENT_INCLUDE_DIR}
        ${LIBSODIUM_INCLUDE_DIRS}
        ${LZ4_INCLUDE_DIRS}
        ${OPENSSL_INCLUDE_DIR}
)

# ============================================================================
# TESTS (Day 53: Added SecretsManager tests)
# ============================================================================
option(BUILD_TESTS "Build test executables" ON)

if(BUILD_TESTS)
    message(STATUS "========================================")
    message(STATUS "Building Tests")
    message(STATUS "========================================")

    # Test 1: SecretsManager Unit Tests
    # add_executable(test_secrets_manager
    #         tests/test_secrets_manager.cpp
    #         src/secrets_manager.cpp
    # )

    # target_include_directories(test_secrets_manager
    #         PRIVATE
    #         ${CMAKE_CURRENT_SOURCE_DIR}/include
    #         ${LIBSODIUM_INCLUDE_DIRS}
    #         ${OPENSSL_INCLUDE_DIR}
    # )

    # target_link_libraries(test_secrets_manager
    #         PRIVATE
    #         Threads::Threads
    #         ${LIBSODIUM_LIBRARIES}
    #         OpenSSL::SSL
    #         OpenSSL::Crypto
    # )

    # Test 2: HMAC Integration Tests
    add_executable(test_hmac_integration
            tests/test_hmac_integration.cpp
            src/secrets_manager.cpp
    )
    target_include_directories(test_hmac_integration
            PRIVATE
            ${CMAKE_CURRENT_SOURCE_DIR}/include
            ${LIBSODIUM_INCLUDE_DIRS}
            ${OPENSSL_INCLUDE_DIR}
    )
    target_link_libraries(test_hmac_integration
            PRIVATE
            Threads::Threads
            ${LIBSODIUM_LIBRARIES}
            OpenSSL::SSL
            OpenSSL::Crypto
            fmt
    )
    add_test(NAME test_hmac_integration COMMAND test_hmac_integration)

    # Grace period
    # add_executable(test_secrets_manager_grace_period
    #         tests/test_secrets_manager_grace_period.cpp
    #         src/secrets_manager.cpp
    # )

    # target_include_directories(test_secrets_manager_grace_period
    #         PRIVATE
    #         ${CMAKE_SOURCE_DIR}/include
    # )

    # target_link_libraries(test_secrets_manager_grace_period
    #         PRIVATE
    #         GTest::gtest
    #         GTest::gtest_main
    #         spdlog::spdlog
    #         OpenSSL::SSL
    #         OpenSSL::Crypto
    # )

    # Test: SecretsManager Basic (Day 55)
    enable_testing()
    add_executable(test_secrets_manager_simple
            tests/test_secrets_manager_simple.cpp
            src/secrets_manager.cpp
    )

    target_include_directories(test_secrets_manager_simple
            PRIVATE
            ${CMAKE_CURRENT_SOURCE_DIR}/include
            ${OPENSSL_INCLUDE_DIR}
    )

    # DEBT-COMPILER-WARNINGS-CLEANUP-001: assert() activo en tests independientemente del PROFILE
    target_compile_options(test_secrets_manager_simple PRIVATE -UNDEBUG)
    add_test(NAME test_secrets_manager_simple COMMAND test_secrets_manager_simple)
    target_link_libraries(test_secrets_manager_simple
            PRIVATE
            Threads::Threads
            OpenSSL::SSL
            OpenSSL::Crypto
            fmt
    )
    # target_include_directories(test_hmac_integration
    #         PRIVATE
    #         ${CMAKE_CURRENT_SOURCE_DIR}/include
    #         ${LIBSODIUM_INCLUDE_DIRS}
    #         ${OPENSSL_INCLUDE_DIR}
    # )

    # target_link_libraries(test_hmac_integration
    #         PRIVATE
    #         Threads::Threads
    #         ${LIBSODIUM_LIBRARIES}
    #         OpenSSL::SSL
    #         OpenSSL::Crypto
    # )
    # Add to test suite
    # add_test(NAME SecretsManagerGracePeriod COMMAND test_secrets_manager_grace_period)

    # ============================================================================
    # Notes:
    # ============================================================================
    #
    # This adds a new test executable for the grace period functionality.
    #
    # Dependencies:
    # - GTest (already in your project)
    # - spdlog (already in your project)
    # - OpenSSL (for RAND_bytes in key generation)
    # - nlohmann_json (header-only, already in your project)
    #
    # Make sure OpenSSL is found earlier in your CMakeLists.txt with:
    # find_package(OpenSSL REQUIRED)
    #
    # If you get linker errors about OpenSSL, add:
    # target_link_libraries(your_main_target PRIVATE OpenSSL::SSL OpenSSL::Crypto)
    message(STATUS "✅ Test executables configured:")
    message(STATUS "   - test_secrets_manager")
    message(STATUS "   - test_hmac_integration")
    message(STATUS "========================================")
endif()

# ============================================================================
# SUMMARY
# ============================================================================
message(STATUS "========================================")
message(STATUS "Build Configuration:")
message(STATUS "  C++ Standard: ${CMAKE_CXX_STANDARD}")
message(STATUS "  Build Type: ${CMAKE_BUILD_TYPE}")
message(STATUS "  CXX Flags: ${CMAKE_CXX_FLAGS}")
message(STATUS "========================================")
message(STATUS "Dependencies:")
message(STATUS "  crypto-transport: ${CRYPTO_TRANSPORT_LIB}")
message(STATUS "  libsodium: ${LIBSODIUM_LIBRARIES}")
message(STATUS "  LZ4: ${LZ4_LIBRARIES}")
message(STATUS "  OpenSSL: ${OPENSSL_LIBRARIES}")
message(STATUS "========================================")
message(STATUS "Sources:")
foreach(src ${SOURCES})
    message(STATUS "  - ${src}")
endforeach()
message(STATUS "========================================")
message(STATUS "🎯 Single Source of Truth:")
message(STATUS "  Compiler Flags: Controlled by root Makefile via PROFILE")
message(STATUS "========================================")