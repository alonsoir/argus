#!/usr/bin/env bash
# d277_snap_blacklist.sh -- DAY277: instantaneas del ipset de bloqueo + contadores
# de la cadena iptables del firewall, a CSV. Correr en la VM defender. Ctrl-C para parar.
set -u
SET="${SET:-ml_defender_blacklist_test}"
CHAIN="${CHAIN:-ML_DEFENDER_TEST}"
INTERVAL="${INTERVAL:-5}"
OUT="${1:-/vagrant/logs/lab/d277_snaps_$(date +%Y%m%d_%H%M%S).csv}"
mkdir -p "$(dirname "$OUT")"
echo "ts_epoch,kind,key,v1,v2" > "$OUT"
echo "-> $OUT cada ${INTERVAL}s (set=$SET chain=$CHAIN)"
while true; do
  ts=$(date +%s)
  sudo ipset list "$SET" 2>/dev/null | awk -v ts="$ts" '
    /^Members:/ {m=1; next}
    m && NF { ip=$1; to=""; cm="";
      for (i=2;i<=NF;i++) { if ($i=="timeout") to=$(i+1); if ($i=="comment") { cm=$(i+1); gsub(/"/,"",cm) } }
      printf "%s,entry,%s,%s,%s\n", ts, ip, to, cm }' >> "$OUT"
  n=$(sudo ipset list "$SET" -t 2>/dev/null | awk -F': ' '/Number of entries/ {print $2}')
  echo "$ts,set_size,$SET,${n:-NA}," >> "$OUT"
  sudo iptables -L "$CHAIN" -v -n -x 2>/dev/null | awk -v ts="$ts" '
    NR>2 && NF { r=$3; for (i=10;i<=NF;i++) r=r" "$i; gsub(/,/,";",r);
      printf "%s,ipt_rule,%s,%s,%s\n", ts, r, $1, $2 }' >> "$OUT"
  sleep "$INTERVAL"
done
