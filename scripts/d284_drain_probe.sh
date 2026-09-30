#!/usr/bin/env bash
# DAY284 P5 — durante un drenaje: syscalls del sniffer (strace -c) y ritmo lineas de log vs eventos.
# Uso: d284_drain_probe.sh [SEGUNDOS]   (solo observacion)
set -euo pipefail
DUR="${1:-60}"
LOG=/vagrant/logs/lab/sniffer.log
OUT=/vagrant/logs/lab/d284_drain_probe.txt
command -v strace >/dev/null || { echo "PARAR: falta strace (sudo apt-get install -y strace)"; exit 1; }
PID=$(pgrep -o -x sniffer) || { echo "PARAR: el sniffer no corre"; exit 1; }
last_proc() { grep 'Paquetes procesados' "$LOG" | tail -n 1 | LC_ALL=C awk '{print $NF+0}'; }
{
  echo "pid=$PID"
  echo "--- fds de log del sniffer"
  sudo ls -l /proc/"$PID"/fd | grep -E 'log|vagrant' || echo "(ninguno con log|vagrant)"
  L0=$(wc -l < "$LOG"); P0=$(last_proc); T0=$(date +%s)
  sudo timeout "$DUR" strace -c -f -p "$PID" -o /tmp/d284_strace.txt || true
  L1=$(wc -l < "$LOG"); P1=$(last_proc); T1=$(date +%s)
  echo "--- ritmo (dt=$((T1-T0)) s)  procesados: $P0 -> $P1"
  LC_ALL=C awk -v l0="$L0" -v l1="$L1" -v p0="$P0" -v p1="$P1" -v dt="$((T1-T0))" 'BEGIN{
    printf "lineas_log/s=%.1f  eventos/s=%.1f  lineas_por_evento=%s\n",
      (l1-l0)/dt, (p1-p0)/dt, (p1>p0 ? sprintf("%.2f",(l1-l0)/(p1-p0)) : "n/d")}'
  echo "--- strace -c (todos los hilos)"
  cat /tmp/d284_strace.txt
} > "$OUT" 2>&1
echo "OK: $OUT"
