#!/usr/bin/env python3
# DAY289 — day288_post.sh: registro configurable por REG (por defecto "runs" = comportamiento DAY288).
import sys
from pathlib import Path
F = Path("/vagrant/day288_post.sh")
MODO = sys.argv[1] if len(sys.argv) > 1 else "--check"
if MODO not in ("--check", "--apply"):
    sys.exit("uso: --check | --apply")
t = F.read_text()
if 'REG=${REG:-runs}' in t:
    print("YA APLICADO"); sys.exit(0)
cambios = [('FAM=${1:?familia}; R=${2:?tasa}; P=${3:?proto}\n',
            'FAM=${1:?familia}; R=${2:?tasa}; P=${3:?proto}\nREG=${REG:-runs}  # DAY289: registro (runs | contraste)\n'),
           ('"$D/runs.tsv"', '"$D/${REG}.tsv"'),
           ('"$D/runs_caliente.tsv"', '"$D/${REG}_caliente.tsv"'),
           ('"$D/runs_descartadas.tsv"', '"$D/${REG}_descartadas.tsv"')]
for viejo, _ in cambios:
    n = t.count(viejo)
    if n != 1:
        sys.exit(f"PARAR: '{viejo.strip()}' aparece {n} veces (se esperaba 1); no se toca nada")
if MODO == "--check":
    print("CHECK OK: 4 sustituciones aplicables"); sys.exit(0)
for viejo, nuevo in cambios:
    t = t.replace(viejo, nuevo)
F.write_text(t)
print("APLICADO")
