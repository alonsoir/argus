#!/usr/bin/env python3
# DAY298: registra en el MANIFEST el gemelo de A2 (DAY297), ntp_reflex_10k_lab_src61.pcap. Comando establecido
# regenerandolo en el client DAY298: sha256 identico al fichero en uso. Atomico. Uso: --check | --apply
import os, sys

F = "scripts/dataset_lab/MANIFEST.md"
MARCA = "ntp_reflex_10k_lab_src61.pcap |"
FIN = "El de 17k sale de .51: requiere el mismo alias en el client que el de 5k.\n"
SECCION = """
## DAY297 — gemelo de A2 desde .61 (derivado, regenerable; registrado DAY298)

Mismo ataque NTP que `ntp_reflex_10k_lab.pcap` reescribiendo SOLO la IP de origen, en el client. Comando
establecido DAY298 regenerándolo: sha256 idéntico al fichero usado en A2.

    tcprewrite --infile=/vagrant/datasets/lab/ntp_reflex_10k_lab.pcap --outfile=/vagrant/datasets/lab/ntp_reflex_10k_lab_src61.pcap --srcipmap=192.168.100.50/32:192.168.100.61/32 --fixcsum

| pcap | paquetes | origen | sha256 |
|------|----------|--------|--------|
| ntp_reflex_10k_lab_src61.pcap | 10000 | 192.168.100.61 | a9b49ceeba95b3955bc1aca7e8bfe9e5ffaf231ca29fd341e7878b1e53261d36 |

Requiere el alias `sudo ip addr add 192.168.100.61/24 dev eth1` en el client (no persiste al reiniciar la VM).
"""

def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
        sys.exit("uso: d298_patch_manifest_src61.py --check | --apply")
    txt = open(F).read()
    if MARCA in txt:
        sys.exit(f"NO APLICABLE: {F} ya registra el pcap de .61")
    if not txt.endswith(FIN):
        sys.exit(f"NO APLICABLE: {F} no termina en la línea esperada (alguien lo cambió)")
    if sys.argv[1] == "--check":
        print("CHECK OK: se añadirá la sección del gemelo .61 al final del MANIFEST")
        return
    tmp = F + ".tmp"
    with open(tmp, "w") as o:
        o.write(txt + SECCION)
    os.replace(tmp, F)
    print("APLICADO: gemelo .61 registrado en el MANIFEST")

main()
