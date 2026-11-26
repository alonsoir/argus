#!/usr/bin/env bash
# scripts/terceros/pyarrow_instalar.sh — [PYARROW-D338] DEBT-LAB-TERCEROS-DESCARGA-SIN-VERIFICAR-001, lente pip C:
# pyarrow, en la versión y con el hash de provisioning/pyarrow/requirements.txt, en el Python del sistema del defender.
#   - sin argumentos (como root, lo llama la provisión del Vagrantfile): si el import ya resuelve a /usr/local con la
#     versión del lock, no baja nada; si no, pip3 install --require-hashes --no-deps --only-binary=:all: y lo comprueba.
#   - --comprobar (como vagrant, lo llama make parquet-convert): solo comprueba, no instala. Una copia en ~/.local (la de
#     antes) taparía a la de /usr/local: sale con 1 y dice cómo quitarla.
# Antes (hasta DAY337): parquet-convert hacía `pip3 install --upgrade pyarrow` como vagrant en cada corrida, sin versión
# ni hash: bajaba la última que hubiera en PyPI a ~vagrant/.local. Medido DAY336-338: pyarrow 26.0.1 no tiene
# dependencias, así que el lock es una sola línea. Las funciones pya_* no tocan el sistema (las prueba
# scripts/terceros/test_pyarrow_instalar.sh en el Mac).
set -u
LC_ALL=C; export LC_ALL
PYA_LOCK=${PYA_LOCK:-$(dirname "$0")/../../provisioning/pyarrow/requirements.txt}

# 0 si el lock tiene exactamente una línea (salvo comentarios y vacías) y es pyarrow==<versión> --hash=sha256:<64 hex>
pya_lock_valido() {
  local f=$1
  [ -f "$f" ] || { echo "[PYARROW] falta el lock: $f" >&2; return 1; }
  awk '
    /^[[:space:]]*(#|$)/ { next }
    {
      n++
      if (NF != 2 || $1 !~ /^pyarrow==[0-9][0-9A-Za-z.+!_-]*$/ || $2 !~ /^--hash=sha256:[0-9a-f]+$/ || length($2) != 78) {
        print "[PYARROW] línea " NR " mal formada: " $0 > "/dev/stderr"; mal = 1
      }
    }
    END {
      if (n != 1) { print "[PYARROW] el lock tiene " n + 0 " líneas de paquete, se esperaba 1 (pyarrow)" > "/dev/stderr"; mal = 1 }
      exit mal
    }' "$f"
}

# la versión fijada en el lock (ya validado)
pya_version_lock() {
  awk '/^[[:space:]]*(#|$)/ { next } { split($1, p, "=="); print p[2]; exit }' "$1"
}

# 0 si la ruta del __file__ de pyarrow está en el dist-packages de /usr/local (la de pip como root en Debian)
pya_origen_local() {
  case "$1" in
    *..*) return 1 ;;
    /usr/local/lib/python3.[0-9]*/dist-packages/pyarrow/__init__.py) return 0 ;;
    *) return 1 ;;
  esac
}

# 0 si "versión ruta" (lo que imprime el import) es la versión del lock desde /usr/local
pya_instalado_ok() {
  local esperada=$1 linea=$2 v f
  v=${linea%% *}; f=${linea#* }
  [ -n "$linea" ] && [ "$v" != "$linea" ] || return 1
  [ "$v" = "$esperada" ] && pya_origen_local "$f"
}

# 0 si el fichero (Makefile o Vagrantfile) no tiene, fuera de comentarios, ninguna línea que instale pyarrow con pip
pya_sin_pip() {
  local f=$1
  [ -f "$f" ] || return 1
  ! grep -v '^[[:space:]]*#' "$f" | grep -E "pip3?[[:space:]]+install" | grep -q -i -E "(^|[[:space:]\"'])pyarrow([[:space:]=<>\"']|$)"
}

pya_import() {
  python3 -c 'import pyarrow, sys; sys.stdout.write(pyarrow.__version__ + " " + pyarrow.__file__)' 2>/dev/null
}

main() {
  local v linea
  pya_lock_valido "$PYA_LOCK" || { echo "[PYARROW] ❌ lock mal formado: $PYA_LOCK"; return 1; }
  v=$(pya_version_lock "$PYA_LOCK")
  linea=$(pya_import)
  if [ "${1:-}" = "--comprobar" ]; then
    if pya_instalado_ok "$v" "$linea"; then
      echo "[PYARROW] ✅ pyarrow ${linea}"; return 0
    fi
    echo "[PYARROW] ❌ se esperaba pyarrow $v de /usr/local/lib/python3.*/dist-packages, el import da: '${linea:-no importa}'"
    case "$linea" in
      *"/.local/"*) echo "[PYARROW]    una copia en ~/.local tapa a la de la provisión: pip3 uninstall -y --break-system-packages pyarrow (como $(id -un))" ;;
    esac
    return 1
  fi
  [ "$(id -u)" = 0 ] || { echo "[PYARROW] ❌ hay que correrlo como root (o con --comprobar)"; return 1; }
  if pya_instalado_ok "$v" "$linea"; then
    echo "[PYARROW] ✅ pyarrow $v ya instalado (${linea#* }); no se baja nada"; return 0
  fi
  pip3 install --require-hashes --no-deps --only-binary=:all: --break-system-packages --timeout=300 -r "$PYA_LOCK" ||
    { echo "[PYARROW] ❌ pip3 install con --require-hashes"; return 1; }
  linea=$(pya_import)
  pya_instalado_ok "$v" "$linea" || { echo "[PYARROW] ❌ tras instalar, el import da: '${linea:-no importa}'"; return 1; }
  echo "[PYARROW] ✅ pyarrow ${linea}"
}

if [ "${BASH_SOURCE[0]}" = "$0" ]; then main "$@"; exit $?; fi
