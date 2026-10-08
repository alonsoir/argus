#!/usr/bin/env python3
"""DAY291 — EWMA por víctima con HISTÉRESIS, offline sobre ddos_windows.csv.
Misma fórmula que victim_ewma_step (sniffer/include/ddos_contract_v2.hpp) + estado bajo_presion:
  entra con ratio >= K_in (y clave caliente si se exige), sale con ratio < K_out;
  dentro del estado, alfa lento = 1/tau. Cada arranque del sniffer (win que retrocede) empieza de cero.
Variante 'actual': sin histéresis, hot = caliente && ratio >= K_actual (código de hoy).
Detalle: episodios del ambiente por /16 y episodios largos del lab con su perfil de pps."""
import argparse, csv
from datetime import datetime, timezone

ap = argparse.ArgumentParser()
ap.add_argument("--csv", default="/vagrant/logs/lab/ddos_windows.csv")
ap.add_argument("--k-in", default="3,4,5")
ap.add_argument("--caliente", default="si,no", help="si, no o si,no")
ap.add_argument("--k-out", type=float, default=1.5)
ap.add_argument("--tau-s", type=float, default=3600.0)
ap.add_argument("--alpha", type=float, default=0.1)
ap.add_argument("--k-actual", type=float, default=5.0)
ap.add_argument("--floor", type=float, default=10.0)
ap.add_argument("--warm", type=int, default=30)
ap.add_argument("--evict", type=int, default=3600)
ap.add_argument("--lab-victim", default="192.168.100.1")
ap.add_argument("--ultimos-lab", type=int, default=6)
ap.add_argument("--largo", type=int, default=300, help="ventanas para listar un episodio lab como largo")
ap.add_argument("--top16", type=int, default=8)
a = ap.parse_args()
ALPHA_SLOW = 1.0 / a.tau_s
print("params:", vars(a), "alpha_lento=%.6g" % ALPHA_SLOW)

runs, cur, last_win = [], [], None
with open(a.csv, newline="") as f:
    for x in csv.DictReader(f):
        w = int(x["win"])
        if last_win is not None and w < last_win:
            runs.append(cur); cur = []
        last_win = w
        if int(x["window_ms"]) > 0:
            cur.append(x)
runs.append(cur)
print("arranques=%d ventanas_validas=%d" % (len(runs), sum(len(r) for r in runs)))

def utc(ms):
    return datetime.fromtimestamp(int(ms) / 1000, tz=timezone.utc).strftime("%m-%d %H:%M:%S")

def simulate(k_in, need_warm, hyst):
    eps = []
    for ri, rows in enumerate(runs):
        st = {}
        for r in rows:
            win = int(r["win"]); key = (r["dst_ip"], r["proto"])
            pps = int(r["d_pkts"]) * 1000.0 / int(r["window_ms"])
            s = st.get(key)
            if s is not None and win > s["last"] and win - s["last"] > a.evict:
                if s["press"]: eps.append(s["ep"])
                s = None
            if s is None:
                s = {"ewma": 0.0, "last": 0, "seen": 0, "press": False, "ep": None}; st[key] = s
            prior = 0.0
            if s["seen"] > 0:
                gap = win - s["last"] if win > s["last"] else 1
                prior = s["ewma"] * (1.0 - a.alpha) ** (gap - 1)
            ratio = pps / max(prior, a.floor)
            warm_ok = (s["seen"] >= a.warm) or not need_warm
            if hyst:
                enter = (not s["press"]) and warm_ok and ratio >= k_in
                leave = s["press"] and ratio < a.k_out
            else:
                hot = (s["seen"] >= a.warm) and ratio >= a.k_actual
                enter = hot and not s["press"]
                leave = (not hot) and s["press"]
            if enter:
                s["press"] = True
                s["ep"] = {"key": key, "run": ri, "ts0": r["ts_ms"], "win0": win, "winl": win, "tsl": r["ts_ms"],
                           "rmax": ratio, "cierre": "fin_arranque", "pps_cierre": -1.0, "pps0": pps, "psum": 0.0, "n": 0, "ppsl": pps}
            elif leave:
                s["ep"]["cierre"] = "histeresis"; s["ep"]["pps_cierre"] = pps; eps.append(s["ep"]); s["press"] = False; s["ep"] = None
            if hyst:
                alpha = ALPHA_SLOW if s["press"] else a.alpha
            else:
                alpha = (a.alpha / 60.0) if hot else a.alpha
            if s["press"]:
                e = s["ep"]; e["winl"] = win; e["tsl"] = r["ts_ms"]; e["rmax"] = max(e["rmax"], ratio)
                e["psum"] += pps; e["n"] += 1; e["ppsl"] = pps
            s["ewma"] = (1.0 - alpha) * prior + alpha * pps
            s["last"] = win; s["seen"] += 1
        for s in st.values():
            if s["press"]: eps.append(s["ep"])
    for e in eps:
        e["nwin"] = e["winl"] - e["win0"] + 1
    return eps

def report(name, eps):
    amb = [e for e in eps if e["key"][0] != a.lab_victim]
    lab = [e for e in eps if e["key"][0] == a.lab_victim]
    print("\n=== %s" % name)
    for tag, L in (("AMBIENTE", amb), ("LAB", lab)):
        d = sorted(e["nwin"] for e in L)
        if d:
            print("%s episodios=%d ventanas_total=%d mediana=%d p90=%d max=%d" % (
                tag, len(d), sum(d), d[len(d) // 2], d[int(len(d) * 0.9)], d[-1]))
        else:
            print("%s episodios=0" % tag)
    p16 = {}
    for e in amb:
        p = ".".join(e["key"][0].split(".")[:2])
        c = p16.setdefault(p, [0, 0]); c[0] += 1; c[1] += e["nwin"]
    for p, (n, w) in sorted(p16.items(), key=lambda kv: -kv[1][0])[:a.top16]:
        print("  ambiente /16 %-9s episodios=%d ventanas=%d" % (p, n, w))
    for e in sorted(lab, key=lambda e: int(e["ts0"])):
        if e["nwin"] >= a.largo:
            print("  LARGO run=%d %s/%s %s -> %s UTC ventanas=%d rmax=%.2f pps_entrada=%.1f pps_medio=%.1f pps_salida=%.1f cierre=%s pps_cierre=%.1f" % (
                e["run"], e["key"][0], e["key"][1], utc(e["ts0"]), utc(e["tsl"]), e["nwin"], e["rmax"],
                e["pps0"], e["psum"] / max(e["n"], 1), e["ppsl"], e["cierre"], e["pps_cierre"]))
    for e in sorted(lab, key=lambda e: int(e["ts0"]))[-a.ultimos_lab:]:
        print("  lab %s/%s inicio=%s UTC ventanas=%d ratio_max=%.2f" % (
            e["key"][0], e["key"][1], utc(e["ts0"]), e["nwin"], e["rmax"]))

report("actual (sin histeresis, K=%g, caliente obligatoria)" % a.k_actual, simulate(a.k_actual, True, False))
for k in [float(x) for x in a.k_in.split(",")]:
    for cw in a.caliente.split(","):
        need_warm = (cw == "si")
        report("histeresis K_in=%g K_out=%g tau=%gs caliente=%s" % (k, a.k_out, a.tau_s, cw),
               simulate(k, need_warm, True))
