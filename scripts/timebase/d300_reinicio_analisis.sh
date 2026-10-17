#!/usr/bin/env bash
# DAY300: marcados de la etapa 1 antes y despues del reinicio del sniffer. Corta el ml-detector.log por la
# linea anotada con el sniffer YA parado (linea_ml_parado; si falta, linea_ml_reinicio) y suma los
# resumenes [DDOS-V2] a cada lado. Uso: d300_reinicio_analisis.sh DIRECTORIO_CORRIDA
set -eu
export LC_ALL=C
D=${1:?directorio de la corrida}
T=$D/tiempos.txt; M=$D/ml-detector.log; S=$D/sniffer.log
for f in "$T" "$M" "$S"; do [ -f "$f" ] || { echo "ABORTA: no existe $f"; exit 1; }; done
L=$(awk '$1=="linea_ml_parado"{print $2}' "$T")
if [ -z "$L" ]; then L=$(awk '$1=="linea_ml_reinicio"{print $2}' "$T"); echo "AVISO: sin linea_ml_parado, corte en linea_ml_reinicio"; fi
[ -n "$L" ] || { echo "ABORTA: sin linea de corte en $T"; exit 1; }
echo "== tiempos"; cat "$T"
echo "== ml-detector.log: $(wc -l < "$M") lineas; corte en la linea $L"
awk -v L="$L" '/\[DDOS-V2\] bajo_presion=/ {
    p = 0; t = 0
    for (i = 1; i <= NF; i++) {
      if ($i ~ /^bajo_presion=/) { split($i, a, "="); p = a[2] }
      if ($i ~ /^ataque=/)       { split($i, b, "="); t = b[2] }
    }
    if (NR <= L) { pa += p; ta += t; na++ } else { pd += p; td += t; nd++ }
  }
  END {
    printf "antes_de_la_parada:   resumenes=%d pases=%d marcados=%d\n", na, pa, ta
    printf "despues_del_arranque: resumenes=%d pases=%d marcados=%d\n", nd, pd, td
    if (ta > 0) printf "razon marcados_despues/marcados_antes = %.3f\n", td / ta
    else print "razon: sin marcados antes de la parada"
  }' "$M"
echo "== sniffer.log: senales, volcados y restauraciones"
grep -n -e "\[Signal\]" -e "volcado de parada" -e "restauradas" -e "sin estado previo" -e "descartado" -e "ZMQ-DROP" "$S" || true
