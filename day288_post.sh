#!/usr/bin/env bash
# DAY288 — tras pipeline-stop: QA, registro y medida. Uso: day288_post.sh FAMILIA TASA PROTO
# runs.tsv: familia, tasa, fichero, ventanas_previas (ventanas de la clave .1/PROTO entre el arranque
# del pipeline y el inicio del ataque; <30 = regimen frio, el elegido para el dataset)
set -eu
export LC_ALL=C
FAM=${1:?familia}; R=${2:?tasa}; P=${3:?proto}
REG=${REG:-runs}  # DAY289: registro (runs | contraste)
TAG=${FAM}_${R}
D=/vagrant/logs/lab/day288
W=/vagrant/logs/lab/ddos_windows.csv
M=$(cat "$D/marca.txt")
pkill -f 'vmstat -t 1' || true
pkill -f 'top -b -d 2' || true
QA=$(/vagrant/day288_qa_corrida.sh "$M" "$R" "$P")
echo "QA $TAG: $QA"
F=$(basename "$(ls -1t /vagrant/logs/lab/ddos_dataset/ddos_dataset_*.csv | head -1)")
S=$(echo "$F" | sed -E 's/ddos_dataset_([0-9]{4})([0-9]{2})([0-9]{2})-([0-9]{2})([0-9]{2})([0-9]{2})\.csv/\1-\2-\3 \4:\5:\6/')
T0=$(date -u -d "$S" +%s)
read A B < <(tail -n +"$((M+1))" "$W" | awk -F',' -v P="$P" -v R="$R" '
  ($4=="192.168.100.1" || $4=="3232261121" || $4=="23374016") && $5==P && $3>0 && $6*1000/$3 >= R/2 {
    if (a=="") a=int($2/1000); b=int($2/1000) }
  END { printf "%d %d\n", a, b }')
PREV=$(awk -F',' -v a="$T0" -v b="$A" -v P="$P" 'NR>1 && ($4=="192.168.100.1" || $4=="3232261121" || $4=="23374016") && $5==P && $2/1000>=a && $2/1000<b {n++} END{print n+0}' "$W")
echo "arranque=$(date -u -d @"$T0" +%T) ataque_desde=$(date -u -d @"$A" +%T) ataque_hasta=$(date -u -d @"$B" +%T) ventanas_previas=$PREV $( [ "$PREV" -lt 30 ] && echo FRIO || echo CALIENTE )"
case "$QA" in
  *ACEPTADA) if [ "$PREV" -lt 30 ]; then printf '%s\t%s\t%s\t%s\n' "$FAM" "$R" "$F" "$PREV" >> "$D/${REG}.tsv"
             else printf '%s\t%s\t%s\t%s\n' "$FAM" "$R" "$F" "$PREV" >> "$D/${REG}_caliente.tsv"; fi ;;
  *)         printf '%s\t%s\t%s\t%s\tRECHAZADA\n' "$FAM" "$R" "$F" "$PREV" >> "$D/${REG}_descartadas.tsv" ;;
esac
awk 'NR>2 && ($17+0>=20 || $13+$14>=80 || $16+0>=20) {n++; if (a=="") a=$19; b=$19}
     END {printf "segundos_con_carga_vmstat=%d primero=%s ultimo=%s\n", n+0, a, b}' "$D/vmstat_${TAG}.txt"
/vagrant/day288_medir_corrida.sh "$F" "$TAG"
