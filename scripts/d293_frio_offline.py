#!/usr/bin/env python3
"""DAY293 bloque 1d — víctima fría offline sobre ddos_windows.csv (contadores del kernel por ventana).
Misma pizarra que d291_histeresis_offline.py (histéresis D291: K_in, K_out, tau, warm, evict) en dos variantes:
  actual  = la EWMA aprende con alfa rápido desde la 1.ª ventana (código de hoy).
  congela = idea GLM: mientras la clave lleve < warm ventanas la EWMA NO aprende (referencia = suelo); después, como actual.
Por arranque y clave {lab_victim, proto}: ventanas vistas antes del ataque, ventanas activas (pps >= --umbral-activa),
activas en presión, ventanas hasta la 1.ª presión, presión residual tras la última activa, ratio máximo.
Coste: episodios y ventanas en presión en el resto de claves (ambiente). No toca el lab ni el sniffer."""
import argparse, csv
from datetime import datetime
from zoneinfo import ZoneInfo

ap = argparse.ArgumentParser()
ap.add_argument("--csv", default="/vagrant/logs/lab/ddos_windows.csv")
ap.add_argument("--desde", default="2026-10-05", help="fecha local (Europe/Madrid) mínima del arranque, AAAA-MM-DD")
ap.add_argument("--hasta", default="2026-10-05", help="fecha local máxima del arranque, AAAA-MM-DD")
ap.add_argument("--k-in", type=float, default=3.0)
ap.add_argument("--k-out", type=float, default=1.5)
ap.add_argument("--tau-s", type=float, default=3600.0)
ap.add_argument("--alpha", type=float, default=0.1)
ap.add_argument("--floor", type=float, default=10.0)
ap.add_argument("--warm", type=int, default=30)
ap.add_argument("--evict", type=int, default=3600)
ap.add_argument("--lab-victim", default="192.168.100.1")
ap.add_argument("--umbral-activa", type=float, default=20.0, help="pps de la clave del lab para contar la ventana como activa")
a = ap.parse_args()
ALPHA_SLOW = 1.0 / a.tau_s
TZ = ZoneInfo("Europe/Madrid")
VARIANTES = ("actual", "congela")
print("params:", vars(a), "alpha_lento=%.6g" % ALPHA_SLOW)

def loc(ms):
    return datetime.fromtimestamp(ms / 1000, tz=TZ).strftime("%Y-%m-%d %H:%M:%S")

runs, cur, last = [], [], None
with open(a.csv, newline="") as f:
    for x in csv.DictReader(f):
        w = int(x["win"])
        if last is not None and w < last:
            runs.append(cur); cur = []
        last = w
        if int(x["window_ms"]) > 0:
            cur.append(x)
runs.append(cur)
runs = [r for r in runs if r]
print("arranques_totales=%d" % len(runs))

def simulate(rows, congela):
    st, out = {}, []
    for r in rows:
        win = int(r["win"]); key = (r["dst_ip"], r["proto"])
        pps = int(r["d_pkts"]) * 1000.0 / int(r["window_ms"])
        s = st.get(key)
        if s is not None and win > s["last"] and win - s["last"] > a.evict:
            s = None
        if s is None:
            s = {"ewma": 0.0, "last": 0, "seen": 0, "press": False}; st[key] = s
        prior = 0.0
        if s["seen"] > 0:
            gap = win - s["last"] if win > s["last"] else 1
            prior = s["ewma"] * (1.0 - a.alpha) ** (gap - 1)
        ratio = pps / max(prior, a.floor)
        warm_ok = s["seen"] >= a.warm
        if (not s["press"]) and warm_ok and ratio >= a.k_in:
            s["press"] = True
        elif s["press"] and ratio < a.k_out:
            s["press"] = False
        if congela and s["seen"] < a.warm:
            new = prior
        else:
            alpha = ALPHA_SLOW if s["press"] else a.alpha
            new = (1.0 - alpha) * prior + alpha * pps
        s["ewma"] = new; s["last"] = win; s["seen"] += 1
        out.append((key, win, int(r["ts_ms"]), pps, ratio, s["press"]))
    return out

sel = [ri for ri, rows in enumerate(runs) if a.desde <= loc(int(rows[0]["ts_ms"]))[:10] <= a.hasta]
print("arranques_en_rango=%d" % len(sel))

print("\n# INVENTARIO: arranque, inicio y fin locales, ventanas, claves del lab (proto:pps_max)")
res_all = {}
for ri in sel:
    rows = runs[ri]
    res_all[ri] = {v: simulate(rows, v == "congela") for v in VARIANTES}
    mx = {}
    for (k, w, ts, pps, ratio, press) in res_all[ri]["actual"]:
        if k[0] == a.lab_victim:
            mx[k[1]] = max(mx.get(k[1], 0.0), pps)
    wins = sorted({int(r["win"]) for r in rows})
    print("%d\t%s\t%s\t%d\t%s" % (ri, loc(int(rows[0]["ts_ms"])), loc(int(rows[-1]["ts_ms"])), len(wins),
          " ".join("%s:%.0f" % (p, v) for p, v in sorted(mx.items()))))

print("\n# CLAVE DEL LAB (solo claves con alguna ventana activa)")
hdr = ["arr", "inicio", "proto", "vista_antes", "activas", "pps_med"]
for v in VARIANTES:
    hdr += [v + "_pres", v + "_pct", v + "_1a", v + "_resid", v + "_rmax"]
print("\t".join(hdr))
for ri in sel:
    protos = sorted({k[1] for (k, *_r) in res_all[ri]["actual"] if k[0] == a.lab_victim})
    for p in protos:
        key = (a.lab_victim, p)
        row, ok = None, True
        for v in VARIANTES:
            seq = [(w, pps, ratio, press) for (k, w, ts, pps, ratio, press) in res_all[ri][v] if k == key]
            act = [x for x in seq if x[1] >= a.umbral_activa]
            if not act:
                ok = False; break
            w0, wl = act[0][0], act[-1][0]
            if row is None:
                antes = sum(1 for x in seq if x[0] < w0)
                row = [str(ri), loc(int(runs[ri][0]["ts_ms"])), p, str(antes), str(len(act)),
                       "%.1f" % (sum(x[1] for x in act) / len(act))]
            npres = sum(1 for x in act if x[3])
            first = next((x[0] - w0 for x in act if x[3]), None)
            resid = sum(1 for x in seq if x[0] > wl and x[3])
            rmax = max(x[2] for x in act)
            row += [str(npres), "%.1f" % (100.0 * npres / len(act)), "-" if first is None else str(first), str(resid), "%.2f" % rmax]
        if ok:
            print("\t".join(row))

print("\n# COSTE en el resto de claves (ambiente, dst != lab_victim): episodios, ventanas en presión, claves distintas")
for v in VARIANTES:
    eps = wp = 0; claves = set()
    for ri in sel:
        prev = {}
        for (k, w, ts, pps, ratio, press) in res_all[ri][v]:
            if k[0] == a.lab_victim:
                continue
            if press:
                wp += 1; claves.add((ri, k))
                if not prev.get(k, False):
                    eps += 1
            prev[k] = press
    print("%s\tepisodios=%d\tventanas_en_presion=%d\tclaves=%d" % (v, eps, wp, len(claves)))
