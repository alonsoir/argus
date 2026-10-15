#!/usr/bin/env bash
# DAY298: tiempos de las lineas de la sombra (prefijo de pared UTC del log del firewall) relativos a
# inicio_ataque del client (epoch). Uso: d298_alinear_sombra.sh DIRECTORIO_CORRIDA
set -eu
D=${1:?directorio de la corrida}
A=$(awk '$1=="inicio_ataque"{print $2}' "$D/tiempos.txt")
[ -n "$A" ] || { echo "ABORTA: sin inicio_ataque en $D/tiempos.txt"; exit 1; }
echo "inicio_ataque=$A ($(date -u -d "@$A" '+%F %T') UTC)"
grep -E '^[0-9]{4}-[0-9]{2}-[0-9]{2} ' "$D/firewall-agent.log" | grep -E 'primer DROP|registro=INICIO|registro=FIN' \
 | while read -r d t resto; do
     e=$(date -u -d "$d $t" +%s.%N)
     LC_ALL=C awk -v e="$e" -v a="$A" -v r="$(printf '%s' "$resto" | grep -oE 'primer DROP[^:]*|registro=[A-Z]+|ts_s=[0-9]+|inicio_s=[0-9]+|fin_s=[0-9]+' | tr '\n' ' ')" \
       'BEGIN{printf "%+9.3f s  %s\n", e-a, r}'
   done
