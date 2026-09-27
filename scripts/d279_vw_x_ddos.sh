#!/usr/bin/env bash
# Cruza, POR EVENTO, la ventana por victima ([VICTIM-WINDOW]) con el veredicto de la cabeza
# DDoS. vpps = d_pkts*1000/window_ms de la victima del evento (ultima ventana cerrada).
# Uso: d279_vw_x_ddos.sh "HH:MM:SS" "HH:MM:SS"   (inicio/fin del replay)
set -euo pipefail
export LC_ALL=C
LOG=/vagrant/logs/lab/ml-detector.log
DAY=$(date +%F)
T0="[$DAY $1"; T1="[$DAY $2"
OUT=/tmp/d279_vw_x_ddos.txt
grep -E 'Event received: id=|Flow: |\[VICTIM-WINDOW\]|DDoS: class=' "$LOG" | awk -v t0="$T0" -v t1="$T1" '
  function bucket(v) { return v=="-" ? "absent" : (v<1 ? "0" : (v<10 ? "1-9" : (v<50 ? "10-49" : "50+"))) }
  function flush() {
    if (id=="" || ts<t0 || ts>t1) return
    n[(flood?"FLOOD":"OTHER") " " type " vpps=" bucket(vp) " ddos=" (c==""?"-":c)]++
  }
  /Event received: id=/ {
    flush(); ts=substr($0,1,20); s=$0; sub(/.*id=/,"",s); id=s
    type=(id ~ /^fast-alert-/)?"FAST":"NORM"; flood=0; c=""; vp="-"; next
  }
  /Flow: 192\.168\.100\.50:[0-9]+ -> 192\.168\.100\.1:[0-9]+ \(UDP\)/ { flood=1; next }
  /\[VICTIM-WINDOW\]/ {
    s=$0; sub(/.*event=/,"",s); sub(/,.*/,"",s)
    if (s!=id) { mism++; next }
    if ($0 ~ /absent/) { vp="-"; next }
    d=$0; sub(/.*d_pkts=/,"",d);    sub(/,.*/,"",d)
    w=$0; sub(/.*window_ms=/,"",w); sub(/,.*/,"",w)
    vp=(w+0>0) ? (d*1000.0/w) : 0; next
  }
  /DDoS: class=/ { match($0,/class=[01]/); c=substr($0,RSTART+6,1); next }
  END { flush(); for (k in n) print n[k], k; print "id_mismatch=" mism+0 > "/dev/stderr" }' \
  | sort -k2,2 -k3,3 -k4,4 > "$OUT"
cat "$OUT"
