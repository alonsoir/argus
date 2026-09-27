#!/usr/bin/env python3
"""
join_flood_escalation_v2.py  —  DAY272, limpia el denominador del recall.

v1 midio el patron escalation->class (solido) pero anclo flood solo en
plm=482, que resulto NO exclusivo del flood (el ambiente tambien lo produce;
el contador crecia con el log vivo). v2 anade Feature[13] Destination Port al
join para separar flood (puerto alto) de ambiente (DNS/NTP 53/123) POR DATO.

Bloque = de Feature[0] al veredicto DDoS del mismo thread; se resetea SOLO en
Feature[0], para que Feature[13] (puerto) y Feature[17] (plm) del mismo bloque
convivan. Interleaving de threads resuelto por thread-id.

Reporta, sobre plm=482:
  - Destination Port por clase   -> que es flood, que es ambiente.
  - recall FLOJO (plm=482)       = v1, contaminado.
  - recall DURO  (plm=482 & port alto) = limpio si el puerto separa.
  - escalation vs class con ancla dura.

CONGELA EL LOG ANTES:  cp logs/lab/detector.log /tmp/detector-day272.log
Uso:  python3 join_flood_escalation_v2.py /tmp/detector-day272.log
Solo lee.
"""

import re
import sys
import statistics as st
from collections import defaultdict

LOG = sys.argv[1] if len(sys.argv) > 1 else "/tmp/detector-day272.log"
FLOOD_PLM = 482.0
PORT_HI = 1024   # umbral flood vs servicios bajos; ajustalo segun la tabla

RE_TID   = re.compile(r"\[ml-detector\] \[\w+\] \[(\d+)\]")
RE_F0    = re.compile(r"Feature\[0\]")
RE_PLM   = re.compile(r"Feature\[17\] Packet Length Mean\s*:\s*([-0-9.]+)")
RE_PORT  = re.compile(r"Feature\[13\] Destination Port\s*:\s*([-0-9.]+)")
RE_DDOSF = re.compile(r"DDoS Features:")
RE_ESC   = re.compile(r"escalation=([-0-9.]+)")
RE_ENT   = re.compile(r"\bentropy=([-0-9.]+)")
RE_VERD  = re.compile(r"DDoS: class=([01]).*?ddos_prob=([-0-9.]+)")


def bucket(x, step=0.005):
    return round((x // step) * step, 3)


def parse(path):
    state = defaultdict(dict)
    records = []
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            m = RE_TID.search(line)
            if not m:
                continue
            tid = m.group(1)
            s = state[tid]

            if RE_F0.search(line):
                s.clear()                       # nuevo bloque de features level1
            mport = RE_PORT.search(line)
            if mport:
                s["port"] = float(mport.group(1)); continue
            mp = RE_PLM.search(line)
            if mp:
                s["plm"] = float(mp.group(1)); continue
            if RE_DDOSF.search(line):
                me = RE_ESC.search(line);  s["esc"] = float(me.group(1)) if me else None
                mn = RE_ENT.search(line);  s["ent"] = float(mn.group(1)) if mn else None
                continue
            mv = RE_VERD.search(line)
            if mv:
                s["class"] = int(mv.group(1))
                s["ddos_prob"] = float(mv.group(2))
                records.append(dict(s))
                state[tid] = {}
    return records


def recall(rs, tag):
    if not rs:
        print(f"recall {tag:<22}: 0/0"); return
    pos = sum(1 for r in rs if r["class"] == 1)
    print(f"recall {tag:<22}: {pos}/{len(rs)} = {pos/len(rs):.3f}")


def esc_table(rs, titulo):
    by = defaultdict(lambda: [0, 0])
    for r in rs:
        if r.get("esc") is not None:
            by[bucket(r["esc"])][r["class"]] += 1
    print(f"{titulo}  (cubos 0.005)")
    print(f"  {'valor':>8} | {'NORMAL':>6} | {'DDOS':>5} | {'%DDOS':>6}")
    for k in sorted(by):
        n0, n1 = by[k]; tot = n0 + n1
        print(f"  {k:>8.3f} | {n0:>6} | {n1:>5} | {100*n1/tot:>5.1f}%")
    e1 = [r["esc"] for r in rs if r["class"] == 1 and r.get("esc") is not None]
    e0 = [r["esc"] for r in rs if r["class"] == 0 and r.get("esc") is not None]
    if e0 and e1:
        print(f"  media  NORMAL={st.mean(e0):.4f}  DDOS={st.mean(e1):.4f}")
    print()


def main():
    try:
        records = parse(LOG)
    except FileNotFoundError:
        print(f"[ABORT] no encuentro {LOG} - congelaste el log?", file=sys.stderr)
        sys.exit(2)

    flood = [r for r in records if r.get("plm") == FLOOD_PLM
             and "class" in r and r.get("esc") is not None]

    print(f"log            : {LOG}")
    print(f"registros DDoS : {len(records)}")
    print(f"flood plm=482  : {len(flood)}\n")
    if not flood:
        print("[!] 0 flood - revisar firma o join."); sys.exit(0)

    byport = defaultdict(lambda: [0, 0])
    sinport = [0, 0]
    for r in flood:
        if "port" in r:
            byport[int(r["port"])][r["class"]] += 1
        else:
            sinport[r["class"]] += 1
    print("Destination Port entre plm=482 (top 15 por total):")
    print(f"  {'port':>7} | {'NORMAL':>6} | {'DDOS':>5}")
    for port, (n0, n1) in sorted(byport.items(), key=lambda kv: -(kv[1][0] + kv[1][1]))[:15]:
        print(f"  {port:>7} | {n0:>6} | {n1:>5}")
    if sinport != [0, 0]:
        print(f"  {'s/port':>7} | {sinport[0]:>6} | {sinport[1]:>5}")
    print()

    hard = [r for r in flood if r.get("port", 0) >= PORT_HI]
    recall(flood, "FLOJO (plm=482)")
    recall(hard,  f"DURO (+port>={PORT_HI})")
    print()

    if hard:
        esc_table(hard, "escalation vs class  (ancla DURA)")


if __name__ == "__main__":
    main()