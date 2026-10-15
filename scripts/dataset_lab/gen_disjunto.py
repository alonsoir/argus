#!/usr/bin/env python3
# DAY298 1.a: pcap largo de N paquetes repitiendo el original en vueltas, SIN repetir ninguna 5-tupla.
# Los flujos del sniffer no caducan (DEBT-SNIFFER-FLOW-EXPIRY-001): repetir una tupla en cualquier momento
# acumula flow_packet_count. Vuelta 0 = original identico. Vuelta k>=1: cada (ip_src, sport, ip_dst, dport)
# recibe un dport nuevo de una lista barajada (semilla fija) de puertos >=1024 que esa clase
# (ip_src, sport, ip_dst) no usa en el original; nunca se reutiliza. Checksum UDP a 0 (valido en IPv4).
# Timestamps desplazados por vuelta (monotonos). Solo pcap clasico, Ethernet, IPv4/UDP: aborta ante otra cosa.
# Escribe a SALIDA.tmp y renombra solo si todo fue bien.
# Uso: d298_pcap_disjunto.py ENTRADA SALIDA N SEMILLA
import hashlib, os, random, struct, sys

def main():
    if len(sys.argv) != 5:
        sys.exit("uso: d298_pcap_disjunto.py ENTRADA SALIDA N SEMILLA")
    src, dst, n, seed = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
    data = open(src, 'rb').read()
    magics = {b'\xd4\xc3\xb2\xa1': ('<', 10**6), b'\xa1\xb2\xc3\xd4': ('>', 10**6),
              b'\x4d\x3c\xb2\xa1': ('<', 10**9), b'\xa1\xb2\x3c\x4d': ('>', 10**9)}
    if data[:4] not in magics:
        sys.exit(f"ABORTA: magic {data[:4].hex()} no es pcap clasico")
    e, unit = magics[data[:4]]
    if struct.unpack(e + 'I', data[20:24])[0] != 1:
        sys.exit("ABORTA: linktype != 1 (Ethernet)")
    recs, off = [], 24
    while off < len(data):
        ts_s, ts_f, incl, orig = struct.unpack(e + 'IIII', data[off:off + 16])
        pkt = bytes(data[off + 16:off + 16 + incl])
        off += 16 + incl
        if len(pkt) < 42 or pkt[12:14] != b'\x08\x00':
            sys.exit("ABORTA: paquete no Ethernet/IPv4")
        if pkt[23] != 17:
            sys.exit("ABORTA: paquete no UDP")
        u = 14 + (pkt[14] & 0x0f) * 4
        clase = pkt[26:30] + pkt[u:u + 2] + pkt[30:34]
        dport = struct.unpack('>H', pkt[u + 2:u + 4])[0]
        recs.append((ts_s * unit + ts_f, orig, pkt, u, clase, dport))
    if not recs:
        sys.exit("ABORTA: pcap vacio")
    usados = {}
    for _, _, _, _, c, p in recs:
        usados.setdefault(c, set()).add(p)
    rng = random.Random(seed)
    pools, ptr = {}, {}
    for c in sorted(usados):
        libres = [p for p in range(1024, 65536) if p not in usados[c]]
        rng.shuffle(libres)
        pools[c], ptr[c] = libres, 0
    t0 = recs[0][0]
    span = recs[-1][0] - t0 + unit
    asign = {}
    tmp = dst + '.tmp'
    with open(tmp, 'wb') as f:
        f.write(data[:24])
        for i in range(n):
            k, j = divmod(i, len(recs))
            t, orig, pkt, u, c, p = recs[j]
            if k > 0:
                key = (k, c, p)
                if key not in asign:
                    if ptr[c] >= len(pools[c]):
                        f.close()
                        os.remove(tmp)
                        sys.exit(f"ABORTA: sin puertos libres para la clase {c.hex()} en la vuelta {k}")
                    asign[key] = pools[c][ptr[c]]
                    ptr[c] += 1
                b = bytearray(pkt)
                b[u + 2:u + 4] = struct.pack('>H', asign[key])
                b[u + 6:u + 8] = b'\x00\x00'
                pkt = bytes(b)
            tn = t + k * span
            f.write(struct.pack(e + 'IIII', tn // unit, tn % unit, len(pkt), orig))
            f.write(pkt)
    os.replace(tmp, dst)
    vueltas = (n + len(recs) - 1) // len(recs)
    base = len({(c, p) for _, _, _, _, c, p in recs[:min(n, len(recs))]})
    print(f"entrada={src} paquetes_entrada={len(recs)} salida={dst} paquetes_salida={n} vueltas={vueltas} semilla={seed}")
    print(f"tuplas_esperadas={base + len(asign)} (vuelta0={base} nuevas={len(asign)})")
    for c in sorted(usados):
        print(f"  clase {c.hex()}: puertos_originales={len(usados[c])} libres={len(pools[c])} usados_nuevos={ptr[c]}")
    print(f"sha256={hashlib.sha256(open(dst, 'rb').read()).hexdigest()}")

main()
