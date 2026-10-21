#!/usr/bin/env bash
# DAY300: inventario 3 para DEBT-FW-PROTECTED-RANGES-001 (solo lectura).
sec() { printf '\n===== %s =====\n' "$1"; }
sec "whitelist.json: tamano"
wc -c firewall-acl-agent/config/rules/whitelist.json
sec "firewall.json: bloque ipsets (blacklist/whitelist)"
git grep -n -B 2 -A 14 "\"whitelist\": {" -- firewall-acl-agent/config/firewall.json
sec "main.cpp: creacion de ipsets y whitelist"
git grep -n -B 3 -A 12 -e "make_whitelist_config" -e "create_set" -e "ensure_set" -- firewall-acl-agent/src/main.cpp
sec "ipset_wrapper.hpp: make_whitelist_config y tipos de set"
git grep -n -A 12 "inline IPSetConfig make_whitelist_config" -- firewall-acl-agent/include/firewall/ipset_wrapper.hpp
git grep -n -e "hash:net" -e "hash:ip" -e "enum class IPSetType" -- firewall-acl-agent/include/firewall/ipset_wrapper.hpp
sec "batch_processor.cpp: entradas add_ip / add_detection"
git grep -n -B 2 -A 30 "^void BatchProcessor::add_ip" -- firewall-acl-agent/src/core/batch_processor.cpp
git grep -n -e "^void BatchProcessor::" -e "^bool BatchProcessor::" -- firewall-acl-agent/src/core/batch_processor.cpp
sec "config_loader.hpp: struct de ddos_shadow"
git grep -n -B 2 -A 16 "struct DdosShadowConfig" -- firewall-acl-agent/include/firewall/config_loader.hpp
sec "zmq_subscriber.cpp: linea de resumen de la sombra"
git grep -n -B 4 -A 14 "\[SOMBRA-DDOS\] resumen: habilitada=" -- firewall-acl-agent/src/api/zmq_subscriber.cpp
sec "CMakeLists del firewall: como se registran los tests sueltos"
git grep -n -B 2 -A 8 "test_ip_cidr_validator" -- firewall-acl-agent/CMakeLists.txt
