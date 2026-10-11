#!/usr/bin/env bash
# DAY290 — CPU por hilo del sniffer segun el kernel (/proc/PID/task/TID/stat: utime+stime). SOLO LECTURA.
# Arbitro entre top y perf. Uso: bash day290_cpu_hilos.sh SEGUNDOS [PID]
set -eu
export LC_ALL=C
SEG="${1:-}"
PID="${2:-}"
[[ "$SEG" =~ ^[0-9]+$ ]] && [ "$SEG" -gt 0 ] || { echo "ERROR: SEGUNDOS debe ser entero > 0 (recibido: $SEG)" >&2; exit 2; }
if [ -z "$PID" ]; then PID="$(pgrep -x sniffer | head -1 || true)"; fi
[ -n "$PID" ] && [ -d "/proc/$PID" ] || { echo "ERROR: no hay proceso sniffer" >&2; exit 3; }
HZ=$(getconf CLK_TCK)

# tid ticks(utime+stime). Tras el ultimo ") " del stat: $1=estado, $12=utime, $13=stime
snap() {
  local t s rest tid
  for t in /proc/"$PID"/task/*; do
    s=$(cat "$t/stat" 2>/dev/null) || continue
    tid=${t##*/}
    rest=${s##*) }
    set -- $rest
    echo "$tid $(( ${12} + ${13} ))"
  done | sort
}

A=$(snap)
sleep "$SEG"
B=$(snap)

echo "sniffer PID=$PID ventana=${SEG}s CLK_TCK=$HZ (100 % = un nucleo entero)"
printf "%-8s %-16s %8s  %s\n" tid comm pct_cpu wchan
join <(echo "$A") <(echo "$B") | while read -r tid a b; do
  comm=$(cat "/proc/$PID/task/$tid/comm" 2>/dev/null || echo '?')
  wchan=$(cat "/proc/$PID/task/$tid/wchan" 2>/dev/null || echo '?')
  awk -v t="$tid" -v c="$comm" -v w="$wchan" -v d=$((b - a)) -v hz="$HZ" -v s="$SEG" \
    'BEGIN { printf "%-8s %-16s %7.1f%%  %s\n", t, c, 100 * d / (hz * s), w }'
done | sort -k3 -rn
