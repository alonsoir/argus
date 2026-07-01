#!/usr/bin/env bash
# canonize-adr.sh — normaliza nombres de ADR a ADR-NNN[-vX]-slug.md
#
# DISEÑO: el origen sale del glob del filesystem (byte-exacto, inmune a problemas de
# codificación Unicode al teclear nombres). El slug se deriva con Python/unicodedata,
# que translitera acentos y maneja UTF-8 correctamente (sed y/// falla con multibyte).
#
# INVARIANTES:
#   - TODO es `git mv` -> preserva historia.
#   - NADA se borra. Versiones conservadas con -vN (registro Test Driven Hardening).
#   - NO toca ADR-058 (no está en docs/adr/ de esta rama; va en day196).
#   - NO toca ficheros ya canónicos.
#
# USO (en el guest):
#   vagrant ssh -c 'cd /vagrant && bash scripts/canonize-adr.sh --dry-run'
#   vagrant ssh -c 'cd /vagrant && bash scripts/canonize-adr.sh'

set -euo pipefail
cd /vagrant

DRY=0
case "${1:-}" in
  --dry-run|-n) DRY=1 ;;
  "") DRY=0 ;;
  *) echo "uso: $0 [--dry-run|-n]"; exit 2 ;;
esac

ERRORS=0; PLANNED=0; SKIPPED=0

slugify() {
  python3 - "$1" << 'PY'
import sys, unicodedata, re
s = sys.argv[1]
# separadores semánticos -> guion ANTES de strip (para no perder host<->net)
s = re.sub(r'[↔→←·&/]', '-', s)
s = unicodedata.normalize('NFKD', s)
s = ''.join(c for c in s if not unicodedata.combining(c))  # quita acentos
s = s.encode('ascii', 'ignore').decode('ascii')            # quita no-ASCII restante
s = s.lower()
s = re.sub(r'[^a-z0-9]+', '-', s)
s = re.sub(r'-+', '-', s).strip('-')
print(s)
PY
}

is_canonical() { [[ "$1" =~ ^ADR-[0-9]{3}(-v[0-9]+(\.[0-9]+)?(-final)?)?-[a-z0-9-]+\.md$ ]]; }

echo "$([[ $DRY -eq 1 ]] && echo '=== DRY-RUN — no ejecuta ===' || echo '=== EJECUTANDO ===') rama: $(git branch --show-current)"
echo

shopt -s nullglob
for src in docs/adr/ADR-*.md; do
  base="$(basename "$src")"
  if is_canonical "$base"; then SKIPPED=$((SKIPPED+1)); continue; fi

  num="$(echo "$base" | sed -E 's/^ADR-0*([0-9]+).*/\1/')"
  printf -v num3 '%03d' "$num"

  ver=""
  if [[ "$base" =~ [._\ ][Vv]([0-9]+(\.[0-9]+)?)([-_]?[Ff][Ii][Nn][Aa][Ll])? ]]; then
    vraw="${BASH_REMATCH[1]}"
    [[ "$base" =~ [Ff][Ii][Nn][Aa][Ll] ]] && ver="-v${vraw}-final" || ver="-v${vraw}"
  fi

  body="$(echo "$base" \
    | sed -E 's/\.md$//' \
    | sed -E 's/^ADR-0*[0-9]+//' \
    | sed -E 's/[._ ][Vv][0-9]+(\.[0-9]+)?([-_]?[Ff][Ii][Nn][Aa][Ll])?//')"
  slug="$(slugify "$body")"

  if [[ -z "$slug" ]]; then
    echo "  ✗ SLUG VACÍO desde: $base (revisar a mano)"; ERRORS=$((ERRORS+1)); continue
  fi

  dst="docs/adr/ADR-${num3}${ver}-${slug}.md"
  PLANNED=$((PLANNED+1))

  if [[ -e "$dst" && "$dst" != "$src" ]]; then
    echo "  ✗ COLISIÓN: $(basename "$dst")  (desde $base)"; ERRORS=$((ERRORS+1)); continue
  fi

  if [[ "$DRY" -eq 1 ]]; then
    echo "  → $base"
    echo "      ⇒ $(basename "$dst")"
  else
    git mv "$src" "$dst"
    echo "  ✓ $(basename "$dst")"
  fi
done

echo
echo "===== RESUMEN ====="
echo "ya canónicos (saltados): $SKIPPED"
echo "a renombrar:             $PLANNED"
echo "errores:                 $ERRORS"
[[ "$ERRORS" -gt 0 ]] && { echo "✗ corrige antes de ejecutar"; exit 1; }
[[ "$DRY" -eq 1 ]] && echo "✓ dry-run limpio; ejecuta sin --dry-run" || echo "✓ aplicado; revisa git status"