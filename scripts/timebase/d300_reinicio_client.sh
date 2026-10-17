#!/usr/bin/env bash
# DAY300 E2E del reinicio: base .51 a 10 pps durante 510 s (5100 pkts del pcap disjunto de 17k); a los 90 s,
# ataque ntp .50 a 60 pps durante 360 s (21600 pkts del pcap disjunto de 63k); despues 60 s de base.
# Escribe marcas epoch en stdout (el orquestador las lee).
set -eu
BASE=/vagrant/datasets/lab/benign_dns_ntp_17k_disjunto_src51.pcap
ATQ=/vagrant/datasets/lab/ntp_reflex_63k_disjunto_lab.pcap
echo "inicio_base $(date +%s.%N)"
sudo tcpreplay -i eth1 --pps=10 --limit=5100 "$BASE" > /tmp/d300_base.txt 2>&1 &
PB=$!
sleep 90
echo "inicio_ataque $(date +%s.%N)"
sudo tcpreplay -i eth1 --pps=60 --limit=21600 "$ATQ" > /tmp/d300_atq.txt 2>&1
echo "fin_ataque $(date +%s.%N)"
wait "$PB"
echo "fin_base $(date +%s.%N)"
echo "--- base";   grep -E 'Actual|Failed' /tmp/d300_base.txt || true
echo "--- ataque"; grep -E 'Actual|Failed' /tmp/d300_atq.txt  || true
