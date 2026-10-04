#!/usr/bin/env bash
# DAY287 2.2 — reflexion UDP del lab por el pipeline. Uso: day287_medir_reflex.sh <sport> <etiqueta>
set -u
export LC_ALL=C
SPORT=$1; TAG=$2
OUT=/vagrant/logs/lab/day287/26_reflex_${TAG}.txt
DS=$(ls -1t /vagrant/logs/lab/ddos_dataset/ddos_dataset_*.csv | head -1)
{
echo "dataset=$DS  sport=$SPORT  tag=$TAG"
echo "--- filas .50 -> .1 UDP sport=$SPORT por kind"
awk -F',' -v sp="$SPORT" 'NR>1 && $3=="192.168.100.50" && $4=="192.168.100.1" && $7==17 && $5==sp { print "kind=" $8 }' "$DS" | sort | uniq -c
echo "--- rasgos medios (kind=0)"
awk -F',' -v sp="$SPORT" 'NR>1 && $3=="192.168.100.50" && $4=="192.168.100.1" && $7==17 && $5==sp && $8==0 {
  n++; ms+=$10; r+=$11; e+=$12; fp+=$13; vp+=$16
  if ($18==1) c1++; else if ($18==0) c0++; else cn++
} END { if (n) printf "n=%d mean_size=%.1f refl=%.3f entropy=%.3f flow_pkts=%.2f victim_pps=%.1f class1=%d class0=%d no_eval=%d\n", n, ms/n, r/n, e/n, fp/n, vp/n, c1, c0, cn }' "$DS"
echo "--- 3 filas de ejemplo"
awk -F',' -v sp="$SPORT" 'NR>1 && $3=="192.168.100.50" && $4=="192.168.100.1" && $7==17 && $5==sp && $8==0' "$DS" | head -3
} > "$OUT" 2>&1
wc -l "$OUT"
