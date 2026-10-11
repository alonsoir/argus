#!/usr/bin/env python3
"""DAY286: corrige AGG_ANCHOR en patch_d286_window_ms_single.py (DdosWindow tiene 2 miembros mas)."""
p = "/vagrant/patch_d286_window_ms_single.py"
s = open(p).read()
old = 'AGG_ANCHOR = "    std::vector<DdosVictimDelta> victims;  // solo delta > 0; d_pkts desc, luego dst_ip\\n};\\n"'
new = 'AGG_ANCHOR = "    uint32_t evicted = 0;         // estaban en la lectura anterior y ya no estan\\n};\\n"'
if new in s:
    print("YA CORREGIDO")
elif s.count(old) == 1:
    open(p, "w").write(s.replace(old, new))
    print("CORREGIDO")
else:
    print("ABORTO: no encuentro la linea AGG_ANCHOR original")
