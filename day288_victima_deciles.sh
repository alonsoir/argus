#!/usr/bin/env bash
# DAY288 — victim_pps y victim_rate_ratio por decil temporal de una corrida. Uso: FICHERO TAG
set -eu
export LC_ALL=C
F=/vagrant/logs/lab/ddos_dataset/${1:?fichero}
OUT=/vagrant/logs/lab/day288/victima_deciles_${2:?tag}.txt
awk -F',' '
  NR==FNR { if (FNR>1 && $3=="192.168.100.50" && $4=="192.168.100.1" && $8==0) {
              if (tmin=="" || $1+0<tmin) tmin=$1+0; if ($1+0>tmax) tmax=$1+0 }
            next }
  FNR==1 {next}
  $3=="192.168.100.50" && $4=="192.168.100.1" && $8==0 && $16>-9000 {
    d=int(10*($1-tmin)/(tmax-tmin+1)); n[d]++; s[d]+=$16; r[d]+=$15
    if (!(d in mn) || $16<mn[d]) mn[d]=$16; if ($16>mx[d]) mx[d]=$16
    v[d" "$16]++
  }
  END {
    for (k in v) { split(k,a," "); nd[a[1]]++ }
    print "decil n pps_media pps_min pps_max valores_distintos ratio_medio"
    for (d=0; d<10; d++) printf "%d %d %.1f %.1f %.1f %d %.3f\n", d, n[d], s[d]/n[d], mn[d], mx[d], nd[d], r[d]/n[d]
  }' "$F" "$F" > "$OUT"
cat "$OUT"
