cmake_minimum_required(VERSION 3.20)
project(safe_path VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Header-only library
add_library(safe_path INTERFACE)
target_include_directories(safe_path INTERFACE
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    $<INSTALL_INTERFACE:include>
)

# Tests
option(SAFE_PATH_BUILD_TESTS "Build safe_path tests" ON)

if(SAFE_PATH_BUILD_TESTS)
    find_package(GTest REQUIRED)

    add_executable(test_safe_path tests/test_safe_path.cpp)
    target_link_libraries(test_safe_path
        PRIVATE
            safe_path
            GTest::gtest
            GTest::gtest_main
    )
    target_compile_options(test_safe_path PRIVATE -Wall -Wextra -Wpedantic)

    include(GoogleTest)
    gtest_discover_tests(test_safe_path)
endif()

# ─── test_safe_path_config — DEBT-DEV-PROD-SYMLINK-001 ──────────────────────
if(GTest_FOUND AND EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/tests/test_safe_path_config.cpp")
    add_executable(test_safe_path_config tests/test_safe_path_config.cpp)
    target_link_libraries(test_safe_path_config
        PRIVATE safe_path GTest::gtest GTest::gtest_main)
    target_include_directories(test_safe_path_config PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/include)
    add_test(NAME test_safe_path_config COMMAND test_safe_path_config)
    message(STATUS "✅ test_safe_path_config registered (DEBT-DEV-PROD-SYMLINK-001)")
endif()

# ─── test_safe_path_property — DEBT-PROPERTY-TESTING-PATTERN-001 ────────────
if(GTest_FOUND AND EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/tests/test_safe_path_property.cpp")
    add_executable(test_safe_path_property tests/test_safe_path_property.cpp)
    target_link_libraries(test_safe_path_property
        PRIVATE safe_path GTest::gtest GTest::gtest_main)
    target_include_directories(test_safe_path_property PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/include)
    include(GoogleTest)
    gtest_discover_tests(test_safe_path_property)
    message(STATUS "✅ test_safe_path_property registered (DEBT-PROPERTY-TESTING-PATTERN-001)")
endif()
