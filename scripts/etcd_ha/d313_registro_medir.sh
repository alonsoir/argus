#!/bin/bash
# d313_registro_medir.sh — DAY313, paso 4b.3 de DEBT-ETCD-HA-TLS-RAFT-001: el registro de componentes vive en el etcd
# real (gRPC + TLS). Mide registro, nombre != CN, reinicio del etcd-server (registro conservado), etcd caído (lectura de
# copia, escritura 503) y vuelta, muerto que se marca y revive, parada del etcd-server y desregistro.
#   Mac, raíz del repo:  bash scripts/etcd_ha/d313_registro_medir.sh            (modo lab: defender + VM etcd)
#   banco de pruebas:    MODO=local DIR=/dev/shm/pki bash d313_registro_medir.sh (todo en la misma máquina)
# El etcd-server de la VM etcd debe estar parado al empezar (lo arranca el propio script con d313_es_vm.sh).
# Predicciones escritas antes de medir: columna "esperado". RESULTADO PASA solo si cuadran todas.
# Nunca imprime una clave: los cuerpos van a /dev/null salvo /components (solo nombres).
set -uo pipefail
LC_ALL=C; export LC_ALL
MODO=${MODO:-lab}
ts() { date -u +%FT%TZ; }
falla() { echo "[D313B] $(ts) FALLA: $*"; exit 1; }
case "$MODO" in
  lab)
    [ -f Vagrantfile ] && [ -d .git ] || falla "no estoy en la raíz del repo"
    URL=https://192.168.100.20:2379
    PKI=/dev/shm/d313b-pki
    ESVM=/vagrant/scripts/etcd_ha/d313_es_vm.sh
    ETCD_PARAR="sudo systemctl stop etcd"
    ETCD_ARRANCAR="sudo systemctl start etcd"
    ETCDCTL="sudo etcdctl --endpoints=https://127.0.0.1:2381 --cacert=/etc/etcd/tls/ca.crt --cert=/etc/argus-pki/etcd-server.crt --key=/etc/argus-pki/etcd-server.key"
    CFG=$(mktemp -t d313bssh.XXXXXX)
    trap 'ssh -F "$CFG" -T defender "rm -rf $PKI" > /dev/null 2>&1; rm -f "$CFG"' EXIT
    vagrant ssh-config defender > "$CFG" 2>/dev/null && vagrant ssh-config etcd >> "$CFG" 2>/dev/null \
      || falla "vagrant ssh-config (¿defender y etcd levantadas?)"
    D() { ssh -F "$CFG" -T -o LogLevel=ERROR defender "$1"; }
    E() { ssh -F "$CFG" -T -o LogLevel=ERROR etcd "$1"; }
    for f in ca.crt admin.crt admin.key sniffer.crt sniffer.key ml-detector.crt ml-detector.key; do
      [ -f "$HOME/argus-pki/$f" ] || falla "falta ~/argus-pki/$f"
    done
    COPYFILE_DISABLE=1 tar --no-xattrs -C "$HOME/argus-pki" -cf - ca.crt admin.crt admin.key sniffer.crt sniffer.key \
      ml-detector.crt ml-detector.key | D "umask 077; rm -rf $PKI; mkdir -p $PKI; tar -C $PKI -xf -"
    [ "$(D "ls $PKI | wc -l")" = 7 ] || falla "los certificados no llegaron al defender"
    ;;
  local)
    URL=${URL:-https://127.0.0.1:2379}
    PKI=${DIR:?DIR con ca.crt y los certificados de cliente}
    ESVM=${ESVM:-/tmp/d313_es_vm.sh}
    ETCD_PARAR=${ETCD_PARAR:-"bash /tmp/etcd_bench.sh parar"}
    ETCD_ARRANCAR=${ETCD_ARRANCAR:-"bash /tmp/etcd_bench.sh arrancar"}
    ETCDCTL="etcdctl --endpoints=https://127.0.0.1:2381 --cacert=/etc/etcd/tls/ca.crt --cert=/etc/argus-pki/etcd-server.crt --key=/etc/argus-pki/etcd-server.key"
    D() { bash -c "$1"; }
    E() { bash -c "$1"; }
    ;;
  *) falla "MODO '$MODO' (lab | local)";;
esac
LOGES=/var/tmp/d313-etcd-server.log
FALLOS=0; N=0

# c ROL METODO RUTA [CUERPO] -> código HTTP (el cuerpo va en base64 para no pelear con las comillas por ssh)
c() {
  local rol=$1 met=$2 ruta=$3 cuerpo=${4:-} b64=""
  [ -n "$cuerpo" ] && b64=$(printf '%s' "$cuerpo" | base64 | tr -d '\n')
  D "printf '%s' '$b64' | base64 -d | curl -sS -o /dev/null -w '%{http_code}' --max-time 15 --cacert $PKI/ca.crt --cert $PKI/$rol.crt --key $PKI/$rol.key -X $met -H 'Content-Type: application/json' $( [ -n "$cuerpo" ] && echo '--data-binary @-' ) '$URL$ruta' 2>/dev/null"
}
componentes() {  # nombres registrados y desde_copia, vistos por admin
  D "curl -sS --max-time 15 --cacert $PKI/ca.crt --cert $PKI/admin.crt --key $PKI/admin.key '$URL/components' 2>/dev/null" \
    | python3 -c 'import sys,json; d=json.load(sys.stdin); print(",".join(sorted(d["components"])), "desde_copia=%s" % str(d.get("desde_copia")).lower())' 2>/dev/null
}
medir() {  # NOMBRE ESPERADO OBTENIDO DESCRIPCIÓN
  N=$((N+1)); local ok=FALLA
  [ "$2" = "$3" ] && ok=PASA
  [ "$ok" = PASA ] || FALLOS=$((FALLOS+1))
  printf '[D313B] %s %-4s %-60s esperado=%-32s obtenido=%-32s %s\n' "$(ts)" "$1" "$4" "$2" "$3" "$ok"
}
cuenta_log() { E "sudo grep -c -- '$1' $LOGES 2>/dev/null || true"; }
latir() { c "$1" POST "/v1/heartbeat/$1" '{"timestamp": 1}'; }
registrar() { c "$1" POST /register "{\"component\": \"$2\"}"; }

echo "[D313B] $(ts) MODO=$MODO URL=$URL"
E "bash $ESVM arrancar" | grep -E 'D313-VM|ETCD-ALMACEN\]|REGISTRO-CARGADO|FALLA' || falla "no arrancó el etcd-server"

# ── registro y nombre != CN ──────────────────────────────────────────────────
medir R1 200 "$(registrar sniffer sniffer)" "sniffer se registra como sniffer"
medir R2 403 "$(registrar sniffer ml-detector)" "sniffer intenta registrarse como ml-detector"
medir R2b 1 "$(cuenta_log 'no es el CN')" "log: [ETCD-AUTHZ-DENEGADO] ... no es el CN"
medir R3 200 "$(latir sniffer)" "latido de sniffer"
medir R4 "etcd-server,sniffer desde_copia=false" "$(componentes)" "/components (admin)"
medir R5 "/argus/registro/sniffer" "$(E "$ETCDCTL get /argus/registro/sniffer --keys-only 2>/dev/null" | head -n 1)" "la clave está en el etcd real"

# ── reinicio del etcd-server: el registro se conserva (DAY311: volvía vacío) ──
E "bash $ESVM parar" | grep -E 'parado|FALLA'
E "bash $ESVM arrancar" > /dev/null
medir R6 1 "$(E "sudo grep -c 'REGISTRO-CARGADO\] 2 componentes del almacén: etcd-server,sniffer' $LOGES")" "log tras reinicio: cargados etcd-server y sniffer"
medir R7 200 "$(latir sniffer)" "latido de sniffer tras reiniciar (antes 404)"
medir R8 "etcd-server,sniffer desde_copia=false" "$(componentes)" "/components tras reiniciar"

# ── etcd caído: lecturas de la copia, escrituras 503 ─────────────────────────
E "$ETCD_PARAR" > /dev/null 2>&1
sleep 2
medir R9 503 "$(latir sniffer)" "latido con etcd caído"
medir R10 503 "$(registrar ml-detector ml-detector)" "registro con etcd caído"
medir R11 200 "$(c sniffer GET /config/sniffer)" "GET /config/sniffer con etcd caído (copia)"
medir R12 "etcd-server,sniffer desde_copia=true" "$(componentes)" "/components con etcd caído (copia)"
medir R13 1 "$(cuenta_log '\[ETCD-ALMACEN-NO-DISPONIBLE\] etcd')" "log: primera línea [ETCD-ALMACEN-NO-DISPONIBLE]"
E "$ETCD_ARRANCAR" > /dev/null 2>&1
# el reloj empieza cuando etcd escucha (no cuando se manda arrancar: eso mide el arranque de etcd, no el etcd-server)
for _ in $(seq 1 60); do E "ss -ltnH 'sport = :2381'" | grep -q . && break; sleep 0.5; done
T1=$(date +%s.%N)
cod=000; for _ in $(seq 1 60); do cod=$(latir sniffer); [ "$cod" = 200 ] && break; sleep 0.25; done
DT=$(awk -v a="$T1" -v b="$(date +%s.%N)" 'BEGIN{printf "%.1f", b-a}')
medir R14 200 "$cod" "latido con etcd de vuelta"
medir R14b si "$(awk -v d="$DT" 'BEGIN{print (d <= 3.0) ? "si" : "no"}')" "200 en <= 3 s desde que etcd escucha (fue $DT s)"
medir R15 1 "$(cuenta_log 'ETCD-ALMACEN-RECUPERADO')" "log: [ETCD-ALMACEN-RECUPERADO]"

# ── muerto se marca (no se borra) y revive ───────────────────────────────────
medir R16 200 "$(registrar ml-detector ml-detector)" "ml-detector se registra"
T0=$(date +%s)
echo "[D313B] $(ts) espera de 105 s sin latidos de ml-detector ni sniffer (límite 30 s x 3 = 90 s, revisión cada 10 s)"
sleep 105
medir R17 1 "$(cuenta_log 'COMPONENTE-MUERTO\] ml-detector')" "log: [ETCD-COMPONENTE-MUERTO] ml-detector"
medir R18 "etcd-server,ml-detector,sniffer desde_copia=false" "$(componentes)" "el muerto sigue registrado"
medir R19 200 "$(latir ml-detector)" "latido del muerto (antes 404 para siempre)"
medir R20 1 "$(cuenta_log 'COMPONENTE-REVIVIDO\] ml-detector')" "log: [ETCD-COMPONENTE-REVIVIDO] ml-detector"
echo "[D313B] $(ts) ($(( $(date +%s) - T0 )) s desde el registro de ml-detector)"

# ── desregistro y parada ─────────────────────────────────────────────────────
medir R21 200 "$(c ml-detector POST /unregister '{"component": "ml-detector"}')" "ml-detector se desregistra"
medir R22 404 "$(c ml-detector POST /unregister '{"component": "ml-detector"}')" "segundo desregistro"
medir R23 403 "$(c sniffer POST /unregister '{"component": "ml-detector"}')" "sniffer desregistra a otro"
medir R24 200 "$(c sniffer POST /unregister '{"component": "sniffer"}')" "sniffer se desregistra"
medir R25 0 "$(cuenta_log '[0-9a-f]\{64\}')" "log: 0 cadenas de 64 hex"
P=$(E "bash $ESVM parar" | grep -oE 'en [0-9.]+ s' | grep -oE '[0-9.]+')
medir R26 si "$(awk -v p="${P:-999}" 'BEGIN{print (p < 1.0) ? "si" : "no"}')" "parada del etcd-server < 1 s (fue ${P:-?} s)"

echo "[D313B] $(ts) medidas=$N fallos=$FALLOS"
[ "$FALLOS" = 0 ] && echo "[D313B] RESULTADO PASA" || { echo "[D313B] RESULTADO FALLA"; exit 1; }
