#!/usr/bin/env python3
# DAY292 — añade syn_flood_10k_lab al MANIFEST de scripts/dataset_lab. Atómico. Uso: --check | --apply
import sys
F = "/vagrant/scripts/dataset_lab/MANIFEST.md"
MARCA = "syn_flood_10k_lab"
A1 = "gen_syn_flood.py 5000 /vagrant/datasets/lab/syn_flood_5k_lab.pcap"
A2 = "| syn_flood_5k_lab.pcap |"
N1 = "    python3 /vagrant/scripts/dataset_lab/gen_syn_flood.py 10000 /vagrant/datasets/lab/syn_flood_10k_lab.pcap   # DAY292: batería caliente (90 s a 100 pps)"
N2 = "| syn_flood_10k_lab.pcap | 10000 | 54 B | igual que 5k; sus primeros 5000 paquetes son byte a byte el de 5k (misma semilla) | 65b590c76eb1484759616295cc65be46894621bc391d3649fb093d5150f4cd47 |"
modo = sys.argv[1] if len(sys.argv) > 1 else ""
if modo not in ("--check", "--apply"):
    sys.exit("uso: --check | --apply")
L = open(F).read().split("\n")
if any(MARCA in l for l in L):
    sys.exit("ABORTA: la marca ya está (ya aplicado)")
i1 = [i for i, l in enumerate(L) if A1 in l]
i2 = [i for i, l in enumerate(L) if l.startswith(A2)]
if len(i1) != 1 or len(i2) != 1:
    sys.exit(f"ABORTA: anclajes encontrados {len(i1)} y {len(i2)}, se esperaba 1 y 1")
for i, n in sorted([(i1[0], N1), (i2[0], N2)], reverse=True):
    L.insert(i + 1, n)
if modo == "--check":
    print(f"OK check: insertaría tras la línea {i1[0]+1} y tras la línea {i2[0]+1}")
    sys.exit(0)
open(F, "w").write("\n".join(L))
print("APLICADO")
