#!/usr/bin/env bash
set -euo pipefail
# Ejecutar desde la raíz del repo (test-zeromq-docker).
test -f Vagrantfile || { echo "ERROR: ejecuta esto desde la raíz del repo"; exit 1; }

mkdir -p host-engine/tools
[ -f host-engine/CMakeLists.txt ] || : > host-engine/CMakeLists.txt
[ -f host-engine/tools/host_bronze_to_gold_converter.cpp ] || : > host-engine/tools/host_bronze_to_gold_converter.cpp

echo "Estructura host-engine/:"
find host-engine -type f | sort