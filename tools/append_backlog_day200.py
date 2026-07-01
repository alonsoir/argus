#!/usr/bin/env python3
"""
append_backlog_day200.py — DAY 200 TAREA 1

Método (lección DEDUP, DAY 158, no negociable):
- Fuente canónica de cada deuda decidida ANTES de escribir (este script no inventa
  contenido; consume backlog-additions-day200.md ya redactado contra ADR-058 + PLAN).
- Una sola pasada.
- Append-only: aborta si CUALQUIER nombre DEBT-... del fichero de entrada ya existe
  como cabecera '### DEBT-...' en BACKLOG.md.
- Gate de cierre tras el append: grep -E '^### DEBT|^## ' docs/BACKLOG.md | sort | uniq -d
  debe devolver vacío (cero duplicados de sección).
- NO cat >> a mano.

Uso (desde el HOST, nunca vagrant ssh -c para editar ficheros de macOS):
  python3 tools/append_backlog_day200.py \
      --backlog docs/BACKLOG.md \
      --additions docs/debt/backlog-additions-day200.md
"""
import argparse
import re
import sys

DEBT_HEADER_RE = re.compile(r'^### (DEBT-[A-Z0-9-]+)', re.MULTILINE)
SECTION_HEADER_RE = re.compile(r'^(### DEBT-[A-Z0-9-]+|## .+)$', re.MULTILINE)


def read(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def write(path: str, content: str) -> None:
    # heredoc-safe: leer todo primero, escribir después, nunca open(p,'w') + read()
    # en la misma expresión (esa trampa trunca a 0 bytes — lección DAY196-199).
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def existing_debt_ids(backlog_text: str) -> set:
    return set(DEBT_HEADER_RE.findall(backlog_text))


def new_debt_ids(additions_text: str) -> list:
    # Preserva orden de aparición para mensajes de error deterministas.
    seen = []
    for m in DEBT_HEADER_RE.finditer(additions_text):
        if m.group(1) not in seen:
            seen.append(m.group(1))
    return seen


def duplicate_sections(text: str) -> list:
    headers = SECTION_HEADER_RE.findall(text)
    seen, dups = set(), []
    for h in headers:
        if h in seen:
            dups.append(h)
        seen.add(h)
    return dups


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--backlog", required=True)
    ap.add_argument("--additions", required=True)
    ap.add_argument("--dry-run", action="store_true",
                    help="Solo valida y reporta, no escribe.")
    args = ap.parse_args()

    backlog_text = read(args.backlog)
    additions_text = read(args.additions)

    existing = existing_debt_ids(backlog_text)
    incoming = new_debt_ids(additions_text)

    if not incoming:
        print("ABORT: el fichero de adiciones no contiene ninguna cabecera '### DEBT-...'.",
              file=sys.stderr)
        return 1

    collisions = [d for d in incoming if d in existing]
    if collisions:
        print("ABORT: las siguientes deudas YA EXISTEN en BACKLOG.md — "
              "append-only no puede proceder (revisar/renombrar/replace manual):",
              file=sys.stderr)
        for c in collisions:
            print(f"  - {c}", file=sys.stderr)
        return 1

    # Append físico: una sola escritura, contenido ya validado.
    separator = "\n" if backlog_text.endswith("\n") else "\n\n"
    merged = backlog_text + separator + additions_text.rstrip() + "\n"

    # Gate de cierre ANTES de tocar disco: simular el resultado final.
    dups = duplicate_sections(merged)
    if dups:
        print("ABORT: el resultado tendría secciones duplicadas — gate de cierre falla "
              "antes de escribir:", file=sys.stderr)
        for d in sorted(set(dups)):
            print(f"  - {d}", file=sys.stderr)
        return 1

    print(f"OK: {len(incoming)} deudas nuevas, cero colisiones, gate de duplicados limpio.")
    for d in incoming:
        print(f"  + {d}")

    if args.dry_run:
        print("\n--dry-run: no se ha escrito nada.")
        return 0

    write(args.backlog, merged)
    print(f"\nEscrito: {args.backlog}")
    print("Verificar ahora manualmente:")
    print(f"  grep -E '^### DEBT|^## ' {args.backlog} | sort | uniq -d   # debe ser vacío")
    return 0


if __name__ == "__main__":
    sys.exit(main())