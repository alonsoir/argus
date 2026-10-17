#!/usr/bin/env bash
# DAY300: puntos de enganche para DEBT-FW-PROTECTED-RANGES-001 (solo lectura).
sec() { printf '\n===== %s =====\n' "$1"; }
sec "ip_cidr_validator.hpp completo"
cat firewall-acl-agent/include/firewall/ip_cidr_validator.hpp
sec "ddos_shadow_policy.hpp: API publica"
git grep -n -e "struct " -e "class " -e "    [a-zA-Z_:<>]* [a-z_]*(.*) *{" -e "    [a-zA-Z_:<>]* [a-z_]*(.*);" -- firewall-acl-agent/include/firewall/ddos_shadow_policy.hpp
sec "zmq_subscriber.cpp: tratamiento del DROP de la sombra"
git grep -n -B 30 -A 25 "primer DROP recibido" -- firewall-acl-agent/src/api/zmq_subscriber.cpp
sec "batch_processor: donde se anaden IPs al ipset"
git grep -n -e "add_batch" -e "add_ip" -e "blacklist_ipset" -e "batch_add" -e "flush" -- firewall-acl-agent/src/core/batch_processor.cpp
sec "firewall.json: bloque de la sombra"
git grep -n -B 2 -A 25 "\"ddos_shadow\"" -- firewall-acl-agent/config/firewall.json
sec "config_loader.cpp: parseo de ddos_shadow"
git grep -n -A 30 "ddos_shadow" -- firewall-acl-agent/src/core/config_loader.cpp
sec "whitelist.json"
cat firewall-acl-agent/config/rules/whitelist.json
