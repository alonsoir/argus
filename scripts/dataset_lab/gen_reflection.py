#!/usr/bin/env python3
# DAY288 — genera un pcap de reflexion UDP (NTP/DNS): N datagramas desde el puerto de servicio
# SPORT de 192.168.100.50 a puertos destino altos aleatorios (seed 42) de 192.168.100.1,
# MACs de la topologia del lab. Mismo esqueleto que gen_syn_flood.py. Solo stdlib.
# Uso: gen_reflection.py N SPORT PAYLOAD_LEN OUT
import struct, socket, sys, random

N        = int(sys.argv[1])
SPORT    = int(sys.argv[2])
PAYLOAD  = int(sys.argv[3])
OUT      = sys.argv[4]
SMAC     = bytes.fromhex("080027078c2f")  # 08:00:27:07:8c:2f  client eth1
DMAC     = bytes.fromhex("0800276f63da")  # 08:00:27:6f:63:da  defender eth2
SRC_IP   = socket.inet_aton("192.168.100.50")
DST_IP   = socket.inet_aton("192.168.100.1")
random.seed(42)  # reproducible

if 14 + 20 + 8 + PAYLOAD > 1514:
    sys.exit("PAYLOAD_LEN fragmentaria la trama (MTU 1500); no es lo que se quiere aqui")

def cksum(data):
    if len(data) % 2:
        data += b"\x00"
    s = sum(struct.unpack("!%dH" % (len(data) // 2), data))
    s = (s >> 16) + (s & 0xFFFF)
    s += s >> 16
    return (~s) & 0xFFFF

def ip_hdr(src, dst, payload_len, proto, ident):
    ver_ihl = (4 << 4) | 5
    total   = 20 + payload_len
    h = struct.pack("!BBHHHBBH4s4s", ver_ihl, 0, total, ident, 0, 64, proto, 0, src, dst)
    c = cksum(h)
    return struct.pack("!BBHHHBBH4s4s", ver_ihl, 0, total, ident, 0, 64, proto, c, src, dst)

def udp(sport, dport, data):
    ulen   = 8 + len(data)
    pseudo = struct.pack("!4s4sBBH", SRC_IP, DST_IP, 0, socket.IPPROTO_UDP, ulen)
    c = cksum(pseudo + struct.pack("!HHHH", sport, dport, ulen, 0) + data)
    if c == 0:
        c = 0xFFFF
    return struct.pack("!HHHH", sport, dport, ulen, c) + data

DATA = bytes((i * 7) & 0xFF for i in range(PAYLOAD))  # carga determinista

LINKTYPE_EN10MB = 1
with open(OUT, "wb") as f:
    f.write(struct.pack("!IHHiIII", 0xa1b2c3d4, 2, 4, 0, 0, 65535, LINKTYPE_EN10MB))
    ts = 0
    for i in range(N):
        dport = random.randint(1024, 65535)
        u   = udp(SPORT, dport, DATA)
        ip  = ip_hdr(SRC_IP, DST_IP, len(u), socket.IPPROTO_UDP, i & 0xFFFF)
        eth = DMAC + SMAC + struct.pack("!H", 0x0800)
        pkt = eth + ip + u
        ts_s, ts_us = divmod(ts, 1000000); ts += 10000  # 10 ms entre paquetes
        f.write(struct.pack("!IIII", ts_s, ts_us, len(pkt), len(pkt)))
        f.write(pkt)
print("escrito", OUT, "con", N, "datagramas sport", SPORT, "trama", 14 + 20 + 8 + PAYLOAD, "B")
