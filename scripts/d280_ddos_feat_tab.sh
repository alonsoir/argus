#!/usr/bin/env bash
# DAY280 — tabula, para eventos FLOOD (192.168.100.50 -> 192.168.100.1 UDP), el veredicto
# de la cabeza DDoS contra la línea "DDoS Features:" completa (+ puerto destino y duración).
# Cuenta combinaciones y muestra las TOP por clase. Rango de seq opcional ("-" = sin filtro).
# Uso: d280_ddos_feat_tab.sh SEQ_INI SEQ_FIN [top]
set -euo pipefail
export LC_ALL=C
LOG=${LOG:-/vagrant/logs/lab/ml-detector.log}
S0=$1; S1=$2; TOP=${3:-12}
awk -v s0="$S0" -v s1="$S1" '
  function flush() {
    if (id!="" && flood && (s0=="-" || (sq!="" && sq+0>=s0+0 && sq+0<=s1+0)) && c!="")
      n["class=" c " | dport=" dp " dur=" du " | " f]++
    id=""; flood=0; sq=""; c=""; f="(sin linea de features)"; dp="?"; du="?"
  }
  /Event received: id=/ { flush(); id=1; next }
  /Flow: 192\.168\.100\.50:[0-9]+ -> 192\.168\.100\.1:[0-9]+ \(UDP\)/ {
    flood=1; s=$0; sub(/.*192\.168\.100\.1:/,"",s); sub(/ .*/,"",s); dp=(s+0>=1024?"alto":s); next }
  /  Duration: / { s=$0; sub(/.*Duration: /,"",s); sub(/s.*/,"",s); du=(s+0<1?"<1s":(s+0<10?"1-10s":">=10s")); next }
  /\[VICTIM-WINDOW\]/ && !/absent/ { q=$0; sub(/.*seq=/,"",q); sub(/[, ].*/,"",q); sq=q; next }
  /DDoS Features:/ { s=$0; sub(/.*DDoS Features: /,"",s); gsub(/entropy=[0-9.]+/,"entropy=*",s); f=s; next }
  /DDoS: class=/ { match($0,/class=[01]/); c=substr($0,RSTART+6,1); next }
  END { flush(); for (k in n) print n[k] "\t" k }' "$LOG" | sort -t$'\t' -k1,1nr > /tmp/d280_feat_tab.$$
echo "== class=1 (dispara)"; grep -P '\tclass=1' /tmp/d280_feat_tab.$$ | head -n "$TOP" || echo "(ninguno)"
echo "== class=0 (no dispara)"; grep -P '\tclass=0' /tmp/d280_feat_tab.$$ | head -n "$TOP" || echo "(ninguno)"
rm -f /tmp/d280_feat_tab.$$
