#!/usr/bin/env python3
# DAY298: lab_frio.sh lanzaba el trafico del client con nohup dentro de vagrant ssh -c ... &; al cerrarse la
# sesion el subshell recibia SIGHUP antes de que nohup actuara y el trafico no salia (frio_base50_1: 0
# paquetes de .51). Ahora: setsid (sesion nueva), sesion abierta 2 s y comprobacion de que tcpreplay vive.
# Atomico. Uso, desde la raiz del repo: --check | --apply
import os, subprocess, sys, tempfile

F = "scripts/timebase/lab_frio.sh"
MARCA = "DAY298-SETSID"
V = ("  vagrant ssh client -c \"nohup bash -c '$CLI' > /tmp/$N.client.txt 2>&1 < /dev/null &\" || falla \"no arranca el client\"\n")
N = ("  # [DAY298-SETSID] setsid: sesion propia, sin la terminal de vagrant ssh (si no, SIGHUP al cerrar la sesion).\n"
     "  vagrant ssh client -c \"setsid nohup bash -c '$CLI' > /tmp/$N.client.txt 2>&1 < /dev/null & sleep 2; "
     "pgrep -af '^(sudo )?tcpreplay'\" || falla \"el trafico del client no esta en marcha (no hay tcpreplay vivo)\"\n")

def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
        sys.exit("uso: d298_patch_frio_cli.py --check | --apply")
    txt = open(F).read()
    if MARCA in txt:
        sys.exit(f"NO APLICABLE: {F} ya lleva {MARCA}")
    if txt.count(V) != 1:
        sys.exit(f"NO APLICABLE: la linea del client aparece {txt.count(V)} veces, se esperaba 1")
    nuevo = txt.replace(V, N)
    with tempfile.NamedTemporaryFile("w", suffix=".sh", delete=False) as t:
        t.write(nuevo)
    r = subprocess.run(["bash", "-n", t.name], capture_output=True, text=True)
    os.unlink(t.name)
    if r.returncode != 0:
        sys.exit(f"NO APLICABLE: bash -n falla:\n{r.stderr}")
    if sys.argv[1] == "--check":
        print("CHECK OK: lanzamiento con setsid + comprobacion de tcpreplay vivo; bash -n limpio")
        return
    with open(F + ".tmp", "w") as o:
        o.write(nuevo)
    os.replace(F + ".tmp", F)
    print("APLICADO [DAY298-SETSID]")

main()
