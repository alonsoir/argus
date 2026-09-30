#!/usr/bin/env bash
# DAY284 — resume d284_top.txt en una ventana [T0,T1] (epoch): %Cpu medio (us sy id wa si st) y %CPU por hilo.
# Uso: d284_cpu_summary.sh ENTRADA T0 T1
set -euo pipefail
IN="$1"; T0="$2"; T1="$3"
LC_ALL=C awk -v t0="$T0" -v t1="$T1" '
  /^start / { s=$2; next }
  /^=== /   { t=s+$2-1; w=(t>=t0 && t<=t1); if(w) fr++; next }
  !w        { next }
  /^%Cpu/   { for(i=2;i<=NF;i++){ k=$(i+1); gsub(/,/,"",k); v=$i+0;
                if(k=="us"||k=="sy"||k=="id"||k=="wa"||k=="si"||k=="st") c[k]+=v } ; n++; next }
  { h[$3]+=$2 }
  END { printf "frames=%d  us=%.1f sy=%.1f id=%.1f wa=%.1f si=%.1f st=%.1f\n", fr,
          c["us"]/n, c["sy"]/n, c["id"]/n, c["wa"]/n, c["si"]/n, c["st"]/n
        for(k in h) printf "  %-22s %6.1f%%\n", k, h[k]/fr }' "$IN"
