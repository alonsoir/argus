#!/usr/bin/env python3
"""DAY280 — episodios de una víctima en el CSV del lector, SOLO del último arranque
(tras el último reinicio de 'win'), con su rango de win (= seq en [VICTIM-WINDOW]).
Uso: python3 scripts/d280_episodes.py [csv] [victim] [proto] [gap_ms] [min_pkts]"""
import sys, csv, datetime as dt
a = sys.argv[1:] + [None] * 5
CSVF = a[0] or "/vagrant/logs/lab/ddos_windows.csv"
V = a[1] or "192.168.100.1"; P = a[2] or "17"
GAP = int(a[3] or 5000); MINP = int(a[4] or 1000)
rows = list(csv.DictReader(open(CSVF)))
start, prev = 0, None
for i, r in enumerate(rows):
    w = int(r["win"])
    if prev is not None and w < prev: start = i
    prev = w
key = [(int(r["win"]), int(r["ts_ms"]), int(r["d_pkts"])) for r in rows[start:]
       if r["dst_ip"] == V and r["proto"] == P]
hm = lambda ms: dt.datetime.fromtimestamp(ms / 1000).strftime("%H:%M:%S")
eps, cur = [], []
for k in key:
    if cur and k[1] - cur[-1][1] > GAP:
        eps.append(cur); cur = []
    cur.append(k)
if cur: eps.append(cur)
print(f"último arranque: win {rows[start]['win']}..{rows[-1]['win']}  víctima {V}/{P}")
print("EP  win_ini  win_fin  ventanas  suma  pkts/vent  t_ini  t_fin")
for i, e in enumerate(eps, 1):
    s = sum(x[2] for x in e)
    if s < MINP: continue
    print(f"{i}  {e[0][0]}  {e[-1][0]}  {len(e)}  {s}  {s/len(e):.1f}  {hm(e[0][1])}  {hm(e[-1][1])}")
print(f"último win del CSV: {rows[-1]['win']}")
