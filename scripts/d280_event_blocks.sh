#!/usr/bin/env bash
# DAY280 — imprime ENTEROS los bloques de log de los primeros N eventos FLOOD
# (192.168.100.50 -> 192.168.100.1 UDP) cuya ventana estampada cae en [SEQ_INI, SEQ_FIN].
# Bloque = desde "Event received: id=" hasta la línea anterior al siguiente.
# Uso: d280_event_blocks.sh SEQ_INI SEQ_FIN [N] [ddos=0|1|any]   (SEQ_INI="-" = sin filtro de seq, p.ej. logs anteriores a DAY279)
set -euo pipefail
export LC_ALL=C
LOG=${LOG:-/vagrant/logs/lab/ml-detector.log}
S0=$1; S1=$2; N=${3:-3}; WANT=${4:-any}
awk -v s0="$S0" -v s1="$S1" -v N="$N" -v want="$WANT" '
  function flush(   i) {
    if (nb==0) return
    if (flood && (s0=="-" || (sq!="" && sq+0>=s0+0 && sq+0<=s1+0)) && (want=="any" || c==want) && shown<N) {
      shown++; print "=================== evento " shown " (seq=" sq ", ddos=" (c==""?"-":c) ") ==================="
      for (i=1;i<=nb;i++) print blk[i]
    }
    nb=0; flood=0; sq=""; c=""
  }
  /Event received: id=/ { flush() }
  { blk[++nb]=$0 }
  /Flow: 192\.168\.100\.50:[0-9]+ -> 192\.168\.100\.1:[0-9]+ \(UDP\)/ { flood=1 }
  /\[VICTIM-WINDOW\]/ && !/absent/ { q=$0; sub(/.*seq=/,"",q); sub(/[, ].*/,"",q); sq=q }
  /DDoS: class=/ { match($0,/class=[01]/); c=substr($0,RSTART+6,1) }
  END { flush(); print "mostrados=" shown+0 > "/dev/stderr" }' "$LOG"
