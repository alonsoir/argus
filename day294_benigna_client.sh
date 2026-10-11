#!/usr/bin/env bash
# DAY294 — corrida BENIGNA que presiona la etapa 1 (CLIENT). Base .51 -> .1 a 10 pps durante 450 s (pcap src51).
# Tramos desde .50 -> .1, nunca vistos en entrenamiento: dnsperf real a 30 q/s (90 s), pausa 30 s, dnsperf a 100 q/s
# (90 s), pausa 30 s, subida TCP legítima 50 KB/s a :9000 (90 s; sink en el defender), pausa 30 s.
set -eu
D=/vagrant/logs/lab/day294; L=/vagrant/datasets/lab
ip -4 addr show eth1 | grep -q 'inet 192.168.100.51/' || { echo "ABORTA: falta 192.168.100.51 en eth1"; exit 4; }
command -v dnsperf > /dev/null || { echo "ABORTA: falta dnsperf"; exit 5; }
Q=/tmp/d294_consultas.txt
: > "$Q"; for i in $(seq 1 20); do echo "h$i.lab.argus A" >> "$Q"; done
echo "inicio_base $(date +%T) epoch=$(date +%s)"
sudo tcpreplay -i eth1 --pps=10 --limit=4500 "$L/benign_dns_ntp_small_5k_lab_src51.pcap" > "$D/benigna_base.txt" 2>&1 &
PB=$!
sleep 90
echo "inicio_dns30 $(date +%T) epoch=$(date +%s)"
dnsperf -s 192.168.100.1 -d "$Q" -Q 30 -l 90 > "$D/benigna_dns30.txt" 2>&1 || true
echo "fin_dns30 $(date +%T) epoch=$(date +%s)"
sleep 30
echo "inicio_dns100 $(date +%T) epoch=$(date +%s)"
dnsperf -s 192.168.100.1 -d "$Q" -Q 100 -l 90 > "$D/benigna_dns100.txt" 2>&1 || true
echo "fin_dns100 $(date +%T) epoch=$(date +%s)"
sleep 30
echo "inicio_tcp50 $(date +%T) epoch=$(date +%s)"
python3 /vagrant/scripts/d281_tcp_upload.py 192.168.100.1 9000 50 90 192.168.100.50 > "$D/benigna_tcp50.txt" 2>&1 || true
echo "fin_tcp50 $(date +%T) epoch=$(date +%s)"
wait "$PB"
echo "fin_base $(date +%T) epoch=$(date +%s)"
echo "--- base";   grep -E 'Actual|Failed' "$D/benigna_base.txt" || true
echo "--- dns30";  grep -E 'Queries (sent|completed|lost)' "$D/benigna_dns30.txt" || true
echo "--- dns100"; grep -E 'Queries (sent|completed|lost)' "$D/benigna_dns100.txt" || true
echo "--- tcp50";  tail -n 3 "$D/benigna_tcp50.txt" || true
