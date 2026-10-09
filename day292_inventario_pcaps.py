#!/usr/bin/env python3
# DAY292 — inventario de pcaps: paquetes, sha256, protocolos, IPs origen/destino, fragmentos. Solo lectura.
import hashlib, struct, sys, collections
def ip(b): return ".".join(str(x) for x in b)
for f in sys.argv[1:]:
    h = hashlib.sha256(open(f, "rb").read()).hexdigest()
    d = open(f, "rb").read()
    magic = d[:4]
    end = "<" if magic in (b"\xd4\xc3\xb2\xa1", b"\x4d\x3c\xb2\xa1") else ">"
    dlt = struct.unpack(end + "I", d[20:24])[0]
    off, n = 24, 0
    proto, src, dst = collections.Counter(), collections.Counter(), collections.Counter()
    noip = frag = 0
    while off + 16 <= len(d):
        incl = struct.unpack(end + "I", d[off+8:off+12])[0]
        p = d[off+16:off+16+incl]; off += 16 + incl; n += 1
        if dlt != 1 or len(p) < 34 or p[12:14] != b"\x08\x00": noip += 1; continue
        q = p[14:]
        if struct.unpack(">H", q[6:8])[0] & 0x1fff: frag += 1
        proto[{6: "TCP", 17: "UDP"}.get(q[9], str(q[9]))] += 1
        src[ip(q[12:16])] += 1; dst[ip(q[16:20])] += 1
    print(f"{f.split('/')[-1]}  pkts={n}  dlt={dlt}  no_ipv4={noip}  frag_no_primeros={frag}")
    print(f"  sha256={h}")
    print(f"  proto={dict(proto)}  src={src.most_common(3)}  dst={dst.most_common(3)}")
