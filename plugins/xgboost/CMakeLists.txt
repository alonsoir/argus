cmake_minimum_required(VERSION 3.16)
project(plugin_xgboost VERSION 0.1.0 LANGUAGES CXX C)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# ADR-026 Track 1 — XGBoost inference plugin (PRODUCTION)
# Gate de merge: Precision >= 0.99 + F1 >= 0.9985 en CTU-13 Neris
# Ver docs/XGBOOST-VALIDATION.md

# ── plugin-loader headers (plugin_api.h) ──────────────────────────
find_path(PLUGIN_LOADER_INCLUDE_DIR
    NAMES plugin_loader/plugin_api.h
    PATHS
        ${CMAKE_SOURCE_DIR}/../../plugin-loader/include
        /usr/local/include
        /usr/include
)
if(NOT PLUGIN_LOADER_INCLUDE_DIR)
    message(FATAL_ERROR "plugin_api.h not found. Build plugin-loader first: make plugin-loader-build")
endif()

# ── XGBoost C API ────────────────────────────────────────────────
find_path(XGBOOST_INCLUDE_DIR
    NAMES xgboost/c_api.h
    PATHS
        /usr/local/include
        /usr/include
)
if(NOT XGBOOST_INCLUDE_DIR)
    message(FATAL_ERROR "xgboost/c_api.h not found. Run: vagrant provision --provision-with all-dependencies")
endif()

find_library(XGBOOST_LIB
    NAMES xgboost
    PATHS
        /usr/local/lib
        /usr/lib
)
if(NOT XGBOOST_LIB)
    message(FATAL_ERROR "libxgboost.so not found. Run: vagrant provision --provision-with all-dependencies")
endif()

message(STATUS "plugin_xgboost: XGBoost headers: ${XGBOOST_INCLUDE_DIR}")
message(STATUS "plugin_xgboost: XGBoost library: ${XGBOOST_LIB}")

# ── Target ───────────────────────────────────────────────────────
add_library(plugin_xgboost SHARED xgboost_plugin.cpp)

target_include_directories(plugin_xgboost PRIVATE
    ${PLUGIN_LOADER_INCLUDE_DIR}
    ${XGBOOST_INCLUDE_DIR}
)

target_link_libraries(plugin_xgboost PRIVATE
    ${XGBOOST_LIB}
)

set_target_properties(plugin_xgboost PROPERTIES
    PREFIX "lib"
    OUTPUT_NAME "plugin_xgboost"
    POSITION_INDEPENDENT_CODE ON
)

target_compile_options(plugin_xgboost PRIVATE
    -Wall -Wextra -Wpedantic
)

# MLD_XGBOOST_MODEL_PATH: ruta al modelo .ubj en runtime
# Default: /etc/ml-defender/models/xgboost_cicids2017.ubj
target_compile_definitions(plugin_xgboost PRIVATE
    MLD_XGBOOST_MODEL_PATH="/etc/ml-defender/models/xgboost_cicids2017.ubj"
)

message(STATUS "plugin_xgboost: will build libplugin_xgboost.so (PRODUCTION — ADR-026 Track 1)")
