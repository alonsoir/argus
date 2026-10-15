#!/usr/bin/env python3
# DAY298: la contabilidad del ayudante guarda tambien ml-detector.log (resumen [DDOS-V2]: pases de la etapa 1,
# ataque, sin_estado) y sniffer.log (linea [DDOS-HYST] con abs_pps, avisos de configuracion). Atomico. --check | --apply
import os, subprocess, sys, tempfile

F = "scripts/timebase/lab_corrida_defender.sh"
MARCA = "DAY298-LOGS"
V = '    cp /vagrant/logs/lab/firewall-agent.log "$D/$N/firewall-agent.log"\n'
N = (V + '    cp /vagrant/logs/lab/ml-detector.log "$D/$N/ml-detector.log"  # [DAY298-LOGS]\n'
         '    cp /vagrant/logs/lab/sniffer.log "$D/$N/sniffer.log"\n')

def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
        sys.exit("uso: d298_patch_contar_logs.py --check | --apply")
    txt = open(F).read()
    if MARCA in txt:
        sys.exit(f"NO APLICABLE: {F} ya lleva {MARCA}")
    if txt.count(V) != 1:
        sys.exit(f"NO APLICABLE: la copia de firewall-agent.log aparece {txt.count(V)} veces, se esperaba 1")
    nuevo = txt.replace(V, N)
    with tempfile.NamedTemporaryFile("w", suffix=".sh", delete=False) as t:
        t.write(nuevo)
    r = subprocess.run(["bash", "-n", t.name], capture_output=True, text=True)
    os.unlink(t.name)
    if r.returncode != 0:
        sys.exit(f"NO APLICABLE: bash -n falla:\n{r.stderr}")
    if sys.argv[1] == "--check":
        print("CHECK OK: contar copia tambien ml-detector.log y sniffer.log; bash -n limpio")
        return
    modo = os.stat(F).st_mode
    with open(F + ".tmp", "w") as o:
        o.write(nuevo)
    os.chmod(F + ".tmp", modo)
    os.replace(F + ".tmp", F)
    print("APLICADO [DAY298-LOGS]")

main()
