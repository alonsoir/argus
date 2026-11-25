#!/usr/bin/env bash
# scripts/terceros/ml_entreno_instalar.sh — [ML-ENTRENO-D337] DEBT-LAB-TERCEROS-DESCARGA-SIN-VERIFICAR-001, lente pip B:
# instala, como root en el defender, el entorno de entrenamiento de las cabezas ML en un venv propio (ME_VENV), desde
# provisioning/ml-entreno/requirements.txt, con --require-hashes --no-deps --only-binary=:all:, y comprueba después
# pip check y que pip freeze es exactamente el lock. Si ya lo es, no baja nada. Sale con 1 si algo no cuadra.
# Antes (hasta DAY336): la provisión base instalaba ml-training/requirements-ddos-pinned.txt con pip en el Python del
# sistema, sin hashes y sin narwhals fijado, en cada VM nueva, aunque nada del pipeline ni del EMECAS lo usaba (medido
# DAY337). Lo llama make ml-entreno (opcional). Uso del entorno: $ME_VENV/bin/python3 <script>.
# Las funciones me_* no tocan el sistema (las prueba scripts/terceros/test_ml_entreno.sh en el Mac).
set -u
LC_ALL=C; export LC_ALL
ME_LOCK=${ME_LOCK:-$(dirname "$0")/../../provisioning/ml-entreno/requirements.txt}
ME_VENV=${ME_VENV:-/opt/argus/ml-entreno}

# 0 si el lock tiene al menos una línea y todas (salvo comentarios y vacías) son <nombre>==<versión>
# --hash=sha256:<64 hex>, sin nombres repetidos (comparados como los compara pip: minúsculas, _ y . como -)
me_lock_valido() {
  local f=$1
  [ -f "$f" ] || { echo "[ML-ENTRENO] falta el lock: $f" >&2; return 1; }
  awk '
    /^[[:space:]]*(#|$)/ { next }
    {
      n++
      if (NF != 2 || $1 !~ /^[A-Za-z0-9][A-Za-z0-9._-]*==[A-Za-z0-9][A-Za-z0-9.+!_-]*$/ ||
          $2 !~ /^--hash=sha256:[0-9a-f]+$/ || length($2) != 78) {
        print "[ML-ENTRENO] línea " NR " mal formada: " $0 > "/dev/stderr"; mal = 1; next
      }
      split($1, p, "=="); k = tolower(p[1]); gsub(/[_.]/, "-", k)
      if (k in visto) { print "[ML-ENTRENO] paquete repetido: " k > "/dev/stderr"; mal = 1 }
      visto[k] = 1
    }
    END { if (n == 0) { print "[ML-ENTRENO] lock sin paquetes" > "/dev/stderr"; mal = 1 }; exit mal }' "$f"
}

# <nombre>==<versión> de cada línea (lock o salida de pip freeze), normalizado como pip y ordenado
me_normaliza() {
  awk '
    /^[[:space:]]*(#|$)/ { next }
    { split($1, p, "=="); k = tolower(p[1]); gsub(/[_.]/, "-", k); print k "==" p[2] }' "$1" | sort
}

# 0 si el fichero de pip freeze tiene exactamente los paquetes y versiones del lock; si no, dice la diferencia
me_freeze_igual() {
  local lock=$1 freeze=$2
  [ -f "$freeze" ] || return 1
  diff <(me_normaliza "$lock") <(me_normaliza "$freeze") >&2
}

# 0 si el fichero (un Vagrantfile) no tiene, fuera de comentarios, ninguna mención a requirements-ddos-pinned ni ninguna
# línea que instale con pip un paquete del lock: el entorno de entrenamiento no vuelve a la provisión base
me_sin_pip() {
  local f=$1 lock=$2 k sin_comentarios
  [ -f "$f" ] && [ -f "$lock" ] || return 1
  sin_comentarios=$(grep -v '^[[:space:]]*#' "$f")
  printf '%s\n' "$sin_comentarios" | grep -q 'requirements-ddos-pinned' && return 1
  for k in $(me_normaliza "$lock" | sed 's/==.*//'); do
    if printf '%s\n' "$sin_comentarios" | grep -E "pip3?[[:space:]]+install" |
        grep -q -i -E "(^|[[:space:]])${k}([[:space:]=<>]|$)"; then
      return 1
    fi
  done
  return 0
}

ME_TMP=
main() {
  [ "$(id -u)" = 0 ] || { echo "[ML-ENTRENO] ❌ hay que correrlo como root"; return 1; }
  me_lock_valido "$ME_LOCK" || { echo "[ML-ENTRENO] ❌ lock mal formado: $ME_LOCK"; return 1; }
  ME_TMP=$(mktemp) || return 1
  trap 'rm -f "$ME_TMP"' EXIT
  if [ ! -x "$ME_VENV/bin/python3" ]; then
    python3 -m venv "$ME_VENV" || { echo "[ML-ENTRENO] ❌ python3 -m venv $ME_VENV (¿python3-venv?)"; return 1; }
  fi
  "$ME_VENV/bin/pip" freeze > "$ME_TMP" 2>/dev/null
  if me_freeze_igual "$ME_LOCK" "$ME_TMP" 2>/dev/null; then
    echo "[ML-ENTRENO] ✅ $ME_VENV ya tiene exactamente el lock; no se baja nada"
    return 0
  fi
  "$ME_VENV/bin/pip" install --require-hashes --no-deps --only-binary=:all: --timeout=300 -r "$ME_LOCK" ||
    { echo "[ML-ENTRENO] ❌ pip install con --require-hashes"; return 1; }
  "$ME_VENV/bin/pip" check || { echo "[ML-ENTRENO] ❌ pip check"; return 1; }
  "$ME_VENV/bin/pip" freeze > "$ME_TMP"
  me_freeze_igual "$ME_LOCK" "$ME_TMP" ||
    { echo "[ML-ENTRENO] ❌ $ME_VENV no es exactamente el lock (si sobra algo: rm -rf $ME_VENV y repetir)"; return 1; }
  echo "[ML-ENTRENO] ✅ $ME_VENV: $(me_normaliza "$ME_LOCK" | tr '\n' ' ')"
  echo "[ML-ENTRENO]    uso: $ME_VENV/bin/python3 <script>"
}

if [ "${BASH_SOURCE[0]}" = "$0" ]; then main "$@"; exit $?; fi
