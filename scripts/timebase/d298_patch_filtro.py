#!/usr/bin/env python3
# DAY298: el filtro de tcpdump del ayudante del orquestador se puede cambiar con FILTRO en el entorno.
# Por defecto, el de DAY297 (origenes .50/.51/.61): las corridas existentes no cambian. Atomico. --check | --apply
import os, subprocess, sys, tempfile

F = "scripts/timebase/lab_corrida_defender.sh"
MARCA = "DAY298-FILTRO"
V = "FILTRO='src host 192.168.100.50 or src host 192.168.100.51 or src host 192.168.100.61'\n"
N = ("FILTRO=${FILTRO:-src host 192.168.100.50 or src host 192.168.100.51 or src host 192.168.100.61}"
     "  # [DAY298-FILTRO] cambiable desde el entorno\n")

def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
        sys.exit("uso: d298_patch_filtro.py --check | --apply")
    txt = open(F).read()
    if MARCA in txt:
        sys.exit(f"NO APLICABLE: {F} ya lleva {MARCA}")
    if txt.count(V) != 1:
        sys.exit(f"NO APLICABLE: la linea FILTRO aparece {txt.count(V)} veces, se esperaba 1")
    nuevo = txt.replace(V, N)
    with tempfile.NamedTemporaryFile("w", suffix=".sh", delete=False) as t:
        t.write(nuevo)
    r = subprocess.run(["bash", "-n", t.name], capture_output=True, text=True)
    os.unlink(t.name)
    if r.returncode != 0:
        sys.exit(f"NO APLICABLE: bash -n falla:\n{r.stderr}")
    if sys.argv[1] == "--check":
        print("CHECK OK: FILTRO cambiable desde el entorno; bash -n limpio")
        return
    modo = os.stat(F).st_mode
    with open(F + ".tmp", "w") as o:
        o.write(nuevo)
    os.chmod(F + ".tmp", modo)
    os.replace(F + ".tmp", F)
    print("APLICADO [DAY298-FILTRO]")

main()
