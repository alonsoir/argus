cmake_minimum_required(VERSION 3.16)
project(correlation_engine VERSION 1.0.0 LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# ── Dependencias ──────────────────────────────────────────────────────────────
find_package(PkgConfig REQUIRED)
pkg_check_modules(SPDLOG REQUIRED spdlog)

# ntp_utils — desde common/ (ADR-046 P0)
add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/../common
                 ${CMAKE_CURRENT_BINARY_DIR}/common)

# ── correlation-engine binary ─────────────────────────────────────────────────
add_executable(correlation-engine
        src/main.cpp
)
target_include_directories(correlation-engine PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/../common
        ${CMAKE_CURRENT_SOURCE_DIR}/../common/include
        ${SPDLOG_INCLUDE_DIRS}
)
target_link_libraries(correlation-engine PRIVATE
        ntp_utils
        ${SPDLOG_LIBRARIES}
)
target_compile_options(correlation-engine PRIVATE -Werror -Wall -Wextra)

# Resumen de compilación
message(STATUS "╔══════════════════════════════════════════════╗")
message(STATUS "║  correlation-engine — ADR-048 F2 (DAY 167)  ║")
message(STATUS "║  NTP gate: ADR-046 P0                        ║")
message(STATUS "║  community_id join key: pendiente ADR-048 F2 ║")
message(STATUS "╚══════════════════════════════════════════════╝")

# ── Tests ─────────────────────────────────────────────────────────────────────
option(BUILD_TESTS "Build tests" ON)
if(BUILD_TESTS)
    enable_testing()

    # NTP-1/2/3 reutiliza el test de common/ — no duplicar lógica
    add_executable(test_ntp_gate
            ${CMAKE_CURRENT_SOURCE_DIR}/../common/tests/test_ntp_health_check.cpp
            ${CMAKE_CURRENT_SOURCE_DIR}/../common/ntp_health_check.cpp
    )
    target_include_directories(test_ntp_gate PRIVATE
            ${CMAKE_CURRENT_SOURCE_DIR}/../common
    )
    target_link_libraries(test_ntp_gate PRIVATE
            ntp_utils
    )
    add_test(NAME test_ntp_gate COMMAND test_ntp_gate)
    set_tests_properties(test_ntp_gate PROPERTIES TIMEOUT 10)
endif()
