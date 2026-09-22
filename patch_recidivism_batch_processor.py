#!/usr/bin/env python3
"""patch_recidivism_batch_processor.py -- anade el escalado de castigo por
reincidencia (StrikeState/RecidivismConfig) a BatchProcessor, su carga desde
firewall.json via ConfigLoader, y el test unitario correspondiente.

Toca ocho ficheros, con anclas de texto exacto (falla si no encuentra
exactamente una coincidencia, o si detecta que ya esta aplicado):

  - firewall-acl-agent/include/firewall/batch_processor.hpp
  - firewall-acl-agent/src/core/batch_processor.cpp
  - firewall-acl-agent/config/firewall.json
  - firewall-acl-agent/include/firewall/config_loader.hpp
  - firewall-acl-agent/src/core/config_loader.cpp
  - firewall-acl-agent/CMakeLists.txt (anade el test unitario a TEST_SOURCES
    y registra test_recidivism_e2e como ejecutable standalone LABELS "e2e;root",
    clonando el patron de test_ipset_injection_integration)
  - firewall-acl-agent/src/main.cpp (conversion RecidivismConfigNew ->
    RecidivismConfig + processor.set_recidivism_config(...))

Y CREA (no parchea) dos ficheros nuevos:
  - firewall-acl-agent/tests/unit/test_batch_processor_recidivism.cpp  (unitario, dry_run)
  - firewall-acl-agent/tests/test_recidivism_e2e.cpp                   (aceptacion, root+ipset real)

Uso (desde la raiz del repo, o pasando --root):
  python3 patch_recidivism_batch_processor.py --check
  python3 patch_recidivism_batch_processor.py --dry
  python3 patch_recidivism_batch_processor.py --apply

--check: verifica que cada ancla aparece exactamente una vez (o que el
         parche ya esta aplicado, via el marcador RECIDIVISM-D276). No
         escribe nada.
--dry:   muestra el diff unificado que se aplicaria a cada fichero tocado,
         y el contenido integro de los ficheros de test nuevos. No escribe nada.
--apply: aplica los cambios in-place. Crea <fichero>.orig si no existe ya
         (nunca sobreescribe un .orig existente). Escribe cada test nuevo
         solo si no existe ya.

Ejecucion de los tests (Makefile raiz, ya wired):
  make test-firewall      -> unitario (ctest -LE "e2e", sin root)
  make test-firewall-e2e  -> aceptacion (sudo ... ctest -L "e2e", con root,
                              crea/destruye su propio ipset de prueba)

No compila nada, no toca git, no hace commit -- eso lo hace el usuario.
"""
import argparse
import difflib
import sys
from pathlib import Path

MARKER = "RECIDIVISM-D276"

HPP_REL = "firewall-acl-agent/include/firewall/batch_processor.hpp"
CPP_REL = "firewall-acl-agent/src/core/batch_processor.cpp"
JSON_REL = "firewall-acl-agent/config/firewall.json"
CFG_HPP_REL = "firewall-acl-agent/include/firewall/config_loader.hpp"
CFG_CPP_REL = "firewall-acl-agent/src/core/config_loader.cpp"
CMAKE_REL = "firewall-acl-agent/CMakeLists.txt"
MAIN_REL = "firewall-acl-agent/src/main.cpp"
NEW_TEST_REL = "firewall-acl-agent/tests/unit/test_batch_processor_recidivism.cpp"
NEW_E2E_TEST_REL = "firewall-acl-agent/tests/test_recidivism_e2e.cpp"

# ---------------------------------------------------------------------------
# HPP patches (batch_processor.hpp)
# ---------------------------------------------------------------------------

HPP_STRUCTS_ANCHOR = """namespace mldefender::firewall {

//===----------------------------------------------------------------------===//
// Configuration
//===----------------------------------------------------------------------===//"""

HPP_STRUCTS_REPLACEMENT = f"""namespace mldefender::firewall {{

//===----------------------------------------------------------------------===//
// Recidivism escalation ({MARKER})
//===----------------------------------------------------------------------===//

/// Estado de reincidencia por IP
struct StrikeState {{
    uint32_t strikes{{0}};
    std::chrono::steady_clock::time_point last_seen;
}};

/// Configuracion de escalado de castigo por reincidencia. Vive en firewall,
/// no en los detectores: firewall es la unica fuente de verdad del ipset.
struct RecidivismConfig {{
    bool enabled{{true}};
    /// Duracion en segundos por nivel de reincidencia (indice 0 = 1a vez)
    std::vector<uint32_t> strike_durations_sec{{60, 300, 3600, 86400, 604800}};
    /// A partir de este numero de reincidencias, bloqueo permanente (timeout=0)
    uint32_t permanent_after_strikes{{6}};
    /// Si ha pasado mas de esto sin verla, se resetea el contador de esa IP
    std::chrono::seconds quiet_period_reset{{std::chrono::hours(72)}};
    /// Cota de memoria: IPs distintas trackeadas como maximo
    size_t max_tracked_ips{{100000}};
    /// Fichero donde se vuelca strike_states_ antes de resetear por overflow.
    /// Si no se puede escribir, NO se resetea (no se pierde evidencia).
    std::string overflow_log_path{{"/vagrant/logs/lab/firewall_strike_overflow.log"}};
}};

//===----------------------------------------------------------------------===//
// Configuration
//===----------------------------------------------------------------------===//"""

HPP_SETTER_ANCHOR = """    void set_irp_config(const IrpConfig& irp) { irp_config_ = irp; }
    // Testeable sin fork — lógica de decisión pura (ADR-042)
    bool should_auto_isolate(const protobuf::Detection& detection) const;
    void check_auto_isolate(const protobuf::Detection& detection);"""
HPP_SETTER_REPLACEMENT = f"""    void set_irp_config(const IrpConfig& irp) {{ irp_config_ = irp; }}
    // Testeable sin fork — lógica de decisión pura (ADR-042)
    bool should_auto_isolate(const protobuf::Detection& detection) const;
    void check_auto_isolate(const protobuf::Detection& detection);

    void set_recidivism_config(const RecidivismConfig& cfg) {{ recidivism_config_ = cfg; }}  // {MARKER}
    /// {MARKER}: publico a proposito -- testeable sin IPSetWrapper real ni
    /// kernel, igual que should_auto_isolate. Calcula el timeout a aplicar a
    /// esta IP y actualiza su contador de reincidencia.
    uint32_t compute_penalty_timeout(const std::string& ip);"""

HPP_MEMBERS_ANCHOR = """    IrpConfig            irp_config_;         ///< ADR-042 auto-isolate config"""
HPP_MEMBERS_REPLACEMENT = (
    """    IrpConfig            irp_config_;         ///< ADR-042 auto-isolate config\n"""
    f"""    RecidivismConfig recidivism_config_;                          ///< {MARKER}\n"""
    f"""    std::unordered_map<std::string, StrikeState> strike_states_;  ///< {MARKER}, guardado por mutex_"""
)

HPP_METHOD_DECL_ANCHOR = """    /// Trigger backpressure callback if needed
    void check_backpressure();
};"""
HPP_METHOD_DECL_REPLACEMENT = f"""    /// Trigger backpressure callback if needed
    void check_backpressure();

    /// {MARKER}: strike_states_ ha superado max_tracked_ips. Vuelca TODO
    /// su contenido a recidivism_config_.overflow_log_path. Solo si el
    /// volcado tiene exito se vacia strike_states_ -- si falla, se deja
    /// crecer en memoria antes que perder evidencia en silencio.
    void dump_and_reset_strike_states();
}};"""

HPP_PATCHES = [
    ("structs", HPP_STRUCTS_ANCHOR, HPP_STRUCTS_REPLACEMENT),
    ("setter_and_public_method", HPP_SETTER_ANCHOR, HPP_SETTER_REPLACEMENT),
    ("members", HPP_MEMBERS_ANCHOR, HPP_MEMBERS_REPLACEMENT),
    ("private_method_decl", HPP_METHOD_DECL_ANCHOR, HPP_METHOD_DECL_REPLACEMENT),
]

# ---------------------------------------------------------------------------
# CPP patches (batch_processor.cpp)
# ---------------------------------------------------------------------------

CPP_INCLUDE_ANCHOR = """#include <algorithm>
#include <sstream>"""
CPP_INCLUDE_REPLACEMENT = f"""#include <algorithm>
#include <sstream>
#include <fstream>  // {MARKER}: volcado de strike_states_ a disco"""

CPP_FLUSH_LOOP_ANCHOR = """    for (const auto& ip : pending_ips_) {
        entries.push_back(IPSetEntry{ip});
    }"""
CPP_FLUSH_LOOP_REPLACEMENT = f"""    for (const auto& ip : pending_ips_) {{
        // {MARKER}: timeout variable por reincidencia en vez del fijo del set
        uint32_t penalty = compute_penalty_timeout(ip);
        std::string reason = "strikes=" + std::to_string(strike_states_[ip].strikes);
        entries.push_back(IPSetEntry{{ip, penalty, reason}});
    }}"""

CPP_NEW_METHODS_ANCHOR = """bool BatchProcessor::should_block(const protobuf::Detection& detection) const {"""
CPP_NEW_METHODS_REPLACEMENT = f"""// ── compute_penalty_timeout / dump_and_reset_strike_states — {MARKER} ──
// Vive en firewall porque es la unica fuente de verdad del ipset; los
// detectores (ultra-fast y ml-detector) solo mandan evidencia (Detection),
// firewall decide la duracion real del castigo.
uint32_t BatchProcessor::compute_penalty_timeout(const std::string& ip) {{
    if (!recidivism_config_.enabled) {{
        return 0;  // 0 = usa el timeout por defecto del set (sin escalado)
    }}

    // Chequeo de overflow ANTES de tocar el mapa para esta IP: si hicieramos
    // esto despues de state = strike_states_[ip], un clear() posterior
    // invalidaria la referencia 'state' y seria UB escribir en ella.
    if (strike_states_.size() >= recidivism_config_.max_tracked_ips &&
        strike_states_.find(ip) == strike_states_.end()) {{
        dump_and_reset_strike_states();
    }}

    auto now = std::chrono::steady_clock::now();
    auto& state = strike_states_[ip];

    if (state.strikes > 0 &&
        (now - state.last_seen) > recidivism_config_.quiet_period_reset) {{
        FIREWALL_LOG_INFO("Recidivism counter reset by quiet period",
            "ip", ip, "previous_strikes", state.strikes);
        state.strikes = 0;
    }}

    state.strikes++;
    state.last_seen = now;

    if (state.strikes >= recidivism_config_.permanent_after_strikes) {{
        FIREWALL_LOG_WARN("IP alcanza umbral de bloqueo permanente",
            "ip", ip, "strikes", state.strikes);
        return 0;  // permanente
    }}

    size_t idx = std::min<size_t>(state.strikes - 1,
        recidivism_config_.strike_durations_sec.size() - 1);
    return recidivism_config_.strike_durations_sec[idx];
}}

void BatchProcessor::dump_and_reset_strike_states() {{
    FIREWALL_LOG_ERROR("################################################");
    FIREWALL_LOG_ERROR("### AVISO CRITICO: strike_states_ LLENO       ###");
    FIREWALL_LOG_ERROR("### max_tracked_ips alcanzado ({MARKER})       ###");
    FIREWALL_LOG_ERROR("################################################");
    FIREWALL_LOG_ERROR("strike_states_ overflow",
        "size", strike_states_.size(),
        "max_tracked_ips", recidivism_config_.max_tracked_ips);

    std::ofstream out(recidivism_config_.overflow_log_path, std::ios::app);
    if (!out) {{
        FIREWALL_LOG_ERROR(
            "No se pudo abrir overflow_log_path -- NO se resetea "
            "strike_states_ para no perder las IPs (crecera en memoria "
            "hasta que se resuelva el fichero)",
            "path", recidivism_config_.overflow_log_path);
        return;
    }}

    auto now_t = std::chrono::system_clock::to_time_t(std::chrono::system_clock::now());
    for (const auto& [ip, state] : strike_states_) {{
        auto age_s = std::chrono::duration_cast<std::chrono::seconds>(
            std::chrono::steady_clock::now() - state.last_seen).count();
        out << now_t << ",overflow_reset," << ip << ","
            << state.strikes << "," << age_s << "\\n";
    }}
    out.flush();
    if (!out) {{
        FIREWALL_LOG_ERROR(
            "Fallo al escribir el volcado completo -- NO se resetea "
            "strike_states_ para no perder evidencia",
            "path", recidivism_config_.overflow_log_path);
        return;
    }}

    FIREWALL_LOG_INFO("strike_states_ volcado a disco antes del reset",
        "entries_dumped", strike_states_.size(),
        "path", recidivism_config_.overflow_log_path);

    strike_states_.clear();
}}

bool BatchProcessor::should_block(const protobuf::Detection& detection) const {{"""

CPP_PATCHES = [
    ("include", CPP_INCLUDE_ANCHOR, CPP_INCLUDE_REPLACEMENT),
    ("flush_loop", CPP_FLUSH_LOOP_ANCHOR, CPP_FLUSH_LOOP_REPLACEMENT),
    ("new_methods", CPP_NEW_METHODS_ANCHOR, CPP_NEW_METHODS_REPLACEMENT),
]

# ---------------------------------------------------------------------------
# JSON patch (firewall.json)
# ---------------------------------------------------------------------------

JSON_ANCHOR = """  "batch_processor": {
    "batch_size_threshold": 10,
    "batch_time_threshold_ms": 1000,
    "max_pending_ips": 100,
    "min_confidence": 0.5,
    "enable_batching": true,
    "flush_on_shutdown": true
  },"""
JSON_REPLACEMENT = f"""  "batch_processor": {{
    "batch_size_threshold": 10,
    "batch_time_threshold_ms": 1000,
    "max_pending_ips": 100,
    "min_confidence": 0.5,
    "enable_batching": true,
    "flush_on_shutdown": true
  }},
  "recidivism": {{
    "_comment": "{MARKER} -- escalado de castigo por reincidencia, vive en firewall no en los detectores",
    "enabled": true,
    "strike_durations_sec": [60, 300, 3600, 86400, 604800],
    "permanent_after_strikes": 6,
    "quiet_period_reset_sec": 259200,
    "max_tracked_ips": 100000,
    "overflow_log_path": "/vagrant/logs/lab/firewall_strike_overflow.log"
  }},"""

JSON_PATCHES = [
    ("recidivism_section", JSON_ANCHOR, JSON_REPLACEMENT),
]

# ---------------------------------------------------------------------------
# config_loader.hpp patches
# ---------------------------------------------------------------------------

CFG_HPP_STRUCT_ANCHOR = """struct BatchProcessorConfigNew {
    int batch_size_threshold = 10;
    int batch_time_threshold_ms = 1000;
    int max_pending_ips = 100;
    float min_confidence = 0.5f;
    bool enable_batching = true;
    bool flush_on_shutdown = true;
};"""
CFG_HPP_STRUCT_REPLACEMENT = f"""struct BatchProcessorConfigNew {{
    int batch_size_threshold = 10;
    int batch_time_threshold_ms = 1000;
    int max_pending_ips = 100;
    float min_confidence = 0.5f;
    bool enable_batching = true;
    bool flush_on_shutdown = true;
}};

//===----------------------------------------------------------------------===//
// Recidivism Configuration ({MARKER})
//===----------------------------------------------------------------------===//
struct RecidivismConfigNew {{
    bool enabled = true;
    std::vector<int> strike_durations_sec = {{60, 300, 3600, 86400, 604800}};
    int permanent_after_strikes = 6;
    int quiet_period_reset_sec = 259200;
    int max_tracked_ips = 100000;
    std::string overflow_log_path = "/vagrant/logs/lab/firewall_strike_overflow.log";
}};"""

CFG_HPP_MEMBER_ANCHOR = """    BatchProcessorConfigNew batch_processor;"""
CFG_HPP_MEMBER_REPLACEMENT = (
    """    BatchProcessorConfigNew batch_processor;\n"""
    f"""    RecidivismConfigNew recidivism;   // {MARKER}"""
)

CFG_HPP_PARSER_DECL_ANCHOR = """    static BatchProcessorConfigNew parse_batch_processor(const Json::Value& json);"""
CFG_HPP_PARSER_DECL_REPLACEMENT = (
    """    static BatchProcessorConfigNew parse_batch_processor(const Json::Value& json);\n"""
    f"""    static RecidivismConfigNew parse_recidivism(const Json::Value& json);  // {MARKER}"""
)

CFG_HPP_ARRAY_HELPER_ANCHOR = """    static std::vector<std::string> parse_string_array(const Json::Value& array);"""
CFG_HPP_ARRAY_HELPER_REPLACEMENT = (
    """    static std::vector<std::string> parse_string_array(const Json::Value& array);\n"""
    f"""    static std::vector<int> parse_int_array(const Json::Value& array);  // {MARKER}"""
)

CFG_HPP_PATCHES = [
    ("recidivism_struct", CFG_HPP_STRUCT_ANCHOR, CFG_HPP_STRUCT_REPLACEMENT),
    ("config_member", CFG_HPP_MEMBER_ANCHOR, CFG_HPP_MEMBER_REPLACEMENT),
    ("parser_decl", CFG_HPP_PARSER_DECL_ANCHOR, CFG_HPP_PARSER_DECL_REPLACEMENT),
    ("int_array_helper_decl", CFG_HPP_ARRAY_HELPER_ANCHOR, CFG_HPP_ARRAY_HELPER_REPLACEMENT),
]

# ---------------------------------------------------------------------------
# config_loader.cpp patches
# ---------------------------------------------------------------------------

CFG_CPP_STRING_ARRAY_ANCHOR = """std::vector<std::string> ConfigLoader::parse_string_array(const Json::Value& array) {
    std::vector<std::string> result;
    if (array.isArray()) {
        for (const auto& item : array) {
            result.push_back(item.asString());
        }
    }
    return result;
}"""
CFG_CPP_STRING_ARRAY_REPLACEMENT = f"""std::vector<std::string> ConfigLoader::parse_string_array(const Json::Value& array) {{
    std::vector<std::string> result;
    if (array.isArray()) {{
        for (const auto& item : array) {{
            result.push_back(item.asString());
        }}
    }}
    return result;
}}

// {MARKER}
std::vector<int> ConfigLoader::parse_int_array(const Json::Value& array) {{
    std::vector<int> result;
    if (array.isArray()) {{
        for (const auto& item : array) {{
            result.push_back(item.asInt());
        }}
    }}
    return result;
}}"""

CFG_CPP_LOAD_CALL_ANCHOR = """    if (root.isMember("batch_processor")) {
        config.batch_processor = parse_batch_processor(root["batch_processor"]);
    }"""
CFG_CPP_LOAD_CALL_REPLACEMENT = f"""    if (root.isMember("batch_processor")) {{
        config.batch_processor = parse_batch_processor(root["batch_processor"]);
    }}

    // {MARKER}: opcional -- si falta, usa los defaults de RecidivismConfigNew
    if (root.isMember("recidivism")) {{
        config.recidivism = parse_recidivism(root["recidivism"]);
    }}"""

CFG_CPP_PARSER_IMPL_ANCHOR = """BatchProcessorConfigNew ConfigLoader::parse_batch_processor(const Json::Value& json) {
    BatchProcessorConfigNew config;
    config.batch_size_threshold = get_optional<int>(json, "batch_size_threshold", 10);
    config.batch_time_threshold_ms = get_optional<int>(json, "batch_time_threshold_ms", 1000);
    config.max_pending_ips = get_optional<int>(json, "max_pending_ips", 100);
    config.min_confidence = get_optional<float>(json, "min_confidence", 0.5f);
    config.enable_batching = get_optional<bool>(json, "enable_batching", true);
    config.flush_on_shutdown = get_optional<bool>(json, "flush_on_shutdown", true);
    return config;
}"""
CFG_CPP_PARSER_IMPL_REPLACEMENT = f"""BatchProcessorConfigNew ConfigLoader::parse_batch_processor(const Json::Value& json) {{
    BatchProcessorConfigNew config;
    config.batch_size_threshold = get_optional<int>(json, "batch_size_threshold", 10);
    config.batch_time_threshold_ms = get_optional<int>(json, "batch_time_threshold_ms", 1000);
    config.max_pending_ips = get_optional<int>(json, "max_pending_ips", 100);
    config.min_confidence = get_optional<float>(json, "min_confidence", 0.5f);
    config.enable_batching = get_optional<bool>(json, "enable_batching", true);
    config.flush_on_shutdown = get_optional<bool>(json, "flush_on_shutdown", true);
    return config;
}}

// {MARKER}
RecidivismConfigNew ConfigLoader::parse_recidivism(const Json::Value& json) {{
    RecidivismConfigNew config;
    config.enabled = get_optional<bool>(json, "enabled", true);
    if (json.isMember("strike_durations_sec")) {{
        config.strike_durations_sec = parse_int_array(json["strike_durations_sec"]);
    }}
    config.permanent_after_strikes = get_optional<int>(json, "permanent_after_strikes", 6);
    config.quiet_period_reset_sec = get_optional<int>(json, "quiet_period_reset_sec", 259200);
    config.max_tracked_ips = get_optional<int>(json, "max_tracked_ips", 100000);
    config.overflow_log_path = get_optional<std::string>(json, "overflow_log_path",
        "/vagrant/logs/lab/firewall_strike_overflow.log");
    return config;
}}"""

CFG_CPP_PATCHES = [
    ("int_array_helper_impl", CFG_CPP_STRING_ARRAY_ANCHOR, CFG_CPP_STRING_ARRAY_REPLACEMENT),
    ("load_call", CFG_CPP_LOAD_CALL_ANCHOR, CFG_CPP_LOAD_CALL_REPLACEMENT),
    ("parser_impl", CFG_CPP_PARSER_IMPL_ANCHOR, CFG_CPP_PARSER_IMPL_REPLACEMENT),
]

# ---------------------------------------------------------------------------
# CMakeLists.txt patch: registra el test nuevo
# ---------------------------------------------------------------------------

CMAKE_ANCHOR = """    set(TEST_SOURCES
            tests/unit/test_ipset_is_valid_ip.cpp
            tests/unit/test_ipset_wrapper.cpp
            tests/unit/test_logger.cpp
            tests/unit/test_config_loader_traversal.cpp
            tests/unit/test_config_loader_setname.cpp
            tests/unit/test_set_name_validator.cpp
            tests/unit/test_parse_autonomy_cidr_injection.cpp   # ← DAY190 CWE-78
            tests/unit/test_comment_validator.cpp
            tests/unit/test_safe_exec.cpp
            tests/test_globals_stub.cpp
    )"""
CMAKE_REPLACEMENT = f"""    set(TEST_SOURCES
            tests/unit/test_ipset_is_valid_ip.cpp
            tests/unit/test_ipset_wrapper.cpp
            tests/unit/test_logger.cpp
            tests/unit/test_config_loader_traversal.cpp
            tests/unit/test_config_loader_setname.cpp
            tests/unit/test_set_name_validator.cpp
            tests/unit/test_parse_autonomy_cidr_injection.cpp   # ← DAY190 CWE-78
            tests/unit/test_comment_validator.cpp
            tests/unit/test_safe_exec.cpp
            tests/unit/test_batch_processor_recidivism.cpp   # ← {MARKER}
            tests/test_globals_stub.cpp
    )"""

CMAKE_E2E_ANCHOR = """    # H-2 DAY188: ipset injection (INTEGRACION, requiere root+ipset -> VM, no make test normal)
    add_executable(test_ipset_injection_integration
        tests/unit/test_ipset_injection_integration.cpp
    )
    target_include_directories(test_ipset_injection_integration PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/include
        ${CMAKE_CURRENT_SOURCE_DIR}/src/core
    )
    target_link_libraries(test_ipset_injection_integration PRIVATE
        firewall_core
        GTest::gtest
        GTest::gtest_main
    )
    add_test(NAME test_ipset_injection_integration COMMAND test_ipset_injection_integration)
    set_tests_properties(test_ipset_injection_integration PROPERTIES LABELS "e2e;root")"""
CMAKE_E2E_REPLACEMENT = f"""    # H-2 DAY188: ipset injection (INTEGRACION, requiere root+ipset -> VM, no make test normal)
    add_executable(test_ipset_injection_integration
        tests/unit/test_ipset_injection_integration.cpp
    )
    target_include_directories(test_ipset_injection_integration PRIVATE
        ${{CMAKE_CURRENT_SOURCE_DIR}}/include
        ${{CMAKE_CURRENT_SOURCE_DIR}}/src/core
    )
    target_link_libraries(test_ipset_injection_integration PRIVATE
        firewall_core
        GTest::gtest
        GTest::gtest_main
    )
    add_test(NAME test_ipset_injection_integration COMMAND test_ipset_injection_integration)
    set_tests_properties(test_ipset_injection_integration PROPERTIES LABELS "e2e;root")

    # test_recidivism_e2e — {MARKER} (INTEGRACION, requiere root+ipset -> VM, no make test normal)
    add_executable(test_recidivism_e2e
        tests/test_recidivism_e2e.cpp
    )
    target_include_directories(test_recidivism_e2e PRIVATE
        ${{CMAKE_CURRENT_SOURCE_DIR}}/include
        ${{CMAKE_CURRENT_SOURCE_DIR}}/src/core
    )
    target_link_libraries(test_recidivism_e2e PRIVATE
        firewall_core
        GTest::gtest
        GTest::gtest_main
    )
    add_test(NAME test_recidivism_e2e COMMAND test_recidivism_e2e)
    set_tests_properties(test_recidivism_e2e PROPERTIES LABELS "e2e;root")"""

CMAKE_PATCHES = [
    ("test_sources", CMAKE_ANCHOR, CMAKE_REPLACEMENT),
    ("e2e_test_registration", CMAKE_E2E_ANCHOR, CMAKE_E2E_REPLACEMENT),
]

# ---------------------------------------------------------------------------
# main.cpp patch: conversion RecidivismConfigNew -> RecidivismConfig y
# processor.set_recidivism_config(...), justo donde hoy se hace lo mismo
# para IrpConfig (ADR-042). Sin esto el JSON se parsea pero nunca llega a
# aplicarse al BatchProcessor en tiempo de ejecucion.
# ---------------------------------------------------------------------------

MAIN_ANCHOR = """    processor.set_irp_config(config.irp);  // ADR-042"""
MAIN_REPLACEMENT = f"""    processor.set_irp_config(config.irp);  // ADR-042

    // ── Recidivism config ({MARKER}) ──────────────────────────────────
    // Misma logica que la conversion de batch_config de arriba: el JSON
    // se parsea a tipos planos (RecidivismConfigNew) y aqui se convierte
    // al tipo "real" que usa BatchProcessor (RecidivismConfig), con los
    // tipos de chrono/uint32_t que compute_penalty_timeout necesita.
    RecidivismConfig recidivism_config;
    recidivism_config.enabled = config.recidivism.enabled;
    recidivism_config.strike_durations_sec.assign(
        config.recidivism.strike_durations_sec.begin(),
        config.recidivism.strike_durations_sec.end());
    recidivism_config.permanent_after_strikes =
        static_cast<uint32_t>(config.recidivism.permanent_after_strikes);
    recidivism_config.quiet_period_reset =
        std::chrono::seconds(config.recidivism.quiet_period_reset_sec);
    recidivism_config.max_tracked_ips =
        static_cast<size_t>(config.recidivism.max_tracked_ips);
    recidivism_config.overflow_log_path = config.recidivism.overflow_log_path;
    processor.set_recidivism_config(recidivism_config);  // {MARKER}"""

MAIN_PATCHES = [
    ("set_recidivism_config_call", MAIN_ANCHOR, MAIN_REPLACEMENT),
]

FILES = [
    (HPP_REL, HPP_PATCHES),
    (CPP_REL, CPP_PATCHES),
    (JSON_REL, JSON_PATCHES),
    (CFG_HPP_REL, CFG_HPP_PATCHES),
    (CFG_CPP_REL, CFG_CPP_PATCHES),
    (CMAKE_REL, CMAKE_PATCHES),
    (MAIN_REL, MAIN_PATCHES),
]

# ---------------------------------------------------------------------------
# Nuevo fichero de test (no es un parche -- se crea si no existe)
# ---------------------------------------------------------------------------

NEW_TEST_CONTENT = f"""// test_batch_processor_recidivism.cpp — {MARKER}
// Unit tests de compute_penalty_timeout / dump_and_reset_strike_states.
// Logica pura sobre BatchProcessor: no se llama a flush()/add_batch(), no
// se toca el kernel ni hace falta root (IPSetWrapper en dry_run).
#include <gtest/gtest.h>
#include "firewall/batch_processor.hpp"
#include "firewall/ipset_wrapper.hpp"
#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>

using namespace mldefender::firewall;

namespace {{

std::string read_file(const std::string& path) {{
    std::ifstream in(path);
    std::stringstream ss;
    ss << in.rdbuf();
    return ss.str();
}}

}}  // namespace

class RecidivismTest : public ::testing::Test {{
protected:
    void SetUp() override {{
        ipset_ = std::make_unique<IPSetWrapper>();
        ipset_->set_dry_run(true);  // nunca tocamos el kernel en estos tests
        processor_ = std::make_unique<BatchProcessor>(*ipset_);
    }}

    std::unique_ptr<IPSetWrapper> ipset_;
    std::unique_ptr<BatchProcessor> processor_;
}};

TEST_F(RecidivismTest, FirstStrikeUsesFirstDuration) {{
    RecidivismConfig cfg;
    cfg.strike_durations_sec = {{60, 300, 3600}};
    cfg.permanent_after_strikes = 10;
    processor_->set_recidivism_config(cfg);

    EXPECT_EQ(processor_->compute_penalty_timeout("1.2.3.4"), 60u);
}}

TEST_F(RecidivismTest, EscalatesOnRepeatedStrikes) {{
    RecidivismConfig cfg;
    cfg.strike_durations_sec = {{60, 300, 3600}};
    cfg.permanent_after_strikes = 10;
    cfg.quiet_period_reset = std::chrono::hours(999);  // no interfiere en este test
    processor_->set_recidivism_config(cfg);

    EXPECT_EQ(processor_->compute_penalty_timeout("1.2.3.4"), 60u);    // 1a vez
    EXPECT_EQ(processor_->compute_penalty_timeout("1.2.3.4"), 300u);   // 2a vez
    EXPECT_EQ(processor_->compute_penalty_timeout("1.2.3.4"), 3600u);  // 3a vez
    // Se queda en la ultima duracion configurada si sigue reincidiendo
    // por debajo de permanent_after_strikes
    EXPECT_EQ(processor_->compute_penalty_timeout("1.2.3.4"), 3600u);  // 4a vez
}}

TEST_F(RecidivismTest, DifferentIpsTrackedIndependently) {{
    RecidivismConfig cfg;
    cfg.strike_durations_sec = {{60, 300}};
    processor_->set_recidivism_config(cfg);

    EXPECT_EQ(processor_->compute_penalty_timeout("1.1.1.1"), 60u);
    EXPECT_EQ(processor_->compute_penalty_timeout("2.2.2.2"), 60u);   // no hereda reincidencia de 1.1.1.1
    EXPECT_EQ(processor_->compute_penalty_timeout("1.1.1.1"), 300u);  // 1.1.1.1 si escala
}}

TEST_F(RecidivismTest, PermanentAfterThreshold) {{
    RecidivismConfig cfg;
    cfg.strike_durations_sec = {{60}};
    cfg.permanent_after_strikes = 3;
    processor_->set_recidivism_config(cfg);

    EXPECT_EQ(processor_->compute_penalty_timeout("9.9.9.9"), 60u);  // strike 1
    EXPECT_EQ(processor_->compute_penalty_timeout("9.9.9.9"), 60u);  // strike 2
    EXPECT_EQ(processor_->compute_penalty_timeout("9.9.9.9"), 0u);   // strike 3 = permanente
}}

TEST_F(RecidivismTest, DisabledReturnsDefaultTimeout) {{
    RecidivismConfig cfg;
    cfg.enabled = false;
    processor_->set_recidivism_config(cfg);

    EXPECT_EQ(processor_->compute_penalty_timeout("5.5.5.5"), 0u);
    EXPECT_EQ(processor_->compute_penalty_timeout("5.5.5.5"), 0u);  // nunca escala si esta deshabilitado
}}

TEST_F(RecidivismTest, OverflowDumpsToFileAndResets) {{
    const std::string overflow_path = "/tmp/test_recidivism_overflow.log";
    std::remove(overflow_path.c_str());

    RecidivismConfig cfg;
    cfg.strike_durations_sec = {{60, 300}};
    cfg.max_tracked_ips = 2;  // fuerza el overflow con pocas IPs
    cfg.overflow_log_path = overflow_path;
    processor_->set_recidivism_config(cfg);

    processor_->compute_penalty_timeout("10.0.0.1");
    processor_->compute_penalty_timeout("10.0.0.2");
    // La 3a IP distinta dispara el overflow: dump + reset ANTES de contarla
    EXPECT_EQ(processor_->compute_penalty_timeout("10.0.0.3"), 60u);  // trata a 10.0.0.3 como 1a vez

    std::string dumped = read_file(overflow_path);
    EXPECT_NE(dumped.find("10.0.0.1"), std::string::npos);
    EXPECT_NE(dumped.find("10.0.0.2"), std::string::npos);

    // Tras el reset, 10.0.0.1 vuelve a contar como 1a vez: el contador en
    // memoria se reinicio, pero la evidencia quedo en el fichero de volcado.
    EXPECT_EQ(processor_->compute_penalty_timeout("10.0.0.1"), 60u);

    std::remove(overflow_path.c_str());
}}

TEST_F(RecidivismTest, OverflowDoesNotResetIfDumpFails) {{
    RecidivismConfig cfg;
    cfg.strike_durations_sec = {{60, 300}};
    cfg.max_tracked_ips = 2;
    // Ruta invalida (directorio inexistente): el volcado debe fallar
    cfg.overflow_log_path = "/ruta/que/no/existe/overflow.log";
    processor_->set_recidivism_config(cfg);

    processor_->compute_penalty_timeout("10.0.0.1");
    processor_->compute_penalty_timeout("10.0.0.2");
    // La 3a IP dispara el intento de overflow, que FALLA al escribir.
    // Contrato: si el volcado falla, NO se resetea. Lo verificamos
    // indirectamente: si 10.0.0.1 hubiera sido reseteada, volveria a dar 60
    // en vez de escalar a 300.
    processor_->compute_penalty_timeout("10.0.0.3");
    EXPECT_EQ(processor_->compute_penalty_timeout("10.0.0.1"), 300u);
}}
"""

# ---------------------------------------------------------------------------
# Test de aceptacion/e2e (root, ipset real) -- {MARKER}
#
# A diferencia del unitario de arriba (dry_run=true, logica pura), este
# test SI toca el kernel: crea un ipset de prueba propio (no el de
# produccion "blacklist"), hace flush() de verdad via BatchProcessor con
# recidivism habilitado, y verifica con `ipset list` que el timeout
# aplicado a la entrada escala segun strike_durations_sec.
#
# Sigue el patron ya visto en test_autonomy_e2e.cpp (TEST_F + fixture con
# SetUp/TearDown) y en test_ipset_injection_integration (root + ipset
# real, labels "e2e;root" en CMakeLists.txt).
#
# PENDIENTE: registrar este fichero en CMakeLists.txt. Necesito el bloque
# exacto de test_ipset_injection_integration (add_executable +
# target_link_libraries + add_test + set_tests_properties LABELS
# "e2e;root") para clonar el patron con un ancla de texto exacto, en vez
# de arriesgarme a inventar los nombres de libreria con los que enlaza.
# En cuanto lo tenga, esto se añade a la lista FILES/CMAKE_PATCHES igual
# que el resto.
# ---------------------------------------------------------------------------

NEW_E2E_TEST_CONTENT = f"""// test_recidivism_e2e.cpp — {MARKER}
// Test de ACEPTACION: requiere root (manipula un ipset real del kernel).
// No usa el ipset de produccion "blacklist" -- crea uno propio de prueba
// y lo destruye al final, para no interferir con nada mas.
//
// Que verifica, de extremo a extremo, sin mocks:
//   1) BatchProcessor::flush() escribe de verdad en el ipset del kernel.
//   2) El timeout de la entrada escala segun strike_durations_sec cuando
//      la misma IP reincide en flushes sucesivos.
//   3) Al superar permanent_after_strikes, la entrada queda sin timeout
//      (bloqueo permanente).
//
// Ejecucion (ver Makefile raiz): `make test-firewall-e2e` (usa
// `sudo ... ctest -L "e2e"`), o directamente como root:
//   sudo ./firewall-acl-agent/build-debug/test_recidivism_e2e
#include <gtest/gtest.h>
#include "firewall/batch_processor.hpp"
#include "firewall/ipset_wrapper.hpp"
#include <array>
#include <cstdio>
#include <cstdlib>  // std::system
#include <memory>
#include <regex>
#include <sstream>
#include <string>
#include <thread>
#include <chrono>
#include <unistd.h>  // getuid

using namespace mldefender::firewall;

namespace {{

// Lanza un comando y devuelve su stdout. No usar con entrada no confiable
// -- aqui el unico dato interpolado es TEST_SET_NAME, fijo y controlado
// por este fichero.
std::string shell(const std::string& cmd) {{
    std::array<char, 256> buf{{}};
    std::string out;
    FILE* pipe = popen(cmd.c_str(), "r");
    if (!pipe) return out;
    while (fgets(buf.data(), buf.size(), pipe) != nullptr) {{
        out += buf.data();
    }}
    pclose(pipe);
    return out;
}}

// Busca "ip timeout N" en la salida de `ipset list` y devuelve N, o -1 si
// la ip no aparece (por ejemplo, si quedo con timeout 0 == permanente,
// `ipset list` no imprime "timeout" en absoluto para esa entrada).
int extract_timeout(const std::string& ipset_list_output, const std::string& ip) {{
    std::regex re(ip + R"(\\s+timeout\\s+(\\d+))");
    std::smatch m;
    if (std::regex_search(ipset_list_output, m, re)) {{
        return std::stoi(m[1].str());
    }}
    return -1;
}}

bool entry_present(const std::string& ipset_list_output, const std::string& ip) {{
    return ipset_list_output.find(ip) != std::string::npos;
}}

constexpr const char* TEST_SET_NAME = "argus_test_recidivism_e2e";

}}  // namespace

class RecidivismE2ETest : public ::testing::Test {{
protected:
    void SetUp() override {{
        if (getuid() != 0) {{
            GTEST_SKIP() << "requiere root (manipula ipset real) -- "
                            "ejecutar via 'make test-firewall-e2e'";
        }}
        // -exist: no falla si ya existiera de una corrida anterior mal
        // terminada. timeout 0 en la definicion del set = por defecto
        // permanente; cada entrada individual lleva su propio timeout.
        shell(std::string("ipset destroy ") + TEST_SET_NAME + " 2>/dev/null");
        int rc = std::system(
            (std::string("ipset create ") + TEST_SET_NAME +
             " hash:ip timeout 0 2>&1").c_str());
        ASSERT_EQ(rc, 0) << "no se pudo crear el ipset de prueba "
                          << TEST_SET_NAME
                          << " -- ¿ipset instalado? ¿de verdad estamos "
                             "corriendo como root?";

        ipset_ = std::make_unique<IPSetWrapper>();
        // dry_run=false a proposito: este es el unico test del feature
        // que debe tocar el kernel de verdad -- el unitario (dry_run) ya
        // cubre la logica pura de compute_penalty_timeout.
        ipset_->set_dry_run(false);

        BatchProcessorConfig cfg;
        cfg.batch_size_threshold = 1;   // flush inmediato, 1 ip por batch
        cfg.max_pending_ips = 10;
        cfg.confidence_threshold = 0.0f;
        cfg.blacklist_ipset = TEST_SET_NAME;
        processor_ = std::make_unique<BatchProcessor>(*ipset_, cfg);

        RecidivismConfig rcfg;
        rcfg.enabled = true;
        rcfg.strike_durations_sec = {{5, 10, 20}};
        rcfg.permanent_after_strikes = 4;
        rcfg.quiet_period_reset = std::chrono::hours(999);  // no interfiere
        rcfg.max_tracked_ips = 1000;
        rcfg.overflow_log_path = "/tmp/argus_test_recidivism_e2e_overflow.log";
        processor_->set_recidivism_config(rcfg);
    }}

    void TearDown() override {{
        if (getuid() != 0) return;  // nada que limpiar si se hizo SKIP
        processor_.reset();
        ipset_.reset();
        shell(std::string("ipset destroy ") + TEST_SET_NAME + " 2>/dev/null");
    }}

    std::string list_set() {{
        return shell(std::string("ipset list ") + TEST_SET_NAME + " 2>&1");
    }}

    std::unique_ptr<IPSetWrapper> ipset_;
    std::unique_ptr<BatchProcessor> processor_;
}};

TEST_F(RecidivismE2ETest, FirstFlushAppliesFirstStrikeDuration) {{
    const std::string ip = "203.0.113.11";
    processor_->add_ip(ip);
    processor_->flush();

    auto listing = list_set();
    ASSERT_TRUE(entry_present(listing, ip)) << listing;
    int timeout = extract_timeout(listing, ip);
    ASSERT_GT(timeout, 0);
    // strike 1 = 5s de configuracion; damos margen porque el timeout ya
    // esta contando hacia atras desde que se aplico.
    EXPECT_LE(timeout, 5);
    EXPECT_GE(timeout, 1);
}}

TEST_F(RecidivismE2ETest, RepeatedOffenderEscalatesRealTimeout) {{
    const std::string ip = "203.0.113.22";

    processor_->add_ip(ip);
    processor_->flush();
    auto after_strike1 = list_set();
    int t1 = extract_timeout(after_strike1, ip);
    ASSERT_GT(t1, 0) << after_strike1;

    processor_->add_ip(ip);
    processor_->flush();
    auto after_strike2 = list_set();
    int t2 = extract_timeout(after_strike2, ip);
    ASSERT_GT(t2, 0) << after_strike2;

    // strike 2 (10s) debe ser un castigo mayor que strike 1 (5s), aun con
    // el descuento normal del contador. Verificamos la escalada real en
    // el kernel, no solo en la funcion pura (eso ya lo hace el unitario).
    EXPECT_GT(t2, t1);
}}

TEST_F(RecidivismE2ETest, PermanentAfterThresholdHasNoTimeoutInKernel) {{
    const std::string ip = "203.0.113.33";

    for (int i = 0; i < 4; ++i) {{
        processor_->add_ip(ip);
        processor_->flush();
    }}

    auto listing = list_set();
    ASSERT_TRUE(entry_present(listing, ip)) << listing;
    // strike 4 == permanent_after_strikes: compute_penalty_timeout
    // devuelve 0, IPSetEntry se crea sin timeout -> ipset no imprime
    // "timeout" para esa entrada.
    EXPECT_EQ(extract_timeout(listing, ip), -1) << listing;
}}
"""


def load(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def check_file(root: Path, rel: str, patches):
    path = root / rel
    if not path.exists():
        print("ERROR: no existe %s" % path, file=sys.stderr)
        return False
    text = load(path)
    if MARKER in text:
        print("%-70s ya aplicado (marcador %s presente)" % (rel, MARKER))
        return True
    ok = True
    for name, anchor, _ in patches:
        count = text.count(anchor)
        status = "OK" if count == 1 else ("FALTA" if count == 0 else "AMBIGUO(%d)" % count)
        print("%-70s [%s] ancla '%s'" % (rel, status, name))
        if count != 1:
            ok = False
    return ok


def apply_patches(text: str, patches):
    for name, anchor, replacement in patches:
        count = text.count(anchor)
        if count != 1:
            raise SystemExit("Ancla '%s' no encontrada exactamente una vez (count=%d) -- aborto" % (name, count))
        text = text.replace(anchor, replacement, 1)
    return text


# Ficheros nuevos (no se parchean, se crean si no existen ya)
NEW_FILES = [
    (NEW_TEST_REL, NEW_TEST_CONTENT),
    (NEW_E2E_TEST_REL, NEW_E2E_TEST_CONTENT),
]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=".", help="raiz del repo (default: directorio actual)")
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--dry", action="store_true")
    mode.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    root = Path(args.root).resolve()

    if args.check:
        all_ok = True
        for rel, patches in FILES:
            if not check_file(root, rel, patches):
                all_ok = False
        for rel, _content in NEW_FILES:
            new_path = root / rel
            if new_path.exists():
                print("%-70s ya existe (no se sobreescribe)" % rel)
            else:
                print("%-70s [OK] se creara" % rel)
        return 0 if all_ok else 1

    if args.dry:
        for rel, patches in FILES:
            path = root / rel
            if not path.exists():
                print("ERROR: no existe %s" % path, file=sys.stderr)
                return 2
            original = load(path)
            if MARKER in original:
                print("=== %s: ya aplicado, sin diff ===" % rel)
                continue
            patched = apply_patches(original, patches)
            diff = difflib.unified_diff(
                original.splitlines(keepends=True),
                patched.splitlines(keepends=True),
                fromfile=rel + " (actual)",
                tofile=rel + " (parcheado)",
            )
            print("=== %s ===" % rel)
            sys.stdout.writelines(diff)
            print()
        for rel, content in NEW_FILES:
            new_path = root / rel
            print("=== %s (fichero nuevo) ===" % rel)
            if new_path.exists():
                print("(ya existe -- no se tocaria)")
            else:
                print(content)
        return 0

    if args.apply:
        for rel, patches in FILES:
            path = root / rel
            if not path.exists():
                print("ERROR: no existe %s" % path, file=sys.stderr)
                return 2
            original = load(path)
            if MARKER in original:
                print("%s: ya aplicado, no se toca" % rel)
                continue
            patched = apply_patches(original, patches)
            backup = path.with_suffix(path.suffix + ".orig")
            if not backup.exists():
                backup.write_text(original, encoding="utf-8")
                print("backup: %s" % backup)
            path.write_text(patched, encoding="utf-8")
            print("aplicado: %s" % rel)

        for rel, content in NEW_FILES:
            new_path = root / rel
            if new_path.exists():
                print("%s: ya existe, no se sobreescribe" % rel)
            else:
                new_path.parent.mkdir(parents=True, exist_ok=True)
                new_path.write_text(content, encoding="utf-8")
                print("creado: %s" % rel)
        return 0


if __name__ == "__main__":
    sys.exit(main())