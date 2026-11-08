#!/usr/bin/env bash
# [PROTEGIDOS-ANTISPOOF-D320] DAY320 E2E del antispoofing (ADR-060 D8, paso 8e.4b) con la MITIGACIÓN REAL.
# Conmutador SOLO durante la prueba: operation.dry_run=false, ddos_mitigacion.habilitada=true y la escalera de prueba
# [60, 120] de d302 (modo descarta). Entrada de prueba en el manifiesto, firmada con argus-infra en la VM etcd:
# 192.168.100.62/32 por eth2 con una MAC que no es la de nadie (02:00:00:00:d3:20); se quita en el trap (dos versiones
# firmadas por corrida). .20 (VM etcd) no se toca.
#   S1 el client manda 20 UDP con origen .62 (entra por eth2 con la MAC del client): SPOOF-MAC +20, 0 llegan a mangle
#   S2 un netns del defender manda 20 UDP con origen .20 por un veth: SPOOF-IF +20, 0 llegan a mangle
#   S3 en toda la corrida el spoofing contado es exactamente lo inyectado (el tráfico legítimo de .20 suma 0) y su
#      entrada del set de protegidos sube (su tráfico llega); la VM etcd sigue sana
#   S4 evidencia en el journal (ARGUS-SPOOF-IF y -MAC), [PROTEGIDOS-SPOOFING] en el log del firewall, sin
#      [PROTEGIDOS-RUTA] ni [PROTEGIDOS-VIGIA] ERROR
# trap: quita .62 del manifiesto, para el pipeline, retira cadenas (filter y raw), sets, netns y reglas de cuenta, y
# restaura el JSON byte a byte (cmp).
# Uso (raiz del repo, Mac; VMs client y etcd arriba): DIA=day320 bash scripts/etcd_ha/d320_antispoof_e2e.sh NOMBRE
#
# PREDICCIÓN (escrita antes de la corrida): S1-S4 PASA; el antispoofing se aplica en modo descarta con redes=3
# (.20, .61, .62), ips_mac=1, mac=1 y sin_ruta=0.
set -u
N=${1:?nombre de la corrida}
export DIA=${DIA:-day320}
H=/vagrant/scripts/timebase/lab_corrida_defender.sh
U=/vagrant/scripts/etcd_ha/d320_manda_udp.py
DM=logs/lab/$DIA/$N
JSON=firewall-acl-agent/config/firewall.json
BAK=/tmp/$N.firewall.json.orig
F=logs/lab/firewall-agent.log
IP62=192.168.100.62; MAL=02:00:00:00:d3:20
NS=argas320e; VA=ase0; VB=ase1
WL=""; BL=""; CHAIN=""; AS=""; SR=""; SI=""; SM=""; K=30
JSON_TOCADO=0; RESTAURADO=0; FALLOS=0; ENTRADA62=0
paso()  { echo; echo "=== [$(date +%T)] $*"; }
falla() { echo; echo "PARADA [$(date +%T)]: $*"; exit 1; }
pasa()  { echo "PASA  $*"; }
mal()   { echo "FALLA $*"; FALLOS=$((FALLOS + 1)); }
# vm VM ORDEN: salida sin la línea [argus] de vagrant y con el código de salida DEL COMANDO REMOTO (no del filtro:
# medido DAY320, con el filtro al final un 'grep -q' remoto sin salida devolvía 1 aunque hubiera casado).
vm()    { local out rc; out=$(vagrant ssh "$1" -c "$2" 2>/dev/null); rc=$?
          [ -n "$out" ] && printf '%s\n' "$out" | tr -d '\r' | grep -v '^\[argus\]'; return $rc; }
infra() { vm etcd "sudo /usr/local/sbin/argus-infra $1"; }
cuenta(){ vm defender "sudo iptables -w -t raw -L $1 -v -x -n 2>/dev/null | awk 'NR == 4 {print \$1}'"; }   # regla 2 = la de cuenta
llegan(){ vm defender "sudo iptables -w -t mangle -L PREROUTING -v -x -n | awk '/$1/ {print \$1}'"; }
restaurar() {
  [ "$RESTAURADO" = 1 ] && return 0
  RESTAURADO=1
  echo; echo "=== [$(date +%T)] TRAP: restaurando el lab"
  if [ "$ENTRADA62" = 1 ]; then
    infra "del --planta lab-vagrant --cidr $IP62/32 --interfaz eth2 --motivo 'fin de la prueba antispoof DAY320' --si" | tail -n 3
  fi
  make pipeline-stop > "/tmp/${N}_stop_trap.txt" 2>&1
  echo "    pipeline-stop rc=$?"
  vm defender "sudo ip netns del $NS 2>/dev/null; sudo ip link del $VA 2>/dev/null; sudo iptables -w -t mangle -D PREROUTING -i eth2 -s $IP62 -m comment --comment d320as-62 2>/dev/null; sudo iptables -w -t mangle -D PREROUTING -i $VA -s 192.168.100.20 -m comment --comment d320as-20 2>/dev/null; true" > /dev/null
  if [ -n "$AS" ]; then
    vm defender "while sudo iptables -w -t raw -D PREROUTING -j $AS 2>/dev/null; do :; done; for c in $AS ${AS}_IF ${AS}_MAC; do sudo iptables -w -t raw -F \$c 2>/dev/null; done; for c in $AS ${AS}_IF ${AS}_MAC; do sudo iptables -w -t raw -X \$c 2>/dev/null; done; while sudo iptables -D INPUT -j $CHAIN 2>/dev/null; do :; done; sudo iptables -F $CHAIN 2>/dev/null; sudo iptables -X $CHAIN 2>/dev/null; for s in $SR $SI $SM $BL $WL; do sudo ipset destroy \$s 2>/dev/null; done; echo \"    quedan raw=\$(sudo iptables -w -t raw -S | grep -c $AS) filter=\$(sudo iptables -S | grep -c $CHAIN) sets=\$(sudo ipset list -n | grep -c -x -e $SR -e $SI -e $SM -e $BL -e $WL)\""
  fi
  if [ "$JSON_TOCADO" = 1 ] && [ -f "$BAK" ]; then
    cp "$BAK" "$JSON"
    if cmp -s "$BAK" "$JSON"; then echo "    JSON restaurado (cmp 0)"; else echo "    ERROR: el JSON NO coincide con $BAK"; fi
  fi
  echo "    el pipeline queda PARADO (como d302); make pipeline-start PROFILE=production para levantarlo"
}
trap restaurar EXIT
trap 'exit 130' INT TERM

paso "1 comprobaciones previas y nombres"
git diff --quiet -- "$JSON" || falla "$JSON tiene cambios sin commit: no se toca"
for v in client etcd; do vagrant status "$v" 2>/dev/null | grep -qE "^$v +running" || falla "la VM $v no está arriba (vagrant up $v)"; done
read -r WL BL CHAIN AS SR SI SM K < <(python3 - "$JSON" <<'PYEOF'
import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
p = d.get("protegidos", {}); a = p.get("antispoof", {})
print(p.get("set_name", "ml_defender_protegidos"), d["ipsets"]["blacklist"]["set_name"], d["iptables"]["chain_name"],
      a.get("cadena", "ARGUS_ANTISPOOF"), a.get("set_redes", "ml_defender_prot_redes"),
      a.get("set_ips_mac", "ml_defender_prot_ipmac"), a.get("set_mac", "ml_defender_prot_mac"),
      p.get("comprobacion_kernel_sec", 30))
PYEOF
) || falla "no leo el JSON"
LIM=$((K + 5))
echo "    cadena raw=$AS sets=$SR,$SI,$SM protegidos=$WL K=$K s"
mkdir -p "$DM"
vm client "ip neigh show 192.168.100.1 dev eth1 | grep -q lladdr" || falla "el client no tiene la MAC de .1 (make lab-e2e-prep)"

paso "2 entrada de prueba $IP62 por eth2 con MAC $MAL (argus-infra, VM etcd)"
infra "add --planta lab-vagrant --categoria intranet --cidr $IP62/32 --interfaz eth2 --mac $MAL --motivo-entrada 'prueba antispoof DAY320' --motivo 'prueba antispoof DAY320 (se quita al acabar)' --si" | tail -n 4
infra "list" | grep -q "$IP62/32" || falla "argus-infra no publicó $IP62"
ENTRADA62=1

paso "3 pipeline-stop y conmutador SOLO para la prueba (copia exacta en $BAK)"
make pipeline-stop > "/tmp/${N}_stop0.txt" 2>&1 || falla "pipeline-stop"
rm -f "$BAK"; cp "$JSON" "$BAK" || falla "copia del JSON"
JSON_TOCADO=1
python3 - "$JSON" <<'PYEOF' || falla "no se pudo conmutar el JSON"
import json, sys
p = sys.argv[1]
d = json.load(open(p, encoding="utf-8"))
d["operation"]["dry_run"] = False
d["ddos_mitigacion"]["habilitada"] = True
d["recidivism"]["strike_durations_sec"] = [60, 120]
with open(p, "w", encoding="utf-8") as f:
    json.dump(d, f, indent=2, ensure_ascii=False)
    f.write("\n")
print("    ahora: dry_run=False habilitada=True escalera=[60, 120] (PRUEBA)")
PYEOF

paso "4 logs a cero y pipeline-start PROFILE=production"
vm defender "DIA=$DIA bash $H truncar" > /dev/null || falla "truncar"
make pipeline-start PROFILE=production > "/tmp/${N}_start.txt" 2>&1 || { tail -n 20 "/tmp/${N}_start.txt"; falla "pipeline-start rc!=0"; }

paso "5 antispoofing en modo descarta con la entrada de prueba (máximo 120 s)"
ok=0
for i in $(seq 1 120); do
  if grep -E "\[PROTEGIDOS-ANTISPOOF\] aplicado .*modo=descarta redes=3 ips_mac=1 mac=1" "$F" > /dev/null 2>&1 && \
     vm defender "sudo ipset save $SM | grep -qi '$IP62,$MAL'"; then ok=1; break; fi
  sleep 1
done
grep "\[PROTEGIDOS-ANTISPOOF\]" "$F" | tail -n 3
[ "$ok" = 1 ] || falla "no aparece el antispoofing en modo descarta con redes=3 ips_mac=1 mac=1 y $IP62 en $SM"
vm defender "sudo iptables -w -t raw -S PREROUTING | sed -n 2p; sudo iptables -w -t raw -S $AS; sudo iptables -w -t raw -S ${AS}_MAC" | sed 's/^/    /'
I0=$(cuenta "${AS}_IF"); M0=$(cuenta "${AS}_MAC")
P0=$(vm defender "sudo ipset save $WL | awk '\$3 ~ /^192\\.168\\.100\\.20,/ {for (i = 4; i < NF; i++) if (\$i == \"packets\") print \$(i + 1)}'")
echo "    contadores al empezar: spoof_if=$I0 spoof_mac=$M0; .20 en $WL=$P0 paquetes"
T0=$(vm defender "date '+%Y-%m-%d %H:%M:%S'")

paso "6 S1 el client manda 20 UDP con origen $IP62 (MAC del client)"
vm defender "sudo iptables -w -t mangle -I PREROUTING 1 -i eth2 -s $IP62 -m comment --comment d320as-62" > /dev/null
vm client "sudo python3 -I $U $IP62 192.168.100.1 20"
sleep 2
M1=$(cuenta "${AS}_MAC"); L62=$(llegan d320as-62)
[ "$((M1 - M0))" = 20 ] && [ "${L62:-x}" = 0 ] && pasa "S1 SPOOF-MAC +$((M1 - M0)), llegan a mangle $L62" || mal "S1 SPOOF-MAC +$((M1 - M0)) (esperado 20), llegan a mangle ${L62:-?} (esperado 0)"

paso "7 S2 un netns del defender manda 20 UDP con origen .20 por un veth"
vm defender "sudo ip netns add $NS && sudo ip link add $VA type veth peer name $VB && sudo ip link set $VB netns $NS && sudo ip addr add 10.252.0.1/30 dev $VA && sudo ip link set $VA up && sudo ip -n $NS addr add 10.252.0.2/30 dev $VB && sudo ip -n $NS link set $VB up && sudo ip netns exec $NS ping -c1 -W1 10.252.0.1 > /dev/null; sudo iptables -w -t mangle -I PREROUTING 1 -i $VA -s 192.168.100.20 -m comment --comment d320as-20" > /dev/null
I1a=$(cuenta "${AS}_IF")
vm defender "sudo ip netns exec $NS python3 -I $U 192.168.100.20 10.252.0.1 20"
sleep 2
I1=$(cuenta "${AS}_IF"); L20=$(llegan d320as-20)
[ "$((I1 - I1a))" = 20 ] && [ "${L20:-x}" = 0 ] && pasa "S2 SPOOF-IF +$((I1 - I1a)), llegan a mangle $L20" || mal "S2 SPOOF-IF +$((I1 - I1a)) (esperado 20), llegan a mangle ${L20:-?} (esperado 0)"

paso "8 S3 el tráfico legítimo de .20 no cuenta (70 s, chrony de la VM etcd cada 64 s)"
sleep 70
I2=$(cuenta "${AS}_IF"); M2=$(cuenta "${AS}_MAC")
P2=$(vm defender "sudo ipset save $WL | awk '\$3 ~ /^192\\.168\\.100\\.20,/ {for (i = 4; i < NF; i++) if (\$i == \"packets\") print \$(i + 1)}'")
[ "$((I2 - I0))" = 20 ] && [ "$((M2 - M0))" = 20 ] && [ "${P2:-0}" -gt "${P0:-0}" ] \
  && pasa "S3 spoofing contado = inyectado (interfaz +$((I2 - I0)), mac +$((M2 - M0))); .20 legítima $P0 -> $P2 paquetes" \
  || mal "S3 interfaz +$((I2 - I0)) mac +$((M2 - M0)) (esperado 20 y 20); .20 legítima ${P0:-?} -> ${P2:-?}"
make pipeline-status > "/tmp/${N}_status.txt" 2>&1
grep -q "etcd-server:   RUNNING" "/tmp/${N}_status.txt" && pasa "S3 la VM etcd sigue sana (pipeline-status)" || { mal "S3 etcd-server no RUNNING"; grep etcd "/tmp/${N}_status.txt"; }

paso "9 S4 evidencia y log"
JI=$(vm defender "sudo journalctl -k --since '$T0' --no-pager | grep -c 'ARGUS-SPOOF-IF '")
JM=$(vm defender "sudo journalctl -k --since '$T0' --no-pager | grep -c 'ARGUS-SPOOF-MAC '")
[ "${JI:-0}" -ge 1 ] && [ "${JM:-0}" -ge 1 ] && pasa "S4 journal: ARGUS-SPOOF-IF=$JI ARGUS-SPOOF-MAC=$JM" || mal "S4 journal: IF=${JI:-?} MAC=${JM:-?} (esperado >= 1 cada una)"
vm defender "sudo journalctl -k --since '$T0' --no-pager | grep -m 1 'ARGUS-SPOOF-MAC '" | cut -c1-220 | sed 's/^/    /'
ns=$(grep -c "\[PROTEGIDOS-SPOOFING\]" "$F"); nr=$(grep -c "\[PROTEGIDOS-RUTA\]" "$F"); ne=$(grep -c "\[PROTEGIDOS-VIGIA\] ERROR" "$F")
grep "\[PROTEGIDOS-SPOOFING\]" "$F" | tail -n 2 | sed 's/^/    /'
[ "$ns" -ge 1 ] && [ "$nr" = 0 ] && [ "$ne" = 0 ] && pasa "S4 [PROTEGIDOS-SPOOFING]=$ns, [PROTEGIDOS-RUTA]=0, ERROR=0" || mal "S4 SPOOFING=$ns RUTA=$nr ERROR=$ne (esperado >=1, 0, 0)"
cp "$F" "$DM/firewall-agent.log" 2>/dev/null
echo; echo "=== RESULTADO $([ "$FALLOS" = 0 ] && echo PASA || echo "FALLA ($FALLOS)") — $DM/"
[ "$FALLOS" = 0 ]
