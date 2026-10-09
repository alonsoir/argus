#!/usr/bin/env python3
# DAY292 — mide una corrida de la batería caliente. Uso: day292_medir.py [CSV]
# Columnas (0-idx): 0 ts_ns, 2 src, 3 dst, 6 proto, 7 kind, 9 mean_size, 12 flow_pkts, 14 ratio, 15 victim_pps, 17 old_class
import csv, glob, os, sys, collections
F = sys.argv[1] if len(sys.argv) > 1 else max(glob.glob("/vagrant/logs/lab/ddos_dataset/ddos_dataset_*.csv"), key=os.path.getmtime)
R = list(csv.reader(open(F)))[1:]
print("fichero=" + F)
print("event_kind:", dict(collections.Counter(r[7] for r in R)))
R = [r for r in R if r[7] == "0" and r[3] == "192.168.100.1"]
QUIEN = {"192.168.100.51": "BASE", "192.168.100.50": "ATQ"}
PROTO = {"6": "tcp", "17": "udp"}
def q(r): return QUIEN.get(r[2], "otro") + "/" + PROTO.get(r[6], r[6])
atq = [r for r in R if r[2] == "192.168.100.50"]
if not atq:
    sys.exit("SIN filas de .50 hacia .1")
t0 = min(float(r[0]) for r in atq); t1 = max(float(r[0]) for r in atq)
print(f"ataque: {len(atq)} filas, {(t1-t0)/1e9:.1f} s")
g = collections.defaultdict(list)
for r in R:
    b = int((float(r[0]) - t0) // 1e10)
    g[(max(b, -99) if b >= -3 else -99, q(r))].append(r)
def linea(etq, L):
    m = lambda i: sum(float(r[i]) for r in L) / len(L)
    old = 100.0 * sum(r[17] == "1" for r in L) / len(L)
    print(f"{etq:>6}  {L[0] and q(L[0]):10s} {len(L):5d}  ratio={m(14):7.3f}  pps={m(15):6.1f}  size={m(9):7.1f}  fpk={m(12):7.2f}  old1={old:5.1f}%")
print(" tramo  quien          n")
for k in sorted(g):
    linea("previo" if k[0] == -99 else str(k[0]), g[k])
print("--- durante el ataque [primera, última fila de .50]")
dur = collections.defaultdict(list)
for r in R:
    if t0 <= float(r[0]) <= t1:
        dur[q(r)].append(r)
for k in sorted(dur):
    linea("total", dur[k])
