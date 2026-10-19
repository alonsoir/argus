#!/usr/bin/env bash
# DAY302 E2E de la mitigacion REAL de ddos_v2 [DDOS-MITIGACION-B2-D302]. Conmutador SOLO durante la prueba:
# operation.dry_run=false, ddos_mitigacion.habilitada=true, recidivism.strike_durations_sec=[60, 120] (escalera de
# PRUEBA, decision de Alonso DAY302). Dos ataques NTP desde .50 (+ .61 protegido) con pausa; base .51 todo el rato.
# trap: restaura el JSON byte a byte (cmp), para el pipeline, retira cadena y sets del defender y realinea relojes.
# Uso (raiz del repo, Mac): bash scripts/timebase/d302_mitigacion_e2e.sh NOMBRE 2>&1 | tee /tmp/d302_NOMBRE.txt
set -u
N=${1:?nombre de la corrida}
export DIA=${DIA:-day302}
H=/vagrant/scripts/timebase/lab_corrida_defender.sh
D=/vagrant/logs/lab/$DIA/$N
DM=logs/lab/$DIA/$N
CSV=/var/lib/argus/sniffer/ddos_victim_estado.csv
CLI=/tmp/$N.client.txt
FIL='dst host 192.168.100.1'
JSON=firewall-acl-agent/config/firewall.json
BAK=/tmp/$N.firewall.json.orig
CHAIN=ML_DEFENDER_TEST
F=logs/lab/firewall-agent.log
BL=""
WL=""
JSON_TOCADO=0
RESTAURADO=0
paso()  { echo; echo "=== [$(date +%T)] $*"; }
falla() { echo; echo "PARADA [$(date +%T)]: $*"; exit 1; }
marca() { vagrant ssh defender -c "mkdir -p $D && echo \"$1 \$(date +%s.%N)\" >> $D/tiempos.txt" > /dev/null 2>&1; }
restaurar() {
  [ "$RESTAURADO" = 1 ] && return 0
  RESTAURADO=1
  echo; echo "=== [$(date +%T)] TRAP: restaurando el lab"
  vagrant ssh defender -c "touch $D/parar_muestreo" > /dev/null 2>&1
  make pipeline-stop > "/tmp/${N}_stop_trap.txt" 2>&1
  echo "    pipeline-stop rc=$?"
  if [ -n "$BL" ]; then
    vagrant ssh defender -c "while sudo iptables -D INPUT -j $CHAIN 2>/dev/null; do :; done; sudo iptables -F $CHAIN 2>/dev/null; sudo iptables -X $CHAIN 2>/dev/null; sudo ipset destroy $BL 2>/dev/null; sudo ipset destroy $WL 2>/dev/null; echo \"    quedan reglas=\$(sudo iptables -S | grep -c $CHAIN) sets=\$(sudo ipset list -n | grep -c -x -e $BL -e $WL)\"" 2>/dev/null | tr -d '\r' | grep -v '^\[argus\]'
  fi
  if [ "$JSON_TOCADO" = 1 ] && [ -f "$BAK" ]; then
    cp "$BAK" "$JSON"
    if cmp -s "$BAK" "$JSON"; then echo "    JSON restaurado (cmp 0)"; else echo "    ERROR: el JSON NO coincide con $BAK"; fi
  fi
  make lab-clock-step > "/tmp/${N}_clock_trap.txt" 2>&1
  echo "    lab-clock-step rc=$?"
}
trap restaurar EXIT
trap 'exit 130' INT TERM

paso "0 lab-clock-step"
make lab-clock-step || falla "relojes no alineados"
paso "1 alias .51 en el client, JSON de serie y nombres de los sets"
vagrant ssh client -c "ip -4 addr show dev eth1 | grep -q 192.168.100.51" || falla "falta 192.168.100.51 en eth1 del client (sudo ip addr add 192.168.100.51/24 dev eth1)"
git diff --quiet -- "$JSON" || falla "$JSON tiene cambios sin commit: no se toca"
BL=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["ipsets"]["blacklist"]["set_name"])' "$JSON") || falla "no leo ipsets.blacklist.set_name"
WL=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["ipsets"]["whitelist"]["set_name"])' "$JSON") || falla "no leo ipsets.whitelist.set_name"
echo "    blacklist=$BL whitelist=$WL cadena=$CHAIN"
paso "2 pipeline-stop y comprobacion"
make pipeline-stop > "/tmp/${N}_stop0.txt" 2>&1 || falla "pipeline-stop"
vagrant ssh defender -c "DIA=$DIA bash $H vivos" || falla "quedan procesos vivos"
paso "3 estado previo de iptables/ipset en el defender"
vagrant ssh defender -c "echo \"    reglas=\$(sudo iptables -S | grep -c $CHAIN) sets=\$(sudo ipset list -n | grep -c -x -e $BL -e $WL)\"" 2>/dev/null | tr -d '\r' | grep -v '^\[argus\]'
paso "4 conmutador SOLO para la prueba (copia exacta en $BAK)"
rm -f "$BAK"
cp "$JSON" "$BAK" || falla "copia del JSON"
JSON_TOCADO=1
python3 - "$JSON" <<'PYEOF' || falla "no se pudo conmutar el JSON"
import json, sys
p = sys.argv[1]
d = json.load(open(p, encoding="utf-8"))
antes = (d["operation"]["dry_run"], d["ddos_mitigacion"]["habilitada"], d["recidivism"]["strike_durations_sec"])
d["operation"]["dry_run"] = False
d["ddos_mitigacion"]["habilitada"] = True
d["recidivism"]["strike_durations_sec"] = [60, 120]
with open(p, "w", encoding="utf-8") as f:
    json.dump(d, f, indent=2, ensure_ascii=False)
    f.write("\n")
print(f"    antes: dry_run={antes[0]} habilitada={antes[1]} escalera={antes[2]}")
print("    ahora: dry_run=False habilitada=True escalera=[60, 120] (PRUEBA)")
PYEOF
paso "5 logs a cero y CSV de estado borrado"
vagrant ssh defender -c "DIA=$DIA bash $H truncar" || falla "truncar"
vagrant ssh defender -c "sudo rm -f $CSV && mkdir -p $D && : > $D/tiempos.txt && rm -f $D/parar_muestreo $D/muestreo.txt" || falla "preparar"
paso "6 pipeline-start PROFILE=production"
make pipeline-start PROFILE=production > "/tmp/${N}_start.txt" 2>&1 || { tail -n 20 "/tmp/${N}_start.txt"; falla "pipeline-start rc!=0"; }
if grep -E '^[[:space:]]*❌.*STOPPED' "/tmp/${N}_start.txt"; then falla "algun componente STOPPED"; fi
paso "7 firewall en modo ACTIVA con cadena y sets (maximo 90 s)"
ok=0
for i in $(seq 1 90); do
  if grep -q "\[DDOS-MITIGACION\] modo: ACTIVA" "$F" 2>/dev/null; then ok=1; break; fi
  sleep 1
done
[ "$ok" = 1 ] || falla "no aparece '[DDOS-MITIGACION] modo: ACTIVA' en $F"
grep -E "\[DDOS-MITIGACION\] modo|CONFIG-AVISO\] recidivism" "$F" | head -n 3
vagrant ssh defender -c "sudo iptables -S $CHAIN && sudo ipset list -n | grep -x -e $BL -e $WL" 2>/dev/null | tr -d '\r' | grep -v '^\[argus\]' || falla "faltan la cadena $CHAIN o los sets"
paso "8 esperar ESTABLE"
vagrant ssh defender -c "bash /vagrant/day288_esperar_estable.sh" || falla "esperar_estable"
marca estable
paso "9 captura en eth2 ($FIL)"
vagrant ssh defender -c "DIA=$DIA FILTRO='$FIL' bash $H cap_start $N" || falla "no arranca tcpdump"
paso "10 muestreo de ipset e iptables en el defender (cada 1 s)"
vagrant ssh defender -c "setsid nohup bash /vagrant/scripts/timebase/d302_muestreo_defender.sh $D/muestreo.txt $D/parar_muestreo $BL $CHAIN > /dev/null 2>&1 < /dev/null & sleep 2" > /dev/null 2>&1
sleep 5
[ -s "$DM/muestreo.txt" ] || falla "el muestreo no escribe en $DM/muestreo.txt"
tail -n 1 "$DM/muestreo.txt"
paso "11 client en segundo plano (base 450 s; ataques a los 60 s y a los 240 s, 60 s cada uno)"
vagrant ssh client -c "setsid nohup bash /vagrant/scripts/timebase/d302_mitigacion_client.sh > $CLI 2>&1 < /dev/null & sleep 8; pgrep -af '^(sudo )?tcpreplay'" || falla "el trafico del client no esta en marcha"
marca inicio_cliente
paso "12 esperando fin_base (hasta 600 s); progreso cada ~30 s"
ok=0
t0=$(date +%s)
ult=0
while [ $(( $(date +%s) - t0 )) -lt 600 ]; do
  if vagrant ssh client -c "grep -q fin_base $CLI" 2>/dev/null; then ok=1; break; fi
  if vagrant ssh client -c "grep -q PARADA $CLI" 2>/dev/null; then break; fi
  ahora=$(date +%s)
  if [ $((ahora - ult)) -ge 30 ]; then
    ult=$ahora
    echo "    [$(date +%T)] $(tail -n 1 "$DM/muestreo.txt" 2>/dev/null | cut -c1-200)"
  fi
  sleep 2
done
[ "$ok" = 1 ] || { vagrant ssh client -c "cat $CLI"; falla "no aparece fin_base en $CLI"; }
marca fin_cliente
sleep 15
paso "13 fin del muestreo y de la captura"
vagrant ssh defender -c "touch $D/parar_muestreo" > /dev/null 2>&1
sleep 3
vagrant ssh defender -c "DIA=$DIA bash $H cap_stop $N" || falla "cap_stop"
paso "14 pipeline-stop"
make pipeline-stop > "/tmp/${N}_stop1.txt" 2>&1 || falla "pipeline-stop final"
paso "15 contabilidad y salida del client"
vagrant ssh defender -c "DIA=$DIA bash $H contar $N" || falla "contar"
vagrant ssh client -c "cat $CLI" 2>/dev/null | tr -d '\r' | grep -v '^\[argus\]' > "$DM/cliente.txt"
cat "$DM/cliente.txt"
paso "16 analisis y criterios PASA/FALLA"
bash scripts/timebase/d302_mitigacion_analisis.sh "$DM"
rc=$?
echo; echo "=== [$(date +%T)] HECHO: $DM/ (analisis rc=$rc)"
exit $rc
