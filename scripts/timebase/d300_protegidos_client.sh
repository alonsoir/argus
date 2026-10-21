#!/usr/bin/env bash
# DAY300 E2E de rangos protegidos: base .51 a 10 pps durante 330 s; a los 90 s, durante 180 s, ataque NTP
# desde .50 (no protegido) a 60 pps y desde .61 (protegido como intranet en el lab) a 30 pps, a la vez.
set -eu
BASE=/vagrant/datasets/lab/benign_dns_ntp_17k_disjunto_src51.pcap
A50=/vagrant/datasets/lab/ntp_reflex_63k_disjunto_lab.pcap
A61=/vagrant/datasets/lab/ntp_reflex_10k_lab_src61.pcap
echo "inicio_base $(date +%s.%N)"
sudo tcpreplay -i eth1 --pps=10 --limit=3300 "$BASE" > /tmp/d300p_base.txt 2>&1 &
PB=$!
sleep 90
echo "inicio_ataque $(date +%s.%N)"
sudo tcpreplay -i eth1 --pps=30 --limit=5400 "$A61" > /tmp/d300p_a61.txt 2>&1 &
P61=$!
sudo tcpreplay -i eth1 --pps=60 --limit=10800 "$A50" > /tmp/d300p_a50.txt 2>&1
wait "$P61"
echo "fin_ataque $(date +%s.%N)"
wait "$PB"
echo "fin_base $(date +%s.%N)"
echo "--- base"; grep -E 'Actual|Failed' /tmp/d300p_base.txt || true
echo "--- a50";  grep -E 'Actual|Failed' /tmp/d300p_a50.txt  || true
echo "--- a61";  grep -E 'Actual|Failed' /tmp/d300p_a61.txt  || true
