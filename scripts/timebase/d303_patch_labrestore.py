#!/usr/bin/env python3
# DAY303 [ARGUS-LAB-RESTORE-D303]: lab-e2e deja el pipeline ARRANCADO, como lo encontro.
# Medido (EMECAS 19:50, acto II, K18-K20): cada E2E del lab termina con make pipeline-stop (y el trap del d302
# tambien), asi que tras lab-e2e no hay etcd-server ni ml-detector. emecas++ acto II (test-e2e-synthetic-full)
# supone el pipeline en marcha: el injector no encuentra etcd-server en localhost:2379 y timeout corta (124).
# Antes de [ARGUS-LAB-E2E-D303] emecas acababa con test-e2e-synthetic, que deja el pipeline arrancado.
# Arreglo: al final de lab-e2e, $(MAKE) pipeline-start y comprobacion de que no hay componentes STOPPED.
# Uso (Mac, raiz del repo): python3 scripts/timebase/d303_patch_labrestore.py --check | --apply
import difflib
import sys
from pathlib import Path

MARCA = "[ARGUS-LAB-RESTORE-D303]"
MK = Path("Makefile")
if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
    print("uso: d303_patch_labrestore.py --check | --apply")
    sys.exit(2)
mk = MK.read_text(encoding="utf-8")
if MARCA in mk:
    print("YA APLICADO, no se toca nada")
    sys.exit(1)
viejo = ("\t$(MAKE) lab-e2e-mitigacion\n"
         "\t@echo \"[LAB-E2E] PASA los cinco E2E del lab $$(date '+%F %T')\"\n")
nuevo = ("\t$(MAKE) lab-e2e-mitigacion\n"
         "\t@echo \"[LAB-E2E] " + MARCA + " los E2E paran el pipeline: se deja arrancado, como se encontro\"\n"
         "\t$(MAKE) pipeline-start > /tmp/argus_lab_e2e_restore.txt 2>&1 || { tail -n 20 /tmp/argus_lab_e2e_restore.txt; "
         "echo \"[LAB-E2E] FALLA: pipeline-start al restaurar\"; exit 1; }\n"
         "\t@if grep -E 'STOPPED' /tmp/argus_lab_e2e_restore.txt; then echo \"[LAB-E2E] FALLA: componente STOPPED al restaurar\"; exit 1; fi\n"
         "\t@grep -E 'RUNNING' /tmp/argus_lab_e2e_restore.txt\n"
         "\t@echo \"[LAB-E2E] PASA los cinco E2E del lab $$(date '+%F %T')\"\n")
n = mk.count(viejo)
if n != 1:
    print("PARO: el patcher no toca nada.")
    print(" - se esperaba 1 vez el final de lab-e2e (lab-e2e-mitigacion + echo PASA), hay " + str(n))
    sys.exit(1)
mk2 = mk.replace(viejo, nuevo, 1)
print("=== " + sys.argv[1] + ": anclas encontradas, 0 errores ===")
print("".join(difflib.unified_diff(mk.splitlines(True), mk2.splitlines(True),
                                   fromfile="a/Makefile", tofile="b/Makefile", n=1)))
if sys.argv[1] == "--apply":
    MK.write_text(mk2, encoding="utf-8")
    print("APLICADO", MARCA)
