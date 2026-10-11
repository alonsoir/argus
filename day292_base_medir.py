#!/usr/bin/env python3
# DAY292 — mide un piloto de línea base sobre el CSV del escritor. Uso: day292_base_medir.py [CSV] [SRC]
import csv, glob, os, sys, collections
F = sys.argv[1] if len(sys.argv) > 1 else max(glob.glob("/vagrant/logs/lab/ddos_dataset/ddos_dataset_*.csv"), key=os.path.getmtime)
SRC = sys.argv[2] if len(sys.argv) > 2 else "192.168.100.51"
rows = list(csv.reader(open(F)))
hdr, rows = rows[0], rows[1:]
print("fichero=" + F)
print("cabecera:", " | ".join(f"{i+1}:{h}" for i, h in enumerate(hdr)))
k = hdr.index("event_kind") if "event_kind" in hdr else None
if k is not None:
    print("event_kind:", dict(collections.Counter(r[k] for r in rows)))
    rows = [r for r in rows if r[k] == "0"]
print("filas kind=0 por src:", collections.Counter(r[2] for r in rows).most_common(8))
mine = [r for r in rows if r[2] == SRC]
if not mine:
    sys.exit("SIN filas de " + SRC)
t0 = float(mine[0][0])
g = collections.defaultdict(list)
for r in rows:
    b = int((float(r[0]) - t0) // 1e10)
    g[(b, r[2] == SRC)].append(r)
print("tramo(10s)  quien  n  ratio_medio  pps_medio  size_medio(col?)")
for b in sorted({b for b, _ in g}):
    for es in (True, False):
        L = g.get((b, es))
        if not L:
            continue
        rr = sum(float(r[14]) for r in L) / len(L)
        pp = sum(float(r[15]) for r in L) / len(L)
        print(f"{b:4d}  {'BASE' if es else 'otro'}  {len(L):5d}  {rr:8.3f}  {pp:8.1f}")
