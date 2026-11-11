#!/bin/bash
# [PROTEGIDOS-ANTISPOOF-D320] DEBT-FW-MANIFIESTO-PROTEGIDOS-001 (ADR-060, D8), medida previa de 8e.4b (decisión H-B).
# Solo mide: no toca los sets ni las cadenas de aRGus (todo lleva el prefijo ARGUS_M / argm / am320_) y lo deja todo
# como estaba al salir (trap). Las reglas sobre el tráfico real solo cuentan (sin DROP); el único DROP se prueba en
# una cadena a la que solo se salta desde la interfaz veth de prueba.
#
# Uso, en el defender:  sudo bash /vagrant/scripts/etcd_ha/d320_medir_antispoof.sh
#
# Diseño medido (H-B, coste por paquete constante: un lookup para el tráfico no protegido, como mucho cuatro):
#   1 -i lo                                       -> RETURN
#   2 origen NO en el set de IPs protegidas      -> RETURN   (casi todo el tráfico sale aquí)
#   3 (origen, interfaz) NO en el set con iface  -> goto SPOOF-IF (contar / LOG con límite / DROP)
#   4 origen NO en el set de IPs con MAC         -> RETURN
#   5 (origen, MAC) NO en el set ip,mac          -> goto SPOOF-MAC
# v2 (DAY320, tras medir la v1): las reglas 3 y 5 saltan con -g (goto) y no con -j. Con -j, en modo "solo contar" el
# paquete volvía de la cadena de spoofing y seguía por la principal (la v1 midió regla6 +10 en el caso c): en sombra
# un paquete podía contar en SPOOF-IF y también en SPOOF-MAC, y con DROP solo en una. Con -g sale a PREROUTING al
# acabar: una clasificación por paquete, igual en sombra que con DROP.
#   6                                             -> RETURN
# Entradas de prueba: .20 por la interfaz real hacia la LAN (la de 'ip route get 192.168.100.20'), sin MAC; .21 y .22
# por la veth de prueba, .21 con una MAC que no es la de la veth y .22 con la MAC real de la veth; .23 por la interfaz
# real CON MAC (para el caso de interfaz y MAC malas a la vez).
#
# PREDICCIÓN (escrita antes de medir):
#  M1 ipset tiene hash:net, hash:net,iface, hash:ip y hash:ip,mac con counters.
#  M2 iptables-restore --noflush crea y rehace las cadenas de prueba de golpe (una sola orden).
#  M3 Inyectando 10 paquetes UDP de cada origen desde el netns por la veth:
#     a) origen 10.250.0.2 (no protegido): regla 2 +10; reglas 3, 5 y 6 +0.
#     b) origen .20 (protegido, pero entra por la veth y no por su interfaz): regla 3 +10, SPOOF-IF +10.
#     c) origen .21 (interfaz correcta, MAC distinta): regla 5 +10, SPOOF-MAC +10, regla 6 +0 (goto).
#     d) origen .22 (interfaz y MAC correctas): regla 6 +10, sin spoofing.
#     e) origen .23 (interfaz mala Y MAC mala): regla 3 +10, SPOOF-IF +10, regla 5 +0, SPOOF-MAC +0 (cuenta una vez).
#     El tráfico real solo puede sumar en las reglas 2 y 4 (la .20 legítima por su interfaz sale por la 4).
#  M10 Camino legítimo (necesita la VM etcd arriba): en 70 s sin inyectar (chrony de la VM etcd pregunta cada 64 s), el tráfico real de .20 por su interfaz
#     sube el contador de (.20, interfaz) y SPOOF-IF/SPOOF-MAC suman 0. Sin vecino .20: NO MEDIDO (no es FALLA).
#  M4 LOG con --limit-burst 5: 5 líneas en el log del kernel con el prefijo de SPOOF-IF y 5 con el de SPOOF-MAC.
#  M5 Con DROP en SPOOF-IF: 10 paquetes de .20 por la veth cuentan en raw y llegan 0 a mangle PREROUTING (sin DROP,
#     llegan 10).
#  M6 'ip route get' de .20 da la interfaz real; la de .21 (que en el manifiesto de prueba dice veth) NO da la veth:
#     así se detectaría una entrada cuya interfaz no casa con la ruta (H-D).
#  M7 Contadores por entrada de ipset (informativo: qué entradas suben con las coincidencias negadas).
#  M8 Coste de lo que hará el vigía: 'ipset list' de un set pequeño y 'iptables -L' de la cadena, unos ms.
#  M9 rp_filter (all, default y cada interfaz): solo se informa (H-F).
# Si algo no da lo previsto: FALLA en el resumen y se para ahí (no se sigue construyendo sobre ello).
set -u
export LC_ALL=C
[ "$(id -u)" = 0 ] || { echo "hay que lanzarlo como root (sudo)"; exit 2; }

NS=argm320; VA=argm0; VB=argm1; IPA=10.250.0.1; IPB=10.250.0.2
S_IP=am320_ip; S_IF=am320_if; S_IPM=am320_ipm; S_MAC=am320_mac
C=ARGUS_M_AS; CIF=ARGUS_M_SPIF; CMAC=ARGUS_M_SPMAC; CDROP=ARGUS_M_DROP
MARCA="d320-medida"; PRE_IF="ARGUS-M-SPOOF-IF "; PRE_MAC="ARGUS-M-SPOOF-MAC "
MAL_MAC="02:00:00:00:d3:20"
PASAN=0; FALLAN=0; HAY_MAC=1
pasa() { echo "PASA  $*"; PASAN=$((PASAN+1)); }
falla() { echo "FALLA $*"; FALLAN=$((FALLAN+1)); }
ms() { echo $(( $(date +%s%N) / 1000000 )); }

limpiar() {
  iptables -w -t raw -D PREROUTING -m comment --comment "$MARCA" -j "$C" 2>/dev/null
  iptables -w -t raw -D PREROUTING -i "$VA" -m comment --comment "$MARCA-drop" -j "$CDROP" 2>/dev/null
  iptables -w -t mangle -D PREROUTING -i "$VA" -s 192.168.100.20 -m comment --comment "$MARCA-llegan" 2>/dev/null
  for c in "$C" "$CIF" "$CMAC" "$CDROP"; do iptables -w -t raw -F "$c" 2>/dev/null; done
  for c in "$C" "$CIF" "$CMAC" "$CDROP"; do iptables -w -t raw -X "$c" 2>/dev/null; done
  for s in "$S_IP" "$S_IF" "$S_IPM" "$S_MAC"; do ipset destroy "$s" 2>/dev/null; done
  ip netns del "$NS" 2>/dev/null
  ip link del "$VA" 2>/dev/null
}
trap limpiar EXIT
limpiar

echo "== M0 inventario"
uname -r; iptables -V; ipset -v | head -1
IFL=$(ip -o route get 192.168.100.20 2>/dev/null | sed -n 's/.* dev \([^ ]*\).*/\1/p')
[ -n "$IFL" ] || { echo "no hay ruta a 192.168.100.20: ¿es el defender?"; exit 1; }
echo "interfaz hacia la LAN (ruta a .20): $IFL"
echo "vecino .20: $(ip neigh show 192.168.100.20 | head -1)"
echo "reglas previas en raw PREROUTING: $(iptables -w -t raw -S PREROUTING | grep -c '^-A')"

echo "== M9 rp_filter"
for f in all default "$IFL" lo $(ls /sys/class/net | grep -vE "^(lo|$IFL)$"); do
  [ -r /proc/sys/net/ipv4/conf/$f/rp_filter ] && echo "  rp_filter[$f]=$(cat /proc/sys/net/ipv4/conf/$f/rp_filter)"
done

echo "== M1 tipos de set"
ipset create "$S_IP" hash:net counters && pasa "M1 hash:net counters" || falla "M1 hash:net counters"
ipset create "$S_IF" hash:net,iface counters && pasa "M1 hash:net,iface counters" || falla "M1 hash:net,iface counters"
ipset create "$S_IPM" hash:ip counters && pasa "M1 hash:ip counters" || falla "M1 hash:ip counters"
if ipset create "$S_MAC" hash:ip,mac counters; then pasa "M1 hash:ip,mac counters"
else falla "M1 hash:ip,mac counters (sin él no hay regla de MAC en O(1); se mide el resto)"; HAY_MAC=0; fi

echo "== red de prueba (netns $NS, veth $VA <-> $VB)"
ip netns add "$NS" && ip link add "$VA" type veth peer name "$VB" && ip link set "$VB" netns "$NS" \
  && ip addr add "$IPA/30" dev "$VA" && ip link set "$VA" up \
  && ip -n "$NS" addr add "$IPB/30" dev "$VB" && ip -n "$NS" link set "$VB" up && ip -n "$NS" link set lo up \
  || { falla "red de prueba"; exit 1; }
MACB=$(ip netns exec "$NS" cat /sys/class/net/$VB/address)
echo "MAC de la veth del netns: $MACB"

ipset add "$S_IP" 192.168.100.20/32; ipset add "$S_IP" 192.168.100.21/32; ipset add "$S_IP" 192.168.100.22/32
ipset add "$S_IP" 192.168.100.23/32
ipset add "$S_IF" "192.168.100.20/32,$IFL"; ipset add "$S_IF" "192.168.100.21/32,$VA"; ipset add "$S_IF" "192.168.100.22/32,$VA"
ipset add "$S_IF" "192.168.100.23/32,$IFL"
ipset add "$S_IPM" 192.168.100.21; ipset add "$S_IPM" 192.168.100.22; ipset add "$S_IPM" 192.168.100.23
if [ $HAY_MAC = 1 ]; then ipset add "$S_MAC" "192.168.100.21,$MAL_MAC"; ipset add "$S_MAC" "192.168.100.22,$MACB"
  ipset add "$S_MAC" "192.168.100.23,$MAL_MAC"; fi

reglas() {  # $1 = destino de la regla de cuenta de SPOOF-IF ("" = solo contar, o "-j DROP")
  {
    echo "*raw"
    echo ":$C - [0:0]"; echo ":$CIF - [0:0]"; echo ":$CMAC - [0:0]"
    echo "-A $C -i lo -j RETURN"
    echo "-A $C -m set ! --match-set $S_IP src -j RETURN"
    echo "-A $C -m set ! --match-set $S_IF src,src -g $CIF"
    echo "-A $C -m set ! --match-set $S_IPM src -j RETURN"
    if [ $HAY_MAC = 1 ]; then echo "-A $C -m set ! --match-set $S_MAC src,src -g $CMAC"
    else echo "-A $C -m comment --comment sin-hash-ip-mac"; fi
    echo "-A $C -j RETURN"
    echo "-A $CIF -m limit --limit 5/min --limit-burst 5 -j LOG --log-prefix \"$PRE_IF\""
    echo "-A $CIF -m comment --comment cuenta $1"
    echo "-A $CMAC -m limit --limit 5/min --limit-burst 5 -j LOG --log-prefix \"$PRE_MAC\""
    echo "-A $CMAC -m comment --comment cuenta"
    echo "COMMIT"
  } > /tmp/d320_reglas.txt
  iptables-restore -w --noflush < /tmp/d320_reglas.txt
}
echo "== M2 iptables-restore --noflush"
if reglas ""; then
  n=$(iptables -w -t raw -S "$C" | grep -c '^-A'); n2=$(iptables -w -t raw -S "$CIF" | grep -c '^-A')
  [ "$n" = 6 ] && [ "$n2" = 2 ] && pasa "M2 cadenas creadas de golpe ($C=$n reglas, $CIF=$n2)" || falla "M2 $C=$n $CIF=$n2 (esperado 6 y 2)"
  reglas "" && n=$(iptables -w -t raw -S "$C" | grep -c '^-A') && [ "$n" = 6 ] \
    && pasa "M2 rehacer la cadena con --noflush no duplica ($n reglas)" || falla "M2 al rehacer: $n reglas"
else falla "M2 iptables-restore --noflush"; cat /tmp/d320_reglas.txt; exit 1; fi
iptables -w -t raw -I PREROUTING 1 -m comment --comment "$MARCA" -j "$C" || { falla "salto desde PREROUTING"; exit 1; }

cnt() { iptables -w -t raw -L "$1" -v -x -n --line-numbers | awk -v n="$2" '$1==n {print $2}'; }
foto() { R2=$(cnt $C 2); R3=$(cnt $C 3); R5=$(cnt $C 5); R6=$(cnt $C 6); FIF=$(cnt $CIF 2); FMAC=$(cnt $CMAC 2); }
manda() {  # $1 = origen, $2 = paquetes
  ip netns exec "$NS" python3 -I - "$1" "$IPA" "$2" <<'PY'
import socket, struct, sys
src, dst, n = sys.argv[1], sys.argv[2], int(sys.argv[3])
s = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_RAW)
carga = b"argus-d320-medida"
udp = struct.pack("!HHHH", 40320, 40321, 8 + len(carga), 0) + carga
ip = struct.pack("!BBHHHBBH4s4s", 0x45, 0, 20 + len(udp), 0, 0, 64, 17, 0, socket.inet_aton(src), socket.inet_aton(dst))
for _ in range(n):
    s.sendto(ip + udp, (dst, 0))
PY
  sleep 1
}
ip netns exec "$NS" ping -c1 -W1 "$IPA" >/dev/null 2>&1   # ARP resuelto antes de medir
T0=$(date '+%Y-%m-%d %H:%M:%S')

echo "== M3 inyección (10 paquetes por origen)"
caso() {  # nombre origen d2 d3 d5 d6 dif dmac   (d2: mínimo; resto: exactos)
  local nom=$1 src=$2; foto; local a2=$R2 a3=$R3 a5=$R5 a6=$R6 aif=$FIF amac=$FMAC
  manda "$src" 10; foto
  local e2=$((R2-a2)) e3=$((R3-a3)) e5=$((R5-a5)) e6=$((R6-a6)) eif=$((FIF-aif)) emac=$((FMAC-amac))
  local txt="M3 $nom: regla2 +$e2 regla3 +$e3 regla5 +$e5 regla6 +$e6 SPOOF-IF +$eif SPOOF-MAC +$emac"
  if [ "$e2" -ge "$3" ] && [ "$e3" = "$4" ] && [ "$e5" = "$5" ] && [ "$e6" = "$6" ] && [ "$eif" = "$7" ] && [ "$emac" = "$8" ]
  then pasa "$txt"; else falla "$txt (esperado regla2 >=+$3 regla3 +$4 regla5 +$5 regla6 +$6 SPOOF-IF +$7 SPOOF-MAC +$8)"; fi
}
caso "a) no protegido" "$IPB"       10 0  0  0  0  0
caso "b) .20 por otra interfaz" 192.168.100.20 0 10 0 0 10 0
if [ $HAY_MAC = 1 ]; then
  caso "c) .21 MAC distinta" 192.168.100.21 0 0 10 0 0 10
  caso "d) .22 interfaz y MAC buenas" 192.168.100.22 0 0 0 10 0 0
  caso "e) .23 interfaz y MAC malas" 192.168.100.23 0 10 0 0 10 0
else echo "  (c y d no se miden: sin hash:ip,mac)"; fi

echo "== M4 LOG con límite"
sleep 1
L1=$(journalctl -k --since "$T0" --no-pager 2>/dev/null | grep -c "$PRE_IF")
L2=$(journalctl -k --since "$T0" --no-pager 2>/dev/null | grep -c "$PRE_MAC")
[ "$L1" = 5 ] && pasa "M4 SPOOF-IF: $L1 líneas en el log del kernel" || falla "M4 SPOOF-IF: $L1 líneas (esperado 5)"
if [ $HAY_MAC = 1 ]; then [ "$L2" = 5 ] && pasa "M4 SPOOF-MAC: $L2 líneas" || falla "M4 SPOOF-MAC: $L2 líneas (esperado 5)"; fi
echo "  muestra: $(journalctl -k --since "$T0" --no-pager 2>/dev/null | grep -m1 "$PRE_IF" | cut -c1-220)"

echo "== M5 DROP efectivo (solo desde la veth)"
iptables -w -t mangle -I PREROUTING 1 -i "$VA" -s 192.168.100.20 -m comment --comment "$MARCA-llegan"
llegan() { iptables -w -t mangle -L PREROUTING -v -x -n --line-numbers | awk '/'"$MARCA"'-llegan/ {print $2}'; }
a=$(llegan); manda 192.168.100.20 10; b=$(llegan)
[ $((b-a)) = 10 ] && pasa "M5 sin DROP llegan a mangle $((b-a))" || falla "M5 sin DROP llegan $((b-a)) (esperado 10)"
iptables -w -t raw -N "$CDROP" && iptables -w -t raw -A "$CDROP" -m set ! --match-set "$S_IF" src,src -m set --match-set "$S_IP" src -j DROP \
  && iptables -w -t raw -I PREROUTING 1 -i "$VA" -m comment --comment "$MARCA-drop" -j "$CDROP"
d0=$(cnt $CDROP 1); a=$(llegan); manda 192.168.100.20 10; b=$(llegan); d1=$(cnt $CDROP 1)
[ $((b-a)) = 0 ] && [ $((d1-d0)) = 10 ] && pasa "M5 con DROP: $((d1-d0)) descartados en raw, $((b-a)) llegan a mangle" \
  || falla "M5 con DROP: descartados $((d1-d0)), llegan $((b-a)) (esperado 10 y 0)"

echo "== M6 interfaz del manifiesto contra la ruta (H-D)"
r20=$(ip -o route get 192.168.100.20 | sed -n 's/.* dev \([^ ]*\).*/\1/p'); r21=$(ip -o route get 192.168.100.21 | sed -n 's/.* dev \([^ ]*\).*/\1/p')
[ "$r20" = "$IFL" ] && pasa "M6 .20: ruta por $r20 = interfaz de la entrada" || falla "M6 .20: ruta por $r20"
[ "$r21" != "$VA" ] && pasa "M6 .21: la entrada dice $VA y la ruta va por $r21 -> se detecta" || falla "M6 .21: ruta por $r21"

echo "== M10 camino legítimo de .20 por $IFL (70 s sin inyectar)"
if [ -n "$(ip neigh show 192.168.100.20 | grep -v FAILED)" ] || ping -c1 -W1 192.168.100.20 >/dev/null 2>&1; then
  leg() { ipset list "$S_IF" | awk -v k="192.168.100.20,$IFL" '$1==k {print $3}'; }
  foto; g0=$(leg); i0=$FIF; m0=$FMAC; sleep 70; foto; g1=$(leg)
  [ "$((g1-g0))" -gt 0 ] && [ "$((FIF-i0))" = 0 ] && [ "$((FMAC-m0))" = 0 ] \
    && pasa "M10 .20 legítima: +$((g1-g0)) paquetes por (.20,$IFL), SPOOF-IF +$((FIF-i0)), SPOOF-MAC +$((FMAC-m0))" \
    || falla "M10 .20 legítima: (.20,$IFL) +$((g1-g0)), SPOOF-IF +$((FIF-i0)), SPOOF-MAC +$((FMAC-m0)) (esperado >0, 0, 0)"
else echo "NO MEDIDO M10: sin vecino .20 (VM etcd parada: vagrant up etcd)"; fi

echo "== M7 contadores por entrada (informativo)"
for s in "$S_IP" "$S_IF" "$S_IPM" "$S_MAC"; do ipset list "$s" 2>/dev/null | grep -E '^192\.168\.100\.2[0-3]' | sed "s/^/  $s: /"; done

echo "== M8 coste de las lecturas del vigía (10 de cada)"
t=$(ms); for i in $(seq 10); do ipset list "$S_IF" >/dev/null; done; t1=$(( $(ms)-t ))
t=$(ms); for i in $(seq 10); do iptables -w -t raw -L "$C" -v -x -n >/dev/null; done; t2=$(( $(ms)-t ))
echo "  ipset list: $((t1/10)) ms por lectura; iptables -L: $((t2/10)) ms por lectura"
[ $((t1/10)) -lt 100 ] && [ $((t2/10)) -lt 100 ] && pasa "M8 lecturas por debajo de 100 ms" || falla "M8 lecturas lentas"

echo "== RESUMEN: $PASAN PASA, $FALLAN FALLA (al salir se borra todo lo de prueba)"
[ "$FALLAN" = 0 ]
