#!/usr/bin/env bash
# scripts/terceros/test_vault_instalar.sh — [TERCEROS-VAULT-D333] tests de las funciones vault_* de vault_instalar.sh y
# de provisioning/vault/{VERSION,CLAVE} (Mac, sin VMs ni red: no tocan el sistema). Cada caso de rechazo se vuelve a
# correr contra funciones que lo aceptan todo, y tiene que fallar ahí: así se ve que el test distingue.
set -u
LC_ALL=C; export LC_ALL
aqui=$(dirname "$0")
src=${VAULT_SRC:-$aqui/../../provisioning/vault}
. "$aqui/vault_instalar.sh"

BIN='Vault v2.2.1 (0e7c41b936218bd2401ab0f891c93bec10e2e8e4), built 2026-10-22T16:27:49Z'
NUEVA=D55C0D1AC78A8D8126CB631CFC9CA96ACA026560
VIEJA=798AEC654E5C15428C8E42EEAA16FCBCA621E701
ANILLO=/usr/share/keyrings/hashicorp-archive-keyring.gpg
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
printf 'deb [signed-by=/usr/share/keyrings/hashicorp.gpg] https://apt.releases.hashicorp.com bookworm main\n' > "$tmp/nueva.list"
printf 'deb [signed-by=%s] https://apt.releases.hashicorp.com bookworm main\n' "$ANILLO" > "$tmp/vieja.list"
casos=0; fallos=0; rechazos=0; rechazos_vistos=0

acepta() { local n=$1; shift; casos=$((casos + 1)); if "$@" >/dev/null 2>&1; then echo "✅ $n"; else echo "❌ $n"; fallos=$((fallos + 1)); fi; }
rechaza() { local n=$1; shift; casos=$((casos + 1)); rechazos=$((rechazos + 1)); if "$@" >/dev/null 2>&1; then echo "❌ $n"; fallos=$((fallos + 1)); rechazos_vistos=$((rechazos_vistos + 1)); else echo "✅ $n"; fi; }
# huellas FICHERO -> las líneas sin comentar, como las lee lib_apt_oficial.sh
huellas() { grep -v '^#' "$1" | tr -d ' \t' | grep -E '^[0-9A-F]{40}$' | sort -u; }
version_repo() { vault_version_valida "$(tr -d '[:space:]' < "$src/VERSION")"; }
clave_es() { [ "$(huellas "$src/CLAVE")" = "$1" ]; }
clave_sin_basura() { [ "$(grep -v '^#' "$src/CLAVE" | grep -vc '^[[:space:]]*$')" = 1 ]; }

los_casos() {
  acepta "versión 2.2.1-1 válida" vault_version_valida 2.2.1-1
  acepta "versión 10.0.12-3 válida" vault_version_valida 10.0.12-3
  rechaza "versión 2.2.1 (sin revisión del paquete)" vault_version_valida 2.2.1
  rechaza "versión 2.2-1 (sin parche)" vault_version_valida 2.2-1
  rechaza "versión v2.2.1-1 (con v)" vault_version_valida v2.2.1-1
  rechaza "versión 2.2.1+ent-1 (enterprise)" vault_version_valida 2.2.1+ent-1
  rechaza "versión vacía" vault_version_valida ""
  rechaza "versión latest (por nombre)" vault_version_valida latest
  rechaza "dos versiones en dos líneas" vault_version_valida $'2.2.1-1\n2.2.2-1'
  acepta "el binario medido DAY332 es 2.2.1-1" vault_binario_cuadra 2.2.1-1 "$BIN"
  rechaza "el binario es otra versión (2.2.2)" vault_binario_cuadra 2.2.1-1 "${BIN/v2.2.1/v2.2.2}"
  rechaza "el binario 2.2.10 no es 2.2.1" vault_binario_cuadra 2.2.1-1 "${BIN/v2.2.1/v2.2.10}"
  rechaza "el binario enterprise 2.2.1+ent" vault_binario_cuadra 2.2.1-1 "${BIN/v2.2.1/v2.2.1+ent}"
  rechaza "el binario no responde" vault_binario_cuadra 2.2.1-1 ""
  rechaza "vault no está (bash: vault: command not found)" vault_binario_cuadra 2.2.1-1 "bash: vault: command not found"
  acepta "anillo de antes huérfano: solo la lista nueva" vault_anillo_huerfano "$ANILLO" "$tmp/nueva.list"
  acepta "anillo de antes huérfano: sin ficheros de apt" vault_anillo_huerfano "$ANILLO" "$tmp/no-existe.list"
  rechaza "anillo de antes aún nombrado por una lista" vault_anillo_huerfano "$ANILLO" "$tmp/nueva.list" "$tmp/vieja.list"
  acepta "provisioning/vault/VERSION bien formado" version_repo
  acepta "provisioning/vault/CLAVE es la huella contrastada DAY333" clave_es "$NUEVA"
  acepta "provisioning/vault/CLAVE: una sola línea sin comentar" clave_sin_basura
  rechaza "provisioning/vault/CLAVE no es la clave de antes de la rotación" clave_es "$VIEJA"
}

los_casos
echo "$((casos - fallos))/$casos casos"
total=$fallos

# Contra funciones que lo aceptan todo, cada rechazo tiene que dar ❌.
vault_version_valida() { return 0; }
vault_binario_cuadra() { return 0; }
vault_anillo_huerfano() { return 0; }
clave_es() { return 0; }
esperados=$rechazos; casos=0; fallos=0; rechazos=0; rechazos_vistos=0
los_casos > /dev/null
if [ "$rechazos_vistos" = "$esperados" ]; then
  echo "✅ contra funciones que lo aceptan todo fallan los $esperados casos de rechazo"
else
  echo "❌ contra funciones que lo aceptan todo fallan $rechazos_vistos de los $esperados casos de rechazo"; total=$((total + 1))
fi
[ "$total" = 0 ] && echo "✅ test-vault-instalar" || { echo "❌ test-vault-instalar: $total fallos"; exit 1; }
