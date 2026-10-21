#!/usr/bin/env python3
# DAY303 [ARGUS-ESTABLE-LAB-D303]: el paso "esperar ESTABLE" de los tres E2E del lab pasa a
# scripts/timebase/d303_esperar_estable_lab.sh (fondo ICMP controlado solo durante la espera).
# Medido K13-K15: sin las 5 VMs el lab esta mudo y day288_esperar_estable.sh no ve sondeos (EMECAS 13:39 FALLA).
# Uso (Mac, raiz del repo): python3 scripts/timebase/d303_patch_estable.py --check | --apply
import difflib
import sys
from pathlib import Path

MARCA = "[ARGUS-ESTABLE-LAB-D303]"
ENVOLTORIO = Path("scripts/timebase/d303_esperar_estable_lab.sh")
FICHEROS = [Path("scripts/timebase/d300_reinicio_e2e.sh"), Path("scripts/timebase/d300_protegidos_e2e.sh"),
            Path("scripts/timebase/d302_mitigacion_e2e.sh")]
VIEJO = 'vagrant ssh defender -c "bash /vagrant/day288_esperar_estable.sh" || falla "esperar_estable"'
NUEVO = ('bash scripts/timebase/d303_esperar_estable_lab.sh || falla "esperar_estable"  # ' + MARCA +
         ' fondo ICMP controlado')
if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
    print("uso: d303_patch_estable.py --check | --apply")
    sys.exit(2)
errores = []
if not ENVOLTORIO.is_file():
    errores.append("falta " + str(ENVOLTORIO))
cambios = []
for f in FICHEROS:
    s = f.read_text(encoding="utf-8")
    if MARCA in s:
        errores.append(str(f) + ": YA APLICADO")
        continue
    n = s.count(VIEJO)
    if n != 1:
        errores.append(str(f) + ": se esperaba 1 vez la llamada a day288_esperar_estable.sh, hay " + str(n))
        continue
    cambios.append((f, s, s.replace(VIEJO, NUEVO, 1)))
if errores:
    print("PARO: el patcher no toca nada.")
    for e in errores:
        print(" -", e)
    sys.exit(1)
print("=== " + sys.argv[1] + ": anclas encontradas, 0 errores ===")
for f, a, b in cambios:
    print("".join(difflib.unified_diff(a.splitlines(True), b.splitlines(True),
                                       fromfile="a/" + str(f), tofile="b/" + str(f), n=0)))
if sys.argv[1] == "--apply":
    for f, a, b in cambios:
        f.write_text(b, encoding="utf-8")
    print("APLICADO", MARCA)
