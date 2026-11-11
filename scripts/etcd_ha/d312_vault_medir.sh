#!/bin/bash
# d312_vault_medir.sh — DAY312, medidas del paso 2 (Vault en modo servidor en la VM etcd). Instrumento: se commitea.
# Se ejecuta EN la VM etcd con sudo:  sudo bash /vagrant/scripts/etcd_ha/d312_vault_medir.sh [CERT_OTRO KEY_OTRO]
# CERT_OTRO/KEY_OTRO: certificado de otra identidad de la CA (p. ej. sniffer) para comprobar que Vault la rechaza.
# Escribe UNA vez argus-hmac/d312/prueba (la política no permite borrar: queda como rastro de la medida).
# Nunca imprime la clave de desellado ni tokens: solo longitudes y códigos.
set -u
export VAULT_ADDR=https://127.0.0.1:8200 VAULT_CACERT=/etc/vault.d/tls/ca.crt
ES_CRT=/etc/argus-pki/etcd-server.crt; ES_KEY=/etc/argus-pki/etcd-server.key
R=0; ok() { echo "[VAULT-MEDIR] PASA $*"; }; ko() { echo "[VAULT-MEDIR] FALLA $*"; R=1; }
echo "[VAULT-MEDIR] host=$(hostname) $(date -u +%FT%TZ)"

S=$(VAULT_CLIENT_CERT=$ES_CRT VAULT_CLIENT_KEY=$ES_KEY vault status -format=json 2>/dev/null)
echo "$S" | python3 -c 'import sys,json; s=json.load(sys.stdin); print("[VAULT-MEDIR] estado sealed=%s storage=%s version=%s" % (s["sealed"], s["storage_type"], s["version"]))' \
  || ko "M1 no se pudo leer el estado"
echo "$S" | grep -q '"sealed": false' && ok "M1 desellado" || ko "M1 sellado"

T=$(VAULT_CLIENT_CERT=$ES_CRT VAULT_CLIENT_KEY=$ES_KEY vault login -method=cert -path=cert -token-only name=etcd-server 2>/dev/null)
[ "${#T}" -gt 20 ] && ok "M2a login CN=etcd-server (token de ${#T} caracteres)" || ko "M2a login CN=etcd-server"
kv() { VAULT_TOKEN=$T VAULT_CLIENT_CERT=$ES_CRT VAULT_CLIENT_KEY=$ES_KEY vault "$@" 2>&1; }
if kv kv get -field=huella argus-hmac/d312/prueba > /dev/null; then
  ok "M2b argus-hmac/d312/prueba ya existe (corrida anterior): huella=$(kv kv get -field=huella argus-hmac/d312/prueba)"
else
  kv kv put argus-hmac/d312/prueba huella=d312abcd > /dev/null && ok "M2b escrita argus-hmac/d312/prueba" || ko "M2b escritura"
fi
[ "$(kv kv get -field=huella argus-hmac/d312/prueba)" = "d312abcd" ] && ok "M2c relectura huella=d312abcd" || ko "M2c relectura"
kv kv metadata delete argus-hmac/d312/prueba | grep -q 'Code: 403' && ok "M2d borrar -> 403" || ko "M2d borrar no dio 403"
kv kv put secret/d312 a=1 | grep -q 'Code: 403' && ok "M2e fuera de argus-hmac/ -> 403" || ko "M2e fuera de argus-hmac/ no dio 403"

if [ $# -eq 2 ]; then
  O=$(VAULT_CLIENT_CERT=$1 VAULT_CLIENT_KEY=$2 vault login -method=cert -path=cert -token-only name=etcd-server 2>&1)
  echo "$O" | grep -q 'Code: 400' && ok "M3 login con otra identidad ($(openssl x509 -in "$1" -noout -subject -nameopt RFC2253 | sed 's/^subject=//; s/^CN=\([^,]*\).*/\1/')) -> 400" || ko "M3 otra identidad no dio 400"
else
  echo "[VAULT-MEDIR] M3 omitida (sin CERT_OTRO KEY_OTRO)"
fi
H=$(curl -s -o /dev/null -w '%{http_code}' --cacert $VAULT_CACERT https://127.0.0.1:8200/v1/sys/health); RC=$?
[ "$RC" -ne 0 ] && [ "$H" = "000" ] && ok "M4 sin certificado de cliente: sin TLS (curl rc=$RC)" || ko "M4 sin certificado: http=$H rc=$RC"
L=$(ss -ltnH 'sport = :8200' | awk '{print $4}' | sort -u | tr '\n' ' ')
[ "$L" = "127.0.0.1:8200 " ] && ok "M5 escucha solo en 127.0.0.1:8200" || ko "M5 escucha: $L"
P=$(stat -c '%a %U' /etc/vault.d/unseal.key 2>/dev/null)
[ "$P" = "600 root" ] && ok "M6 unseal.key 600 root" || ko "M6 unseal.key: $P"
echo "[VAULT-MEDIR] RESULTADO $([ $R -eq 0 ] && echo PASA || echo FALLA)"
exit $R
