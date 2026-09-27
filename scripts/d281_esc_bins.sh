#!/usr/bin/env bash
# Clase DDoS x tramo de escalation x tipo (FAST/NORM), filtrado por seq de VICTIM-WINDOW.
# Uso: d281_esc_bins.sh LOG [SEQ_LO] [SEQ_HI]   (eventos sin VICTIM-WINDOW tienen seq=-1)
set -euo pipefail
LOG=${1:?log}
LO=${2:--1}
HI=${3:-999999999}
LC_ALL=C awk -v lo="$LO" -v hi="$HI" '
/Event received: id=/ { id=$0; sub(/.*id=/,"",id); typ=(id ~ /^fast-alert-/)?"FAST":"NORM"; seq=-1; esc=""; next }
/\[VICTIM-WINDOW\]/  { s=$0; sub(/.*seq=/,"",s); sub(/,.*/,"",s); seq=s+0; next }
/DDoS Features:/     { e=$0; sub(/.*escalation=/,"",e); sub(/,.*/,"",e); esc=e; next }
/DDoS: class=/ {
  if (esc=="") next
  if (seq<lo || seq>hi) { esc=""; next }
  c=$0; sub(/.*class=/,"",c); c=substr(c,1,1); v=esc+0
  if (v==0) b="a:0.000"; else if (v<0.0038) b="b:0.001-0.003"; else if (v<0.0134) b="c:0.004-0.013"; else b="d:>=0.014"
  n[typ" "b" class="c]++; esc=""; next }
END { for (k in n) printf "%s %d\n", k, n[k] }' "$LOG" | LC_ALL=C sort
