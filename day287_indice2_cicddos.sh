#!/usr/bin/env bash
# DAY287 punto 2a-bis — tipo de ataque por chunk: sentido del atacante, proto/puerto ORIGEN y longitud dominantes
set -u
export LC_ALL=C
DIR=/vagrant/datasets/cicddos2019
OUT=/vagrant/logs/lab/day287/16_indice2_cicddos.txt
TMP=$(mktemp)
for f in "$DIR"/SAT-01-12-2018_0*; do
  b=$(basename "$f"); n=${b##*_0}; n=${n:-0}
  r=$(tcpdump -r - -c 5000 -nn -q < "$f" 2>/dev/null | awk '
    $3 ~ /^172\.16\.0\.5\./ { as++; m=split($3, p, "."); pr=$6; sub(/,$/, "", pr); sp[pr "/" p[m]]++; ln[$NF]++ }
    $5 ~ /^172\.16\.0\.5\./ { ad++ }
    END {
      bs="-"; c=0; for (k in sp) if (sp[k]>c) { c=sp[k]; bs=k }
      bl="-"; d=0; for (k in ln) if (ln[k]>d) { d=ln[k]; bl=k }
      printf "src=%d dst=%d top_sport=%s top_len=%s", as, ad, bs, bl
    }')
  echo "$n $r" >> "$TMP"
done
sort -n -k1,1 "$TMP" > "$OUT"; rm -f "$TMP"
wc -l "$OUT"
