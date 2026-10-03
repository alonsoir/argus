#!/usr/bin/env python3
"""DAY286: window_ms del tablero ([VICTIM-WINDOW] seq) frente al del CSV (win), por ventana.
Uso: d286_wms_compare.py ddos_windows.csv ml-detector.log"""
import csv, re, sys
from collections import Counter

KV = re.compile(r"(\w+)=([^,\s]+)")
csv_wms, last, start, rows = {}, None, 0, []
with open(sys.argv[1], newline="") as f:
    for x in csv.DictReader(f):
        w = int(x["win"])
        if last is not None and w < last:
            start = len(rows)
        last = w
        rows.append(x)
for r in rows[start:]:
    csv_wms[int(r["win"])] = int(r["window_ms"])
board = {}
with open(sys.argv[2], errors="replace") as f:
    for line in f:
        if "[VICTIM-WINDOW]" in line and "window_ms=" in line:
            d = dict(KV.findall(line.split("[VICTIM-WINDOW]", 1)[1]))
            board[int(d["seq"])] = int(d["window_ms"])
both = sorted(set(board) & set(csv_wms))
diffs = Counter(board[s] - csv_wms[s] for s in both)
print(f"ventanas en ambos={len(both)}")
print("tablero - csv : n ventanas")
for k in sorted(diffs):
    print(f"  {k:+d} ms : {diffs[k]}")
ej = [s for s in both if board[s] != csv_wms[s]][:5]
print("ejemplos (seq tablero csv): " + ", ".join(f"{s} {board[s]} {csv_wms[s]}" for s in ej))
