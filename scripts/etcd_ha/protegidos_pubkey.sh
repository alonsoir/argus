#!/usr/bin/env bash
# protegidos_pubkey.sh — DAY318, ADR-060 8e.2 [PROTEGIDOS-PUBKEY-D318]. Se ejecuta en el Mac, raíz del repo
# (make protegidos-pubkey; el bootstrap lo llama en [4b/8], antes de compilar).
# Lleva la clave PÚBLICA del manifiesto de protegidos de la VM etcd (Vault transit) al defender, donde CMake la compila en
# el firewall-acl-agent (patrón ADR-025; sin ella el firewall no compila):
#   /etc/ml-defender/firewall-acl-agent/protegidos_pubkey_actual.hex   (ranura actual, 64 hex + salto de línea, 0644)
# La ranura siguiente (protegidos_pubkey_siguiente.hex) solo existe durante una rotación; este script no la escribe y
# avisa si la encuentra. Por la terminal solo sale la huella (16 hex del sha256 de los 32 bytes), nunca la clave entera.
set -u
export LC_ALL=C
TAG=PROTEGIDOS-PUBKEY
falla() { echo "[$TAG] FALLA: $*" >&2; exit 1; }
DESTINO=/etc/ml-defender/firewall-acl-agent/protegidos_pubkey_actual.hex
SIGUIENTE=/etc/ml-defender/firewall-acl-agent/protegidos_pubkey_siguiente.hex
CRUDO=$(vagrant ssh control-1 -c "sudo bash /vagrant/scripts/etcd_ha/protegidos_pubkey_vm.sh" 2>/tmp/argus_protegidos_pubkey_err.txt)
RC=$?
SAL=$(printf '%s\n' "$CRUDO" | tr -d '\r')
CLAVE=$(printf '%s\n' "$SAL" | sed -n 's/^PROTEGIDOS_CLAVE=\(protegidos-[a-z0-9-]*\)$/\1/p')
VER=$(printf '%s\n' "$SAL" | sed -n 's/^PROTEGIDOS_VERSION=\([0-9][0-9]*\)$/\1/p')
HEX=$(printf '%s\n' "$SAL" | sed -n 's/^PROTEGIDOS_PUBKEY_HEX=\([0-9a-f]\{64\}\)$/\1/p')
if [ "$RC" -ne 0 ] || [ -z "$CLAVE" ] || [ -z "$VER" ] || [ ${#HEX} -ne 64 ]; then
  cat /tmp/argus_protegidos_pubkey_err.txt >&2
  falla "no se pudo leer la clave pública de la VM etcd (rc=$RC; arriba el error de la VM)"
fi
HUELLA=$(printf '%s' "$HEX" | xxd -r -p | shasum -a 256 2>/dev/null | cut -c1-16)
[ -n "$HUELLA" ] || HUELLA=$(printf '%s' "$HEX" | xxd -r -p | sha256sum | cut -c1-16)
LEIDO=$(vagrant ssh defender -c "sudo install -d -m 0755 /etc/ml-defender/firewall-acl-agent && printf '%s\n' '$HEX' | sudo tee $DESTINO.tmp > /dev/null && sudo chmod 0644 $DESTINO.tmp && sudo mv -f $DESTINO.tmp $DESTINO && cat $DESTINO; [ -e $SIGUIENTE ] && echo SIGUIENTE_PRESENTE" 2>/dev/null | tr -d '\r')
[ "$(printf '%s\n' "$LEIDO" | grep -c -x "$HEX")" = 1 ] || falla "la clave leída de vuelta en el defender no coincide con la de Vault"
if printf '%s\n' "$LEIDO" | grep -q -x SIGUIENTE_PRESENTE; then
  echo "[$TAG] AVISO: existe $SIGUIENTE en el defender (ranura siguiente de una rotación); este script no la toca"
fi
echo "[$TAG] clave=$CLAVE version=$VER huella=$HUELLA -> defender:$DESTINO (ranura actual)"
