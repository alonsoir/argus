#!/usr/bin/env bash
# Veredictos de la cabeza DDoS por (fase, src, dst, proto) + histograma de ddos_prob.
set -euo pipefail
WIN=/tmp/d279_win.txt
OUT1=/tmp/d279_ddos_by_flowkey.txt
OUT2=/tmp/d279_ddos_prob_hist.txt
awk -v r0="[2026-09-24 03:12:49" -v r1="[2026-09-24 03:21:09" -v o1="$OUT1" -v o2="$OUT2" '
  /Flow: / {
    if (pending) lost++
    ts=substr($0,1,20)
    s=$0; sub(/.*Flow: /,"",s)            # SRC:SP -> DST:DP (PROTO)
    split(s,p," "); split(p[1],a,":"); split(p[3],b,":")
    src=a[1]; dst=b[1]; proto=p[4]; gsub(/[()]/,"",proto)
    phase=(ts<r0)?"PRE":((ts>r1)?"POST":"REPLAY")
    pending=1; next
  }
  /DDoS: class=/ {
    if (!pending) { orphan++; next }
    match($0,/class=[01]/);            c=substr($0,RSTART+6,1)
    match($0,/ddos_prob=[0-9.]+/);     pr=substr($0,RSTART+10,RLENGTH-10)
    k[phase" "src" "dst" "proto" class="c]++
    h[phase" "proto" prob="pr" class="c]++
    pending=0
  }
  END {
    for (x in k) print k[x], x > o1
    for (x in h) print h[x], x > o2
    print "Flow sin veredicto=" lost+0 "  veredicto sin Flow=" orphan+0
  }' "$WIN"
sort -k2,2 -k1,1nr -o "$OUT1" "$OUT1"
sort -k2,2 -k1,1nr -o "$OUT2" "$OUT2"
wc -l "$OUT1" "$OUT2"
