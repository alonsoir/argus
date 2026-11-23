#!/usr/bin/env bash
# scripts/terceros/test_cpphttplib_instalar.sh — [TERCEROS-HTTPLIB-D335] tests de las funciones ch_* de
# cpphttplib_instalar.sh y de provisioning/cpp-httplib/{VERSION,COMMIT} (Mac, sin VMs ni red). El tag contra el commit
# fijado y los reintentos, en test_lib_git_fijado.sh. Cada caso de rechazo se vuelve a correr contra funciones que lo
# aceptan todo, y tiene que fallar ahí: así se ve que el test distingue.
set -u
LC_ALL=C; export LC_ALL
aqui=$(dirname "$0")
src=${CPPHTTPLIB_SRC:-$aqui/../../provisioning/cpp-httplib}
. "$aqui/cpphttplib_instalar.sh"

COMMIT_DAY335=7800c3dc5b33285cbb18baa5998de4ff7ef63515
OTRO_COMMIT=0123456789abcdef0123456789abcdef01234567
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
casos=0; fallos=0; rechazos=0; rechazos_vistos=0
acepta() { local n=$1; shift; casos=$((casos + 1)); if "$@" >/dev/null 2>&1; then echo "✅ $n"; else echo "❌ $n"; fallos=$((fallos + 1)); fi; }
rechaza() { local n=$1; shift; casos=$((casos + 1)); rechazos=$((rechazos + 1)); if "$@" >/dev/null 2>&1; then echo "❌ $n"; fallos=$((fallos + 1)); rechazos_vistos=$((rechazos_vistos + 1)); else echo "✅ $n"; fi; }

# cabeceras de juguete: las líneas 11 y 12 de la httplib.h del tag v0.67.0 (medido DAY335), otra versión, y sin define
cabecera() { printf '//\n//  httplib.h\n//\n#ifndef CPPHTTPLIB_HTTPLIB_H\n#define CPPHTTPLIB_HTTPLIB_H\n\n#define CPPHTTPLIB_VERSION "%s"\n#define CPPHTTPLIB_VERSION_NUM "0x004300"\n' "$1"; }
cabecera 0.67.0 > "$T/h_bien"
cabecera 0.66.0 > "$T/h_otra"
printf '#ifndef CPPHTTPLIB_HTTPLIB_H\n#endif\n' > "$T/h_sin"
cp "$T/h_bien" "$T/h_tocada"; echo '// cambiada' >> "$T/h_tocada"
printf '%s %s\n' "$COMMIT_DAY335" "$(ch_sha256 "$T/h_bien")" > "$T/m_bien"
printf '%s %s\n' "$OTRO_COMMIT" "$(ch_sha256 "$T/h_bien")" > "$T/m_otro"
printf '%s\n' "$COMMIT_DAY335" > "$T/m_sin_sha"

version_es() { [ "$(ch_version_de_cabecera "$1")" = "$2" ]; }
sha_es() { [ "$(ch_sha256 "$1")" = "$2" ]; }
version_repo() { gf_version_valida "$(tr -d '[:space:]' < "$src/VERSION")"; }
commit_repo_es() { [ "$(gf_commit_de_fichero "$src/COMMIT")" = "$1" ]; }
carga_lib() { declare -F gf_clonar >/dev/null; }

los_casos() {
  acepta "cpphttplib_instalar.sh carga lib_git_fijado.sh (gf_clonar definida)" carga_lib
  acepta "versión de la cabecera del tag v0.67.0" version_es "$T/h_bien" 0.67.0
  acepta "versión de una cabecera 0.66.0" version_es "$T/h_otra" 0.66.0
  acepta "cabecera sin CPPHTTPLIB_VERSION: vacío" version_es "$T/h_sin" ""
  acepta "cabecera que no existe: vacío" version_es "$T/no_existe" ""
  acepta "sha256 de un fichero conocido" sha_es "$T/h_sin" "$(printf '#ifndef CPPHTTPLIB_HTTPLIB_H\n#endif\n' | { command -v sha256sum >/dev/null && sha256sum || shasum -a 256; } | cut -d' ' -f1)"
  acepta "estado: cabecera 0.67.0 y marca con su commit y su sha256" ch_estado 0.67.0 "$COMMIT_DAY335" "$T/h_bien" "$T/m_bien"
  rechaza "estado: la cabecera dice otra versión (0.66.0)" ch_estado 0.67.0 "$COMMIT_DAY335" "$T/h_otra" "$T/m_bien"
  rechaza "estado: cabecera cambiada después de instalar (otro sha256)" ch_estado 0.67.0 "$COMMIT_DAY335" "$T/h_tocada" "$T/m_bien"
  rechaza "estado: la marca dice otro commit" ch_estado 0.67.0 "$COMMIT_DAY335" "$T/h_bien" "$T/m_otro"
  rechaza "estado: marca sin sha256 (solo el commit)" ch_estado 0.67.0 "$COMMIT_DAY335" "$T/h_bien" "$T/m_sin_sha"
  rechaza "estado: sin marca (la httplib.h de antes, de la rama principal)" ch_estado 0.67.0 "$COMMIT_DAY335" "$T/h_bien" "$T/no_existe"
  rechaza "estado: sin cabecera" ch_estado 0.67.0 "$COMMIT_DAY335" "$T/no_existe" "$T/m_bien"
  acepta "provisioning/cpp-httplib/VERSION bien formado" version_repo
  acepta "provisioning/cpp-httplib/COMMIT es el del tag v0.67.0 (medido DAY335)" commit_repo_es "$COMMIT_DAY335"
  rechaza "provisioning/cpp-httplib/COMMIT no es otro commit" commit_repo_es "$OTRO_COMMIT"
}

los_casos
echo "$((casos - fallos))/$casos casos"
total=$fallos

# Contra funciones que lo aceptan todo, cada rechazo tiene que dar ❌.
ch_estado() { return 0; }
commit_repo_es() { return 0; }
esperados=$rechazos; casos=0; fallos=0; rechazos=0; rechazos_vistos=0
los_casos > /dev/null
if [ "$rechazos_vistos" = "$esperados" ]; then
  echo "✅ contra funciones que lo aceptan todo fallan los $esperados casos de rechazo"
else
  echo "❌ contra funciones que lo aceptan todo fallan $rechazos_vistos de los $esperados casos de rechazo"; total=$((total + 1))
fi
[ "$total" = 0 ] && echo "✅ test-cpphttplib-instalar" || { echo "❌ test-cpphttplib-instalar: $total fallos"; exit 1; }
