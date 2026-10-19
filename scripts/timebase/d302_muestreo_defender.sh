#!/usr/bin/env bash
# DAY302 muestreo (defender) cada ~1 s: miembros del set blacklist (ip:timeout:comentario) y contador de paquetes de
# la regla DROP de la cadena de aRGus. Uso: bash d302_muestreo_defender.sh SALIDA FICHERO_PARADA SET CADENA
# Termina al existir FICHERO_PARADA.
set -u
OUT=$1
STOP=$2
BL=$3
CH=$4
: > "$OUT"
while [ ! -e "$STOP" ]; do
  t=$(date +%s.%N)
  m=$(sudo ipset list "$BL" 2>/dev/null | awk '/^Members:/ {f = 1; next} f && NF {printf "%s:%s:%s;", $1, ($2 == "timeout" ? $3 : "-"), $NF}')
  d=$(sudo iptables -L "$CH" -v -n -x 2>/dev/null | awk -v bl="$BL" '$3 == "DROP" && index($0, bl) {s += $1} END {print s + 0}')
  echo "S $t drop_pkts=$d miembros=$m" >> "$OUT"
  sleep 1
done
echo "FIN $(date +%s.%N)" >> "$OUT"
