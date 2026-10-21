#!/usr/bin/env bash
# DAY303 K5: quien crea los build-active, que componentes, y a donde apuntan hoy
set -u
echo "===== K5 objetivo set-build-profile ====="
awk '/^set-build-profile:/ {p=1; print NR": "$0; next} p && /^[^\t#]/ {exit} p {print NR": "$0}' Makefile | cut -c1-170
echo "===== K5 scripts que crean build-active ====="
git grep -n -F 'build-active' -- scripts/ '*.sh' | grep -v pipeline_health | cut -c1-170 | head -15
echo "===== K5 cuerpo de rag-clean ====="
awk '/^rag-clean:/ {p=1; next} p && /^[^\t#]/ {exit} p {print NR": "$0}' Makefile
echo "===== K5 enlaces build-active y build de hoy ====="
ls -ld */build-active tools/build etcd-server/build 2>&1
