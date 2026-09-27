#!/usr/bin/env python3
"""patch_ring_loss_counters.py  --  DAY275, punto 3 (cuantificar la perdida del ring)

Instrumenta sniffer/src/kernel/sniffer.bpf.c para que A-B (ring - mapa) se
descomponga EXACTAMENTE en sus dos causas posibles:

    B (mapa ddos_victims) = A (stats[0]) + stats[1] + stats[2]

    stats[0]  eventos enviados al ring (submit)   -- ya existe, NO se toca
    stats[1]  bpf_ringbuf_reserve fallido (ring lleno)      -- NUEVO
    stats[2]  bpf_ringbuf_discard (filtros / L4 truncada)   -- NUEVO (6 sitios)

Cambios (todos marcados con [RING-LOSS-D275:*]):
  1. stats: max_entries 1 -> 3 (+ macros STAT_*). Compatible: el loader busca el
     mapa por nombre y solo lee la clave 0.
  2. helper static __always_inline stat_inc(key), justo tras el mapa stats.
  3. rama `if (!event)` tras bpf_ringbuf_reserve: stat_inc(STAT_RESERVE_FAIL).
  4. los seis bpf_ringbuf_discard(event, 0): stat_inc(STAT_FILTER_DISCARD).

Uso (exactamente uno):
  --dry     muestra el diff, no escribe
  --apply   escribe el fichero (NO hace commit)
  --check   comprueba si el fichero esta ya parcheado (exit 0 = si, 1 = no, 3 = parcial)
Opcional: --file RUTA  (por defecto sniffer/src/kernel/sniffer.bpf.c junto a este script)

Si un ancla no aparece EXACTAMENTE las veces esperadas, aborta sin escribir (exit 2).
"""
import argparse
import difflib
import re
import sys
from pathlib import Path

TAG = "RING-LOSS-D275"
DEFAULT_REL = "sniffer/src/kernel/sniffer.bpf.c"

# --- 1. mapa stats ----------------------------------------------------------
MAP_RE = re.compile(
    r'(?P<blk>struct \{\n'
    r'[ \t]*__uint\(type, BPF_MAP_TYPE_ARRAY\);\n'
    r'[ \t]*__uint\(max_entries, 1\);\n'
    r'[ \t]*__type\(key, __u32\);\n'
    r'[ \t]*__type\(value, __u64\);\n'
    r'\} stats SEC\("\.maps"\);\n)'
)

MAP_NEW = '''/* [RING-LOSS-D275:MAP] Claves de stats. Identidad medida en userspace:
 *   ddos_victims(suma) = stats[STAT_EVENTS] + stats[STAT_RESERVE_FAIL]
 *                        + stats[STAT_FILTER_DISCARD]
 * STAT_EVENTS (0) conserva su significado y posicion historicos. */
#define STAT_EVENTS          0
#define STAT_RESERVE_FAIL    1
#define STAT_FILTER_DISCARD  2
#define STAT_MAX             3

struct {
    __uint(type, BPF_MAP_TYPE_ARRAY);
    __uint(max_entries, STAT_MAX);
    __type(key, __u32);
    __type(value, __u64);
} stats SEC(".maps");

/* [RING-LOSS-D275:HELPER] Incremento atomico de stats[key]. En un ARRAY la
 * clave siempre existe (key < max_entries); el NULL solo satisface al verificador. */
static __always_inline void stat_inc(__u32 key)
{
    __u64 *c = bpf_map_lookup_elem(&stats, &key);
    if (c)
        __sync_fetch_and_add(c, 1);
}
'''

# --- 3. reserve fallido -------------------------------------------------------
RESERVE_RE = re.compile(
    r'(?P<head>[ \t]*struct simple_event \*event = bpf_ringbuf_reserve\(&events, sizeof\(\*event\), 0\);\n'
    r'[ \t]*if \(!event\) \{\n)'
    r'(?P<ind>[ \t]*)(?P<ret>return XDP_PASS;\n[ \t]*\}\n)'
)

# --- 4. descartes -------------------------------------------------------------
DISCARD_RE = re.compile(r'^(?P<ind>[ \t]*)bpf_ringbuf_discard\(event, 0\);[ \t]*\n', re.M)
N_DISCARD = 6


def transform(src: str):
    """Devuelve (nuevo_texto, lista_de_errores)."""
    errs = []
    if TAG in src:
        return None, ["el fichero ya contiene %s: ya parcheado (usa --check)" % TAG]

    n_map = len(MAP_RE.findall(src))
    n_res = len(RESERVE_RE.findall(src))
    n_dis = len(DISCARD_RE.findall(src))
    if n_map != 1:
        errs.append("ancla mapa stats: %d coincidencias (esperada 1)" % n_map)
    if n_res != 1:
        errs.append("ancla reserve/if(!event): %d coincidencias (esperada 1)" % n_res)
    if n_dis != N_DISCARD:
        errs.append("bpf_ringbuf_discard(event, 0): %d sitios (esperados %d)" % (n_dis, N_DISCARD))
    if errs:
        return None, errs

    out = MAP_RE.sub(lambda m: MAP_NEW, src, count=1)
    out = RESERVE_RE.sub(
        lambda m: (m.group("head") + m.group("ind")
                   + "stat_inc(STAT_RESERVE_FAIL); /* [RING-LOSS-D275:RESERVE] */\n"
                   + m.group("ind") + m.group("ret")),
        out, count=1)
    out = DISCARD_RE.sub(
        lambda m: (m.group(0) + m.group("ind")
                   + "stat_inc(STAT_FILTER_DISCARD); /* [RING-LOSS-D275:DISCARD] */\n"),
        out)
    return out, []


def state(src: str):
    """(map, helper, reserve, discards) presentes."""
    return (src.count("[RING-LOSS-D275:MAP]"),
            src.count("[RING-LOSS-D275:HELPER]"),
            src.count("[RING-LOSS-D275:RESERVE]"),
            src.count("[RING-LOSS-D275:DISCARD]"))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry", action="store_true")
    g.add_argument("--apply", action="store_true")
    g.add_argument("--check", action="store_true")
    ap.add_argument("--file", default=None)
    a = ap.parse_args()

    path = Path(a.file) if a.file else Path(__file__).resolve().parent / DEFAULT_REL
    if not path.is_file():
        print("ERROR: no existe %s" % path)
        return 2
    src = path.read_text()

    if a.check:
        m, h, r, d = state(src)
        ok = (m, h, r, d) == (1, 1, 1, N_DISCARD)
        print("map=%d helper=%d reserve=%d discards=%d (esperado 1/1/1/%d)" % (m, h, r, d, N_DISCARD))
        if ok:
            print("PARCHEADO")
            return 0
        if (m, h, r, d) == (0, 0, 0, 0):
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

    diff = difflib.unified_diff(src.splitlines(True), new.splitlines(True),
                                "a/" + str(path), "b/" + str(path), n=2)
    sys.stdout.writelines(diff)

    if a.dry:
        print("\n[--dry] nada escrito.")
        return 0
    path.write_text(new)
    print("\n[--apply] escrito %s (sin commit). Siguiente: reconstruir el sniffer y --check." % path)
    return 0


if __name__ == "__main__":
    sys.exit(main())