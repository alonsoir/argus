#!/usr/bin/env bash
# DAY300 E2E de rangos protegidos [PROTEGIDOS-D300]: ataque simultaneo desde .50 (no protegido) y .61
# (intranet en el JSON del lab). Arranque limpio (CSV de estado borrado), captura en eth2, contabilidad y analisis.
# Uso (raiz del repo, Mac): bash scripts/timebase/d300_protegidos_e2e.sh NOMBRE
set -u
N=${1:?nombre de la corrida}
DIA=${DIA:-day300}
H=/vagrant/scripts/timebase/lab_corrida_defender.sh
D=/vagrant/logs/lab/$DIA/$N
CSV=/var/lib/argus/sniffer/ddos_victim_estado.csv
CLI=/tmp/$N.client.txt
FIL='dst host 192.168.100.1'
paso()  { echo; echo "=== [$(date +%T)] $*"; }
falla() { echo; echo "PARADA [$(date +%T)]: $*"; exit 1; }
marca() { vagrant ssh defender -c "mkdir -p $D && echo \"$1 \$(date +%s.%N)\" >> $D/tiempos.txt"; }

paso "0 lab-clock-step"
make lab-clock-step || falla "relojes no alineados"
paso "1 alias .51 en el client"
vagrant ssh client -c "ip -4 addr show dev eth1 | grep -q 192.168.100.51" || falla "falta 192.168.100.51 en eth1 del client"
paso "2 pipeline-stop y comprobacion"
make pipeline-stop || falla "pipeline-stop"
vagrant ssh defender -c "DIA=$DIA bash $H vivos" || falla "quedan procesos vivos"
paso "3 logs a cero y CSV de estado borrado"
vagrant ssh defender -c "DIA=$DIA bash $H truncar" || falla "truncar"
vagrant ssh defender -c "sudo rm -f $CSV && mkdir -p $D && : > $D/tiempos.txt" || falla "borrar CSV"
paso "4 pipeline-start PROFILE=production"
make pipeline-start PROFILE=production > "/tmp/${N}_start.txt" 2>&1 || { tail -n 20 "/tmp/${N}_start.txt"; falla "pipeline-start rc!=0"; }
if grep -E '^[[:space:]]*❌.*STOPPED' "/tmp/${N}_start.txt"; then falla "algun componente STOPPED"; fi
paso "5 esperar ESTABLE"
bash scripts/timebase/d303_esperar_estable_lab.sh || falla "esperar_estable"  # [ARGUS-ESTABLE-LAB-D303] fondo ICMP controlado
marca estable
paso "6 captura en eth2 ($FIL)"
vagrant ssh defender -c "DIA=$DIA FILTRO='$FIL' bash $H cap_start $N" || falla "no arranca tcpdump"
paso "7 client en segundo plano"
vagrant ssh client -c "setsid nohup bash /vagrant/scripts/timebase/d300_protegidos_client.sh > $CLI 2>&1 < /dev/null & sleep 2; pgrep -af '^(sudo )?tcpreplay'" || falla "el trafico del client no esta en marcha"
marca inicio_cliente
paso "8 esperar el fin del cliente (hasta 450 s)"
ok=0
for i in $(seq 1 450); do
  if vagrant ssh client -c "grep -q fin_base $CLI" 2>/dev/null; then ok=1; break; fi
  sleep 1
done
[ "$ok" = 1 ] || falla "no aparece fin_base en $CLI"
marca fin_cliente
sleep 15
paso "9 fin de captura"
vagrant ssh defender -c "DIA=$DIA bash $H cap_stop $N" || falla "cap_stop"
paso "10 pipeline-stop"
make pipeline-stop || falla "pipeline-stop final"
paso "11 contabilidad y copia"
vagrant ssh defender -c "DIA=$DIA bash $H contar $N" || falla "contar"
vagrant ssh client -c "cat $CLI"
paso "12 analisis de los rangos protegidos"
vagrant ssh defender -c "bash /vagrant/scripts/timebase/d300_protegidos_analisis.sh" || falla "analisis"
echo; echo "=== [$(date +%T)] HECHO: logs/lab/$DIA/$N/"
