#!/usr/bin/env bash
# [PROTEGIDOS-VIGIA-D320] DAY320 E2E del vigía kernel <-> manifiesto (ADR-060 D8, paso 8e.4a), con el pipeline vivo.
# Conmutador SOLO durante la prueba: operation.dry_run=false (con dry_run el agente no toca el kernel y el vigía no
# compara). La mitigación se deja como esté en el JSON. Con el pipeline arrancado se estropea el kernel cuatro veces,
# como lo haría alguien con root, y se mide que el vigía lo detecta ([PROTEGIDOS-DIVERGENCIA]), lo reconcilia
# ([PROTEGIDOS-RECONCILIADO]) y lo deja como dice el manifiesto:
#   E1 una entrada de más en el set de protegidos      E3 la entrada de .20 cambiada a nomatch
#   E2 la regla RETURN de protegidos borrada           E4 una regla ajena delante del salto INPUT -> cadena
# trap: para el pipeline, retira la regla ajena, la cadena y los sets, y restaura el JSON byte a byte (cmp).
# Uso (raiz del repo, Mac): DIA=day320 bash scripts/etcd_ha/d320_vigia_e2e.sh NOMBRE
#
# PREDICCIÓN (escrita antes de la corrida):
#  V0 al arrancar: [PROTEGIDOS-VIGIA] kernel <-> manifiesto cada K s (K = protegidos.comprobacion_kernel_sec del JSON)
#     y, en la primera vuelta, 0 divergencias (el agente acaba de aplicar el vigente).
#  E1..E4: cada una reconciliada en <= K + 5 s (una vuelta del vigía más el sondeo de 1 s), con su DIVERGENCIA y su
#     RECONCILIADO en el log del firewall, y el kernel queda igual que antes de estropearlo.
#  Final: 0 líneas [PROTEGIDOS-VIGIA] ERROR.
set -u
N=${1:?nombre de la corrida}
export DIA=${DIA:-day320}
H=/vagrant/scripts/timebase/lab_corrida_defender.sh
DM=logs/lab/$DIA/$N
JSON=firewall-acl-agent/config/firewall.json
BAK=/tmp/$N.firewall.json.orig
F=logs/lab/firewall-agent.log
WL=""; CHAIN=""; BL=""; AS=""; SR=""; SI=""; SM=""; K=0
JSON_TOCADO=0; RESTAURADO=0; FALLOS=0
paso()  { echo; echo "=== [$(date +%T)] $*"; }
falla() { echo; echo "PARADA [$(date +%T)]: $*"; exit 1; }
pasa()  { echo "PASA  $*"; }
mal()   { echo "FALLA $*"; FALLOS=$((FALLOS + 1)); }
def()   { vagrant ssh defender -c "$1" 2>/dev/null | tr -d '\r' | grep -v '^\[argus\]'; }
restaurar() {
  [ "$RESTAURADO" = 1 ] && return 0
  RESTAURADO=1
  echo; echo "=== [$(date +%T)] TRAP: restaurando el lab"
  make pipeline-stop > "/tmp/${N}_stop_trap.txt" 2>&1
  echo "    pipeline-stop rc=$?"
  def "sudo iptables -D INPUT -m comment --comment d320-vigia-extra 2>/dev/null; true" > /dev/null
  if [ -n "$WL" ]; then
    # [PROTEGIDOS-LIMPIEZA-D320] también la cadena raw del antispoofing y sus sets (medido DAY320: quedaban sets=1).
    def "sudo bash /vagrant/scripts/etcd_ha/d320_limpia_kernel.sh $CHAIN $AS $SR $SI $SM $BL $WL; echo \"    quedan reglas d320-vigia-extra=\$(sudo iptables -S | grep -c d320-vigia-extra)\""
  fi
  if [ "$JSON_TOCADO" = 1 ] && [ -f "$BAK" ]; then
    cp "$BAK" "$JSON"
    if cmp -s "$BAK" "$JSON"; then echo "    JSON restaurado (cmp 0)"; else echo "    ERROR: el JSON NO coincide con $BAK"; fi
  fi
  echo "    el pipeline queda PARADO (como d302); make pipeline-start PROFILE=production para levantarlo"
}
trap restaurar EXIT
trap 'exit 130' INT TERM

paso "1 JSON de serie, nombres y periodo del vigía"
git diff --quiet -- "$JSON" || falla "$JSON tiene cambios sin commit: no se toca"
read -r WL CHAIN BL K AS SR SI SM < <(python3 - "$JSON" <<'PYEOF'
import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
p = d.get("protegidos", {}); a = p.get("antispoof", {})
print(p.get("set_name", "ml_defender_protegidos"), d["iptables"]["chain_name"], d["ipsets"]["blacklist"]["set_name"],
      p.get("comprobacion_kernel_sec", 30), a.get("cadena", "ARGUS_ANTISPOOF"), a.get("set_redes", "ml_defender_prot_redes"),
      a.get("set_ips_mac", "ml_defender_prot_ipmac"), a.get("set_mac", "ml_defender_prot_mac"))
PYEOF
) || falla "no leo el JSON"
[ -n "$WL" ] && [ -n "$CHAIN" ] && [ "$K" -ge 5 ] 2>/dev/null || falla "JSON sin protegidos.set_name / iptables.chain_name / comprobacion_kernel_sec"
LIM=$((K + 5))
echo "    set=$WL cadena=$CHAIN blacklist=$BL K=$K s (límite por evento: $LIM s)"
mkdir -p "$DM"

paso "2 pipeline-stop y conmutador SOLO para la prueba (copia exacta en $BAK)"
make pipeline-stop > "/tmp/${N}_stop0.txt" 2>&1 || falla "pipeline-stop"
rm -f "$BAK"; cp "$JSON" "$BAK" || falla "copia del JSON"
JSON_TOCADO=1
python3 - "$JSON" <<'PYEOF' || falla "no se pudo conmutar el JSON"
import json, sys
p = sys.argv[1]
d = json.load(open(p, encoding="utf-8"))
antes = d["operation"]["dry_run"]
d["operation"]["dry_run"] = False
with open(p, "w", encoding="utf-8") as f:
    json.dump(d, f, indent=2, ensure_ascii=False)
    f.write("\n")
print(f"    antes: dry_run={antes}; ahora: dry_run=False (PRUEBA); ddos_mitigacion sin tocar")
PYEOF

paso "3 logs a cero y pipeline-start PROFILE=production"
def "DIA=$DIA bash $H truncar" > /dev/null || falla "truncar"
make pipeline-start PROFILE=production > "/tmp/${N}_start.txt" 2>&1 || { tail -n 20 "/tmp/${N}_start.txt"; falla "pipeline-start rc!=0"; }

paso "4 V0: vigía en marcha y set con el vigente (máximo 90 s)"
ok=0
for i in $(seq 1 90); do
  grep -q "\[PROTEGIDOS-VIGIA\] kernel <-> manifiesto cada $K s" "$F" 2>/dev/null && ok=1 && break
  sleep 1
done
[ "$ok" = 1 ] || falla "no aparece '[PROTEGIDOS-VIGIA] kernel <-> manifiesto cada $K s' en $F"
grep -m 1 "\[PROTEGIDOS-VIGIA\] kernel" "$F"
grep -m 1 "\[PROTEGIDOS-MANIFIESTO\] verificado" "$F" || falla "el firewall no tiene manifiesto vigente: no hay nada que vigilar"
LISTA="sudo ipset save $WL | grep '^add ' | sed -E 's/^add [^ ]+ //; s/ packets [0-9]+ bytes [0-9]+//' | sort"  # sin contadores
ANTES_SET=$(def "$LISTA")
[ -n "$ANTES_SET" ] || falla "el set $WL está vacío o no existe"
ANTES_REG=$(def "sudo iptables -S $CHAIN; sudo iptables -S INPUT | sed -n 2p")
echo "$ANTES_SET" | sed 's/^/    /'
sleep "$LIM"
n=$(grep -c "\[PROTEGIDOS-DIVERGENCIA\]" "$F")
[ "$n" = 0 ] && pasa "V0 primera vuelta del vigía sin divergencias" || mal "V0 $n divergencias sin haber tocado nada"

evento() {  # nombre, orden que estropea (en el defender), comprobación de que quedó bien (en el defender, rc 0)
  local nom=$1 rompe=$2 bien=$3 base t0 t1 ok=0
  base=$(wc -l < "$F")
  def "$rompe" > /dev/null
  t0=$(date +%s)
  while [ $(( $(date +%s) - t0 )) -le "$LIM" ]; do
    if def "$bien && echo SI" | grep -q '^SI$'; then ok=1; break; fi
    sleep 1
  done
  t1=$(date +%s)
  sleep 2
  local div rec
  div=$(tail -n +"$((base + 1))" "$F" | grep -c "\[PROTEGIDOS-DIVERGENCIA\]")
  rec=$(tail -n +"$((base + 1))" "$F" | grep -c "\[PROTEGIDOS-RECONCILIADO\]")
  tail -n +"$((base + 1))" "$F" | grep -E "\[PROTEGIDOS-(DIVERGENCIA|RECONCILIADO|VIGIA)\]" | sed 's/^/    /' | cut -c1-230
  if [ "$ok" = 1 ] && [ "$div" -ge 1 ] && [ "$rec" -ge 1 ]; then
    pasa "$nom reconciliado en $((t1 - t0)) s (límite $LIM), DIVERGENCIA=$div RECONCILIADO=$rec"
  else
    mal "$nom: quedó bien=$ok en $((t1 - t0)) s, DIVERGENCIA=$div RECONCILIADO=$rec"
  fi
  echo "$nom $((t1 - t0)) ok=$ok div=$div rec=$rec" >> "$DM/eventos.txt"
}

paso "5 E1 una entrada de más (10.66.6.6/32,eth2)"
evento "E1" "sudo ipset add $WL 10.66.6.6/32,eth2" "! sudo ipset save $WL | grep -q '10\\.66\\.6\\.6'"
paso "6 E2 la regla RETURN de protegidos borrada"
evento "E2" "sudo iptables -D $CHAIN -m set --match-set $WL src,src -m comment --comment argus-protegidos -j RETURN" \
  "sudo iptables -S $CHAIN | sed -n 2p | grep -q -- '--match-set $WL src,src .*-j RETURN'"
paso "7 E3 la entrada de .20 cambiada a nomatch"
E20=$(echo "$ANTES_SET" | awk '$1 ~ /^192\.168\.100\.20,/ {print $1}')
[ -n "$E20" ] || falla "el vigente no tiene 192.168.100.20 (P1): no se puede probar E3"
evento "E3" "sudo ipset del $WL $E20 && sudo ipset add $WL $E20 nomatch" "! sudo ipset save $WL | grep -q nomatch && sudo ipset save $WL | grep -q '^add $WL $E20 '"
paso "8 E4 una regla ajena delante del salto INPUT -> $CHAIN"
evento "E4" "sudo iptables -I INPUT 1 -m comment --comment d320-vigia-extra" "sudo iptables -S INPUT | sed -n 2p | grep -qx -- '-A INPUT -j $CHAIN'"
def "sudo iptables -D INPUT -m comment --comment d320-vigia-extra 2>/dev/null; true" > /dev/null

paso "9 el kernel queda como al principio y sin errores del vigía"
DESPUES_SET=$(def "$LISTA")
DESPUES_REG=$(def "sudo iptables -S $CHAIN; sudo iptables -S INPUT | sed -n 2p")
[ "$ANTES_SET" = "$DESPUES_SET" ] && pasa "set $WL igual que antes de las pruebas" || { mal "set distinto"; diff <(echo "$ANTES_SET") <(echo "$DESPUES_SET"); }
[ "$ANTES_REG" = "$DESPUES_REG" ] && pasa "cadena $CHAIN y salto INPUT iguales que antes" || { mal "reglas distintas"; diff <(echo "$ANTES_REG") <(echo "$DESPUES_REG"); }
e=$(grep -c "\[PROTEGIDOS-VIGIA\] ERROR" "$F")
[ "$e" = 0 ] && pasa "0 líneas [PROTEGIDOS-VIGIA] ERROR" || mal "$e líneas [PROTEGIDOS-VIGIA] ERROR"
cp "$F" "$DM/firewall-agent.log" 2>/dev/null
echo; echo "=== RESULTADO $([ "$FALLOS" = 0 ] && echo PASA || echo "FALLA ($FALLOS)") — $DM/"
[ "$FALLOS" = 0 ]
