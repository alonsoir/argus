#!/usr/bin/env python3
# DAY305 — [HEADS-TESTS-D305] pruebas unitarias de los lectores de configuracion de las cabezas.
# Los lectores de 'enabled' y de enteros con rango vivian en espacios de nombres anonimos (no se podian probar
# sueltos). Se sacan, SIN cambiar su comportamiento, a una cabecera sin estado por componente, y se cubren con
# una prueba propia registrada en ctest:
#   ml-detector/include/heads_config.hpp  + ml-detector/tests/unit/test_heads_config.cpp  (nlohmann::json)
#   sniffer/include/heads_config.hpp      + sniffer/tests/test_heads_config.cpp           (jsoncpp)
# Reglas probadas (Alonso, DAY305): 'enabled' = booleano o texto true/false sin distinguir mayusculas; ausente o
# cualquier otro valor -> false con [CONFIG-DEFAULT]. Entero con rango: ausente, no entero (tambien 60.0, "60",
# true) o fuera de rango -> defecto con [CONFIG-DEFAULT] que nombra campo, formato y limites. Valor valido: sin aviso.
# Requiere aplicados los parches anteriores de DAY305. Valida TODO antes de escribir NADA.
# Uso, raiz del repo:  python3 d305_tests_config.py --check | --apply
import os, sys

MARK = "[HEADS-TESTS-D305]"
M_CL = "ml-detector/src/config_loader.cpp"
M_TC = "ml-detector/tests/CMakeLists.txt"
S_CT = "sniffer/src/userspace/config_types.cpp"
S_CM = "sniffer/CMakeLists.txt"
NEW = {
    "ml-detector/include/heads_config.hpp": None,
    "ml-detector/tests/unit/test_heads_config.cpp": None,
    "sniffer/include/heads_config.hpp": None,
    "sniffer/tests/test_heads_config.cpp": None,
}

NEW["ml-detector/include/heads_config.hpp"] = f"""#pragma once
// ml-detector/include/heads_config.hpp — {MARK}
// Lectores de configuracion de las cabezas del ml-detector (reglas de Alonso, DAY305). Sin estado, para poder
// probarlos sueltos (tests/unit/test_heads_config.cpp). Los avisos van a 'aviso' (std::cerr por defecto).
#include <nlohmann/json.hpp>
#include <cctype>
#include <iostream>
#include <string>

namespace ml_detector::heads {{

// 'enabled' de una cabeza: booleano JSON o texto "true"/"false" sin distinguir mayusculas. Ausente o cualquier
// otro valor -> false (cabeza APAGADA) con [CONFIG-DEFAULT].
inline bool read_enabled(const nlohmann::json& block, const std::string& ctx, std::ostream& aviso = std::cerr) {{
    if (block.is_object() && block.contains("enabled")) {{
        const auto& v = block["enabled"];
        if (v.is_boolean()) {{
            return v.get<bool>();
        }}
        if (v.is_string()) {{
            std::string s = v.get<std::string>();
            for (auto& c : s) {{
                c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
            }}
            if (s == "true") {{
                return true;
            }}
            if (s == "false") {{
                return false;
            }}
        }}
        aviso << "[CONFIG-DEFAULT] " << ctx << ".enabled invalido (" << v.dump()
              << "; formato true|false, tambien como texto sin distinguir mayusculas): se usa false (cabeza APAGADA)\\n";
        return false;
    }}
    aviso << "[CONFIG-DEFAULT] " << ctx << ".enabled ausente (formato true|false): se usa false (cabeza APAGADA)\\n";
    return false;
}}

// Entero en [mn, mx]. Ausente, no entero (un 60.0 tampoco lo es), o fuera de rango -> 'def' con [CONFIG-DEFAULT]
// que nombra campo, formato y limites.
inline int read_int_in_range(const nlohmann::json& block, const char* key, const std::string& ctx, int def,
                             int mn, int mx, std::ostream& aviso = std::cerr) {{
    if (!block.is_object() || !block.contains(key)) {{
        aviso << "[CONFIG-DEFAULT] " << ctx << "." << key << " ausente (entero en [" << mn << ", " << mx
              << "]): se usa " << def << "\\n";
        return def;
    }}
    const auto& v = block[key];
    bool ok = false;
    long long x = 0;
    if (v.is_number_unsigned()) {{
        const unsigned long long u = v.get<unsigned long long>();
        ok = u <= static_cast<unsigned long long>(mx);
        x = ok ? static_cast<long long>(u) : 0;
    }} else if (v.is_number_integer()) {{
        x = v.get<long long>();
        ok = true;
    }}
    if (!ok || x < mn || x > mx) {{
        aviso << "[CONFIG-DEFAULT] " << ctx << "." << key << " invalido (" << v.dump() << "; entero en [" << mn
              << ", " << mx << "]): se usa " << def << "\\n";
        return def;
    }}
    return static_cast<int>(x);
}}

}}  // namespace ml_detector::heads
"""

NEW["sniffer/include/heads_config.hpp"] = f"""#pragma once
// sniffer/include/heads_config.hpp — {MARK}
// Lectores de configuracion del fast-path y de los intervalos del sniffer (reglas de Alonso, DAY305). Sin estado,
// para poder probarlos sueltos (tests/test_heads_config.cpp). Los avisos van a 'aviso' (std::cerr por defecto).
#include <json/json.h>
#include <cctype>
#include <iostream>
#include <string>

namespace sniffer::heads {{

// 'enabled': booleano o texto "true"/"false" sin distinguir mayusculas; ausente o invalido -> false + aviso.
inline bool leer_enabled(const Json::Value& blk, const std::string& ctx, std::ostream& aviso = std::cerr) {{
    if (blk.isObject() && blk.isMember("enabled")) {{
        const Json::Value& v = blk["enabled"];
        if (v.isBool()) {{
            return v.asBool();
        }}
        if (v.isString()) {{
            std::string s = v.asString();
            for (auto& c : s) {{
                c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
            }}
            if (s == "true") {{
                return true;
            }}
            if (s == "false") {{
                return false;
            }}
        }}
        aviso << "[CONFIG-DEFAULT] " << ctx << ".enabled invalido (formato true|false, tambien como texto sin "
                 "distinguir mayusculas): se usa false (APAGADO)" << std::endl;
        return false;
    }}
    aviso << "[CONFIG-DEFAULT] " << ctx << ".enabled ausente (formato true|false): se usa false (APAGADO)"
          << std::endl;
    return false;
}}

// Entero en [mn, mx]: solo tipos enteros de JSON (un 30.0 o un "30" no valen); ausente, no entero o fuera de
// rango -> defecto + aviso con campo, formato y limites.
inline int leer_entero(const Json::Value& blk, const char* clave, const std::string& ctx, int def, int mn, int mx,
                       std::ostream& aviso = std::cerr) {{
    if (!blk.isObject() || !blk.isMember(clave)) {{
        aviso << "[CONFIG-DEFAULT] " << ctx << "." << clave << " ausente (entero en [" << mn << ", " << mx
              << "]): se usa " << def << std::endl;
        return def;
    }}
    const Json::Value& v = blk[clave];
    const bool entero = v.type() == Json::intValue || v.type() == Json::uintValue;
    if (!entero || (v.type() == Json::uintValue && v.asLargestUInt() > static_cast<Json::LargestUInt>(mx)) ||
        v.asLargestInt() < mn || v.asLargestInt() > mx) {{
        aviso << "[CONFIG-DEFAULT] " << ctx << "." << clave << " invalido (entero en [" << mn << ", " << mx
              << "]): se usa " << def << std::endl;
        return def;
    }}
    return static_cast<int>(v.asLargestInt());
}}

}}  // namespace sniffer::heads
"""

NEW["ml-detector/tests/unit/test_heads_config.cpp"] = r"""// ml-detector/tests/unit/test_heads_config.cpp — [HEADS-TESTS-D305]
// Reglas de Alonso (DAY305) para la configuracion de las cabezas: casos validos sin aviso; ausentes e invalidos
// con el defecto y un [CONFIG-DEFAULT] que nombra el campo. Sin GTest, con main propio (como test_l2_gate).
#include "heads_config.hpp"
#include <iostream>
#include <sstream>
#include <string>

namespace {
int g_casos = 0;
int g_fallos = 0;
void comprueba(bool ok, const std::string& que) {
    ++g_casos;
    if (!ok) {
        ++g_fallos;
        std::cerr << "FALLA: " << que << "\n";
    }
}
using nlohmann::json;
using ml_detector::heads::read_enabled;
using ml_detector::heads::read_int_in_range;

// enabled: valor esperado y si debe avisar
void caso_enabled(const json& blk, bool esperado, bool aviso_esperado, const std::string& que) {
    std::ostringstream av;
    const bool r = read_enabled(blk, "ml.prueba", av);
    comprueba(r == esperado, "enabled " + que + ": valor");
    const bool avisa = av.str().find("[CONFIG-DEFAULT] ml.prueba.enabled") != std::string::npos;
    comprueba(avisa == aviso_esperado, "enabled " + que + ": aviso");
    if (aviso_esperado) {
        comprueba(av.str().find("APAGADA") != std::string::npos, "enabled " + que + ": el aviso dice APAGADA");
    }
}
void caso_entero(const json& blk, int esperado, bool aviso_esperado, const std::string& que) {
    std::ostringstream av;
    const int r = read_int_in_range(blk, "intervalo", "monitoring", 60, 10, 3600, av);
    comprueba(r == esperado, "entero " + que + ": valor (" + std::to_string(r) + ")");
    const bool avisa = av.str().find("[CONFIG-DEFAULT] monitoring.intervalo") != std::string::npos;
    comprueba(avisa == aviso_esperado, "entero " + que + ": aviso");
    if (aviso_esperado) {
        comprueba(av.str().find("[10, 3600]") != std::string::npos, "entero " + que + ": el aviso da los limites");
    }
}
}  // namespace

int main() {
    caso_enabled(json{{"enabled", true}}, true, false, "true");
    caso_enabled(json{{"enabled", false}}, false, false, "false");
    caso_enabled(json{{"enabled", "true"}}, true, false, "\"true\"");
    caso_enabled(json{{"enabled", "TRUE"}}, true, false, "\"TRUE\"");
    caso_enabled(json{{"enabled", "False"}}, false, false, "\"False\"");
    caso_enabled(json{{"enabled", "FALSE"}}, false, false, "\"FALSE\"");
    caso_enabled(json::object(), false, true, "ausente");
    caso_enabled(json{{"enabled", "yes"}}, false, true, "\"yes\"");
    caso_enabled(json{{"enabled", " true"}}, false, true, "\" true\" con espacio");
    caso_enabled(json{{"enabled", 1}}, false, true, "1");
    caso_enabled(json{{"enabled", 0}}, false, true, "0");
    caso_enabled(json{{"enabled", nullptr}}, false, true, "null");
    caso_enabled(json::array({true}), false, true, "bloque que no es objeto");

    caso_entero(json{{"intervalo", 60}}, 60, false, "60");
    caso_entero(json{{"intervalo", 10}}, 10, false, "limite inferior 10");
    caso_entero(json{{"intervalo", 3600}}, 3600, false, "limite superior 3600");
    caso_entero(json{{"intervalo", 300}}, 300, false, "300");
    caso_entero(json::object(), 60, true, "ausente");
    caso_entero(json{{"intervalo", 9}}, 60, true, "9 bajo el minimo");
    caso_entero(json{{"intervalo", 3601}}, 60, true, "3601 sobre el maximo");
    caso_entero(json{{"intervalo", -5}}, 60, true, "-5");
    caso_entero(json{{"intervalo", 60.0}}, 60, true, "60.0 (no es entero)");
    caso_entero(json{{"intervalo", 60.5}}, 60, true, "60.5");
    caso_entero(json{{"intervalo", "60"}}, 60, true, "\"60\" texto");
    caso_entero(json{{"intervalo", true}}, 60, true, "true");
    caso_entero(json{{"intervalo", nullptr}}, 60, true, "null");
    caso_entero(json{{"intervalo", 18446744073709551615ULL}}, 60, true, "uint64 enorme");

    std::cout << "[test_heads_config] ml-detector: " << (g_casos - g_fallos) << "/" << g_casos << " comprobaciones OK"
              << std::endl;
    return g_fallos == 0 ? 0 : 1;
}
"""

NEW["sniffer/tests/test_heads_config.cpp"] = r"""// sniffer/tests/test_heads_config.cpp — [HEADS-TESTS-D305]
// Reglas de Alonso (DAY305) para fast_detector.enabled y los intervalos del sniffer: casos validos sin aviso;
// ausentes e invalidos con el defecto y un [CONFIG-DEFAULT] que nombra el campo. Sin GTest, con main propio.
#include "heads_config.hpp"
#include <iostream>
#include <sstream>
#include <string>

namespace {
int g_casos = 0;
int g_fallos = 0;
void comprueba(bool ok, const std::string& que) {
    ++g_casos;
    if (!ok) {
        ++g_fallos;
        std::cerr << "FALLA: " << que << "\n";
    }
}
using sniffer::heads::leer_enabled;
using sniffer::heads::leer_entero;

Json::Value con(const char* k, const Json::Value& v) {
    Json::Value o(Json::objectValue);
    o[k] = v;
    return o;
}
void caso_enabled(const Json::Value& blk, bool esperado, bool aviso_esperado, const std::string& que) {
    std::ostringstream av;
    const bool r = leer_enabled(blk, "fast_detector", av);
    comprueba(r == esperado, "enabled " + que + ": valor");
    const bool avisa = av.str().find("[CONFIG-DEFAULT] fast_detector.enabled") != std::string::npos;
    comprueba(avisa == aviso_esperado, "enabled " + que + ": aviso");
    if (aviso_esperado) {
        comprueba(av.str().find("APAGADO") != std::string::npos, "enabled " + que + ": el aviso dice APAGADO");
    }
}
void caso_entero(const Json::Value& blk, int esperado, bool aviso_esperado, const std::string& que) {
    std::ostringstream av;
    const int r = leer_entero(blk, "window_interval_seconds", "fast_detector.ransomware", 30, 5, 3600, av);
    comprueba(r == esperado, "entero " + que + ": valor (" + std::to_string(r) + ")");
    const bool avisa =
        av.str().find("[CONFIG-DEFAULT] fast_detector.ransomware.window_interval_seconds") != std::string::npos;
    comprueba(avisa == aviso_esperado, "entero " + que + ": aviso");
    if (aviso_esperado) {
        comprueba(av.str().find("[5, 3600]") != std::string::npos, "entero " + que + ": el aviso da los limites");
    }
}
}  // namespace

int main() {
    caso_enabled(con("enabled", true), true, false, "true");
    caso_enabled(con("enabled", false), false, false, "false");
    caso_enabled(con("enabled", "true"), true, false, "\"true\"");
    caso_enabled(con("enabled", "TRUE"), true, false, "\"TRUE\"");
    caso_enabled(con("enabled", "False"), false, false, "\"False\"");
    caso_enabled(con("enabled", "FALSE"), false, false, "\"FALSE\"");
    caso_enabled(Json::Value(Json::objectValue), false, true, "ausente");
    caso_enabled(con("enabled", "yes"), false, true, "\"yes\"");
    caso_enabled(con("enabled", " true"), false, true, "\" true\" con espacio");
    caso_enabled(con("enabled", 1), false, true, "1");
    caso_enabled(con("enabled", 0), false, true, "0");
    caso_enabled(con("enabled", Json::Value()), false, true, "null");
    caso_enabled(Json::Value(Json::arrayValue), false, true, "bloque que no es objeto");

    caso_entero(con("window_interval_seconds", 30), 30, false, "30");
    caso_entero(con("window_interval_seconds", 5), 5, false, "limite inferior 5");
    caso_entero(con("window_interval_seconds", 3600), 3600, false, "limite superior 3600");
    caso_entero(con("window_interval_seconds", Json::UInt(120)), 120, false, "120 sin signo");
    caso_entero(Json::Value(Json::objectValue), 30, true, "ausente");
    caso_entero(con("window_interval_seconds", 4), 30, true, "4 bajo el minimo");
    caso_entero(con("window_interval_seconds", 3601), 30, true, "3601 sobre el maximo");
    caso_entero(con("window_interval_seconds", -5), 30, true, "-5");
    caso_entero(con("window_interval_seconds", 30.0), 30, true, "30.0 (no es entero)");
    caso_entero(con("window_interval_seconds", 30.5), 30, true, "30.5");
    caso_entero(con("window_interval_seconds", "30"), 30, true, "\"30\" texto");
    caso_entero(con("window_interval_seconds", true), 30, true, "true");
    caso_entero(con("window_interval_seconds", Json::Value()), 30, true, "null");
    caso_entero(con("window_interval_seconds", Json::UInt64(18446744073709551615ULL)), 30, true, "uint64 enorme");

    std::cout << "[test_heads_config] sniffer: " << (g_casos - g_fallos) << "/" << g_casos << " comprobaciones OK"
              << std::endl;
    return g_fallos == 0 ? 0 : 1;
}
"""

EDITS = []  # (fichero, inicio, fin_o_None, reemplazo)
def E(f, start, end, rep):
    EDITS.append((f, start, end, rep))

# ---------------- ml-detector: config_loader.cpp usa la cabecera
E(M_CL, "#include <cctype>  // [HEADS-DEFAULT-OFF-D305]\n", None,
        f"#include <cctype>  // [HEADS-DEFAULT-OFF-D305]\n#include \"heads_config.hpp\"  // {MARK}\n")
E(M_CL, "// [HEADS-SWITCH-D305] interruptor de cabeza: el JSON manda. [HEADS-DEFAULT-OFF-D305] 'enabled' acepta booleano JSON o texto\n",
        "}  // namespace\n",
        f"// [HEADS-SWITCH-D305] [HEADS-DEFAULT-OFF-D305] {MARK} la regla de 'enabled' vive en heads_config.hpp (probada en\n"
        "// tests/unit/test_heads_config.cpp). El estado EFECTIVO de cada cabeza se registra con [HEADS] (zmq_handler).\n"
        "namespace {\n"
        "bool read_head_enabled(const nlohmann::json& block, const std::string& ctx) {\n"
        "    return heads::read_enabled(block, ctx);\n"
        "}\n"
        "}  // namespace\n")
E(M_CL, "        {   // [HEADS-INTERVALO-D305] el JSON manda; ausente, no entero o fuera de rango -> defecto validado + [CONFIG-DEFAULT]\n",
        "                config.monitoring.heads_log_interval_seconds = mon[\"heads_log_interval_seconds\"].get<int>();\n            }\n        }\n",
        f"        // [HEADS-INTERVALO-D305] {MARK} entero en [10, 3600], defecto 60; regla en heads_config.hpp\n"
        "        config.monitoring.heads_log_interval_seconds = heads::read_int_in_range(\n"
        "            mon, \"heads_log_interval_seconds\", \"monitoring\", 60, 10, 3600);\n")
# ---------------- ml-detector: registrar la prueba
E(M_TC, "    add_test(NAME test_ddos_v2_parity COMMAND test_ddos_v2_parity)\nendif()\n", None,
        "    add_test(NAME test_ddos_v2_parity COMMAND test_ddos_v2_parity)\nendif()\n"
        f"# ── test_heads_config — DAY305 {MARK} lectores de configuracion de las cabezas (heads_config.hpp) ──\n"
        "if(EXISTS \"${CMAKE_CURRENT_SOURCE_DIR}/unit/test_heads_config.cpp\")\n"
        "    add_executable(test_heads_config\n            unit/test_heads_config.cpp\n    )\n"
        "    target_include_directories(test_heads_config PRIVATE\n            ${CMAKE_CURRENT_SOURCE_DIR}/../include\n    )\n"
        "    target_compile_features(test_heads_config PRIVATE cxx_std_20)\n"
        "    ml_link_nlohmann(test_heads_config)\n"
        "    add_test(NAME test_heads_config COMMAND test_heads_config)\nendif()\n")
# ---------------- sniffer: config_types.cpp usa la cabecera
E(S_CT, "// [HEADS-SNIFFER-D305] reglas de Alonso: el JSON manda y ningun campo se lee en silencio.\nnamespace {\n",
        "}  // namespace\n\nbool strict_load_json_config(",
        f"// [HEADS-SNIFFER-D305] {MARK} reglas de Alonso (el JSON manda y ningun campo se lee en silencio) en\n"
        "// heads_config.hpp, probadas en tests/test_heads_config.cpp.\n"
        f"#include \"heads_config.hpp\"  // {MARK}\n"
        "using sniffer::heads::leer_enabled;\nusing sniffer::heads::leer_entero;\n\n"
        "bool strict_load_json_config(")
# ---------------- sniffer: registrar la prueba
E(S_CM, "message(STATUS \"🧪 Unit Test: test_ip_format configured (DAY 229 - DEBT-SNIFFER-IP-BYTE-ORDER-001)\")\n", None,
        "message(STATUS \"🧪 Unit Test: test_ip_format configured (DAY 229 - DEBT-SNIFFER-IP-BYTE-ORDER-001)\")\n\n"
        f"# DAY305 {MARK} lectores de configuracion del fast-path y de los intervalos (heads_config.hpp)\n"
        "add_executable(test_heads_config\n        tests/test_heads_config.cpp\n)\n"
        "target_include_directories(test_heads_config PRIVATE\n        ${CMAKE_SOURCE_DIR}/include\n        ${JSONCPP_INCLUDE_DIRS}\n)\n"
        "target_link_directories(test_heads_config PRIVATE ${JSONCPP_LIBRARY_DIRS})\n"
        "target_link_libraries(test_heads_config\n        ${JSONCPP_LIBRARIES}\n)\n"
        "add_test(NAME test_heads_config COMMAND test_heads_config)\n"
        f"message(STATUS \"🧪 Unit Test: test_heads_config configured (DAY 305 - {MARK})\")\n")

def die(m):
    print("ABORTA (no se ha escrito nada): " + m)
    sys.exit(1)

def locate(t, start, end):
    if t.count(start) != 1:
        return None, f"ancla de inicio aparece {t.count(start)} veces"
    i = t.index(start)
    if end is None:
        return (i, i + len(start)), None
    j = t.find(end, i)
    if j < 0:
        return None, "ancla de fin no aparece despues del inicio"
    return (i, j + len(end)), None

def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
        die("uso: python3 d305_tests_config.py --check | --apply")
    for p in NEW:
        if os.path.exists(p):
            die(f"{p} ya existe: el parche ya se aplico (o a medias)")
    files = sorted({e[0] for e in EDITS})
    text = {}
    for f in files:
        try:
            text[f] = open(f, encoding="utf-8").read()
        except OSError as e:
            die(f"no puedo leer {f}: {e}")
        if MARK in text[f]:
            die(f"{f} ya contiene {MARK}")
    if "[HEADS-INTERVALO-D305]" not in text[M_CL] or "[HEADS-SNIFFER-D305]" not in text[S_CT]:
        die("faltan los parches anteriores de DAY305")
    new = dict(text)
    for k, (f, start, end, rep) in enumerate(EDITS, 1):
        span, err = locate(new[f], start, end)
        if err:
            die(f"edicion {k} en {f}: {err}\n---\n{start}---")
        blk = new[f][span[0]:span[1]]
        if end is not None and blk.count("\n") > 60:
            die(f"edicion {k} en {f}: el bloque abarca {blk.count(chr(10))} lineas (demasiadas): ancla de fin equivocada")
        new[f] = new[f][:span[0]] + rep + new[f][span[1]:]
    # comprobaciones del resultado
    if new[M_CL].count("std::tolower") != 0 or new[M_CL].count("read_head_enabled(") != 7:
        die("config_loader.cpp: la regla de enabled no quedo solo en la cabecera, o cambiaron las llamadas")
    if "mon[\"heads_log_interval_seconds\"]" in new[M_CL]:
        die("config_loader.cpp: queda la lectura antigua del intervalo")
    if "namespace {" in new[S_CT] or "leer_enabled(fd, \"fast_detector\")" not in new[S_CT]:
        die("config_types.cpp: resultado inesperado")
    print(f"OK: {len(EDITS)} ediciones validadas en {len(files)} ficheros + {len(NEW)} ficheros nuevos")
    for f in files:
        print(f"   {f}: {new[f].count(chr(10)) - text[f].count(chr(10)):+d} lineas")
    for p, c in NEW.items():
        print(f"   {p}: nuevo, {c.count(chr(10))} lineas")
    if sys.argv[1] == "--check":
        print("--check: no se ha escrito nada")
        return
    for f in files:
        with open(f, "w", encoding="utf-8") as fh:
            fh.write(new[f])
    for p, c in NEW.items():
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(c)
    print("--apply: escrito. Siguiente: compilacion completa y test-components en production")

if __name__ == "__main__":
    main()
