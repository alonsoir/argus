#!/usr/bin/env python3
"""patch_snap_delta_ring.py  --  DAY275, punto 3

Extiende snap_delta.py para usar los contadores nuevos del kernel
(ver patch_ring_loss_counters.py):

    stats[1]  bpf_ringbuf_reserve fallido (ring lleno)
    stats[2]  bpf_ringbuf_discard (filtros de puerto / L4 truncada)

y comprobar la identidad exacta del kernel:

    B (suma mapa ddos_victims) = A (stats[0]) + stats[1] + stats[2]

Tras la linea "A - B" imprime stats[1], stats[2], el residuo
B - (A + s1 + s2) (0 = identidad exacta) y el % de paquetes contados que llego
al ring. Si el snapshot ANTES no tiene las claves 1/2 (sniffer viejo) se
tratan como 0 y se avisa.

Uso (exactamente uno):  --dry | --apply | --check     [--file RUTA]
No hace commit. Aborta sin escribir si las anclas no coinciden exactamente.
"""
import argparse
import difflib
import sys
from pathlib import Path

TAG = "RING-LOSS-D275"

ANCHOR_STATS0 = '    stats0 = b["stats"].get(0, 0) - a["stats"].get(0, 0)\n'
ANCHOR_AB = ('    print("  A - B (ring - mapa)            : %+d   '
             '(0 = sin perdida entre contador y ring)" % (stats0 - sum_p))\n')

ADD_STATS = '''    # [RING-LOSS-D275:STATS] contadores nuevos del kernel (claves 1 y 2)
    stats1 = b["stats"].get(1, 0) - a["stats"].get(1, 0)
    stats2 = b["stats"].get(2, 0) - a["stats"].get(2, 0)
    has_ring_counters = (1 in b["stats"]) and (2 in b["stats"]) and (1 in a["stats"]) and (2 in a["stats"])
'''

ADD_PRINT = '''    # [RING-LOSS-D275:PRINT] descomposicion exacta de A - B
    if has_ring_counters:
        print("  stats[1] reserve fallido (ring): %+d   (ring lleno)" % stats1)
        print("  stats[2] descartes filtro/L4   : %+d   (puertos excluidos, cabecera L4 truncada)" % stats2)
        print("  B - (A + s1 + s2)              : %+d   (0 = identidad exacta del kernel)"
              % (sum_p - (stats0 + stats1 + stats2)))
        if sum_p:
            print("  llegado al ring (A / B)        : %.1f %%" % (100.0 * stats0 / sum_p))
    else:
        print("  AVISO: faltan stats[1]/stats[2] en algun snapshot (sniffer sin contadores de perdida)")
'''


def transform(src):
    if TAG in src:
        return None, ["ya contiene %s: ya parcheado (usa --check)" % TAG]
    errs = []
    for name, anc in (("stats0", ANCHOR_STATS0), ("A-B print", ANCHOR_AB)):
        n = src.count(anc)
        if n != 1:
            errs.append("ancla '%s': %d coincidencias (esperada 1)" % (name, n))
    if errs:
        return None, errs
    out = src.replace(ANCHOR_STATS0, ANCHOR_STATS0 + ADD_STATS, 1)
    out = out.replace(ANCHOR_AB, ANCHOR_AB + ADD_PRINT, 1)
    return out, []


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry", action="store_true")
    g.add_argument("--apply", action="store_true")
    g.add_argument("--check", action="store_true")
    ap.add_argument("--file", default=None)
    a = ap.parse_args()

    path = Path(a.file) if a.file else Path(__file__).resolve().parent / "snap_delta.py"
    if not path.is_file():
        print("ERROR: no existe %s" % path)
        return 2
    src = path.read_text()

    if a.check:
        s, p = src.count("[RING-LOSS-D275:STATS]"), src.count("[RING-LOSS-D275:PRINT]")
        print("stats=%d print=%d (esperado 1/1)" % (s, p))
        if (s, p) == (1, 1):
            print("PARCHEADO")
            return 0
        if (s, p) == (0, 0):
            print("NO PARCHEADO")
            return 1
        print("PARCIAL: revisar a mano")
        return 3

    new, errs = transform(src)
    if errs:
        print("ABORTO (no se escribe nada):")
        for e in errs:
            print("  - " + e)
        return 2
    sys.stdout.writelines(difflib.unified_diff(src.splitlines(True), new.splitlines(True),
                                               "a/" + str(path), "b/" + str(path), n=2))
    if a.dry:
        print("\n[--dry] nada escrito.")
        return 0
    path.write_text(new)
    print("\n[--apply] escrito %s (sin commit)." % path)
    return 0


if __name__ == "__main__":
    sys.exit(main())