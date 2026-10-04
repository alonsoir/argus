#!/usr/bin/env bash
# DAY287 — P11 lado dataset: ¿las filas del dataset sin pareja en correlacion son su cola?
set -u
export LC_ALL=C
OUT=/vagrant/logs/lab/day287
MARKER=$OUT/run_marker
DS=$(ls -1t /vagrant/logs/lab/ddos_dataset/ddos_dataset_*.csv | head -1)
find /vagrant/logs/correlation -type f -name 'argus-*' -newer "$MARKER" | sort | xargs cat > "$OUT/12_corr_run.csv"
awk -F',' '
  FNR==NR {
    eid=$3; ts=""
    if (match(eid, /[0-9]+/)) ts=substr(eid, RSTART, RLENGTH)
    cr[$5 "|" ts]++; next
  }
  FNR==1 || $2=="" { next }
  {
    n++; k=$2 "|" $1
    if (cr[k]>0) { cr[k]--; ok++ }
    else { miss++; if (first=="") first=n; last=n; if (miss<=30) lst=lst sprintf("  idx=%d ts=%s kind=%s %s->%s\n", n, $1, $8, $3, $4) }
  }
  END {
    printf "ds_con_cid=%d cruzan=%d ds_sin_cruzar=%d\n", n, ok, miss
    printf "primer_idx=%s ultimo_idx=%s (cola contigua si primero=%d y ultimo=%d)\n", first, last, n-miss+1, n
    printf "%s", lst
  }' "$OUT/12_corr_run.csv" "$DS" > "$OUT/13_cruce_ds.txt" 2>&1
wc -l "$OUT/13_cruce_ds.txt"
