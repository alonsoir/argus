#!/usr/bin/env bash
# DAY306 — Segunda lectura para DEBT-DDOS-V1-RETIRE-001. SOLO LECTURA.
# Saca: (A) un tar con los ficheros que faltan por leer enteros, (B) los cruces
# pendientes y (C) para cada fichero candidato a borrar, si lo nombra el paper y
# quién más lo usa. Todo con git grep / git archive (solo ficheros trackeados).
# Ejecutar en el Mac desde cualquier punto del repo.
set -u
export LC_ALL=C
cd "$(git rev-parse --show-toplevel)" || exit 1
OUT=/tmp/d306_lectura2
rm -rf "$OUT"; mkdir -p "$OUT"
X=(':(exclude)docs' ':(exclude)site' ':(exclude)*.md' ':(exclude)*.pb.cc' ':(exclude)*.pb.h' ':(exclude)*_pb2.py')

# ---------- (A) ficheros a leer enteros ----------
git archive --format=tar.gz -o "$OUT/ficheros2.tar.gz" HEAD \
  ml-detector/tests/integration/test_csv_event_writer.cpp \
  ml-detector/tests/integration/test_csv_feature_extraction.cpp \
  ml-detector/tests/unit/test_rag_logger_artifact_save.cpp \
  ml-detector/include/csv_event_writer.hpp \
  ml-detector/include/ddos_dataset_writer.hpp \
  sniffer/tests/test_ddos_flow_snap.cpp \
  sniffer/config/sniffer.json \
  tools/generate_synthetic_events.cpp \
  tools/synthetic_sniffer_injector.cpp \
  protobuf/generate.sh

{
# ---------- (B) cruces ----------
echo "== HEAD $(git rev-parse --short HEAD)  rama $(git rev-parse --abbrev-ref HEAD)"
echo "== B1 quien carga xgboost_ddos / metadata level2 ddos";  git grep -I -n -E 'xgboost_ddos|level2_ddos_metadata|models/production/level2' -- . "${X[@]}"
echo "== B2 quien parsea [HEADS] ddos_v1= / [DETECCIONES] ddos= / [HEAD-SCORES] ddos="
git grep -I -n -E 'ddos_v1=|DETECCIONES|HEAD-SCORES' -- . "${X[@]}" ':(exclude)ml-detector/src'
echo "== B3 RANDOM_FOREST_DDOS";                                git grep -I -n 'RANDOM_FOREST_DDOS' -- . "${X[@]}"
echo "== B4 level2_specialized_predictions";                    git grep -I -n 'level2_specialized_predictions' -- . "${X[@]}"
echo "== B5 se construyen las herramientas sinteticas";         git grep -I -n -E 'generate_synthetic_events|synthetic_sniffer_injector' -- '*CMakeLists.txt' Makefile '*.mk'
echo "== B6 backups trackeados";                                git ls-files | grep -E '\.backup$|\.bak|\.v1\.0$'
echo "== B7 tarea proto del Makefile y que ficheros escribe";   git grep -n -E '^proto[a-z-]*:|generate\.sh|network_security\.pb' -- Makefile
echo "== B8 old_ddos_prob/old_ddos_class: quien lee el dataset DDoS v2"
git grep -I -n -E 'old_ddos_(prob|class)' -- . "${X[@]}"
echo "== B9 fuentes del paper trackeadas";                     git ls-files | grep -E '\.(tex|bib)$'
echo "== B10 bloque ddos PLANNED de sniffer.json: quien lee 'activation_thresholds' / 'syn_flood_rate'"
git grep -I -n -E 'activation_thresholds|syn_flood_rate|udp_flood_rate|icmp_flood_rate' -- . "${X[@]}" ':(exclude)*.json'

# ---------- (C) candidatos a borrar: ¿lo nombra el paper? ¿quien mas lo usa? ----------
echo "== C candidatos  (fichero | paper | usado_por, sin docs/site/md)"
git ls-files ml-training/scripts/ddos_detection ml-training/scripts/ddos_template.txt \
             ml-training/requirements-ddos-pinned.txt \
             ml-detector/models/production/level2/ddos ml-detector/models/metadata/level2_ddos_metadata.json \
             ml-training/outputs/metadata ml-training/outputs/plots \
  | grep -i ddos | while read -r f; do
    b=$(basename "$f")
    p=$(git grep -l -F "$b" -- '*.tex' 'paper-artifacts' 'README.md' 'docs/ml-heads/paper_*' 2>/dev/null | tr '\n' ' ')
    u=$(git grep -l -F "$b" -- . "${X[@]}" 2>/dev/null | grep -v -x -F "$f" | tr '\n' ' ')
    echo "$f | paper: ${p:--} | usado_por: ${u:--}"
  done
echo "== FIN"
} > "$OUT/cruces2.txt" 2>&1

ls -l "$OUT"
