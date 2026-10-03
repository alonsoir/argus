#!/usr/bin/env python3
"""DAY286: resumen de [DDOS-V2] por grupo (sin fast alerts).
Uso: d286_ddos_v2_summary.py LOG > salida.txt"""
import re, sys
from collections import defaultdict

KV = re.compile(r"(\w+)=([^,\s]+)")
FIELDS = ["syn_ack", "mean_size", "refl", "entropy", "pkts", "completion", "vratio", "vpps"]

def group(src, sport, dst, dport):
    if src == "192.168.100.50" and sport == "53" and dport == "40000":
        return "refl_test"
    if dport == "9999" or sport == "9999":
        return "upload"
    if src == "192.168.100.50" and dst == "192.168.100.1":
        return "flood"
    return "ambiente"

data = defaultdict(lambda: defaultdict(list))
n_fast = 0
with open(sys.argv[1], errors="replace") as f:
    for line in f:
        if "[DDOS-V2]" not in line:
            continue
        d = dict(KV.findall(line.split("[DDOS-V2]", 1)[1]))
        if d.get("event", "").startswith("fast-alert-"):
            n_fast += 1
            continue
        sip, sp = d["src"].rsplit(":", 1)
        dip, dp = d["dst"].rsplit(":", 1)
        g = group(sip, sp, dip, dp)
        for k in FIELDS:
            data[g][k].append(float(d[k]))

def pct(v, p):
    v = sorted(v)
    return v[min(len(v) - 1, int(p / 100.0 * len(v)))]

print(f"fast_alerts_excluidas={n_fast}")
for g in ["refl_test", "flood", "upload", "ambiente"]:
    if g not in data:
        print(f"\n== {g}: 0 eventos")
        continue
    n = len(data[g]["refl"])
    print(f"\n== {g}: {n} eventos")
    for k in FIELDS:
        v = data[g][k]
        sent = sum(1 for x in v if x <= -9998)
        print(f"  {k:10s} min={min(v):10.3f} p50={pct(v,50):10.3f} p90={pct(v,90):10.3f} max={max(v):10.3f} centinela={sent}")
