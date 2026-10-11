#!/usr/bin/env python3
"""DAY286 H2 v3: congelar la EWMA solo en claves calientes (>= W ventanas vistas).
Uso: d286_h2_ewma_warm.py CSV > salida.txt"""
import csv, sys
from collections import Counter

FLOOD_KEY = ("192.168.100.1", "17")
FLOOD_MIN_PPS = 50.0
ALPHA, FLOOR, K, NMAX = 0.1, 10.0, 5.0, 60
CONFIGS = [(ALPHA, FLOOR, None, 0, 0), (ALPHA, FLOOR, K, NMAX, 0),
           (ALPHA, FLOOR, K, NMAX, 10), (ALPHA, FLOOR, K, NMAX, 30),
           (0.05, FLOOR, K, NMAX, 10), (0.05, FLOOR, K, NMAX, 30)]
OFFSETS = [0, 1, 2, 5, 10, 30, 59, 61, 80, 100]

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

def run(alpha, floor, k, nmax, warm):
    state = {}  # key -> [ewma, last_ts, frozen, seen]
    eps, cur, last_fts = [], None, None
    amb, amb_hi = [], Counter()
    for ts, key, pps in rows:
        if key in state:
            ewma, last, fz, seen = state[key]
            gap = max(1, round((ts - last) / 1000.0))
            prior = ewma * (1.0 - alpha) ** (gap - 1)
        else:
            prior, fz, seen = 0.0, 0, 0
        ratio = pps / max(prior, floor)
        if k is not None and seen >= warm and ratio >= k and fz < nmax:
            state[key] = [prior, ts, fz + 1, seen + 1]
        else:
            state[key] = [(1.0 - alpha) * prior + alpha * pps, ts, 0, seen + 1]
        if key == FLOOD_KEY and pps >= FLOOD_MIN_PPS:
            if cur is None or (ts - last_fts) > 2500:
                cur = []
                eps.append(cur)
            cur.append(ratio)
            last_fts = ts
        else:
            amb.append(ratio)
            if ratio >= 10:
                amb_hi[key] += 1
    amb.sort()
    return eps, amb, amb_hi

def summary(label, eps):
    onset = sum(1 for e in eps if max(e[:3]) >= 5)
    meds = []
    for o in OFFSETS:
        v = sorted(e[o] for e in eps if o < len(e))
        if v:
            meds.append(f"{o}:{pct(v,50):.1f}(n={len(v)})")
    print(f"  {label}: arranque>=5 en 3 primeras: {onset}/{len(eps)} | mediana: {' '.join(meds)}")

for cfg in CONFIGS:
    alpha, floor, k, nmax, warm = cfg
    eps, amb, amb_hi = run(*cfg)
    tag = f"K={k} N={nmax} W={warm}" if k is not None else "sin congelar"
    print(f"\n=== alpha={alpha} suelo={floor} {tag} ===")
    summary("todos", eps)
    summary("largos(>=100)", [e for e in eps if len(e) >= 100])
    print(f"  ambiente n={len(amb)} p99={pct(amb,99):.2f} p99.9={pct(amb,99.9):.2f} "
          f"max={amb[-1]:.2f} >=5:{sum(r>=5 for r in amb)} >=10:{sum(r>=10 for r in amb)}")
    print("  claves ambiente con mas ventanas >=10: "
          + ", ".join(f"{d}/{p}:{c}" for (d, p), c in amb_hi.most_common(5)))
