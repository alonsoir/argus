#!/usr/bin/env bash
# DAY303 [ARGUS-EMECAS-RUN-D303]: lanza EMECAS con el Mac despierto y deja rastro para emecas_watch.sh
#  - log completo en logs/lab/emecas/emecas_<fecha>.log (enlace emecas_actual.log al ultimo)
#  - emecas_actual.pid (este script), emecas_actual.start (epoch de inicio), emecas_actual.rc (al terminar)
#  - caffeinate -dims: ni el Mac ni el disco duermen mientras dure (con tapa cerrada hace falta corriente)
# Uso (Mac, raiz del repo), en segundo plano para que cerrar la terminal no lo mate:
#   nohup bash scripts/emecas/emecas_run.sh emecas+++ production < /dev/null > /dev/null 2>&1 &
set -u
OBJ="${1:-emecas+++}"
PERFIL="${2:-production}"
DIR=logs/lab/emecas
mkdir -p "$DIR"
TS=$(date +%Y%m%d_%H%M%S)
LOG="$DIR/emecas_${TS}.log"
if [[ -f "$DIR/emecas_actual.pid" ]] && kill -0 "$(cat "$DIR/emecas_actual.pid")" 2>/dev/null && [[ ! -f "$DIR/emecas_actual.rc" ]]; then
  echo "[EMECAS-RUN] ya hay una corrida viva (pid $(cat "$DIR/emecas_actual.pid")); no lanzo otra"
  exit 1
fi
rm -f "$DIR/emecas_actual.rc"
echo "$$" > "$DIR/emecas_actual.pid"
date +%s > "$DIR/emecas_actual.start"
ln -sfn "emecas_${TS}.log" "$DIR/emecas_actual.log"
echo "[EMECAS-RUN] inicio $(date '+%F %T') objetivo=${OBJ} PROFILE=${PERFIL} log=${LOG}" > "$LOG"
# DAY303 M1: lanzado en segundo plano desde zsh, vagrant toco la terminal y el job quedo
# "suspended (tty output)" (estado T, sin avanzar). Se corta todo lazo con la terminal:
# stdin de /dev/null y nueva sesion (setsid, via python3: macOS no trae el comando setsid),
# asi no hay terminal de control y SIGTTOU/SIGTTIN no pueden pararlo.
python3 -c 'import os, sys; os.setsid(); os.execvp(sys.argv[1], sys.argv[1:])' \
  caffeinate -dims make "$OBJ" PROFILE="$PERFIL" < /dev/null >> "$LOG" 2>&1
rc=$?
echo "[EMECAS-RUN] fin $(date '+%F %T') rc=${rc}" >> "$LOG"
echo "$rc" > "$DIR/emecas_actual.rc"
exit "$rc"
