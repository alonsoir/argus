#!/usr/bin/env bash
# DAY302: 4.o inventario b2 (solo lectura): add_batch completo (orden set_exists / dry_run) y tests que hacen flush. Mac, raiz del repo.
set -u
DIA=day302
OUT=logs/lab/$DIA/inv_b2_4.txt
mkdir -p logs/lab/$DIA
FW=firewall-acl-agent
S=$FW/src
sec() { printf '\n===== %s =====\n' "$1"; }
{
sec "S1 add_batch completo"
git grep -n -A 120 "^IPSetResult<void> IPSetWrapper::add_batch(" -- "$S/core/ipset_wrapper.cpp"
sec "S1 set_dry_run y m_dry_run"
git grep -n -E "set_dry_run|m_dry_run" -- "$FW/include/firewall/ipset_wrapper.hpp"
sec "S3 tests que llaman a flush o add_ip"
git grep -n -E "flush\(\)|add_ip\(|add_detection" -- "$FW/tests"
} > "$OUT" 2>&1
echo "inventario en $OUT ($(wc -l < "$OUT") lineas)"
