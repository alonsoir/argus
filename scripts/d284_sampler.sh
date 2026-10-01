#!/usr/bin/env bash
# DAY284 — muestrea cada PASO s: epoch, ultimo calls de [ML-TIME], ultimo "Paquetes procesados".
# Uso: [LOG=ruta] d284_sampler.sh SEGUNDOS PASO SALIDA   (solo observacion)
# Tolera log recien truncado (grep sin coincidencias -> 0).
set -euo pipefail
N="${1:-600}"; PASO="${2:-5}"; OUT="${3:-/vagrant/logs/lab/d284_sampler.txt}"
LOG="${LOG:-/vagrant/logs/lab/sniffer.log}"
echo "# log=$LOG" > "$OUT"
echo "epoch calls procesados" >> "$OUT"
FIN=$(( $(date +%s) + N ))
while [ "$(date +%s)" -lt "$FIN" ]; do
  c=$( { grep '\[ML-TIME\]' "$LOG" || true; } | tail -n 1 | LC_ALL=C awk -F'[ =]+' '{for(i=1;i<=NF;i++) if($i=="calls") print $(i+1)+0}')
  p=$( { grep 'Paquetes procesados' "$LOG" || true; } | tail -n 1 | LC_ALL=C awk '{print $NF+0}')
  echo "$(date +%s) ${c:-0} ${p:-0}" >> "$OUT"
  sleep "$PASO"
done
echo "OK: $OUT"
