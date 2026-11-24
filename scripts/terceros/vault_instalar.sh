#!/usr/bin/env bash
# scripts/terceros/vault_instalar.sh — [TERCEROS-VAULT-D333] DEBT-LAB-TERCEROS-DESCARGA-SIN-VERIFICAR-001, lente Vault:
# HashiCorp Vault desde el repositorio apt oficial de HashiCorp, con su clave comprobada por huella y la versión fijada.
# Se ejecuta EN el defender y en la VM etcd (control-1), como root: aprovisionador vault-install del Vagrantfile
# (VAULT_INSTALL, [VAULT-INSTALL-D312]: un único sitio donde se instala Vault). Lee de provisioning/vault/:
#   VERSION  versión exacta del paquete deb, X.Y.Z-N (p. ej. 2.2.1-1). Sin defecto: mal o ausente, para (error de
#            fabricante: el lab lo ve antes que nadie).
#   CLAVE    huella de la clave de firma del repositorio (lib_apt_oficial.sh)
# Antes (hasta DAY332): la versión en el Vagrantfile (VAULT_PIN) y la clave bajada con wget e instalada sin comprobar,
# fuera la que fuera. HashiCorp la rotó el 10-sep-2026 (medido DAY333; ver provisioning/vault/CLAVE).
# El repositorio se configura SIEMPRE, también si Vault ya está en su versión: una VM aprovisionada con la clave de
# antes de la rotación pasa a la nueva, y se borra el anillo de antes (hashicorp-archive-keyring.gpg) si ya nadie lo usa.
# Las funciones vault_* no tocan el sistema (las prueba scripts/terceros/test_vault_instalar.sh en el Mac).
set -u
LC_ALL=C; export LC_ALL
log() { echo "[TERCEROS-VAULT] $*"; }
fallo() { echo "[TERCEROS-VAULT] FALLA: $*"; exit 1; }

# vault_version_valida VERSION -> rc 0 si es X.Y.Z-N (la cadena entera: un salto de línea dentro también es error)
vault_version_valida() {
  [[ "$1" =~ ^[0-9]{1,3}[.][0-9]{1,3}[.][0-9]{1,3}-[0-9]{1,3}$ ]]
}

# vault_binario_cuadra VERSION LINEA -> rc 0 si la primera línea de `vault version` es de esa versión
# (medido DAY332: "Vault v2.2.1 (0e7c41b936218bd2401ab0f891c93bec10e2e8e4), built 2026-10-22T16:27:49Z")
vault_binario_cuadra() {
  case "$2" in
    "Vault v${1%-*} ("*) return 0 ;;
  esac
  return 1
}

# vault_anillo_huerfano ANILLO FICHERO... -> rc 0 si ninguno de los ficheros (los de apt) nombra el anillo
vault_anillo_huerfano() {
  local anillo=$1; shift
  ! grep -qsF "$anillo" "$@"
}

main() {
  local src=${VAULT_SRC:-/vagrant/provisioning/vault} lib v actual linea
  local viejo=/usr/share/keyrings/hashicorp-archive-keyring.gpg
  lib=$(dirname "${BASH_SOURCE[0]}")/../vigilancia/lib_apt_oficial.sh
  [ "$(id -u)" = 0 ] || fallo "hay que ejecutarlo como root"
  for f in VERSION CLAVE; do [ -r "$src/$f" ] || fallo "no leo $src/$f"; done
  v=$(tr -d '[:space:]' < "$src/VERSION")
  vault_version_valida "$v" || fallo "$src/VERSION: '$v' mal formado (X.Y.Z-N: p. ej. 2.2.1-1). ERROR DE FABRICANTE: avisar a aRGus"
  log "versión $v (de $src/VERSION)"
  [ -r "$lib" ] || fallo "no leo $lib"
  # shellcheck source=../vigilancia/lib_apt_oficial.sh
  . "$lib"
  repo_oficial hashicorp https://apt.releases.hashicorp.com/gpg "$src/CLAVE" \
    https://apt.releases.hashicorp.com "bookworm main" || fallo "repositorio de HashiCorp"
  if [ -e "$viejo" ]; then
    if vault_anillo_huerfano "$viejo" /etc/apt/sources.list /etc/apt/sources.list.d/*; then
      rm -f "$viejo" && log "borrado $viejo (el anillo de antes de [TERCEROS-VAULT-D333]; ya no lo nombra apt)"
    else
      log "AVISO: $viejo sigue nombrado en la configuración de apt; no se borra"
    fi
  fi
  actual=$(dpkg-query -W -f='${Version}' vault 2>/dev/null || true)
  if [ "$actual" = "$v" ]; then
    apt-mark hold vault >/dev/null || fallo "apt-mark hold vault"
    log "vault $v ya instalado"
  else
    log "instalando vault $v (instalado antes: ${actual:-ninguno})"
    actualizar_indices || fallo "apt-get update"
    instalar_fijado vault "$v" || fallo "vault $v"
  fi
  linea=$(vault version 2>&1 | head -1)
  vault_binario_cuadra "$v" "$linea" || fallo "el binario dice '$linea', se espera la versión ${v%-*}"
  log "✅ $linea (paquete $v de provisioning/vault/VERSION, fijado con apt-mark hold)"
}

if [ "${BASH_SOURCE[0]}" = "$0" ]; then main "$@"; fi
