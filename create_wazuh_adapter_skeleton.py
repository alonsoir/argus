#!/usr/bin/env python3
"""
create_wazuh_adapter_skeleton.py — aRGus NDR (DAY 242)

Crea, desde la raíz del proyecto, la estructura del componente `wazuh-adapter/`
(Pieza 1 del cierre host) con los 13 ficheros VACÍOS, listos para pegar el
contenido entregado.

SEGURO por diseño: nunca sobrescribe un fichero que YA existe (aunque esté
vacío) — re-ejecutarlo no destruye trabajo ya pegado; solo crea lo que falta.

NO toca nada fuera de `wazuh-adapter/`: ni el Makefile raíz (edición a mano),
ni `libs/host-domain-v1/` (existe de la Pieza 0), ni el CMakeLists raíz.

Uso:
    python3 create_wazuh_adapter_skeleton.py            # crea en el cwd
    python3 create_wazuh_adapter_skeleton.py --root .   # idem, explícito
    python3 create_wazuh_adapter_skeleton.py --dry-run  # enseña, no toca disco
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Los 13 ficheros del componente, relativos a la raíz del proyecto.
FILES = [
    "wazuh-adapter/.gitignore",
    "wazuh-adapter/CMakeLists.txt",
    "wazuh-adapter/README.md",
    "wazuh-adapter/config/wazuh_adapter.json",
    "wazuh-adapter/include/wazuh_adapter/batch_writer.hpp",
    "wazuh-adapter/include/wazuh_adapter/config.hpp",
    "wazuh-adapter/include/wazuh_adapter/to_row.hpp",
    "wazuh-adapter/src/batch_writer.cpp",
    "wazuh-adapter/src/config.cpp",
    "wazuh-adapter/src/main.cpp",
    "wazuh-adapter/src/to_row.cpp",
    "wazuh-adapter/tests/CMakeLists.txt",
    "wazuh-adapter/tests/test_to_row.cpp",
]


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Crea el esqueleto VACÍO de wazuh-adapter/ (Pieza 1, DAY 242)."
    )
    ap.add_argument("--root", default=".",
                    help="Raíz del proyecto donde crear wazuh-adapter/ (por defecto: cwd).")
    ap.add_argument("--dry-run", action="store_true",
                    help="Enseña lo que haría, sin tocar el disco.")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"ERROR: la raíz no existe o no es un directorio: {root}", file=sys.stderr)
        return 2

    created, skipped = 0, 0
    for rel in FILES:
        path = root / rel
        if path.exists():
            print(f"  skip   (ya existe)  {rel}")
            skipped += 1
            continue
        if args.dry_run:
            print(f"  CREARÍA             {rel}")
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()  # fichero VACÍO
        print(f"  creado              {rel}")
        created += 1

    print()
    if args.dry_run:
        print("(dry-run: no se tocó el disco)")
    else:
        print(f"Hecho: {created} creados, {skipped} ya existían.  Raíz: {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())