#!/usr/bin/env python3
"""DAY286: d286_h2_equiv.py excluye fast alerts del cruce (estan fuera de las cabezas)."""
p = "/vagrant/scripts/d286_h2_equiv.py"
s = open(p).read()
if "n_fast" in s:
    print("YA APLICADO")
    raise SystemExit(0)
old = "for ev, d in vw.items():\n    if ev not in v2:\n        continue\n"
new = ("n_fast = 0\nfor ev, d in vw.items():\n    if ev.startswith(\"fast-alert-\"):\n"
       "        n_fast += 1\n        continue\n    if ev not in v2:\n        continue\n")
old2 = 'print(f"eventos con ambas lineas={n_join}")'
new2 = 'print(f"fast alerts excluidas={n_fast}")\n' + old2
if s.count(old) != 1 or s.count(old2) != 1:
    print("ABORTO: fragmento no encontrado una sola vez")
    raise SystemExit(1)
open(p, "w").write(s.replace(old, new).replace(old2, new2))
print("APLICADO")
