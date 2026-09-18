#!/usr/bin/env python3
"""
join_flood_escalation_v3.py  —  DAY272, clava la interpretacion temporal.

v2 dio: escalation separa perfecto dentro del flood (recall 77%), y el puerto
resulto proxy del tiempo (todo puerto alto, cada puerto 100% de una clase).
Hipotesis: los NORMAL (escalation=0) son el ONSET del flood, antes de que la
ventana caliente -> latencia de deteccion, no fallo de cobertura.

v3 captura el timestamp del veredicto y parte el flood en tramos temporales.
Si %DDOS sube de 0 a 100 conforme avanza el flood -> warmup CONFIRMADO.
Ancla flood = plm=482 (v2 mostro que ya es limpio; el puerto no aportaba).

Uso:  python3 join_flood_escalation_v3.py /tmp/detector-day272.log
Solo lee.
"""

import re
import sys
import statistics as st
from datetime import datetime
from collections import defaultdict

LOG = sys.argv[1] if len(sys.argv) > 1 else "/tmp/detector-day272.log"
FLOOD_PLM = 482.0
NBINS = 10

RE_TS    = re.compile(r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+)\]")
RE_TID   = re.compile(r"\[ml-detector\] \[\w+\] \[(\d+)\]")
RE_F0    = re.compile(r"Feature\[0\]")
RE_PLM   = re.compile(r"Feature\[17\] Packet Length Mean\s*:\s*([-0-9.]+)")
RE_DDOSF = re.compile(r"DDoS Features:")
RE_ESC   = re.compile(r"escalation=([-0-9.]+)")
RE_VERD  = re.compile(r"DDoS: class=([01]).*?ddos_prob=([-0-9.]+)")


def parse(path):
    state = defaultdict(dict)
    records = []
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            m = RE_TID.search(line)
            if not m:
                continue
            s = state[m.group(1)]
            if RE_F0.search(line):
                s.clear()
            mp = RE_PLM.search(line)
            if mp:
                s["plm"] = float(mp.group(1)); continue
            if RE_DDOSF.search(line):
                me = RE_ESC.search(line); s["esc"] = float(me.group(1)) if me else None
                continue
            mv = RE_VERD.search(line)
            if mv:
                s["class"] = int(mv.group(1))
                mts = RE_TS.search(line)
                if mts:
                    s["t"] = datetime.strptime(mts.group(1), "%Y-%m-%d %H:%M:%S.%f").timestamp()
                records.append(dict(s))
                state[m.group(1)] = {}
    return records


def main():
    try:
        records = parse(LOG)
    except FileNotFoundError:
        print(f"[ABORT] no encuentro {LOG}", file=sys.stderr); sys.exit(2)

    flood = [r for r in records if r.get("plm") == FLOOD_PLM
             and "class" in r and r.get("esc") is not None and "t" in r]
    if not flood:
        print("[!] 0 flood con timestamp."); sys.exit(0)

    flood.sort(key=lambda r: r["t"])
    t0 = flood[0]["t"]; t1 = flood[-1]["t"]
    span = max(t1 - t0, 1e-9)
    print(f"log           : {LOG}")
    print(f"flood plm=482 : {len(flood)}   span = {span:.1f}s\n")

    # comprobacion directa: tiempos de NORMAL vs DDOS
    tn = [r["t"] - t0 for r in flood if r["class"] == 0]
    td = [r["t"] - t0 for r in flood if r["class"] == 1]
    if tn:
        print(f"NORMAL (esc=0): n={len(tn):>3}  t[s] min={min(tn):.1f} med={st.median(tn):.1f} max={max(tn):.1f}")
    if td:
        print(f"DDOS  (esc>0) : n={len(td):>3}  t[s] min={min(td):.1f} med={st.median(td):.1f} max={max(td):.1f}")
    print()

    # %DDOS y escalation media por tramo temporal
    print(f"tramo temporal ({NBINS} bins)")
    print(f"  {'t_ini[s]':>9} | {'n':>4} | {'%DDOS':>6} | {'esc_med':>8}")
    width = span / NBINS
    bins = defaultdict(list)
    for r in flood:
        b = min(int((r["t"] - t0) / width), NBINS - 1)
        bins[b].append(r)
    for b in range(NBINS):
        rs = bins.get(b, [])
        if not rs:
            print(f"  {b*width:>9.1f} | {0:>4} | {'-':>6} | {'-':>8}")
            continue
        pos = sum(1 for r in rs if r["class"] == 1)
        em = st.mean(r["esc"] for r in rs)
        print(f"  {b*width:>9.1f} | {len(rs):>4} | {100*pos/len(rs):>5.1f}% | {em:>8.4f}")


if __name__ == "__main__":
    main()