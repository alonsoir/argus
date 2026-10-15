#!/usr/bin/env python3
# DAY298: anade al MANIFEST de scripts/dataset_lab los dos pcaps largos sin tuplas repetidas (A5 en vivo).
# Atomico: comprueba que no lleva la marca y que el fichero termina en la linea esperada; escribe a .tmp y renombra.
# Uso, desde la raiz del repo: --check | --apply
import os, sys

F = "scripts/dataset_lab/MANIFEST.md"
MARCA = "## DAY298"
FIN = "La línea base TCP desde .51 es tráfico vivo: `scripts/d281_tcp_upload.py HOST PORT KB_S SEG 192.168.100.51`.\n"
SECCION = """
## DAY298 — pcaps largos sin 5-tuplas repetidas (derivados, regenerables; A5 en vivo)

Los flujos del sniffer no caducan por inactividad (DEBT-SNIFFER-FLOW-EXPIRY-001): repetir una 5-tupla en
cualquier momento de la corrida acumula `flow_packet_count`, así que `tcpreplay --loop` no sirve para
corridas largas. `gen_disjunto.py` repite el original en vueltas: la vuelta 0 es idéntica y en cada vuelta
k>=1 cada tupla recibe un puerto destino nuevo (>=1024, no usado por su clase origen/sport/destino en el
original, lista barajada con semilla fija, nunca reutilizado). Origen, sport (firma de reflexión) y víctima
intactos; estructura interna de cada vuelta conservada; checksum UDP a 0 (válido en IPv4); timestamps
monótonos. Comprobado con un contador independiente (tcpdump): tuplas contadas = tuplas esperadas.
Límite: con origen, sport y destino fijos caben como mucho 64512 tuplas (~1050 s de ataque a 60 pps).
Ejecutados en el defender:

    python3 /vagrant/scripts/dataset_lab/gen_disjunto.py /vagrant/datasets/lab/ntp_reflex_10k_lab.pcap /vagrant/datasets/lab/ntp_reflex_63k_disjunto_lab.pcap 63000 298
    python3 /vagrant/scripts/dataset_lab/gen_disjunto.py /vagrant/datasets/lab/benign_dns_ntp_small_5k_lab_src51.pcap /vagrant/datasets/lab/benign_dns_ntp_17k_disjunto_src51.pcap 17100 298

| pcap | paquetes | trama | tuplas (max paq/tupla) | sha256 |
|------|----------|-------|------------------------|--------|
| ntp_reflex_63k_disjunto_lab.pcap | 63000 | 482 B | 58645 (4) | f3732ea337b8d50e0e67fe9a09ce234065304328c5c1188ab1e5f32b9d2272d0 |
| benign_dns_ntp_17k_disjunto_src51.pcap | 17100 | 80–250 B | 16634 (3) | 5badabb15c30d019b0cb98c3128e44b4c9aaf9d6f456932c81050466b823b0ea |

El de 17k sale de .51: requiere el mismo alias en el client que el de 5k.
"""

def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
        sys.exit("uso: d298_patch_manifest.py --check | --apply")
    txt = open(F).read()
    if MARCA in txt:
        sys.exit(f"NO APLICABLE: {F} ya contiene '{MARCA}'")
    if not txt.endswith(FIN):
        sys.exit(f"NO APLICABLE: {F} no termina en la línea esperada (alguien lo cambió)")
    if sys.argv[1] == "--check":
        print("CHECK OK: se añadirá la sección DAY298 (2 comandos, 2 filas) al final del MANIFEST")
        return
    tmp = F + ".tmp"
    with open(tmp, "w") as o:
        o.write(txt + SECCION)
    os.replace(tmp, F)
    print("APLICADO: sección DAY298 en el MANIFEST")

main()
