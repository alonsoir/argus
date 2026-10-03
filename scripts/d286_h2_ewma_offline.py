#!/usr/bin/env python3
"""DAY286 H2: EWMA por victima offline sobre ddos_windows.csv.
ratio = pps_ventana / max(ewma_previa, suelo); ventanas ausentes de una clave = ceros.
Uso: d286_h2_ewma_offline.py CSV > salida.txt"""
import csv, sys

FLOOD_KEY = ("192.168.100.1", "17")
FLOOD_MIN_PPS = 50.0
ALPHAS = [0.01, 0.05, 0.1, 0.3]
FLOORS = [1.0, 5.0, 10.0]
OFFSETS = [0, 1, 2, 3, 5, 7, 10, 30, 60, 100]
MAX_EP_DETAIL = 5

def pct(sorted_vals, p):
    if not sorted_vals:
        return float("nan")
    i = min(len(sorted_vals) - 1, int(p / 100.0 * len(sorted_vals)))
    return sorted_vals[i]

rows, skipped = [], 0
with open(sys.argv[1], newline="") as f:
    for x in csv.DictReader(f):
        wm = int(x["window_ms"])
        if wm <= 0:
            skipped += 1
            continue
        rows.append((int(x["ts_ms"]), (x["dst_ip"], x["proto"]),
                     int(x["d_pkts"]) * 1000.0 / wm))
rows.sort(key=lambda t: t[0])
keys = {k for _, k, _ in rows}
print(f"filas={len(rows)} saltadas_window_ms0={skipped} claves={len(keys)} "
      f"span_s={(rows[-1][0]-rows[0][0])/1000.0:.0f}")

for alpha in ALPHAS:
    for floor in FLOORS:
        state = {}
        episodes, cur, last_flood_ts = [], None, None
        ambient = []
        for ts, key, pps in rows:
            if key in state:
                ewma, last = state[key]
                gap = max(1, round((ts - last) / 1000.0))
                prior = ewma * (1.0 - alpha) ** (gap - 1)
            else:
                prior = 0.0
            ratio = pps / max(prior, floor)
            state[key] = ((1.0 - alpha) * prior + alpha * pps, ts)
            if key == FLOOD_KEY and pps >= FLOOD_MIN_PPS:
                if cur is None or (ts - last_flood_ts) > 2500:
                    cur = []
                    episodes.append(cur)
                cur.append((pps, ratio))
                last_flood_ts = ts
            else:
                ambient.append(ratio)
        ambient.sort()
        print(f"\n=== alpha={alpha} suelo={floor} ===")
        print(f"episodios={len(episodes)}")
        for i, ep in enumerate(episodes[:MAX_EP_DETAIL]):
            pp = sorted(p for p, _ in ep)
            rs = [r for _, r in ep]
            at = " ".join(f"{o}:{rs[o]:.1f}" for o in OFFSETS if o < len(rs))
            print(f"  ep{i} ventanas={len(ep)} pps_med={pct(pp,50):.1f} "
                  f">=5:{sum(r>=5 for r in rs)} >=2:{sum(r>=2 for r in rs)} | {at}")
        print(f"  ambiente n={len(ambient)} p50={pct(ambient,50):.2f} "
              f"p90={pct(ambient,90):.2f} p99={pct(ambient,99):.2f} "
              f"p99.9={pct(ambient,99.9):.2f} max={ambient[-1]:.2f} "
              f">=5:{sum(r>=5 for r in ambient)} >=10:{sum(r>=10 for r in ambient)}")
