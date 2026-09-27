#!/usr/bin/env bash
# Umbrales del bosque DDoS por feature_idx (espacio MinMax de train). Uso: d281_hpp_thr.sh [IDX] [HPP]
set -euo pipefail
IDX=${1:-7}
HPP=${2:-ml-detector/include/ml_defender/ddos_trees_inline.hpp}
grep -E "^[[:space:]]*\{${IDX}, " "$HPP" \
 | sed -E 's/^[[:space:]]*\{[0-9]+, ([-0-9.eE]+)f.*/\1/' \
 | LC_ALL=C sort -g \
 | LC_ALL=C awk '{v[NR]=$1} END{n=NR; if(n==0){print "idx='"$IDX"' n=0"; exit}
   printf "idx=%s n=%d min=%.6f p25=%.6f med=%.6f p75=%.6f max=%.6f\n", "'"$IDX"'", n, v[1], v[int(n*0.25)+1], v[int(n*0.5)+1], v[int(n*0.75)+1], v[n]}'
