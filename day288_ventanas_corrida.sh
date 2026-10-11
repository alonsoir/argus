#!/usr/bin/env bash
# DAY288 — ventanas del lector del kernel (ddos_windows.csv) para la victima .1/UDP durante una corrida.
# Uso: day288_ventanas_corrida.sh FICHERO_DATASET TAG
set -eu
export LC_ALL=C
F=/vagrant/logs/lab/ddos_dataset/${1:?fichero}
W=/vagrant/logs/lab/ddos_windows.csv
OUT=/vagrant/logs/lab/day288/ventanas_${2:?tag}.txt
read TMIN TMAX < <(awk -F',' 'FNR>1 && $3=="192.168.100.50" && $4=="192.168.100.1" && $8==0 {
    if (a=="" || $1+0<a) a=$1+0; if ($1+0>b) b=$1+0 } END {printf "%.0f %.0f\n", a, b}' "$F")
{
  echo "dataset tmin_ns=$TMIN tmax_ns=$TMAX"
  echo "--- ventanas .1/UDP alineadas por reloj (t_rel_s respecto a tmin del dataset)"
  awk -F',' -v a="$TMIN" -v b="$TMAX" '
    NR>1 && ($4=="192.168.100.1" || $4=="3232261121" || $4=="23374016") && $5==17 {
      t=$2*1e6
      if (t >= a-60e9 && t <= b+5e9) {
        n++; pps = ($3>0) ? $6*1000/$3 : -1
        printf "win=%s t_rel_s=%.1f window_ms=%s d_pkts=%s pps=%.1f\n", $1, (t-a)/1e9, $3, $6, pps }
    } END { print "ventanas_alineadas=" n+0 }' "$W"
  echo "--- ultimas 150 ventanas .1/UDP sin alinear (por si el reloj no casa)"
  awk -F',' 'NR>1 && ($4=="192.168.100.1" || $4=="3232261121" || $4=="23374016") && $5==17' "$W" | tail -150
} > "$OUT"
wc -l "$OUT"
