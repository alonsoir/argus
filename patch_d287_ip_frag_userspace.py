#!/usr/bin/env python3
"""DAY287 [IP-FRAG-D287] parte 2: mismo criterio que el XDP en el resto del repo.
 - sniffer/src/userspace/main_libpcap.cpp (Variant B): fragmento IPv4 no-primero -> no se emite
   evento (antes leia bytes de la carga como puertos TCP/UDP).
 - snap_delta.py: lee stats[3] (STAT_FRAG_SKIPPED) y lo incluye en la identidad
   B = A + s1 + s2 + s3 (sin el, el residuo deja de ser 0 con trafico fragmentado).
Uso: python3 patch_d287_ip_frag_userspace.py --check | --apply   (atomico, idempotente, no compila)"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

EDITS = [
    ("sniffer/src/userspace/main_libpcap.cpp",
     "    if (ip_hdr_len < sizeof(struct ip)) return 0;\n",
     "    if (ip_hdr_len < sizeof(struct ip)) return 0;\n"
     "    // [IP-FRAG-D287] Fragmento no-primero (offset != 0): no lleva cabecera L4. No se emite\n"
     "    // evento, mismo criterio que el XDP (antes se leian bytes de la carga como puertos).\n"
     "    if ((ntohs(iph->ip_off) & IP_OFFMASK) != 0) return 0;\n"),
    ("snap_delta.py",
     '    stats2 = b["stats"].get(2, 0) - a["stats"].get(2, 0)\n',
     '    stats2 = b["stats"].get(2, 0) - a["stats"].get(2, 0)\n'
     '    stats3 = b["stats"].get(3, 0) - a["stats"].get(3, 0)  # [IP-FRAG-D287] fragmentos no-primeros\n'),
    ("snap_delta.py",
     '        print("  stats[2] descartes filtro/L4   : %+d   (puertos excluidos, cabecera L4 truncada)" % stats2)\n',
     '        print("  stats[2] descartes filtro/L4   : %+d   (puertos excluidos, cabecera L4 truncada)" % stats2)\n'
     '        print("  stats[3] fragmentos no-primeros: %+d   (sin L4: contados en el mapa, no van al ring)" % stats3)  # [IP-FRAG-D287]\n'),
    ("snap_delta.py",
     '        print("  B - (A + s1 + s2)              : %+d   (0 = identidad exacta del kernel)"\n'
     '              % (sum_p - (stats0 + stats1 + stats2)))\n',
     '        print("  B - (A + s1 + s2 + s3)         : %+d   (0 = identidad exacta del kernel)"  # [IP-FRAG-D287]\n'
     '              % (sum_p - (stats0 + stats1 + stats2 + stats3)))\n'),
]


def die(m):
    print(f"[ABORT] {m}")
    sys.exit(2)


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
        print(__doc__)
        sys.exit(1)
    texts = {}
    for rel, _, _ in EDITS:
        if rel not in texts:
            p = ROOT / rel
            if not p.exists():
                die(f"no existe {rel}")
            texts[rel] = p.read_text()
    done = [new in texts[rel] for rel, _, new in EDITS]
    if all(done):
        print("[OK] YA APLICADO: 4 sitios presentes.")
        return
    if any(done):
        die(f"estado PARCIAL {done}; revisar con git diff")
    new = dict(texts)
    for rel, old, rep in EDITS:
        c = new[rel].count(old)
        if c != 1:
            die(f"ancla en {rel} aparece {c} veces (esperado 1): {old.splitlines()[0][:60]!r}")
        new[rel] = new[rel].replace(old, rep, 1)
        print(f"[PLAN] {rel}: {old.splitlines()[0].strip()[:60]!r}")
    if sys.argv[1] == "--check":
        print("[CHECK] sin cambios en disco. Lanza --apply.")
        return
    for rel, t in new.items():
        p = ROOT / rel
        tmp = p.with_name(p.name + ".tmp")
        tmp.write_text(t)
        tmp.replace(p)
        print(f"[APPLY] {rel}")
    print("[OK] aplicado. Siguiente: make pipeline-build PROFILE=production (en el Mac).")


if __name__ == "__main__":
    main()
