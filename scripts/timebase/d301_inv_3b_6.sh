#!/usr/bin/env bash
# DAY301: 6.o inventario 3b (solo lectura): destinos de iptables, cadenas, rate limiting, netmask y limpieza.
set -u
DIA=day301
OUT=logs/lab/$DIA/inv_3b_6.txt
mkdir -p logs/lab/$DIA
FW=firewall-acl-agent
sec() { printf '\n===== %s =====\n' "$1"; }
{
sec "I1 IPTablesTarget"
git grep -n -A 12 "enum class IPTablesTarget" -- "$FW/include/firewall/iptables_wrapper.hpp"
sec "I2 FirewallConfig"
git grep -n -A 25 "struct FirewallConfig" -- "$FW/include/firewall/iptables_wrapper.hpp"
sec "I2 main: firewall_config"
git grep -n -B 3 -A 24 "FirewallConfig firewall_config" -- "$FW/src/main.cpp"
sec "I3 netmask"
git grep -n -B 2 -A 2 "netmask" -- "$FW/include/firewall/ipset_wrapper.hpp"
sec "I4 tests de setup_base_rules"
git grep -n "setup_base_rules" -- "$FW/tests"
sec "I5 limpieza de reglas al parar"
git grep -n -E "cleanup|remove_base_rules|teardown|flush_chain|delete_chain" -- "$FW/src/main.cpp" "$FW/src/core/iptables_wrapper.cpp"
} > "$OUT" 2>&1
echo "inventario en $OUT ($(wc -l < "$OUT") lineas)"
