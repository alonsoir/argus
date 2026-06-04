cmake_minimum_required(VERSION 3.20)
project(correlation_engine VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
add_compile_options(-Wall -Wextra -Werror)

find_package(PkgConfig REQUIRED)
pkg_check_modules(LIBSODIUM REQUIRED libsodium)
message(STATUS "libsodium: ${LIBSODIUM_VERSION}")
find_package(OpenSSL REQUIRED)   # HMAC del reader (mismo OpenSSL que ml-detector/firewall)

# nlohmann_json: find_package -> fallback header-only vendoreado (patrón del proyecto)
find_package(nlohmann_json 3.11.0 QUIET)
if(NOT nlohmann_json_FOUND)
    find_path(NLOHMANN_JSON_INCLUDE_DIR nlohmann/json.hpp
            PATHS /usr/include /usr/local/include
            ${CMAKE_CURRENT_SOURCE_DIR}/../third_party/json/include)
    if(NLOHMANN_JSON_INCLUDE_DIR)
        message(STATUS "nlohmann/json (header-only): ${NLOHMANN_JSON_INCLUDE_DIR}")
        add_library(nlohmann_json INTERFACE)
        target_include_directories(nlohmann_json INTERFACE ${NLOHMANN_JSON_INCLUDE_DIR})
        add_library(nlohmann_json::nlohmann_json ALIAS nlohmann_json)
    else()
        message(FATAL_ERROR "nlohmann/json no encontrado. Vendorear en ../third_party/json/include o instalar nlohmann-json3-dev")
    endif()
else()
    message(STATUS "nlohmann/json: ${nlohmann_json_VERSION}")
endif()

# ── librería del engine: flow_uid (header-only) + correlation_reader ──
add_library(correlation_engine STATIC src/correlation_reader.cpp)
target_include_directories(correlation_engine PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_include_directories(correlation_engine PUBLIC ${LIBSODIUM_INCLUDE_DIRS})
target_link_libraries(correlation_engine PUBLIC ${LIBSODIUM_LIBRARIES} OpenSSL::Crypto)

# ── tests (GoogleTest) ──
enable_testing()
find_package(GTest REQUIRED)

add_executable(test_flow_uid tests/test_flow_uid.cpp)
target_link_libraries(test_flow_uid PRIVATE correlation_engine nlohmann_json::nlohmann_json GTest::gtest_main)
target_compile_definitions(test_flow_uid PRIVATE
        VECTORS_PATH="${CMAKE_CURRENT_SOURCE_DIR}/tests/vectors/correlation_vectors.json")
add_test(NAME test_flow_uid COMMAND test_flow_uid)

add_executable(test_correlation_reader tests/test_correlation_reader.cpp)
target_link_libraries(test_correlation_reader PRIVATE correlation_engine GTest::gtest_main)
add_test(NAME test_correlation_reader COMMAND test_correlation_reader)