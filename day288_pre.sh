#!/usr/bin/env bash
# DAY288 — antes de arrancar el pipeline: rota logs en sitio, graba vmstat y top. Uso: day288_pre.sh TAG
set -eu
TAG=${1:?tag}
D=/vagrant/logs/lab/day288
sudo truncate -s 0 /vagrant/logs/lab/sniffer.log /vagrant/logs/lab/ml-detector.log
rm -f "$D/marca.txt"
nohup vmstat -t 1 > "$D/vmstat_${TAG}.txt" 2>&1 &
disown
nohup top -b -d 2 -w 200 > "$D/top_${TAG}.txt" 2>&1 &
disown
echo "pre OK tag=$TAG"
