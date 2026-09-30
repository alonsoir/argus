#!/usr/bin/env bash
# DAY284 — resume d284_pmp_raw.txt en [T0,T1]: por hilo (LWP), las 4 funciones superiores de la pila y cuantas veces.
# Uso: d284_pmp_summary.sh ENTRADA T0 T1
set -euo pipefail
IN="$1"; T0="$2"; T1="$3"
LC_ALL=C awk -v t0="$T0" -v t1="$T1" '
  function flush_key() { if (key != "" && w) c[key]++; key="" }
  /^=== muestra/ { flush_key(); w=($4>=t0 && $4<=t1); next }
  /^Thread .*LWP/ { flush_key(); match($0,/LWP [0-9]+/); key=substr($0,RSTART+4,RLENGTH-4) ":"; nf=0; next }
  /^#[0-9]+ / && key!="" && nf<4 {
    f=""; for(i=1;i<=NF;i++) if($i=="in"){f=$(i+1);break}
    if(f=="") f=$2
    sub(/\(.*/,"",f); key=key " < " f; nf++; next }
  END { flush_key(); for(k in c) printf "%3d %s\n", c[k], k }' "$IN" | sort -rn
