#!/usr/bin/env python3
# DAY284 — SNIFFER_LOG parametrizable en sniffer-start (defecto = ruta actual). Idempotente, no commitea.
# Uso: d284_patch_sniffer_log.py [--check]
import sys, pathlib
p = pathlib.Path("/vagrant/Makefile")
src = p.read_text()
if "SNIFFER_LOG ?=" in src:
    print("YA PARCHEADO: nada que hacer"); sys.exit(0)

head = "# ── sniffer-start — Variant A (eBPF)"
i0 = src.find(head)
if i0 < 0 or src.count(head) != 1:
    print("PARAR: cabecera de sniffer-start no encontrada una sola vez"); sys.exit(1)
i1 = src.find("\n\n", i0)
if i1 < 0:
    print("PARAR: fin de bloque no encontrado"); sys.exit(1)
block = src[i0:i1]

a_old = "'mkdir -p /vagrant/logs/lab && \\"
a_new = "'mkdir -p $(dir $(SNIFFER_LOG)) && \\"
b_old = ">> /vagrant/logs/lab/sniffer.log 2>&1'\""
b_new = ">> $(SNIFFER_LOG) 2>&1'\""
for old in (a_old, b_old):
    n = block.count(old)
    if n != 1:
        print(f"PARAR: ancla {old!r} aparece {n} veces en el bloque (esperado 1)"); sys.exit(1)

new_block = block.replace(a_old, a_new).replace(b_old, b_new)
decl = ("# DAY284 — ruta del log del sniffer; override p.ej. SNIFFER_LOG=/tmp/argus-lab/sniffer.log\n"
        "SNIFFER_LOG ?= /vagrant/logs/lab/sniffer.log\n\n")
out = src[:i0] + decl + new_block + src[i1:]

if "--check" in sys.argv:
    print("CHECK OK: anclas unicas, se aplicaria el cambio"); sys.exit(0)
p.write_text(out)
print("OK: Makefile parcheado (SNIFFER_LOG)")
