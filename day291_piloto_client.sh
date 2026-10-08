#!/usr/bin/env bash
# DAY291 — piloto caliente (se ejecuta en el CLIENT).
# Línea base .51 a 10 pps (2100 pkts) + ataque ntp .50 a PPS durante 90 s, que empieza a los 90 s.
# Uso: day291_piloto_client.sh PPS
set -eu
PPS=${1:?pps del ataque}
LIM=$((PPS*90))
D=/vagrant/logs/lab/day291
BASE=/vagrant/datasets/lab/benign_dns_ntp_small_5k_lab_src51.pcap
ATQ=/vagrant/datasets/lab/ntp_reflex_10k_lab.pcap
echo "pps=$PPS limit=$LIM"
echo "inicio_base $(date +%T)"
sudo tcpreplay -i eth1 --pps=10 --limit=2100 "$BASE" > "$D/piloto${PPS}_base.txt" 2>&1 &
PB=$!
sleep 90
echo "inicio_ataque $(date +%T)"
sudo tcpreplay -i eth1 --pps="$PPS" --limit="$LIM" "$ATQ" > "$D/piloto${PPS}_ataque.txt" 2>&1
echo "fin_ataque $(date +%T)"
wait "$PB"
echo "fin_base $(date +%T)"
sleep 30
echo "--- base";   grep -E 'Actual|Failed' "$D/piloto${PPS}_base.txt"   || true
echo "--- ataque"; grep -E 'Actual|Failed' "$D/piloto${PPS}_ataque.txt" || true
