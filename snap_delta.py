#!/usr/bin/env python3
"""snap_delta.py -- delta entre dos fotos de snap_ddos.sh (ANTES / DESPUES). Solo stdlib.

Uso:
    python3 snap_delta.py ANTES.txt DESPUES.txt
    python3 snap_delta.py ANTES.txt DESPUES.txt --sent 50000 23999270 --key 192.168.100.1/17 --key 192.168.100.1/1

Entrada: la salida de `sudo bash /vagrant/snap_ddos.sh > fichero` (fecha, `ip -s link` de eth1/eth2,
y dos lineas JSON de `bpftool -j map dump`: stats y ddos_victims).

Salida:
  * ventana en segundos y delta de RX por interfaz (paquetes, bytes, dropped, missed)
  * kernel: delta de stats[0] (eventos al ring), suma de deltas de todo el mapa, A-B
  * cable - mapa: lo que entro por las interfaces y el mapa NO conto (no IPv4, drops de la NIC...)
  * delta de las claves pedidas (--key IP/PROTO; por defecto 192.168.100.1/17 y /1)
  * con --sent PKTS BYTES: enviado - contado en esas claves
  * top de victimas por delta de paquetes
"""
import argparse
import json
import re
import sys


def ip_str(v):
    return "%d.%d.%d.%d" % ((v >> 24) & 255, (v >> 16) & 255, (v >> 8) & 255, v & 255)


def ip_num(s):
    a, b, c, d = (int(x) for x in s.split("."))
    return (a << 24) | (b << 16) | (c << 8) | d


def le(hex_list):
    return int.from_bytes(bytes(int(x, 16) for x in hex_list), "little")


def add_entry(snap, e):
    f = e.get("formatted")
    if f is not None:
        k, v = f["key"], f["value"]
        if isinstance(k, dict):
            snap["victims"][(int(k["dst_ip"]), int(k["proto"]))] = (int(v["pkts"]), int(v["bytes"]))
        else:
            snap["stats"][int(k)] = int(v)
        return
    k, v = e["key"], e["value"]  # sin BTF: bytes little-endian
    if len(k) == 8 and len(v) == 16:
        snap["victims"][(le(k[:4]), le(k[4:]))] = (le(v[:8]), le(v[8:]))
    elif len(k) == 4 and len(v) == 8:
        snap["stats"][le(k)] = le(v)


def parse(path):
    with open(path, encoding="utf-8", errors="replace") as fh:
        lines = fh.read().splitlines()
    snap = {"t": None, "if": {}, "stats": {}, "victims": {}}
    for ln in lines:
        if re.fullmatch(r"\s*\d+(\.\d+)?\s*", ln):
            snap["t"] = float(ln)
            break
    cur = None
    for i, ln in enumerate(lines):
        m = re.match(r"^\d+:\s+([^:\s]+):", ln)
        if m:
            cur = m.group(1)
            continue
        if cur and ln.strip().startswith("RX:") and i + 1 < len(lines):
            nums = lines[i + 1].split()
            if len(nums) >= 5 and all(n.isdigit() for n in nums[:5]):
                snap["if"][cur] = {"bytes": int(nums[0]), "pkts": int(nums[1]),
                                   "dropped": int(nums[3]), "missed": int(nums[4])}
    for ln in lines:
        s = ln.strip()
        if not s.startswith("["):
            continue
        try:
            arr = json.loads(s)
        except ValueError:
            continue
        for e in arr:
            if isinstance(e, dict) and "key" in e:
                add_entry(snap, e)
    return snap


def main():
    ap = argparse.ArgumentParser(description="Delta entre dos fotos de snap_ddos.sh")
    ap.add_argument("antes")
    ap.add_argument("despues")
    ap.add_argument("--key", action="append", metavar="IP/PROTO",
                    help="clave a desglosar (repetible); por defecto 192.168.100.1/17 y /1")
    ap.add_argument("--sent", nargs=2, type=int, metavar=("PKTS", "BYTES"),
                    help="paquetes y bytes enviados por tcpreplay (linea Actual:)")
    ap.add_argument("--top", type=int, default=6, help="cuantas victimas listar (por defecto 6)")
    args = ap.parse_args()

    a, b = parse(args.antes), parse(args.despues)
    for name, s in (("ANTES", a), ("DESPUES", b)):
        if not s["victims"] and not s["stats"]:
            print("ERROR: la foto %s no trae los mapas (sniffer parado? bpftool sin sudo?)" % name)
            return 2

    print("ventana                     : %.3f s" % ((b["t"] or 0) - (a["t"] or 0)))
    print("interfaces (RX, delta):")
    wire_pkts = wire_bytes = 0
    for name in sorted(set(a["if"]) & set(b["if"])):
        d = {k: b["if"][name][k] - a["if"][name][k] for k in ("pkts", "bytes", "dropped", "missed")}
        wire_pkts += d["pkts"]
        wire_bytes += d["bytes"]
        print("  %-5s pkts %+d  bytes %+d  dropped %+d  missed %+d"
              % (name, d["pkts"], d["bytes"], d["dropped"], d["missed"]))
    print("  total pkts %+d  bytes %+d" % (wire_pkts, wire_bytes))

    stats0 = b["stats"].get(0, 0) - a["stats"].get(0, 0)
    # [RING-LOSS-D275:STATS] contadores nuevos del kernel (claves 1 y 2)
    stats1 = b["stats"].get(1, 0) - a["stats"].get(1, 0)
    stats2 = b["stats"].get(2, 0) - a["stats"].get(2, 0)
    has_ring_counters = (1 in b["stats"]) and (2 in b["stats"]) and (1 in a["stats"]) and (2 in a["stats"])
    deltas = {}
    resets = 0
    for k, (bp, bb) in b["victims"].items():
        ap_, ab = a["victims"].get(k, (0, 0))
        if bp < ap_ or bb < ab:  # evict LRU + reinsercion: el contador arranco de cero
            resets += 1
            deltas[k] = (bp, bb)
        else:
            deltas[k] = (bp - ap_, bb - ab)
    evicted = sum(1 for k in a["victims"] if k not in b["victims"])
    sum_p = sum(p for p, _ in deltas.values())
    sum_b = sum(x for _, x in deltas.values())

    print("kernel:")
    print("  stats[0] (eventos al ring)     : %+d" % stats0)
    print("  mapa ddos_victims, suma deltas : %+d pkts  %+d B  (%d claves con delta)"
          % (sum_p, sum_b, sum(1 for p, x in deltas.values() if p or x)))
    print("  A - B (ring - mapa)            : %+d   (0 = sin perdida entre contador y ring)" % (stats0 - sum_p))
    # [RING-LOSS-D275:PRINT] descomposicion exacta de A - B
    if has_ring_counters:
        print("  stats[1] reserve fallido (ring): %+d   (ring lleno)" % stats1)
        print("  stats[2] descartes filtro/L4   : %+d   (puertos excluidos, cabecera L4 truncada)" % stats2)
        print("  B - (A + s1 + s2)              : %+d   (0 = identidad exacta del kernel)"
              % (sum_p - (stats0 + stats1 + stats2)))
        if sum_p:
            print("  llegado al ring (A / B)        : %.1f %%" % (100.0 * stats0 / sum_p))
    else:
        print("  AVISO: faltan stats[1]/stats[2] en algun snapshot (sniffer sin contadores de perdida)")
    print("  cable - mapa (no contado)      : %+d pkts  %+d B   (no IPv4, drops de la NIC...)"
          % (wire_pkts - sum_p, wire_bytes - sum_b))
    if resets or evicted:
        print("  AVISO: %d contadores reiniciados por LRU, %d claves desalojadas" % (resets, evicted))

    keys = args.key or ["192.168.100.1/17", "192.168.100.1/1"]
    print("claves pedidas:")
    tot_p = tot_b = 0
    for spec in keys:
        ip, proto = spec.split("/")
        p, x = deltas.get((ip_num(ip), int(proto)), (0, 0))
        tot_p += p
        tot_b += x
        print("  %-22s : %+d pkts  %+d B" % (spec, p, x))
    if args.sent:
        print("enviado - contado (claves)   : %+d pkts  %+d B   (enviado %d pkts, %d B)"
              % (args.sent[0] - tot_p, args.sent[1] - tot_b, args.sent[0], args.sent[1]))

    print("top victimas por delta de paquetes:")
    top = sorted(deltas.items(), key=lambda kv: (-kv[1][0], kv[0]))[:args.top]
    for (ip, proto), (p, x) in top:
        print("  %-16s proto %-3d : %+d pkts  %+d B" % (ip_str(ip), proto, p, x))
    return 0


if __name__ == "__main__":
    sys.exit(main())