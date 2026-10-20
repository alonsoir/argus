#!/usr/bin/env python3
# DAY303 [ARGUS-LAB-E2E-D303]: los E2E del lab de esta rama como objetivos make con PASA/FALLA, dentro de EMECAS.
# Decision de Alonso DAY303: EMECAS estricto y determinista; si pasa, el pipeline E2E funciona como se diseno.
#  - lab-e2e-prep: deja el client recien creado como lo necesitan los E2E (alias .51 en eth1, idempotente, y la
#    MAC de .1 en la tabla de vecinos de eth1, que d302_mitigacion_client.sh lee). Se llama antes de CADA E2E.
#  - lab-e2e-reinicio-{antes,ordenada,kill9}: d300_reinicio_e2e.sh + d303_veredicto_reinicio.sh (R1-R3)
#  - lab-e2e-protegidos: d300_protegidos_e2e.sh + d303_veredicto_protegidos.sh (P1-P5)
#  - lab-e2e-mitigacion: d302_mitigacion_e2e.sh (sus criterios y su rc ya existen; trap restaura el JSON)
#  - lab-e2e: los cinco en serie; para al primer FALLA
#  - emecas: lab-e2e tras test-e2e-synthetic
# Validado antes (V1, DAY303): veredictos sobre las corridas de DAY300 -> antes2/ordenada/kill9/protegidos PASA,
# antes original (corte mal puesto, 997 marcados) FALLA solo en R3.
# Uso (Mac, raiz del repo): python3 scripts/timebase/d303_patch_labe2e.py --check | --apply
import difflib
import re
import sys
from pathlib import Path

MARCA = "[ARGUS-LAB-E2E-D303]"
MK = Path("Makefile")
NECESARIOS = [
    "scripts/timebase/d300_reinicio_e2e.sh", "scripts/timebase/d300_reinicio_client.sh",
    "scripts/timebase/d300_protegidos_e2e.sh", "scripts/timebase/d300_protegidos_client.sh",
    "scripts/timebase/d302_mitigacion_e2e.sh", "scripts/timebase/d302_mitigacion_client.sh",
    "scripts/timebase/d302_mitigacion_analisis.sh", "scripts/timebase/lab_corrida_defender.sh",
    "scripts/timebase/d303_veredicto_reinicio.sh", "scripts/timebase/d303_veredicto_protegidos.sh",
    "day288_esperar_estable.sh",
]
if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
    print("uso: d303_patch_labe2e.py --check | --apply")
    sys.exit(2)
mk = MK.read_text(encoding="utf-8")
if MARCA in mk:
    print("YA APLICADO, no se toca nada")
    sys.exit(1)
errores = []
for f in NECESARIOS:
    if not Path(f).is_file():
        errores.append("falta " + f)
for t in ("lab-clock-step", "pipeline-start", "pipeline-stop", "sniffer-start", "sniffer-stop"):
    if not re.search(r"^" + re.escape(t) + r":", mk, flags=re.M):
        errores.append("Makefile: no encuentro el objetivo " + t + " (lo usan los E2E)")
if re.search(r"^lab-e2e[a-z-]*:", mk, flags=re.M):
    errores.append("Makefile: ya existe algun objetivo lab-e2e*")

DIA = "$(LAB_E2E_DIA)"
VR = "/vagrant/scripts/timebase/d303_veredicto_reinicio.sh"
VP = "/vagrant/scripts/timebase/d303_veredicto_protegidos.sh"
bloque = [
    "# " + MARCA + " E2E del lab con PASA/FALLA (decision de Alonso DAY303: EMECAS estricto y determinista).",
    "# Cada objetivo prepara el client, corre el E2E (que para al primer fallo) y aplica su veredicto (rc 0 = PASA).",
    "# Corridas en logs/lab/$(LAB_E2E_DIA)/lab_*/. Duracion total de lab-e2e: ~60 min.",
    "LAB_E2E_DIA ?= emecas_e2e",
    ".PHONY: lab-e2e lab-e2e-prep lab-e2e-reinicio-antes lab-e2e-reinicio-ordenada lab-e2e-reinicio-kill9 lab-e2e-protegidos lab-e2e-mitigacion",
    "lab-e2e-prep:",
    "\t@echo \"[LAB-E2E] client: alias 192.168.100.51 en eth1 y MAC de 192.168.100.1 en la tabla de vecinos\"",
    "\t@vagrant ssh client -c \"ip -4 addr show dev eth1 | grep -q 192.168.100.51 || sudo ip addr add 192.168.100.51/24 dev eth1; "
    "ping -c 3 -W 1 -I eth1 192.168.100.1 > /dev/null 2>&1; ip -4 addr show dev eth1 | grep -q 192.168.100.51 && "
    "ip neigh show 192.168.100.1 dev eth1 | grep -q lladdr && ip neigh show 192.168.100.1 dev eth1\" "
    "|| { echo \"[LAB-E2E] FALLA: client sin alias .51 o sin MAC de .1\"; exit 1; }",
    "",
]
for modo in ("antes", "ordenada", "kill9"):
    n = "lab_reinicio_" + modo
    bloque += [
        "lab-e2e-reinicio-" + modo + ":",
        "\t@$(MAKE) lab-e2e-prep",
        "\tDIA=" + DIA + " bash scripts/timebase/d300_reinicio_e2e.sh " + modo + " " + n,
        "\t@vagrant ssh defender -c \"bash " + VR + " " + modo + " /vagrant/logs/lab/" + DIA + "/" + n + "\"",
        "",
    ]
bloque += [
    "lab-e2e-protegidos:",
    "\t@$(MAKE) lab-e2e-prep",
    "\tDIA=" + DIA + " bash scripts/timebase/d300_protegidos_e2e.sh lab_protegidos",
    "\t@vagrant ssh defender -c \"bash " + VP + " /vagrant/logs/lab/" + DIA + "/lab_protegidos\"",
    "",
    "lab-e2e-mitigacion:",
    "\t@$(MAKE) lab-e2e-prep",
    "\tDIA=" + DIA + " bash scripts/timebase/d302_mitigacion_e2e.sh lab_mitigacion",
    "",
    "lab-e2e:",
    "\t@echo \"[LAB-E2E] inicio $$(date '+%F %T'): reinicio antes/ordenada/kill9, protegidos, mitigacion\"",
    "\t$(MAKE) lab-e2e-reinicio-antes",
    "\t$(MAKE) lab-e2e-reinicio-ordenada",
    "\t$(MAKE) lab-e2e-reinicio-kill9",
    "\t$(MAKE) lab-e2e-protegidos",
    "\t$(MAKE) lab-e2e-mitigacion",
    "\t@echo \"[LAB-E2E] PASA los cinco E2E del lab $$(date '+%F %T')\"",
    "",
]
nuevo = "\n".join(bloque) + "\n"

# emecas: lab-e2e tras test-e2e-synthetic, dentro del bloque emecas: (hasta emecas++:)
i = mk.find("\nemecas:")
j = mk.find("\nemecas++: emecas\n")
mk2 = mk
if i < 0 or j < 0 or j < i or mk.count("\nemecas:") != 1:
    errores.append("Makefile: no delimito el bloque emecas: ... emecas++:")
else:
    trozo = mk[i:j]
    ancla = "\t$(MAKE) test-e2e-synthetic\n"
    if trozo.count(ancla) != 1:
        errores.append("emecas: se esperaba 1 '$(MAKE) test-e2e-synthetic' dentro del bloque, hay " + str(trozo.count(ancla)))
    else:
        trozo2 = trozo.replace(ancla, ancla + "\t$(MAKE) lab-e2e\n", 1)
        # el bloque nuevo, justo antes de emecas++ (tras emecas-frescura si esta ahi)
        mk2 = mk[:i] + trozo2 + "\n" + nuevo + mk[j:]

if errores:
    print("PARO: el patcher no toca nada.")
    for e in errores:
        print(" -", e)
    sys.exit(1)
print("=== " + sys.argv[1] + ": anclas encontradas, 0 errores ===")
print("".join(difflib.unified_diff(mk.splitlines(True), mk2.splitlines(True),
                                   fromfile="a/Makefile", tofile="b/Makefile", n=1)))
if sys.argv[1] == "--apply":
    MK.write_text(mk2, encoding="utf-8")
    print("APLICADO", MARCA)
