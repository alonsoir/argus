#!/usr/bin/env bash
# DAY287 paso 2.1 — ¿dónde queda serializado ddos_embedded v2 sin VERBOSE?
set -u
export LC_ALL=C
cd /vagrant || exit 1
OUT=/vagrant/logs/lab/day287
mkdir -p "$OUT"

git log --oneline -3 > "$OUT/00_head.txt" 2>&1

# Quién lee ddos_embedded en el ml-detector (sin generados)
git grep -n 'ddos_embedded' -- 'ml-detector/' ':!*.pb.cc' ':!*.pb.h' \
  > "$OUT/01_ddos_embedded_mldet.txt" 2>&1

# Dónde aparecen los nombres de los campos v2 en todo el repo (sin generados)
git grep -nE 'mean_packet_size|reflection_signature|flow_packet_count|victim_rate_ratio|victim_pps' \
  -- ':!*.pb.cc' ':!*.pb.h' > "$OUT/02_campos_v2.txt" 2>&1

# Rasgos DDoS dentro de los escritores CSV / RAG del ml-detector
git grep -nE 'syn_ack_ratio|packet_size_entropy|flow_completion_rate|geographical_concentration' \
  -- 'ml-detector/src/' 'ml-detector/include/' ':!*.pb.cc' ':!*.pb.h' \
  > "$OUT/03_ddos_en_mldet.txt" 2>&1

# Umbral y ruta del CSV
git grep -nE 'min_score_threshold|base_dir|csv_writer' -- 'ml-detector/config/' \
  > "$OUT/04_umbral_csv.txt" 2>&1

# Estado real del CSV en disco
ls -l /vagrant/logs/ml-detector/events/ > "$OUT/05_csv_ls.txt" 2>&1
F=$(ls -1t /vagrant/logs/ml-detector/events/*.csv 2>/dev/null | head -1)
if [ -n "$F" ]; then
  echo "fichero=$F filas=$(wc -l < "$F")" > "$OUT/06_csv_nf.txt"
  tail -n 20000 "$F" | awk -F',' '{print NF}' | sort -n | uniq -c >> "$OUT/06_csv_nf.txt"
else
  echo "sin CSV" > "$OUT/06_csv_nf.txt"
fi

wc -l "$OUT"/*.txt
