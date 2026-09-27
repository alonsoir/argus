#!/usr/bin/env bash
# DAY280 — carga DNS BENIGNA contra el resolver del lab (unbound en 192.168.100.1).
# Niveles de qps por separado, con pausa entre medias para que el CSV los separe en episodios.
# Uso (en el client): LEVELS="50 100 200" DUR=120 PAUSE=60 scripts/d280_dns_load.sh
set -uo pipefail
OUT=/vagrant/logs/lab
QF=$OUT/d280_dns_queries.txt
TIMES=$OUT/d280_dns_times.txt
LEVELS=${LEVELS:-50 100 200}
DUR=${DUR:-120}
PAUSE=${PAUSE:-60}
for i in $(seq 1 20); do echo "h$i.lab.argus A"; done > "$QF"
got=$(dig @192.168.100.1 h1.lab.argus A +short +time=2 +tries=1)
[ "$got" = "192.168.100.201" ] || { echo "ABORTO: el resolver no responde bien (h1 -> '$got')"; exit 1; }
: > "$TIMES"
for q in $LEVELS; do
  echo "INICIO qps=$q $(date +%T)" | tee -a "$TIMES"
  dnsperf -s 192.168.100.1 -d "$QF" -Q "$q" -l "$DUR" -c "${CLIENTS:-4}" > "$OUT/d280_dnsperf_q${q}.txt" 2>&1
  echo "FIN qps=$q $(date +%T)" | tee -a "$TIMES"
  grep -E 'Queries sent|Queries completed|Queries lost|Queries per second' "$OUT/d280_dnsperf_q${q}.txt"
  sleep "$PAUSE"
done
echo "HECHO. Tiempos en $TIMES"
