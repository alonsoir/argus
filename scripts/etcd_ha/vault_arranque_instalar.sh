#!/usr/bin/env bash
# scripts/etcd_ha/vault_arranque_instalar.sh — [VAULT-ARRANQUE-D322] arranque del Vault del lab (VM etcd): desellado
# ligado a vault.service con identidad propia y rotación del audit sin SIGHUP a un Vault que arranca.
# Se ejecuta EN la VM etcd, como root: aprovisionador "vault-arranque" del Vagrantfile (run: always), DESPUÉS de
# vault-install (crea el usuario vault y vault.service) y ANTES de vault-server (que ya espera el desellado puesto).
# Medido DAY322: logrotate.timer (Persistent=true) corre al arrancar la VM tras una noche apagada, su postrotate mandaba
# SIGHUP a un Vault que aún arrancaba (vault.service "Failed with result 'protocol'"), Restart=on-failure lo levantaba
# SELLADO y el desellado, ligado a multi-user.target, ya se había descartado ("Dependency failed"): solo lo arrancaba,
# de rebote, el `systemctl start` del aprovisionador etcd-server-unit (Wants=). Sin Vagrant, Vault se quedaba sellado.
# Lee de provisioning/vault/ (nada en el código):
#   argus-vault-unseal            script de desellado     -> /usr/local/sbin/argus-vault-unseal (0755)
#   argus-vault-unseal.service    unidad, WantedBy=vault  -> /etc/systemd/system/argus-vault-unseal.service (0644)
#   argus-vault-audit.logrotate   rotación del audit      -> /etc/logrotate.d/argus-vault-audit (0644)
# Y de /tmp/argus-pki-unseal/ (aprovisionadores file desde ARGUS_PKI_DIR del Mac; se borra al acabar):
#   ca.crt, argus-vault-unseal.crt, argus-vault-unseal.key -> /etc/argus-pki/argus-vault-unseal.{crt,key} (0644/0600 root)
# Comprueba: certificado firmado por la CA, CN=OU=argus-vault-unseal, clave que casa con el certificado; unidad
# habilitada SOLO en vault.service.wants (no en multi-user.target.wants); logrotate acepta el fichero. Si Vault está
# activo, lanza el desellado y comprueba que acaba bien. Cualquier fallo: rc 1 con el motivo.
set -u
LC_ALL=C; export LC_ALL
SRC=${VAULT_ARRANQUE_SRC:-/vagrant/provisioning/vault}
PKI_IN=/tmp/argus-pki-unseal
PKI=/etc/argus-pki
CRT=$PKI/argus-vault-unseal.crt
KEY=$PKI/argus-vault-unseal.key
UNIDAD=argus-vault-unseal.service
log() { echo "[VAULT-ARRANQUE] $*"; }
fallo() { echo "[VAULT-ARRANQUE] FALLA: $*"; exit 1; }

[ "$(id -u)" = 0 ] || fallo "hay que ejecutarlo como root"
for f in argus-vault-unseal argus-vault-unseal.service argus-vault-audit.logrotate; do
  [ -r "$SRC/$f" ] || fallo "no leo $SRC/$f"
done
id vault > /dev/null 2>&1 || fallo "no existe el usuario vault (¿corrió el aprovisionador vault-install?)"
systemctl cat vault.service > /dev/null 2>&1 || fallo "no existe vault.service (¿corrió el aprovisionador vault-install?)"
command -v openssl > /dev/null || fallo "no hay openssl"
command -v logrotate > /dev/null || { apt-get install -y logrotate > /dev/null 2>&1 || fallo "no se pudo instalar logrotate"; }

# 1 identidad del desellado (CN=OU=argus-vault-unseal, sin políticas en Vault)
install -d -m 0700 -o root -g root "$PKI"
if [ -d "$PKI_IN" ]; then
  for f in ca.crt argus-vault-unseal.crt argus-vault-unseal.key; do
    [ -s "$PKI_IN/$f" ] || fallo "falta $PKI_IN/$f; en el Mac: bash scripts/etcd_ha/d312_pki.sh cliente \$ARGUS_PKI_DIR argus-vault-unseal"
  done
  openssl verify -CAfile "$PKI_IN/ca.crt" "$PKI_IN/argus-vault-unseal.crt" > /dev/null 2>&1 \
    || fallo "argus-vault-unseal.crt no lo firma la CA del lab (ca.crt de ARGUS_PKI_DIR)"
  SUJ=$(openssl x509 -in "$PKI_IN/argus-vault-unseal.crt" -noout -subject -nameopt RFC2253)
  case "$SUJ" in
    *CN=argus-vault-unseal*) ;; *) fallo "argus-vault-unseal.crt con sujeto '$SUJ' (se espera CN=argus-vault-unseal)";;
  esac
  case "$SUJ" in
    *OU=argus-vault-unseal*) ;; *) fallo "argus-vault-unseal.crt con sujeto '$SUJ' (se espera OU=argus-vault-unseal)";;
  esac
  P_CRT=$(openssl x509 -in "$PKI_IN/argus-vault-unseal.crt" -noout -pubkey | openssl sha256 | awk '{print $NF}')
  P_KEY=$(openssl pkey -in "$PKI_IN/argus-vault-unseal.key" -pubout | openssl sha256 | awk '{print $NF}')
  [ "$P_CRT" = "$P_KEY" ] || fallo "argus-vault-unseal.key no casa con argus-vault-unseal.crt"
  # Mismo certificado (público) ya puesto y clave presente: no se reescribe nada. La clave instalada no se lee para
  # compararla (sería una lectura ajena para Falco) y reescribirla en cada `vagrant up` dispararía el FIM de Wazuh.
  if [ -s "$KEY" ] && [ -f "$CRT" ] && cmp -s "$PKI_IN/argus-vault-unseal.crt" "$CRT"; then
    log "identidad sin cambios (mismo certificado): no se reinstala"
  else
    install -m 0644 -o root -g root "$PKI_IN/argus-vault-unseal.crt" "$CRT"
    install -m 0600 -o root -g root "$PKI_IN/argus-vault-unseal.key" "$KEY"
    log "identidad instalada en $PKI"
  fi
  rm -rf "$PKI_IN"
fi
[ -s "$CRT" ] && [ -s "$KEY" ] || fallo "faltan $CRT o $KEY; en el Mac: bash scripts/etcd_ha/d312_pki.sh cliente \$ARGUS_PKI_DIR argus-vault-unseal"
[ "$(stat -c '%a %U' "$KEY")" = "600 root" ] || fallo "$KEY con permisos $(stat -c '%a %U' "$KEY") (se espera 600 root)"
log "identidad: $(openssl x509 -in "$CRT" -noout -subject -nameopt RFC2253 | sed 's/^subject=//'), huella $(openssl x509 -in "$CRT" -noout -fingerprint -sha256 | sed 's/^.*=//; s/://g' | cut -c1-16)"

# 2 ficheros (solo si cambian)
CAMBIOS=0
poner() {  # origen destino modo
  if [ -f "$2" ] && cmp -s "$1" "$2"; then return 0; fi
  install -D -m "$3" -o root -g root "$1" "$2" || fallo "no se pudo poner $2"
  CAMBIOS=$((CAMBIOS + 1)); log "puesto $2"
}
install -d -m 0750 -o vault -g vault /var/log/vault
poner "$SRC/argus-vault-unseal"          /usr/local/sbin/argus-vault-unseal          0755
poner "$SRC/argus-vault-unseal.service"  /etc/systemd/system/$UNIDAD                 0644
poner "$SRC/argus-vault-audit.logrotate" /etc/logrotate.d/argus-vault-audit          0644
logrotate -d /etc/logrotate.d/argus-vault-audit > /dev/null 2>&1 || fallo "logrotate rechaza /etc/logrotate.d/argus-vault-audit"

# 3 unidad ligada a vault.service, y solo ahí (reenable quita el enlace viejo de multi-user.target.wants)
systemctl daemon-reload
systemctl reenable "$UNIDAD" > /dev/null 2>&1 || fallo "systemctl reenable $UNIDAD"
[ -L /etc/systemd/system/vault.service.wants/$UNIDAD ] || fallo "$UNIDAD no quedó en vault.service.wants"
[ ! -e /etc/systemd/system/multi-user.target.wants/$UNIDAD ] || fallo "$UNIDAD sigue en multi-user.target.wants"
log "$UNIDAD habilitada en vault.service.wants (cada arranque de Vault lo dessella); $CAMBIOS fichero(s) cambiado(s)"

# 4 si Vault está en marcha, desellar ya (idempotente: desellado o sin inicializar da rc 0)
if systemctl is-active --quiet vault.service; then
  systemctl start "$UNIDAD" || fallo "$UNIDAD falló: journalctl -u $UNIDAD -n 20"
  log "desellado comprobado: $(journalctl -u "$UNIDAD" -b -o cat --no-pager 2>/dev/null | grep -F '[VAULT-UNSEAL]' | tail -1)"
else
  log "vault.service no está activo: el desellado irá con su próximo arranque"
fi
log "HECHO"
