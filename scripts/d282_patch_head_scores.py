#!/usr/bin/env python3
# DAY282 paso 1 — [HEAD-SCORES]: puntuacion de cada cabeza por evento, nivel info.
# Solo observacion: no toca final_score, final_decision, CSV ni esquema.
import re, sys, pathlib

p = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "/vagrant/ml-detector/src/zmq_handler.cpp")
src = p.read_text()
if "[HEAD-SCORES]" in src:
    sys.exit("ABORT: ya parcheado")

def once(a):
    n = src.count(a)
    if n != 1:
        sys.exit(f"ABORT: ancla aparece {n} veces: {a!r}")

def indent_of(a):
    i = src.index(a)
    return src[src.rfind("\n", 0, i) + 1:i]

GATE    = "if (l2_gate_open(force_all_heads_, label_l1, confidence_l1, config_.ml.thresholds.level1_attack)) {"
DDOS    = "auto ddos_result = ddos_detector_->predict(ddos_features);"
RANSOM  = "auto ransomware_result = ransomware_detector_->predict(ransomware_features);"
TRAFFIC = "auto traffic_result = traffic_detector_->predict(traffic_features);"
INTERN  = "auto internal_result = internal_detector_->predict(internal_features);"
PLUGIN  = "// ADR-012 PHASE 2d"

for a in (GATE, DDOS, RANSOM, TRAFFIC, INTERN, PLUGIN):
    once(a)

ind = indent_of(GATE)
src = src.replace(GATE,
    "// [HEAD-SCORES-D282] clase:puntuacion por cabeza; -1 = no evaluada\n"
    f"{ind}int hs_ddos_c = -1, hs_ransom_c = -1, hs_traffic_c = -1, hs_internal_c = -1;\n"
    f"{ind}double hs_ddos_p = 0.0, hs_ransom_p = 0.0, hs_traffic_p = 0.0, hs_internal_p = 0.0;\n"
    f"{ind}const bool hs_gate = l2_gate_open(force_all_heads_, label_l1, confidence_l1, config_.ml.thresholds.level1_attack);\n"
    f"{ind}if (hs_gate) {{")

def after(a, code):
    global src
    i = indent_of(a)
    src = src.replace(a, a + "\n" + i + code)

after(DDOS,    "hs_ddos_c = static_cast<int>(ddos_result.class_id); hs_ddos_p = ddos_result.ddos_prob;")
after(RANSOM,  "hs_ransom_c = static_cast<int>(ransomware_result.class_id); hs_ransom_p = ransomware_result.ransomware_prob;")
after(TRAFFIC, "hs_traffic_c = static_cast<int>(traffic_result.class_id); hs_traffic_p = traffic_result.probability;")
after(INTERN,  "hs_internal_c = static_cast<int>(internal_result.class_id); hs_internal_p = internal_result.suspicious_prob;")

i = indent_of(PLUGIN)
block = (
    "{\n"
    f"{i}    auto hs_fmt = [](int c, double p) -> std::string {{\n"
    f"{i}        if (c < 0) return std::string(\"na\");\n"
    f"{i}        char b[32]; std::snprintf(b, sizeof(b), \"%d:%.4f\", c, p); return std::string(b);\n"
    f"{i}    }};\n"
    f"{i}    logger_->info(\"[HEAD-SCORES] event={{}}, gate={{}}, l1={{}}:{{:.4f}}, fast={{:.4f}}, ddos={{}}, ransom={{}}, traffic={{}}, internal={{}}, cat={{}}\",\n"
    f"{i}                  event.event_id(), hs_gate ? 1 : 0, label_l1, confidence_l1, fast_score,\n"
    f"{i}                  hs_fmt(hs_ddos_c, hs_ddos_p), hs_fmt(hs_ransom_c, hs_ransom_p),\n"
    f"{i}                  hs_fmt(hs_traffic_c, hs_traffic_p), hs_fmt(hs_internal_c, hs_internal_p),\n"
    f"{i}                  event.threat_category());\n"
    f"{i}}}\n"
    f"{i}"
)
src = src.replace(PLUGIN, block + PLUGIN)

if "#include <cstdio>" not in src:
    m = re.search(r"^#include <[^>]+>\n", src, re.M)
    if not m:
        sys.exit("ABORT: no encuentro ningun #include <...>")
    src = src[:m.end()] + "#include <cstdio>\n" + src[m.end():]

p.write_text(src)
print("OK: parche aplicado en", p)
