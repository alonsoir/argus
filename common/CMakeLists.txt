cmake_minimum_required(VERSION 3.16)
project(vault_client VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# ── Dependencias ──────────────────────────────────────────────────────────────
find_package(PkgConfig REQUIRED)
pkg_check_modules(LIBSODIUM REQUIRED libsodium)
find_package(CURL REQUIRED)

# ── Librería ──────────────────────────────────────────────────────────────────
add_library(vault_client SHARED
    vault_client.cpp
)

target_include_directories(vault_client
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}>
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
    PRIVATE
        ${LIBSODIUM_INCLUDE_DIRS}
        ${CURL_INCLUDE_DIRS}
)

target_link_libraries(vault_client
    PUBLIC
        ${LIBSODIUM_LIBRARIES}
        ${CURL_LIBRARIES}
)

set_target_properties(vault_client PROPERTIES
    VERSION   ${PROJECT_VERSION}
    SOVERSION 1
)

# ── Instalación ───────────────────────────────────────────────────────────────
install(TARGETS vault_client
    LIBRARY DESTINATION lib
    ARCHIVE DESTINATION lib
)
install(FILES
    vault_client.h
    include/reason_codes.hpp
    include/sentinel.hpp
    DESTINATION include/vault_client
)

# ── Tests ─────────────────────────────────────────────────────────────────────
option(BUILD_TESTS "Build tests" ON)
if(BUILD_TESTS)
    enable_testing()
    add_executable(test_vault_client
        tests/test_vault_client.cpp
    )
    target_include_directories(test_vault_client PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}
        ${LIBSODIUM_INCLUDE_DIRS}
        ${CURL_INCLUDE_DIRS}
    )
    target_link_libraries(test_vault_client PRIVATE
        vault_client
    )
    add_test(NAME test_vault_client COMMAND test_vault_client)
endif()
