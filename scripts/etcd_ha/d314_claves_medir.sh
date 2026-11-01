#!/bin/bash
# d314_claves_medir.sh — DAY314, paso 4b.4 de DEBT-ETCD-HA-TLS-RAFT-001: las claves HMAC viven en Vault (kv v2 con
# cas_required) con ventana de dos. Mide: creación y misma huella, escritura sin CAS rechazada por Vault, reinicio del
# etcd-server y de Vault (misma huella), Vault parado (copia en memoria, sin copia 503, rotar 503), arranque con Vault
# parado (503) y vuelta, enfriamiento, rotación (ventana de dos en /secrets/valid y en Vault), log sin claves y parada.
#   Mac, raíz del repo:  bash scripts/etcd_ha/d314_claves_medir.sh              (modo lab: defender + VM etcd)
#   banco de pruebas:    MODO=local DIR=/dev/shm/pki bash d314_claves_medir.sh   (todo en la misma máquina)
# El etcd-server de la VM etcd debe estar parado al empezar (lo arranca el propio script con d313_es_vm.sh) y Vault
# desellado. La clave de prueba es la del CN ml-detector en el Vault de la VM: hasta el paso 5 el ml-detector real
# habla con el etcd-server del defender (modo memoria), así que nadie más la usa. Repetible: cada pasada rota con force.
# Predicciones escritas antes de medir: columna "esperado". RESULTADO PASA solo si cuadran todas.
# Nunca imprime una clave: de los cuerpos solo se sacan huella, desde_copia y número de claves.
set -uo pipefail
LC_ALL=C; export LC_ALL
MODO=${MODO:-lab}
ts() { date -u +%FT%TZ; }
falla() { echo "[D314] $(ts) FALLA: $*"; exit 1; }
VENV="VAULT_ADDR=https://127.0.0.1:8200 VAULT_CACERT=/etc/vault.d/tls/ca.crt VAULT_CLIENT_CERT=/etc/argus-pki/etcd-server.crt VAULT_CLIENT_KEY=/etc/argus-pki/etcd-server.key"
case "$MODO" in
  lab)
    [ -f Vagrantfile ] && [ -d .git ] || falla "no estoy en la raíz del repo"
    URL=https://192.168.100.20:2379
    PKI=/dev/shm/d314-pki
    ESVM=/vagrant/scripts/etcd_ha/d313_es_vm.sh
    VAULT_PARAR="sudo systemctl stop vault"
    VAULT_ARRANCAR="sudo systemctl start vault && sudo systemctl restart argus-vault-unseal"
    CFG=$(mktemp -t d314ssh.XXXXXX)
    trap 'ssh -F "$CFG" -T defender "rm -rf $PKI" > /dev/null 2>&1; rm -f "$CFG"' EXIT
    vagrant ssh-config defender > "$CFG" 2>/dev/null && vagrant ssh-config etcd >> "$CFG" 2>/dev/null \
      || falla "vagrant ssh-config (¿defender y etcd levantadas?)"
    D() { ssh -F "$CFG" -T -o LogLevel=ERROR defender "$1"; }
    E() { ssh -F "$CFG" -T -o LogLevel=ERROR etcd "$1"; }
    F="ca.crt admin.crt admin.key ml-detector.crt ml-detector.key firewall-acl-agent.crt firewall-acl-agent.key bronze-to-gold-converter.crt bronze-to-gold-converter.key"
    for f in $F; do [ -f "$HOME/argus-pki/$f" ] || falla "falta ~/argus-pki/$f"; done
    # shellcheck disable=SC2086
    COPYFILE_DISABLE=1 tar --no-xattrs -C "$HOME/argus-pki" -cf - $F \
      | D "umask 077; rm -rf $PKI; mkdir -p $PKI; tar -C $PKI -xf -"
    [ "$(D "ls $PKI | wc -l")" = 9 ] || falla "los certificados no llegaron al defender"
    ;;
  local)
    URL=${URL:-https://127.0.0.1:2379}
    PKI=${DIR:?DIR con ca.crt y los certificados de cliente}
    ESVM=${ESVM:-/tmp/d313_es_vm.sh}
    VAULT_PARAR=${VAULT_PARAR:-"pkill -x vault; sleep 1"}
    VAULT_ARRANCAR=${VAULT_ARRANCAR:-"bash /root/bw_vault.sh > /dev/null"}
    D() { bash -c "$1"; }
    E() { bash -c "$1"; }
    ;;
  *) falla "MODO '$MODO' (lab | local)";;
esac
LOGES=/var/tmp/d313-etcd-server.log
FALLOS=0; N=0
CN=ml-detector   # la clave de prueba es la del ml-detector (su certificado): en la VM etcd aún no la usa nadie (paso 5)

# pedir ROL METODO RUTA -> "código|huella|desde_copia|n_claves|huellas" (nunca la clave)
pedir() {
  D "curl -sS -o /dev/shm/d314.cuerpo -w '%{http_code}' --max-time 20 --cacert $PKI/ca.crt --cert $PKI/$1.crt --key $PKI/$1.key -X $2 '$URL$3' 2>/dev/null; echo -n '|'; python3 -c '
import json,sys
try: d=json.load(open(\"/dev/shm/d314.cuerpo\"))
except Exception: d={}
k=d.get(\"keys\") or []
nk=d.get(\"new_key\") or {}
print(\"%s|%s|%s|%s\" % (d.get(\"huella\") or nk.get(\"huella\",\"\"), str(d.get(\"desde_copia\",\"\")).lower(), d.get(\"valid_keys_count\",\"\"), \",\".join(x.get(\"huella\",\"\") for x in k)))'; rm -f /dev/shm/d314.cuerpo"
}
campo() { echo "$1" | cut -d'|' -f"$2"; }
medir() {  # NOMBRE ESPERADO OBTENIDO DESCRIPCIÓN
  N=$((N+1)); local ok=FALLA
  [ "$2" = "$3" ] && ok=PASA
  [ "$ok" = PASA ] || FALLOS=$((FALLOS+1))
  printf '[D314] %s %-4s %-62s esperado=%-24s obtenido=%-24s %s\n' "$(ts)" "$1" "$4" "$2" "$3" "$ok"
}
cuenta_log() { E "sudo grep -c -- '$1' $LOGES 2>/dev/null || true"; }
# vault_campo RUTA CAMPO: lee un campo (no la clave) con el certificado del etcd-server, en la VM
vault_campo() {
  E "sudo env $VENV bash -c 'T=\$(vault login -method=cert -path=cert -token-only name=etcd-server 2>/dev/null); VAULT_TOKEN=\$T vault kv get -field=$2 argus-hmac/$1 2>/dev/null'"
}
vault_sin_cas() {  # escribir sin CAS: Vault debe rechazarlo (cas_required); devuelve el código HTTP
  E "sudo env $VENV bash -c 'T=\$(vault login -method=cert -path=cert -token-only name=etcd-server 2>/dev/null); curl -s -o /dev/null -w %{http_code} --cacert \$VAULT_CACERT --cert \$VAULT_CLIENT_CERT --key \$VAULT_CLIENT_KEY -H \"X-Vault-Token: \$T\" -X POST -d \"{\\\"data\\\":{\\\"x\\\":1}}\" https://127.0.0.1:8200/v1/argus-hmac/data/d314/sin-cas'"
}
es_arrancar() { E "bash $ESVM arrancar" | grep -E 'D313-VM|ETCD-CLAVES\]|ETCD-VAULT|FALLA'; }
es_parar() { E "bash $ESVM parar" | grep -E 'parado|FALLA'; }

echo "[D314] $(ts) MODO=$MODO URL=$URL CN=$CN"
es_arrancar || falla "no arrancó el etcd-server"
medir C0 1 "$(cuenta_log '\[ETCD-VAULT\] conectado')" "log: [ETCD-VAULT] conectado al arrancar"

# ── creación y misma huella ──────────────────────────────────────────────────
R=$(pedir $CN GET /secrets/$CN); H1=$(campo "$R" 2)
medir C1 "200|false" "$(campo "$R" 1)|$(campo "$R" 3)" "GET /secrets/$CN (ml-detector): 200, no desde la copia"
medir C1b 8 "${#H1}" "huella de 8 hex ($H1)"
R=$(pedir $CN GET /secrets/$CN)
medir C2 "$H1" "$(campo "$R" 2)" "segunda petición: misma huella"
medir C3 "$H1" "$(vault_campo $CN/ventana activa)" "en Vault: $CN/ventana activa = huella"
medir C3b si "$([ -n "$(vault_campo "$CN/$H1" creada)" ] && echo si || echo no)" "en Vault: existe $CN/$H1 con su fecha de creación"
medir C4 400 "$(vault_sin_cas)" "Vault rechaza escribir sin CAS (cas_required=true)"

# ── reinicio del etcd-server y de Vault: misma huella ────────────────────────
es_parar > /dev/null
es_arrancar > /dev/null
medir C5 "$H1" "$(campo "$(pedir $CN GET /secrets/$CN)" 2)" "tras reiniciar el etcd-server: misma huella (DAY311: otra)"
E "$VAULT_PARAR" > /dev/null 2>&1
E "$VAULT_ARRANCAR" > /dev/null 2>&1
sleep 2
medir C6 "$H1" "$(campo "$(pedir $CN GET /secrets/$CN)" 2)" "tras reiniciar y desellar Vault: misma huella"

# ── Vault parado: copia en memoria; sin copia 503; rotar 503 ─────────────────
# lo que hay con Vault arriba (1 clave, o 2 si una pasada anterior rotó hace menos de grace_period_seconds): la copia
# debe dar lo mismo. [D314] la predicción fija "1" solo valía con Vault vacío (1ª pasada en el banco)
VAL_ANTES=$(campo "$(pedir bronze-to-gold-converter GET /secrets/valid/$CN)" 5)
E "$VAULT_PARAR" > /dev/null 2>&1
sleep 1
R=$(pedir $CN GET /secrets/$CN)
medir C7 "200|$H1|true" "$(campo "$R" 1)|$(campo "$R" 2)|$(campo "$R" 3)" "Vault parado: GET 200 desde la copia"
medir C8 1 "$(cuenta_log '\[ETCD-VAULT-NO-DISPONIBLE\] Vault')" "log: primera línea [ETCD-VAULT-NO-DISPONIBLE]"
medir C9 503 "$(campo "$(pedir admin POST "/secrets/rotate/$CN?force=true")" 1)" "Vault parado: rotar (admin, force) 503"
R=$(pedir bronze-to-gold-converter GET /secrets/valid/$CN)
medir C10 "200|true|$VAL_ANTES" "$(campo "$R" 1)|$(campo "$R" 3)|$(campo "$R" 5)" "Vault parado: /secrets/valid (conversor) desde la copia, las mismas"
medir C11 503 "$(campo "$(pedir firewall-acl-agent GET /secrets/firewall-acl-agent)" 1)" "Vault parado: CN sin copia (firewall) 503, no se genera"
T0=$(date +%s.%N)
R=$(pedir $CN GET /secrets/$CN)
DT=$(awk -v a="$T0" -v b="$(date +%s.%N)" 'BEGIN{printf "%.2f", b-a}')
medir C11b si "$(awk -v d="$DT" 'BEGIN{print (d < 1.0) ? "si" : "no"}')" "con Vault parado la copia se sirve sin esperar (< 1 s; fue $DT s)"

# ── arranque con Vault parado y vuelta ───────────────────────────────────────
es_parar > /dev/null
es_arrancar > /dev/null
medir C12 1 "$(cuenta_log '\[ETCD-VAULT-NO-DISPONIBLE\] Vault')" "arranque con Vault parado: [ETCD-VAULT-NO-DISPONIBLE]"
medir C12b 503 "$(campo "$(pedir $CN GET /secrets/$CN)" 1)" "arranque con Vault parado: sin copia, GET 503"
E "$VAULT_ARRANCAR" > /dev/null 2>&1
T1=$(date +%s.%N)
cod=000; for _ in $(seq 1 60); do cod=$(campo "$(pedir $CN GET /secrets/$CN)" 1); [ "$cod" = 200 ] && break; sleep 0.5; done
DT=$(awk -v a="$T1" -v b="$(date +%s.%N)" 'BEGIN{printf "%.1f", b-a}')
medir C13 "200|$H1" "$cod|$(campo "$(pedir $CN GET /secrets/$CN)" 2)" "Vault de vuelta: 200 y misma huella"
medir C13b si "$(awk -v d="$DT" 'BEGIN{print (d <= 12.0) ? "si" : "no"}')" "200 en <= 12 s desde que se manda arrancar Vault (fue $DT s; sondeo 5 s)"
medir C13c 1 "$(cuenta_log 'ETCD-VAULT-RECUPERADO')" "log: [ETCD-VAULT-RECUPERADO]"

# ── rotación: enfriamiento, force, ventana de dos ────────────────────────────
R=$(pedir admin POST "/secrets/rotate/$CN?force=true"); H2=$(campo "$R" 2)
medir C14 "200|2" "$(campo "$R" 1)|$(campo "$R" 4)" "rotar con force (admin): 200 y 2 claves válidas"
medir C14b distinta "$([ -n "$H2" ] && [ "$H2" != "$H1" ] && echo distinta || echo igual)" "huella nueva ($H2) distinta de la anterior"
medir C15 429 "$(campo "$(pedir admin POST "/secrets/rotate/$CN")" 1)" "rotar sin force con la activa recién creada: 429 (enfriamiento)"
medir C15b 1 "$(cuenta_log 'ETCD-CLAVES-ENFRIAMIENTO\] '"$CN")" "log: [ETCD-CLAVES-ENFRIAMIENTO] $CN"
R=$(pedir bronze-to-gold-converter GET /secrets/valid/$CN)
medir C16 "200|2|$H2,$H1" "$(campo "$R" 1)|$(campo "$R" 4)|$(campo "$R" 5)" "/secrets/valid: activa y anterior, en ese orden"
medir C17 "$H2" "$(campo "$(pedir $CN GET /secrets/$CN)" 2)" "el ml-detector recibe la nueva"
medir C18 "$H2 $H1" "$(vault_campo $CN/ventana activa) $(vault_campo $CN/ventana anterior)" "en Vault: ventana activa=nueva anterior=vieja"

# ── log y parada ─────────────────────────────────────────────────────────────
medir C19 0 "$(cuenta_log '[0-9a-f]\{64\}')" "log: 0 cadenas de 64 hex"
P=$(es_parar | grep -oE 'en [0-9.]+ s' | grep -oE '[0-9.]+')
medir C20 si "$(awk -v p="${P:-999}" 'BEGIN{print (p < 1.0) ? "si" : "no"}')" "parada del etcd-server < 1 s (fue ${P:-?} s)"

echo "[D314] $(ts) medidas=$N fallos=$FALLOS"
[ "$FALLOS" = 0 ] && echo "[D314] RESULTADO PASA" || { echo "[D314] RESULTADO FALLA"; exit 1; }
