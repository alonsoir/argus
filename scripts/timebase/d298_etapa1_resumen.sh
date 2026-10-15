#!/usr/bin/env bash
# DAY298: lo que dice el pipeline de la etapa 1 en una corrida. Suma los resumenes [DDOS-V2] del ml-detector
# (pases de la etapa 1 = bajo_presion, marcados = ataque, eventos sin estado) y muestra la configuracion activa
# de la histeresis del sniffer. Uso: d298_etapa1_resumen.sh DIRECTORIO_CORRIDA
set -eu
D=${1:?directorio de la corrida}
M="$D/ml-detector.log"
S="$D/sniffer.log"
[ -f "$M" ] || { echo "ABORTA: no existe $M"; exit 1; }
echo "== sniffer: configuracion de la histeresis"
grep -h -E '\[DDOS-HYST\]|\[CONFIG-DEFAULT\]|\[CONFIG-OBSOLETO\]' "$S" 2>/dev/null || echo "  (sin sniffer.log)"
echo "== ml-detector: suma de los resumenes [DDOS-V2]"
LC_ALL=C awk '/\[DDOS-V2\] bajo_presion=/ {for(i=1;i<=NF;i++){ if($i ~ /^bajo_presion=/){split($i,a,"=");p+=a[2]} if($i ~ /^ataque=/){split($i,b,"=");t+=b[2]} } n++}
             /\[DDOS-V2\] sin_estado=/ {for(i=1;i<=NF;i++) if($i ~ /^sin_estado=/){split($i,c,"=");s+=c[2]}}
             END{printf "  resumenes=%d pases_etapa1=%d marcados_ataque=%d sin_estado=%d\n", n, p, t, s}' "$M"
