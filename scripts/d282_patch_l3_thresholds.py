#!/usr/bin/env python3
# DAY282 — DEBT-ML-DETECTOR-L3-THRESHOLDS-NOT-LOADED-001
# level3_web y level3_internal se declaraban pero nunca se leian del JSON (valor indeterminado, UB).
# 1) config_loader.cpp: get_required de ambos + impresion en el resumen de arranque
# 2) config_loader.hpp: inicializadores {} en los 6 umbrales (un olvido futuro = 0 ruidoso, no basura)
# 3) main.cpp: traffic imprime level3_web (antes level2_ddos); internal imprime level3_internal (antes level3_web)
# Idempotente; aborta sin escribir nada si alguna ancla no casa exactamente 1 vez.
import re, sys, pathlib

ROOT = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "/vagrant/ml-detector")
cpp  = ROOT / "src/config_loader.cpp"
hpp  = ROOT / "include/config_loader.hpp"
mainf = ROOT / "src/main.cpp"
s_cpp, s_hpp, s_main = cpp.read_text(), hpp.read_text(), mainf.read_text()

if '"level3_internal", "ml.thresholds"' in s_cpp:
    sys.exit("ABORT: ya parcheado")

def once(src, a, name):
    n = src.count(a)
    if n != 1:
        sys.exit(f"ABORT [{name}]: ancla aparece {n} veces: {a!r}")

def indent_of(src, a):
    i = src.index(a)
    return src[src.rfind("\n", 0, i) + 1:i]

# --- 1) config_loader.cpp ---
A_LOAD = 'config.ml.thresholds.level3_anomaly = get_required<float>(thresh, "level3_anomaly", "ml.thresholds");'
A_PRN  = 'std::cout << "  Level 3 Anomaly: " << config.ml.thresholds.level3_anomaly << "\\n\\n";'
once(s_cpp, A_LOAD, "cpp-load"); once(s_cpp, A_PRN, "cpp-print")
i = indent_of(s_cpp, A_LOAD)
s_cpp = s_cpp.replace(A_LOAD, A_LOAD +
    f'\n{i}config.ml.thresholds.level3_web = get_required<float>(thresh, "level3_web", "ml.thresholds");'
    f'\n{i}config.ml.thresholds.level3_internal = get_required<float>(thresh, "level3_internal", "ml.thresholds");')
i = indent_of(s_cpp, A_PRN)
s_cpp = s_cpp.replace(A_PRN,
    'std::cout << "  Level 3 Anomaly: " << config.ml.thresholds.level3_anomaly << "\\n";'
    f'\n{i}std::cout << "  Level 3 Web (traffic): " << config.ml.thresholds.level3_web << "\\n";'
    f'\n{i}std::cout << "  Level 3 Internal: " << config.ml.thresholds.level3_internal << "\\n\\n";')

# --- 2) config_loader.hpp ---
for name in ("level1_attack", "level2_ddos", "level2_ransomware", "level3_anomaly", "level3_web", "level3_internal"):
    a = f"float {name};"
    once(s_hpp, a, f"hpp-{name}")
    s_hpp = s_hpp.replace(a, f"float {name}{{}};")

# --- 3) main.cpp (primero internal, luego traffic, para no duplicar anclas) ---
A_INT = 'log->info("   Threshold: {}", config.ml.thresholds.level3_web);'
once(s_main, A_INT, "main-internal")
s_main = s_main.replace(A_INT, 'log->info("   Threshold: {}", config.ml.thresholds.level3_internal);')
pat = re.compile(r'(level3\.web\.features_count\);\s*\n\s*log->info\("   Threshold: \{\}", config\.ml\.thresholds\.)level2_ddos(\);)')
m = pat.findall(s_main)
if len(m) != 1:
    sys.exit(f"ABORT [main-traffic]: patron aparece {len(m)} veces")
s_main = pat.sub(r'\1level3_web\2', s_main)

cpp.write_text(s_cpp); hpp.write_text(s_hpp); mainf.write_text(s_main)
print("OK: config_loader.cpp, config_loader.hpp, main.cpp parcheados")
