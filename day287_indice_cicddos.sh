#!/usr/bin/env bash
# DAY287 punto 2a — indice de chunks CICDDoS2019 01-12: inicio, fraccion del atacante, proto/puerto dominante
# tcpdump lee por stdin: el perfil AppArmor de tcpdump no deja abrir ficheros sin extension .pcap
set -u
export LC_ALL=C
DIR=/vagrant/datasets/cicddos2019
OUT=/vagrant/logs/lab/day287/15_indice_cicddos.txt
ERR=/vagrant/logs/lab/day287/15_indice_cicddos.err
TMP=$(mktemp)
: > "$ERR"
for f in "$DIR"/SAT-01-12-2018_0*; do
  b=$(basename "$f")
  n=${b##*_0}; n=${n:-0}
  first=$(tcpdump -r - -c 1 -tt -nn < "$f" 2>>"$ERR" | awk '{print $1}')
  [ -n "$first" ] || { echo "SIN_TS $b" >> "$ERR"; continue; }
  utc=$(date -u -d "@${first%.*}" +%H:%M:%S)
  stats=$(tcpdump -r - -c 20000 -nn -q < "$f" 2>>"$ERR" | awk '
    { tot++
      if ($3 ~ /^172\.16\.0\.5\./ || $5 ~ /^172\.16\.0\.5\./) {
        a++
        dp=$5; sub(/:$/, "", dp); m=split(dp, p, "."); pr=$6; sub(/,$/, "", pr)
        c[pr "/" p[m]]++
      }
    }
    END {
      best="-"; bc=0; for (k in c) if (c[k]>bc) { bc=c[k]; best=k }
      printf "%.3f %s", (tot ? a/tot : 0), best
    }')
  echo "$n $first $utc $stats" >> "$TMP"
done
{ echo "n first_epoch first_utc att_frac top_att_proto_dport"; sort -n -k1,1 "$TMP"; } > "$OUT"
rm -f "$TMP"
wc -l "$OUT"
echo "sin_ts=$(grep -c '^SIN_TS' "$ERR")"
