#!/usr/bin/env bash
# DAY297 D15 A2 (CLIENT): base .51 a 10 pps (2100 paquetes) y, a los 90 s, ataque .50 a PPS y gemelo .61 a GPPS
# (mismos paquetes que el ataque, otra IP origen) a la vez, durante 90 s. Uso: bash a2_gemelo_client.sh PPS GPPS
set -eu
PPS=${1:?pps del ataque .50}
GPPS=${2:?pps del gemelo .61}
LIM=$((PPS * 90))
GLIM=$((GPPS * 90))
D=/vagrant/logs/lab/day297
mkdir -p "$D"
BASE=/vagrant/datasets/lab/benign_dns_ntp_small_5k_lab_src51.pcap
ATQ=/vagrant/datasets/lab/ntp_reflex_10k_lab.pcap
GEM=/vagrant/datasets/lab/ntp_reflex_10k_lab_src61.pcap
P="$D/gem${PPS}_${GPPS}"
echo "pps=$PPS limit=$LIM gemelo_pps=$GPPS gemelo_limit=$GLIM"
echo "inicio_base $(date +%T.%N)"
sudo tcpreplay -i eth1 --pps=10 --limit=2100 "$BASE" > "${P}_base.txt" 2>&1 &
PB=$!
sleep 90
echo "inicio_ataque_y_gemelo $(date +%T.%N)"
sudo tcpreplay -i eth1 --pps="$GPPS" --limit="$GLIM" "$GEM" > "${P}_gemelo.txt" 2>&1 &
PG=$!
sudo tcpreplay -i eth1 --pps="$PPS" --limit="$LIM" "$ATQ" > "${P}_ataque.txt" 2>&1
echo "fin_ataque $(date +%T.%N)"
wait "$PG"
echo "fin_gemelo $(date +%T.%N)"
wait "$PB"
echo "fin_base $(date +%T.%N)"
for f in base ataque gemelo; do echo "--- $f"; grep -E 'Actual|Failed' "${P}_$f.txt" || true; done
