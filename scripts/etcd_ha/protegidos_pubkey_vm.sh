#!/usr/bin/env bash
# protegidos_pubkey_vm.sh — DAY318, ADR-060 8e.2 [PROTEGIDOS-PUBKEY-D318]. Se ejecuta EN LA VM etcd como root:
#   vagrant ssh etcd -c "sudo bash /vagrant/scripts/etcd_ha/protegidos_pubkey_vm.sh"
# Lee la clave PÚBLICA del manifiesto de protegidos (Vault transit, argus-transit/keys/<clave>) con el certificado de
# argus-infra (rol argus-infra-admin: firmar, verificar y leer esa clave, nada más) y la imprime en hex.
# Salida (stdout), tres líneas que lee protegidos_pubkey.sh en el Mac:
#   PROTEGIDOS_CLAVE=<nombre de la clave transit>
#   PROTEGIDOS_VERSION=<versión más reciente de la clave>
#   PROTEGIDOS_PUBKEY_HEX=<64 caracteres hex: los 32 bytes de la clave pública Ed25519>
# La clave pública no es un secreto. La privada nunca sale de Vault (exportable=false).
set -u
TAG=PROTEGIDOS-PUBKEY
falla() { echo "[$TAG] FALLA: $*" >&2; exit 1; }
CLAVE_F=/etc/vault.d/argus-protegidos.clave
[ -s "$CLAVE_F" ] || falla "falta $CLAVE_F (Vault sin transit de ADR-060: desde el Mac, vagrant destroy -f etcd && vagrant up etcd)"
CLAVE=$(tr -d '\n' < "$CLAVE_F")
[[ "$CLAVE" =~ ^protegidos-[a-z0-9-]{1,64}$ ]] || falla "nombre de clave '$CLAVE' mal formado en $CLAVE_F"
CA=/etc/vault.d/tls/ca.crt
CRT=/etc/argus-pki/argus-infra.crt
KEY=/etc/argus-pki/argus-infra.key
for f in "$CA" "$CRT" "$KEY"; do [ -s "$f" ] || falla "falta $f"; done
U=https://127.0.0.1:8200
TOK=$(curl -s --max-time 10 --cacert "$CA" --cert "$CRT" --key "$KEY" -X POST -d '{"name":"argus-infra"}' \
        "$U/v1/auth/cert/login" | python3 -c 'import sys,json; print(json.load(sys.stdin)["auth"]["client_token"])' 2>/dev/null) \
  || falla "login en Vault con el certificado de argus-infra"
[ -n "$TOK" ] || falla "login en Vault con el certificado de argus-infra: token vacío"
J=$(curl -s --max-time 10 --cacert "$CA" --cert "$CRT" --key "$KEY" -H "X-Vault-Token: $TOK" "$U/v1/argus-transit/keys/$CLAVE") \
  || falla "lectura de argus-transit/keys/$CLAVE"
unset TOK
printf '%s' "$J" | python3 -c '
import base64, json, sys
clave = sys.argv[1]
try:
    d = json.load(sys.stdin)["data"]
except Exception:
    print("[PROTEGIDOS-PUBKEY] FALLA: respuesta de Vault sin data (¿permiso o clave inexistente?)", file=sys.stderr); sys.exit(1)
if d.get("type") != "ed25519":
    print("[PROTEGIDOS-PUBKEY] FALLA: la clave es de tipo %r, se exige ed25519" % d.get("type"), file=sys.stderr); sys.exit(1)
v = d["latest_version"]
pk = base64.b64decode(d["keys"][str(v)]["public_key"])
if len(pk) != 32:
    print("[PROTEGIDOS-PUBKEY] FALLA: clave pública de %d bytes, se esperan 32" % len(pk), file=sys.stderr); sys.exit(1)
print("PROTEGIDOS_CLAVE=%s" % clave)
print("PROTEGIDOS_VERSION=%d" % v)
print("PROTEGIDOS_PUBKEY_HEX=%s" % pk.hex())
' "$CLAVE" || exit 1
