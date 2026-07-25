# suricata-adapter/CMakeLists.txt
# aRGus NDR — adapter del contrato bronce correlation_v1 para suricata.
#
# MEDIDO (DAY 226):
#   · el parser JSON del repo es nlohmann. El bloque de abajo es copia del patrón de
#     ml-detector/CMakeLists.txt:83-101 (busqueda) y 412-416 (enlazado).
#   · el target de libs/correlation-v1 se llama `correlation_v1` y es **SHARED**
#     (libs/correlation-v1/CMakeLists.txt:15). Al ejecutar el binario hay que poder
#     resolver la biblioteca dinámica; si el primer `run` falla con "library not
#     found", es esto y no un fallo del adapter.
#   · el repo localiza libsodium con `pkg_check_modules(LIBSODIUM REQUIRED libsodium)`
#     (correlation-engine/CMakeLists.txt:10) y le funciona. Aquí se usa la misma vía
#     como camino principal; el fallback a find_library es defensa extra, no debería
#     dispararse nunca en este repo.
#
# ⚠️ PASO MANUAL: añadir `add_subdirectory(suricata-adapter)` al CMakeLists.txt raíz, DESPUÉS
#    del de libs/correlation-v1 — este componente depende de él.

cmake_minimum_required(VERSION 3.16)

# ¿Build suelto de este componente o incluido desde el raíz? Se detecta comparando
# rutas: `if(NOT DEFINED PROJECT_NAME)` no sirve, PROJECT_NAME siempre está definido
# en cuanto alguien llamó a project() más arriba.
set(SURICATA_ADAPTER_STANDALONE OFF)
if(CMAKE_SOURCE_DIR STREQUAL CMAKE_CURRENT_SOURCE_DIR)
    set(SURICATA_ADAPTER_STANDALONE ON)
    project(suricata_adapter LANGUAGES CXX)
endif()

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# --- Dependencias ----------------------------------------------------------
# nlohmann/json — MEDIDO DAY 226: es el parser del repo. Patrón COPIADO de
# ml-detector/CMakeLists.txt:83-101 (QUIET + fallback header-only), para que este
# componente compile en los mismos entornos que el resto y falle con el mismo mensaje.
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

# El nombre del target depende de por cuál de las dos ramas se entro (ml-detector
# hace la misma comprobacion al enlazar).
if(TARGET nlohmann_json::nlohmann_json)
    set(SURICATA_ADAPTER_JSON_TARGET nlohmann_json::nlohmann_json)
else()
    set(SURICATA_ADAPTER_JSON_TARGET nlohmann_json)
endif()

# --- libs/correlation-v1 — NOTARIO del contrato, nunca se reimplementa aquí -----
# Si el raíz ya lo añadió, el target existe. Si no, se intenta añadir por ruta
# relativa para que este componente sea construible suelto.
if(NOT TARGET correlation_v1)
    if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/../libs/correlation-v1/CMakeLists.txt")
        add_subdirectory("${CMAKE_CURRENT_SOURCE_DIR}/../libs/correlation-v1"
                         "${CMAKE_CURRENT_BINARY_DIR}/correlation-v1")
    else()
        message(FATAL_ERROR
            "El target 'correlation_v1' no está definido. Anade "
            "add_subdirectory(libs/correlation-v1) ANTES de add_subdirectory(suricata-adapter) "
            "en el CMakeLists.txt raiz. Si el target se llama de otra forma, "
            "comprobar con: git grep -n add_library -- libs/correlation-v1/CMakeLists.txt")
    endif()
endif()

# --- libsodium: BLAKE2b-256 + base64 para el event_id determinista (D3) ---------
# ⚠️ SIN MEDIR cómo lo hace el resto del repo. Se intenta pkg-config y se cae a
#    find_library, porque en macOS con Homebrew pkg-config no siempre ve libsodium
#    sin PKG_CONFIG_PATH — y este repo se desarrolla en macOS.
find_package(PkgConfig QUIET)
if(PkgConfig_FOUND)
    pkg_check_modules(SODIUM QUIET IMPORTED_TARGET libsodium)
endif()

if(TARGET PkgConfig::SODIUM)
    message(STATUS "Found libsodium (pkg-config): ${SODIUM_VERSION}")
    set(SURICATA_ADAPTER_SODIUM_TARGET PkgConfig::SODIUM)
else()
    find_path(SODIUM_INCLUDE_DIR sodium.h)
    find_library(SODIUM_LIBRARY NAMES sodium libsodium)
    if(SODIUM_INCLUDE_DIR AND SODIUM_LIBRARY)
        message(STATUS "Found libsodium: ${SODIUM_LIBRARY}")
        add_library(suricata_adapter_sodium INTERFACE)
        target_include_directories(suricata_adapter_sodium INTERFACE ${SODIUM_INCLUDE_DIR})
        target_link_libraries(suricata_adapter_sodium INTERFACE ${SODIUM_LIBRARY})
        set(SURICATA_ADAPTER_SODIUM_TARGET suricata_adapter_sodium)
    else()
        message(FATAL_ERROR
            "libsodium not found. Install: brew install libsodium  /  "
            "sudo apt-get install libsodium-dev")
    endif()
endif()

# --- Biblioteca del adapter (pura, testeable sin I/O) ----------------------
add_library(suricata_adapter_lib
    src/to_row.cpp
    src/batch_writer.cpp
    src/config.cpp
)

target_include_directories(suricata_adapter_lib
    PUBLIC
        ${CMAKE_CURRENT_SOURCE_DIR}/include
)

# correlation_v1 es PUBLIC: to_row.hpp incluye correlation_v1/correlation_v1.hpp y
# expone CorrelationV1Row en su interfaz. nlohmann y libsodium son PRIVATE: solo
# aparecen dentro de los .cpp, nunca en las cabeceras del componente. Mantenerlo así
# es lo que permite cambiar de parser JSON tocando un solo fichero.
target_link_libraries(suricata_adapter_lib
    PUBLIC
        correlation_v1
    PRIVATE
        ${SURICATA_ADAPTER_JSON_TARGET}
        ${SURICATA_ADAPTER_SODIUM_TARGET}
)

target_compile_options(suricata_adapter_lib PRIVATE
    -Wall -Wextra -Wpedantic -Werror
)

# --- Ejecutable ------------------------------------------------------------
add_executable(suricata_adapter src/main.cpp)

# main.cpp llama a sodium_init(), así que necesita libsodium por su cuenta: en la
# biblioteca es PRIVATE y no se propaga.
target_link_libraries(suricata_adapter PRIVATE
    suricata_adapter_lib
    ${SURICATA_ADAPTER_SODIUM_TARGET}
)
target_compile_options(suricata_adapter PRIVATE -Wall -Wextra -Wpedantic -Werror)

# --- Tests -----------------------------------------------------------------
# enable_testing() solo si se construye suelto; si venimos del raíz, ya lo llamó él
# (llamarlo dos veces no rompe, pero deja la raíz de CTest en el sitio equivocado).
if(SURICATA_ADAPTER_STANDALONE)
    enable_testing()
endif()
add_subdirectory(tests)

# --- Resumen (mismo estilo que ml-detector/CMakeLists.txt:529) --------------
message(STATUS "")
message(STATUS "--- suricata-adapter ---")
message(STATUS "  C++ standard:    ${CMAKE_CXX_STANDARD}")
message(STATUS "  correlation_v1:  target disponible")
message(STATUS "  nlohmann/json:   ${SURICATA_ADAPTER_JSON_TARGET}")
message(STATUS "  libsodium:       ${SURICATA_ADAPTER_SODIUM_TARGET}")
message(STATUS "  standalone:      ${SURICATA_ADAPTER_STANDALONE}")
message(STATUS "")
