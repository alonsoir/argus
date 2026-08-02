cmake_minimum_required(VERSION 3.16)
project(argus_host_engine LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(PkgConfig REQUIRED)

# Fallback defensivo de PKG_CONFIG_PATH (lección DAY 207 del converter de red):
# shells no-interactivos (vagrant ssh -c) pueden no cargar .bashrc; añadir la ruta
# real sin pisar un PKG_CONFIG_PATH ya correcto.
if(EXISTS "/usr/lib/x86_64-linux-gnu/pkgconfig")
    set(ENV{PKG_CONFIG_PATH} "/usr/lib/x86_64-linux-gnu/pkgconfig:$ENV{PKG_CONFIG_PATH}")
endif()

pkg_check_modules(ARROW   REQUIRED arrow)
pkg_check_modules(PARQUET REQUIRED parquet)
message(STATUS "arrow: ${ARROW_VERSION} | parquet: ${PARQUET_VERSION}")

# Puerta de integridad HMAC-SHA256. El converter host NO enlaza correlation_engine
# (invariante ISLA) -> OpenSSL::Crypto se pide explícito, no se hereda.
find_package(OpenSSL REQUIRED)

add_executable(host_bronze_to_gold_converter tools/host_bronze_to_gold_converter.cpp)
target_include_directories(host_bronze_to_gold_converter PRIVATE
        ${ARROW_INCLUDE_DIRS} ${PARQUET_INCLUDE_DIRS})
target_link_directories(host_bronze_to_gold_converter PRIVATE
        ${ARROW_LIBRARY_DIRS} ${PARQUET_LIBRARY_DIRS})
target_link_libraries(host_bronze_to_gold_converter PRIVATE
        ${ARROW_LIBRARIES} ${PARQUET_LIBRARIES} OpenSSL::Crypto)