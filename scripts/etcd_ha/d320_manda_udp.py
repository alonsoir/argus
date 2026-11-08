#!/usr/bin/env python3
# [PROTEGIDOS-ANTISPOOF-D320] ADR-060 8e.4b: manda N paquetes UDP con el ORIGEN que se le dé (socket raw, IP_HDRINCL),
# para probar el antispoofing. Uso (root): python3 -I d320_manda_udp.py ORIGEN DESTINO N
# Lo usan d320_antispoof_e2e.sh (en el client y en un netns del defender) y la misma técnica que d320_medir_antispoof.sh.
import socket
import struct
import sys

if len(sys.argv) != 4:
    print("uso: d320_manda_udp.py ORIGEN DESTINO N", file=sys.stderr)
    sys.exit(2)
src, dst, n = sys.argv[1], sys.argv[2], int(sys.argv[3])
if not 1 <= n <= 10000:
    print("N en [1, 10000]", file=sys.stderr)
    sys.exit(2)
s = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_RAW)
carga = b"argus-d320-antispoof"
udp = struct.pack("!HHHH", 40320, 40321, 8 + len(carga), 0) + carga
ip = struct.pack("!BBHHHBBH4s4s", 0x45, 0, 20 + len(udp), 0, 0, 64, 17, 0, socket.inet_aton(src), socket.inet_aton(dst))
for _ in range(n):
    s.sendto(ip + udp, (dst, 0))
print(f"enviados {n} UDP {src} -> {dst}")
