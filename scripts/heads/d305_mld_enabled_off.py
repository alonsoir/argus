#!/usr/bin/env python3
# DAY305 — [HEADS-DEFAULT-OFF-D305] regla de Alonso para 'enabled' de cada cabeza del ml-detector (level1,
# level2.ddos, level2.ransomware, level3.internal, level3.web y ml.ddos_v2):
#   - booleano JSON true/false, o texto "true"/"false" sin distinguir mayusculas ("TRUE", "False"...);
#   - ausente o cualquier otro valor -> false (cabeza APAGADA) con [CONFIG-DEFAULT]; el ml-detector arranca igual.
# Cambia el defecto anterior (true, DAY293 para ddos_v2 y esta manana para las demas). El JSON del laboratorio
# no cambia de comportamiento: todos sus 'enabled' son booleanos explicitos.
# Requiere aplicados d305_mld_heads.py, d305_mld_json.py y d305_mld_heads_intervalo.py.
# Valida TODO antes de escribir NADA. Uso, raiz del repo:  python3 d305_mld_enabled_off.py --check | --apply
import json, sys

MARK = "[HEADS-DEFAULT-OFF-D305]"
CL = "ml-detector/src/config_loader.cpp"
JS = "ml-detector/config/ml_detector_config.json"

EDITS = []
def E(f, old, new, n=1):
    EDITS.append((f, old, new, n))

E(CL, "#include <iomanip>\n", f"#include <iomanip>\n#include <cctype>  // {MARK}\n")
E(CL,
"""// [HEADS-SWITCH-D305] interruptor de cabeza: el JSON manda; si 'enabled' falta o no es booleano se usa true
// (comportamiento historico, un JSON incompleto no apaga nada en silencio) y se avisa con [CONFIG-DEFAULT].
// El estado EFECTIVO de cada cabeza se registra en el log con [HEADS] (zmq_handler).
namespace {
bool read_head_enabled(const nlohmann::json& block, const std::string& ctx) {
    if (block.is_object() && block.contains("enabled") && block["enabled"].is_boolean()) {
        return block["enabled"].get<bool>();
    }
    std::cerr << "[CONFIG-DEFAULT] " << ctx << ".enabled ausente o no booleano (formato true|false): se usa true\\n";
    return true;
}
}  // namespace
""",
f"""// [HEADS-SWITCH-D305] interruptor de cabeza: el JSON manda. {MARK} 'enabled' acepta booleano JSON o texto
// "true"/"false" sin distinguir mayusculas; si falta o tiene cualquier otro valor la cabeza queda APAGADA (false)
// y se avisa con [CONFIG-DEFAULT]. El estado EFECTIVO de cada cabeza se registra en el log con [HEADS] (zmq_handler).
namespace {{
bool read_head_enabled(const nlohmann::json& block, const std::string& ctx) {{
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
        std::cerr << "[CONFIG-DEFAULT] " << ctx << ".enabled invalido (" << v.dump()
                  << "; formato true|false, tambien como texto sin distinguir mayusculas): se usa false (cabeza APAGADA)\\n";
        return false;
    }}
    std::cerr << "[CONFIG-DEFAULT] " << ctx << ".enabled ausente (formato true|false): se usa false (cabeza APAGADA)\\n";
    return false;
}}
}}  // namespace
""")
E(CL,
"""            config.ml.ddos_v2.enabled = true;
            config.ml.ddos_v2.k_ratio = kDefK;
            if (!ml.contains("ddos_v2") || !ml["ddos_v2"].is_object()) {
                std::cerr << "[CONFIG-DEFAULT] ml.ddos_v2 ausente o no es un objeto: enabled=true, k_ratio=" << kDefK
""",
f"""            config.ml.ddos_v2.enabled = false;  // {MARK}
            config.ml.ddos_v2.k_ratio = kDefK;
            if (!ml.contains("ddos_v2") || !ml["ddos_v2"].is_object()) {{
                std::cerr << "[CONFIG-DEFAULT] ml.ddos_v2 ausente o no es un objeto: enabled=false (cabeza APAGADA), k_ratio=" << kDefK
""")
E(CL,
"""                if (d2.contains("enabled") && d2["enabled"].is_boolean()) {
                    config.ml.ddos_v2.enabled = d2["enabled"].get<bool>();
                } else {
                    std::cerr << "[CONFIG-DEFAULT] ml.ddos_v2.enabled ausente o no booleano (formato true|false): se usa true\\n";
                }
""",
f"""                config.ml.ddos_v2.enabled = read_head_enabled(d2, "ml.ddos_v2");  // {MARK}
""")

OLD_DOC = "si falta o no es booleano se usa true con [CONFIG-DEFAULT] y el ml-detector arranca igual."
NEW_DOC = (f"{MARK} acepta true|false, tambien como texto sin distinguir mayusculas; si falta o tiene otro valor "
           "se usa false (cabeza APAGADA) con [CONFIG-DEFAULT] y el ml-detector arranca igual.")
E(JS, OLD_DOC, NEW_DOC, 5)
E(JS, "enabled: true|false, defecto true. k_ratio:",
      f"enabled: true|false (tambien como texto, sin distinguir mayusculas); si falta o tiene otro valor, false "
      f"(cabeza APAGADA) con [CONFIG-DEFAULT] {MARK}. k_ratio:")

def die(m):
    print("ABORTA (no se ha escrito nada): " + m)
    sys.exit(1)

def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
        die("uso: python3 d305_mld_enabled_off.py --check | --apply")
    files = sorted({f for f, _, _, _ in EDITS})
    text = {}
    for f in files:
        try:
            text[f] = open(f, encoding="utf-8").read()
        except OSError as e:
            die(f"no puedo leer {f}: {e}")
        if MARK in text[f]:
            die(f"{f} ya contiene {MARK}: el parche ya se aplico (o a medias)")
    if "[HEADS-INTERVALO-D305]" not in text[CL] or "[HEADS-SWITCH-D305]" not in text[JS]:
        die("faltan los parches anteriores de DAY305 (heads, json, intervalo)")
    new = dict(text)
    for i, (f, old, rep, n) in enumerate(EDITS, 1):
        c = new[f].count(old)
        if c != n:
            die(f"edicion {i} en {f}: el ancla aparece {c} veces (se esperaban {n}):\n---\n{old}\n---")
        new[f] = new[f].replace(old, rep)
    if new[CL].count(MARK) != 4:
        die(f"{CL}: {new[CL].count(MARK)} marcas (se esperaban 4)")
    if "se usa true" in new[CL]:
        die(f"{CL}: queda algun defecto 'se usa true'")
    if new[CL].count('read_head_enabled(') != 7:  # definicion + 5 cabezas + ddos_v2
        die(f"{CL}: {new[CL].count('read_head_enabled(')} apariciones de read_head_enabled( (se esperaban 7)")
    try:
        j = json.loads(new[JS])
    except json.JSONDecodeError as e:
        die(f"el JSON resultante no parsea: {e}")
    ml = j["ml"]
    vals = [ml["level1"]["enabled"], ml["level2"]["ddos"]["enabled"], ml["level2"]["ransomware"]["enabled"],
            ml["level3"]["web"]["enabled"], ml["level3"]["internal"]["enabled"], ml["ddos_v2"]["enabled"]]
    if vals != [False, False, False, False, False, True]:
        die(f"JSON: valores de enabled inesperados {vals}")
    if new[JS].count(MARK) != 6:
        die(f"{JS}: {new[JS].count(MARK)} marcas (se esperaban 6)")
    print(f"OK: {len(EDITS)} ediciones validadas; defecto de 'enabled' -> false; JSON valido y sin cambios de valor")
    for f in files:
        print(f"   {f}: +{new[f].count(chr(10)) - text[f].count(chr(10))} lineas, {new[f].count(MARK)} marcas")
    if sys.argv[1] == "--check":
        print("--check: no se ha escrito nada")
        return
    for f in files:
        with open(f, "w", encoding="utf-8") as fh:
            fh.write(new[f])
    print("--apply: escrito. Siguiente: compilacion completa en production")

if __name__ == "__main__":
    main()
