#!/usr/bin/env bash
# DAY288 — filas kind=0 con rasgos de flujo (9-14) a centinela pero victima (15-16) vivos.
set -eu
export LC_ALL=C
F=/vagrant/logs/lab/ddos_dataset/ddos_dataset_20261004-070818.csv
OUT=/vagrant/logs/lab/day288/02_huecos_flujo.txt
awk -F',' '
  NR==FNR { if (FNR>1 && $3=="192.168.100.50" && $4=="192.168.100.1") {
              if (tmin=="" || $1+0<tmin) tmin=$1+0; if ($1+0>tmax) tmax=$1+0 }
            next }
  FNR==1 {next}
  $3=="192.168.100.50" && $4=="192.168.100.1" && $8==0 {
    d=int(10*($1-tmin)/(tmax-tmin+1))
    tot[$5" "d]++
    if ($9<=-9000) { h++; hs[$5]++; hd[$5" "d]++; ho[$18]++
                     if (ns<5) { print "ejemplo: " $0; ns++ } }
  }
  END {
    printf "huecos_kind0=%d\n", h
    printf "por_sport:"; for (x in hs) printf " %s=%d", x, hs[x]; print ""
    printf "old_class:"; for (x in ho) printf " %s=%d", x, ho[x]; print ""
    print "decil  sport  huecos/total_kind0"
    for (s=0; s<2; s++) { sp = (s==0) ? 123 : 53
      for (d=0; d<10; d++) printf "%d  %d  %d/%d\n", d, sp, hd[sp" "d]+0, tot[sp" "d]+0 }
  }' "$F" "$F" > "$OUT"
wc -l "$OUT"
