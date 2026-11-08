#!/usr/bin/env bash
# [PROTEGIDOS-LIMPIEZA-D320] Test de d320_limpia_kernel.sh. Necesita root, iptables e ipset. Usa nombres PROPIOS
# (D320T_*, d320t_*), así que se puede correr en el defender sin tocar las cadenas ni los sets del pipeline.
# Reproduce el estado medido en el defender el DAY320 (cadena raw del antispoofing que usa el set de protegidos) y
# comprueba: que la limpieza antigua lo deja (el test discrimina), que la nueva lo quita entero, que no toca nombres
# parecidos, idempotencia, saltos repetidos, sin antispoofing ('-'), uso malo, que avisa (rc 1) si algo ajeno
# sigue usando un set y que --contar cuenta sin tocar.
# Uso: sudo bash scripts/etcd_ha/test_d320_limpia_kernel.sh      Salida: N/M PASA; rc 0 si todo pasa, 77 sin root.
set -u
L="$(cd "$(dirname "$0")" && pwd)/d320_limpia_kernel.sh"
[ "$(id -u)" = 0 ] || { echo "SKIP: necesita root"; exit 77; }
command -v ipset > /dev/null && command -v iptables > /dev/null || { echo "SKIP: faltan iptables/ipset"; exit 77; }

CH=D320T_FILTER; AS=D320T_AS; WL=d320t_prot; BL=d320t_bl; SR=d320t_redes; SI=d320t_ipmac; SM=d320t_mac
PARECIDOS_CAD="D320T_ASX D320T_FILTERX"; PARECIDOS_SET="d320t_prot_x d320t_blx"
SETS="$SR $SI $SM $BL $WL"
OK=0; TOT=0
pasa() { OK=$((OK + 1)); TOT=$((TOT + 1)); echo "PASA  $*"; }
mal()  { TOT=$((TOT + 1)); echo "FALLA $*"; }
limpia_todo() {
  iptables -w -D INPUT -m set --match-set $WL src -m comment --comment d320t-ajeno -j ACCEPT 2>/dev/null
  bash "$L" "$CH" "$AS" $SETS > /dev/null 2>&1 || true
  for c in $PARECIDOS_CAD; do
    iptables -w -t raw -F "$c" 2>/dev/null; iptables -w -t raw -X "$c" 2>/dev/null
    iptables -w -F "$c" 2>/dev/null; iptables -w -X "$c" 2>/dev/null
  done
  for s in $PARECIDOS_SET; do ipset destroy "$s" 2>/dev/null; done
}
trap limpia_todo EXIT

# Tipo para el set de MAC: hash:ip,mac si el kernel lo tiene (defender), hash:ip si no (banco, medido DAY320).
TMAC=hash:ip,mac
ipset create d320t_sonda hash:ip,mac 2>/dev/null && ipset destroy d320t_sonda || TMAC=hash:ip

monta() {   # el estado que dejó en el defender la última corrida de lab-e2e-antispoof (modo descarta)
  ipset create $WL hash:net,iface -exist; ipset create $BL hash:ip -exist
  ipset create $SR hash:net -exist; ipset create $SI hash:ip -exist; ipset create $SM $TMAC -exist
  iptables -w -N $CH 2>/dev/null; iptables -w -I INPUT 1 -j $CH
  iptables -w -A $CH -m set --match-set $WL src,src -j RETURN
  iptables -w -A $CH -m set --match-set $BL src -j DROP
  iptables -w -t raw -N $AS 2>/dev/null; iptables -w -t raw -N ${AS}_IF 2>/dev/null; iptables -w -t raw -N ${AS}_MAC 2>/dev/null
  iptables -w -t raw -I PREROUTING 1 -j $AS
  iptables -w -t raw -A $AS -i lo -j RETURN
  iptables -w -t raw -A $AS -m set ! --match-set $SR src -j RETURN
  iptables -w -t raw -A $AS -m set ! --match-set $WL src,src -g ${AS}_IF
  iptables -w -t raw -A $AS -m set ! --match-set $SI src -j RETURN
  iptables -w -t raw -A $AS -m set ! --match-set $SM src,src -g ${AS}_MAC
  iptables -w -t raw -A $AS -j RETURN
  iptables -w -t raw -A ${AS}_IF -m limit --limit 5/min -j LOG --log-prefix "D320T-IF "
  iptables -w -t raw -A ${AS}_IF -j DROP
  iptables -w -t raw -A ${AS}_MAC -m limit --limit 5/min -j LOG --log-prefix "D320T-MAC "
  iptables -w -t raw -A ${AS}_MAC -j DROP
}
cuenta_sets() { local n=0 s; for s in $SETS; do ipset list -n | grep -qx "$s" && n=$((n + 1)); done; echo $n; }
cuenta_raw()  { iptables -w -t raw -S | grep -c -w -e $AS -e ${AS}_IF -e ${AS}_MAC; }

limpia_todo
# Nombres parecidos: no se pueden llevar por delante.
for c in $PARECIDOS_CAD; do iptables -w -t raw -N "$c"; iptables -w -N "$c"; done
for s in $PARECIDOS_SET; do ipset create "$s" hash:ip; done

# T1: la limpieza ANTIGUA (la de los traps de d302 y del vigía) deja la cadena raw y el set de protegidos.
monta
while iptables -w -D INPUT -j $CH 2>/dev/null; do :; done; iptables -w -F $CH; iptables -w -X $CH
ipset destroy $BL 2>/dev/null; ipset destroy $WL 2>/dev/null
r=$(cuenta_raw); ipset list -n | grep -qx $WL && w=1 || w=0
[ "$r" -gt 0 ] && [ "$w" = 1 ] && pasa "T1 la limpieza antigua deja raw=$r y $WL (el defecto medido)" || mal "T1 raw=$r prot=$w"

# T2: la nueva lo quita todo, a partir de ese mismo estado.
out=$(bash "$L" "$CH" "$AS" $SETS); rc=$?
[ "$rc" = 0 ] && [ "$out" = "    quedan raw=0 filter=0 sets=0" ] && [ "$(cuenta_sets)" = 0 ] && [ "$(cuenta_raw)" = 0 ] \
  && pasa "T2 desde los restos: rc=0 '$out'" || mal "T2 rc=$rc '$out' sets=$(cuenta_sets) raw=$(cuenta_raw)"

# T3: desde el estado completo (cadena del filtro incluida) y con el salto raw y el de INPUT repetidos.
monta; iptables -w -t raw -I PREROUTING 1 -j $AS; iptables -w -I INPUT 1 -j $CH
out=$(bash "$L" "$CH" "$AS" $SETS); rc=$?
[ "$rc" = 0 ] && [ "$(cuenta_sets)" = 0 ] && ! iptables -w -t raw -S PREROUTING | grep -qw $AS && ! iptables -w -S INPUT | grep -qw $CH \
  && pasa "T3 estado completo con saltos dobles: rc=0 '$out'" || mal "T3 rc=$rc '$out'"

# T4: los nombres parecidos siguen ahí.
f=0; for c in $PARECIDOS_CAD; do iptables -w -t raw -S "$c" > /dev/null 2>&1 && iptables -w -S "$c" > /dev/null 2>&1 || f=1; done
for s in $PARECIDOS_SET; do ipset list -n | grep -qx "$s" || f=1; done
[ "$f" = 0 ] && pasa "T4 no toca $PARECIDOS_CAD $PARECIDOS_SET" || mal "T4 se llevó algún nombre parecido"

# T5: idempotente.
out=$(bash "$L" "$CH" "$AS" $SETS); rc=$?
[ "$rc" = 0 ] && [ "$out" = "    quedan raw=0 filter=0 sets=0" ] && pasa "T5 segunda pasada sin nada: rc=0" || mal "T5 rc=$rc '$out'"

# T6: sin antispoofing ('-').
ipset create $WL hash:net,iface; ipset create $BL hash:ip; iptables -w -N $CH; iptables -w -I INPUT 1 -j $CH
iptables -w -A $CH -m set --match-set $WL src,src -j RETURN
out=$(bash "$L" "$CH" - $BL $WL); rc=$?
[ "$rc" = 0 ] && [ "$out" = "    quedan raw=0 filter=0 sets=0" ] && pasa "T6 con '-': rc=0" || mal "T6 rc=$rc '$out'"

# T7: algo ajeno sigue usando el set de protegidos: no se puede destruir y lo dice (rc 1, sets=1).
monta; iptables -w -A INPUT -m set --match-set $WL src -m comment --comment d320t-ajeno -j ACCEPT
out=$(bash "$L" "$CH" "$AS" $SETS); rc=$?
[ "$rc" = 1 ] && [ "$out" = "    quedan raw=0 filter=0 sets=1" ] && pasa "T7 regla ajena: rc=1 '$out'" || mal "T7 rc=$rc '$out'"
iptables -w -D INPUT -m set --match-set $WL src -m comment --comment d320t-ajeno -j ACCEPT

# T9: --contar cuenta los restos sin tocarlos (rc 1 y los mismos números dos veces), y da 0 tras limpiar.
monta
o1=$(bash "$L" --contar "$CH" "$AS" $SETS); r1=$?
o2=$(bash "$L" --contar "$CH" "$AS" $SETS); r2=$?
n1=$(cuenta_sets)
bash "$L" "$CH" "$AS" $SETS > /dev/null
o3=$(bash "$L" --contar "$CH" "$AS" $SETS); r3=$?
[ "$r1" = 1 ] && [ "$o1" = "$o2" ] && [ "$r2" = 1 ] && [ "$n1" = 5 ] && [ "$o1" = "    quedan raw=14 filter=4 sets=5" ] \
  && [ "$r3" = 0 ] && [ "$o3" = "    quedan raw=0 filter=0 sets=0" ] \
  && pasa "T9 --contar: '$o1' rc=1 sin tocar; tras limpiar rc=0" || mal "T9 r=$r1/$r2/$r3 '$o1' '$o2' '$o3' sets=$n1"

# T8: uso malo.
bash "$L" "$CH" "$AS" > /dev/null 2>&1; r1=$?
bash "$L" "$CH" 'X;rm' $WL > /dev/null 2>&1; r2=$?
bash "$L" "" "$AS" $WL > /dev/null 2>&1; r3=$?
bash "$L" --contar "$CH" "$AS" > /dev/null 2>&1; r4=$?
[ "$r1" = 2 ] && [ "$r2" = 2 ] && [ "$r3" = 2 ] && [ "$r4" = 2 ] && pasa "T8 uso malo: rc 2 2 2 2" || mal "T8 rc $r1 $r2 $r3 $r4"

echo "$OK/$TOT PASA (set de MAC: $TMAC)"
[ "$OK" = "$TOT" ]
