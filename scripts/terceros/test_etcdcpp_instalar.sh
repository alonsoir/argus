#!/usr/bin/env bash
# scripts/terceros/test_etcdcpp_instalar.sh — [TERCEROS-ETCDCPP-D335] tests de las funciones ec_* de etcdcpp_instalar.sh
# y de provisioning/etcd-cpp-apiv3/{VERSION,COMMIT} (Mac, sin VMs ni red). El tag contra el commit fijado y los
# reintentos, en test_lib_git_fijado.sh. Medido DAY335: dos compilaciones del mismo commit dan libetcd-cpp-api.so con
# sha256 distinto (el build no es reproducible bit a bit); la marca guarda el sha256 de la instalada para ver si alguien
# la cambia después, no un sha256 de referencia: lo que se contrasta con el mantenedor es el commit. Cada caso de rechazo
# se vuelve a correr contra funciones que lo aceptan todo, y tiene que fallar ahí: así se ve que el test distingue.
set -u
LC_ALL=C; export LC_ALL
aqui=$(dirname "$0")
src=${ETCDCPP_SRC:-$aqui/../../provisioning/etcd-cpp-apiv3}
. "$aqui/etcdcpp_instalar.sh"

COMMIT_DAY335=e31ac4d4caa55fa662e207150ba40f8151b7ad96
OTRO_COMMIT=0123456789abcdef0123456789abcdef01234567
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
casos=0; fallos=0; rechazos=0; rechazos_vistos=0
acepta() { local n=$1; shift; casos=$((casos + 1)); if "$@" >/dev/null 2>&1; then echo "✅ $n"; else echo "❌ $n"; fallos=$((fallos + 1)); fi; }
rechaza() { local n=$1; shift; casos=$((casos + 1)); rechazos=$((rechazos + 1)); if "$@" >/dev/null 2>&1; then echo "❌ $n"; fallos=$((fallos + 1)); rechazos_vistos=$((rechazos_vistos + 1)); else echo "✅ $n"; fi; }

# fichero de versión de CMake de juguete: su primera línea es la de la v0.15.3 instalada (medido DAY335)
cfgver() { printf 'set(PACKAGE_VERSION "%s")\n\n# Check whether the requested PACKAGE_FIND_VERSION is compatible\n' "$1"; }
cfgver 0.15.3 > "$T/v_bien"
cfgver 0.15.4 > "$T/v_otra"
printf '# sin versión\n' > "$T/v_sin"
printf 'biblioteca de juguete\n' > "$T/so_real"
ln -s so_real "$T/so_enlace"
cp "$T/so_real" "$T/so_tocada"; printf 'x' >> "$T/so_tocada"
printf '%s %s\n' "$COMMIT_DAY335" "$(ec_sha256 "$T/so_real")" > "$T/m_bien"
printf '%s %s\n' "$OTRO_COMMIT" "$(ec_sha256 "$T/so_real")" > "$T/m_otro"
printf '%s\n' "$COMMIT_DAY335" > "$T/m_sin_sha"

version_es() { [ "$(ec_version_de_cmake "$1")" = "$2" ]; }
mismo_sha() { [ -n "$(ec_sha256 "$1")" ] && [ "$(ec_sha256 "$1")" = "$(ec_sha256 "$2")" ]; }
sha_vacio() { [ -z "$(ec_sha256 "$1")" ]; }
version_repo() { gf_version_valida "$(tr -d '[:space:]' < "$src/VERSION")"; }
commit_repo_es() { [ "$(gf_commit_de_fichero "$src/COMMIT")" = "$1" ]; }
carga_lib() { declare -F gf_clonar >/dev/null; }

los_casos() {
  acepta "etcdcpp_instalar.sh carga lib_git_fijado.sh (gf_clonar definida)" carga_lib
  acepta "versión del fichero de CMake de la v0.15.3" version_es "$T/v_bien" 0.15.3
  acepta "versión de un fichero de CMake 0.15.4" version_es "$T/v_otra" 0.15.4
  acepta "fichero de CMake sin PACKAGE_VERSION: vacío" version_es "$T/v_sin" ""
  acepta "fichero de CMake que no existe: vacío" version_es "$T/no_existe" ""
  acepta "sha256 de un enlace = el del fichero al que apunta" mismo_sha "$T/so_enlace" "$T/so_real"
  acepta "sha256 de lo que no existe: vacío" sha_vacio "$T/no_existe"
  acepta "estado: .so, versión 0.15.3 y marca con su commit y su sha256" ec_estado 0.15.3 "$COMMIT_DAY335" "$T/so_real" "$T/v_bien" "$T/m_bien"
  acepta "estado: la .so por un enlace" ec_estado 0.15.3 "$COMMIT_DAY335" "$T/so_enlace" "$T/v_bien" "$T/m_bien"
  rechaza "estado: el fichero de CMake dice otra versión (0.15.4)" ec_estado 0.15.3 "$COMMIT_DAY335" "$T/so_real" "$T/v_otra" "$T/m_bien"
  rechaza "estado: sin fichero de versión de CMake" ec_estado 0.15.3 "$COMMIT_DAY335" "$T/so_real" "$T/no_existe" "$T/m_bien"
  rechaza "estado: .so cambiada después de instalar (otro sha256)" ec_estado 0.15.3 "$COMMIT_DAY335" "$T/so_tocada" "$T/v_bien" "$T/m_bien"
  rechaza "estado: la marca dice otro commit" ec_estado 0.15.3 "$COMMIT_DAY335" "$T/so_real" "$T/v_bien" "$T/m_otro"
  rechaza "estado: marca sin sha256 (solo el commit)" ec_estado 0.15.3 "$COMMIT_DAY335" "$T/so_real" "$T/v_bien" "$T/m_sin_sha"
  rechaza "estado: sin marca (la .so de antes)" ec_estado 0.15.3 "$COMMIT_DAY335" "$T/so_real" "$T/v_bien" "$T/no_existe"
  rechaza "estado: sin .so" ec_estado 0.15.3 "$COMMIT_DAY335" "$T/no_existe" "$T/v_bien" "$T/m_bien"
  acepta "provisioning/etcd-cpp-apiv3/VERSION bien formado" version_repo
  acepta "provisioning/etcd-cpp-apiv3/COMMIT es el del tag v0.15.3 (medido DAY335)" commit_repo_es "$COMMIT_DAY335"
  rechaza "provisioning/etcd-cpp-apiv3/COMMIT no es otro commit" commit_repo_es "$OTRO_COMMIT"
}

los_casos
echo "$((casos - fallos))/$casos casos"
total=$fallos

# Contra funciones que lo aceptan todo, cada rechazo tiene que dar ❌.
ec_estado() { return 0; }
commit_repo_es() { return 0; }
esperados=$rechazos; casos=0; fallos=0; rechazos=0; rechazos_vistos=0
los_casos > /dev/null
if [ "$rechazos_vistos" = "$esperados" ]; then
  echo "✅ contra funciones que lo aceptan todo fallan los $esperados casos de rechazo"
else
  echo "❌ contra funciones que lo aceptan todo fallan $rechazos_vistos de los $esperados casos de rechazo"; total=$((total + 1))
fi
[ "$total" = 0 ] && echo "✅ test-etcdcpp-instalar" || { echo "❌ test-etcdcpp-instalar: $total fallos"; exit 1; }
