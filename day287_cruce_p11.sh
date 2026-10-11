#!/usr/bin/env bash
# DAY287 — P11: ¿las filas de correlacion que faltan en el dataset son la cola de la corrida?
set -u
export LC_ALL=C
OUT=/vagrant/logs/lab/day287
MARKER=$OUT/run_marker
DS=$(ls -1t /vagrant/logs/lab/ddos_dataset/ddos_dataset_*.csv | head -1)
find /vagrant/logs/correlation -type f -name 'argus-*' -newer "$MARKER" | sort > "$OUT/10_corr_ficheros.txt"
xargs cat < "$OUT/10_corr_ficheros.txt" > "$OUT/10_corr_run.csv"
awk -F',' '
  FNR==NR { if (FNR>1 && $2!="") ds[$2 "|" $1]++; next }
  {
    n++
    eid=$3; ts=""
    if (match(eid, /[0-9]+/)) ts=substr(eid, RSTART, RLENGTH)
    k=$5 "|" ts
    if (ds[k]>0) { ds[k]--; ok++ }
    else { miss++; if (first=="") first=n; last=n; if (miss<=30) lst=lst sprintf("  idx=%d eid=%s\n", n, eid) }
  }
  END {
    left=0; for (k in ds) left+=ds[k]
    printf "corr_total=%d cruzan=%d corr_sin_cruzar=%d dataset_sin_cruzar=%d\n", n, ok, miss, left
    printf "primer_idx_sin_cruzar=%s ultimo_idx_sin_cruzar=%s (contigua_al_final si primero=%d y ultimo=%d)\n", first, last, n-miss+1, n
    printf "%s", lst
  }' "$DS" "$OUT/10_corr_run.csv" > "$OUT/11_cruce_p11.txt" 2>&1
wc -l "$OUT/11_cruce_p11.txt"
