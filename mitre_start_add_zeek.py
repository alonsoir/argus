#!/usr/bin/env python3
"""
mitre_start_add_zeek.py — DAY 237 (v2)
Inserta el tramo Zeek en scripts/mitre_start.sh, espejando la mitad Suricata
+ el ciclo de vida de zeekctl alrededor de la ventana nmap.

CAMBIO v1 -> v2 (fix medido DAY 237):
  El conn.log VIVO vive en /opt/zeek/spool/zeek/ SOLO mientras zeek corre; el
  'zeekctl stop' lo archiva fuera del spool (gzip+fechado). Por eso ahora se
  COSECHA del spool ANTES del stop (mientras zeek sigue vivo), no despues.
  Orden nuevo:  deploy -> nmap -> sleep 45 -> cp del spool -> stop.

Diseño (invariantes del proyecto):
  - ANCLADO: localiza lineas EXACTAS del fichero. Anclaje que no aparece
    exactamente una vez -> ABORTA sin tocar nada.
  - ALL-OR-NOTHING: valida los 5 anclajes ANTES de aplicar nada.
  - IDEMPOTENTE: si ya esta cableado ('zeekctl deploy'), no hace nada.
  - REVERSIBLE: backup <fichero>.bak-<STAMP> antes de sobrescribir.

IMPORTANTE: v2 se aplica sobre el mitre_start.sh ORIGINAL. Si aplicaste el v1,
restaura primero:  git checkout scripts/mitre_start.sh   (o usa tu .bak-*).

Uso:
    python3 mitre_start_add_zeek.py                       # scripts/mitre_start.sh
    python3 mitre_start_add_zeek.py ruta/a/mitre_start.sh
    python3 mitre_start_add_zeek.py --dry-run             # muestra, no escribe
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

DEFAULT_TARGET = "scripts/mitre_start.sh"

# --- Bloques a insertar -------------------------------------------------------
# Son lineas de SHELL. Los '\"' son escapes que necesita el shell dentro de
# vagrant ssh -c "...". En Python los escribimos como '\\"'.

VAR_BLOCK = (
    'ZEEKCTL="/opt/zeek/bin/zeekctl"\n'
    '# <CONFIRMAR> nombre/ruta del binario del adapter (espejo de suricata_adapter):\n'
    'ZEEK_ADAPTER="/vagrant/zeek-adapter/build-zeek/zeek_adapter"\n'
    'ZEEK_SPOOL="/opt/zeek/spool/zeek"   # conn.log vivo (confirmado DAY 237)\n'
)

DEPLOY_BLOCK = (
    '# --- Zeek vivo: deploy ANTES del nmap (conn.log nace ~T0, windowing por construccion) ---\n'
    'vagrant ssh zeek -c "sudo $ZEEKCTL deploy" || die "zeekctl deploy fallo"\n'
)

# Cosecha + stop: va DESPUES del drenaje. cp del spool MIENTRAS zeek corre
# (el stop archiva el conn.log fuera del spool), luego stop.
HARVEST_STOP_BLOCK = (
    '# --- Zeek: cosechar conn.log del spool MIENTRAS corre, antes del stop (que lo archiva) ---\n'
    'vagrant ssh zeek -c "sudo cp $ZEEK_SPOOL/conn.log $LAB/zeek-$STAMP.conn.log && sudo chmod 644 $LAB/zeek-$STAMP.conn.log" || die "no hay conn.log en el spool (zeek no vio trafico en la ventana?)"\n'
    'vagrant ssh zeek -c "sudo $ZEEKCTL stop"\n'
)

# 4b) Oro de Zeek — el conn.log YA esta en $LAB (cosechado arriba). Solo
#     adapter (config per-run, base_dir=$LAB, toy key inline) -> converter.
GOLD_BLOCK = (
    '\n'
    '# 4b) Oro de Zeek: conn.log de la ventana (ya cosechado) -> adapter (toy key inline) -> converter\n'
    'vagrant ssh zeek -c "python3 -c \\"import json; json.dump({\'base_dir\':\'$LAB\',\'node_id\':\'cpp_sniffer_v33_day12\',\'input_path\':\'logs/lab/zeek-$STAMP.conn.log\',\'hmac_key_env\':\'ARGUS_BRONZE_HMAC_KEY_HEX\'}, open(\'$LAB/zeek-adapter-$STAMP.json\',\'w\'))\\""\n'
    'vagrant ssh zeek -c "cd /vagrant && ARGUS_BRONZE_HMAC_KEY_HEX=$TOY_KEY $ZEEK_ADAPTER $LAB/zeek-adapter-$STAMP.json"\n'
    'ZEEK_CSV=$(vagrant ssh zeek -c "ls -t $LAB/zeek-*.csv | head -1" 2>/dev/null | tr -d \'\\r\')\n'
    'vagrant ssh defender -c "cd $CE && ARGUS_BRONZE_HMAC_KEY_HEX=$TOY_KEY ./bronze_to_gold_converter $ZEEK_CSV $LAB/zeek-$STAMP.avro $LAB/zeek-$STAMP.parquet"\n'
)

LOADER_BLOCK = (
    'vagrant ssh defender -c "cd $CE && ./parquet_to_kuzu_loader $LAB/zeek-$STAMP.parquet $KUZU $SCHEMA"\n'
)

# --- Anclajes (linea EXACTA del fichero) y modo -------------------------------
INSERTIONS = [
    {
        "name": "variables (ZEEKCTL / ZEEK_ADAPTER / ZEEK_SPOOL)",
        "anchor": 'LAB="/vagrant/logs/lab"; ADAPTER="/vagrant/suricata-adapter/build-suricata/suricata_adapter"',
        "mode": "after",
        "block": VAR_BLOCK,
    },
    {
        "name": "zeekctl deploy (tras el marker T0, antes del nmap)",
        "anchor": 'vagrant ssh defender -c "touch $LAB/mitre-t0-$STAMP.marker"',
        "mode": "after",
        "block": DEPLOY_BLOCK,
    },
    {
        "name": "cosecha del spool + zeekctl stop (tras el drenaje)",
        "anchor": 'echo "-- Drenaje 45s --"; sleep 45',
        "mode": "after",
        "block": HARVEST_STOP_BLOCK,
    },
    {
        "name": "oro de Zeek (paso 4b, antes del paso 5)",
        "anchor": "# 5) Kuzu fresca + carga de los dos oros + poblador CORRELATES_FLOW",
        "mode": "before",
        "block": GOLD_BLOCK,
    },
    {
        "name": "3a carga en Kuzu (tras el loader de Suricata)",
        "anchor": 'vagrant ssh defender -c "cd $CE && ./parquet_to_kuzu_loader $LAB/suricata-$STAMP.parquet $KUZU $SCHEMA"',
        "mode": "after",
        "block": LOADER_BLOCK,
    },
]

ALREADY_WIRED_MARKER = "zeekctl deploy"


def fail(msg: str) -> "NoReturn":
    print(f"\n  X  {msg}\n", file=sys.stderr)
    sys.exit(1)


def main() -> int:
    args = [a for a in sys.argv[1:]]
    dry_run = "--dry-run" in args
    args = [a for a in args if a != "--dry-run"]
    target = Path(args[0]) if args else Path(DEFAULT_TARGET)

    if not target.is_file():
        fail(f"no encuentro el fichero: {target}  (lo corres desde la raiz del repo?)")

    text = target.read_text(encoding="utf-8")

    if ALREADY_WIRED_MARKER in text:
        print(f"  ~  '{target}' ya parece cableado (encontrado '{ALREADY_WIRED_MARKER}').")
        print("     Si venias del v1, restaura primero: git checkout scripts/mitre_start.sh")
        return 0

    # Validacion all-or-nothing: cada anclaje EXACTAMENTE una vez.
    for ins in INSERTIONS:
        n = text.count(ins["anchor"])
        if n != 1:
            fail(
                f"anclaje '{ins['name']}' aparece {n} veces (esperaba 1).\n"
                f"     Ancla buscada:\n       {ins['anchor']}\n"
                f"     El fichero no es el esperado. Abortado sin tocar nada."
            )

    new_text = text
    for ins in INSERTIONS:
        anchor, block = ins["anchor"], ins["block"]
        if ins["mode"] == "after":
            new_text = new_text.replace(anchor + "\n", anchor + "\n" + block.rstrip("\n") + "\n", 1)
        else:  # before
            new_text = new_text.replace(anchor, block.rstrip("\n") + "\n" + anchor, 1)

    if new_text == text:
        fail("no se aplico ningun cambio (inesperado tras validar). Abortado.")

    if dry_run:
        print("=== DRY-RUN — no se escribe. Bloques que se insertarian: ===\n")
        for ins in INSERTIONS:
            print(f"--- {ins['name']} ({ins['mode']}) ---")
            print(ins["block"].rstrip("\n"))
            print()
        print(f"(el fichero real '{target}' NO se toca en --dry-run)")
        return 0

    stamp = time.strftime("%Y%m%d-%H%M%S")
    backup = target.with_suffix(target.suffix + f".bak-{stamp}")
    backup.write_text(text, encoding="utf-8")
    target.write_text(new_text, encoding="utf-8")

    print(f"  OK  '{target}' modificado (v2). Backup en '{backup}'.")
    print("      5 bloques: variables, deploy, cosecha+stop, oro 4b, 3a carga Kuzu.\n")
    print("  Orden del tramo Zeek: deploy -> nmap -> drenaje -> cp del spool -> stop -> adapter -> converter -> loader.\n")
    print("  ANTES DE CORRER mitre-start:")
    print("   - [GATE visibilidad] PASADO DAY 237 (grep -c 192.168.100.50 conn.log = 10).")
    print("   - ZEEK_SPOOL confirmado (/opt/zeek/spool/zeek).")
    print("   - <CONFIRMAR> ZEEK_ADAPTER: binario/CLI en /vagrant/zeek-adapter/build-zeek.")
    print("\n  Verifica la sintaxis:  bash -n " + str(target))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())