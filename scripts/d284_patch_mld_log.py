#!/usr/bin/env python3
# DAY284 — ML_DETECTOR_LOG parametrizable en ml-detector-start (defecto = ruta actual). Idempotente, no commitea.
# Uso: d284_patch_mld_log.py [--check]
import sys, pathlib
p = pathlib.Path("/vagrant/Makefile")
src = p.read_text()
if "ML_DETECTOR_LOG ?=" in src:
    print("YA PARCHEADO: nada que hacer"); sys.exit(0)

head = "ml-detector-start:\n"
if src.count(head) != 1:
    print("PARAR: 'ml-detector-start:' no aparece una sola vez"); sys.exit(1)
i0 = src.find(head)
l0 = i0 + len(head)
l1 = src.find("\n", l0) + 1
line = src[l0:l1]

a_old = "mkdir -p /vagrant/logs/lab &&"
a_new = "mkdir -p $(dir $(ML_DETECTOR_LOG)) &&"
b_old = ">> /vagrant/logs/lab/ml-detector.log 2>&1"
b_new = ">> $(ML_DETECTOR_LOG) 2>&1"
for old in (a_old, b_old):
    n = line.count(old)
    if n != 1:
        print(f"PARAR: {old!r} aparece {n} veces en la receta (esperado 1)"); sys.exit(1)

new_line = line.replace(a_old, a_new).replace(b_old, b_new)
decl = ("# DAY284 — ruta del log del ml-detector; override p.ej. ML_DETECTOR_LOG=/tmp/argus-lab/ml-detector.log\n"
        "ML_DETECTOR_LOG ?= /vagrant/logs/lab/ml-detector.log\n\n")
out = src[:i0] + decl + head + new_line + src[l1:]

if "--check" in sys.argv:
    print("CHECK OK: anclas unicas en la receta, se aplicaria el cambio"); sys.exit(0)
p.write_text(out)
print("OK: Makefile parcheado (ML_DETECTOR_LOG)")
