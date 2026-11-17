#!/usr/bin/env bash
# d317_reinicio_vm.sh — DAY317, paso 7 de DEBT-ETCD-HA-TLS-RAFT-001 [REINICIO-VM-D317] (instrumento de medida; sustituye a
# d311_reinicio_etcd.sh). Reinicia el etcd-server de la VM etcd con el pipeline vivo y tráfico benigno, y da un veredicto
# PASA/FALLA: misma huella de clave (bronce y CSV), ningún registro nuevo (REANUDADO), latidos 200 tras arrancar, y todo el
# bronce del intervalo (también el firmado con el servidor caído) verificable con la clave de antes y con la de después.
# Requisitos: pipeline arrancado (make pipeline-start PROFILE=production) y alias .51 en el client (make lab-e2e-prep).
# Uso (Mac, raíz del repo):
#   DIA=day317 bash scripts/etcd_ha/d317_reinicio_vm.sh NOMBRE [CAIDO_S] [TRAS_S]
#     CAIDO_S: segundos con el etcd-server parado, entero [60, 1800], defecto 150
#     TRAS_S:  segundos tras arrancarlo, entero [60, 1800], defecto 150
#   bash scripts/etcd_ha/d317_reinicio_vm.sh --veredicto logs/lab/dayNNN/NOMBRE   (reevalúa una corrida ya hecha)
# Trap: pase lo que pase, para el tráfico, deja el etcd-server de la VM activo y borra las claves del defender.
set -u
export LC_ALL=C
TAG=REINICIO-VM

veredicto() {  # DIR -> imprime cada condición y VEREDICTO; rc 0 si PASA
  local L=$1 f c n ok=1 tras
  [ -f "$L/parametros.txt" ] || { echo "[$TAG] FALLA: falta $L/parametros.txt"; return 1; }
  # shellcheck disable=SC1091
  . "$L/parametros.txt"   # TRAS, INTERVALOS (cn=s ...), HUELLAS (X_C=hhhhhhhh ...)
  cond() { if [ "$2" = 1 ]; then echo "  OK     $1"; else echo "  FALLA  $1"; ok=0; fi; }
  hu() { echo "$HUELLAS" | tr ' ' '\n' | sed -n "s/^$1=//p"; }
  cuenta() { local x; x=$(grep -c -F -- "$1" "$2" 2>/dev/null); echo "${x:-0}"; }
  echo "[$TAG] veredicto de $L (TRAS=$TRAS s; intervalos: $INTERVALOS)"
  for f in ml-detector.log firewall-agent.log sniffer.log etcd-server-tras.log verificacion.txt; do
    cond "existe $f" "$([ -f "$L/$f" ] && echo 1 || echo 0)"
  done
  for C in ml-detector firewall-acl-agent; do
    a=$(hu "A_$C"); b=$(hu "B_$C")
    cond "huella de $C igual antes y después ($a -> $b)" "$([ -n "$a" ] && [ "$a" = "$b" ] && echo 1 || echo 0)"
  done
  f=$L/ml-detector.log
  cond "ml-detector: [BRONCE-CLAVE-SIN-CONFIRMAR] >= 1 ($(cuenta '[BRONCE-CLAVE-SIN-CONFIRMAR]' "$f"))" "$([ "$(cuenta '[BRONCE-CLAVE-SIN-CONFIRMAR]' "$f")" -ge 1 ] && echo 1 || echo 0)"
  cond "ml-detector: [BRONCE-CLAVE-CONFIRMADA] >= 1 ($(cuenta '[BRONCE-CLAVE-CONFIRMADA]' "$f"))" "$([ "$(cuenta '[BRONCE-CLAVE-CONFIRMADA]' "$f")" -ge 1 ] && echo 1 || echo 0)"
  for t in '[BRONCE-CLAVE-CAMBIADA]' '[BRONCE-SIN-CLAVE]'; do
    cond "ml-detector: $t = 0 ($(cuenta "$t" "$f"))" "$([ "$(cuenta "$t" "$f")" -eq 0 ] && echo 1 || echo 0)"
  done
  f=$L/firewall-agent.log
  cond "firewall: [FW-CSV-CLAVE-SIN-CONFIRMAR] >= 1 ($(cuenta '[FW-CSV-CLAVE-SIN-CONFIRMAR]' "$f"))" "$([ "$(cuenta '[FW-CSV-CLAVE-SIN-CONFIRMAR]' "$f")" -ge 1 ] && echo 1 || echo 0)"
  cond "firewall: [FW-CSV-CLAVE-CONFIRMADA] >= 1 ($(cuenta '[FW-CSV-CLAVE-CONFIRMADA]' "$f"))" "$([ "$(cuenta '[FW-CSV-CLAVE-CONFIRMADA]' "$f")" -ge 1 ] && echo 1 || echo 0)"
  for t in '[FW-CSV-CLAVE-CAMBIADA]' '[FW-CSV-SIN-CLAVE]'; do
    cond "firewall: $t = 0 ($(cuenta "$t" "$f"))" "$([ "$(cuenta "$t" "$f")" -eq 0 ] && echo 1 || echo 0)"
  done
  for p in ml-detector:ml-detector firewall-agent:firewall-acl-agent sniffer:sniffer; do
    f=$L/${p%%:*}.log; c=${p#*:}
    cond "$c: [ETCD-CLIENTE-SIN-SERVICIO] >= 1 ($(cuenta '[ETCD-CLIENTE-SIN-SERVICIO]' "$f"))" "$([ "$(cuenta '[ETCD-CLIENTE-SIN-SERVICIO]' "$f")" -ge 1 ] && echo 1 || echo 0)"
    cond "$c: [ETCD-CLIENTE-REANUDADO] = 1 ($(cuenta '[ETCD-CLIENTE-REANUDADO]' "$f"))" "$([ "$(cuenta '[ETCD-CLIENTE-REANUDADO]' "$f")" -eq 1 ] && echo 1 || echo 0)"
    for t in '[ETCD-CLIENTE-REGISTRADO]' '[ETCD-CLIENTE-REGISTRO-PERDIDO]'; do
      cond "$c: $t = 0 ($(cuenta "$t" "$f"))" "$([ "$(cuenta "$t" "$f")" -eq 0 ] && echo 1 || echo 0)"
    done
  done
  f=$L/etcd-server-tras.log
  n=$(grep -E '\[ETCD-REGISTRO\] registrado ' "$f" 2>/dev/null | grep -v -c -E 'registrado etcd-server *$'); n=${n:-0}
  cond "etcd-server tras arrancar: componentes registrados de nuevo = 0 ($n)" "$([ "$n" -eq 0 ] && echo 1 || echo 0)"
  n=$(grep -c -E '\[ETCD←\] POST +/register ' "$f" 2>/dev/null); n=${n:-0}
  cond "etcd-server tras arrancar: POST /register = 0 ($n)" "$([ "$n" -eq 0 ] && echo 1 || echo 0)"
  n=$(grep -E '\[ETCD←\] POST +/v1/heartbeat/' "$f" 2>/dev/null | grep -v -c 'status=200 '); n=${n:-0}
  cond "etcd-server tras arrancar: latidos con status distinto de 200 = 0 ($n)" "$([ "$n" -eq 0 ] && echo 1 || echo 0)"
  for c in sniffer ml-detector firewall-acl-agent; do
    s=$(echo "$INTERVALOS" | tr ' ' '\n' | sed -n "s/^$c=//p"); s=${s:-30}
    min=$(( TRAS / s - 1 )); [ "$min" -lt 1 ] && min=1
    n=$(grep -c -E "\[ETCD←\] POST +/v1/heartbeat/$c +\| status=200 " "$f" 2>/dev/null); n=${n:-0}
    cond "etcd-server tras arrancar: latidos 200 de $c >= $min ($n; intervalo $s s)" "$([ "$n" -ge "$min" ] && echo 1 || echo 0)"
  done
  f=$L/verificacion.txt
  n=$(grep -v -c '^#' "$f" 2>/dev/null); n=${n:-0}
  m=$(awk '!/^#/ && $6 != "AB" && $6 != "VACIO"' "$f" 2>/dev/null | wc -l | tr -d ' ')
  cond "bronce: segmentos del intervalo >= 1 ($n)" "$([ "$n" -ge 1 ] && echo 1 || echo 0)"
  cond "bronce: todos verifican con la clave de antes y con la de después (fuera de AB/VACIO: $m)" "$([ "$n" -ge 1 ] && [ "$m" -eq 0 ] && echo 1 || echo 0)"
  n=$(awk '/\[SOMBRA-DDOS\] resumen:/ { for (i = 1; i <= NF; i++) { split($i, a, "="); if (a[1] == "eventos") s += a[2] } } END { print s + 0 }' "$L/firewall-agent.log" 2>/dev/null)
  cond "continuidad: el firewall resume eventos (eventos=$n)" "$([ "${n:-0}" -gt 0 ] && echo 1 || echo 0)"
  if [ "$ok" = 1 ]; then echo "[$TAG] VEREDICTO PASA"; return 0; else echo "[$TAG] VEREDICTO FALLA"; return 1; fi
}

if [ "${1:-}" = "--veredicto" ]; then veredicto "${2:?directorio de la corrida}"; exit $?; fi

N=${1:?nombre de la corrida}
entero() {  # nombre valor defecto min max -> VAL, ORIGEN
  local n=$1 v=$2 d=$3 lo=$4 hi=$5
  if [ -z "$v" ]; then VAL=$d; ORIGEN="defecto: ausente"; return; fi
  if ! [[ "$v" =~ ^[0-9]+$ ]] || [ "$v" -lt "$lo" ] || [ "$v" -gt "$hi" ]; then VAL=$d; ORIGEN="defecto: '$v' mal formado, entero en [$lo, $hi]"; return; fi
  VAL=$v; ORIGEN="argumento"
}
entero CAIDO_S "${2:-}" 150 60 1800; CAIDO=$VAL; O_CAIDO=$ORIGEN
entero TRAS_S  "${3:-}" 150 60 1800; TRAS=$VAL;  O_TRAS=$ORIGEN
DIA=${DIA:-}
echo "$DIA" | grep -q -E '^day[0-9]{3}$' || { echo "PARADA: DIA debe ser dayNNN (es '$DIA')"; exit 1; }
echo "[$TAG] $N: CAIDO_S=$CAIDO ($O_CAIDO) TRAS_S=$TRAS ($O_TRAS) DIA=$DIA"
AY=/vagrant/scripts/etcd_ha/d317_reinicio_defender.sh
D=/vagrant/logs/lab/$DIA/$N; L=logs/lab/$DIA/$N
BASE=/vagrant/datasets/lab/benign_dns_ntp_17k_disjunto_src51.pcap
PID=/tmp/d317_trafico.pid
paso()  { echo; echo "=== [$(date +%T)] $*"; }
falla() { echo; echo "PARADA [$(date +%T)]: $*"; exit 1; }
def()   { vagrant ssh defender -c "$1" 2>/dev/null | tr -d '\r' | grep -v '^\[argus\]'; return "${PIPESTATUS[0]}"; }
cli()   { vagrant ssh client -c "$1" 2>/dev/null | tr -d '\r' | grep -v '^\[argus\]'; return "${PIPESTATUS[0]}"; }
vme()   { vagrant ssh control-1 -c "$1" 2>/dev/null | tr -d '\r' | grep -v '^\[argus\]'; return "${PIPESTATUS[0]}"; }
marca() { def "echo \"$1 \$(date +%s.%N)\" >> $D/tiempos.txt"; }
PARAR_TRAFICO="if [ -f $PID ]; then sudo kill \$(cat $PID) 2>/dev/null; rm -f $PID; fi; sudo pkill -x tcpreplay 2>/dev/null; for i in 1 2 3 4 5; do pgrep -x tcpreplay > /dev/null || break; sleep 1; done; pgrep -x tcpreplay > /dev/null && echo 'AVISO: queda tcpreplay vivo' || echo 'tráfico parado'"
limpiar() {
  echo; echo "=== [$(date +%T)] trap: tráfico, etcd-server de la VM y claves"
  cli "$PARAR_TRAFICO"
  if ! vme "systemctl is-active --quiet ml-defender-etcd-server.service"; then
    echo "etcd-server de la VM parado: lo arranco"; make etcd-server-start > /tmp/${N}_trap_start.txt 2>&1; tail -n 2 /tmp/${N}_trap_start.txt
  fi
  def "bash $AY borrar"
}
huella() { def "bash $AY clave $1 $2" | tee -a "/tmp/${N}_huellas.txt" | sed -n "s/.*huella_$1_$2=\([0-9a-f]\{8\}\).*/$1_$2=\1/p"; }

paso "0 comprobaciones"
[ -f Vagrantfile ] && [ -d .git ] || falla "no estoy en la raíz del repo"
def "test -e $D" && falla "ya existe $D (no se reescribe una corrida)"
def "test -f $AY" || falla "falta $AY en el defender"
make etcd-vm-check > /tmp/${N}_check.txt 2>&1 || { cat /tmp/${N}_check.txt; falla "la VM etcd no está sana"; }
make pipeline-status > /tmp/${N}_status.txt 2>&1
grep -q 'STOPPED' /tmp/${N}_status.txt && { cat /tmp/${N}_status.txt; falla "algún componente STOPPED"; }
cli "ip -4 addr show dev eth1 | grep -q 192.168.100.51" || falla "falta 192.168.100.51 en el client: make lab-e2e-prep"
def "mkdir -p $D && : > $D/tiempos.txt" || falla "no creo $D"
: > "/tmp/${N}_huellas.txt"
trap limpiar EXIT

paso "1 marcas de los logs, intervalos de latido y claves A"
M=$(def "bash $AY marcas"); echo "$M"
set -- $(echo "$M" | awk '{ for (i = 1; i <= NF; i++) { split($i, a, "="); v[a[1]] = a[2] } } END { print v["ml-detector"], v["firewall-agent"], v["sniffer"], v["epoch"] }')
OML=${1:-}; OFW=${2:-}; OSN=${3:-}; T0=${4:-}
[ -n "$T0" ] || falla "no leo las marcas"
INTERVALOS=$(def "bash $AY intervalos" | tr -s ' ' | sed 's/ $//'); echo "intervalos: $INTERVALOS"
# [REINICIO-VM-D317b] vagrant ssh antepone una línea vacía: cada valor capturado se sanea (reinicio_vm_1 paró por eso)
TV0=$(vme "date -u '+%Y-%m-%d %H:%M:%S UTC'" | grep -E '^[0-9]{4}-' | tail -n 1); [ -n "$TV0" ] || falla "no leo la hora de la VM etcd"
HA=$(huella A ml-detector); HAF=$(huella A firewall-acl-agent)
[ -n "$HA" ] && [ -n "$HAF" ] || { cat "/tmp/${N}_huellas.txt"; falla "no leo las claves A"; }
echo "$HA $HAF"
marca inicio

paso "2 tráfico benigno .51 -> .1 a 10 pps en el client"
LIM=$(( (60 + CAIDO + TRAS + 60) * 10 ))
cli "setsid nohup sudo tcpreplay -i eth1 --pps=10 --limit=$LIM $BASE > /tmp/d317_trafico.txt 2>&1 < /dev/null & echo \$! > $PID; sleep 2; pgrep -x tcpreplay > /dev/null" || falla "el tráfico no arranca"
marca trafico
sleep 60

paso "3 etcd-server de la VM PARADO ($CAIDO s)"
make etcd-server-stop > /tmp/${N}_stop.txt 2>&1 || falla "etcd-server-stop"
vme "systemctl is-active ml-defender-etcd-server.service" | grep -qx inactive || falla "el etcd-server de la VM sigue activo"
marca parado
sleep "$CAIDO"

paso "4 etcd-server de la VM ARRANCADO ($TRAS s)"
TV1=$(vme "date -u '+%Y-%m-%d %H:%M:%S UTC'" | grep -E '^[0-9]{4}-' | tail -n 1); [ -n "$TV1" ] || falla "no leo la hora de la VM etcd (arranque)"
make etcd-server-start > /tmp/${N}_start.txt 2>&1 || { tail -n 12 /tmp/${N}_start.txt; falla "etcd-server-start (no quedó sano)"; }
marca arrancado
sleep "$TRAS"
HB=$(huella B ml-detector); HBF=$(huella B firewall-acl-agent)
[ -n "$HB" ] && [ -n "$HBF" ] || { cat "/tmp/${N}_huellas.txt"; falla "no leo las claves B"; }
echo "$HB $HBF"
marca claves_B

paso "5 fin del tráfico y rotación del último segmento (40 s)"
cli "$PARAR_TRAFICO"
marca fin_trafico
sleep 40
T1=$(def "date +%s" | tr -dc '0-9'); [ -n "$T1" ] || falla "no leo la hora del defender"

paso "6 copia de los logs y verificación de segmentos (claves A y B)"
def "bash $AY copiar $D $OML $OFW $OSN" || falla "copiar"
vme "sudo journalctl -u ml-defender-etcd-server --since '$TV0' --no-pager -o short-iso" > "$L/etcd-server.log" || falla "journal de la VM"
vme "sudo journalctl -u ml-defender-etcd-server --since '$TV1' --no-pager -o short-iso" > "$L/etcd-server-tras.log" || falla "journal de la VM (tras arrancar)"
echo "[$TAG] etcd-server.log: $(wc -l < "$L/etcd-server.log" | tr -d ' ') líneas; etcd-server-tras.log: $(wc -l < "$L/etcd-server-tras.log" | tr -d ' ')"
def "bash $AY verificar $D $T0 $T1" | tee "/tmp/${N}_verif.txt"
grep -q 'segmentos=' "/tmp/${N}_verif.txt" || falla "verificar"
cp "/tmp/${N}_huellas.txt" "$L/huellas.txt"
cat > "$L/parametros.txt" <<PAR
TRAS=$TRAS
CAIDO=$CAIDO
INTERVALOS="$INTERVALOS"
HUELLAS="$HA $HAF $HB $HBF"
PAR

paso "7 veredicto"
veredicto "$L" | tee "$L/veredicto.txt"
rc=${PIPESTATUS[0]}
echo; echo "=== [$(date +%T)] HECHO: $L/ (veredicto.txt, verificacion.txt, tiempos.txt, logs)"
exit "$rc"
