#!/usr/bin/env bash
# DAY301: 5.o inventario 3b (solo lectura): reglas base de iptables, add del ipset, HASH_NET y log de firewall-start.
set -u
DIA=day301
OUT=logs/lab/$DIA/inv_3b_5.txt
mkdir -p logs/lab/$DIA
FW=firewall-acl-agent
sec() { printf '\n===== %s =====\n' "$1"; }
{
sec "W1 setup_base_rules"
git grep -n -A 120 "IPTablesWrapper::setup_base_rules" -- "$FW/src/core/iptables_wrapper.cpp"
sec "W2 add individual (cabecera)"
git grep -n -B 3 -A 10 "IPSetResult<void> add(" -- "$FW/include/firewall/ipset_wrapper.hpp"
sec "W2 add individual (implementacion)"
git grep -n -A 45 "IPSetResult<void> IPSetWrapper::add(" -- "$FW/src/core/ipset_wrapper.cpp"
sec "W2 validacion de IP"
git grep -n -E "is_valid_ip|valid_ip_or_cidr|is_valid_cidr" -- "$FW/src" "$FW/include"
sec "W3 HASH_NET"
git grep -n -B 2 -A 6 "HASH_NET" -- "$FW/src/core/ipset_wrapper.cpp"
sec "W4 firewall-start"
git grep -n -A 18 "^firewall-start:" -- Makefile
} > "$OUT" 2>&1
echo "inventario en $OUT ($(wc -l < "$OUT") lineas)"
