#!/usr/bin/env bash
# DAY292 — corrida de la batería caliente (CLIENT). Uso: day292_bateria_client.sh FAM PPS
# Base .51 -> .1 a ~10 pps durante 210 s (UDP: pcap src51; syn: subida TCP viva a 10 KB/s, sink en el defender :9000).
# Ataque/contraste .50 -> .1 a PPS durante 90 s, empezando a los 90 s. La base sigue durante el ataque.
set -eu
FAM=${1:?familia}; PPS=${2:?pps}
D=/vagrant/logs/lab/day292; L=/vagrant/datasets/lab; C=/vagrant/datasets/cicddos2019
case "$FAM" in
  ntp)        ATQ=$L/ntp_reflex_10k_lab.pcap;           N=10000; BASE=udp ;;
  dns)        ATQ=$L/dns_reflex_10k_lab.pcap;           N=10000; BASE=udp ;;
  syn)        ATQ=$L/syn_flood_10k_lab.pcap;            N=10000; BASE=tcp ;;
  udpA)       ATQ=$C/_0125_50k_lab.pcap;                N=50000; BASE=udp ;;
  udpB)       ATQ=$C/_0220_50k_lab.pcap;                N=50000; BASE=udp ;;
  bdns_small) ATQ=$L/benign_dns_ntp_small_5k_lab.pcap;  N=5000;  BASE=udp ;;
  bdns_large) ATQ=$L/benign_dns_large_5k_lab.pcap;      N=5000;  BASE=udp ;;
  *) echo "ABORTA: familia desconocida $FAM"; exit 2 ;;
esac
LIM=$((PPS*90))
[ "$LIM" -le "$N" ] || { echo "ABORTA: $FAM tiene $N paquetes y $PPS pps x 90 s pide $LIM"; exit 3; }
ip -4 addr show eth1 | grep -q 'inet 192.168.100.51/' || { echo "ABORTA: falta 192.168.100.51 en eth1"; exit 4; }
T=${FAM}_${PPS}
echo "corrida=$T base=$BASE pps=$PPS limit=$LIM"
echo "inicio_base $(date +%T)"
if [ "$BASE" = udp ]; then
  sudo tcpreplay -i eth1 --pps=10 --limit=2100 "$L/benign_dns_ntp_small_5k_lab_src51.pcap" > "$D/${T}_base.txt" 2>&1 &
else
  python3 /vagrant/scripts/d281_tcp_upload.py 192.168.100.1 9000 10 210 192.168.100.51 > "$D/${T}_base.txt" 2>&1 &
fi
PB=$!
sleep 90
echo "inicio_ataque $(date +%T)"
sudo tcpreplay -i eth1 --pps="$PPS" --limit="$LIM" "$ATQ" > "$D/${T}_ataque.txt" 2>&1
echo "fin_ataque $(date +%T)"
wait "$PB"
echo "fin_base $(date +%T)"
sleep 30
echo "--- base";   grep -E 'Actual|Failed|sent' "$D/${T}_base.txt"   || true
echo "--- ataque"; grep -E 'Actual|Failed' "$D/${T}_ataque.txt" || true
