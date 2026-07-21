#!/usr/bin/env python3
"""scaffold_adapter.py — andamiaje estándar de un adapter del contrato bronce correlation_v1.

aRGus NDR — DAY 226.

Crea la estructura de un componente de primer nivel `<sensor>-adapter/` que traduce
la salida nativa de un sensor a filas del contrato bronce (19 columnas) reutilizando
`libs/correlation-v1` para serialize/HMAC/validate. NUNCA reimplementa el contrato.

Corte en tres capas (correlation_v1.hpp, DAY 185):
    [nativo -> Row]   to_row()          <- ESTE COMPONENTE, uno por sensor
    [Row -> bytes]    serialize()       <- libs/correlation-v1, notario único (P3)
    [bytes -> disco]  BatchWriter       <- ESTE COMPONENTE (CorrelationWriter vive
                                           en ml-detector y arrastra protobuf)

Uso:
    python3 tools/scaffold_adapter.py --sensor suricata
    python3 tools/scaffold_adapter.py --sensor suricata --root . --force
    python3 tools/scaffold_adapter.py --sensor zeek --dry-run

Sensores con mapeo escrito: suricata.
Cualquier otro nombre genera el mismo andamiaje con un `to_row` que devuelve Error
("no implementado") — compila y el test falla RUIDOSAMENTE, que es lo que queremos.

Idempotente por defecto: no pisa ficheros existentes salvo --force.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Plantillas. Marcadores: @@SENSOR@@ (suricata), @@NS@@ (suricata_adapter),
# @@DIR@@ (suricata-adapter), @@GUARD@@ (SURICATA_ADAPTER)
# ---------------------------------------------------------------------------

CMAKELISTS = r'''# @@DIR@@/CMakeLists.txt
# aRGus NDR — adapter del contrato bronce correlation_v1 para @@SENSOR@@.
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
# ⚠️ PASO MANUAL: añadir `add_subdirectory(@@DIR@@)` al CMakeLists.txt raíz, DESPUÉS
#    del de libs/correlation-v1 — este componente depende de él.

cmake_minimum_required(VERSION 3.16)

# ¿Build suelto de este componente o incluido desde el raíz? Se detecta comparando
# rutas: `if(NOT DEFINED PROJECT_NAME)` no sirve, PROJECT_NAME siempre está definido
# en cuanto alguien llamó a project() más arriba.
set(@@GUARD@@_STANDALONE OFF)
if(CMAKE_SOURCE_DIR STREQUAL CMAKE_CURRENT_SOURCE_DIR)
    set(@@GUARD@@_STANDALONE ON)
    project(@@NS@@ LANGUAGES CXX)
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
    set(@@GUARD@@_JSON_TARGET nlohmann_json::nlohmann_json)
else()
    set(@@GUARD@@_JSON_TARGET nlohmann_json)
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
            "add_subdirectory(libs/correlation-v1) ANTES de add_subdirectory(@@DIR@@) "
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
    set(@@GUARD@@_SODIUM_TARGET PkgConfig::SODIUM)
else()
    find_path(SODIUM_INCLUDE_DIR sodium.h)
    find_library(SODIUM_LIBRARY NAMES sodium libsodium)
    if(SODIUM_INCLUDE_DIR AND SODIUM_LIBRARY)
        message(STATUS "Found libsodium: ${SODIUM_LIBRARY}")
        add_library(@@NS@@_sodium INTERFACE)
        target_include_directories(@@NS@@_sodium INTERFACE ${SODIUM_INCLUDE_DIR})
        target_link_libraries(@@NS@@_sodium INTERFACE ${SODIUM_LIBRARY})
        set(@@GUARD@@_SODIUM_TARGET @@NS@@_sodium)
    else()
        message(FATAL_ERROR
            "libsodium not found. Install: brew install libsodium  /  "
            "sudo apt-get install libsodium-dev")
    endif()
endif()

# --- Biblioteca del adapter (pura, testeable sin I/O) ----------------------
add_library(@@NS@@_lib
    src/to_row.cpp
    src/batch_writer.cpp
    src/config.cpp
)

target_include_directories(@@NS@@_lib
    PUBLIC
        ${CMAKE_CURRENT_SOURCE_DIR}/include
)

# correlation_v1 es PUBLIC: to_row.hpp incluye correlation_v1/correlation_v1.hpp y
# expone CorrelationV1Row en su interfaz. nlohmann y libsodium son PRIVATE: solo
# aparecen dentro de los .cpp, nunca en las cabeceras del componente. Mantenerlo así
# es lo que permite cambiar de parser JSON tocando un solo fichero.
target_link_libraries(@@NS@@_lib
    PUBLIC
        correlation_v1
    PRIVATE
        ${@@GUARD@@_JSON_TARGET}
        ${@@GUARD@@_SODIUM_TARGET}
)

target_compile_options(@@NS@@_lib PRIVATE
    -Wall -Wextra -Wpedantic -Werror
)

# --- Ejecutable ------------------------------------------------------------
add_executable(@@NS@@ src/main.cpp)

# main.cpp llama a sodium_init(), así que necesita libsodium por su cuenta: en la
# biblioteca es PRIVATE y no se propaga.
target_link_libraries(@@NS@@ PRIVATE
    @@NS@@_lib
    ${@@GUARD@@_SODIUM_TARGET}
)
target_compile_options(@@NS@@ PRIVATE -Wall -Wextra -Wpedantic -Werror)

# --- Tests -----------------------------------------------------------------
# enable_testing() solo si se construye suelto; si venimos del raíz, ya lo llamó él
# (llamarlo dos veces no rompe, pero deja la raíz de CTest en el sitio equivocado).
if(@@GUARD@@_STANDALONE)
    enable_testing()
endif()
add_subdirectory(tests)

# --- Resumen (mismo estilo que ml-detector/CMakeLists.txt:529) --------------
message(STATUS "")
message(STATUS "--- @@DIR@@ ---")
message(STATUS "  C++ standard:    ${CMAKE_CXX_STANDARD}")
message(STATUS "  correlation_v1:  target disponible")
message(STATUS "  nlohmann/json:   ${@@GUARD@@_JSON_TARGET}")
message(STATUS "  libsodium:       ${@@GUARD@@_SODIUM_TARGET}")
message(STATUS "  standalone:      ${@@GUARD@@_STANDALONE}")
message(STATUS "")
'''

TESTS_CMAKELISTS = r'''# @@DIR@@/tests/CMakeLists.txt
#
# Sin framework de terceros a propósito: un main() con asserts que ctest ejecuta.
# El repo usa ctest (`make correlation-engine-test`); qué framework usa por dentro
# NO se ha medido (DAY 226). Si es GoogleTest y prefieres alinear, cámbialo aquí.

add_executable(test_to_row test_to_row.cpp)
target_link_libraries(test_to_row PRIVATE @@NS@@_lib)
target_compile_options(test_to_row PRIVATE -Wall -Wextra -Wpedantic -Werror)

add_test(NAME @@NS@@_to_row COMMAND test_to_row)
'''

TO_ROW_HPP = r'''// @@DIR@@/include/@@NS@@/to_row.hpp
// aRGus NDR — @@SENSOR@@ -> CorrelationV1Row. Capa PURA del adapter.
//
// ESPEJO de ml-detector/src/correlation_writer.cpp::to_correlation_v1_row (el ORÁCULO).
// Misma forma, misma semántica de tres estados. Lo que cambia es la fuente de datos.
//
// PURA: sin fichero, sin reloj, sin red, sin fetch de clave. Eso permite que el test
// le pase una línea literal y compruebe el Row campo a campo sin montar nada.
#pragma once

#include <string>

#include <correlation_v1/correlation_v1.hpp>

namespace @@NS@@ {

// Constantes del contrato para este productor.
// D-C (correlation_v1.hpp): schema_version y source_sensor son CAMPOS del Row,
// no constantes de la librería. Cada adapter fija los suyos.
inline constexpr const char* SCHEMA_VERSION           = "1";
inline constexpr const char* CORRELATION_SOURCE_SENSOR = "@@SENSOR@@";

// Col 17. ⚠️ El guard D-D está DIFERIDO en validate() v1: hoy NO se exige que este
// símbolo sea un DetectorSource legal. Cuando se active (commit de contrato),
// "@@SENSOR@@" tendrá que ser símbolo legal o estas filas empezarán a rechazarse.
inline constexpr const char* AUTHORITATIVE_SOURCE      = "@@SENSOR@@";

// Prefijo del event_id (D3): espacio de nombres propio, sin colisión con aRGus.
inline constexpr const char* EVENT_ID_PREFIX           = "@@SENSOR@@:";

// ---------------------------------------------------------------------------
// Resultado de tres estados. NO se reutiliza ml-detector::ToRowResult porque
// arrastra protobuf; se IMITA exactamente para que D5 (descarte explícito) sea
// el mismo mecanismo que ya usa aRGus, no una convención nueva de este adapter.
//
//   Ok    -> hay fila
//   Skip  -> descarte LEGÍTIMO (no es pérdida). Sin línea y sin fallo, pero con
//            motivo, para el contador ruidoso de D5.
//   Error -> bug del productor. Ruidoso.
// ---------------------------------------------------------------------------
struct [[nodiscard]] ToRowResult {
    enum class Status { Ok, Skip, Error };

    Status status = Status::Error;
    correlation_v1::CorrelationV1Row row{};
    std::string reason;   // motivo del Skip o diagnóstico del Error; vacío si Ok

    static ToRowResult ok(correlation_v1::CorrelationV1Row r);
    static ToRowResult skip(std::string why);
    static ToRowResult error(std::string what);
};

// ---------------------------------------------------------------------------
// to_row — una línea de la salida nativa de @@SENSOR@@ -> Row.
//
// node_id: punto de OBSERVACIÓN (D2), no el host que ejecuta el sensor. Viene de
// la config; dos sensores con el mismo node_id declaran que observan lo mismo.
// ---------------------------------------------------------------------------
[[nodiscard]] ToRowResult to_row(const std::string& line, const std::string& node_id);

// Expuesta para el test: "2011-08-10T09:04:32.432327+0000" -> (secs, nanos).
// Respeta el offset DEL EVENTO, no el de la máquina que ejecuta el adapter.
[[nodiscard]] bool parse_iso8601(const std::string& ts, int64_t& secs, int32_t& nanos);

// Expuesta para el test: event_id determinista (D3).
[[nodiscard]] std::string make_event_id(const std::string& timestamp,
                                        const std::string& flow_id,
                                        const std::string& signature_id,
                                        const std::string& community_id);

}  // namespace @@NS@@
'''

TO_ROW_CPP_SURICATA = r'''// @@DIR@@/src/to_row.cpp
// aRGus NDR — eve.json (Suricata) -> CorrelationV1Row.
//
// ⚠️ ÚNICO FICHERO DEL COMPONENTE QUE TOCA JSON. Es deliberado: si el repo no usa
//    nlohmann sino rapidjson/simdjson, se reescribe este fichero y nada más.
//
// Decisiones aplicadas (docs/design/multisensor-graph-identity/puerta-diseno-multisensor.md):
//   D3  event_id = "suricata:" + base64(BLAKE2b-256(timestamp ‖ flow_id ‖ sid ‖ community_id))
//   D5  descarte explícito con motivo (stats, decoder sin flujo, telemetría)
//   D6  los 3 scores quedan a 0.0 = ausencia documentada; el consumidor filtra por
//       source_sensor. Los de TEXTO sí se mapean:
//         final_classification <- alert.signature
//         threat_category      <- alert.category
//       alert.severity SE PIERDE (ordinal 1-3, no probabilidad). Rederivable desde
//       la signature.

#include "@@NS@@/to_row.hpp"

#include <cstring>
#include <ctime>
#include <string>

#include <nlohmann/json.hpp>
#include <sodium.h>

namespace @@NS@@ {

namespace {

// Separador de campos en la preimagen del event_id. Marca de campo no imprimible
// para que la concatenación sea inyectiva ante valores con caracteres raros.
// ⚠️ DECISIÓN NO RATIFICADA (DAY 226): la puerta de diseño dice "timestamp ‖ flow_id ‖
//    signature_id ‖ community_id" sin fijar la codificación. flow_uid.hpp usa
//    length-prefix canónico; aquí se usa separador. Unificar o documentar la diferencia.
constexpr char kFieldSep = '\x1f';

std::string json_str(const nlohmann::json& j, const char* key) {
    auto it = j.find(key);
    if (it == j.end() || it->is_null()) return {};
    if (it->is_string()) return it->get<std::string>();
    return it->dump();  // números (flow_id, signature_id) -> su representación
}

}  // namespace

// ---------------------------------------------------------------------------
ToRowResult ToRowResult::ok(correlation_v1::CorrelationV1Row r) {
    ToRowResult t;
    t.status = Status::Ok;
    t.row = std::move(r);
    return t;
}

ToRowResult ToRowResult::skip(std::string why) {
    ToRowResult t;
    t.status = Status::Skip;
    t.reason = std::move(why);
    return t;
}

ToRowResult ToRowResult::error(std::string what) {
    ToRowResult t;
    t.status = Status::Error;
    t.reason = std::move(what);
    return t;
}

// ---------------------------------------------------------------------------
// parse_iso8601 — "2011-08-10T09:04:32.432327+0000" (formato MEDIDO en DAY 225).
// Tolera 'Z', offset con y sin dos puntos, y fracción de 0 a 9 dígitos.
// ---------------------------------------------------------------------------
bool parse_iso8601(const std::string& ts, int64_t& secs, int32_t& nanos) {
    if (ts.size() < 19) return false;

    std::tm tm{};
    const char* rest = strptime(ts.c_str(), "%Y-%m-%dT%H:%M:%S", &tm);
    if (rest == nullptr) return false;

    // Fracción de segundo.
    int64_t frac_ns = 0;
    if (*rest == '.') {
        ++rest;
        int digits = 0;
        int64_t value = 0;
        while (digits < 9 && *rest >= '0' && *rest <= '9') {
            value = value * 10 + (*rest - '0');
            ++digits;
            ++rest;
        }
        while (*rest >= '0' && *rest <= '9') ++rest;  // exceso: se descarta
        for (int i = digits; i < 9; ++i) value *= 10;
        frac_ns = value;
    }

    // Offset del EVENTO (no el de esta máquina).
    int64_t offset_sec = 0;
    if (*rest == '+' || *rest == '-') {
        const int sign = (*rest == '-') ? -1 : 1;
        ++rest;
        if (std::strlen(rest) < 4) return false;
        const int hh = (rest[0] - '0') * 10 + (rest[1] - '0');
        const int mm_off = (rest[2] == ':') ? (rest[3] - '0') * 10 + (rest[4] - '0')
                                            : (rest[2] - '0') * 10 + (rest[3] - '0');
        offset_sec = sign * (hh * 3600 + mm_off * 60);
    } else if (*rest != 'Z' && *rest != '\0') {
        return false;
    }

    const time_t utc = timegm(&tm);          // interpreta tm como UTC
    secs  = static_cast<int64_t>(utc) - offset_sec;
    nanos = static_cast<int32_t>(frac_ns);
    return true;
}

// ---------------------------------------------------------------------------
// make_event_id — D3. Determinista: el mismo eve.json da el mismo event_id en
// cada replay, así que reprocesar no duplica nodos en el grafo.
// NO usa pcap_cnt (existe en replay offline, no garantizado en vivo).
// ---------------------------------------------------------------------------
std::string make_event_id(const std::string& timestamp,
                          const std::string& flow_id,
                          const std::string& signature_id,
                          const std::string& community_id) {
    std::string preimage;
    preimage.reserve(timestamp.size() + flow_id.size() +
                     signature_id.size() + community_id.size() + 3);
    preimage.append(timestamp);    preimage.push_back(kFieldSep);
    preimage.append(flow_id);      preimage.push_back(kFieldSep);
    preimage.append(signature_id); preimage.push_back(kFieldSep);
    preimage.append(community_id);

    unsigned char digest[32];
    crypto_generichash(digest, sizeof(digest),
                       reinterpret_cast<const unsigned char*>(preimage.data()),
                       preimage.size(), nullptr, 0);

    char b64[sodium_base64_ENCODED_LEN(sizeof(digest), sodium_base64_VARIANT_ORIGINAL)];
    sodium_bin2base64(b64, sizeof(b64), digest, sizeof(digest),
                      sodium_base64_VARIANT_ORIGINAL);

    return std::string(EVENT_ID_PREFIX) + b64;
}

// ---------------------------------------------------------------------------
// to_row
// ---------------------------------------------------------------------------
ToRowResult to_row(const std::string& line, const std::string& node_id) {
    if (line.empty()) return ToRowResult::skip("linea vacia");

    nlohmann::json j;
    try {
        j = nlohmann::json::parse(line);
    } catch (const nlohmann::json::parse_error& e) {
        return ToRowResult::error(std::string("json ilegible: ") + e.what());
    }

    const std::string event_type = json_str(j, "event_type");

    // D5 — descarte explícito. `stats` no es un evento de red (medido DAY 225: 2
    // eventos, sin community_id ni flow_id).
    if (event_type == "stats") return ToRowResult::skip("event_type=stats");

    // Hoy solo alertas. La telemetría (dns/http/tls/... = 98,7% del volumen) trae
    // community_id pero flow.start = 0 en los NUEVE tipos (medido DAY 225): cuelga
    // de la conversación por community_id (D4) y necesita su propia ruta.
    if (event_type != "alert") return ToRowResult::skip("event_type=" + event_type);

    // D-F / D5 — sin community_id no hay identidad. Mismo SKIP que el oráculo.
    // (validate() lo rechazaría igual: la política está reforzada por el contrato.)
    const std::string community_id = json_str(j, "community_id");
    if (community_id.empty()) {
        return ToRowResult::skip("sin community_id (decoder sin flujo)");
    }

    // flow.start — MEDIDO DAY 225: presente en 2.870 de 2.872 alertas. NO usar el
    // `timestamp` del evento: en una alerta es la hora de la alerta, no del flujo.
    const auto flow_it = j.find("flow");
    if (flow_it == j.end()) return ToRowResult::skip("alerta sin objeto flow");

    const std::string flow_start = json_str(*flow_it, "start");
    int64_t secs = 0;
    int32_t nanos = 0;
    if (flow_start.empty() || !parse_iso8601(flow_start, secs, nanos)) {
        return ToRowResult::error("flow.start no parseable: " + flow_start);
    }

    const auto alert_it = j.find("alert");
    if (alert_it == j.end()) return ToRowResult::error("event_type=alert sin objeto alert");

    correlation_v1::CorrelationV1Row r;
    r.schema_version  = SCHEMA_VERSION;                                    // 0
    r.source_sensor   = CORRELATION_SOURCE_SENSOR;                         // 1
    r.event_id        = make_event_id(json_str(j, "timestamp"),            // 2
                                      json_str(j, "flow_id"),
                                      json_str(*alert_it, "signature_id"),
                                      community_id);
    r.node_id         = node_id;                                           // 3
    r.community_id    = community_id;                                      // 4
    r.flow_start_sec  = secs;                                              // 5
    r.flow_start_nano = nanos;                                             // 6
    // Cols 7-10 — DEL OBJETO `flow`, NO del nivel superior. MEDIDO DAY 226 sobre
    // las 2.872 alertas del Neris: 2.870 traen flow.src_ip (las 2 que no son
    // exactamente las de decoder, ya descartadas arriba) y **2.853 de 2.870 (99,4%)
    // están INVERTIDAS respecto al nivel superior**.
    //
    // Por qué: el par de nivel superior es el del PAQUETE que disparó la alerta y
    // depende de `direction`; el de `flow` es el del ORIGINADOR del flujo. Copiar el
    // de arriba dejaría src/dst intercambiados entre alertas del MISMO community_id,
    // y con D1 el nodo del grafo ES la conversación.
    //
    // El fallback al nivel superior no se dispara en la práctica; existe para no
    // depender de que `flow` traiga siempre estos campos en otras versiones/capturas.
    const nlohmann::json& ep = flow_it->contains("src_ip") ? *flow_it : j;

    r.src_ip          = json_str(ep, "src_ip");                            // 7
    r.dst_ip          = json_str(ep, "dest_ip");                           // 8
    r.src_port        = ep.value("src_port", 0u);                          // 9
    r.dst_port        = ep.value("dest_port", 0u);                         // 10
    r.protocol        = json_str(j, "proto");                              // 11  (solo nivel superior)

    // D6 — el veredicto propio de Suricata va a los campos de TEXTO. Dejarlos
    // vacíos tiraría a la basura el valor de integrar Suricata.
    r.final_classification = json_str(*alert_it, "signature");             // 12
    r.threat_category      = json_str(*alert_it, "category");              // 13

    // D6 — los 3 scores son `double`: "vacío" NO es representable. Quedan a 0.0
    // como AUSENCIA DOCUMENTADA. El consumidor filtra SIEMPRE por source_sensor.
    // (Opción C, NaN, era la semánticamente correcta; descartada por round-trip
    // sin probar en CSV/Parquet/Kuzu.)
    r.fast_detector_score  = 0.0;                                          // 14
    r.ml_detector_score    = 0.0;                                          // 15
    r.overall_threat_score = 0.0;                                          // 16

    r.authoritative_source = AUTHORITATIVE_SOURCE;                         // 17
    // col 18 (HMAC) la calcula serialize(); no vive en el Row.

    return ToRowResult::ok(std::move(r));
}

}  // namespace @@NS@@
'''

TO_ROW_CPP_STUB = r'''// @@DIR@@/src/to_row.cpp
// aRGus NDR — @@SENSOR@@ -> CorrelationV1Row.
//
// 🔴 NO IMPLEMENTADO. Andamiaje generado por tools/scaffold_adapter.py.
//
// Devuelve Error a propósito: compila, y el test falla RUIDOSAMENTE. Un stub que
// devolviera Skip mentiría (parecería un descarte legítimo) y un stub que devolviera
// Ok con un Row vacío sería peor todavía: validate() lo rechazaría por community_id
// vacío y el fallo aparecería tres capas más abajo.
//
// Antes de escribirlo, MEDIR contra fichero (nunca contra memoria) qué emite este
// sensor de verdad: qué tipos de evento, cuáles traen community_id, cuáles traen
// inicio de flujo. Ver tools/eval/eve_field_coverage.py como plantilla.

#include "@@NS@@/to_row.hpp"

namespace @@NS@@ {

ToRowResult ToRowResult::ok(correlation_v1::CorrelationV1Row r) {
    ToRowResult t;
    t.status = Status::Ok;
    t.row = std::move(r);
    return t;
}

ToRowResult ToRowResult::skip(std::string why) {
    ToRowResult t;
    t.status = Status::Skip;
    t.reason = std::move(why);
    return t;
}

ToRowResult ToRowResult::error(std::string what) {
    ToRowResult t;
    t.status = Status::Error;
    t.reason = std::move(what);
    return t;
}

bool parse_iso8601(const std::string&, int64_t&, int32_t&) {
    return false;
}

std::string make_event_id(const std::string&, const std::string&,
                          const std::string&, const std::string&) {
    return {};
}

ToRowResult to_row(const std::string&, const std::string&) {
    return ToRowResult::error("to_row de @@SENSOR@@ no implementado");
}

}  // namespace @@NS@@
'''

BATCH_WRITER_HPP = r'''// @@DIR@@/include/@@NS@@/batch_writer.hpp
// aRGus NDR — capa [bytes -> disco] del adapter.
//
// POR QUÉ NO SE REUTILIZA CorrelationWriter: vive en ml-detector y arrastra protobuf
// (correlation_v1.hpp, corte en tres capas). Y su complejidad —rotación por tiempo
// absoluto, mutex, reloj— existe para un productor CONTINUO. Este adapter es de LOTE:
// un fichero por ejecución. Copiar aquella máquina sería complejidad sin demanda.
//
// Lo que SÍ se copia es lo que importa: escritura atómica .tmp -> rename, para que
// ningún consumidor vea jamás un fichero a medio escribir.
#pragma once

#include <cstdint>
#include <fstream>
#include <string>

namespace @@NS@@ {

class BatchWriter {
public:
    BatchWriter(std::string base_dir, std::string source_sensor);
    ~BatchWriter();

    BatchWriter(const BatchWriter&) = delete;
    BatchWriter& operator=(const BatchWriter&) = delete;

    // Abre <base_dir>/<source_sensor>-%Y-%m-%d-%H%M%S.csv.tmp
    [[nodiscard]] bool open();

    // Escribe una línea ya serializada por libs/correlation-v1 (cols 0-18).
    [[nodiscard]] bool write_line(const std::string& line);

    // Cierra y RENOMBRA .tmp -> definitivo. Hasta aquí el fichero no existe
    // para nadie. Si no se llama, el .tmp se queda: fallo visible, no silencioso.
    [[nodiscard]] bool close();

    uint64_t lines_written() const noexcept { return lines_written_; }
    const std::string& tmp_path()   const noexcept { return tmp_path_; }
    const std::string& final_path() const noexcept { return final_path_; }

private:
    std::string base_dir_;
    std::string source_sensor_;
    std::string tmp_path_;
    std::string final_path_;
    std::ofstream out_;
    uint64_t lines_written_ = 0;
};

}  // namespace @@NS@@
'''

BATCH_WRITER_CPP = r'''// @@DIR@@/src/batch_writer.cpp

#include "@@NS@@/batch_writer.hpp"

#include <cstdio>
#include <ctime>
#include <utility>

namespace @@NS@@ {

BatchWriter::BatchWriter(std::string base_dir, std::string source_sensor)
    : base_dir_(std::move(base_dir)), source_sensor_(std::move(source_sensor)) {}

BatchWriter::~BatchWriter() {
    if (out_.is_open()) out_.close();   // .tmp sin renombrar = fallo visible
}

bool BatchWriter::open() {
    if (out_.is_open()) return false;

    // Basename idéntico en forma al del oráculo: <sensor>-%Y-%m-%d-%H%M%S.csv
    // Este es el ÚNICO uso del reloj en todo el componente; to_row es puro.
    const std::time_t now = std::time(nullptr);
    std::tm tm{};
    localtime_r(&now, &tm);
    char stamp[32];
    std::strftime(stamp, sizeof(stamp), "%Y-%m-%d-%H%M%S", &tm);

    final_path_ = base_dir_ + "/" + source_sensor_ + "-" + stamp + ".csv";
    tmp_path_   = final_path_ + ".tmp";

    out_.open(tmp_path_, std::ios::out | std::ios::trunc);
    return out_.is_open();
}

bool BatchWriter::write_line(const std::string& line) {
    if (!out_.is_open()) return false;
    out_ << line << "\n";               // sin cabecera: el bronce no la tiene
    if (!out_) return false;
    ++lines_written_;
    return true;
}

bool BatchWriter::close() {
    if (!out_.is_open()) return false;
    out_.flush();
    const bool stream_ok = static_cast<bool>(out_);
    out_.close();
    if (!stream_ok) return false;
    return std::rename(tmp_path_.c_str(), final_path_.c_str()) == 0;
}

}  // namespace @@NS@@
'''

CONFIG_HPP = r'''// @@DIR@@/include/@@NS@@/config.hpp
// aRGus NDR — configuración del adapter de @@SENSOR@@.
#pragma once

#include <string>

namespace @@NS@@ {

struct Config {
    // Buzón PLANO del bronce, compartido con el resto de productores.
    std::string base_dir = "/vagrant/logs/correlation";

    // D2 — punto de OBSERVACIÓN, no el host. Dos sensores con el mismo node_id
    // declaran que observan la misma interfaz; si observan interfaces distintas es
    // CORRECTO que generen subgrafos distintos.
    //
    // ⚠️ MEDIDO DAY 226: el node_id real que emite aRGus hoy es "cpp_sniffer_v33_day12",
    //    una etiqueta de VERSIÓN del sniffer. Para converger hay que poner aquí ese
    //    mismo valor. Es incorrecto semánticamente y está registrado como deuda.
    std::string node_id;

    // Entrada: eve.json (JSONL) a procesar en lote.
    std::string input_path;

    // Clave HMAC de 64 chars hex -> 32 bytes.
    // ⚠️ DEBE SER LA MISMA QUE USA aRGus o el lector de aguas abajo rechazará estas
    //    filas. correlation_v1.hpp dice: "ARGUS_BRONZE_HMAC_KEY_HEX en test,
    //    etcd-server en el adapter". Hoy: variable de entorno.
    std::string hmac_key_env = "ARGUS_BRONZE_HMAC_KEY_HEX";
};

// Carga desde JSON. Devuelve false y deja `error` si el fichero falta o es ilegible.
[[nodiscard]] bool load_config(const std::string& path, Config& out, std::string& error);

}  // namespace @@NS@@
'''

CONFIG_CPP = r'''// @@DIR@@/src/config.cpp

#include "@@NS@@/config.hpp"

#include <fstream>

#include <nlohmann/json.hpp>

namespace @@NS@@ {

bool load_config(const std::string& path, Config& out, std::string& error) {
    std::ifstream in(path);
    if (!in) {
        error = "no se puede abrir la config: " + path;
        return false;
    }

    nlohmann::json j;
    try {
        in >> j;
    } catch (const nlohmann::json::parse_error& e) {
        error = std::string("config ilegible: ") + e.what();
        return false;
    }

    out.base_dir     = j.value("base_dir", out.base_dir);
    out.node_id      = j.value("node_id", out.node_id);
    out.input_path   = j.value("input_path", out.input_path);
    out.hmac_key_env = j.value("hmac_key_env", out.hmac_key_env);

    if (out.node_id.empty()) {
        error = "node_id vacio: sin el, las filas no convergen con las de aRGus (D2)";
        return false;
    }
    return true;
}

}  // namespace @@NS@@
'''

CONFIG_JSON = r'''{
  "_comentario": "aRGus NDR — adapter de @@SENSOR@@. DAY 226.",
  "_node_id": "D2: punto de observacion, NO el host. Debe coincidir con el de aRGus para converger. Valor real medido en el bronce de aRGus: cpp_sniffer_v33_day12",
  "_hmac_key_env": "Debe ser la MISMA clave que usa aRGus o el lector rechazara estas filas",

  "base_dir": "/vagrant/logs/correlation",
  "node_id": "cpp_sniffer_v33_day12",
  "input_path": "logs/day225-@@SENSOR@@-neris/eve.json",
  "hmac_key_env": "ARGUS_BRONZE_HMAC_KEY_HEX"
}
'''

MAIN_CPP = r'''// @@DIR@@/src/main.cpp
// aRGus NDR — adapter de @@SENSOR@@, modo LOTE.
//
// Pipeline: linea JSONL -> to_row() -> serialize() -> BatchWriter
//                                      ^^^^^^^^^^^
//                          libs/correlation-v1, notario único (P3).
//                          Lo que validate() rechaza, serialize() NO lo emite.
//
// Contadores RUIDOSOS al final (D5): un descarte silencioso es indistinguible de
// un bug. Si skipped y written no cuadran con lo medido en el eve.json, se ve aquí.

#include <cstdlib>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

#include <sodium.h>

#include <correlation_v1/correlation_v1.hpp>

#include "@@NS@@/batch_writer.hpp"
#include "@@NS@@/config.hpp"
#include "@@NS@@/to_row.hpp"

namespace {

// 64 chars hex -> 32 bytes. La lib recibe la clave YA decodificada (es INPUT puro).
bool hex_to_key(const std::string& hex, std::vector<uint8_t>& out, std::string& error) {
    if (hex.size() != 64) {
        error = "la clave HMAC debe tener 64 chars hex, tiene " + std::to_string(hex.size());
        return false;
    }
    out.assign(32, 0);
    for (size_t i = 0; i < 32; ++i) {
        auto nibble = [&](char c, int& v) {
            if (c >= '0' && c <= '9') { v = c - '0';        return true; }
            if (c >= 'a' && c <= 'f') { v = c - 'a' + 10;   return true; }
            if (c >= 'A' && c <= 'F') { v = c - 'A' + 10;   return true; }
            return false;
        };
        int hi = 0, lo = 0;
        if (!nibble(hex[i * 2], hi) || !nibble(hex[i * 2 + 1], lo)) {
            error = "caracter no hexadecimal en la clave HMAC";
            return false;
        }
        out[i] = static_cast<uint8_t>((hi << 4) | lo);
    }
    return true;
}

}  // namespace

int main(int argc, char** argv) {
    if (sodium_init() < 0) {
        std::cerr << "[FATAL] sodium_init fallo\n";
        return 2;
    }

    if (argc < 2) {
        std::cerr << "uso: @@NS@@ <config.json> [entrada.json]\n";
        return 2;
    }

    @@NS@@::Config cfg;
    std::string error;
    if (!@@NS@@::load_config(argv[1], cfg, error)) {
        std::cerr << "[FATAL] " << error << "\n";
        return 2;
    }
    if (argc >= 3) cfg.input_path = argv[2];

    const char* key_hex = std::getenv(cfg.hmac_key_env.c_str());
    if (key_hex == nullptr) {
        std::cerr << "[FATAL] variable de entorno no definida: " << cfg.hmac_key_env << "\n";
        return 2;
    }
    std::vector<uint8_t> hmac_key;
    if (!hex_to_key(key_hex, hmac_key, error)) {
        std::cerr << "[FATAL] " << error << "\n";
        return 2;
    }

    std::ifstream in(cfg.input_path);
    if (!in) {
        std::cerr << "[FATAL] no se puede abrir la entrada: " << cfg.input_path << "\n";
        return 2;
    }

    @@NS@@::BatchWriter writer(cfg.base_dir, @@NS@@::CORRELATION_SOURCE_SENSOR);
    if (!writer.open()) {
        std::cerr << "[FATAL] no se puede abrir el fichero de salida en " << cfg.base_dir << "\n";
        return 2;
    }

    uint64_t total = 0, written = 0, skipped = 0, to_row_err = 0, serialize_err = 0;
    std::string line;
    while (std::getline(in, line)) {
        ++total;
        auto tr = @@NS@@::to_row(line, cfg.node_id);

        if (tr.status == @@NS@@::ToRowResult::Status::Skip) {
            ++skipped;
            continue;
        }
        if (tr.status == @@NS@@::ToRowResult::Status::Error) {
            ++to_row_err;
            std::cerr << "[WARN] to_row linea " << total << ": " << tr.reason << "\n";
            continue;
        }

        auto sr = correlation_v1::serialize(tr.row, hmac_key);
        if (!sr) {
            ++serialize_err;
            std::cerr << "[WARN] serialize rechazo linea " << total << ": " << sr.error << "\n";
            continue;
        }
        if (!writer.write_line(sr.line)) {
            std::cerr << "[FATAL] fallo de escritura en " << writer.tmp_path() << "\n";
            return 2;
        }
        ++written;
    }

    if (!writer.close()) {
        std::cerr << "[FATAL] fallo al cerrar/renombrar " << writer.tmp_path() << "\n";
        return 2;
    }

    // D5 — contadores ruidosos. Sin esto, un descarte masivo pasaría por exito.
    std::cout << "[" << @@NS@@::CORRELATION_SOURCE_SENSOR << "-adapter]"
              << " leidas="        << total
              << " escritas="      << written
              << " descartadas="   << skipped
              << " err_to_row="    << to_row_err
              << " err_serialize=" << serialize_err
              << "\n salida: "     << writer.final_path() << "\n";

    return (written > 0) ? 0 : 1;   // 0 filas es fallo, no exito silencioso
}
'''

TEST_CPP = r'''// @@DIR@@/tests/test_to_row.cpp
// aRGus NDR — test de la capa PURA del adapter de @@SENSOR@@.
//
// Sin framework: main() con asserts, ejecutado por ctest. to_row es pura, así que
// el test le da una línea literal y comprueba el Row campo a campo. Sin VM, sin
// fichero, sin reloj.
//
// VECTOR REAL: primera alerta de logs/day225-@@SENSOR@@-neris/eve.json, copiada
// literalmente (DAY 226). Es un "SURICATA TCPv4 invalid checksum", o sea un
// artefacto de la captura (68/1000 checksums invalidos, medido DAY 225), no un
// ataque. Da igual para el test: trae community_id y flow.start, que es lo que
// se comprueba. Pero no sirve de escaparate en el paper.
//
// Reproducir:  grep -m1 '"event_type":"alert"' logs/day225-@@SENSOR@@-neris/eve.json

#include <cassert>
#include <cstdint>
#include <iostream>
#include <string>

#include "@@NS@@/to_row.hpp"

namespace {

const char* kAlertLine = R"({"timestamp":"2011-08-10T09:06:36.150781+0000","flow_id":1180526643469803,"pcap_cnt":126,"event_type":"alert","src_ip":"94.63.149.152","src_port":80,"dest_ip":"147.32.84.165","dest_port":1040,"proto":"TCP","pkt_src":"wire/pcap","community_id":"1:MuSlbWV2Dy5Z168c5sxOWncbYyQ=","alert":{"action":"allowed","gid":1,"signature_id":2200074,"rev":2,"signature":"SURICATA TCPv4 invalid checksum","category":"Generic Protocol Command Decode","severity":3},"app_proto":"http","direction":"to_client","flow":{"pkts_toserver":6,"pkts_toclient":3,"bytes_toserver":532,"bytes_toclient":4556,"start":"2011-08-10T09:06:36.078254+0000","src_ip":"147.32.84.165","dest_ip":"94.63.149.152","src_port":1040,"dest_port":80}})";

int failures = 0;

void check(bool cond, const char* what) {
    if (!cond) {
        std::cerr << "FALLO: " << what << "\n";
        ++failures;
    }
}

void test_parse_iso8601() {
    int64_t secs = 0;
    int32_t nanos = 0;
    check(@@NS@@::parse_iso8601("2011-08-10T09:06:36.078254+0000", secs, nanos),
          "parse_iso8601 acepta el formato medido");
    check(secs == 1312967196, "epoch de 2011-08-10T09:06:36Z");
    check(nanos == 78254000, "micros x 1000 -> nanos (078254 -> 78254000)");

    // El offset es DEL EVENTO: la misma hora de pared con +0200 son 2 h menos de epoch.
    int64_t secs_cest = 0;
    int32_t nanos_cest = 0;
    check(@@NS@@::parse_iso8601("2011-08-10T09:06:36.078254+0200", secs_cest, nanos_cest),
          "parse_iso8601 acepta offset no nulo");
    check(secs_cest == secs - 7200, "el offset del evento se resta");
}

void test_alerta_produce_fila() {
    auto r = @@NS@@::to_row(kAlertLine, "cpp_sniffer_v33_day12");
    check(r.status == @@NS@@::ToRowResult::Status::Ok, "una alerta con community_id da Ok");
    if (r.status != @@NS@@::ToRowResult::Status::Ok) return;

    check(r.row.schema_version == "1",                          "col 0 schema_version");
    check(r.row.source_sensor == "@@SENSOR@@",                  "col 1 source_sensor");
    check(r.row.event_id.rfind("@@SENSOR@@:", 0) == 0,          "col 2 event_id prefijado (D3)");
    check(r.row.node_id == "cpp_sniffer_v33_day12",             "col 3 node_id de la config");
    check(r.row.community_id == "1:MuSlbWV2Dy5Z168c5sxOWncbYyQ=", "col 4 community_id");
    check(r.row.flow_start_sec == 1312967196,                   "col 5 de flow.start (09:06:36), NO del timestamp del evento (09:06:36.150781)");
    check(r.row.flow_start_nano == 78254000,                    "col 6 de flow.start");

    // Cols 7-10 del OBJETO flow (originador), no del nivel superior (paquete).
    // En este vector estan invertidos entre si, como en el 99,4% de las alertas
    // del Neris: si el adapter copiara el nivel superior, aqui saldria
    // 94.63.149.152:80 -> 147.32.84.165:1040. Este test es el que lo impide.
    check(r.row.src_ip == "147.32.84.165",                      "col 7 <- flow.src_ip, no el de nivel superior");
    check(r.row.dst_ip == "94.63.149.152",                      "col 8 <- flow.dest_ip");
    check(r.row.src_port == 1040,                               "col 9 <- flow.src_port");
    check(r.row.dst_port == 80,                                 "col 10 <- flow.dest_port");
    check(r.row.protocol == "TCP",                              "col 11 proto -> protocol");
    check(r.row.final_classification == "SURICATA TCPv4 invalid checksum",
          "col 12 <- alert.signature (D6)");
    check(r.row.threat_category == "Generic Protocol Command Decode",
          "col 13 <- alert.category (D6)");
    check(r.row.fast_detector_score == 0.0,                     "col 14 = 0.0 ausencia (D6)");
    check(r.row.ml_detector_score == 0.0,                       "col 15 = 0.0 ausencia (D6)");
    check(r.row.overall_threat_score == 0.0,                    "col 16 = 0.0 ausencia (D6)");
    check(r.row.authoritative_source == "@@SENSOR@@",           "col 17 authoritative_source");
}

void test_event_id_determinista() {
    auto a = @@NS@@::to_row(kAlertLine, "n1");
    auto b = @@NS@@::to_row(kAlertLine, "n1");
    check(a.status == @@NS@@::ToRowResult::Status::Ok &&
          a.row.event_id == b.row.event_id,
          "D3: la misma linea da el mismo event_id (reprocesar no duplica nodos)");
}

void test_descartes() {
    auto stats = @@NS@@::to_row(R"({"event_type":"stats"})", "n1");
    check(stats.status == @@NS@@::ToRowResult::Status::Skip, "stats se descarta (D5)");

    auto dns = @@NS@@::to_row(R"({"event_type":"dns","community_id":"1:abc="})", "n1");
    check(dns.status == @@NS@@::ToRowResult::Status::Skip, "la telemetria se descarta hoy (D4)");

    auto decoder = @@NS@@::to_row(
        R"({"event_type":"alert","alert":{"signature_id":2200076}})", "n1");
    check(decoder.status == @@NS@@::ToRowResult::Status::Skip,
          "alerta de decoder sin community_id se descarta (D5), no es Error");

    auto basura = @@NS@@::to_row("{esto no es json", "n1");
    check(basura.status == @@NS@@::ToRowResult::Status::Error,
          "json ilegible es Error, no Skip: un Skip lo haria invisible");
}

}  // namespace

int main() {
    test_parse_iso8601();
    test_alerta_produce_fila();
    test_event_id_determinista();
    test_descartes();

    if (failures != 0) {
        std::cerr << failures << " comprobacion(es) fallidas\n";
        return 1;
    }
    std::cout << "OK — capa pura del adapter de @@SENSOR@@\n";
    return 0;
}
'''

README = r'''# @@DIR@@

Adapter del contrato bronce `correlation_v1` para **@@SENSOR@@**.

Traduce la salida nativa del sensor a filas del bronce (19 columnas) y las serializa
con `libs/correlation-v1`. **No reimplementa el contrato**: `validate()` y el HMAC
viven en la librería, que es el notario único (P3).

## Corte en tres capas

| Capa | Quién | Dónde |
|---|---|---|
| nativo → `Row` | este componente | `src/to_row.cpp` |
| `Row` → bytes | `libs/correlation-v1` | `serialize()` |
| bytes → disco | este componente | `src/batch_writer.cpp` |

`to_row` es **pura**: sin fichero, sin reloj, sin red. Todo el I/O vive en
`main.cpp` y `batch_writer.cpp`. Por eso el test no necesita montar nada.

## Uso

```sh
export ARGUS_BRONZE_HMAC_KEY_HEX=<64 chars hex>
@@NS@@ config/@@SENSOR@@_adapter.json [entrada.json]
```

Escribe `<base_dir>/@@SENSOR@@-%Y-%m-%d-%H%M%S.csv` de forma atómica (`.tmp` → rename).
Sale con código 1 si no escribió ninguna fila: cero filas es un fallo, no un éxito
silencioso.

## Invariantes que este componente NO puede romper

- **Nunca reimplementar `validate()`, el HMAC ni el formato CSV.** Si hiciera falta
  cambiar los bytes, se cambia la librería y se enteran los cinco productores.
- **Descarte explícito y ruidoso** (D5). Un `Skip` silencioso es indistinguible de
  un bug; por eso `Skip` lleva motivo y `main` imprime los contadores.
- **`node_id` es el punto de observación** (D2), no el host. Viene de la config.
- **Los 3 scores quedan a `0.0`** = ausencia documentada (D6). El consumidor filtra
  por `source_sensor`.

## Deudas conocidas que le afectan

- `DEBT-SNIFFER-IP-BYTE-ORDER-001` — hasta que se arregle, el `community_id` de
  aRGus está corrupto y **estas filas no convergen con las suyas** aunque ambas
  sean correctas por separado.
- Guard **D-D** diferido: cuando se active, `"@@SENSOR@@"` tendrá que ser un símbolo
  `DetectorSource` legal o `validate()` empezará a rechazar estas filas.

## Estándar

Este layout es el estándar de todos los adapters. El de aRGus vive hoy incrustado
en `ml-detector/src/correlation_writer.cpp` (`to_correlation_v1_row`) y debe salir
de ahí, en su propia refactorización, para cumplirlo. Generado con:

```sh
python3 tools/scaffold_adapter.py --sensor @@SENSOR@@
```
'''

# ---------------------------------------------------------------------------

GITIGNORE_NOTE = """# /vagrant es carpeta COMPARTIDA entre VMs, asi que cada una construye en su
# propio directorio con sufijo (build-suricata, build-defender...). El patron
# tiene que cubrirlos todos, no solo `build/`.
build*/
"""

# Sensores con mapeo escrito. El resto recibe el stub.
IMPLEMENTED = {"suricata": TO_ROW_CPP_SURICATA}


def build_files(sensor: str) -> dict[str, str]:
    to_row_cpp = IMPLEMENTED.get(sensor, TO_ROW_CPP_STUB)
    ns = f"{sensor}_adapter"
    comp = f"{sensor}-adapter"

    raw = {
        f"{comp}/CMakeLists.txt": CMAKELISTS,
        f"{comp}/README.md": README,
        f"{comp}/.gitignore": GITIGNORE_NOTE,
        f"{comp}/config/{sensor}_adapter.json": CONFIG_JSON,
        f"{comp}/include/{ns}/to_row.hpp": TO_ROW_HPP,
        f"{comp}/include/{ns}/batch_writer.hpp": BATCH_WRITER_HPP,
        f"{comp}/include/{ns}/config.hpp": CONFIG_HPP,
        f"{comp}/src/to_row.cpp": to_row_cpp,
        f"{comp}/src/batch_writer.cpp": BATCH_WRITER_CPP,
        f"{comp}/src/config.cpp": CONFIG_CPP,
        f"{comp}/src/main.cpp": MAIN_CPP,
        f"{comp}/tests/CMakeLists.txt": TESTS_CMAKELISTS,
        f"{comp}/tests/test_to_row.cpp": TEST_CPP,
    }

    out = {}
    for path, body in raw.items():
        text = (body.replace("@@SENSOR@@", sensor)
                .replace("@@NS@@", ns)
                .replace("@@DIR@@", comp)
                .replace("@@GUARD@@", ns.upper()))
        out[path] = text
    return out


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Genera el andamiaje estandar de un adapter correlation_v1.")
    ap.add_argument("--sensor", required=True,
                    help="nombre del sensor en minusculas: suricata, zeek, wazuh, argus")
    ap.add_argument("--root", default=".",
                    help="raiz del repositorio (por defecto: el directorio actual)")
    ap.add_argument("--force", action="store_true",
                    help="sobrescribe ficheros existentes (por defecto NO los toca)")
    ap.add_argument("--dry-run", action="store_true",
                    help="solo imprime lo que haria")
    args = ap.parse_args()

    sensor = args.sensor.strip().lower()
    if not sensor.isalnum():
        print(f"[ERROR] nombre de sensor no valido: {args.sensor!r} "
              f"(solo alfanumerico, en minusculas)", file=sys.stderr)
        return 2

    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"[ERROR] la raiz no existe: {root}", file=sys.stderr)
        return 2

    files = build_files(sensor)

    created, skipped, overwritten = [], [], []
    for rel, content in sorted(files.items()):
        target = root / rel
        exists = target.exists()

        if exists and not args.force:
            skipped.append(rel)
            continue

        if args.dry_run:
            (overwritten if exists else created).append(rel)
            continue

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        (overwritten if exists else created).append(rel)

    prefix = "[dry-run] " if args.dry_run else ""
    for rel in created:
        print(f"{prefix}creado      {rel}")
    for rel in overwritten:
        print(f"{prefix}SOBRESCRITO {rel}")
    for rel in skipped:
        print(f"          ya existe, intacto: {rel}  (usa --force para pisarlo)")

    if sensor not in IMPLEMENTED:
        print(f"\n🔴 '{sensor}' no tiene mapeo escrito: src/to_row.cpp es un stub que "
              f"devuelve Error.\n   Mide primero que emite el sensor de verdad "
              f"(tools/eval/eve_field_coverage.py como plantilla).")

    print(f"""
--- PASOS MANUALES, no los hace este script ---

1. Anadir al CMakeLists.txt raiz:      add_subdirectory({sensor}-adapter)

2. VERIFICAR {sensor}-adapter/CMakeLists.txt contra ml-detector/CMakeLists.txt.
   El patron del repo NO se midio (DAY 226): version minima de CMake, flags,
   y sobre todo COMO se localiza el parser JSON. Suposicion usada: nlohmann_json.
       git grep -n 'nlohmann\\|rapidjson\\|simdjson' -- ml-detector/CMakeLists.txt
   Si es otro, se reescribe src/to_row.cpp y nada mas (el JSON esta confinado ahi).

3. Sustituir la linea SINTETICA de tests/test_to_row.cpp por una real:
       grep -m1 '"event_type":"alert"' logs/day225-{sensor}-neris/eve.json

4. Rama ANTES del primer git add, y git add explicito por fichero.
""")
    return 0
#!/usr/bin/env python3
"""scaffold_adapter.py — andamiaje estándar de un adapter del contrato bronce correlation_v1.

aRGus NDR — DAY 226.

Crea la estructura de un componente de primer nivel `<sensor>-adapter/` que traduce
la salida nativa de un sensor a filas del contrato bronce (19 columnas) reutilizando
`libs/correlation-v1` para serialize/HMAC/validate. NUNCA reimplementa el contrato.

Corte en tres capas (correlation_v1.hpp, DAY 185):
    [nativo -> Row]   to_row()          <- ESTE COMPONENTE, uno por sensor
    [Row -> bytes]    serialize()       <- libs/correlation-v1, notario único (P3)
    [bytes -> disco]  BatchWriter       <- ESTE COMPONENTE (CorrelationWriter vive
                                           en ml-detector y arrastra protobuf)

Uso:
    python3 tools/scaffold_adapter.py --sensor suricata
    python3 tools/scaffold_adapter.py --sensor suricata --root . --force
    python3 tools/scaffold_adapter.py --sensor zeek --dry-run

Sensores con mapeo escrito: suricata.
Cualquier otro nombre genera el mismo andamiaje con un `to_row` que devuelve Error
("no implementado") — compila y el test falla RUIDOSAMENTE, que es lo que queremos.

Idempotente por defecto: no pisa ficheros existentes salvo --force.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Plantillas. Marcadores: @@SENSOR@@ (suricata), @@NS@@ (suricata_adapter),
# @@DIR@@ (suricata-adapter), @@GUARD@@ (SURICATA_ADAPTER)
# ---------------------------------------------------------------------------

CMAKELISTS = r'''# @@DIR@@/CMakeLists.txt
# aRGus NDR — adapter del contrato bronce correlation_v1 para @@SENSOR@@.
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
# ⚠️ PASO MANUAL: añadir `add_subdirectory(@@DIR@@)` al CMakeLists.txt raíz, DESPUÉS
#    del de libs/correlation-v1 — este componente depende de él.

cmake_minimum_required(VERSION 3.16)

# ¿Build suelto de este componente o incluido desde el raíz? Se detecta comparando
# rutas: `if(NOT DEFINED PROJECT_NAME)` no sirve, PROJECT_NAME siempre está definido
# en cuanto alguien llamó a project() más arriba.
set(@@GUARD@@_STANDALONE OFF)
if(CMAKE_SOURCE_DIR STREQUAL CMAKE_CURRENT_SOURCE_DIR)
    set(@@GUARD@@_STANDALONE ON)
    project(@@NS@@ LANGUAGES CXX)
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
    set(@@GUARD@@_JSON_TARGET nlohmann_json::nlohmann_json)
else()
    set(@@GUARD@@_JSON_TARGET nlohmann_json)
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
            "add_subdirectory(libs/correlation-v1) ANTES de add_subdirectory(@@DIR@@) "
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
    set(@@GUARD@@_SODIUM_TARGET PkgConfig::SODIUM)
else()
    find_path(SODIUM_INCLUDE_DIR sodium.h)
    find_library(SODIUM_LIBRARY NAMES sodium libsodium)
    if(SODIUM_INCLUDE_DIR AND SODIUM_LIBRARY)
        message(STATUS "Found libsodium: ${SODIUM_LIBRARY}")
        add_library(@@NS@@_sodium INTERFACE)
        target_include_directories(@@NS@@_sodium INTERFACE ${SODIUM_INCLUDE_DIR})
        target_link_libraries(@@NS@@_sodium INTERFACE ${SODIUM_LIBRARY})
        set(@@GUARD@@_SODIUM_TARGET @@NS@@_sodium)
    else()
        message(FATAL_ERROR
            "libsodium not found. Install: brew install libsodium  /  "
            "sudo apt-get install libsodium-dev")
    endif()
endif()

# --- Biblioteca del adapter (pura, testeable sin I/O) ----------------------
add_library(@@NS@@_lib
    src/to_row.cpp
    src/batch_writer.cpp
    src/config.cpp
)

target_include_directories(@@NS@@_lib
    PUBLIC
        ${CMAKE_CURRENT_SOURCE_DIR}/include
)

# correlation_v1 es PUBLIC: to_row.hpp incluye correlation_v1/correlation_v1.hpp y
# expone CorrelationV1Row en su interfaz. nlohmann y libsodium son PRIVATE: solo
# aparecen dentro de los .cpp, nunca en las cabeceras del componente. Mantenerlo así
# es lo que permite cambiar de parser JSON tocando un solo fichero.
target_link_libraries(@@NS@@_lib
    PUBLIC
        correlation_v1
    PRIVATE
        ${@@GUARD@@_JSON_TARGET}
        ${@@GUARD@@_SODIUM_TARGET}
)

target_compile_options(@@NS@@_lib PRIVATE
    -Wall -Wextra -Wpedantic -Werror
)

# --- Ejecutable ------------------------------------------------------------
add_executable(@@NS@@ src/main.cpp)

# main.cpp llama a sodium_init(), así que necesita libsodium por su cuenta: en la
# biblioteca es PRIVATE y no se propaga.
target_link_libraries(@@NS@@ PRIVATE
    @@NS@@_lib
    ${@@GUARD@@_SODIUM_TARGET}
)
target_compile_options(@@NS@@ PRIVATE -Wall -Wextra -Wpedantic -Werror)

# --- Tests -----------------------------------------------------------------
# enable_testing() solo si se construye suelto; si venimos del raíz, ya lo llamó él
# (llamarlo dos veces no rompe, pero deja la raíz de CTest en el sitio equivocado).
if(@@GUARD@@_STANDALONE)
    enable_testing()
endif()
add_subdirectory(tests)

# --- Resumen (mismo estilo que ml-detector/CMakeLists.txt:529) --------------
message(STATUS "")
message(STATUS "--- @@DIR@@ ---")
message(STATUS "  C++ standard:    ${CMAKE_CXX_STANDARD}")
message(STATUS "  correlation_v1:  target disponible")
message(STATUS "  nlohmann/json:   ${@@GUARD@@_JSON_TARGET}")
message(STATUS "  libsodium:       ${@@GUARD@@_SODIUM_TARGET}")
message(STATUS "  standalone:      ${@@GUARD@@_STANDALONE}")
message(STATUS "")
'''

TESTS_CMAKELISTS = r'''# @@DIR@@/tests/CMakeLists.txt
#
# Sin framework de terceros a propósito: un main() con asserts que ctest ejecuta.
# El repo usa ctest (`make correlation-engine-test`); qué framework usa por dentro
# NO se ha medido (DAY 226). Si es GoogleTest y prefieres alinear, cámbialo aquí.

add_executable(test_to_row test_to_row.cpp)
target_link_libraries(test_to_row PRIVATE @@NS@@_lib)
target_compile_options(test_to_row PRIVATE -Wall -Wextra -Wpedantic -Werror)

add_test(NAME @@NS@@_to_row COMMAND test_to_row)
'''

TO_ROW_HPP = r'''// @@DIR@@/include/@@NS@@/to_row.hpp
// aRGus NDR — @@SENSOR@@ -> CorrelationV1Row. Capa PURA del adapter.
//
// ESPEJO de ml-detector/src/correlation_writer.cpp::to_correlation_v1_row (el ORÁCULO).
// Misma forma, misma semántica de tres estados. Lo que cambia es la fuente de datos.
//
// PURA: sin fichero, sin reloj, sin red, sin fetch de clave. Eso permite que el test
// le pase una línea literal y compruebe el Row campo a campo sin montar nada.
#pragma once

#include <string>

#include <correlation_v1/correlation_v1.hpp>

namespace @@NS@@ {

// Constantes del contrato para este productor.
// D-C (correlation_v1.hpp): schema_version y source_sensor son CAMPOS del Row,
// no constantes de la librería. Cada adapter fija los suyos.
inline constexpr const char* SCHEMA_VERSION           = "1";
inline constexpr const char* CORRELATION_SOURCE_SENSOR = "@@SENSOR@@";

// Col 17. ⚠️ El guard D-D está DIFERIDO en validate() v1: hoy NO se exige que este
// símbolo sea un DetectorSource legal. Cuando se active (commit de contrato),
// "@@SENSOR@@" tendrá que ser símbolo legal o estas filas empezarán a rechazarse.
inline constexpr const char* AUTHORITATIVE_SOURCE      = "@@SENSOR@@";

// Prefijo del event_id (D3): espacio de nombres propio, sin colisión con aRGus.
inline constexpr const char* EVENT_ID_PREFIX           = "@@SENSOR@@:";

// ---------------------------------------------------------------------------
// Resultado de tres estados. NO se reutiliza ml-detector::ToRowResult porque
// arrastra protobuf; se IMITA exactamente para que D5 (descarte explícito) sea
// el mismo mecanismo que ya usa aRGus, no una convención nueva de este adapter.
//
//   Ok    -> hay fila
//   Skip  -> descarte LEGÍTIMO (no es pérdida). Sin línea y sin fallo, pero con
//            motivo, para el contador ruidoso de D5.
//   Error -> bug del productor. Ruidoso.
// ---------------------------------------------------------------------------
struct [[nodiscard]] ToRowResult {
    enum class Status { Ok, Skip, Error };

    Status status = Status::Error;
    correlation_v1::CorrelationV1Row row{};
    std::string reason;   // motivo del Skip o diagnóstico del Error; vacío si Ok

    static ToRowResult ok(correlation_v1::CorrelationV1Row r);
    static ToRowResult skip(std::string why);
    static ToRowResult error(std::string what);
};

// ---------------------------------------------------------------------------
// to_row — una línea de la salida nativa de @@SENSOR@@ -> Row.
//
// node_id: punto de OBSERVACIÓN (D2), no el host que ejecuta el sensor. Viene de
// la config; dos sensores con el mismo node_id declaran que observan lo mismo.
// ---------------------------------------------------------------------------
[[nodiscard]] ToRowResult to_row(const std::string& line, const std::string& node_id);

// Expuesta para el test: "2011-08-10T09:04:32.432327+0000" -> (secs, nanos).
// Respeta el offset DEL EVENTO, no el de la máquina que ejecuta el adapter.
[[nodiscard]] bool parse_iso8601(const std::string& ts, int64_t& secs, int32_t& nanos);

// Expuesta para el test: event_id determinista (D3).
[[nodiscard]] std::string make_event_id(const std::string& timestamp,
                                        const std::string& flow_id,
                                        const std::string& signature_id,
                                        const std::string& community_id);

}  // namespace @@NS@@
'''

TO_ROW_CPP_SURICATA = r'''// @@DIR@@/src/to_row.cpp
// aRGus NDR — eve.json (Suricata) -> CorrelationV1Row.
//
// ⚠️ ÚNICO FICHERO DEL COMPONENTE QUE TOCA JSON. Es deliberado: si el repo no usa
//    nlohmann sino rapidjson/simdjson, se reescribe este fichero y nada más.
//
// Decisiones aplicadas (docs/design/multisensor-graph-identity/puerta-diseno-multisensor.md):
//   D3  event_id = "suricata:" + base64(BLAKE2b-256(timestamp ‖ flow_id ‖ sid ‖ community_id))
//   D5  descarte explícito con motivo (stats, decoder sin flujo, telemetría)
//   D6  los 3 scores quedan a 0.0 = ausencia documentada; el consumidor filtra por
//       source_sensor. Los de TEXTO sí se mapean:
//         final_classification <- alert.signature
//         threat_category      <- alert.category
//       alert.severity SE PIERDE (ordinal 1-3, no probabilidad). Rederivable desde
//       la signature.

#include "@@NS@@/to_row.hpp"

#include <cstring>
#include <ctime>
#include <string>

#include <nlohmann/json.hpp>
#include <sodium.h>

namespace @@NS@@ {

namespace {

// Separador de campos en la preimagen del event_id. Marca de campo no imprimible
// para que la concatenación sea inyectiva ante valores con caracteres raros.
// ⚠️ DECISIÓN NO RATIFICADA (DAY 226): la puerta de diseño dice "timestamp ‖ flow_id ‖
//    signature_id ‖ community_id" sin fijar la codificación. flow_uid.hpp usa
//    length-prefix canónico; aquí se usa separador. Unificar o documentar la diferencia.
constexpr char kFieldSep = '\x1f';

std::string json_str(const nlohmann::json& j, const char* key) {
    auto it = j.find(key);
    if (it == j.end() || it->is_null()) return {};
    if (it->is_string()) return it->get<std::string>();
    return it->dump();  // números (flow_id, signature_id) -> su representación
}

}  // namespace

// ---------------------------------------------------------------------------
ToRowResult ToRowResult::ok(correlation_v1::CorrelationV1Row r) {
    ToRowResult t;
    t.status = Status::Ok;
    t.row = std::move(r);
    return t;
}

ToRowResult ToRowResult::skip(std::string why) {
    ToRowResult t;
    t.status = Status::Skip;
    t.reason = std::move(why);
    return t;
}

ToRowResult ToRowResult::error(std::string what) {
    ToRowResult t;
    t.status = Status::Error;
    t.reason = std::move(what);
    return t;
}

// ---------------------------------------------------------------------------
// parse_iso8601 — "2011-08-10T09:04:32.432327+0000" (formato MEDIDO en DAY 225).
// Tolera 'Z', offset con y sin dos puntos, y fracción de 0 a 9 dígitos.
// ---------------------------------------------------------------------------
bool parse_iso8601(const std::string& ts, int64_t& secs, int32_t& nanos) {
    if (ts.size() < 19) return false;

    std::tm tm{};
    const char* rest = strptime(ts.c_str(), "%Y-%m-%dT%H:%M:%S", &tm);
    if (rest == nullptr) return false;

    // Fracción de segundo.
    int64_t frac_ns = 0;
    if (*rest == '.') {
        ++rest;
        int digits = 0;
        int64_t value = 0;
        while (digits < 9 && *rest >= '0' && *rest <= '9') {
            value = value * 10 + (*rest - '0');
            ++digits;
            ++rest;
        }
        while (*rest >= '0' && *rest <= '9') ++rest;  // exceso: se descarta
        for (int i = digits; i < 9; ++i) value *= 10;
        frac_ns = value;
    }

    // Offset del EVENTO (no el de esta máquina).
    int64_t offset_sec = 0;
    if (*rest == '+' || *rest == '-') {
        const int sign = (*rest == '-') ? -1 : 1;
        ++rest;
        if (std::strlen(rest) < 4) return false;
        const int hh = (rest[0] - '0') * 10 + (rest[1] - '0');
        const int mm_off = (rest[2] == ':') ? (rest[3] - '0') * 10 + (rest[4] - '0')
                                            : (rest[2] - '0') * 10 + (rest[3] - '0');
        offset_sec = sign * (hh * 3600 + mm_off * 60);
    } else if (*rest != 'Z' && *rest != '\0') {
        return false;
    }

    const time_t utc = timegm(&tm);          // interpreta tm como UTC
    secs  = static_cast<int64_t>(utc) - offset_sec;
    nanos = static_cast<int32_t>(frac_ns);
    return true;
}

// ---------------------------------------------------------------------------
// make_event_id — D3. Determinista: el mismo eve.json da el mismo event_id en
// cada replay, así que reprocesar no duplica nodos en el grafo.
// NO usa pcap_cnt (existe en replay offline, no garantizado en vivo).
// ---------------------------------------------------------------------------
std::string make_event_id(const std::string& timestamp,
                          const std::string& flow_id,
                          const std::string& signature_id,
                          const std::string& community_id) {
    std::string preimage;
    preimage.reserve(timestamp.size() + flow_id.size() +
                     signature_id.size() + community_id.size() + 3);
    preimage.append(timestamp);    preimage.push_back(kFieldSep);
    preimage.append(flow_id);      preimage.push_back(kFieldSep);
    preimage.append(signature_id); preimage.push_back(kFieldSep);
    preimage.append(community_id);

    unsigned char digest[32];
    crypto_generichash(digest, sizeof(digest),
                       reinterpret_cast<const unsigned char*>(preimage.data()),
                       preimage.size(), nullptr, 0);

    char b64[sodium_base64_ENCODED_LEN(sizeof(digest), sodium_base64_VARIANT_ORIGINAL)];
    sodium_bin2base64(b64, sizeof(b64), digest, sizeof(digest),
                      sodium_base64_VARIANT_ORIGINAL);

    return std::string(EVENT_ID_PREFIX) + b64;
}

// ---------------------------------------------------------------------------
// to_row
// ---------------------------------------------------------------------------
ToRowResult to_row(const std::string& line, const std::string& node_id) {
    if (line.empty()) return ToRowResult::skip("linea vacia");

    nlohmann::json j;
    try {
        j = nlohmann::json::parse(line);
    } catch (const nlohmann::json::parse_error& e) {
        return ToRowResult::error(std::string("json ilegible: ") + e.what());
    }

    const std::string event_type = json_str(j, "event_type");

    // D5 — descarte explícito. `stats` no es un evento de red (medido DAY 225: 2
    // eventos, sin community_id ni flow_id).
    if (event_type == "stats") return ToRowResult::skip("event_type=stats");

    // Hoy solo alertas. La telemetría (dns/http/tls/... = 98,7% del volumen) trae
    // community_id pero flow.start = 0 en los NUEVE tipos (medido DAY 225): cuelga
    // de la conversación por community_id (D4) y necesita su propia ruta.
    if (event_type != "alert") return ToRowResult::skip("event_type=" + event_type);

    // D-F / D5 — sin community_id no hay identidad. Mismo SKIP que el oráculo.
    // (validate() lo rechazaría igual: la política está reforzada por el contrato.)
    const std::string community_id = json_str(j, "community_id");
    if (community_id.empty()) {
        return ToRowResult::skip("sin community_id (decoder sin flujo)");
    }

    // flow.start — MEDIDO DAY 225: presente en 2.870 de 2.872 alertas. NO usar el
    // `timestamp` del evento: en una alerta es la hora de la alerta, no del flujo.
    const auto flow_it = j.find("flow");
    if (flow_it == j.end()) return ToRowResult::skip("alerta sin objeto flow");

    const std::string flow_start = json_str(*flow_it, "start");
    int64_t secs = 0;
    int32_t nanos = 0;
    if (flow_start.empty() || !parse_iso8601(flow_start, secs, nanos)) {
        return ToRowResult::error("flow.start no parseable: " + flow_start);
    }

    const auto alert_it = j.find("alert");
    if (alert_it == j.end()) return ToRowResult::error("event_type=alert sin objeto alert");

    correlation_v1::CorrelationV1Row r;
    r.schema_version  = SCHEMA_VERSION;                                    // 0
    r.source_sensor   = CORRELATION_SOURCE_SENSOR;                         // 1
    r.event_id        = make_event_id(json_str(j, "timestamp"),            // 2
                                      json_str(j, "flow_id"),
                                      json_str(*alert_it, "signature_id"),
                                      community_id);
    r.node_id         = node_id;                                           // 3
    r.community_id    = community_id;                                      // 4
    r.flow_start_sec  = secs;                                              // 5
    r.flow_start_nano = nanos;                                             // 6
    // Cols 7-10 — DEL OBJETO `flow`, NO del nivel superior. MEDIDO DAY 226 sobre
    // las 2.872 alertas del Neris: 2.870 traen flow.src_ip (las 2 que no son
    // exactamente las de decoder, ya descartadas arriba) y **2.853 de 2.870 (99,4%)
    // están INVERTIDAS respecto al nivel superior**.
    //
    // Por qué: el par de nivel superior es el del PAQUETE que disparó la alerta y
    // depende de `direction`; el de `flow` es el del ORIGINADOR del flujo. Copiar el
    // de arriba dejaría src/dst intercambiados entre alertas del MISMO community_id,
    // y con D1 el nodo del grafo ES la conversación.
    //
    // El fallback al nivel superior no se dispara en la práctica; existe para no
    // depender de que `flow` traiga siempre estos campos en otras versiones/capturas.
    const nlohmann::json& ep = flow_it->contains("src_ip") ? *flow_it : j;

    r.src_ip          = json_str(ep, "src_ip");                            // 7
    r.dst_ip          = json_str(ep, "dest_ip");                           // 8
    r.src_port        = ep.value("src_port", 0u);                          // 9
    r.dst_port        = ep.value("dest_port", 0u);                         // 10
    r.protocol        = json_str(j, "proto");                              // 11  (solo nivel superior)

    // D6 — el veredicto propio de Suricata va a los campos de TEXTO. Dejarlos
    // vacíos tiraría a la basura el valor de integrar Suricata.
    r.final_classification = json_str(*alert_it, "signature");             // 12
    r.threat_category      = json_str(*alert_it, "category");              // 13

    // D6 — los 3 scores son `double`: "vacío" NO es representable. Quedan a 0.0
    // como AUSENCIA DOCUMENTADA. El consumidor filtra SIEMPRE por source_sensor.
    // (Opción C, NaN, era la semánticamente correcta; descartada por round-trip
    // sin probar en CSV/Parquet/Kuzu.)
    r.fast_detector_score  = 0.0;                                          // 14
    r.ml_detector_score    = 0.0;                                          // 15
    r.overall_threat_score = 0.0;                                          // 16

    r.authoritative_source = AUTHORITATIVE_SOURCE;                         // 17
    // col 18 (HMAC) la calcula serialize(); no vive en el Row.

    return ToRowResult::ok(std::move(r));
}

}  // namespace @@NS@@
'''

TO_ROW_CPP_STUB = r'''// @@DIR@@/src/to_row.cpp
// aRGus NDR — @@SENSOR@@ -> CorrelationV1Row.
//
// 🔴 NO IMPLEMENTADO. Andamiaje generado por tools/scaffold_adapter.py.
//
// Devuelve Error a propósito: compila, y el test falla RUIDOSAMENTE. Un stub que
// devolviera Skip mentiría (parecería un descarte legítimo) y un stub que devolviera
// Ok con un Row vacío sería peor todavía: validate() lo rechazaría por community_id
// vacío y el fallo aparecería tres capas más abajo.
//
// Antes de escribirlo, MEDIR contra fichero (nunca contra memoria) qué emite este
// sensor de verdad: qué tipos de evento, cuáles traen community_id, cuáles traen
// inicio de flujo. Ver tools/eval/eve_field_coverage.py como plantilla.

#include "@@NS@@/to_row.hpp"

namespace @@NS@@ {

ToRowResult ToRowResult::ok(correlation_v1::CorrelationV1Row r) {
    ToRowResult t;
    t.status = Status::Ok;
    t.row = std::move(r);
    return t;
}

ToRowResult ToRowResult::skip(std::string why) {
    ToRowResult t;
    t.status = Status::Skip;
    t.reason = std::move(why);
    return t;
}

ToRowResult ToRowResult::error(std::string what) {
    ToRowResult t;
    t.status = Status::Error;
    t.reason = std::move(what);
    return t;
}

bool parse_iso8601(const std::string&, int64_t&, int32_t&) {
    return false;
}

std::string make_event_id(const std::string&, const std::string&,
                          const std::string&, const std::string&) {
    return {};
}

ToRowResult to_row(const std::string&, const std::string&) {
    return ToRowResult::error("to_row de @@SENSOR@@ no implementado");
}

}  // namespace @@NS@@
'''

BATCH_WRITER_HPP = r'''// @@DIR@@/include/@@NS@@/batch_writer.hpp
// aRGus NDR — capa [bytes -> disco] del adapter.
//
// POR QUÉ NO SE REUTILIZA CorrelationWriter: vive en ml-detector y arrastra protobuf
// (correlation_v1.hpp, corte en tres capas). Y su complejidad —rotación por tiempo
// absoluto, mutex, reloj— existe para un productor CONTINUO. Este adapter es de LOTE:
// un fichero por ejecución. Copiar aquella máquina sería complejidad sin demanda.
//
// Lo que SÍ se copia es lo que importa: escritura atómica .tmp -> rename, para que
// ningún consumidor vea jamás un fichero a medio escribir.
#pragma once

#include <cstdint>
#include <fstream>
#include <string>

namespace @@NS@@ {

class BatchWriter {
public:
    BatchWriter(std::string base_dir, std::string source_sensor);
    ~BatchWriter();

    BatchWriter(const BatchWriter&) = delete;
    BatchWriter& operator=(const BatchWriter&) = delete;

    // Abre <base_dir>/<source_sensor>-%Y-%m-%d-%H%M%S.csv.tmp
    [[nodiscard]] bool open();

    // Escribe una línea ya serializada por libs/correlation-v1 (cols 0-18).
    [[nodiscard]] bool write_line(const std::string& line);

    // Cierra y RENOMBRA .tmp -> definitivo. Hasta aquí el fichero no existe
    // para nadie. Si no se llama, el .tmp se queda: fallo visible, no silencioso.
    [[nodiscard]] bool close();

    uint64_t lines_written() const noexcept { return lines_written_; }
    const std::string& tmp_path()   const noexcept { return tmp_path_; }
    const std::string& final_path() const noexcept { return final_path_; }

private:
    std::string base_dir_;
    std::string source_sensor_;
    std::string tmp_path_;
    std::string final_path_;
    std::ofstream out_;
    uint64_t lines_written_ = 0;
};

}  // namespace @@NS@@
'''

BATCH_WRITER_CPP = r'''// @@DIR@@/src/batch_writer.cpp

#include "@@NS@@/batch_writer.hpp"

#include <cstdio>
#include <ctime>
#include <utility>

namespace @@NS@@ {

BatchWriter::BatchWriter(std::string base_dir, std::string source_sensor)
    : base_dir_(std::move(base_dir)), source_sensor_(std::move(source_sensor)) {}

BatchWriter::~BatchWriter() {
    if (out_.is_open()) out_.close();   // .tmp sin renombrar = fallo visible
}

bool BatchWriter::open() {
    if (out_.is_open()) return false;

    // Basename idéntico en forma al del oráculo: <sensor>-%Y-%m-%d-%H%M%S.csv
    // Este es el ÚNICO uso del reloj en todo el componente; to_row es puro.
    const std::time_t now = std::time(nullptr);
    std::tm tm{};
    localtime_r(&now, &tm);
    char stamp[32];
    std::strftime(stamp, sizeof(stamp), "%Y-%m-%d-%H%M%S", &tm);

    final_path_ = base_dir_ + "/" + source_sensor_ + "-" + stamp + ".csv";
    tmp_path_   = final_path_ + ".tmp";

    out_.open(tmp_path_, std::ios::out | std::ios::trunc);
    return out_.is_open();
}

bool BatchWriter::write_line(const std::string& line) {
    if (!out_.is_open()) return false;
    out_ << line << "\n";               // sin cabecera: el bronce no la tiene
    if (!out_) return false;
    ++lines_written_;
    return true;
}

bool BatchWriter::close() {
    if (!out_.is_open()) return false;
    out_.flush();
    const bool stream_ok = static_cast<bool>(out_);
    out_.close();
    if (!stream_ok) return false;
    return std::rename(tmp_path_.c_str(), final_path_.c_str()) == 0;
}

}  // namespace @@NS@@
'''

CONFIG_HPP = r'''// @@DIR@@/include/@@NS@@/config.hpp
// aRGus NDR — configuración del adapter de @@SENSOR@@.
#pragma once

#include <string>

namespace @@NS@@ {

struct Config {
    // Buzón PLANO del bronce, compartido con el resto de productores.
    std::string base_dir = "/vagrant/logs/correlation";

    // D2 — punto de OBSERVACIÓN, no el host. Dos sensores con el mismo node_id
    // declaran que observan la misma interfaz; si observan interfaces distintas es
    // CORRECTO que generen subgrafos distintos.
    //
    // ⚠️ MEDIDO DAY 226: el node_id real que emite aRGus hoy es "cpp_sniffer_v33_day12",
    //    una etiqueta de VERSIÓN del sniffer. Para converger hay que poner aquí ese
    //    mismo valor. Es incorrecto semánticamente y está registrado como deuda.
    std::string node_id;

    // Entrada: eve.json (JSONL) a procesar en lote.
    std::string input_path;

    // Clave HMAC de 64 chars hex -> 32 bytes.
    // ⚠️ DEBE SER LA MISMA QUE USA aRGus o el lector de aguas abajo rechazará estas
    //    filas. correlation_v1.hpp dice: "ARGUS_BRONZE_HMAC_KEY_HEX en test,
    //    etcd-server en el adapter". Hoy: variable de entorno.
    std::string hmac_key_env = "ARGUS_BRONZE_HMAC_KEY_HEX";
};

// Carga desde JSON. Devuelve false y deja `error` si el fichero falta o es ilegible.
[[nodiscard]] bool load_config(const std::string& path, Config& out, std::string& error);

}  // namespace @@NS@@
'''

CONFIG_CPP = r'''// @@DIR@@/src/config.cpp

#include "@@NS@@/config.hpp"

#include <fstream>

#include <nlohmann/json.hpp>

namespace @@NS@@ {

bool load_config(const std::string& path, Config& out, std::string& error) {
    std::ifstream in(path);
    if (!in) {
        error = "no se puede abrir la config: " + path;
        return false;
    }

    nlohmann::json j;
    try {
        in >> j;
    } catch (const nlohmann::json::parse_error& e) {
        error = std::string("config ilegible: ") + e.what();
        return false;
    }

    out.base_dir     = j.value("base_dir", out.base_dir);
    out.node_id      = j.value("node_id", out.node_id);
    out.input_path   = j.value("input_path", out.input_path);
    out.hmac_key_env = j.value("hmac_key_env", out.hmac_key_env);

    if (out.node_id.empty()) {
        error = "node_id vacio: sin el, las filas no convergen con las de aRGus (D2)";
        return false;
    }
    return true;
}

}  // namespace @@NS@@
'''

CONFIG_JSON = r'''{
  "_comentario": "aRGus NDR — adapter de @@SENSOR@@. DAY 226.",
  "_node_id": "D2: punto de observacion, NO el host. Debe coincidir con el de aRGus para converger. Valor real medido en el bronce de aRGus: cpp_sniffer_v33_day12",
  "_hmac_key_env": "Debe ser la MISMA clave que usa aRGus o el lector rechazara estas filas",

  "base_dir": "/vagrant/logs/correlation",
  "node_id": "cpp_sniffer_v33_day12",
  "input_path": "logs/day225-@@SENSOR@@-neris/eve.json",
  "hmac_key_env": "ARGUS_BRONZE_HMAC_KEY_HEX"
}
'''

MAIN_CPP = r'''// @@DIR@@/src/main.cpp
// aRGus NDR — adapter de @@SENSOR@@, modo LOTE.
//
// Pipeline: linea JSONL -> to_row() -> serialize() -> BatchWriter
//                                      ^^^^^^^^^^^
//                          libs/correlation-v1, notario único (P3).
//                          Lo que validate() rechaza, serialize() NO lo emite.
//
// Contadores RUIDOSOS al final (D5): un descarte silencioso es indistinguible de
// un bug. Si skipped y written no cuadran con lo medido en el eve.json, se ve aquí.

#include <cstdlib>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

#include <sodium.h>

#include <correlation_v1/correlation_v1.hpp>

#include "@@NS@@/batch_writer.hpp"
#include "@@NS@@/config.hpp"
#include "@@NS@@/to_row.hpp"

namespace {

// 64 chars hex -> 32 bytes. La lib recibe la clave YA decodificada (es INPUT puro).
bool hex_to_key(const std::string& hex, std::vector<uint8_t>& out, std::string& error) {
    if (hex.size() != 64) {
        error = "la clave HMAC debe tener 64 chars hex, tiene " + std::to_string(hex.size());
        return false;
    }
    out.assign(32, 0);
    for (size_t i = 0; i < 32; ++i) {
        auto nibble = [&](char c, int& v) {
            if (c >= '0' && c <= '9') { v = c - '0';        return true; }
            if (c >= 'a' && c <= 'f') { v = c - 'a' + 10;   return true; }
            if (c >= 'A' && c <= 'F') { v = c - 'A' + 10;   return true; }
            return false;
        };
        int hi = 0, lo = 0;
        if (!nibble(hex[i * 2], hi) || !nibble(hex[i * 2 + 1], lo)) {
            error = "caracter no hexadecimal en la clave HMAC";
            return false;
        }
        out[i] = static_cast<uint8_t>((hi << 4) | lo);
    }
    return true;
}

}  // namespace

int main(int argc, char** argv) {
    if (sodium_init() < 0) {
        std::cerr << "[FATAL] sodium_init fallo\n";
        return 2;
    }

    if (argc < 2) {
        std::cerr << "uso: @@NS@@ <config.json> [entrada.json]\n";
        return 2;
    }

    @@NS@@::Config cfg;
    std::string error;
    if (!@@NS@@::load_config(argv[1], cfg, error)) {
        std::cerr << "[FATAL] " << error << "\n";
        return 2;
    }
    if (argc >= 3) cfg.input_path = argv[2];

    const char* key_hex = std::getenv(cfg.hmac_key_env.c_str());
    if (key_hex == nullptr) {
        std::cerr << "[FATAL] variable de entorno no definida: " << cfg.hmac_key_env << "\n";
        return 2;
    }
    std::vector<uint8_t> hmac_key;
    if (!hex_to_key(key_hex, hmac_key, error)) {
        std::cerr << "[FATAL] " << error << "\n";
        return 2;
    }

    std::ifstream in(cfg.input_path);
    if (!in) {
        std::cerr << "[FATAL] no se puede abrir la entrada: " << cfg.input_path << "\n";
        return 2;
    }

    @@NS@@::BatchWriter writer(cfg.base_dir, @@NS@@::CORRELATION_SOURCE_SENSOR);
    if (!writer.open()) {
        std::cerr << "[FATAL] no se puede abrir el fichero de salida en " << cfg.base_dir << "\n";
        return 2;
    }

    uint64_t total = 0, written = 0, skipped = 0, to_row_err = 0, serialize_err = 0;
    std::string line;
    while (std::getline(in, line)) {
        ++total;
        auto tr = @@NS@@::to_row(line, cfg.node_id);

        if (tr.status == @@NS@@::ToRowResult::Status::Skip) {
            ++skipped;
            continue;
        }
        if (tr.status == @@NS@@::ToRowResult::Status::Error) {
            ++to_row_err;
            std::cerr << "[WARN] to_row linea " << total << ": " << tr.reason << "\n";
            continue;
        }

        auto sr = correlation_v1::serialize(tr.row, hmac_key);
        if (!sr) {
            ++serialize_err;
            std::cerr << "[WARN] serialize rechazo linea " << total << ": " << sr.error << "\n";
            continue;
        }
        if (!writer.write_line(sr.line)) {
            std::cerr << "[FATAL] fallo de escritura en " << writer.tmp_path() << "\n";
            return 2;
        }
        ++written;
    }

    if (!writer.close()) {
        std::cerr << "[FATAL] fallo al cerrar/renombrar " << writer.tmp_path() << "\n";
        return 2;
    }

    // D5 — contadores ruidosos. Sin esto, un descarte masivo pasaría por exito.
    std::cout << "[" << @@NS@@::CORRELATION_SOURCE_SENSOR << "-adapter]"
              << " leidas="        << total
              << " escritas="      << written
              << " descartadas="   << skipped
              << " err_to_row="    << to_row_err
              << " err_serialize=" << serialize_err
              << "\n salida: "     << writer.final_path() << "\n";

    return (written > 0) ? 0 : 1;   // 0 filas es fallo, no exito silencioso
}
'''

TEST_CPP = r'''// @@DIR@@/tests/test_to_row.cpp
// aRGus NDR — test de la capa PURA del adapter de @@SENSOR@@.
//
// Sin framework: main() con asserts, ejecutado por ctest. to_row es pura, así que
// el test le da una línea literal y comprueba el Row campo a campo. Sin VM, sin
// fichero, sin reloj.
//
// VECTOR REAL: primera alerta de logs/day225-@@SENSOR@@-neris/eve.json, copiada
// literalmente (DAY 226). Es un "SURICATA TCPv4 invalid checksum", o sea un
// artefacto de la captura (68/1000 checksums invalidos, medido DAY 225), no un
// ataque. Da igual para el test: trae community_id y flow.start, que es lo que
// se comprueba. Pero no sirve de escaparate en el paper.
//
// Reproducir:  grep -m1 '"event_type":"alert"' logs/day225-@@SENSOR@@-neris/eve.json

#include <cassert>
#include <cstdint>
#include <iostream>
#include <string>

#include "@@NS@@/to_row.hpp"

namespace {

const char* kAlertLine = R"({"timestamp":"2011-08-10T09:06:36.150781+0000","flow_id":1180526643469803,"pcap_cnt":126,"event_type":"alert","src_ip":"94.63.149.152","src_port":80,"dest_ip":"147.32.84.165","dest_port":1040,"proto":"TCP","pkt_src":"wire/pcap","community_id":"1:MuSlbWV2Dy5Z168c5sxOWncbYyQ=","alert":{"action":"allowed","gid":1,"signature_id":2200074,"rev":2,"signature":"SURICATA TCPv4 invalid checksum","category":"Generic Protocol Command Decode","severity":3},"app_proto":"http","direction":"to_client","flow":{"pkts_toserver":6,"pkts_toclient":3,"bytes_toserver":532,"bytes_toclient":4556,"start":"2011-08-10T09:06:36.078254+0000","src_ip":"147.32.84.165","dest_ip":"94.63.149.152","src_port":1040,"dest_port":80}})";

int failures = 0;

void check(bool cond, const char* what) {
    if (!cond) {
        std::cerr << "FALLO: " << what << "\n";
        ++failures;
    }
}

void test_parse_iso8601() {
    int64_t secs = 0;
    int32_t nanos = 0;
    check(@@NS@@::parse_iso8601("2011-08-10T09:06:36.078254+0000", secs, nanos),
          "parse_iso8601 acepta el formato medido");
    check(secs == 1312967196, "epoch de 2011-08-10T09:06:36Z");
    check(nanos == 78254000, "micros x 1000 -> nanos (078254 -> 78254000)");

    // El offset es DEL EVENTO: la misma hora de pared con +0200 son 2 h menos de epoch.
    int64_t secs_cest = 0;
    int32_t nanos_cest = 0;
    check(@@NS@@::parse_iso8601("2011-08-10T09:06:36.078254+0200", secs_cest, nanos_cest),
          "parse_iso8601 acepta offset no nulo");
    check(secs_cest == secs - 7200, "el offset del evento se resta");
}

void test_alerta_produce_fila() {
    auto r = @@NS@@::to_row(kAlertLine, "cpp_sniffer_v33_day12");
    check(r.status == @@NS@@::ToRowResult::Status::Ok, "una alerta con community_id da Ok");
    if (r.status != @@NS@@::ToRowResult::Status::Ok) return;

    check(r.row.schema_version == "1",                          "col 0 schema_version");
    check(r.row.source_sensor == "@@SENSOR@@",                  "col 1 source_sensor");
    check(r.row.event_id.rfind("@@SENSOR@@:", 0) == 0,          "col 2 event_id prefijado (D3)");
    check(r.row.node_id == "cpp_sniffer_v33_day12",             "col 3 node_id de la config");
    check(r.row.community_id == "1:MuSlbWV2Dy5Z168c5sxOWncbYyQ=", "col 4 community_id");
    check(r.row.flow_start_sec == 1312967196,                   "col 5 de flow.start (09:06:36), NO del timestamp del evento (09:06:36.150781)");
    check(r.row.flow_start_nano == 78254000,                    "col 6 de flow.start");

    // Cols 7-10 del OBJETO flow (originador), no del nivel superior (paquete).
    // En este vector estan invertidos entre si, como en el 99,4% de las alertas
    // del Neris: si el adapter copiara el nivel superior, aqui saldria
    // 94.63.149.152:80 -> 147.32.84.165:1040. Este test es el que lo impide.
    check(r.row.src_ip == "147.32.84.165",                      "col 7 <- flow.src_ip, no el de nivel superior");
    check(r.row.dst_ip == "94.63.149.152",                      "col 8 <- flow.dest_ip");
    check(r.row.src_port == 1040,                               "col 9 <- flow.src_port");
    check(r.row.dst_port == 80,                                 "col 10 <- flow.dest_port");
    check(r.row.protocol == "TCP",                              "col 11 proto -> protocol");
    check(r.row.final_classification == "SURICATA TCPv4 invalid checksum",
          "col 12 <- alert.signature (D6)");
    check(r.row.threat_category == "Generic Protocol Command Decode",
          "col 13 <- alert.category (D6)");
    check(r.row.fast_detector_score == 0.0,                     "col 14 = 0.0 ausencia (D6)");
    check(r.row.ml_detector_score == 0.0,                       "col 15 = 0.0 ausencia (D6)");
    check(r.row.overall_threat_score == 0.0,                    "col 16 = 0.0 ausencia (D6)");
    check(r.row.authoritative_source == "@@SENSOR@@",           "col 17 authoritative_source");
}

void test_event_id_determinista() {
    auto a = @@NS@@::to_row(kAlertLine, "n1");
    auto b = @@NS@@::to_row(kAlertLine, "n1");
    check(a.status == @@NS@@::ToRowResult::Status::Ok &&
          a.row.event_id == b.row.event_id,
          "D3: la misma linea da el mismo event_id (reprocesar no duplica nodos)");
}

void test_descartes() {
    auto stats = @@NS@@::to_row(R"({"event_type":"stats"})", "n1");
    check(stats.status == @@NS@@::ToRowResult::Status::Skip, "stats se descarta (D5)");

    auto dns = @@NS@@::to_row(R"({"event_type":"dns","community_id":"1:abc="})", "n1");
    check(dns.status == @@NS@@::ToRowResult::Status::Skip, "la telemetria se descarta hoy (D4)");

    auto decoder = @@NS@@::to_row(
        R"({"event_type":"alert","alert":{"signature_id":2200076}})", "n1");
    check(decoder.status == @@NS@@::ToRowResult::Status::Skip,
          "alerta de decoder sin community_id se descarta (D5), no es Error");

    auto basura = @@NS@@::to_row("{esto no es json", "n1");
    check(basura.status == @@NS@@::ToRowResult::Status::Error,
          "json ilegible es Error, no Skip: un Skip lo haria invisible");
}

}  // namespace

int main() {
    test_parse_iso8601();
    test_alerta_produce_fila();
    test_event_id_determinista();
    test_descartes();

    if (failures != 0) {
        std::cerr << failures << " comprobacion(es) fallidas\n";
        return 1;
    }
    std::cout << "OK — capa pura del adapter de @@SENSOR@@\n";
    return 0;
}
'''

README = r'''# @@DIR@@

Adapter del contrato bronce `correlation_v1` para **@@SENSOR@@**.

Traduce la salida nativa del sensor a filas del bronce (19 columnas) y las serializa
con `libs/correlation-v1`. **No reimplementa el contrato**: `validate()` y el HMAC
viven en la librería, que es el notario único (P3).

## Corte en tres capas

| Capa | Quién | Dónde |
|---|---|---|
| nativo → `Row` | este componente | `src/to_row.cpp` |
| `Row` → bytes | `libs/correlation-v1` | `serialize()` |
| bytes → disco | este componente | `src/batch_writer.cpp` |

`to_row` es **pura**: sin fichero, sin reloj, sin red. Todo el I/O vive en
`main.cpp` y `batch_writer.cpp`. Por eso el test no necesita montar nada.

## Uso

```sh
export ARGUS_BRONZE_HMAC_KEY_HEX=<64 chars hex>
@@NS@@ config/@@SENSOR@@_adapter.json [entrada.json]
```

Escribe `<base_dir>/@@SENSOR@@-%Y-%m-%d-%H%M%S.csv` de forma atómica (`.tmp` → rename).
Sale con código 1 si no escribió ninguna fila: cero filas es un fallo, no un éxito
silencioso.

## Invariantes que este componente NO puede romper

- **Nunca reimplementar `validate()`, el HMAC ni el formato CSV.** Si hiciera falta
  cambiar los bytes, se cambia la librería y se enteran los cinco productores.
- **Descarte explícito y ruidoso** (D5). Un `Skip` silencioso es indistinguible de
  un bug; por eso `Skip` lleva motivo y `main` imprime los contadores.
- **`node_id` es el punto de observación** (D2), no el host. Viene de la config.
- **Los 3 scores quedan a `0.0`** = ausencia documentada (D6). El consumidor filtra
  por `source_sensor`.

## Deudas conocidas que le afectan

- `DEBT-SNIFFER-IP-BYTE-ORDER-001` — hasta que se arregle, el `community_id` de
  aRGus está corrupto y **estas filas no convergen con las suyas** aunque ambas
  sean correctas por separado.
- Guard **D-D** diferido: cuando se active, `"@@SENSOR@@"` tendrá que ser un símbolo
  `DetectorSource` legal o `validate()` empezará a rechazar estas filas.

## Estándar

Este layout es el estándar de todos los adapters. El de aRGus vive hoy incrustado
en `ml-detector/src/correlation_writer.cpp` (`to_correlation_v1_row`) y debe salir
de ahí, en su propia refactorización, para cumplirlo. Generado con:

```sh
python3 tools/scaffold_adapter.py --sensor @@SENSOR@@
```
'''

# ---------------------------------------------------------------------------

GITIGNORE_NOTE = """# /vagrant es carpeta COMPARTIDA entre VMs, asi que cada una construye en su
# propio directorio con sufijo (build-suricata, build-defender...). El patron
# tiene que cubrirlos todos, no solo `build/`.
build*/
"""

# Sensores con mapeo escrito. El resto recibe el stub.
IMPLEMENTED = {"suricata": TO_ROW_CPP_SURICATA}


def build_files(sensor: str) -> dict[str, str]:
    to_row_cpp = IMPLEMENTED.get(sensor, TO_ROW_CPP_STUB)
    ns = f"{sensor}_adapter"
    comp = f"{sensor}-adapter"

    raw = {
        f"{comp}/CMakeLists.txt": CMAKELISTS,
        f"{comp}/README.md": README,
        f"{comp}/.gitignore": GITIGNORE_NOTE,
        f"{comp}/config/{sensor}_adapter.json": CONFIG_JSON,
        f"{comp}/include/{ns}/to_row.hpp": TO_ROW_HPP,
        f"{comp}/include/{ns}/batch_writer.hpp": BATCH_WRITER_HPP,
        f"{comp}/include/{ns}/config.hpp": CONFIG_HPP,
        f"{comp}/src/to_row.cpp": to_row_cpp,
        f"{comp}/src/batch_writer.cpp": BATCH_WRITER_CPP,
        f"{comp}/src/config.cpp": CONFIG_CPP,
        f"{comp}/src/main.cpp": MAIN_CPP,
        f"{comp}/tests/CMakeLists.txt": TESTS_CMAKELISTS,
        f"{comp}/tests/test_to_row.cpp": TEST_CPP,
    }

    out = {}
    for path, body in raw.items():
        text = (body.replace("@@SENSOR@@", sensor)
                .replace("@@NS@@", ns)
                .replace("@@DIR@@", comp)
                .replace("@@GUARD@@", ns.upper()))
        out[path] = text
    return out


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Genera el andamiaje estandar de un adapter correlation_v1.")
    ap.add_argument("--sensor", required=True,
                    help="nombre del sensor en minusculas: suricata, zeek, wazuh, argus")
    ap.add_argument("--root", default=".",
                    help="raiz del repositorio (por defecto: el directorio actual)")
    ap.add_argument("--force", action="store_true",
                    help="sobrescribe ficheros existentes (por defecto NO los toca)")
    ap.add_argument("--dry-run", action="store_true",
                    help="solo imprime lo que haria")
    args = ap.parse_args()

    sensor = args.sensor.strip().lower()
    if not sensor.isalnum():
        print(f"[ERROR] nombre de sensor no valido: {args.sensor!r} "
              f"(solo alfanumerico, en minusculas)", file=sys.stderr)
        return 2

    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"[ERROR] la raiz no existe: {root}", file=sys.stderr)
        return 2

    files = build_files(sensor)

    created, skipped, overwritten = [], [], []
    for rel, content in sorted(files.items()):
        target = root / rel
        exists = target.exists()

        if exists and not args.force:
            skipped.append(rel)
            continue

        if args.dry_run:
            (overwritten if exists else created).append(rel)
            continue

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        (overwritten if exists else created).append(rel)

    prefix = "[dry-run] " if args.dry_run else ""
    for rel in created:
        print(f"{prefix}creado      {rel}")
    for rel in overwritten:
        print(f"{prefix}SOBRESCRITO {rel}")
    for rel in skipped:
        print(f"          ya existe, intacto: {rel}  (usa --force para pisarlo)")

    if sensor not in IMPLEMENTED:
        print(f"\n🔴 '{sensor}' no tiene mapeo escrito: src/to_row.cpp es un stub que "
              f"devuelve Error.\n   Mide primero que emite el sensor de verdad "
              f"(tools/eval/eve_field_coverage.py como plantilla).")

    print(f"""
--- PASOS MANUALES, no los hace este script ---

1. Anadir al CMakeLists.txt raiz:      add_subdirectory({sensor}-adapter)

2. VERIFICAR {sensor}-adapter/CMakeLists.txt contra ml-detector/CMakeLists.txt.
   El patron del repo NO se midio (DAY 226): version minima de CMake, flags,
   y sobre todo COMO se localiza el parser JSON. Suposicion usada: nlohmann_json.
       git grep -n 'nlohmann\\|rapidjson\\|simdjson' -- ml-detector/CMakeLists.txt
   Si es otro, se reescribe src/to_row.cpp y nada mas (el JSON esta confinado ahi).

3. Sustituir la linea SINTETICA de tests/test_to_row.cpp por una real:
       grep -m1 '"event_type":"alert"' logs/day225-{sensor}-neris/eve.json

4. Rama ANTES del primer git add, y git add explicito por fichero.
""")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

if __name__ == "__main__":
    raise SystemExit(main())