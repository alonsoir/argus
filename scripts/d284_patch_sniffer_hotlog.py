#!/usr/bin/env python3
# DAY284 — saca del camino caliente 4 logs por evento del sniffer, tras g_verbosity (mecanismo existente).
# Envuelve la sentencia completa en if(...){...}; no cambia su contenido. Idempotente, atomico, no commitea.
# Uso: d284_patch_sniffer_hotlog.py [--check]
import sys, pathlib
p = pathlib.Path("/vagrant/sniffer/src/userspace/ring_consumer.cpp")
src = p.read_text()
TAG = "// DAY284: log por evento fuera del camino caliente"
if TAG in src:
    print("YA PARCHEADO: nada que hacer"); sys.exit(0)

TARGETS = [
    ('std::cout << "[CRYPTO] \U0001F4E6 Compressed: "', "DETAILED"),
    ('std::cout << "[CRYPTO] \U0001F512 Encrypted: "',  "DETAILED"),
    ('std::cout << "[DUAL-NIC] ifindex="',              "DETAILED"),
    ('std::cout << "[FAST ALERT] Ransomware heuristic: "', "BASIC"),
]

out = src
for marker, lvl in TARGETS:
    n = out.count(marker)
    if n != 1:
        print(f"PARAR: marcador {marker!r} aparece {n} veces (esperado 1)"); sys.exit(1)
    i = out.find(marker)
    ls = out.rfind("\n", 0, i) + 1                 # inicio de la linea
    indent = out[ls:i]
    if indent.strip() != "":
        print(f"PARAR: {marker!r} no empieza la linea"); sys.exit(1)
    e = out.find("std::endl;", i)
    if e < 0:
        print(f"PARAR: sin 'std::endl;' tras {marker!r}"); sys.exit(1)
    le = out.find("\n", e) + 1                     # fin de la linea del ';'
    stmt = out[ls:le]
    body = "".join("    " + l if l.strip() else l for l in stmt.splitlines(keepends=True))
    wrapped = (f"{indent}if (g_verbosity >= FeatureLogger::VerbosityLevel::{lvl}) {{  {TAG}\n"
               f"{body}{indent}}}\n")
    out = out[:ls] + wrapped + out[le:]

if "--check" in sys.argv:
    print("CHECK OK: 4 marcadores unicos, se aplicaria el cambio"); sys.exit(0)
p.write_text(out)
print("OK: 4 sentencias envueltas en g_verbosity")
