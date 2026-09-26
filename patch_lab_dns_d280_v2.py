#!/usr/bin/env python3
"""DAY280 v2 — corrige LAB-DNS-D280 en el client.
El bloque 'lab-dns-load' no puede instalar nada: cuando corre, client-setup ya cambió
la ruta por defecto a 192.168.100.1 y el client no tiene salida a internet
(MEDIDO: 'Temporary failure resolving deb.debian.org').
Cambios: (1) quita el bloque lab-dns-load; (2) añade dnsperf a la lista de apt-get
de client-setup, que corre ANTES del cambio de ruta.
Idempotente, atómico. Uso: python3 patch_lab_dns_d280_v2.py [--check] [Vagrantfile]. No hace commit."""
import sys, re, pathlib

BLOCK_RE = re.compile(r"\n    # LAB-DNS-D280 — generador de carga DNS legítima.*?\n    LAB_DNS_LOAD\n", re.S)
APT_OLD = "          iputils-ping procps chrony \\\n"
APT_NEW = "          iputils-ping procps chrony dnsperf \\\n"
NOTE_ANCHOR = "          apt-get install -y --no-install-recommends \\\n          curl wget iproute2"
NOTE = ("          # LAB-DNS-D280: dnsperf (carga DNS benigna) va AQUÍ y no en un bloque aparte:\n"
        "          # este apt corre antes del cambio de ruta a 192.168.100.1, que deja al client sin internet.\n")

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    check = "--check" in sys.argv
    path = pathlib.Path(args[0] if args else "Vagrantfile")
    src = path.read_text()
    has_block = len(BLOCK_RE.findall(src))
    has_new = src.count(APT_NEW)
    if has_block == 0 and has_new == 1:
        print(f"✅ v2 ya aplicado en {path}; nada que hacer"); return 0
    errs = []
    if has_block != 1: errs.append(f"bloque lab-dns-load encontrado {has_block} veces (se esperaba 1)")
    if src.count(APT_OLD) != 1: errs.append(f"línea apt de client-setup encontrada {src.count(APT_OLD)} veces (se esperaba 1)")
    if src.count(NOTE_ANCHOR) != 1: errs.append(f"ancla apt-get install de client-setup encontrada {src.count(NOTE_ANCHOR)} veces")
    if errs:
        for e in errs: print("❌ " + e)
        print("   NO se ha escrito nada."); return 2
    out = BLOCK_RE.sub("\n", src, count=1)
    out = out.replace("\n        CLIENT\n\n\n  end  # End client VM", "\n        CLIENT\n\n  end  # End client VM", 1)
    out = out.replace(APT_OLD, APT_NEW, 1)
    out = out.replace(NOTE_ANCHOR, NOTE + NOTE_ANCHOR, 1)
    delta = out.count("\n") - src.count("\n")
    if check:
        print(f"🔎 --check: aplicaría v2 ({delta:+d} líneas) a {path}"); return 0
    path.write_text(out)
    print(f"✅ v2 aplicado a {path} ({delta:+d} líneas). Siguiente: 'vagrant validate' en el Mac")
    return 0

if __name__ == "__main__":
    sys.exit(main())
