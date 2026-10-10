#!/usr/bin/env python3
"""DAY293 — patcher atómico (todo o nada) [DDOS-V2-D293]:
 1) ml-detector/tests/CMakeLists.txt: registra test_ddos_v2_parity (tests/unit/) tras el bloque de test_l2_gate.
 2) ml-detector/include/ddos_dataset_writer.hpp: rasgos con %.9g (round-trip exacto de float) en vez de %.6g.
Uso: --check (no escribe) | --apply. Idempotente por la marca. No commitea."""
import sys
from pathlib import Path

MARK = "[DDOS-V2-D293]"
ROOT = Path("/vagrant")
CM = ROOT / "ml-detector/tests/CMakeLists.txt"
WR = ROOT / "ml-detector/include/ddos_dataset_writer.hpp"

BLOCK = """
# ── test_ddos_v2_parity — DAY293, paridad Python/C++ de la cabeza DDoS v2 factorizada [DDOS-V2-D293] ──
if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/unit/test_ddos_v2_parity.cpp")
    add_executable(test_ddos_v2_parity
            unit/test_ddos_v2_parity.cpp
    )
    target_include_directories(test_ddos_v2_parity PRIVATE
            ${CMAKE_CURRENT_SOURCE_DIR}/../include
    )
    target_compile_features(test_ddos_v2_parity PRIVATE cxx_std_20)
    target_compile_definitions(test_ddos_v2_parity PRIVATE
            DDOS_V2_PARITY_CSV="${CMAKE_CURRENT_SOURCE_DIR}/data/ddos_v2_paridad_muestra.csv"
    )
    add_test(NAME test_ddos_v2_parity COMMAND test_ddos_v2_parity)
endif()
"""

OLD_FMT = "%d,%.6g,%.6g,%.6g,%.6g,%.6g,%.6g,%.6g,%.6g,%.6f,%d"
NEW_FMT = "%d,%.9g,%.9g,%.9g,%.9g,%.9g,%.9g,%.9g,%.9g,%.6f,%d"
OLD_BUF = "        char buf[1024];\n"
NEW_BUF = "        char buf[1024];  // [DDOS-V2-D293] rasgos con %.9g: round-trip exacto de float (%.6g redondeaba)\n"


def fail(msg):
    print("ABORTA:", msg); sys.exit(1)


def plan():
    cm, wr = CM.read_text(), WR.read_text()
    out = {}
    if MARK in cm:
        print("CMakeLists: ya aplicado")
    else:
        lines = cm.splitlines(keepends=True)
        idx = [i for i, l in enumerate(lines) if l.strip() == "add_test(NAME test_l2_gate COMMAND test_l2_gate)"]
        if len(idx) != 1:
            fail("ancla add_test(test_l2_gate) encontrada %d veces" % len(idx))
        end = next((j for j in range(idx[0] + 1, len(lines)) if lines[j].strip() == "endif()"), None)
        if end is None:
            fail("no hay endif() tras test_l2_gate")
        out[CM] = "".join(lines[:end + 1]) + BLOCK + "".join(lines[end + 1:])
        print("CMakeLists: bloque test_ddos_v2_parity tras la línea %d" % (end + 1))
    if MARK in wr:
        print("writer: ya aplicado")
    else:
        if wr.count(OLD_FMT) != 1:
            fail("formato %%.6g encontrado %d veces" % wr.count(OLD_FMT))
        if wr.count(OLD_BUF) != 1:
            fail("ancla char buf[1024] encontrada %d veces" % wr.count(OLD_BUF))
        out[WR] = wr.replace(OLD_FMT, NEW_FMT).replace(OLD_BUF, NEW_BUF)
        print("writer: 8 rasgos %.6g -> %.9g")
    return out


if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
    fail("uso: --check | --apply")
cambios = plan()
if sys.argv[1] == "--apply":
    for p, txt in cambios.items():
        tmp = p.with_suffix(p.suffix + ".tmp_d293")
        tmp.write_text(txt)
    for p in cambios:
        p.with_suffix(p.suffix + ".tmp_d293").replace(p)
    print("APLICADO en %d fichero(s)" % len(cambios))
else:
    print("CHECK OK (nada escrito)")
