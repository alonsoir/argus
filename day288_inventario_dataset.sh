#!/usr/bin/env bash
# DAY288 paso 1 — inventario de ddos_dataset_*.csv (solo lectura).
# Columnas: 1 ts_ns 2 community_id 3 src_ip 4 dst_ip 5 sport 6 dport 7 proto 8 kind
#           9 syn_ack 10 mean_size 11 refl 12 entropy 13 flow_pkts 14 completion
#           15 victim_rate_ratio 16 victim_pps 17 old_prob 18 old_class
set -eu
export LC_ALL=C
DIR=/vagrant/logs/lab/ddos_dataset
OUT=/vagrant/logs/lab/day288/01_inventario.txt
: > "$OUT"
for f in $(ls -1 "$DIR"/ddos_dataset_*.csv); do
  {
    echo "=================================================="
    echo "fichero=$(basename "$f")  bytes=$(stat -c %s "$f")"
    echo "sha256=$(sha256sum "$f" | cut -d' ' -f1)"
    echo "cabecera_campos=$(head -1 "$f" | awk -F',' '{print NF}')"
    awk -F',' '
      NR==1 {next}
      { n++; if (NF!=18) bad++
        if ($3=="192.168.100.50" && $4=="192.168.100.1") {
          lab++; k[$8]++; pr[$7]++; sp[$5]++; cid[$2]=1
          if (tmin=="" || $1<tmin) tmin=$1; if ($1>tmax) tmax=$1
          for (c=9;c<=16;c++) if ($c<=-9000) sent[c]++
          oc[$18]++
        } else amb++ }
      END {
        printf "filas=%d  filas_!=18_campos=%d  lab(.50->.1)=%d  ambiente=%d\n", n, bad+0, lab+0, amb+0
        if (lab>0) {
          printf "duracion_lab_s=%.1f  community_id_distintos=%d\n", (tmax-tmin)/1e9, length(cid)
          printf "kind:"; for (x in k) printf " %s=%d", x, k[x]; print ""
          printf "proto:"; for (x in pr) printf " %s=%d", x, pr[x]; print ""
          printf "old_class:"; for (x in oc) printf " %s=%d", x, oc[x]; print ""
          printf "centinelas(col=n):"; for (c=9;c<=16;c++) printf " %d=%d", c, sent[c]+0; print ""
          ns=0; for (x in sp) ns++
          printf "sport_distintos=%d\n", ns
        }
      }' "$f"
    echo "--- top 3 sport (.50->.1)"
    awk -F',' 'NR>1 && $3=="192.168.100.50" && $4=="192.168.100.1" {print $5}' "$f" | sort | uniq -c | sort -rn | head -3
  } >> "$OUT"
done
wc -l "$OUT"
