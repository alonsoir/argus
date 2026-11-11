#!/bin/bash
# d315_b4_medir.sh — [ETCD-B4-D315] medida de 4b.6/B4 en el laboratorio, con mTLS y los certificados reales.
# Se lanza desde el Mac, en la raíz del repo (MODO=lab, defecto; MODO=local es el banco); arranca y para el etcd-server de la VM etcd con d313_es_vm.sh (debe
# estar parado al empezar). Los certificados viajan del Mac (~/argus-pki) a /dev/shm del defender y se borran al salir.
#   B1  firewall-acl-agent se registra: 200
#   B1b paths.hmac_key = /secrets/firewall-acl-agent        (antes /secrets/firewall)
#   B1c paths.config   = /config/firewall-acl-agent         (antes /config/firewall)
#   B1d sin paths.crypto_token, en una respuesta 200         (ruta que el servidor no tiene)
#   B2  GET paths.hmac_key con el certificado del firewall: 200 y huella de 8 hex
#   B3  GET /secrets/firewall (la ruta vieja): 403
#   B4  GET paths.config con el certificado del firewall: 200
#   B5  ml-detector se registra: paths.hmac_key = /secrets/ml-detector (sin guion cortado: antes /secrets/ml)
#   B6  log: 0 cadenas de 64 hex (ninguna clave)
# Efecto permanente: crea en Vault la clave HMAC de firewall-acl-agent (inmutable, nunca se borra; es la que usará).
set -uo pipefail
LC_ALL=C; export LC_ALL
ts() { date -u +%FT%TZ; }
falla() { echo "[D315-B4] $(ts) FALLA: $*"; exit 1; }
MODO=${MODO:-lab}
LOGES=/var/tmp/d313-etcd-server.log
case "$MODO" in
  lab)
    [ -f Vagrantfile ] && [ -d .git ] || falla "no estoy en la raíz del repo"
    URL=https://192.168.100.20:2379
    PKI=/dev/shm/d315b4-pki
    ESVM=/vagrant/scripts/etcd_ha/d313_es_vm.sh
    CFG=$(mktemp -t d315b4ssh.XXXXXX)
    trap 'ssh -F "$CFG" -T defender "rm -rf $PKI /dev/shm/d315b4.cuerpo" > /dev/null 2>&1; rm -f "$CFG"' EXIT
    vagrant ssh-config defender > "$CFG" 2>/dev/null && vagrant ssh-config etcd >> "$CFG" 2>/dev/null \
      || falla "vagrant ssh-config (¿defender y etcd levantadas?)"
    D() { ssh -F "$CFG" -T -o LogLevel=ERROR defender "$1"; }
    E() { ssh -F "$CFG" -T -o LogLevel=ERROR etcd "$1"; }
    F="ca.crt firewall-acl-agent.crt firewall-acl-agent.key ml-detector.crt ml-detector.key"
    for f in $F; do [ -f "$HOME/argus-pki/$f" ] || falla "falta ~/argus-pki/$f"; done
    # shellcheck disable=SC2086
    COPYFILE_DISABLE=1 tar --no-xattrs -C "$HOME/argus-pki" -cf - $F | D "umask 077; rm -rf $PKI; mkdir -p $PKI; tar -C $PKI -xf -"
    [ "$(D "ls $PKI | wc -l")" = 5 ] || falla "los certificados no llegaron al defender"
    ;;
  local)  # banco: servidor en esta máquina; ESVM arranca/para; DIR con ca.crt y los certificados de cliente
    URL=${URL:-https://127.0.0.1:2379}
    PKI=${DIR:?DIR con ca.crt y los certificados de cliente}
    ESVM=${ESVM:?ESVM con arrancar/parar}
    D() { bash -c "$1"; }
    E() { bash -c "$1"; }
    ;;
  *) falla "MODO '$MODO' (lab | local)";;
esac

N=0; FALLOS=0
medir() {  # NOMBRE ESPERADO OBTENIDO DESCRIPCIÓN
  N=$((N+1)); local ok=FALLA
  [ "$2" = "$3" ] && ok=PASA
  [ "$ok" = PASA ] || FALLOS=$((FALLOS+1))
  printf '[D315-B4] %s %-4s %-58s esperado=%-30s obtenido=%-30s %s\n' "$(ts)" "$1" "$4" "$2" "$3" "$ok"
}
# pedir CN METODO RUTA [CUERPO] -> "código|hmac_key|config|crypto_token|huella" (nunca la clave)
pedir() {
  local cuerpo=${4:-}
  D "curl -sS -o /dev/shm/d315b4.cuerpo -w '%{http_code}' --max-time 20 --cacert $PKI/ca.crt --cert $PKI/$1.crt --key $PKI/$1.key \
       -X $2 -H 'Content-Type: application/json' ${cuerpo:+-d '$cuerpo'} '$URL$3' 2>/dev/null; echo -n '|'; python3 -c '
import json
try: d=json.load(open(\"/dev/shm/d315b4.cuerpo\"))
except Exception: d={}
p=d.get(\"paths\") or {}
print(\"%s|%s|%s|%s\" % (p.get(\"hmac_key\",\"\"), p.get(\"config\",\"\"), \"crypto_token\" in p, d.get(\"huella\",\"\")))'; rm -f /dev/shm/d315b4.cuerpo"
}
campo() { echo "$1" | cut -d'|' -f"$2"; }

echo "[D315-B4] $(ts) URL=$URL"
E "bash $ESVM arrancar" | grep -E 'D313-VM|FALLA' || falla "no arrancó el etcd-server"

R=$(pedir firewall-acl-agent POST /register '{"component":"firewall-acl-agent"}')
medir B1  200 "$(campo "$R" 1)" "firewall-acl-agent se registra"
medir B1b /secrets/firewall-acl-agent "$(campo "$R" 2)" "paths.hmac_key con el nombre completo (= CN)"
medir B1c /config/firewall-acl-agent "$(campo "$R" 3)" "paths.config con el nombre completo (= CN)"
medir B1d "200|False" "$(campo "$R" 1)|$(campo "$R" 4)" "sin paths.crypto_token (en una respuesta 200)"
RUTA=$(campo "$R" 2); RUTA_CFG=$(campo "$R" 3)
R=$(pedir firewall-acl-agent GET "${RUTA:-/secrets/firewall-acl-agent}")
H=$(campo "$R" 5)
medir B2  200 "$(campo "$R" 1)" "GET paths.hmac_key (firewall): la clave de su CSV"
medir B2b 8 "${#H}" "huella de 8 hex ($H)"
medir B3  403 "$(campo "$(pedir firewall-acl-agent GET /secrets/firewall)" 1)" "GET /secrets/firewall (ruta vieja): denegado"
medir B4  200 "$(campo "$(pedir firewall-acl-agent GET "${RUTA_CFG:-/config/firewall-acl-agent}")" 1)" "GET paths.config (firewall)"
R=$(pedir ml-detector POST /register '{"component":"ml-detector"}')
medir B5  /secrets/ml-detector "$(campo "$R" 2)" "ml-detector: paths.hmac_key (antes /secrets/ml)"
pedir firewall-acl-agent POST /unregister '{"component":"firewall-acl-agent"}' > /dev/null
pedir ml-detector POST /unregister '{"component":"ml-detector"}' > /dev/null
medir B6  0 "$(E "sudo grep -cE '[0-9a-f]{64}' $LOGES 2>/dev/null || true")" "log: 0 cadenas de 64 hex"
E "bash $ESVM parar" | grep -E 'parado|FALLA'

echo "[D315-B4] $(ts) medidas=$N fallos=$FALLOS"
[ "$FALLOS" = 0 ] && echo "[D315-B4] RESULTADO PASA" || { echo "[D315-B4] RESULTADO FALLA"; exit 1; }
