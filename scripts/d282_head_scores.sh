#!/usr/bin/env bash
# d282_head_scores.sh [LOG] [FILTRO] — cuadre [HEAD-SCORES] vs [DUAL-SCORE] y coherencia clase/puntuacion.
# FILTRO: regex (grep -E) para incluir; '!regex' para excluir. Por defecto, todo.
set -euo pipefail
export LC_ALL=C
LOG="${1:-/vagrant/logs/lab/ml-detector.log}"
FILTRO="${2:-.}"
echo "DUAL-SCORE : $(grep -c '\[DUAL-SCORE\]' "$LOG" || true)"
echo "HEAD-SCORES: $(grep -c '\[HEAD-SCORES\]' "$LOG" || true)"
echo "FILTRO     : $FILTRO"
filtra() { if [[ "$FILTRO" == !* ]]; then grep -vE "${FILTRO#!}" || true; else grep -E "$FILTRO" || true; fi; }
{ grep '\[HEAD-SCORES\]' "$LOG" || true; } | filtra | awk '
function val(k,  s){ if (match($0, k "=[^,]*")) return substr($0, RSTART+length(k)+1, RLENGTH-length(k)-1); return "" }
BEGIN{ split("ddos ransom traffic internal", H, " ") }
{
  n++; gate[val("gate")]++; cat[val("cat")]++
  kind[(index($0, "event=fast-alert-") > 0) ? "FAST" : "NORM"]++
  for (i = 1; i <= 4; i++) { h = H[i]; v = val(h)
    if (v == "na") { na[h]++; continue }
    split(v, a, ":"); c = a[1] + 0; p = a[2] + 0; run[h]++; cls[h, c]++
    if (h == "traffic") { if (p < 0.5) incoh[h]++ }
    else if ((c == 1 && p < 0.5) || (c == 0 && p >= 0.5)) incoh[h]++
  }
}
END{
  printf "eventos=%d FAST=%d NORM=%d gate0=%d gate1=%d\n", n, kind["FAST"], kind["NORM"], gate["0"], gate["1"]
  for (i = 1; i <= 4; i++) { h = H[i]
    printf "%-8s na=%d evaluada=%d class0=%d class1=%d %s=%d\n", h, na[h]+0, run[h]+0, cls[h,0]+0, cls[h,1]+0,
           (h == "traffic" ? "p<0.5" : "incoherentes(clase vs p>=0.5)"), incoh[h]+0 }
  for (c in cat) printf "cat=%s %d\n", c, cat[c]
}'
