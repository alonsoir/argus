#!/usr/bin/env python3
"""
profile_flood_pcap.py  —  DAY272, la vara de medir sin perdida.

Lee el pcap del flood ENTERO (sin ring, sin detector) y reconstruye la verdad:
que recibe cada victima (dst_ip+proto), a que tasa, y con que perfil temporal.
Es la ground truth contra la que se mediran el contador en-kernel y las
formulas candidatas de escalation.

Dos ejes de tiempo:
  - REPLAY: a --pps constante, el paquete i sale en i/pps segundos. Es el eje
    que ve el sniffer. Si la tasa por victima es plana aqui y el detector vio
    decaimiento en la cola -> la cola era PERDIDA DE RING, no la feature.
  - PCAP: los timestamps internos del fichero (timing original CICDDoS2019).
    Informativo; tcprewrite no los toca, tcpreplay --pps los ignora al enviar.

Reporta: nº paquetes, victimas distintas (dst_ip+proto), top victimas,
histograma de tamanos (confirma 482), y la tasa por segundo REPLAY de la
victima dominante (¿plana o decae?).

Uso:  python3 profile_flood_pcap.py datasets/cicddos2019/_0125_50k_lab.pcap [--pps 100]
Solo lee.
"""

import sys
import socket
import argparse
from collections import defaultdict, Counter

def load_backend():
    try:
        import dpkt
        return "dpkt", dpkt
    except ImportError:
        pass
    try:
        import scapy.all as scapy
        return "scapy", scapy
    except ImportError:
        return None, None


def iter_packets_dpkt(path, dpkt):
    """Devuelve (ts, dst_ip_u32, proto, wire_len) por paquete."""
    with open(path, "rb") as fh:
        for ts, buf in dpkt.pcap.Reader(fh):
            try:
                eth = dpkt.ethernet.Ethernet(buf)
            except Exception:
                continue
            ip = getattr(eth, "data", None)
            if not isinstance(ip, dpkt.ip.IP):
                continue
            dst = int.from_bytes(ip.dst, "big")
            yield ts, dst, ip.p, len(buf)


def iter_packets_scapy(path, scapy):
    rd = scapy.PcapReader(path)
    for pkt in rd:
        if not pkt.haslayer(scapy.IP):
            continue
        ip = pkt[scapy.IP]
        dst = int.from_bytes(socket.inet_aton(ip.dst), "big")
        yield float(pkt.time), dst, int(ip.proto), len(pkt)
    rd.close()


def ip_str(u32):
    return socket.inet_ntoa(u32.to_bytes(4, "big"))


PROTO = {1: "ICMP", 6: "TCP", 17: "UDP"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pcap")
    ap.add_argument("--pps", type=int, default=100, help="tasa de replay (para el eje REPLAY)")
    args = ap.parse_args()

    backend, mod = load_backend()
    if backend is None:
        print("[ABORT] ni dpkt ni scapy. Instala:  pip install dpkt", file=sys.stderr)
        sys.exit(2)
    it = iter_packets_dpkt if backend == "dpkt" else iter_packets_scapy

    n = 0
    ts_first = ts_last = None
    by_victim = defaultdict(lambda: [0, 0])         # (dst,proto) -> [pkts, bytes]
    sizes = Counter()
    # tasa REPLAY por segundo de CADA victima: sec -> victima -> pkts
    rate = defaultdict(lambda: defaultdict(int))

    for ts, dst, proto, wlen in it(args.pcap, mod):
        key = (dst, proto)
        by_victim[key][0] += 1
        by_victim[key][1] += wlen
        sizes[wlen] += 1
        sec = n // args.pps                          # eje REPLAY: paquete n -> segundo n/pps
        rate[sec][key] += 1
        if ts_first is None:
            ts_first = ts
        ts_last = ts
        n += 1

    if n == 0:
        print("[!] 0 paquetes IP leidos."); sys.exit(0)

    print(f"backend        : {backend}")
    print(f"paquetes IP    : {n}")
    print(f"pcap span      : {ts_last - ts_first:.1f}s (timestamps internos, informativo)")
    print(f"replay span    : {n/args.pps:.1f}s (a {args.pps}pps)")
    print(f"victimas dist. : {len(by_victim)} (dst_ip+proto)\n")

    print("Top victimas (dst_ip proto | pkts | MB):")
    top = sorted(by_victim.items(), key=lambda kv: -kv[1][0])
    for (dst, proto), (pk, by) in top[:8]:
        print(f"  {ip_str(dst):>15} {PROTO.get(proto, proto):>4} | {pk:>7} | {by/1e6:>6.2f}")
    print()

    print("Tamanos de paquete (top 6 wire len):")
    for sz, c in sizes.most_common(6):
        print(f"  {sz:>6} B | {c:>7}")
    print()

    # perfil temporal REPLAY de la victima dominante
    vic = top[0][0]
    print(f"Tasa REPLAY de la victima dominante {ip_str(vic[0])}/{PROTO.get(vic[1], vic[1])}")
    print("(pkts por segundo de replay; ¿plana o decae?)")
    secs = sorted(rate.keys())
    # resumen por deciles para no volcar 500 lineas
    nb = 10
    span = max(secs[-1] - secs[0] + 1, 1)
    width = max(span // nb, 1)
    print(f"  {'t_ini[s]':>8} | {'pkts_victima':>12} | {'pkts_total':>10}")
    for b in range(nb):
        s0 = secs[0] + b * width
        s1 = s0 + width
        pv = sum(rate[s].get(vic, 0) for s in secs if s0 <= s < s1)
        pt = sum(sum(rate[s].values()) for s in secs if s0 <= s < s1)
        if pt:
            print(f"  {s0:>8} | {pv:>12} | {pt:>10}")


if __name__ == "__main__":
    main()