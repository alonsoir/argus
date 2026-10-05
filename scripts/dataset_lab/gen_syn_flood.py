#!/usr/bin/env python3
# DAY287 2.2 — genera un pcap de SYN flood: N SYN, puerto origen distinto por paquete,
# 192.168.100.50 -> 192.168.100.1:80, MACs de la topologia del lab. Solo stdlib.
import struct, socket, sys, random

N          = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
OUT        = sys.argv[2] if len(sys.argv) > 2 else "/vagrant/datasets/lab/syn_flood_5k_lab.pcap"
SMAC       = bytes.fromhex("080027078c2f")  # 08:00:27:07:8c:2f  client eth1
DMAC       = bytes.fromhex("0800276f63da")  # 08:00:27:6f:63:da  defender eth2
SRC_IP     = socket.inet_aton("192.168.100.50")
DST_IP     = socket.inet_aton("192.168.100.1")
DPORT      = 80
random.seed(42)  # reproducible

def cksum(data):
    if len(data) % 2:
        data += b"\x00"
    s = sum(struct.unpack("!%dH" % (len(data) // 2), data))
    s = (s >> 16) + (s & 0xFFFF)
    s += s >> 16
    return (~s) & 0xFFFF

def ip_hdr(src, dst, payload_len, proto=socket.IPPROTO_TCP, ident=0):
    ver_ihl = (4 << 4) | 5
    total   = 20 + payload_len
    h = struct.pack("!BBHHHBBH4s4s", ver_ihl, 0, total, ident, 0, 64, proto, 0, src, dst)
    c = cksum(h)
    return struct.pack("!BBHHHBBH4s4s", ver_ihl, 0, total, ident, 0, 64, proto, c, src, dst)

def tcp_syn(sport, dport, seq):
    off_flags = (5 << 12) | 0x002  # data offset 5, flag SYN
    pseudo_hdr_fields = (SRC_IP, DST_IP, 0, socket.IPPROTO_TCP, 20)
    def pack(csum):
        return struct.pack("!HHLLHHHH", sport, dport, seq, 0, off_flags, 1480, csum, 0)
    pseudo = struct.pack("!4s4sBBH", *pseudo_hdr_fields)
    c = cksum(pseudo + pack(0))
    return pack(c)

LINKTYPE_EN10MB = 1
with open(OUT, "wb") as f:
    f.write(struct.pack("!IHHiIII", 0xa1b2c3d4, 2, 4, 0, 0, 65535, LINKTYPE_EN10MB))
    ts = 0
    for i in range(N):
        sport = 49152 + (i % (65536 - 49152))
        tcp = tcp_syn(sport, DPORT, random.getrandbits(32))
        ip  = ip_hdr(SRC_IP, DST_IP, len(tcp), ident=i & 0xFFFF)
        eth = DMAC + SMAC + struct.pack("!H", 0x0800)
        pkt = eth + ip + tcp
        ts_s, ts_us = divmod(ts, 1000000); ts += 10000  # 10 ms entre paquetes
        f.write(struct.pack("!IIII", ts_s, ts_us, len(pkt), len(pkt)))
        f.write(pkt)
print("escrito", OUT, "con", N, "SYN")
