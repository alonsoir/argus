#!/usr/bin/env bash
# DAY280 — líneas [VICTIM-WINDOW] en crudo para UNA víctima entre dos horas del log.
# Agrupa por seq (ventana estampada): nº de eventos, d_pkts, window_ms, vpps, rango de age_ms.
# Uso: scripts/d280_vw_raw.sh LOG HH:MM:SS HH:MM:SS [victim]
set -euo pipefail
export LC_ALL=C
LOG=$1; T0=$2; T1=$3; V=${4:-192.168.100.1}
grep -F '[VICTIM-WINDOW]' "$LOG" | awk -v T0="$T0" -v T1="$T1" -v V="$V" '
function f(k,   r){ if (match($0, k "=[^, ]+")) { r=substr($0,RSTART+length(k)+1,RLENGTH-length(k)-1); return r } return "" }
{ if (!match($0,/[0-9][0-9]:[0-9][0-9]:[0-9][0-9]/)) next
  t=substr($0,RSTART,8); if (t<T0 || t>T1) next
  if ($0 ~ /absent/) { absent++; next }
  if (f("victim")!=V) { other++; next }
  s=f("seq"); dp=f("d_pkts")+0; wm=f("window_ms")+0; ag=f("age_ms")+0
  n++; if(!(s in cnt)){ ord[++ns]=s; dpk[s]=dp; wms[s]=wm; amin[s]=ag; amax[s]=ag }
  cnt[s]++; if(ag<amin[s]) amin[s]=ag; if(ag>amax[s]) amax[s]=ag
  if(dp!=dpk[s]) incons[s]=1 }
END{
  printf "eventos victim=%s: %d  | otras víctimas: %d  | absent: %d  | ventanas (seq) distintas: %d\n", V, n, other, absent, ns
  print "seq  eventos  d_pkts  window_ms  vpps  age_min  age_max  (d_pkts distinto en el mismo seq = !!)"
  for(i=1;i<=ns;i++){ s=ord[i]; v=(wms[s]>0? dpk[s]*1000/wms[s] : -1)
    printf "%s  %d  %d  %d  %.1f  %d  %d %s\n", s, cnt[s], dpk[s], wms[s], v, amin[s], amax[s], (incons[s]?"!!":"") }
}'
