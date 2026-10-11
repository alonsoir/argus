#!/usr/bin/env bash
# DAY284 — CPU por hilo (top -H) cada 1 s; fotogramas numerados desde epoch de inicio. Solo observacion.
# Uso: d284_cpu_drain.sh SEGUNDOS SALIDA
set -euo pipefail
N="${1:-420}"; OUT="${2:-/vagrant/logs/lab/d284_top.txt}"
echo "start $(date +%s)" > "$OUT"
LC_ALL=C top -H -b -d 1 -n "$N" -w 200 | LC_ALL=C awk '
  /^top - /  { f++; print "=== " f; next }
  /^%Cpu/    { print; next }
  $1 ~ /^[0-9]+$/ && $9+0 >= 0.5 { print $1, $9, $12 }
' >> "$OUT"
echo "OK: $OUT"
