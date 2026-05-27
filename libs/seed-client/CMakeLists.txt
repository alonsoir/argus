cmake_minimum_required(VERSION 3.16)
project(seed_client VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# ─── Dependencias ────────────────────────────────────────────────────────────
find_package(nlohmann_json 3.9 REQUIRED)

# ─── Biblioteca compartida ────────────────────────────────────────────────────
add_library(seed_client SHARED
        src/seed_client.cpp
)

target_include_directories(seed_client
        PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/../../contrib/safe-path/include>
)

target_link_libraries(seed_client
        PUBLIC nlohmann_json::nlohmann_json
)

# Hardening flags (mismo set que crypto-transport)
target_compile_options(seed_client PRIVATE
        -Wall -Wextra -Wpedantic
        -fstack-protector-strong
        -D_FORTIFY_SOURCE=2
)

set_target_properties(seed_client PROPERTIES
        VERSION ${PROJECT_VERSION}
        SOVERSION 1
        POSITION_INDEPENDENT_CODE ON
)

# ─── Instalación ─────────────────────────────────────────────────────────────
include(GNUInstallDirs)

install(TARGETS seed_client
        LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
        ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
        RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
)

install(DIRECTORY include/seed_client
        DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}
)

# ─── Tests ───────────────────────────────────────────────────────────────────
enable_testing()

add_executable(test_seed_client
        tests/test_seed_client.cpp
)

target_link_libraries(test_seed_client
        PRIVATE seed_client
        PRIVATE nlohmann_json::nlohmann_json
)

target_include_directories(test_seed_client PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/include
)

add_test(NAME seed_client_tests
        COMMAND test_seed_client
        WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}
)

# ─── TEST-PERMS-SEED (DEBT-SEED-PERM-001) ────────────────────────────────────
add_executable(test_perms_seed
        tests/test_perms_seed.cpp
)
target_link_libraries(test_perms_seed
        PRIVATE seed_client
        PRIVATE nlohmann_json::nlohmann_json
)
target_include_directories(test_perms_seed PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/include
)
add_test(NAME perms_seed_tests
        COMMAND test_perms_seed
        WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}
)

# ─── TEST-SEED-CLIENT-TRAVERSAL (DEBT-PRODUCTION-TESTS-REMAINING-001) ─────────
add_executable(test_seed_client_traversal
        tests/test_seed_client_traversal.cpp
)
target_link_libraries(test_seed_client_traversal
        PRIVATE seed_client
        PRIVATE nlohmann_json::nlohmann_json
)
target_include_directories(test_seed_client_traversal PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/include
        ${CMAKE_CURRENT_SOURCE_DIR}/../../contrib/safe-path/include
)
add_test(NAME seed_client_traversal_tests
        COMMAND test_seed_client_traversal
        WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}
)
