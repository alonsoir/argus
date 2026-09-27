#!/usr/bin/env python3
"""DAY280 — retraso sniffer→ml-detector por ventana estampada.
Une cada línea [VICTIM-WINDOW] del log (seq) con la fila del CSV del lector (win) del
ÚLTIMO arranque (tras el último reinicio del contador win) para la misma víctima/proto.
  lag = hora de log del evento - hora de cierre de la ventana en el CSV (ts_ms)
Comprueba de paso que seq == win (d_pkts del log == d_pkts del CSV).
Uso: python3 scripts/d280_vw_lag.py LOG CSV [victim] [proto] > salida.txt
"""
import sys, re, csv, datetime as dt
from collections import defaultdict, OrderedDict

LOG, CSVF = sys.argv[1], sys.argv[2]
V = sys.argv[3] if len(sys.argv) > 3 else "192.168.100.1"
P = sys.argv[4] if len(sys.argv) > 4 else "17"

rows = list(csv.DictReader(open(CSVF)))
start, prev = 0, None
for i, r in enumerate(rows):
    w = int(r["win"])
    if prev is not None and w < prev:
        start = i
    prev = w
csvwin = {}
for r in rows[start:]:
    if r["dst_ip"] == V and r["proto"] == P:
        csvwin[int(r["win"])] = (int(r["ts_ms"]) / 1000.0, int(r["d_pkts"]))
first_ts = int(rows[start]["ts_ms"]) / 1000.0

rx_t = re.compile(r"(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2}:\d{2}(?:\.\d+)?)")
def kv(line, k):
    m = re.search(k + r"=([^,\s]+)", line)
    return m.group(1) if m else None
per = OrderedDict()
nolog_date = 0
for line in open(LOG, errors="replace"):
    if "[VICTIM-WINDOW]" not in line or "absent" in line:
        continue
    if kv(line, "victim") != V:
        continue
    m = rx_t.search(line)
    if not m:
        nolog_date += 1
        continue
    t = dt.datetime.fromisoformat(m.group(1) + " " + m.group(2)).timestamp()
    if t < first_ts - 5:
        continue
    s = int(kv(line, "seq")); dp = int(kv(line, "d_pkts"))
    e = per.setdefault(s, {"n": 0, "t0": t, "t1": t, "dp": dp})
    e["n"] += 1; e["t0"] = min(e["t0"], t); e["t1"] = max(e["t1"], t)

hm = lambda x: dt.datetime.fromtimestamp(x).strftime("%H:%M:%S")
print(f"victim={V} proto={P}  seq en log={len(per)}  win en CSV (último arranque)={len(csvwin)}  líneas sin fecha={nolog_date}")
print("seq  eventos  d_pkts_log  d_pkts_csv  cierre_csv  log_primero  log_ultimo  lag_primero_s  lag_ultimo_s")
mism = nocsv = 0
bymin = defaultdict(list)
for s, e in per.items():
    c = csvwin.get(s)
    if not c:
        nocsv += 1
        print(f"{s}  {e['n']}  {e['dp']}  -  -  {hm(e['t0'])}  {hm(e['t1'])}  -  -")
        continue
    ts, dpc = c
    flag = "" if dpc == e["dp"] else "  !!"
    mism += (dpc != e["dp"])
    l0, l1 = e["t0"] - ts, e["t1"] - ts
    bymin[hm(e["t0"])[:5]].append((l0, e["n"]))
    print(f"{s}  {e['n']}  {e['dp']}  {dpc}  {hm(ts)}  {hm(e['t0'])}  {hm(e['t1'])}  {l0:.1f}  {l1:.1f}{flag}")
print(f"\nRESUMEN: seq con d_pkts distinto al CSV={mism}  seq sin fila CSV={nocsv}")
print("minuto_log  eventos  lag_min_s  lag_max_s")
for mnt, v in bymin.items():
    print(f"{mnt}  {sum(n for _, n in v)}  {min(l for l, _ in v):.1f}  {max(l for l, _ in v):.1f}")
