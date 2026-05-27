# ============================================================================
# plugin-loader/tests/CMakeLists.txt
# TEST-PLUGIN-INVOKE-1 — DAY 102
# ============================================================================
cmake_minimum_required(VERSION 3.20)

find_library(PLUGIN_LOADER_LIB
    NAMES plugin_loader
    PATHS /usr/local/lib
    NO_DEFAULT_PATH
)
find_path(PLUGIN_LOADER_INCLUDE
    NAMES plugin_loader/plugin_loader.hpp
    PATHS /usr/local/include
    NO_DEFAULT_PATH
)

if(NOT PLUGIN_LOADER_LIB OR NOT PLUGIN_LOADER_INCLUDE)
    message(WARNING "plugin_loader no encontrado — tests omitidos")
    return()
endif()

message(STATUS "PLUGIN_LOADER_LIB: ${PLUGIN_LOADER_LIB}")
message(STATUS "PLUGIN_LOADER_INCLUDE: ${PLUGIN_LOADER_INCLUDE}")

add_executable(test_invoke_all test_invoke_all.cpp)

target_include_directories(test_invoke_all PRIVATE
    ${PLUGIN_LOADER_INCLUDE}
)
target_link_libraries(test_invoke_all PRIVATE
    ${PLUGIN_LOADER_LIB}
    dl
)
target_compile_features(test_invoke_all PRIVATE cxx_std_20)
target_compile_definitions(test_invoke_all PRIVATE PLUGIN_LOADER_ENABLED)

enable_testing()
add_test(NAME TEST-PLUGIN-INVOKE-1 COMMAND test_invoke_all)
