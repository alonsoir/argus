#!/usr/bin/env python3
"""DAY286 H2 v2: episodios fechados + EWMA con y sin congelacion.
Congelar: si ratio >= K la EWMA no se actualiza (max N ventanas seguidas).
Uso: d286_h2_ewma_freeze.py CSV > salida.txt"""
import csv, sys, time
from collections import Counter

FLOOD_KEY = ("192.168.100.1", "17")
FLOOD_MIN_PPS = 50.0
CONFIGS = [  # (alpha, suelo, K o None, N)
    (0.1, 5.0, None, 0), (0.1, 5.0, 5.0, 60),
    (0.1, 10.0, None, 0), (0.1, 10.0, 5.0, 60),
    (0.05, 10.0, None, 0), (0.05, 10.0, 5.0, 60),
]
OFFSETS = [0, 1, 2, 5, 10, 30]

def pct(v, p):
    if not v:
        return float("nan")
    return v[min(len(v) - 1, int(p / 100.0 * len(v)))]

rows = []
with open(sys.argv[1], newline="") as f:
    for x in csv.DictReader(f):
        wm = int(x["window_ms"])
        if wm <= 0:
            continue
        rows.append((int(x["ts_ms"]), (x["dst_ip"], x["proto"]),
                     int(x["d_pkts"]) * 1000.0 / wm))
rows.sort(key=lambda t: t[0])

def run(alpha, floor, k, nmax):
    state = {}  # key -> [ewma, last_ts, frozen_windows]
    eps, cur, last_fts = [], None, None
    amb, amb_hi = [], Counter()
    for ts, key, pps in rows:
        if key in state:
            ewma, last, fz = state[key]
            gap = max(1, round((ts - last) / 1000.0))
            prior = ewma * (1.0 - alpha) ** (gap - 1)
        else:
            prior, fz = 0.0, 0
        ratio = pps / max(prior, floor)
        if k is not None and ratio >= k and fz < nmax:
            state[key] = [prior, ts, fz + 1]
        else:
            state[key] = [(1.0 - alpha) * prior + alpha * pps, ts, 0]
        if key == FLOOD_KEY and pps >= FLOOD_MIN_PPS:
            if cur is None or (ts - last_fts) > 2500:
                cur = {"t0": ts, "pps": [], "r": []}
                eps.append(cur)
            cur["pps"].append(pps)
            cur["r"].append(ratio)
            last_fts = ts
        else:
            amb.append(ratio)
            if ratio >= 10:
                amb_hi[key] += 1
    amb.sort()
    return eps, amb, amb_hi

eps0, _, _ = run(*CONFIGS[0])
print(f"filas={len(rows)} episodios={len(eps0)}")
print("idx fecha_local ventanas pps_med")
for i, e in enumerate(eps0):
    t = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(e["t0"] / 1000.0))
    print(f"ep{i} {t} {len(e['r'])} {pct(sorted(e['pps']),50):.1f}")

for cfg in CONFIGS:
    alpha, floor, k, nmax = cfg
    eps, amb, amb_hi = run(*cfg)
    onset = sum(1 for e in eps if max(e["r"][:3]) >= 5)
    meds = []
    for o in OFFSETS:
        v = sorted(e["r"][o] for e in eps if o < len(e["r"]))
        meds.append(f"{o}:{pct(v,50):.1f}(n={len(v)})")
    tag = f"K={k} N={nmax}" if k is not None else "sin congelar"
    print(f"\n=== alpha={alpha} suelo={floor} {tag} ===")
    print(f"  episodios con ratio>=5 en sus 3 primeras ventanas: {onset}/{len(eps)}")
    print(f"  mediana del ratio por desplazamiento: {' '.join(meds)}")
    print(f"  ambiente n={len(amb)} p99={pct(amb,99):.2f} p99.9={pct(amb,99.9):.2f} "
          f"max={amb[-1]:.2f} >=5:{sum(r>=5 for r in amb)} >=10:{sum(r>=10 for r in amb)}")
    print(f"  claves ambiente con mas ventanas >=10: "
          + ", ".join(f"{d}/{p}:{c}" for (d, p), c in amb_hi.most_common(5)))
