#!/usr/bin/env python3
# DAY303 [ARGUS-GATE-EMECAS-D303]: EMECAS ejecuta la puerta del firewall con root.
# En emecas, tras test-all: test-firewall-e2e (falla con cualquier Skipped o gtest de 0 tests) y
# test-firewall-perf (mide y valida la medida). Heredan el PROFILE de la corrida (variables de linea de ordenes).
# Uso (Mac, raiz del repo): python3 scripts/timebase/d303_patch_emecas.py --check | --apply
import difflib
import sys
from pathlib import Path

MARCA = "[ARGUS-GATE-EMECAS-D303]"
MK = Path("Makefile")
if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
    print("uso: d303_patch_emecas.py --check | --apply")
    sys.exit(2)
mk = MK.read_text(encoding="utf-8")
if MARCA in mk:
    print("YA APLICADO, no se toca nada")
    sys.exit(1)
errores = []
VIEJO = "\t$(MAKE) test-all\n\t$(MAKE) test-e2e-synthetic\n"
NUEVO = ("\t$(MAKE) test-all\n"
         "\t$(MAKE) test-firewall-e2e\n"
         "\t$(MAKE) test-firewall-perf\n"
         "\t$(MAKE) test-e2e-synthetic\n")
CAB = "\nemecas:\n"
COM = ("\n# " + MARCA + " tras test-all, la puerta del firewall con root: test-firewall-e2e (falla con\n"
       "# cualquier test saltado o una ejecucion de gtest de 0 tests) y test-firewall-perf (da numeros del\n"
       "# entorno; falla solo si la medida es invalida). Heredan el PROFILE de la corrida: make emecas+++ PROFILE=production\n"
       "emecas:\n")
for viejo, n in ((VIEJO, mk.count(VIEJO)), (CAB, mk.count(CAB))):
    if n != 1:
        errores.append(f"Makefile: se esperaba 1 aparicion de {viejo!r}, hay {n}")
if errores:
    print("PARO: el patcher no toca nada.")
    for e in errores:
        print(" -", e)
    sys.exit(1)
mk2 = mk.replace(VIEJO, NUEVO, 1).replace(CAB, COM, 1)
print(f"=== {sys.argv[1]}: anclas encontradas, 0 errores ===")
print("".join(difflib.unified_diff(mk.splitlines(True), mk2.splitlines(True),
                                   fromfile="a/Makefile", tofile="b/Makefile", n=2)))
if sys.argv[1] == "--apply":
    MK.write_text(mk2, encoding="utf-8")
    print("APLICADO", MARCA)
