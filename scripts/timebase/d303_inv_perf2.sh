#!/usr/bin/env bash
# DAY303: inventario de solo lectura (2): cabecera y helpers del fixture IPSetWrapperTest, safe_exec y API de
# vaciado del wrapper. Mac, raiz del repo.
set -u
DIA=day303
OUT=logs/lab/$DIA/inv_perf2.txt
mkdir -p logs/lab/$DIA
FW=firewall-acl-agent
T=$FW/tests/unit/test_ipset_wrapper.cpp
sec() { printf '\n===== %s =====\n' "$1"; }
{
sec "R1 test_ipset_wrapper.cpp desde el principio hasta el primer TEST_F"
awk '/^TEST_F\(IPSetWrapperTest, CreateAndDestroySet\)/{exit} {printf "%d: %s\n", NR, $0}' "$T"
sec "R1 FlushSet (uso de la API de vaciado)"
git grep -n -A 12 "TEST_F(IPSetWrapperTest, FlushSet)" -- "$T"
sec "R2 safe_exec y safe_exec_with_file_in"
git grep -n -A 45 -E "^int safe_exec\(" -- "$FW"
git grep -n -E "posix_spawn|fork\(|execv|waitpid" -- "$FW/src" "$FW/include"
sec "R3 API publica de IPSetWrapper (flush/destroy/count/test/add_batch)"
git grep -n -E "flush|destroy_set|get_entry_count|bool test\(|add_batch|create_set" -- "$FW/include/firewall/ipset_wrapper.hpp"
sec "otros ficheros que incluyan algo del fixture"
git grep -n -E "IPSetWrapperTest|TEST_SET_NAME" -- "$FW" ":!$T"
} > "$OUT" 2>&1
echo "inventario en $OUT ($(wc -l < "$OUT") lineas)"
