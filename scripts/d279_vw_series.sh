#!/usr/bin/env bash
# Serie temporal de la ventana por victima vista por el ml-detector ([VICTIM-WINDOW]).
# Una fila por ventana (seq) y victima/proto; resumen por fase respecto al replay.
# Uso: d279_vw_series.sh "HH:MM:SS" "HH:MM:SS" [victim] [proto]
set -euo pipefail
export LC_ALL=C
LOG=/vagrant/logs/lab/ml-detector.log
DAY=$(date +%F)
T0="[$DAY $1"; T1="[$DAY $2"
VIC="${3:-192.168.100.1}"; PROTO="${4:-17}"
OUT=/tmp/d279_vw_series_${VIC}_${PROTO}.txt
grep -F '[VICTIM-WINDOW]' "$LOG" | grep -F "victim=${VIC}, proto=${PROTO}," | awk -v t0="$T0" -v t1="$T1" '
  function val(k,   s) { s=$0; sub(".*" k "=", "", s); sub(/,.*/, "", s); return s }
  {
    ts=substr($0,1,20); seq=val("seq")
    if (seq in seen) next; seen[seq]=1
    ph=(ts<t0)?"PRE":((ts>t1)?"POST":"REPLAY")
    d=val("d_pkts")+0; w=val("window_ms")+0
    print ts, "seq=" seq, ph, "d_pkts=" d, "window_ms=" w
    n[ph]++; s[ph]+=d; if (d>mx[ph]) mx[ph]=d
  }
  END {
    for (p in n) printf "RESUMEN %s ventanas=%d d_pkts_medio=%.1f d_pkts_max=%d\n", p, n[p], s[p]/n[p], mx[p] > "/dev/stderr"
  }' > "$OUT"
echo "serie en $OUT ($(wc -l < "$OUT") ventanas)"
