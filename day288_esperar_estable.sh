#!/usr/bin/env bash
# DAY288 — espera a que el lector del kernel este estable antes de lanzar un ataque.
# Estable = en los ultimos 30 s hay >=10 sondeos y todos con window_ms <= 1200. Tope 15 min.
# Guarda la MARCA (n lineas del CSV) en /vagrant/logs/lab/day288/marca.txt para day288_post.sh.
set -eu
export LC_ALL=C
W=/vagrant/logs/lab/ddos_windows.csv
for i in $(seq 1 90); do
  NOW=$(date +%s%3N)
  read N MX < <(tail -400 "$W" | awk -F',' -v now="$NOW" '
      $2+0 >= now-30000 && !seen[$1]++ { n++; if ($3+0>mx) mx=$3+0 } END {printf "%d %d\n", n, mx}')
  echo "$(date -u +%T) sondeos_30s=$N max_window_ms=$MX"
  if [ "$N" -ge 10 ] && [ "$MX" -le 1200 ]; then
    grep -c '' "$W" > /vagrant/logs/lab/day288/marca.txt
    echo "ESTABLE. MARCA=$(cat /vagrant/logs/lab/day288/marca.txt) — ya puedes lanzar el ataque en el client"
    exit 0
  fi
  sleep 10
done
echo "NO SE ESTABILIZO EN 15 MIN — NO lanzar el ataque"
exit 1
