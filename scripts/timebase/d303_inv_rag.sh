#!/usr/bin/env bash
# DAY303 K6: set-build-profile.sh entero y todo lo que aun toca rag / rag-security
set -u
echo "===== K6 set-build-profile.sh ====="
cat -n etcd-server/config/set-build-profile.sh
echo "===== K6 ficheros trackeados que nombran rag-security / rag-start / rag-build / rag/build ====="
git grep -c -E 'rag-security|rag-start|rag-build|rag/build|rag_security' -- ':!rag/' ':!docs/' ':!*.md' ':!scripts/timebase/'
echo "===== K6 Makefile: lineas ====="
git grep -n -E 'rag-security|rag-start|rag-build|rag/build|RAG_BUILD_DIR' -- Makefile | cut -c1-150
echo "===== K6 objetivos que contienen las lineas 927 y 942 ====="
for n in 927 942; do awk -v n="$n" 'NR<=n && /^[A-Za-z0-9_.+-]+:/ {t=$1} NR==n {print n" -> "t; exit}' Makefile; done
