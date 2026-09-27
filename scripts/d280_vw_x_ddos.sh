#!/usr/bin/env bash
# DAY280 — como d279_vw_x_ddos.sh, pero selecciona los eventos por el RANGO DE seq
# de la ventana estampada ([VICTIM-WINDOW] seq=), NO por la hora del log.
# Motivo (MEDIDO DAY280): el ml-detector procesa con retraso (hasta 12 min con VERBOSE),
# así que la hora del log no es la hora del tráfico. seq == win del CSV (verificado).
# FLOOD = eventos 192.168.100.50 -> 192.168.100.1 UDP (en la prueba DNS = carga dnsperf).
# Los eventos 'absent' no llevan seq: se cuentan aparte y no entran en la tabla.
# Uso: d280_vw_x_ddos.sh SEQ_INI SEQ_FIN   (rangos de scripts/d280_episodes.py)
set -euo pipefail
export LC_ALL=C
LOG=${LOG:-/vagrant/logs/lab/ml-detector.log}
S0=$1; S1=$2
grep -E 'Event received: id=|Flow: |\[VICTIM-WINDOW\]|DDoS: class=' "$LOG" | awk -v s0="$S0" -v s1="$S1" '
  function bucket(v) { return v=="-" ? "absent" : (v<1 ? "0" : (v<10 ? "1-9" : (v<50 ? "10-49" : "50+"))) }
  function flush() {
    if (id=="") return
    if (sq=="") { noseq++; return }
    if (sq+0 < s0+0 || sq+0 > s1+0) return
    n[(flood?"FLOOD":"OTHER") " " type " vpps=" bucket(vp) " ddos=" (c==""?"-":c)]++
  }
  /Event received: id=/ {
    flush(); s=$0; sub(/.*id=/,"",s); id=s
    type=(id ~ /^fast-alert-/)?"FAST":"NORM"; flood=0; c=""; vp="-"; sq=""; next
  }
  /Flow: 192\.168\.100\.50:[0-9]+ -> 192\.168\.100\.1:[0-9]+ \(UDP\)/ { flood=1; next }
  /\[VICTIM-WINDOW\]/ {
    s=$0; sub(/.*event=/,"",s); sub(/,.*/,"",s)
    if (s!=id) { mism++; next }
    if ($0 ~ /absent/) { vp="-"; next }
    q=$0; sub(/.*seq=/,"",q);       sub(/[, ].*/,"",q); sq=q
    d=$0; sub(/.*d_pkts=/,"",d);    sub(/,.*/,"",d)
    w=$0; sub(/.*window_ms=/,"",w); sub(/,.*/,"",w)
    vp=(w+0>0) ? (d*1000.0/w) : 0; next
  }
  /DDoS: class=/ { match($0,/class=[01]/); c=substr($0,RSTART+6,1); next }
  END { flush(); for (k in n) print n[k], k
        print "id_mismatch=" mism+0 "  eventos_sin_seq(absent)=" noseq+0 > "/dev/stderr" }' \
  | sort -k2,2 -k3,3 -k4,4
