#!/usr/bin/env bash
# check_mldetector_backlog.sh -- estado del ml-detector antes de una medida.
#
# Objetivo (hallazgo 4, DAY275): el ml-detector puede quedar con atraso tras
# una corrida (cola de eventos por procesar), consumiendo ~4 nucleos en la
# corrida siguiente y contaminando la medida. Este script da una lectura
# rapida de si ya ha drenado antes de lanzar la proxima corrida.
#
# Uso (en `defender`):
#   bash /vagrant/check_mldetector_backlog.sh
#
# No escribe nada, no toca el pipeline. Solo lectura.

set -u

LOG=/vagrant/logs/lab/ml-detector.log
PIDS=$(pgrep -x ml-detector || true)

echo "=== ml-detector: PIDs y CPU% ==="
if [ -z "$PIDS" ]; then
  echo "AVISO: ml-detector no esta corriendo (pgrep -x ml-detector vacio)"
else
  PIDLIST=$(echo "$PIDS" | tr '\n' ',' | sed 's/,$//')
  ps -o pid,pcpu,etimes,comm -p "$PIDLIST"
fi

echo
echo "=== log: crecimiento en 5s ==="
if [ -f "$LOG" ]; then
  s1=$(stat -c%s "$LOG")
  sleep 5
  s2=$(stat -c%s "$LOG")
  delta=$((s2 - s1))
  rate=$(awk -v d="$delta" 'BEGIN { printf "%.0f", d / 5 }')
  echo "tamano: $s1 B -> $s2 B  (+$delta B en 5s, ~$rate B/s)"
else
  echo "AVISO: no existe $LOG"
fi

echo
echo "=== veredicto orientativo ==="
echo "Baseline DAY275 en reposo: ~100 KB/s de log, hilos ~1% CPU."
echo "Si el ritmo de escritura esta muy por encima de eso, o el CPU% sigue"
echo "alto (hilos aun activos varios minutos tras el ultimo replay), hay"
echo "atraso: esperar antes de lanzar la siguiente corrida, o anotarlo"
echo "explicitamente en la tabla de resultados si decides medir igualmente."