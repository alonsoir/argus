#!/usr/bin/env python3
# DAY323 — resumen de un eve.json de Suricata (medida, no toca nada).
# Uso: python3 -I scripts/etcd_ha/d323_eve_resumen.py <eve.json>
# Saca: total de líneas, líneas no JSON, recuento por event_type, primera y
# última marca de tiempo, alertas por firma y los 10 pares (src, dest, proto)
# más frecuentes fuera de stats. Una pasada: lineal en el número de líneas.
import collections
import json
import sys

if len(sys.argv) != 2:
    print("uso: d323_eve_resumen.py <eve.json>", file=sys.stderr)
    sys.exit(2)

tipos = collections.Counter()
firmas = collections.Counter()
pares = collections.Counter()
total = malas = 0
primera = ultima = None

with open(sys.argv[1], encoding="utf-8", errors="replace") as f:
    for linea in f:
        total += 1
        try:
            j = json.loads(linea)
        except ValueError:
            malas += 1
            continue
        et = j.get("event_type", "<sin event_type>")
        tipos[et] += 1
        ts = j.get("timestamp")
        if ts:
            if primera is None:
                primera = ts
            ultima = ts
        if et == "alert":
            firmas[j.get("alert", {}).get("signature", "<sin firma>")] += 1
        if et != "stats":
            pares[(j.get("src_ip", "-"), j.get("dest_ip", "-"), j.get("proto", "-"))] += 1

print(f"[EVE] lineas={total} no_json={malas}")
print(f"[EVE] primera={primera} ultima={ultima}")
print("[EVE] por event_type:")
for et, n in tipos.most_common():
    print(f"  {n:8d}  {et}")
print(f"[EVE] alertas por firma ({sum(firmas.values())}):")
for s, n in firmas.most_common(20):
    print(f"  {n:8d}  {s}")
print("[EVE] 10 pares src -> dest (proto) mas frecuentes, sin stats:")
for (s, d, p), n in pares.most_common(10):
    print(f"  {n:8d}  {s} -> {d} ({p})")
