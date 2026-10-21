#!/usr/bin/env bash
# DAY301: 7.o inventario 3b (solo lectura): enlazado de los tests con root, API de vaciado de sets y safe_exec.
set -u
DIA=day301
OUT=logs/lab/$DIA/inv_3b_7.txt
mkdir -p logs/lab/$DIA
FW=firewall-acl-agent
sec() { printf '\n===== %s =====\n' "$1"; }
{
sec "L1 CMake de test_ipset_injection_integration"
git grep -n -B 2 -A 14 "add_executable(test_ipset_injection_integration" -- "$FW/CMakeLists.txt"
git grep -n -A 4 "test_ipset_injection_integration PROPERTIES" -- "$FW/CMakeLists.txt"
sec "L2 flush/destroy en IPSetWrapper"
git grep -n -B 1 -A 4 -E "(flush_set|destroy_set|flush)\(" -- "$FW/include/firewall/ipset_wrapper.hpp"
sec "L3 safe_exec_with_output"
git grep -n -B 2 -A 6 "safe_exec_with_output(" -- "$FW/include"
} > "$OUT" 2>&1
echo "inventario en $OUT ($(wc -l < "$OUT") lineas)"
