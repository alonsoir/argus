#!/usr/bin/env bash
# DAY303 K3: a que objetivo pertenece cada linea de K2 y quien llama a esos objetivos
set -u
objetivo() { awk -v n="$1" 'NR<=n && /^[A-Za-z0-9_.+-]+:/ {t=$1} NR==n {sub(":","",t); print t; exit}' Makefile; }
for n in 1205 1479 1510 1513 1536 2408 2412 2418 2935 2939 2962 3241 3243 2311; do
  t=$(objetivo "$n"); echo "linea $n -> $t"
done | sort -t'>' -k2 -u > /tmp/d303_k3_obj.txt
cat /tmp/d303_k3_obj.txt
echo "===== K3 quien llama a cada objetivo (MAKE o prerequisito) ====="
for t in $(awk -F'-> ' '{print $2}' /tmp/d303_k3_obj.txt | sort -u); do
  echo "--- $t"
  git grep -n -E "MAKE\)? $t( |$)|^[A-Za-z0-9_.+-]+:.* $t( |$)" -- Makefile | cut -c1-150 | head -6
done
echo "===== K3 cabeceras de bootstrap, pipeline-build, test-all ====="
git grep -n -E '^(bootstrap|pipeline-build|test-all|rag-build|rag):' -- Makefile | cut -c1-200
echo "===== K3 cuerpo de test-all ====="
awk '/^test-all:/ {p=1; print NR": "$0; next} p && /^[^\t#]/ {exit} p {print NR": "$0}' Makefile | cut -c1-150
echo "===== K3 cuerpo de rag-build ====="
awk '/^rag-build:/ {p=1; print NR": "$0; next} p && /^[^\t#]/ {exit} p {print NR": "$0}' Makefile | cut -c1-150
