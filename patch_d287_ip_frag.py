#!/usr/bin/env python3
"""DAY287 [IP-FRAG-D287]: el sniffer XDP no envia al ring los fragmentos IPv4 no-primeros.
Antes leia bytes de la carga como puertos -> flujos fantasma (medido: 63 % de las filas del
bloque B de CICDDoS2019 eran basura). Siguen contados en ddos_victims (van antes); nuevo
contador STAT_FRAG_SKIPPED (indice 3) para que el invariante de RING-LOSS-D275 siga cuadrando.
Uso: python3 patch_d287_ip_frag.py --check | --apply   (atomico, idempotente, no compila)"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REL = "sniffer/src/kernel/sniffer.bpf.c"
MARK = "[IP-FRAG-D287]"

EDITS = [
    ("#define STAT_FILTER_DISCARD  2\n#define STAT_MAX             3\n",
     "#define STAT_FILTER_DISCARD  2\n"
     "#define STAT_FRAG_SKIPPED    3  /* [IP-FRAG-D287] fragmentos no-primeros: contados en ddos_victims, sin ring */\n"
     "#define STAT_MAX             4\n"),
    (" *                        + stats[STAT_FILTER_DISCARD]\n",
     " *                        + stats[STAT_FILTER_DISCARD]\n"
     " *                        + stats[STAT_FRAG_SKIPPED]   [IP-FRAG-D287]\n"),
    ("    // Reserve ring buffer space\n    struct simple_event *event = bpf_ringbuf_reserve(&events, sizeof(*event), 0);\n",
     "    /* [IP-FRAG-D287] Fragmento IPv4 no-primero (offset != 0): no lleva cabecera L4.\n"
     "     * Ya contado arriba en ddos_victims; no se parsean puertos ni se envia al ring\n"
     "     * (antes se leian bytes de la carga como puertos -> flujos fantasma). El primer\n"
     "     * fragmento (offset 0, MF=1) sigue el camino normal. ip[6..7] dentro de los 20 B ya verificados. */\n"
     "    if ((((__u16)(ip[6] & 0x1F) << 8) | ip[7]) != 0) {\n"
     "        stat_inc(STAT_FRAG_SKIPPED);\n"
     "        return XDP_PASS;\n"
     "    }\n"
     "\n"
     "    // Reserve ring buffer space\n"
     "    struct simple_event *event = bpf_ringbuf_reserve(&events, sizeof(*event), 0);\n"),
]


def die(m):
    print(f"[ABORT] {m}")
    sys.exit(2)


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
        print(__doc__)
        sys.exit(1)
    p = ROOT / REL
    text = p.read_text()
    done = [new in text for _, new in EDITS]
    if all(done):
        print("[OK] YA APLICADO: 3 sitios presentes.")
        return
    if any(done):
        die(f"estado PARCIAL {done}; revisar con git diff")
    if MARK in text:
        die("la marca ya aparece en el fichero sin los 3 sitios completos")
    new_text = text
    for old, new in EDITS:
        c = new_text.count(old)
        if c != 1:
            die(f"ancla aparece {c} veces (esperado 1): {old[:60]!r}")
        new_text = new_text.replace(old, new, 1)
        print(f"[PLAN] {REL}: {old.splitlines()[0][:60]!r} -> +{len(new.splitlines()) - len(old.splitlines())} lineas")
    if sys.argv[1] == "--check":
        print("[CHECK] sin cambios en disco. Lanza --apply.")
        return
    t = p.with_name(p.name + ".tmp")
    t.write_text(new_text)
    t.replace(p)
    print(f"[APPLY] {REL}")
    print("[OK] aplicado. Siguiente: make pipeline-build PROFILE=production (en el Mac).")


if __name__ == "__main__":
    main()
