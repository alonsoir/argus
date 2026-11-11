#!/usr/bin/env bash
# DAY318, ADR-060 puntos abiertos 1 y 4: interfaz del defender hacia la LAN y set hash:net,iface.
# Se ejecuta en el defender como root. No toca INPUT ni los sets de aRGus: crea un set y una cadena
# de prueba (sin salto desde INPUT) y los borra al final.
set -u
S=argus_prueba_d318
S2=argus_prueba_d318_b
C=ARGUS_PRUEBA_D318
echo "== interfaces"
ip -br addr
IF=$(ip -o -4 addr show | awk '$4 ~ /^192\.168\.100\.1\// {print $2}')
echo "== interfaz con 192.168.100.1: '${IF}'"
echo "== ruta a la VM etcd"
ip route get 192.168.100.20
OTRA=$(ip -o -4 addr show | awk -v i="$IF" '$2 != i && $2 != "lo" {print $2; exit}')
echo "== otra interfaz para la prueba negativa: '${OTRA}'"
echo "== ipset"
ipset --version
echo "== sets antes"
ipset list -n
ipset create "$S" hash:net,iface
echo "create rc=$?"
ipset add "$S" "192.168.100.20/32,${IF}"
echo "add rc=$?"
ipset test "$S" "192.168.100.20,${IF}"
echo "test interfaz buena rc=$? (esperado 0)"
ipset test "$S" "192.168.100.20,${OTRA}"
echo "test otra interfaz rc=$? (esperado 1)"
ipset test "$S" "192.168.100.21,${IF}"
echo "test otra IP rc=$? (esperado 1)"
iptables -N "$C"
echo "cadena rc=$?"
iptables -A "$C" -m set --match-set "$S" src,src -j RETURN
echo "regla src,src rc=$?"
iptables -S "$C"
ipset create "$S2" hash:net,iface
ipset add "$S2" "192.168.100.61/32,${IF}"
ipset swap "$S" "$S2"
echo "swap rc=$?"
echo "== tras el swap, contenido de $S (esperado 192.168.100.61/32,${IF})"
ipset list "$S"
iptables -F "$C"
iptables -X "$C"
ipset destroy "$S"
ipset destroy "$S2"
echo "== sets despues (igual que antes)"
ipset list -n
