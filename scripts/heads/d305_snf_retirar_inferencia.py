#!/usr/bin/env python3
# DAY305 — [SNIFFER-NO-INFER-D305] retirar la inferencia del sniffer (run_ml_detection).
# Medido DAY305: el sniffer ejecutaba en cada evento de flujo las cabezas embebidas del ml-detector (las mismas
# fuentes, ml-detector/src/*_detector.cpp) y su resultado se sobrescribia en populate_protobuf_event antes de
# enviar; nadie aguas abajo lo usaba. Decision de Alonso: el sniffer solo recoge rasgos y, si esta encendido, el
# fast-path; la inferencia de las cabezas vive en el ml-detector.
# Retira: run_ml_detection + 4 extract_*_features del consumidor + 4 detectores thread_local + 5 contadores (stats,
# foto, reset, print) + [ML-PHASE]/[ML-TIME] + umbrales ml_defender (sniffer.json, ConfigManager, StrictSnifferConfig,
# puente de main.cpp) + las 4 fuentes de detectores del CMakeLists del sniffer + 2 bloques de los scripts de estres
# que buscaban "ML Defender Embedded Detectors". Los extractores de rasgos (MLDefenderExtractor) NO se tocan.
# Cada bloque se localiza por ancla de inicio y fin (unicas) y se comprueba su sha256 antes de tocar nada.
# Uso, raiz del repo:  python3 d305_snf_retirar_inferencia.py --check | --apply
#   (--calibrar imprime los sha256 de cada bloque; solo para preparar el parche)
import hashlib, json, sys

MARK = "[SNIFFER-NO-INFER-D305]"
RC  = "sniffer/src/userspace/ring_consumer.cpp"
RH  = "sniffer/include/ring_consumer.hpp"
CTH = "sniffer/include/config_types.h"
CTC = "sniffer/src/userspace/config_types.cpp"
CMH = "sniffer/include/config_manager.hpp"
CMC = "sniffer/src/userspace/config_manager.cpp"
MN  = "sniffer/src/userspace/main.cpp"
CMK = "sniffer/CMakeLists.txt"
SJ  = "sniffer/config/sniffer.json"
ST1 = "scripts/stress/monitor_stress.sh"
ST2 = "scripts/stress/stress_test_8h.sh"

# (fichero, inicio, fin_incluido_o_None, reemplazo, sha256_esperado_o_None)
# fin None -> el bloque es exactamente 'inicio'. fin "<<EOF>>" -> hasta antes de 'tope' (ver S9).
OPS = []
def S(f, start, end, rep, sha=None):
    OPS.append((f, start, end, rep, sha))

# ---------------- ring_consumer.cpp
S(RC, "\t// ML Defender embedded detectors (thread-local, zero-lock architecture)\n",
      "\tthread_local ml_defender::InternalDetector RingBufferConsumer::internal_detector_;\n", "")
S(RC, "    std::cout << \"[ML Defender] Thresholds (JSON): \"\n",
      "              << \" Internal=\" << config_.ml_defender.thresholds.internal\n              << std::endl;\n", "")
S(RC, "    // DAY 77: NaN-first — orden correcto: NaN -> populate(reales) -> run_ml_detection\n", None,
      f"    // DAY 77: NaN-first — orden correcto: NaN -> populate(reales). {MARK} sin inferencia en el sniffer\n")
S(RC, "    // ML DEFENDER: Embedded Detectors Inference (Phase 1, Day 4)\n", None,
      f"    // {MARK} el sniffer solo recoge rasgos; la inferencia de las cabezas vive en el ml-detector\n")
S(RC, "    const_cast<RingBufferConsumer*>(this)->run_ml_detection(proto_event);\n", None, "")
S(RC, "\n\t// ML Defender embedded detection stats\n",
      "    snapshot.ml_detection_time_us = stats_.ml_detection_time_us.load();\n", "")
S(RC, "\t// ML Defender embedded detectors statistics\n",
      "                  << avg_ml_time << \" μs\\n\";\n    }\n\n", "")
S(RC, "    stats_.ddos_attacks_detected = 0;\n", "    stats_.ml_detection_time_us = 0;\n\n", "")
S(RC, "// ============================================================================\n"
      "// ML DEFENDER: Feature Extraction Functions (Phase 1, Day 4)\n",
      "<<HASTA>>} // namespace sniffer", "")

# ---------------- ring_consumer.hpp
S(RH, "// ML Defender embedded detectors\n#include \"ml_defender/ddos_detector.hpp\"\n",
      "#include \"ml_defender/internal_detector.hpp\"\n", "")
S(RH, "\n    std::atomic<uint64_t> ddos_attacks_detected{0};\n",
      "    std::atomic<uint64_t> ml_detection_time_us{0};\n", "")
S(RH, "    // embebbed models\n    uint64_t ddos_attacks_detected;\n",
      "    uint64_t ml_detection_time_us;\n", "")
S(RH, "    // Layer 3 - ML Defender Embedded Detectors (thread-local, zero-lock)\n",
      "    thread_local static ml_defender::InternalDetector internal_detector_;\n\n", "")
S(RH, "\n    // ML Defender feature extraction\n",
      "    void run_ml_detection(protobuf::NetworkSecurityEvent& proto_event);\n", "")

# ---------------- config_types.h / .cpp
S(CTH, "    // ML Defender thresholds — DAY 80 (Phase1-Day4-CRITICAL CERRADO)\n", "    } ml_defender;\n", "")
S(CTC, "    // DAY 80 ✅ ml_defender thresholds desde JSON (Phase1-Day4-CRITICAL CERRADO)\n",
       "              << \" Internal=\" << config.ml_defender.internal << std::endl;\n", "")

# ---------------- config_manager.hpp / .cpp
S(CMH, "// ML Defender configuration (Phase 1, Day 5)\nstruct MLDefenderConfig {\n",
       "    } validation;\n};\n\n", "")
S(CMH, "    MLDefenderConfig ml_defender;\n", None, "")
S(CMH, "    static MLDefenderConfig parse_ml_defender(const Json::Value& ml_defender_json);\n", None, "")
S(CMC, "\n    config->ml_defender = parse_ml_defender(root.get(\"ml_defender\", Json::Value{}));\n", None, "\n")
S(CMC, "// ============================================================================\n"
       "// ML Defender Configuration Parser (Phase 1, Day 5 - No hardcoding)\n",
       "              << \"Internal=\" << config.thresholds.internal << std::endl;\n\n    return config;\n}\n\n", "")

# ---------------- main.cpp
S(MN, "// DAY 80 ✅ ml_defender thresholds — JSON is the LAW (Phase1-Day4-CRITICAL CERRADO)\n",
      "        sniffer_config.ml_defender.thresholds.internal   = g_config.ml_defender.internal;\n\n", "")

# ---------------- CMakeLists.txt
S(CMK, "        ../ml-detector/src/ddos_detector.cpp\n        ../ml-detector/src/ransomware_detector.cpp\n"
       "        ../ml-detector/src/traffic_detector.cpp\n        ../ml-detector/src/internal_detector.cpp\n", None, "")
S(CMK, "# ML Defender Phase 1 sources\n", None,
       f"# ML Defender Phase 1 sources: solo extraccion de rasgos. {MARK} el sniffer ya no compila los detectores\n")

# ---------------- sniffer.json
S(SJ, "  \"ml_defender\": {\n", "      \"fallback_threshold\": 0.75\n    }\n  },\n", "")

# ---------------- scripts de estres
S(ST1, "    # Últimas detecciones\n    echo \"🛡️  Last ML Detections:\"\n",
       "        grep \"ML Defender Embedded Detectors:\" \"${TEST_DIR}/logs/sniffer.log\" -A 5 | tail -6 | sed 's/^/   /'\n"
       "    else\n        echo \"   Waiting for data...\"\n    fi\n    echo \"\"\n", "")
S(ST2, "        # Show last detection stats\n",
       "                echo \"${LAST_STATS}\" | sed 's/^/     /'\n            fi\n        fi\n", "")

# sha256 esperados por bloque (indice -> sha); se rellenan con --calibrar sobre la copia de referencia
SHA = {
    0: "5b613049c5387956d508ff60408ad5fff9d7fcb0bac1811045003bc981ce3dda",  # sniffer/src/userspace/ring_consumer.cpp (5 lineas)
    1: "fc0ed8d0b0eb5c0d66e2b859411772ebf8dcdd4ec39541168f96b90d2724b9b6",  # sniffer/src/userspace/ring_consumer.cpp (6 lineas)
    2: "50d0464d0db7954a34d528b2c00e6d4a35f8f871c6dd47826c1ef98c1272da1c",  # sniffer/src/userspace/ring_consumer.cpp (1 lineas)
    3: "2ec1591919d82b19484e4c2d2dc3e1fd1e1bf5352253eb5fe0ac6a55aa0db5f7",  # sniffer/src/userspace/ring_consumer.cpp (1 lineas)
    4: "4bb9ee7ed5e6599cd52e82d92f01d75b9cd3b4fdf8e4bbc85905ae605cff857e",  # sniffer/src/userspace/ring_consumer.cpp (1 lineas)
    5: "ac0ed06472f2ecc9e4eec2f985e1c98788dd1bd703e1871fd1a28aaea036f66c",  # sniffer/src/userspace/ring_consumer.cpp (7 lineas)
    6: "b751b0763cddb6fad4846e8731c3da8bcd8bdbb861487385fa956c3248025445",  # sniffer/src/userspace/ring_consumer.cpp (14 lineas)
    7: "c175e600391bfee761129ffbcb63ce44c0204450d9675e2c5ce6b53ae8646beb",  # sniffer/src/userspace/ring_consumer.cpp (6 lineas)
    8: "78ac03135fcc12991eb6cac1b9a941529e98cec5c01501cad9d7262656b2c692",  # sniffer/src/userspace/ring_consumer.cpp (287 lineas)
    9: "006127f13ca0c2f3f5ec43ffc5c39a59bbc8b19dba1d833bd33422b757d4c800",  # sniffer/include/ring_consumer.hpp (5 lineas)
    10: "5978fd4a64dec49a855ae693f7af2e892b9ad5a720101287d099c32fa70de675",  # sniffer/include/ring_consumer.hpp (6 lineas)
    11: "e850515c5115ea1e65edacd60a4ecb2e7b1704a9bd1c4be6a18197e9ed066942",  # sniffer/include/ring_consumer.hpp (6 lineas)
    12: "2a88d033ab34e2b947244221e68a16445558a6a3e0922bd021ea9df70b22eeeb",  # sniffer/include/ring_consumer.hpp (6 lineas)
    13: "62a1fdf2c3703eb99215cdb02b1bdc0181af689ac1287c9ce6fac9cb06e6881e",  # sniffer/include/ring_consumer.hpp (9 lineas)
    14: "7365a9a189fcd9db4a318e0a1837452691042cc01374dbc107e09e9529a61f74",  # sniffer/include/config_types.h (7 lineas)
    15: "185aa777fd925be52ccddf37f362ff8a296f08f534d974853246115a1edc6cfa",  # sniffer/src/userspace/config_types.cpp (13 lineas)
    16: "46b72de592411acb890fd7de167f2f45134111d352bd9b5d25e9bb68081bbcb3",  # sniffer/include/config_manager.hpp (16 lineas)
    17: "c8af98633f036baf5827d0d651bdb3239d5280def6790a2b2afe96d4f99c6478",  # sniffer/include/config_manager.hpp (1 lineas)
    18: "ca12b0a6b4aff920db3e85a5c3a06bcdf7380fd473d3ca0369a216d24e38df74",  # sniffer/include/config_manager.hpp (1 lineas)
    19: "d39fd76509c75a2996bb587001a291c702106c41350c608de9b2f5ac3f13917b",  # sniffer/src/userspace/config_manager.cpp (2 lineas)
    20: "ef6c18f055a90d42ba92c3bab6e00650b0dab989999873fe06aae6e8ad95d33e",  # sniffer/src/userspace/config_manager.cpp (62 lineas)
    21: "b5a3e4a9d3e14f0451ff7b5b78299a4d513c2f9322d4f3ef6efc4baf55b7cc18",  # sniffer/src/userspace/main.cpp (7 lineas)
    22: "85a16283e3a21e3f785cfa3355cd2ed548e634b8b268e87ad7047f41fc4509dc",  # sniffer/CMakeLists.txt (4 lineas)
    23: "7e3844f60c30da08cb0a920b550f01b6d2f083f085fa688d982973371801b619",  # sniffer/CMakeLists.txt (1 lineas)
    24: "b318596606f60cd01f42688668a91835ea34b9f16459806bcd7801095a9c2b1e",  # sniffer/config/sniffer.json (17 lineas)
    25: "d27377a413c17194ccb0506f519c87a5cbb262a88bfb41299f85b737da686d8e",  # scripts/stress/monitor_stress.sh (8 lineas)
    26: "99c32513a198ec75783774ea6bd9b6491fbd9809a6445d9a2b0843e6ca8aa9be",  # scripts/stress/stress_test_8h.sh (8 lineas)
}

def die(m):
    print("ABORTA (no se ha escrito nada): " + m)
    sys.exit(1)

def locate(t, start, end):
    if t.count(start) != 1:
        return None, f"ancla de inicio aparece {t.count(start)} veces"
    i = t.index(start)
    if end is None:
        return (i, i + len(start)), None
    if end.startswith("<<HASTA>>"):
        tope = end[len("<<HASTA>>"):]
        if t.count(tope) != 1:
            return None, f"tope aparece {t.count(tope)} veces"
        j = t.index(tope)
        return ((i, j), None) if j > i else (None, "tope antes del inicio")
    if t.count(end) != 1:
        return None, f"ancla de fin aparece {t.count(end)} veces"
    j = t.index(end)
    if j < i:
        return None, "ancla de fin antes del inicio"
    return (i, j + len(end)), None

def main():
    modo = sys.argv[1] if len(sys.argv) == 2 else ""
    if modo not in ("--check", "--apply", "--calibrar"):
        die("uso: python3 d305_snf_retirar_inferencia.py --check | --apply")
    files = sorted({op[0] for op in OPS})
    text = {}
    for f in files:
        try:
            text[f] = open(f, encoding="utf-8").read()
        except OSError as e:
            die(f"no puedo leer {f}: {e}")
        if MARK in text[f]:
            die(f"{f} ya contiene {MARK}: el parche ya se aplico (o a medias)")
    new = dict(text)
    for k, (f, start, end, rep, _) in enumerate(OPS):
        span, err = locate(new[f], start, end)
        if err:
            die(f"bloque {k} en {f}: {err}\n---\n{start}---")
        blk = new[f][span[0]:span[1]]
        h = hashlib.sha256(blk.encode("utf-8")).hexdigest()
        if modo == "--calibrar":
            print(f"    {k}: \"{h}\",  # {f} ({blk.count(chr(10))} lineas)")
        elif SHA.get(k) != h:
            die(f"bloque {k} en {f}: sha256 {h[:16]}… no coincide con el esperado: el fichero no es el medido")
        new[f] = new[f][:span[0]] + rep + new[f][span[1]:]
    if modo == "--calibrar":
        return
    # comprobaciones del resultado
    for f in (RC, RH, CTH, CTC, CMH, CMC, MN, CMK):
        for w in ("run_ml_detection", "ml_detection_time_us", "MLDefenderConfig", "ddos_attacks_detected",
                  "ml_defender.thresholds", "ml_defender/ddos_detector.hpp", "ml-detector/src/ddos_detector.cpp",
                  "[ML-PHASE]", "[ML-TIME]"):
            if w in new[f]:
                die(f"{f}: sigue apareciendo '{w}'")
    for w in ("ddos_detector_", "ransomware_detector_", "traffic_detector_", "internal_detector_"):
        if w in new[RC] or w in new[RH]:
            die(f"ring_consumer: sigue apareciendo '{w}'")
    if "populate_ml_defender_features(flow_stats, proto_event)" not in new[RC]:
        die("ring_consumer.cpp: ha desaparecido la recogida de rasgos (no debia tocarse)")
    if not new[RC].rstrip().endswith("} // namespace sniffer"):
        die("ring_consumer.cpp: el fichero ya no termina en el cierre del namespace")
    try:
        j = json.loads(new[SJ])
    except json.JSONDecodeError as e:
        die(f"sniffer.json resultante no parsea: {e}")
    if "ml_defender" in j or "fast_detector" not in j:
        die("sniffer.json: resultado inesperado (ml_defender sigue o fast_detector desaparecio)")
    for f in (ST1, ST2):
        if "ML Defender Embedded Detectors" in new[f]:
            die(f"{f}: sigue buscando 'ML Defender Embedded Detectors'")
    print(f"OK: {len(OPS)} bloques validados (ancla + sha256) en {len(files)} ficheros; sniffer.json valido")
    for f in files:
        print(f"   {f}: {new[f].count(chr(10)) - text[f].count(chr(10)):+d} lineas")
    if modo == "--check":
        print("--check: no se ha escrito nada")
        return
    for f in files:
        with open(f, "w", encoding="utf-8") as fh:
            fh.write(new[f])
    print("--apply: escrito. Siguiente: git rm de los 5 scripts d283/d284 y compilacion completa en production")

if __name__ == "__main__":
    main()
