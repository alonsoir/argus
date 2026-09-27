#!/usr/bin/env bash
# Clase DDoS x tramo de escalation x tipo, filtrado por regex sobre la linea "Flow:". Uso: d281_esc_bins_flow.sh LOG REGEX
set -euo pipefail
LOG=${1:?log}
RE=${2:?regex}
LC_ALL=C awk -v re="$RE" '
/Event received: id=/ { id=$0; sub(/.*id=/,"",id); typ=(id ~ /^fast-alert-/)?"FAST":"NORM"; ok=0; esc=""; next }
/  Flow: /            { ok=($0 ~ re); next }
/DDoS Features:/     { e=$0; sub(/.*escalation=/,"",e); sub(/,.*/,"",e); esc=e; next }
/DDoS: class=/ {
  if (esc=="" || !ok) { esc=""; next }
  c=$0; sub(/.*class=/,"",c); c=substr(c,1,1); v=esc+0
  if (v==0) b="a:0.000"; else if (v<0.0038) b="b:0.001-0.003"; else if (v<0.0134) b="c:0.004-0.013"; else b="d:>=0.014"
  n[typ" "b" class="c]++; esc=""; next }
END { for (k in n) printf "%s %d\n", k, n[k] }' "$LOG" | LC_ALL=C sort
