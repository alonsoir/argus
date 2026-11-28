#!/usr/bin/env bash
# scripts/terceros/semgrep_instalar.sh — [SEMGREP-D340] DEBT-LAB-TERCEROS-DESCARGA-SIN-VERIFICAR-001, lente pip D:
# instala, como root en el defender, semgrep en un venv propio (SG_VENV), desde provisioning/semgrep/requirements.txt, con
# --require-hashes --no-deps --only-binary=:all:, y comprueba después pip check, que pip freeze es exactamente el lock y
# que semgrep --version es la del lock. Si ya lo es, no baja nada. Sale con 1 si algo no cuadra.
# Antes (hasta DAY339): la provisión base del Vagrantfile hacía `pip3 install semgrep --break-system-packages` en el
# Python del sistema, sin versión ni hashes, en cada VM nueva: 57 paquetes de pip en /usr/local (medido DAY340), entre
# ellos urllib3 2.8.0, que tapaba al python3-urllib3 de apt que usa python3-requests, y protobuf 6.33.6, que no está en
# apt. Solo lo usa make audit (contrib/audit/audit.mk). Lo llama make audit-semgrep (opcional).
# Las funciones sg_* no tocan el sistema (las prueba scripts/terceros/test_semgrep_instalar.sh en el Mac).
set -u
LC_ALL=C; export LC_ALL
SG_LOCK=${SG_LOCK:-$(dirname "$0")/../../provisioning/semgrep/requirements.txt}
SG_VENV=${SG_VENV:-/opt/argus/semgrep}

# 0 si el lock tiene al menos una línea y todas (salvo comentarios y vacías) son <nombre>==<versión>
# --hash=sha256:<64 hex>, sin nombres repetidos (comparados como los compara pip: minúsculas, _ y . como -)
sg_lock_valido() {
  local f=$1
  [ -f "$f" ] || { echo "[SEMGREP] falta el lock: $f" >&2; return 1; }
  awk '
    /^[[:space:]]*(#|$)/ { next }
    {
      n++
      if (NF != 2 || $1 !~ /^[A-Za-z0-9][A-Za-z0-9._-]*==[A-Za-z0-9][A-Za-z0-9.+!_-]*$/ ||
          $2 !~ /^--hash=sha256:[0-9a-f]+$/ || length($2) != 78) {
        print "[SEMGREP] línea " NR " mal formada: " $0 > "/dev/stderr"; mal = 1; next
      }
      split($1, p, "=="); k = tolower(p[1]); gsub(/[_.]/, "-", k)
      if (k in visto) { print "[SEMGREP] paquete repetido: " k > "/dev/stderr"; mal = 1 }
      visto[k] = 1
    }
    END { if (n == 0) { print "[SEMGREP] lock sin paquetes" > "/dev/stderr"; mal = 1 }; exit mal }' "$f"
}

# <nombre>==<versión> de cada línea (lock o salida de pip freeze), normalizado como pip y ordenado
sg_normaliza() {
  awk '
    /^[[:space:]]*(#|$)/ { next }
    { split($1, p, "=="); k = tolower(p[1]); gsub(/[_.]/, "-", k); print k "==" p[2] }' "$1" | sort
}

# la versión de semgrep del lock (vacía si no está)
sg_version_lock() {
  sg_normaliza "$1" | awk -F'==' '$1 == "semgrep" { print $2 }'
}

# 0 si el fichero de pip freeze tiene exactamente los paquetes y versiones del lock; si no, dice la diferencia
sg_freeze_igual() {
  local lock=$1 freeze=$2
  [ -f "$freeze" ] || return 1
  diff <(sg_normaliza "$lock") <(sg_normaliza "$freeze") >&2
}

# 0 si el fichero (un Vagrantfile) no tiene, fuera de comentarios, ninguna línea que instale con pip un paquete del lock:
# semgrep no vuelve a la provisión base
sg_sin_pip() {
  local f=$1 lock=$2 k sin_comentarios
  [ -f "$f" ] && [ -f "$lock" ] || return 1
  sin_comentarios=$(grep -v '^[[:space:]]*#' "$f")
  for k in $(sg_normaliza "$lock" | sed 's/==.*//'); do
    if printf '%s\n' "$sin_comentarios" | grep -E "pip3?[[:space:]]+install" |
        grep -q -i -E "(^|[[:space:]])${k}([[:space:]=<>]|$)"; then
      return 1
    fi
  done
  return 0
}

# 0 si la primera línea de la salida de semgrep --version (fichero) es exactamente la versión dada
sg_version_igual() {
  local salida=$1 v=$2
  [ -f "$salida" ] && [ -n "$v" ] || return 1
  [ "$(sed -n '1p' "$salida")" = "$v" ]
}

SG_TMP=
main() {
  local v
  [ "$(id -u)" = 0 ] || { echo "[SEMGREP] ❌ hay que correrlo como root"; return 1; }
  sg_lock_valido "$SG_LOCK" || { echo "[SEMGREP] ❌ lock mal formado: $SG_LOCK"; return 1; }
  v=$(sg_version_lock "$SG_LOCK")
  [ -n "$v" ] || { echo "[SEMGREP] ❌ el lock no tiene semgrep: $SG_LOCK"; return 1; }
  SG_TMP=$(mktemp) || return 1
  trap 'rm -f "$SG_TMP"' EXIT
  if [ ! -x "$SG_VENV/bin/python3" ]; then
    python3 -m venv "$SG_VENV" || { echo "[SEMGREP] ❌ python3 -m venv $SG_VENV (¿python3-venv?)"; return 1; }
  fi
  "$SG_VENV/bin/pip" freeze > "$SG_TMP" 2>/dev/null
  if sg_freeze_igual "$SG_LOCK" "$SG_TMP" 2>/dev/null; then
    echo "[SEMGREP] ✅ $SG_VENV ya tiene exactamente el lock; no se baja nada"
  else
    "$SG_VENV/bin/pip" install --require-hashes --no-deps --only-binary=:all: --timeout=300 -r "$SG_LOCK" ||
      { echo "[SEMGREP] ❌ pip install con --require-hashes"; return 1; }
    "$SG_VENV/bin/pip" check || { echo "[SEMGREP] ❌ pip check"; return 1; }
    "$SG_VENV/bin/pip" freeze > "$SG_TMP"
    sg_freeze_igual "$SG_LOCK" "$SG_TMP" ||
      { echo "[SEMGREP] ❌ $SG_VENV no es exactamente el lock (si sobra algo: rm -rf $SG_VENV y repetir)"; return 1; }
  fi
  SEMGREP_ENABLE_VERSION_CHECK=0 "$SG_VENV/bin/semgrep" --version > "$SG_TMP" 2>/dev/null
  sg_version_igual "$SG_TMP" "$v" ||
    { echo "[SEMGREP] ❌ $SG_VENV/bin/semgrep --version no es $v: $(sed -n '1p' "$SG_TMP")"; return 1; }
  echo "[SEMGREP] ✅ $SG_VENV: semgrep $v y su cierre ($(sg_normaliza "$SG_LOCK" | wc -l | tr -d ' ') paquetes del lock)"
  echo "[SEMGREP]    uso: $SG_VENV/bin/semgrep (make audit)"
}

if [ "${BASH_SOURCE[0]}" = "$0" ]; then main "$@"; exit $?; fi
