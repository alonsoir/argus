#!/usr/bin/env bash
# DAY300: mide la parada ordenada del sniffer (SIGTERM -> fin del proceso) en ms.
# Si no termina en LIMITE_S, guarda las pilas de todos los hilos (gdb) y despues SIGKILL.
set -u
LIMITE_S=${LIMITE_S:-20}
PILAS=${PILAS:-/tmp/d300_parada_pilas.txt}
n=$(pgrep -x sniffer | wc -l)
if [ "$n" -eq 0 ]; then echo "sniffer no esta en marcha"; exit 1; fi
if [ "$n" -gt 1 ]; then echo "AVISO: $n procesos sniffer; se mide el primero"; fi
pid=$(pgrep -x sniffer | head -n 1)
echo "pid=$pid  SIGTERM  limite=${LIMITE_S} s"
t0=$(date +%s%N)
sudo kill -TERM "$pid"
while [ -d "/proc/$pid" ]; do
  t=$(( ($(date +%s%N) - t0) / 1000000 ))
  if [ "$t" -ge $(( LIMITE_S * 1000 )) ]; then
    echo "NO PARO en ${LIMITE_S} s: pilas de hilos en $PILAS, despues SIGKILL"
    sudo gdb -p "$pid" -batch -ex "thread apply all bt" > "$PILAS" 2>&1
    sudo kill -KILL "$pid"
    exit 2
  fi
  sleep 0.1
done
t=$(( ($(date +%s%N) - t0) / 1000000 ))
echo "PARADA ORDENADA en ${t} ms"
