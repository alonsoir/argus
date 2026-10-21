#!/usr/bin/env bash
# DAY300: inventario de la tanda 2b de [PROTEGIDOS-D300] (solo lectura).
sec() { printf '\n===== %s =====\n' "$1"; }
sec "config_loader.hpp: alrededor de ddos_shadow"
git grep -n -B 4 -A 3 "DdosShadowParams ddos_shadow;" -- firewall-acl-agent/include/firewall/config_loader.hpp
sec "zmq_subscriber.hpp: struct de config del suscriptor"
git grep -n -B 4 -A 3 "DdosShadowParams ddos_shadow;  ///<" -- firewall-acl-agent/include/firewall/zmq_subscriber.hpp
sec "zmq_subscriber.hpp: miembros de la sombra (contadores, detalle)"
git grep -n -e "sombra_" -e "tb_detalle_" -e "DdosShadowPolicy ddos_shadow_" -- firewall-acl-agent/include/firewall/zmq_subscriber.hpp
sec "main.cpp: copia de ddos_shadow al suscriptor"
git grep -n -B 2 -A 2 "ddos_shadow" -- firewall-acl-agent/src/main.cpp
sec "config_loader.cpp: parse_string_array"
git grep -n -A 14 "parse_string_array(const Json::Value" -- firewall-acl-agent/src/core/config_loader.cpp
sec "config_loader.cpp: fin del bloque ddos_shadow"
git grep -n -B 3 -A 2 "config.ddos_shadow = d;" -- firewall-acl-agent/src/core/config_loader.cpp
sec "zmq_subscriber.cpp: bloque de resumen completo (desde la linea de resumen hasta el reinicio del periodo)"
git grep -n -A 45 "\[SOMBRA-DDOS\] resumen: habilitada=" -- firewall-acl-agent/src/api/zmq_subscriber.cpp
sec "zmq_subscriber.cpp: includes"
git grep -n "#include" -- firewall-acl-agent/src/api/zmq_subscriber.cpp
