#!/usr/bin/env bash
# DAY311 [ETCD-REINICIO-D311] instrumento de medida (se commitea): reiniciar el etcd-server con el pipeline vivo y
# trafico benigno, y medir la clave del bronce (SIN-CONFIRMAR -> CONFIRMADA + CAMBIADA), que segmentos acepta el
# conversor real con la clave vieja (A) y con la nueva (B), la continuidad del pipeline y los latidos.
# Requisito: pipeline ARRANCADO (make pipeline-start PROFILE=production) y alias .51 en el client (make lab-e2e-prep).
# Uso (Mac, raiz del repo): DIA=day311 bash scripts/bronze_key/d311_reinicio_etcd.sh NOMBRE [CAIDO_S] [TRAS_S]
#   CAIDO_S: segundos con el etcd-server parado (defecto 150); TRAS_S: segundos tras arrancarlo (defecto 150).
# Trap: pase lo que pase, para el trafico, deja el etcd-server escuchando y borra las claves del defender.
set -u
N=${1:?nombre de la corrida}
CAIDO=${2:-150}
TRAS=${3:-150}
DIA=${DIA:-}
echo "$DIA" | grep -q -E '^day[0-9]{3}$' || { echo "PARADA: DIA debe ser dayNNN (es '$DIA')"; exit 1; }
AY=/vagrant/scripts/bronze_key/d311_etcd_defender.sh
D=/vagrant/logs/lab/$DIA/$N
BASE=/vagrant/datasets/lab/benign_dns_ntp_17k_disjunto_src51.pcap
PID=/tmp/d311_trafico.pid
paso()  { echo; echo "=== [$(date +%T)] $*"; }
falla() { echo; echo "PARADA [$(date +%T)]: $*"; exit 1; }
def()   { vagrant ssh defender -c "$1" 2>/dev/null | tr -d '\r' | grep -v '^\[argus\]'; return "${PIPESTATUS[0]}"; }
cli()   { vagrant ssh client -c "$1" 2>/dev/null | tr -d '\r' | grep -v '^\[argus\]'; return "${PIPESTATUS[0]}"; }
marca() { def "echo \"$1 \$(date +%s.%N)\" >> $D/tiempos.txt"; }
# parada del trafico: por PID y por nombre exacto (pkill -x no se encuentra a si mismo); hasta 5 s de espera
PARAR_TRAFICO="if [ -f $PID ]; then sudo kill \$(cat $PID) 2>/dev/null; rm -f $PID; fi; sudo pkill -x tcpreplay 2>/dev/null; for i in 1 2 3 4 5; do pgrep -x tcpreplay > /dev/null || break; sleep 1; done; pgrep -x tcpreplay > /dev/null && echo 'AVISO: queda tcpreplay vivo' || echo 'trafico parado'"
limpiar() {
  echo; echo "=== [$(date +%T)] trap: trafico, etcd-server y claves"
  cli "$PARAR_TRAFICO"
  if ! def "bash $AY puerto" | grep -q 'escuchando_2379=1'; then
    echo "etcd-server sin escuchar: lo arranco"; make etcd-server-start PROFILE=production > /dev/null 2>&1
    def "bash $AY puerto"
  fi
  def "bash $AY borrar"
}

paso "0 comprobaciones"
def "test -e $D" && falla "ya existe $D (no se reescribe una corrida)"
def "test -f $AY" || falla "falta $AY en el defender"
def "bash $AY puerto" | grep -q 'escuchando_2379=1' || falla "el etcd-server no escucha en 2379: make pipeline-start PROFILE=production"
make pipeline-status > /tmp/${N}_status.txt 2>&1
grep -q 'STOPPED' /tmp/${N}_status.txt && { cat /tmp/${N}_status.txt; falla "algun componente STOPPED"; }
cli "ip -4 addr show dev eth1 | grep -q 192.168.100.51" || falla "falta 192.168.100.51 en el client: make lab-e2e-prep"
def "mkdir -p $D && : > $D/tiempos.txt" || falla "no creo $D"
trap limpiar EXIT

paso "1 marcas de los logs y clave A"
M=$(def "bash $AY marcas")
echo "$M"
echo "$M" > /tmp/${N}_marcas.txt
OFF=$(echo "$M" | awk '{ for (i = 1; i <= NF; i++) { split($i, a, "="); v[a[1]] = a[2] } } END { print v["ml-detector"], v["firewall-agent"], v["sniffer"], v["etcd-server"], v["epoch"] }')
set -- $OFF
OML=$1; OFW=$2; OSN=$3; OET=$4; T0=$5
[ -n "$T0" ] || falla "no leo las marcas"
def "bash $AY clave A" | tee -a /tmp/${N}_huellas.txt | grep -q 'huella_A=' || falla "no leo la clave A"
cat /tmp/${N}_huellas.txt
marca inicio

paso "2 trafico benigno .51 -> .1 a 10 pps en el client"
LIM=$(( (60 + CAIDO + TRAS + 60) * 10 ))
cli "setsid nohup sudo tcpreplay -i eth1 --pps=10 --limit=$LIM $BASE > /tmp/d311_trafico.txt 2>&1 < /dev/null & echo \$! > $PID; sleep 2; pgrep -x tcpreplay > /dev/null" || falla "el trafico no arranca"
marca trafico
sleep 60

paso "3 etcd-server PARADO ($CAIDO s)"
make etcd-server-stop > /tmp/${N}_stop.txt 2>&1 || falla "etcd-server-stop"
sleep 2
def "bash $AY puerto" | tee -a /tmp/${N}_puerto.txt | grep -q 'escuchando_2379=0' || { cat /tmp/${N}_puerto.txt; falla "el puerto 2379 sigue abierto"; }
marca parado
sleep "$CAIDO"

paso "4 etcd-server ARRANCADO ($TRAS s)"
make etcd-server-start PROFILE=production > /tmp/${N}_start.txt 2>&1 || { tail -n 20 /tmp/${N}_start.txt; falla "etcd-server-start"; }
def "bash $AY puerto" | tee -a /tmp/${N}_puerto.txt | grep -q 'escuchando_2379=1' || { cat /tmp/${N}_puerto.txt; falla "el puerto 2379 no escucha"; }
marca arrancado
sleep "$TRAS"
def "bash $AY clave B" | tee -a /tmp/${N}_huellas.txt | grep -q 'huella_B=' || falla "no leo la clave B"
marca clave_B

paso "5 fin del trafico y rotacion del ultimo segmento (40 s)"
cli "$PARAR_TRAFICO"
marca fin_trafico
sleep 40
T1=$(def "date +%s")

paso "6 copia de los logs nuevos y verificacion de segmentos (claves A y B)"
def "bash $AY copiar $D $OML $OFW $OSN $OET" || falla "copiar"
def "bash $AY verificar $D $T0 $T1" | tee /tmp/${N}_verif.txt
grep -q 'segmentos=' /tmp/${N}_verif.txt || falla "verificar"
cp /tmp/${N}_huellas.txt /tmp/${N}_marcas.txt /tmp/${N}_puerto.txt "logs/lab/$DIA/$N/" 2>/dev/null

paso "7 resumen"
L=logs/lab/$DIA/$N
cat /tmp/${N}_huellas.txt
for t in 'BRONCE-CLAVE-SIN-CONFIRMAR' 'BRONCE-CLAVE-CONFIRMADA' 'BRONCE-CLAVE-CAMBIADA' 'BRONCE-SIN-CLAVE' 'BRONCE-CLAVE-RECUPERADA'; do
  echo "ml-detector [$t]=$(grep -c -F "[$t]" "$L/ml-detector.log")"
done
grep -F -e '[BRONCE-CLAVE-CONFIRMADA]' -e '[BRONCE-CLAVE-CAMBIADA]' "$L/ml-detector.log"
grep -F '[BRONCE-CLAVE-SIN-CONFIRMAR]' "$L/ml-detector.log" | head -n 1
for f in ml-detector firewall-agent sniffer; do
  echo "$f: 'Heartbeat failed'=$(grep -c -F 'Heartbeat failed' "$L/$f.log")"
done
echo "etcd-server: lineas con heartbeat=$(grep -c -i 'heartbeat' "$L/etcd-server.log") con register=$(grep -c -i 'register' "$L/etcd-server.log")"
grep -i 'heartbeat' "$L/etcd-server.log" | tail -n 3
LC_ALL=C awk '/\[SOMBRA-DDOS\] resumen:/ { for (i = 1; i <= NF; i++) { split($i, a, "="); if (a[1] == "eventos") { n++; s += a[2]; if (min == "" || a[2] + 0 < min) min = a[2] + 0 } } }
  END { printf "firewall: resumenes=%d eventos=%d eventos_min_por_resumen=%s\n", n, s, min }' "$L/firewall-agent.log"
grep -F '[TIMEBASE] secuencia:' "$L/firewall-agent.log" | tail -n 1
echo; echo "=== [$(date +%T)] HECHO: $L/ (verificacion.txt, tiempos.txt, logs)"
