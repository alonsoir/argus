#!/usr/bin/env python3
# DAY307 — fuera el mecanismo feature_groups del sniffer (configuracion ceremonial: nadie abre los ficheros,
# la validacion no la llama nadie, StrictSnifferConfig nunca lo rellena; solo imprimia "Feature groups: 4").
#  - sniffer.json: fuera user_space.user_features y el bloque feature_groups (el JSON sigue siendo valido).
#  - config_manager.{hpp,cpp}: fuera FeatureGroupConfig, el campo, su parseo, su validacion y su log;
#    fuera user_features de UserSpaceConfig y su parseo.
#  - config_types.{h,cpp}: fuera FeatureGroup, los campos y el stub validate_feature_groups_section.
#  - sniffer/CMakeLists.txt: fuera el directorio config/features del build y los ficheros "[]" que creaba.
#  - Borra sniffer/config/features/rf_23_features.json y ransomware_20_features.json.
# Valida TODO antes de escribir NADA (sha256 de partida y de llegada, anclas unicas, JSON valido).
# Uso (Mac, raiz del repo): python3 scripts/flow_expiry/d307_sin_feature_groups.py --check | --apply
import hashlib, json, os, sys
EDITS = {'sniffer/config/sniffer.json': {'antes': 'de2a6b26608fac1b22aefbb031d10f55ea63bbc3b11d7d20a8695da7f74fc433', 'despues': '8bbd2bf251c9ef4e84f60216594323a52b1c955561334011fe3ad115622091dc', 'rep': [('    "user_features": [\n      "ddos_feature_group",\n      "ransomware_feature_group",\n      "rf_feature_group",\n      "internal_traffic_feature_group"\n    ],\n', ''), ('  "feature_groups": {\n    "ddos_feature_group": {\n      "count": 83,\n      "reference": "config/features/ddos_83_features.json",\n      "description": "DDOS detection features including packet rates, flag patterns, timing analysis"\n    },\n    "ransomware_feature_group": {\n      "count": 20,\n      "reference": "config/features/ransomware_20_features.json",\n      "description": "Ransomware detection features (20 critical features optimized for RPi)"\n    },\n    "rf_feature_group": {\n      "count": 23,\n      "reference": "config/features/rf_23_features.json",\n      "description": "Random Forest general attack detection (Level 1)"\n    },\n    "internal_traffic_feature_group": {\n      "count": 4,\n      "reference": "config/features/internal_4_features.json",\n      "description": "Internal traffic classification features"\n    }\n  },\n', '')]}, 'sniffer/include/config_manager.hpp': {'antes': '73b14a360fee7873b3b7915c9fe09f75851dfb08bb659dc151749196c9176c10', 'despues': '59e7a60cf8869f3424e43172cd7cd2e4ad349f7c041b8fbcacc6e5646f8633c2', 'rep': [('// Feature group configuration\nstruct FeatureGroupConfig {\n    int count;\n    std::string reference;\n    std::string description;\n};\n\n', ''), ('    std::vector<std::string> user_features;\n\n    struct MemoryManagement {', '\n    struct MemoryManagement {'), ('    std::unordered_map<std::string, FeatureGroupConfig> feature_groups;\n', '')]}, 'sniffer/src/userspace/config_manager.cpp': {'antes': '100e579ea1742e174eeb5a3e82aa5038644c9ca7a045f6ad94e941a13cd9ee82', 'despues': '6b320c33e2a39cf63cd87140bde0ab6a7ba16159927b492badc1df763314ebbb', 'rep': [('\n    // Parse feature groups\n    if (root.isMember("feature_groups")) {\n        for (const auto& group_name : root["feature_groups"].getMemberNames()) {\n            auto group_json = root["feature_groups"][group_name];\n            FeatureGroupConfig group;\n            group.count = group_json.get("count", 0).asInt();\n            group.reference = group_json.get("reference", "").asString();\n            group.description = group_json.get("description", "").asString();\n            config->feature_groups[group_name] = group;\n        }\n    }\n\n', '\n'), ('    user.user_features = parse_string_array(user_json["user_features"]);\n', ''), ('    // Validate feature groups\n    for (const auto& [name, group] : config.feature_groups) {\n        if (group.count <= 0) {\n            errors.push_back("Feature group \'" + name + "\' must have count > 0");\n        }\n        if (group.reference.empty()) {\n            errors.push_back("Feature group \'" + name + "\' must have reference file");\n        }\n    }\n\n', ''), ('    // Feature groups\n    std::cout << "Feature groups: " << config.feature_groups.size() << " defined" << std::endl;\n    for (const auto& [name, group] : config.feature_groups) {\n        std::cout << "  - " << name << ": " << group.count << " features" << std::endl;\n    }\n\n', '')]}, 'sniffer/include/config_types.h': {'antes': 'f45e8649be01c9396ce99c4c11fbb98a5df9fea9dc5ee1ca1bb18855613847e1', 'despues': 'fb5b0a4a4a5784e4d62637fadda49590a58dda3e5abce8e6b8d1074ffc1e3ec6', 'rep': [('struct FeatureGroup {\n    std::string name;\n    int count;\n    std::string reference;\n    std::string description;\n    bool loaded = false;\n};\n\n', ''), ('        std::vector<std::string> user_features;\n        std::string flow_eviction_policy;', '        std::string flow_eviction_policy;'), ('    // Feature groups - TODOS REQUERIDOS\n    std::unordered_map<std::string, FeatureGroup> feature_groups;\n\n', ''), ('void validate_feature_groups_section(const Json::Value& root, StrictSnifferConfig& config, bool verbose);\n', '')]}, 'sniffer/src/userspace/config_types.cpp': {'antes': 'ebf11c8b8d723ec5c4790a825bc827c547c4098bf28e04f4980e495b4b89db09', 'despues': '9ba7d2a0e05fd63698120506b1191081f23179ccb522ad86ee1745a75bce1630', 'rep': [('void validate_feature_groups_section(const Json::Value&, StrictSnifferConfig&, bool) {}\n', '')]}, 'sniffer/CMakeLists.txt': {'antes': 'adda78c0ee38657b37ad30c745ed812ea13549821ab096cdef43ef9aaabce461', 'despues': '544807174ff12187885ca146b55e2025d43abf744f54b73fc8b966f6f568ff18', 'rep': [('file(MAKE_DIRECTORY ${CMAKE_BINARY_DIR}/config/features)\n', ''), ('# Create feature group placeholder files\nset(FEATURE_GROUPS ddos_83 ransomware_83 rf_23 internal_4)\nforeach(GROUP ${FEATURE_GROUPS})\n    file(WRITE ${CMAKE_BINARY_DIR}/config/features/${GROUP}_features.json "[]")\nendforeach()\n\n', '')]}}
BORRAR = {'sniffer/config/features/rf_23_features.json': '3388cd1e99744b1f7966960d630932efc6ddbbf34fceae58a997b067ade0803d', 'sniffer/config/features/ransomware_20_features.json': '146d7826b15c2b6618f63fa393a9575878f1f4381c227d1adca0593caefc8ce8'}

def die(m):
    print("ABORTA: " + m)
    sys.exit(1)

def sha_b(b):
    return hashlib.sha256(b).hexdigest()

def sha(p):
    return sha_b(open(p, "rb").read())

if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
    die("uso: --check | --apply")
APPLY = sys.argv[1] == "--apply"
if not (os.path.isfile("Makefile") and os.path.isfile("sniffer/config/sniffer.json")):
    die("no estoy en la raiz del repo")
if all(sha(p) == e["despues"] for p, e in EDITS.items()) and not any(os.path.exists(p) for p in BORRAR):
    print("[YA APLICADO] feature_groups fuera. Nada que hacer.")
    sys.exit(0)
nuevos = {}
for p, e in EDITS.items():
    s = sha(p)
    if s != e["antes"]:
        die(f"{p} sha256 {s} no es el de partida (estado mixto o fichero cambiado)")
    t = open(p, encoding="utf-8").read()
    for a, b in e["rep"]:
        if t.count(a) != 1:
            die(f"{p}: ancla x{t.count(a)} (esperado 1): {a[:60]!r}")
        t = t.replace(a, b)
    if p.endswith(".json"):
        try:
            json.loads(t)
        except ValueError as ex:
            die(f"{p}: el resultado no seria JSON valido: {ex}")
    if sha_b(t.encode("utf-8")) != e["despues"]:
        die(f"{p}: el resultado no tendria el sha256 esperado")
    nuevos[p] = (t, len(e["rep"]))
for p, h in BORRAR.items():
    if not os.path.exists(p) or sha(p) != h:
        die(f"{p} falta o no es el esperado")
for p, (_, n) in nuevos.items():
    print(f"[OK] editar {p} ({n} bloques)")
for p in BORRAR:
    print(f"[OK] borrar {p}")
if not APPLY:
    print("[CHECK] todo valida; nada escrito. Repite con --apply.")
    sys.exit(0)
for p, (t, _) in nuevos.items():
    tmp = p + ".d307tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(t)
    os.replace(tmp, p)
for p in BORRAR:
    os.remove(p)
if os.path.isdir("sniffer/config/features") and not os.listdir("sniffer/config/features"):
    os.rmdir("sniffer/config/features")
if any(sha(p) != e["despues"] for p, e in EDITS.items()) or any(os.path.exists(p) for p in BORRAR):
    die("verificacion posterior fallida")
print("[APLICADO] feature_groups fuera (falta git rm de los 2 JSON al commitear).")
