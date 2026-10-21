#!/usr/bin/env bash
# DAY300 E2E del reinicio del sniffer a mitad de un ataque de 60 pps (por debajo de abs_pps=200).
# MODO: antes (parada ordenada + CSV borrado) | ordenada (sniffer-stop) | kill9 (pkill -KILL).
# Las tres corridas empiezan sin CSV de estado. Detecta el inicio del ataque en el client, espera 120 s,
# reinicia y anota instantes y lineas del ml-detector.log (al marcar y con el sniffer YA parado).
# Captura en eth2 (dst host .1) para contar el cable. Para al primer fallo.
# Uso (raiz del repo, Mac): bash scripts/timebase/d300_reinicio_e2e.sh MODO NOMBRE
set -u
MODO=${1:?modo: antes|ordenada|kill9}
N=${2:?nombre de la corrida}
case "$MODO" in antes|ordenada|kill9) ;; *) echo "MODO invalido: $MODO"; exit 2;; esac
DIA=${DIA:-day300}
H=/vagrant/scripts/timebase/lab_corrida_defender.sh
D=/vagrant/logs/lab/$DIA/$N
CSV=/var/lib/argus/sniffer/ddos_victim_estado.csv
CLI=/tmp/$N.client.txt
FIL='dst host 192.168.100.1'
paso()  { echo; echo "=== [$(date +%T)] $*"; }
falla() { echo; echo "PARADA [$(date +%T)]: $*"; exit 1; }
marca() { vagrant ssh defender -c "mkdir -p $D && echo \"$1 \$(date +%s.%N)\" >> $D/tiempos.txt"; }
marca_linea() { vagrant ssh defender -c "echo \"$1 \$(wc -l < /vagrant/logs/lab/ml-detector.log)\" >> $D/tiempos.txt"; }

paso "0 lab-clock-step"
make lab-clock-step || falla "relojes no alineados"
paso "1 alias .51 en el client"
vagrant ssh client -c "ip -4 addr show dev eth1 | grep -q 192.168.100.51" || falla "falta 192.168.100.51 en eth1 del client (sudo ip addr add 192.168.100.51/24 dev eth1)"
paso "2 pipeline-stop y comprobacion"
make pipeline-stop || falla "pipeline-stop"
vagrant ssh defender -c "DIA=$DIA bash $H vivos" || falla "quedan procesos vivos"
paso "3 logs a cero y CSV de estado borrado (las tres corridas empiezan igual)"
vagrant ssh defender -c "DIA=$DIA bash $H truncar" || falla "truncar"
vagrant ssh defender -c "sudo rm -f $CSV && mkdir -p $D && : > $D/tiempos.txt && echo modo $MODO >> $D/tiempos.txt" || falla "borrar CSV"
paso "4 pipeline-start PROFILE=production"
make pipeline-start PROFILE=production > "/tmp/${N}_start.txt" 2>&1 || { tail -n 20 "/tmp/${N}_start.txt"; falla "pipeline-start rc!=0"; }
if grep -E '^[[:space:]]*❌.*STOPPED' "/tmp/${N}_start.txt"; then falla "algun componente STOPPED"; fi
paso "5 esperar ESTABLE"
bash scripts/timebase/d303_esperar_estable_lab.sh || falla "esperar_estable"  # [ARGUS-ESTABLE-LAB-D303] fondo ICMP controlado
marca estable
paso "6 captura en eth2 ($FIL)"
vagrant ssh defender -c "DIA=$DIA FILTRO='$FIL' bash $H cap_start $N" || falla "no arranca tcpdump"
paso "7 client en segundo plano"
vagrant ssh client -c "setsid nohup bash /vagrant/scripts/timebase/d300_reinicio_client.sh > $CLI 2>&1 < /dev/null & sleep 2; pgrep -af '^(sudo )?tcpreplay'" || falla "el trafico del client no esta en marcha"
marca inicio_cliente
paso "8 esperar el inicio del ataque (hasta 150 s)"
ok=0
for i in $(seq 1 150); do
  if vagrant ssh client -c "grep -q inicio_ataque $CLI" 2>/dev/null; then ok=1; break; fi
  sleep 1
done
[ "$ok" = 1 ] || falla "no aparece inicio_ataque en $CLI"
marca ataque_visto
paso "9 120 s de ataque antes del reinicio"
sleep 120
paso "10 REINICIO ($MODO)"
marca_linea linea_ml_reinicio
marca reinicio_inicio
case "$MODO" in
  antes)
    make sniffer-stop || falla "sniffer-stop"
    vagrant ssh defender -c "sudo rm -f $CSV" || falla "borrar CSV"
    ;;
  ordenada)
    make sniffer-stop || falla "sniffer-stop"
    ;;
  kill9)
    vagrant ssh defender -c "sudo pkill -KILL -x sniffer; for i in 1 2 3 4 5; do pgrep -x sniffer >/dev/null || break; sleep 1; done; tmux kill-session -t sniffer 2>/dev/null || true" || falla "kill -9"
    ;;
esac
marca sniffer_parado
marca_linea linea_ml_parado
make sniffer-start PROFILE=production || falla "sniffer-start"
marca reinicio_fin
paso "11 esperar el fin del cliente (hasta 600 s)"
ok=0
for i in $(seq 1 600); do
  if vagrant ssh client -c "grep -q fin_base $CLI" 2>/dev/null; then ok=1; break; fi
  sleep 1
done
[ "$ok" = 1 ] || falla "no aparece fin_base en $CLI"
marca fin_cliente
sleep 15
paso "12 fin de captura"
vagrant ssh defender -c "DIA=$DIA bash $H cap_stop $N" || falla "cap_stop"
paso "13 pipeline-stop"
make pipeline-stop || falla "pipeline-stop final"
paso "14 contabilidad y copia"
vagrant ssh defender -c "DIA=$DIA bash $H contar $N" || falla "contar"
vagrant ssh client -c "cat $CLI"
paso "15 analisis"
vagrant ssh defender -c "bash /vagrant/scripts/timebase/d300_reinicio_analisis.sh $D" || falla "analisis"
echo; echo "=== [$(date +%T)] HECHO: logs/lab/$DIA/$N/"
