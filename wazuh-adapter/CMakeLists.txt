# wazuh-adapter/CMakeLists.txt
# aRGus NDR — adapter del contrato bronce host_domain_v1 para wazuh (host-domain).
#
# MEDIDO (DAY 242):
#   · el parser JSON del repo es nlohmann (bloque copiado del patrón de suricata-adapter,
#     que a su vez viene de ml-detector/CMakeLists.txt).
#   · el target de libs/host-domain-v1 se llama `host_domain_v1` y es **SHARED**
#     (libs/host-domain-v1/CMakeLists.txt). Enlaza `crypto`+`sodium` PUBLIC, así que el
#     ejecutable los recibe TRANSITIVAMENTE: este adapter NO toca libsodium directamente
#     (mint_event_id vive en la lib), a diferencia de suricata/zeek. Por eso aquí NO hay
#     bloque de libsodium.
#   · se compila en la VM `wazuh` (build dir con sufijo, `/vagrant` es compartida).
#
# ⚠️ PASO MANUAL (solo si se integra desde el raíz): añadir add_subdirectory(wazuh-adapter)
#    al CMakeLists.txt raíz DESPUÉS del de libs/host-domain-v1. El target del Makefile
#    construye el componente SUELTO, así que no lo necesita.

cmake_minimum_required(VERSION 3.16)

# ¿Build suelto de este componente o incluido desde el raíz?
set(WAZUH_ADAPTER_STANDALONE OFF)
if(CMAKE_SOURCE_DIR STREQUAL CMAKE_CURRENT_SOURCE_DIR)
    set(WAZUH_ADAPTER_STANDALONE ON)
    project(wazuh_adapter LANGUAGES CXX)
endif()

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# --- Dependencias: nlohmann/json (QUIET + fallback header-only) --------------
find_package(nlohmann_json 3.11.0 QUIET)
if(NOT nlohmann_json_FOUND)
    find_path(NLOHMANN_JSON_INCLUDE_DIR nlohmann/json.hpp)
    if(NLOHMANN_JSON_INCLUDE_DIR)
        message(STATUS "Found nlohmann/json (header-only): ${NLOHMANN_JSON_INCLUDE_DIR}")
        add_library(nlohmann_json INTERFACE)
        target_include_directories(nlohmann_json INTERFACE ${NLOHMANN_JSON_INCLUDE_DIR})
    else()
        message(FATAL_ERROR
                "nlohmann/json not found. Install: sudo apt-get install nlohmann-json3-dev")
    endif()
else()
    message(STATUS "Found nlohmann/json: ${nlohmann_json_VERSION}")
endif()

if(TARGET nlohmann_json::nlohmann_json)
    set(WAZUH_ADAPTER_JSON_TARGET nlohmann_json::nlohmann_json)
else()
    set(WAZUH_ADAPTER_JSON_TARGET nlohmann_json)
endif()

# --- libs/host-domain-v1 — NOTARIO del contrato, nunca se reimplementa aquí ---
# Trae serialize()/validate()/mint_event_id()/encode_string_list() + los enlaces
# crypto/sodium PUBLIC. Si el raíz ya lo añadió, el target existe; si no, se añade por
# ruta relativa para que este componente sea construible suelto.
if(NOT TARGET host_domain_v1)
    if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/../libs/host-domain-v1/CMakeLists.txt")
        add_subdirectory("${CMAKE_CURRENT_SOURCE_DIR}/../libs/host-domain-v1"
                "${CMAKE_CURRENT_BINARY_DIR}/host-domain-v1")
    else()
        message(FATAL_ERROR
                "El target 'host_domain_v1' no está definido. Anade "
                "add_subdirectory(libs/host-domain-v1) ANTES de add_subdirectory(wazuh-adapter) "
                "en el CMakeLists.txt raiz.")
    endif()
endif()

# --- Biblioteca del adapter (pura, testeable sin I/O) -----------------------
add_library(wazuh_adapter_lib
        src/to_row.cpp
        src/batch_writer.cpp
        src/config.cpp
)

target_include_directories(wazuh_adapter_lib
        PUBLIC
        ${CMAKE_CURRENT_SOURCE_DIR}/include
)

# host_domain_v1 es PUBLIC: to_row.hpp incluye host_domain_v1/host_domain_v1.hpp y expone
# HostDomainV1Row en su interfaz (y propaga crypto/sodium al ejecutable). nlohmann es
# PRIVATE: solo aparece en los .cpp, nunca en las cabeceras -> cambiar de parser JSON toca
# un solo fichero.
target_link_libraries(wazuh_adapter_lib
        PUBLIC
        host_domain_v1
        PRIVATE
        ${WAZUH_ADAPTER_JSON_TARGET}
)

target_compile_options(wazuh_adapter_lib PRIVATE
        -Wall -Wextra -Wpedantic -Werror
)

# --- Ejecutable ------------------------------------------------------------
# Sin enlaces extra: hereda host_domain_v1 (y crypto/sodium) de la lib del adapter.
add_executable(wazuh_adapter src/main.cpp)
target_link_libraries(wazuh_adapter PRIVATE wazuh_adapter_lib)
target_compile_options(wazuh_adapter PRIVATE -Wall -Wextra -Wpedantic -Werror)

# --- Tests -----------------------------------------------------------------
if(WAZUH_ADAPTER_STANDALONE)
    enable_testing()
endif()
add_subdirectory(tests)

# --- Resumen ---------------------------------------------------------------
message(STATUS "")
message(STATUS "--- wazuh-adapter ---")
message(STATUS "  C++ standard:    ${CMAKE_CXX_STANDARD}")
message(STATUS "  host_domain_v1:  target disponible")
message(STATUS "  nlohmann/json:   ${WAZUH_ADAPTER_JSON_TARGET}")
message(STATUS "  standalone:      ${WAZUH_ADAPTER_STANDALONE}")
message(STATUS "")