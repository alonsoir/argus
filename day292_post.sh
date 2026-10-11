#!/usr/bin/env bash
# DAY292 — cierre de una corrida de la batería caliente (DEFENDER). Uso: day292_post.sh FAM PPS
# Mide PRIMERO; registra en runs_caliente.tsv solo si la medida encuentra el ataque.
set -eu
FAM=${1:?familia}; PPS=${2:?pps}
D=/vagrant/logs/lab/day292
F=$(ls -t /vagrant/logs/lab/ddos_dataset/ddos_dataset_*.csv | head -1)
grep -q "$(basename "$F")" "$D/runs_caliente.tsv" 2>/dev/null && { echo "ABORTA: $(basename "$F") ya registrado"; exit 2; }
M="$D/${FAM}_${PPS}_medida.txt"
if ! python3 /vagrant/day292_medir.py "$F" > "$M" 2>&1; then
  cat "$M"; echo "ABORTA: medida fallida, NO registrado ($(basename "$F"))"; exit 3
fi
printf '%s\t%s\t%s\n' "$FAM" "$PPS" "$(basename "$F")" >> "$D/runs_caliente.tsv"
grep -E '^fichero|^event_kind|^ataque:' "$M"
grep -E '^ +[18] +(ATQ|BASE)' "$M"
sed -n '/durante el ataque/,$p' "$M"
echo "REGISTRADO: $FAM $PPS $(basename "$F")"
