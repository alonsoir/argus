#!/usr/bin/env bash
# DAY303 [ARGUS-EMECAS-WATCH-D303]: de un vistazo, si EMECAS avanza, va colgado o ha fallado.
# Solo lee en el Mac (log, ps); no entra en las VMs, para no cargar el equipo ni pelear por vagrant.
#  - fase alcanzada y barra: hitos fijos del log en orden (el mas avanzado que ya aparece)
#  - tiempo transcurrido y minutos desde la ultima linea del log
#  - CPU de las VMs (VBoxHeadless): si el log calla pero hay CPU, esta trabajando, no colgado
#  - el proceso de la corrida vive o no; procesos zombi (estado Z) en el Mac
#  - ultimo error de make (make: ***) y la ultima linea del log
# Uso (Mac, raiz del repo, en otra terminal): bash scripts/emecas/emecas_watch.sh [segundos=30]
# Ctrl-C para salir; no afecta a la corrida.
set -u
INT="${1:-30}"
DIR=logs/lab/emecas
LOG="$DIR/emecas_actual.log"
CALLADO_AVISO=900

# hitos en orden (texto ASCII que aparece en el log; -F, literal)
FASES=(
  "OSS gate (destroy"
  "Destroying VM"
  "[CLEAN-HOST] PASA"
  "Bringing machine 'defender' up"
  "[1/8]"
  "[2/8]"
  "[3/8]"
  "[4/8]"
  "[5/8]"
  "[6/8]"
  "[7/8]"
  "[8/8]"
  "Bootstrap x86 eBPF completado"
  "[FRESCURA] PASA"
  "ALL TESTS COMPLETE"
  "[CTEST-GATE] PASA (e2e)"
  "[CTEST-GATE] PASA (perf)"
  "RESULTADO PASA (reinicio antes)"
  "RESULTADO PASA (reinicio ordenada)"
  "RESULTADO PASA (reinicio kill9)"
  "RESULTADO PASA (protegidos)"
  "PASA los cinco E2E del lab"
  "EMECAS PASSED"
  "Acto I "
  "Acto II "
  "Acto III "
  "EMECAS++ PASSED"
  "EMECAS+++ PASSED"
)
NF=${#FASES[@]}

# -L: emecas_actual.log es un enlace; sin -L el Mac da la fecha del enlace, no la del log (medido DAY303)
mtime() { stat -L -c %Y "$1" 2>/dev/null || stat -L -f %m "$1"; }
hm() { local s=$1; printf '%dh%02dm' $((s / 3600)) $((s % 3600 / 60)); }

while true; do
  printf '\033[H\033[2J'
  ahora=$(date +%s)
  echo "EMECAS watch  $(date '+%F %T')  (cada ${INT}s, Ctrl-C sale sin tocar la corrida)"
  echo "------------------------------------------------------------------------"
  if [[ ! -e "$LOG" ]]; then
    echo "No hay corrida: falta $LOG (lanza scripts/emecas/emecas_run.sh)"
    sleep "$INT"
    continue
  fi
  # fase
  ult=-1
  i=0
  while [[ $i -lt $NF ]]; do
    if grep -qF -- "${FASES[$i]}" "$LOG"; then ult=$i; fi
    i=$((i + 1))
  done
  hechas=$((ult + 1))
  ancho=40
  lleno=$((hechas * ancho / NF))
  barra=$(printf '%*s' "$lleno" '' | tr ' ' '#')
  vacio=$(printf '%*s' $((ancho - lleno)) '' | tr ' ' '.')
  pct=$((hechas * 100 / NF))
  if [[ $ult -ge 0 ]]; then fase="${FASES[$ult]}"; else fase="(aun ninguna)"; fi
  echo "Avance  [${barra}${vacio}] ${pct}%  hito ${hechas}/${NF}: ${fase}"
  # tiempos
  inicio=$(cat "$DIR/emecas_actual.start" 2>/dev/null || echo "$ahora")
  edad=$((ahora - $(mtime "$LOG")))
  echo "Tiempo  $(hm $((ahora - inicio))) desde el inicio; ultima linea del log hace $((edad / 60)) min $((edad % 60)) s"
  # vida del proceso
  if [[ -f "$DIR/emecas_actual.rc" ]]; then
    rc=$(cat "$DIR/emecas_actual.rc")
    if [[ "$rc" == "0" ]]; then estado="TERMINADA rc=0  -> VERDE"; else estado="TERMINADA rc=${rc}  -> FALLA"; fi
  elif kill -0 "$(cat "$DIR/emecas_actual.pid" 2>/dev/null || echo 0)" 2>/dev/null; then
    # DAY303 M1: un proceso detenido (estado T, p.ej. "suspended (tty output)") tambien pasa kill -0.
    # Se mira el estado de la corrida y de todos sus hijos (caffeinate, make, vagrant...)
    pid=$(cat "$DIR/emecas_actual.pid")
    det=$(ps -A -o pid=,ppid=,stat=,command= | LC_ALL=C awk -v r="$pid" '
      {p[$1]=$2; s[$1]=$3; c[$1]=$0}
      END {for (k in p) {x=k; while (x != "" && x != "1" && x != "0") {if (x == r) {if (s[k] ~ /^T/) print c[k]; break}; x=p[x]}}}' | head -2)
    if [[ -n "$det" ]]; then
      estado="DETENIDA (estado T: suspendida, no avanza). Procesos parados:"$'\n'"$(printf '%s\n' "$det" | cut -c1-100 | sed 's/^/        /')"
    else
      estado="VIVA (pid ${pid})"
    fi
  else
    estado="MUERTA sin rc: el proceso desaparecio sin terminar (cerrada la terminal? reinicio?)"
  fi
  echo "Corrida ${estado}"
  # CPU de las VMs
  cpu=$(ps -A -o %cpu=,command= | grep -i '[V]BoxHeadless' | LC_ALL=C awk '{s += $1; n++} END {printf "%d VMs, %.0f%% CPU", n, s}')
  echo "VMs     ${cpu:-0 VMs}"
  # zombis
  zomb=$(ps -A -o stat=,pid=,ppid=,command= | awk '$1 ~ /^Z/' )
  nz=$(printf '%s' "$zomb" | grep -c . || true)
  echo "Zombis  ${nz}"
  if [[ "$nz" != "0" ]]; then printf '%s\n' "$zomb" | head -3 | cut -c1-100 | sed 's/^/        /'; fi
  # diagnostico de cuelgue
  if [[ -z "$(cat "$DIR/emecas_actual.rc" 2>/dev/null)" && $edad -ge $CALLADO_AVISO ]]; then
    echo "AVISO   el log lleva $((edad / 60)) min callado: si la CPU de las VMs esta cerca de 0, mira la ultima linea"
  fi
  # errores
  # el PRIMER error de make es la causa; los siguientes son make propagandolo hacia arriba
  err=$(grep -E 'make(\[[0-9]+\])?: \*\*\*' "$LOG" | head -1 | cut -c1-110)
  echo "Error   ${err:-ninguno de make}"
  echo "------------------------------------------------------------------------"
  echo "Ultimas lineas:"
  tail -4 "$LOG" | LC_ALL=C sed $'s/\x1b\\[[0-9;]*m//g' | cut -c1-110 | sed 's/^/  /'
  if [[ -f "$DIR/emecas_actual.rc" ]]; then
    echo ""
    echo "La corrida ha terminado. Log: $(readlink "$LOG" 2>/dev/null || echo "$LOG")"
    exit 0
  fi
  sleep "$INT"
done
