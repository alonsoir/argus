#!/usr/bin/env bash
# DAY301: 2.º inventario 3b (solo lectura): filtro de confianza, re-adición, -exist, dry_run en main. Mac, raíz del repo.
set -u
DIA=day301
OUT=logs/lab/$DIA/inv_3b_2.txt
mkdir -p logs/lab/$DIA
FW=firewall-acl-agent
sec() { printf '\n===== %s =====\n' "$1"; }
{
sec "P1 add_detections"
git grep -n -A 50 "BatchProcessor::add_detections" -- "$FW/src/core/batch_processor.cpp"
sec "P2 add_ip"
git grep -n -A 40 "BatchProcessor::add_ip(" -- "$FW/src/core/batch_processor.cpp"
sec "P3 add_batch / restore / -exist"
git grep -n -A 70 "IPSetWrapper::add_batch" -- "$FW/*ipset_wrapper.cpp"
git grep -n -E "\-exist|restore" -- "$FW/*ipset_wrapper.cpp"
sec "whitelist: make_whitelist_config"
git grep -n -A 14 "make_whitelist_config" -- "$FW/include/firewall/ipset_wrapper.hpp"
sec "P4 dry_run en main.cpp"
git grep -n -B 2 -A 20 "dry_run" -- "$FW/src/main.cpp"
sec "Makefile test-firewall-e2e"
git grep -n -A 10 "^test-firewall-e2e:" -- Makefile
} > "$OUT" 2>&1
echo "inventario en $OUT ($(wc -l < "$OUT") líneas)"
