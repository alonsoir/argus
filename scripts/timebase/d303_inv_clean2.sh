#!/usr/bin/env bash
# DAY303 K2: quien compila cada directorio que clean-all no limpia; que es tools/build en git
set -u
for d in common/build common/build-vault rag/build host-engine/build correlation-engine/build common-rag-ingester/build plugin-loader/build ml-detector/build_detector_test suricata-adapter/build zeek-adapter/build wazuh-adapter/build; do
  echo "===== K2 Makefile -> $d ====="
  git grep -n -F "$d" -- Makefile | cut -c1-160 | head -8
done
echo "===== K2 objetivos *-clean de las librerias ====="
for t in seed-client-clean correlation-v1-clean host-domain-v1-clean crypto-transport-clean etcd-client-clean plugin-loader-clean; do
  awk -v t="$t" '$0 ~ "^"t":" {p=1; print NR": "$0; next} p && /^[^\t#]/ {exit} p && /rm /{print NR": "$0}' Makefile
done
echo "===== K2 tools/build en git ====="
git ls-files -s tools/build
git diff tools/build
ls -ld tools/build
