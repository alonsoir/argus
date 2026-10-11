#!/usr/bin/env python3
# DAY289 — contraste benigno de reflexión: respuestas DNS/NTP LEGÍTIMAS hacia 192.168.100.1.
# Mismo esqueleto y topología que gen_reflection.py (helpers copiados: aquel fichero lee argv al
# importarse). Origen .50, como el ataque, para que solo cambien tamaño y tasa. Solo stdlib, seed 42.
# Uso: gen_benign_dns_ntp.py MODO N OUT
#   MODO small: 80 % DNS trama 80-250 B (sport 53) + 20 % NTP trama 90 B (sport 123)
#   MODO large: 100 % DNS trama 1200-1442 B (sport 53; respuestas DNSSEC/TXT legítimas)
import struct, socket, sys, random

if len(sys.argv) != 4 or sys.argv[1] not in ("small", "large"):
    sys.exit("uso: gen_benign_dns_ntp.py small|large N OUT")
MODO, N, OUT = sys.argv[1], int(sys.argv[2]), sys.argv[3]
SMAC   = bytes.fromhex("080027078c2f")  # 08:00:27:07:8c:2f  client eth1
DMAC   = bytes.fromhex("0800276f63da")  # 08:00:27:6f:63:da  defender eth2
SRC_IP = socket.inet_aton("192.168.100.50")
DST_IP = socket.inet_aton("192.168.100.1")
HDR    = 14 + 20 + 8
random.seed(42)  # reproducible

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

cuenta, tramas = {53: 0, 123: 0}, []
LINKTYPE_EN10MB = 1
with open(OUT, "wb") as f:
    f.write(struct.pack("!IHHiIII", 0xa1b2c3d4, 2, 4, 0, 0, 65535, LINKTYPE_EN10MB))
    ts = 0
    for i in range(N):
        if MODO == "small":
            if random.random() < 0.8:
                sport, trama = 53, random.randint(80, 250)
            else:
                sport, trama = 123, 90
        else:
            sport, trama = 53, random.randint(1200, 1442)
        dport = random.randint(1024, 65535)
        data  = bytes(((i + j) * 7) & 0xFF for j in range(trama - HDR))  # carga determinista
        u   = udp(sport, dport, data)
        ip  = ip_hdr(SRC_IP, DST_IP, len(u), socket.IPPROTO_UDP, i & 0xFFFF)
        pkt = DMAC + SMAC + struct.pack("!H", 0x0800) + ip + u
        assert len(pkt) == trama
        ts_s, ts_us = divmod(ts, 1000000); ts += 10000  # 10 ms entre paquetes
        f.write(struct.pack("!IIII", ts_s, ts_us, len(pkt), len(pkt)))
        f.write(pkt)
        cuenta[sport] += 1
        tramas.append(trama)
print(f"escrito {OUT}: modo {MODO}, {N} datagramas, sport53={cuenta[53]} sport123={cuenta[123]}, "
      f"trama min/media/max = {min(tramas)}/{sum(tramas)/len(tramas):.1f}/{max(tramas)} B")
