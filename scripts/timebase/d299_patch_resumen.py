#!/usr/bin/env python3
"""DAY299: d298_etapa1_resumen.sh cuenta el aviso renombrado [DDOS-V2-ANOMALIA] estado_victima_ausente
ademas del antiguo [DDOS-V2] sin_estado (logs de DAY298). Sin esto contaria 0 por construccion.
Uso: --check | --apply (desde la raiz del repo)."""
import os
import sys

P = "scripts/timebase/d298_etapa1_resumen.sh"
EDITS = [
    (r'/\[DDOS-V2\] sin_estado=/ {for(i=1;i<=NF;i++) if($i ~ /^sin_estado=/)',
     r'/\[DDOS-V2\] sin_estado=|\[DDOS-V2-ANOMALIA\] estado_victima_ausente=/ {for(i=1;i<=NF;i++) if($i ~ /^(sin_estado|estado_victima_ausente)=/)'),
    (r'sin_estado=%d\n", n, p, t, s}',
     r'estado_victima_ausente=%d\n", n, p, t, s}'),
]


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
        print("uso: --check | --apply")
        return 2
    t = open(P, encoding="utf-8").read()
    if all(new in t for _, new in EDITS):
        print("[YA-APLICADO]")
        return 0
    for old, _ in EDITS:
        if t.count(old) != 1:
            print(f"[ABORTA] ancla {t.count(old)} veces: {old[:60]}")
            return 1
    if sys.argv[1] == "--check":
        print(f"[CHECK-OK] {len(EDITS)} ediciones pendientes en {P}")
        return 0
    for old, new in EDITS:
        t = t.replace(old, new, 1)
    tmp = P + ".d299tmp"
    open(tmp, "w", encoding="utf-8").write(t)
    os.replace(tmp, P)
    print(f"[APLICADO] {len(EDITS)} ediciones en {P}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
