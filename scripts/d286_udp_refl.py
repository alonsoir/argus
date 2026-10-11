#!/usr/bin/env python3
"""DAY286: envia N datagramas UDP desde SRC_IP:53 a DST:DPORT (simula respuesta reflejada).
Necesita root (puerto < 1024). Uso: sudo python3 d286_udp_refl.py SRC_IP DST DPORT N"""
import socket, sys, time
src, dst, dport, n = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.bind((src, 53))
for i in range(n):
    s.sendto(b"R" * 400, (dst, dport))
    time.sleep(0.1)
print(f"sent {n} datagramas {src}:53 -> {dst}:{dport}")
