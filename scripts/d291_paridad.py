#!/usr/bin/env python3
"""DAY291 — puerta de paridad [DDOS-HYST-D291]: EWMA offline (ddos_windows.csv) vs vivo (dataset del sniffer).
Serie por ventana de la clave victima: (victim_pps, victim_rate_ratio) en float32 con %g (igual que el
escritor). Se colapsan repeticiones consecutivas en las dos fuentes y se exige que la serie del dataset
sea un tramo contiguo IDENTICO de la offline. Parametros = los de sniffer.json (por argumento)."""
import argparse, csv, struct

ap = argparse.ArgumentParser()
ap.add_argument("--windows", default="/vagrant/logs/lab/ddos_windows.csv")
ap.add_argument("--dataset", required=True)
ap.add_argument("--run", type=int, default=-1, help="arranque de ddos_windows.csv (-1 = ultimo)")
ap.add_argument("--victim", default="192.168.100.1")
ap.add_argument("--proto", default="17")
ap.add_argument("--alpha", type=float, default=0.1)
ap.add_argument("--tau-s", type=float, default=3600.0)
ap.add_argument("--k-in", type=float, default=3.0)
ap.add_argument("--k-out", type=float, default=1.5)
ap.add_argument("--warm", type=int, default=30)
ap.add_argument("--floor", type=float, default=10.0)
ap.add_argument("--evict", type=int, default=3600)
ap.add_argument("--interval-ms", type=float, default=1000.0)
a = ap.parse_args()
ALPHA_SLOW = (a.interval_ms / 1000.0) / a.tau_s
print("params:", vars(a), "alpha_lento=%.6g" % ALPHA_SLOW)

def g(x):
    return "%g" % struct.unpack("f", struct.pack("f", x))[0]

def collapse(seq):
    out = []
    for p in seq:
        if not out or out[-1] != p:
            out.append(p)
    return out

runs, cur, last_win = [], [], None
with open(a.windows, newline="") as f:
    for x in csv.DictReader(f):
        w = int(x["win"])
        if last_win is not None and w < last_win:
            runs.append(cur); cur = []
        last_win = w
        if int(x["window_ms"]) > 0:
            cur.append(x)
runs.append(cur)
rows = runs[a.run]
print("arranques=%d usado=%d ventanas_del_arranque=%d" % (len(runs), a.run, len(rows)))

s = {"ewma": 0.0, "last": 0, "seen": 0, "press": False}
off = []
for r in rows:
    if r["dst_ip"] != a.victim or r["proto"] != a.proto:
        continue
    win = int(r["win"])
    pps = int(r["d_pkts"]) * 1000.0 / int(r["window_ms"])
    if s["seen"] > 0 and win > s["last"] and win - s["last"] > a.evict:
        s = {"ewma": 0.0, "last": 0, "seen": 0, "press": False}
    prior = 0.0
    if s["seen"] > 0:
        gap = win - s["last"] if win > s["last"] else 1
        prior = s["ewma"]
        for _ in range(1, gap):
            prior *= (1.0 - a.alpha)
    ratio = pps / (prior if prior > a.floor else a.floor)
    if not s["press"] and s["seen"] >= a.warm and ratio >= a.k_in:
        s["press"] = True
    elif s["press"] and ratio < a.k_out:
        s["press"] = False
    al = ALPHA_SLOW if s["press"] else a.alpha
    s["ewma"] = (1.0 - al) * prior + al * pps
    s["last"] = win
    s["seen"] += 1
    off.append((g(pps), g(ratio)))

ds = []
with open(a.dataset, newline="") as f:
    for x in csv.DictReader(f):
        if x["event_kind"] != "0" or x["dst_ip"] != a.victim or x["proto"] != a.proto:
            continue
        if float(x["victim_pps"]) <= 0:
            continue
        ds.append((g(float(x["victim_pps"])), g(float(x["victim_rate_ratio"]))))

offc, dsc = collapse(off), collapse(ds)
print("offline: ventanas_clave=%d colapsadas=%d | dataset: filas=%d colapsadas=%d" % (len(off), len(offc), len(ds), len(dsc)))
if not dsc:
    print("FALLO: dataset sin filas de la clave"); raise SystemExit(1)
best = None
for i, p in enumerate(offc):
    if p != dsc[0]:
        continue
    mism = [j for j in range(len(dsc)) if i + j >= len(offc) or offc[i + j] != dsc[j]]
    if best is None or len(mism) < len(best[1]):
        best = (i, mism)
    if not mism:
        break
if best is None:
    print("FALLO: el primer par del dataset %s no aparece en la serie offline" % (dsc[0],)); raise SystemExit(1)
i, mism = best
print("alineacion: offset_offline=%d comparadas=%d DISCREPANCIAS=%d sobrantes_offline_al_final=%d" % (
    i, len(dsc), len(mism), max(0, len(offc) - (i + len(dsc)))))
for j in mism[:5]:
    o = offc[i + j] if i + j < len(offc) else None
    print("  j=%d dataset=%s offline=%s" % (j, dsc[j], o))
print("PARIDAD OK" if not mism else "PARIDAD ROTA")
