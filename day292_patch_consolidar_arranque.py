#!/usr/bin/env python3
# DAY292 — añade la columna 'arranque' (D4) a day292_consolidar.py. Atómico. Uso: --check | --apply
import sys
F = "/vagrant/day292_consolidar.py"
MARCA = "ARRANQUE_S"
E = [
 ('ATQ, INO, VIC = "192.168.100.50", "192.168.100.51", "192.168.100.1"\n',
  'ATQ, INO, VIC = "192.168.100.50", "192.168.100.51", "192.168.100.1"\n'
  '# D4: segundos de arranque del atacante fuera del entrenamiento. argv[1], defecto 2.0, rango [0, 10].\n'
  'ARRANQUE_S = float(sys.argv[1]) if len(sys.argv) > 1 else 2.0\n'
  'if not 0.0 <= ARRANQUE_S <= 10.0:\n'
  '    print(f"PARAR: ARRANQUE_S={ARRANQUE_S} fuera de rango [0, 10] s (defecto 2.0)")\n'
  '    sys.exit(1)\n'),
 ('    d = d.assign(rol=rol, fase=fase, etiqueta=(rol == "atacante").astype(int),\n',
  '    d = d.assign(rol=rol, fase=fase, etiqueta=(rol == "atacante").astype(int),\n'
  '                 arranque=(rol == "atacante") & (d.ts_ns < t0 + int(ARRANQUE_S * 1e9)),\n'),
 ('print("== totales")\n',
  'print(f"== arranque del atacante (primeros {ARRANQUE_S} s) por corrida")\n'
  'print(X[X.arranque].groupby(["familia", "tasa"]).size().to_string())\n'
  'print("== totales")\n'),
]
modo = sys.argv[1] if len(sys.argv) > 1 else ""
if modo not in ("--check", "--apply"):
    sys.exit("uso: --check | --apply")
s = open(F).read()
if MARCA in s:
    sys.exit("ABORTA: la marca ya está (ya aplicado)")
for viejo, _ in E:
    if s.count(viejo) != 1:
        sys.exit(f"ABORTA: anclaje encontrado {s.count(viejo)} veces, se esperaba 1:\n{viejo}")
for viejo, nuevo in E:
    s = s.replace(viejo, nuevo)
if modo == "--check":
    print("OK check: 3 anclajes únicos")
    sys.exit(0)
compile(s, F, "exec")
open(F, "w").write(s)
print("APLICADO")
