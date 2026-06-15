cmake_minimum_required(VERSION 3.16)
project(correlation_v1 VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# ─── Dependencias ────────────────────────────────────────────────────────────
# DELTA vs seed-client: la lib NO usa nlohmann_json. SÍ usa OpenSSL para el HMAC
# col 18 (contrato bronce, compartido por los 5 productores; no es transporte).
find_package(OpenSSL REQUIRED)
message(STATUS "Found OpenSSL: ${OPENSSL_VERSION}")

# ─── Biblioteca compartida ────────────────────────────────────────────────────
add_library(correlation_v1 SHARED
        src/correlation_v1.cpp
)

target_include_directories(correlation_v1
        PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
)

# OpenSSL::Crypto PUBLIC: los consumidores (ml-detector y, mañana, los adapters)
# heredan la dependencia del HMAC transitivamente.
target_link_libraries(correlation_v1
        PUBLIC OpenSSL::Crypto
)

# Hardening flags (mismo set que seed-client / crypto-transport).
# -Werror NO se hardcodea aquí: llega del Makefile raíz vía CMAKE_CXX_FLAGS.
target_compile_options(correlation_v1 PRIVATE
        -Wall -Wextra -Wpedantic
        -fstack-protector-strong
        -D_FORTIFY_SOURCE=2
)

set_target_properties(correlation_v1 PROPERTIES
        VERSION ${PROJECT_VERSION}
        SOVERSION 1
        POSITION_INDEPENDENT_CODE ON
)

# ─── Instalación ─────────────────────────────────────────────────────────────
include(GNUInstallDirs)

install(TARGETS correlation_v1
        LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
        ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
        RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
)

install(DIRECTORY include/correlation_v1
        DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}
)

# ─── Tests ───────────────────────────────────────────────────────────────────
enable_testing()

add_executable(test_correlation_v1
        tests/test_correlation_v1.cpp
)

target_link_libraries(test_correlation_v1
        PRIVATE correlation_v1
        PRIVATE OpenSSL::Crypto
)

target_include_directories(test_correlation_v1 PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/include
)

add_test(NAME correlation_v1_tests
        COMMAND test_correlation_v1
        WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}
)

# [DAY182] -UNDEBUG: assert() vivo en production (regla DAY 144).
# Reactiva assert() bajo -DNDEBUG en el test standalone, igual que seed-client.
if(TARGET test_correlation_v1)
    target_compile_options(test_correlation_v1 PRIVATE -UNDEBUG)
endif()