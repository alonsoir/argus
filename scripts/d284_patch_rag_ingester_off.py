#!/usr/bin/env python3
# DAY284 — rag-ingester (deprecado) fuera de pipeline-start / pipeline-start-x86-libpcap / pipeline-status.
# No toca build, seeds, tests, pipeline-stop ni el componente. Idempotente, atomico, no commitea.
# Uso: d284_patch_rag_ingester_off.py [--check]
import sys, pathlib
p = pathlib.Path("/vagrant/Makefile")
src = p.read_text()
start_blk = "\t@$(MAKE) rag-ingester-start\n\t@sleep 3\n"
status_key = "tmux has-session -t rag-ingester"

n_start = src.count(start_blk)
n_status = src.count(status_key)
if n_start == 0 and n_status == 0:
    print("YA PARCHEADO: nada que hacer"); sys.exit(0)
if n_start != 2:
    print(f"PARAR: bloque de arranque aparece {n_start} veces (esperado 2)"); sys.exit(1)
if n_status != 1:
    print(f"PARAR: linea de estado aparece {n_status} veces (esperado 1)"); sys.exit(1)

out = src.replace(start_blk, "")
i = out.find(status_key)
ls = out.rfind("\n", 0, i) + 1
le = out.find("\n", i) + 1
out = out[:ls] + out[le:]

if "--check" in sys.argv:
    print("CHECK OK: 2 arranques + 1 estado, se aplicaria el cambio"); sys.exit(0)
p.write_text(out)
print("OK: rag-ingester fuera del arranque y del estado")
