#!/usr/bin/env bash
# d278_snap_blacklist.sh -- DAY278: instantaneas del ipset de bloqueo + contadores iptables, a CSV.
# Cambios vs d277: CHAIN por defecto INPUT (el DROP vive en INPUT, ML_DEFENDER_TEST tiene 0 refs),
# comment completo (antes solo 1er token), packets por entrada (set con 'counters').
# entry:    ts,entry,ip,timeout,packets,comment
# set_size: ts,set_size,set,n,,
# ipt_rule: ts,ipt_rule,regla,pkts,bytes,
set -u
SET="${SET:-ml_defender_blacklist_test}"
CHAIN="${CHAIN:-INPUT}"
INTERVAL="${INTERVAL:-5}"
OUT="${1:-/vagrant/logs/lab/d278_snaps_$(date +%Y%m%d_%H%M%S).csv}"
mkdir -p "$(dirname "$OUT")"
echo "ts_epoch,kind,key,v1,v2,v3" > "$OUT"
echo "-> $OUT cada ${INTERVAL}s (set=$SET chain=$CHAIN)"
while true; do
  ts=$(date +%s)
  sudo ipset list "$SET" 2>/dev/null | awk -v ts="$ts" '
    /^Members:/ {m=1; next}
    m && NF { ip=$1; to=""; pk=""; cm="";
      for (i=2;i<=NF;i++) { if ($i=="timeout") to=$(i+1); if ($i=="packets") pk=$(i+1) }
      if (match($0, /comment "[^"]*"/)) { cm=substr($0, RSTART+9, RLENGTH-10); gsub(/,/,";",cm) }
      printf "%s,entry,%s,%s,%s,%s\n", ts, ip, to, pk, cm }' >> "$OUT"
  n=$(sudo ipset list "$SET" -t 2>/dev/null | awk -F': ' '/Number of entries/ {print $2}')
  echo "$ts,set_size,$SET,${n:-NA},," >> "$OUT"
  sudo iptables -L "$CHAIN" -v -n -x 2>/dev/null | awk -v ts="$ts" '
    NR>2 && NF { r=$3; for (i=10;i<=NF;i++) r=r" "$i; gsub(/,/,";",r);
      printf "%s,ipt_rule,%s,%s,%s,\n", ts, r, $1, $2 }' >> "$OUT"
  sleep "$INTERVAL"
done
