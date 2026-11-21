#!/usr/bin/env bash
# scripts/terceros/test_arrow_instalar.sh — [TERCEROS-ARROW-D333] tests de las funciones arrow_* de arrow_instalar.sh y de
# provisioning/arrow/{VERSION,CLAVE} (Mac, sin VMs ni red: no tocan el sistema). Cada caso de rechazo se vuelve a correr
# contra funciones que lo aceptan todo, y tiene que fallar ahí: así se ve que el test distingue.
set -u
LC_ALL=C; export LC_ALL
aqui=$(dirname "$0")
src=${ARROW_SRC:-$aqui/../../provisioning/arrow}
. "$aqui/arrow_instalar.sh"

FIRMA=BE7EF45DBAD38E4EECED390E9CBA4EF977CA20B8
# salida de gpgv medida DAY333 sobre el InRelease de bookworm con el anillo de KEYS
GPGV_BIEN="gpgv: Signature made Fri Jul 24 15:07:24 2026 UTC
gpgv:                using RSA key $FIRMA
gpgv: Good signature from \"David Li (CODE SIGNING KEY) <lidavidm@apache.org>\""
GPGV_MAL="gpgv: Signature made Fri Jul 24 15:07:24 2026 UTC
gpgv:                using RSA key $FIRMA
gpgv: BAD signature from \"David Li (CODE SIGNING KEY) <lidavidm@apache.org>\""
GPGV_SIN="gpgv: Signature made Fri Jul 24 15:07:24 2026 UTC
gpgv:                using RSA key $FIRMA
gpgv: Can't check signature: No public key"
BIEN=$'libarrow-dev=24.0.0-1\nlibparquet-dev=24.0.0-1'
casos=0; fallos=0; rechazos=0; rechazos_vistos=0

acepta() { local n=$1; shift; casos=$((casos + 1)); if "$@" >/dev/null 2>&1; then echo "✅ $n"; else echo "❌ $n"; fallos=$((fallos + 1)); fi; }
rechaza() { local n=$1; shift; casos=$((casos + 1)); rechazos=$((rechazos + 1)); if "$@" >/dev/null 2>&1; then echo "❌ $n"; fallos=$((fallos + 1)); rechazos_vistos=$((rechazos_vistos + 1)); else echo "✅ $n"; fi; }
firmante_es() { [ "$(printf '%s\n' "$1" | arrow_firmante)" = "$2" ]; }
firmante() { printf '%s\n' "$1" | arrow_firmante; }
comprueba() { printf '%s\n' "$2" | arrow_comprobar "$1"; }
huellas() { grep -v '^#' "$1" | tr -d ' \t' | grep -E '^[0-9A-F]{40}$' | sort -u; }
version_repo() { arrow_version_valida "$(tr -d '[:space:]' < "$src/VERSION")"; }
clave_cuenta() { [ "$(huellas "$src/CLAVE" | grep -c .)" = "$1" ]; }
clave_tiene() { huellas "$src/CLAVE" | grep -qxF "$1"; }
clave_sin_basura() { [ "$(grep -v '^#' "$src/CLAVE" | grep -vc '^[[:space:]]*$')" = "$(huellas "$src/CLAVE" | grep -c .)" ]; }

los_casos() {
  acepta "versión 24.0.0-1 válida" arrow_version_valida 24.0.0-1
  rechaza "versión 24.0.0 (sin revisión del paquete)" arrow_version_valida 24.0.0
  rechaza "versión 24-1" arrow_version_valida 24-1
  rechaza "versión vacía" arrow_version_valida ""
  rechaza "versión latest (como el .deb de antes)" arrow_version_valida latest
  rechaza "dos versiones en dos líneas" arrow_version_valida $'24.0.0-1\n23.0.1-1'
  acepta "gpgv medido DAY333: firmante BE7EF45D…" firmante_es "$GPGV_BIEN" "$FIRMA"
  rechaza "gpgv con BAD signature" firmante "$GPGV_MAL"
  rechaza "gpgv sin la clave pública" firmante "$GPGV_SIN"
  rechaza "gpgv sin salida" firmante ""
  rechaza "gpgv con dos firmantes" firmante "$GPGV_BIEN"$'\n'"$GPGV_BIEN"
  acepta "libarrow-dev y libparquet-dev en 24.0.0-1" comprueba 24.0.0-1 "$BIEN"
  acepta "otros paquetes de Arrow no cuentan" comprueba 24.0.0-1 "$BIEN"$'\nlibarrow2400=24.0.0-1'
  rechaza "libparquet-dev en otra versión" comprueba 24.0.0-1 "${BIEN/libparquet-dev=24.0.0-1/libparquet-dev=23.0.1-1}"
  rechaza "falta libparquet-dev" comprueba 24.0.0-1 "libarrow-dev=24.0.0-1"
  rechaza "falta libarrow-dev" comprueba 24.0.0-1 "libparquet-dev=24.0.0-1"
  rechaza "nada instalado" comprueba 24.0.0-1 ""
  acepta "provisioning/arrow/VERSION bien formado" version_repo
  acepta "provisioning/arrow/CLAVE: las 25 de KEYS medidas DAY333" clave_cuenta 25
  acepta "provisioning/arrow/CLAVE: incluye la que firma hoy" clave_tiene "$FIRMA"
  acepta "provisioning/arrow/CLAVE: sin líneas que no sean huellas" clave_sin_basura
  rechaza "provisioning/arrow/CLAVE no tiene una huella inventada" clave_tiene 0000000000000000000000000000000000000000
}

los_casos
echo "$((casos - fallos))/$casos casos"
total=$fallos

# Contra funciones que lo aceptan todo, cada rechazo tiene que dar ❌.
arrow_version_valida() { return 0; }
arrow_firmante() { cat >/dev/null; return 0; }
arrow_comprobar() { cat >/dev/null; return 0; }
clave_tiene() { return 0; }
esperados=$rechazos; casos=0; fallos=0; rechazos=0; rechazos_vistos=0
los_casos > /dev/null
if [ "$rechazos_vistos" = "$esperados" ]; then
  echo "✅ contra funciones que lo aceptan todo fallan los $esperados casos de rechazo"
else
  echo "❌ contra funciones que lo aceptan todo fallan $rechazos_vistos de los $esperados casos de rechazo"; total=$((total + 1))
fi
[ "$total" = 0 ] && echo "✅ test-arrow-instalar" || { echo "❌ test-arrow-instalar: $total fallos"; exit 1; }
