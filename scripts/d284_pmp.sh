#!/usr/bin/env bash
# DAY284 — muestreo de pilas: N muestras de backtraces de todos los hilos del sniffer.
# Cada muestra detiene el proceso ~1 s. Uso: d284_pmp.sh N PAUSA SALIDA
set -euo pipefail
N="${1:-24}"; PAUSA="${2:-4}"; OUT="${3:-/vagrant/logs/lab/d284_pmp_raw.txt}"
command -v gdb >/dev/null || { echo "PARAR: falta gdb"; exit 1; }
PID=$(pgrep -o -x sniffer) || { echo "PARAR: el sniffer no corre"; exit 1; }
: > "$OUT"
for i in $(seq 1 "$N"); do
  echo "=== muestra $i $(date +%s)" >> "$OUT"
  sudo gdb -p "$PID" -batch -nx -ex "set pagination off" -ex "thread apply all bt 12" >> "$OUT" 2>/dev/null || true
  sleep "$PAUSA"
done
echo "OK: $OUT"
