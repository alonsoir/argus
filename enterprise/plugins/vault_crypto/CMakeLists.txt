cmake_minimum_required(VERSION 3.16)
project(vault_crypto_plugin VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# ── libsodium ─────────────────────────────────────────────────────────────
find_library(SODIUM_LIB sodium PATHS /usr/local/lib /usr/lib NO_DEFAULT_PATH)
if(NOT SODIUM_LIB)
    message(FATAL_ERROR "libsodium no encontrado")
endif()
find_path(SODIUM_INCLUDE sodium.h PATHS /usr/local/include /usr/include NO_DEFAULT_PATH)

# ── libcurl ───────────────────────────────────────────────────────────────
find_package(CURL REQUIRED)

# ── shared library ────────────────────────────────────────────────────────
add_library(vault_provider SHARED vault_provider.cpp)

target_include_directories(vault_provider
    PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}
        ${CMAKE_SOURCE_DIR}/../../../common/include   # ICryptoProvider.hpp
        ${SODIUM_INCLUDE}
        ${CURL_INCLUDE_DIRS}
)

target_link_libraries(vault_provider
    PRIVATE
        ${SODIUM_LIB}
        ${CURL_LIBRARIES}
)

target_compile_options(vault_provider PRIVATE
    -Wall -Wextra -Wpedantic -Werror
    -fvisibility=hidden
)

set_target_properties(vault_provider PROPERTIES
    PREFIX          "lib"
    OUTPUT_NAME     "vault_provider"
    VERSION         ${PROJECT_VERSION}
    SOVERSION       0
    POSITION_INDEPENDENT_CODE ON
)

# ── install (produccion) ──────────────────────────────────────────────────
install(TARGETS vault_provider
    LIBRARY DESTINATION /usr/lib/argus/enterprise/plugins
)

# ── tests ─────────────────────────────────────────────────────────────────
option(BUILD_TESTS "Build tests" OFF)
if(BUILD_TESTS)
    enable_testing()
    add_subdirectory(tests)
endif()

message(STATUS "vault_crypto plugin — libsodium: ${SODIUM_LIB}")
message(STATUS "vault_crypto plugin — libcurl:   ${CURL_LIBRARIES}")
