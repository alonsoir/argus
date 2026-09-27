#!/usr/bin/env bash
# Flood (.50->.1 UDP) vs resto, por tipo de evento (fast-alert/normal), clase DDoS,
# final>=0.5 y veredicto final. Solo ventana REPLAY.
set -euo pipefail
awk -v r0="[2026-09-24 03:12:49" -v r1="[2026-09-24 03:21:09" '
  function flush() {
    if (id=="" || ts<r0 || ts>r1) return
    key=(flood?"FLOOD":"OTHER")" "type" ddos="(c==""?"-":c)" final>=0.5="fin" verdict="(v==""?"-":v)
    n[key]++
  }
  /Event received: id=/ {
    flush()
    ts=substr($0,1,20); s=$0; sub(/.*id=/,"",s); id=s
    type=(id ~ /^fast-alert-/)?"FAST":"NORM"
    flood=0; c=""; fin="-"; v=""; next
  }
  /Flow: 192\.168\.100\.50:[0-9]+ -> 192\.168\.100\.1:[0-9]+ \(UDP\)/ { flood=1; next }
  /DUAL-SCORE/ { match($0,/final=[0-9.]+/); f=substr($0,RSTART+6,RLENGTH-6)+0; fin=(f>=0.5)?"Y":"N"; next }
  /DDoS: class=/ { match($0,/class=[01]/); c=substr($0,RSTART+6,1); next }
  /: event=/ && !/DUAL-SCORE/ && !/Event received/ {
    s=$0; sub(/: event=.*/,"",s); m=split(s,w," "); v=w[m]; next
  }
  END { flush(); for (k in n) print n[k], k }' /tmp/d279_win2.txt | sort -k2 > /tmp/d279_flood_by_evtype.txt
cat /tmp/d279_flood_by_evtype.txt
