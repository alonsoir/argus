#!/usr/bin/env python3
# DAY303 [ARGUS-CLEAN-HOST-D303]: EMECAS limpia los build* DESDE EL MAC, con las VMs destruidas y ANTES de vagrant up.
# Medido DAY303 (EMECAS 12:16, K11):
#  - tools/provision.sh compila e instala durante vagrant up seed-client, crypto-transport, plugin-loader y
#    etcd-client en sus build/ de /vagrant (carpeta del Mac: sobrevive a vagrant destroy) -> compilaba sobre restos
#  - el clean-all tras vagrant up ([ARGUS-CLEAN-D303]) limpiaba tarde y borraba /usr/local/lib/libcrypto_transport.so
#    recien instalada -> check-system-deps FALLA en bootstrap [1/8]
# Cambios:
#  1. objetivo clean-host-builds: rm -rf en el Mac de los build/ y build-*/ que compilan el provisioning y el pipeline
#     (lista de clean-all + librerias de provision.sh). No toca adapters (se compilan en sus VMs), ni cmake-build-*
#     (CLion), ni nada fuera de esas rutas. Exige estar en la raiz del repo.
#  2. emecas: destroy -> clean-host-builds -> up -> sello -> bootstrap (fuera el clean-all tras up; en una VM recien
#     creada no hay nada que borrar en /usr/local). clean-all sigue existiendo para uso a mano.
# Uso (Mac, raiz del repo): python3 scripts/timebase/d303_patch_cleanhost.py --check | --apply
import difflib
import sys
from pathlib import Path

MARCA = "[ARGUS-CLEAN-HOST-D303]"
MK = Path("Makefile")
DIRS = [
    "sniffer/build", "sniffer/build-*", "ml-detector/build", "ml-detector/build-*",
    "rag-ingester/build", "rag-ingester/build-*", "firewall-acl-agent/build", "firewall-acl-agent/build-*",
    "etcd-server/build", "etcd-server/build-*", "tools/build", "tools/build-*", "rag/build", "rag/build-*",
    "common/build", "host-engine/build", "correlation-engine/build",
    "libs/seed-client/build", "libs/correlation-v1/build", "libs/host-domain-v1/build",
    "crypto-transport/build", "etcd-client/build", "plugin-loader/build",
]
if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
    print("uso: d303_patch_cleanhost.py --check | --apply")
    sys.exit(2)
mk = MK.read_text(encoding="utf-8")
if MARCA in mk:
    print("YA APLICADO, no se toca nada")
    sys.exit(1)
errores = []
if "\nclean-host-builds:" in mk:
    errores.append("Makefile: ya existe clean-host-builds")
for d in DIRS:
    base = d.split("/")[0]
    if not Path(base).is_dir():
        errores.append("no existe el directorio " + base + " (de " + d + ")")

viejo = "\tvagrant destroy -f\n\tvagrant up defender client suricata\n\t$(MAKE) clean-all\n"
nuevo = "\tvagrant destroy -f\n\t$(MAKE) clean-host-builds\n\tvagrant up defender client suricata\n"
if mk.count(viejo) != 1:
    errores.append("emecas: se esperaba 1 vez la secuencia destroy / up / clean-all, hay " + str(mk.count(viejo)))
mk2 = mk.replace(viejo, nuevo, 1)

objetivo = (
    "# " + MARCA + " limpieza de los build* en el MAC (carpeta del repo, sobrevive a vagrant destroy), con las\n"
    "# VMs destruidas y ANTES de vagrant up: provision.sh compila seed-client, crypto-transport, plugin-loader y\n"
    "# etcd-client en sus build/ durante el up (medido DAY303). No toca adapters ni cmake-build-* (CLion).\n"
    ".PHONY: clean-host-builds\n"
    "clean-host-builds:\n"
    "\t@test -f Makefile -a -d .git -a -f Vagrantfile || { echo \"[CLEAN-HOST] FALLA: no estoy en la raiz del repo\"; exit 1; }\n"
    "\t@echo \"[CLEAN-HOST] borrando en el Mac: " + " ".join(DIRS) + "\"\n"
    "\t@rm -rf " + " ".join(DIRS) + "\n"
    "\t@q=$$(ls -d " + " ".join(DIRS) + " 2>/dev/null | wc -l | tr -d ' '); "
    "if [ \"$$q\" != \"0\" ]; then echo \"[CLEAN-HOST] FALLA: quedan $$q directorios\"; exit 1; fi; "
    "echo \"[CLEAN-HOST] PASA: 0 directorios de build en el Mac\"\n"
    "\n"
)
if mk2.count("\nclean-all:") != 1:
    errores.append("Makefile: no encuentro un unico clean-all para colocar el objetivo delante")
else:
    mk2 = mk2.replace("\nclean-all:", "\n" + objetivo + "clean-all:", 1)

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
