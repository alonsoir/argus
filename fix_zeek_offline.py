#!/usr/bin/env python3
"""
fix_zeek_offline.py — aRGus NDR DAY 147
Cambia los tres replay targets de Zeek de live capture (-i eth2)
a modo offline (-r pcap).

Modo offline: zeek lee el pcap directamente, sin tcpreplay ni cliente VM.
  - 100% paquetes analizados (sin perdida virtio)
  - Determinístico y reproducible
  - Modo estandar en investigacion con pcaps historicos

La comparacion con Suricata sigue siendo justa: ambos evaluan
el mismo corpus CTU-13 Neris completo.

Uso:
    python3 fix_zeek_offline.py [--makefile PATH] [--dry-run]
"""

import argparse
import shutil
import sys
from pathlib import Path
from datetime import datetime

CTU13_NERIS_VM = "/vagrant/datasets/ctu13/botnet-capture-20110810-neris.pcap"

# Patron comun en los tres targets — lo que hay que cambiar es el bloque
# de arranque de zeek + el bloque de tcpreplay del cliente.
# Estrategia: reemplazar la linea clave de cada target.

# Bug anterior (live):
OLD_LIVE = "nohup sudo /opt/zeek/bin/zeek -i eth2 local > zeek-stdout.log 2>&1 & \\"
# Fix (offline): zeek lee el pcap directamente (sincrono, sin &)
NEW_OFFLINE = f"sudo /opt/zeek/bin/zeek -r {CTU13_NERIS_VM} local > zeek-stdout.log 2>&1 && \\"

# sleep 5 && espera PID — ya no necesario en modo offline (sincrono)
OLD_SLEEP_PID = (
    "  sleep 5 && \\\n"
    "  echo 'Zeek started, PID:' \\$$(pgrep zeek)\""
)
NEW_DONE_MSG = (
    "  echo 'Zeek offline analysis complete'\""
)

# El bloque de tcpreplay del cliente — ya no necesario en modo offline.
# Lo marcamos con un comentario descriptivo en su lugar.
# Estrategia mas segura: solo cambiar la linea de zeek y el sleep/PID.
# El bloque de tcpreplay puede quedar comentado o simplemente no ejecutarse
# porque zeek ya habra terminado antes de que llegue (en modo sincrono).
# Lo mas limpio: eliminamos el bloque de tcpreplay y el drain sleep.

# Patron del bloque cliente en los tres targets:
def old_client_block(speed: str) -> str:
    mbps = speed.replace("mbps", "")
    return (
        f"\t@cd $(ZEEK_DIR) && vagrant ssh client -c \"\\\n"
        f"\t  sudo tcpreplay -i eth1 --mbps={mbps} --stats=1 $(CTU13_NERIS) \\\n"
        f"\t    > /vagrant/logs/experiment/zeek/tcpreplay-zeek-{speed}.log 2>&1; \\\n"
        f"\t  echo \\\"exit=\\$$?\\\" >> /vagrant/logs/experiment/zeek/tcpreplay-zeek-{speed}.log\" || true\n"
        f"\t@cd $(ZEEK_DIR) && vagrant ssh client -c \\\n"
        f"\t  \"grep -E 'Test complete|Actual:|Successful packets|Failed packets|exit=' \\\n"
        f"\t   /vagrant/logs/experiment/zeek/tcpreplay-zeek-{speed}.log 2>/dev/null | tail -6\" || true\n"
        f"\t@echo \"Esperando drain Zeek (15s)...\"\n"
        f"\t@sleep 15"
    )


def new_client_block(speed: str) -> str:
    return f"\t@echo \"  [offline mode] no tcpreplay needed for {speed} — zeek reads pcap directly\""


def main():
    parser = argparse.ArgumentParser(
        description="Convierte targets Zeek de live capture a modo offline (-r pcap)"
    )
    parser.add_argument("--makefile", default="Makefile")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    makefile = Path(args.makefile)
    if not makefile.exists():
        print(f"No se encuentra: {makefile}")
        sys.exit(1)

    content = makefile.read_text(encoding="utf-8")

    print(f"Makefile: {makefile.resolve()}")

    # ── Cambio 1: linea zeek live → offline (3 ocurrencias) ──────────────────
    n1 = content.count(OLD_LIVE)
    print(f"  Cambio 1 (live→offline zeek cmd) : {n1} ocurrencias (esperadas: 3)")

    # ── Cambio 2: sleep 5 + PID → done msg (3 ocurrencias) ───────────────────
    n2 = content.count(OLD_SLEEP_PID)
    print(f"  Cambio 2 (sleep5+PID → done msg) : {n2} ocurrencias (esperadas: 3)")

    # ── Cambio 3: bloques tcpreplay cliente (1 por speed) ─────────────────────
    speeds = ["10mbps", "50mbps", "100mbps"]
    client_changes = []
    for speed in speeds:
        old = old_client_block(speed)
        if old in content:
            client_changes.append(speed)
    print(f"  Cambio 3 (eliminar tcpreplay)    : {len(client_changes)}/3 bloques encontrados")

    if args.dry_run:
        print("\nDRY-RUN — sin cambios en disco.")
        return

    if n1 == 0 and n2 == 0 and not client_changes:
        print("\nNada que parchear — puede que ya este en modo offline.")
        return

    # Backup
    ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = makefile.with_suffix(f".bak_{ts}")
    shutil.copy2(makefile, bak)
    print(f"\nBackup: {bak.name}")

    new_content = content

    # Cambio 1
    new_content = new_content.replace(OLD_LIVE, NEW_OFFLINE)
    print(f"Cambio 1 aplicado: {new_content.count(NEW_OFFLINE)} ocurrencias")

    # Cambio 2
    new_content = new_content.replace(OLD_SLEEP_PID, NEW_DONE_MSG)
    print(f"Cambio 2 aplicado")

    # Cambio 3: bloques tcpreplay
    for speed in speeds:
        old = old_client_block(speed)
        new = new_client_block(speed)
        new_content = new_content.replace(old, new, 1)
    print(f"Cambio 3 aplicado: {len(client_changes)} bloques cliente eliminados")

    makefile.write_text(new_content, encoding="utf-8")

    # Verificacion
    final = makefile.read_text(encoding="utf-8")
    ok = (
            NEW_OFFLINE in final
            and OLD_LIVE not in final
            and CTU13_NERIS_VM in final
    )
    if ok:
        print("\nParche verificado. Siguiente:")
        print("  make experiment-zeek-run")
    else:
        print("\nVerificacion parcial — revisa el Makefile manualmente.")


if __name__ == "__main__":
    main()