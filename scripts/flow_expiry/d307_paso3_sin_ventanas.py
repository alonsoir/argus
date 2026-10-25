#!/usr/bin/env python3
# DAY307 paso 3 — fuera el TimeWindowManager por flujo y la clase FeatureExtractor (codigo sin lector vivo).
#  - flow_manager.hpp: fuera el #include de time_window_manager.hpp, el miembro time_windows, su creacion en el
#    constructor (queda FlowStatistics() = default) y su actualizacion por paquete.
#  - sharded_flow_manager.cpp: fuera el comentario que lo menciona.
#  - test_sharded_flow_full_contract.cpp: fuera el TEST 3 (comprobaba que time_windows no fuera nulo) y la linea
#    que lo contaba en el TEST 4 (7 -> 6 vectores contados).
#  - sniffer/CMakeLists.txt: fuera feature_extractor.cpp (1) y time_window_manager.cpp (5).
#  - Borra time_window_manager.{hpp,cpp}, feature_extractor.{hpp,cpp}, feature_extractor.cpp.fase1 y .fase2.
# Valida TODO antes de escribir NADA (sha256 de partida de cada fichero, anclas unicas, sha256 del bloque del
# TEST 3, sha256 de llegada). Reconoce el estado "ya aplicado".
# Uso (Mac, raiz del repo): python3 scripts/flow_expiry/d307_paso3_sin_ventanas.py --check | --apply
import hashlib, os, sys

def die(m):
    print("ABORTA: " + m)
    sys.exit(1)

def sha_b(b):
    return hashlib.sha256(b).hexdigest()

def sha(p):
    return sha_b(open(p, "rb").read())

EDITS = {
    "sniffer/include/flow_manager.hpp": {
        "antes": "eaa205cf2a371685afefbef4d481285ed1b066eabf2eb2457a0d2289cc9a5024",
        "despues": "b2e10d1c560802f0672f16139963a04aabef34001f1ff05bcfcb0bc5e53dbaa4",
        "rep": [
            ('#include "time_window_manager.hpp"\n', ''),
            ('    // ============ FASE 3: TIME WINDOW MANAGER ============\n'
             '    std::unique_ptr<TimeWindowManager> time_windows;\n\n', ''),
            ('    // Constructor\n    FlowStatistics() {\n'
             '        time_windows = std::make_unique<TimeWindowManager>();\n    }\n',
             '    // Constructor\n    FlowStatistics() = default;\n'),
            ('        // ⭐ FASE 3: Update time windows\n        if (time_windows) {\n'
             '            time_windows->add_packet(pkt.timestamp, pkt.packet_len, is_fwd);\n        }\n', ''),
        ],
    },
    "sniffer/src/flow/sharded_flow_manager.cpp": {
        "antes": "6259cf99ca06c225d41eb2094fb0e31c2e6fc9ab8b1d4378d6beace69084e6fb",
        "despues": "918050a86d89775f2a0337a253202ff338aad0b83142cb82e9829566fbe3b368",
        "rep": [('        // time_windows will be created by FlowStatistics() constructor\n', '')],
    },
    "sniffer/tests/test_sharded_flow_full_contract.cpp": {
        "antes": "817deff70712927cbf831d64e4b637733ca6c4fad24e95082d1ff8c5667ab597",
        "despues": "6960e7961f91c5c49d424412030c9b7d065876899397dc441341299d2b74607c",
        "rep": [('    total_fields += 7;\n', '    total_fields += 6;\n'),
                ('    if (stats.time_windows != nullptr) populated_fields++;\n', '')],
        "bloque": ("// ============================================================================\n"
                   "// TEST 3: TimeWindowManager integration (FASE 3)\n",
                   "// ============================================================================\n// TEST 4:",
                   "8d3dedf9f16e0f574726c6a06eda5659df47b2c5d3ca85d6423045568acc96c8"),
    },
    "sniffer/CMakeLists.txt": {
        "antes": "8aa489c1d8101150e5007175fc063be0e91aed872dbf461d722b05b184144cca",
        "despues": "adda78c0ee38657b37ad30c745ed812ea13549821ab096cdef43ef9aaabce461",
        "todas": [("        src/userspace/feature_extractor.cpp\n", 1),
                  ("        src/userspace/time_window_manager.cpp\n", 5)],
    },
}
BORRAR = {
    "sniffer/include/time_window_manager.hpp": "1350b132150a8c191ac12d8cf925aa51d0046045a438d0bd6592e4dd16de5f04",
    "sniffer/src/userspace/time_window_manager.cpp": "cd5b0a57ff218b25521a88c9bb97c93a791ce12f418543b61928a8e0b2d065a2",
    "sniffer/include/feature_extractor.hpp": "dab199600210888682c9c8e005a9556d1d0beee5c3ded9c7837b8de1e547a03f",
    "sniffer/src/userspace/feature_extractor.cpp": "58552efb3a3c68bde718ebf2944569321f056954555092f79702d0f8f824218e",
    "sniffer/src/userspace/feature_extractor.cpp.fase1": "fad7a1d7e0d7eb5b46027c9f8e00e9c0654767f1325d7c865cef77443cf9e3dc",
    "sniffer/src/userspace/feature_extractor.cpp.fase2": "fad7a1d7e0d7eb5b46027c9f8e00e9c0654767f1325d7c865cef77443cf9e3dc",
}

if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
    die("uso: --check | --apply")
APPLY = sys.argv[1] == "--apply"
if not (os.path.isfile("Makefile") and os.path.isdir("sniffer/src/userspace")):
    die("no estoy en la raiz del repo")

if all(sha(p) == e["despues"] for p, e in EDITS.items()) and not any(os.path.exists(p) for p in BORRAR):
    print("[YA APLICADO] paso 3 hecho. Nada que hacer.")
    sys.exit(0)

nuevos = {}
for p, e in EDITS.items():
    s = sha(p)
    if s != e["antes"]:
        die(f"{p} sha256 {s} no es el de partida (estado mixto o fichero cambiado)")
    t = open(p, encoding="utf-8").read()
    for a, b in e.get("rep", []):
        if t.count(a) != 1:
            die(f"{p}: ancla x{t.count(a)} (esperado 1): {a[:60]!r}")
        t = t.replace(a, b)
    for a, n in e.get("todas", []):
        if t.count(a) != n:
            die(f"{p}: '{a.strip()}' x{t.count(a)} (esperado {n})")
        t = t.replace(a, "")
    if "bloque" in e:
        ini, fin, bsha = e["bloque"]
        if t.count(ini) != 1 or t.count(fin) != 1:
            die(f"{p}: anclas del TEST 3 x{t.count(ini)}/x{t.count(fin)}")
        i, j = t.index(ini), t.index(fin)
        if j <= i or sha_b(t[i:j].encode("utf-8")) != bsha:
            die(f"{p}: el bloque del TEST 3 no es el esperado")
        t = t[:i] + t[j:]
    if sha_b(t.encode("utf-8")) != e["despues"]:
        die(f"{p}: el resultado no tendria el sha256 esperado")
    nuevos[p] = t
for p, h in BORRAR.items():
    if not os.path.exists(p) or sha(p) != h:
        die(f"{p} falta o no es el esperado")

for p in EDITS:
    print(f"[OK] editar {p}")
for p in BORRAR:
    print(f"[OK] borrar {p}")
if not APPLY:
    print("[CHECK] todo valida; nada escrito. Repite con --apply.")
    sys.exit(0)

for p, t in nuevos.items():
    tmp = p + ".d307tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(t)
    os.replace(tmp, p)
for p in BORRAR:
    os.remove(p)
if any(sha(p) != e["despues"] for p, e in EDITS.items()) or any(os.path.exists(p) for p in BORRAR):
    die("verificacion posterior fallida")
print("[APLICADO] paso 3 (falta git rm de los 6 ficheros borrados al commitear).")
