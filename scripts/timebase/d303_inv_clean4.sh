#!/usr/bin/env bash
# DAY303 K4: prerequisitos de los test de host/correlation, pipeline-build entera, enlace de rag
set -u
echo "===== K4 cabeceras ====="
git grep -n -E '^(host-engine-test|host-engine-build|correlation-engine-test|correlation-engine-build|vault-client-clean|rag-clean):' -- Makefile | cut -c1-200
echo "===== K4 pipeline-build entera ====="
git grep -n -E '^pipeline-build:' -- Makefile | fold -w 150
echo "===== K4 cuerpo de vault-client-clean ====="
awk '/^vault-client-clean:/ {p=1; next} p && /^[^\t#]/ {exit} p {print NR": "$0}' Makefile
echo "===== K4 rag: enlaces y binarios ====="
ls -ld rag/build rag/build-active rag/build-debug
ls -l rag/build/rag-security rag/build-debug/rag-security 2>&1
echo "===== K4 quien crea rag/build-active ====="
git grep -n -F 'rag/build-active' -- Makefile scripts/ | cut -c1-160 | head -8
