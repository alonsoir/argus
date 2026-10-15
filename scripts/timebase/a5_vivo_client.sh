#!/usr/bin/env bash
# DAY298 1.a A5 en vivo: base .51 a 10 pps continua; a los 600 s, ataque ntp .50 a 60 pps durante 1050 s;
# la base sigue 60 s tras el ataque. Pcaps sin 5-tuplas repetidas (MANIFEST DAY298). Mismo escenario que
# A5 offline (base 10, ataque 60, 600 ventanas de base previas). Se usa igual antes y despues del arreglo.
# Uso: DIA=dayNNN a5_vivo_client.sh NOMBRE   (logs en /vagrant/logs/lab/$DIA/NOMBRE/)
set -eu
N=${1:?nombre}
DIA=${DIA:-day298}
[[ "$DIA" =~ ^day[0-9]{3}$ ]] || { echo "DIA invalido: '$DIA' (formato dayNNN)"; exit 2; }
D=/vagrant/logs/lab/$DIA/$N
L=/vagrant/datasets/lab
BASE=$L/benign_dns_ntp_17k_disjunto_src51.pcap
ATQ=$L/ntp_reflex_63k_disjunto_lab.pcap
mkdir -p "$D"
ip -4 addr show dev eth1 | grep -q '192.168.100.51/' || { echo "ABORTA: falta el alias 192.168.100.51 en eth1 (sudo ip addr add 192.168.100.51/24 dev eth1)"; exit 1; }
for f in "$BASE" "$ATQ"; do [ -f "$f" ] || { echo "ABORTA: no existe $f"; exit 1; }; done
echo "inicio_base $(date +%s.%N)" | tee "$D/tiempos.txt"
sudo tcpreplay -i eth1 --pps=10 --limit=17100 "$BASE" > "$D/base.txt" 2>&1 &
PB=$!
sleep 600
echo "inicio_ataque $(date +%s.%N)" | tee -a "$D/tiempos.txt"
sudo tcpreplay -i eth1 --pps=60 --limit=63000 "$ATQ" > "$D/ataque.txt" 2>&1
echo "fin_ataque $(date +%s.%N)" | tee -a "$D/tiempos.txt"
wait "$PB"
echo "fin_base $(date +%s.%N)" | tee -a "$D/tiempos.txt"
echo "--- base";   grep -E 'Actual|Failed' "$D/base.txt"
echo "--- ataque"; grep -E 'Actual|Failed' "$D/ataque.txt"
