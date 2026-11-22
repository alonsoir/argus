#!/usr/bin/env bash
# scripts/terceros/test_etcd_instalar.sh — [TERCEROS-ETCD-D334] tests de las funciones etcd_* de etcd_instalar.sh y de
# provisioning/etcd/{VERSION,SHA256} (Mac, sin VMs ni red: tarballs falsos hechos aquí). Cada caso de rechazo se vuelve
# a correr contra funciones que lo aceptan todo, y tiene que fallar ahí: así se ve que el test distingue.
set -u
LC_ALL=C; export LC_ALL
aqui=$(dirname "$0")
src=${ETCD_SRC:-$aqui/../../provisioning/etcd}
. "$aqui/etcd_instalar.sh"

SHA_DAY333=c8c0d96d8292ef085deabbf735e9561d3d396768e4d606df005aa25964f21911
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
casos=0; fallos=0; rechazos=0; rechazos_vistos=0
acepta() { local n=$1; shift; casos=$((casos + 1)); if "$@" >/dev/null 2>&1; then echo "✅ $n"; else echo "❌ $n"; fallos=$((fallos + 1)); fi; }
rechaza() { local n=$1; shift; casos=$((casos + 1)); rechazos=$((rechazos + 1)); if "$@" >/dev/null 2>&1; then echo "❌ $n"; fallos=$((fallos + 1)); rechazos_vistos=$((rechazos_vistos + 1)); else echo "✅ $n"; fi; }

# binarios falsos: un script que contesta como el de verdad (medido DAY334 en los de v3.6.16)
falso() { # falso DIR NOMBRE VERSION
  if [ "$2" = etcd ]; then
    printf '#!/bin/sh\n[ "$1" = --version ] && { echo "etcd Version: %s"; echo "Git SHA: x"; }\n' "$3" > "$1/$2"
  else
    printf '#!/bin/sh\n[ "$1" = version ] && { echo "%s version: %s"; echo "API version: 3.6"; }\n' "$2" "$3" > "$1/$2"
  fi
  chmod 0755 "$1/$2"
}
# tarballs falsos con la forma del oficial: etcd-vX.Y.Z-linux-amd64/{etcd,etcdctl,etcdutl,README.md,Documentation/}
hacer() { # hacer NOMBRE VERSION_DIR VERSION_BIN BINARIOS...
  local n=$1 vd=$2 vb=$3 d; shift 3
  d="$T/arma_$n/etcd-v$vd-linux-amd64"; mkdir -p "$d/Documentation"
  echo doc > "$d/README.md"; echo doc > "$d/Documentation/x.md"
  for b in "$@"; do falso "$d" "$b" "$vb"; done
  (cd "$T/arma_$n" && tar -czf "$T/$n.tgz" "etcd-v$vd-linux-amd64")
}
hacer bueno 3.6.16 3.6.16 etcd etcdctl etcdutl
hacer sin_etcdutl 3.6.16 3.6.16 etcd etcdctl
hacer otra_version 3.6.17 3.6.17 etcd etcdctl etcdutl
hacer binario_miente 3.6.16 3.6.15 etcd etcdctl etcdutl
# un tarball con un enlace donde debería estar etcd, y otro con un ../ al lado: lo que no es de los tres, no sale
mkdir -p "$T/arma_enlace/etcd-v3.6.16-linux-amd64"; falso "$T/arma_enlace/etcd-v3.6.16-linux-amd64" etcdctl 3.6.16
falso "$T/arma_enlace/etcd-v3.6.16-linux-amd64" etcdutl 3.6.16; ln -s /bin/sh "$T/arma_enlace/etcd-v3.6.16-linux-amd64/etcd"
(cd "$T/arma_enlace" && tar -czf "$T/enlace.tgz" etcd-v3.6.16-linux-amd64)
printf 'esto no es un tar.gz\n' > "$T/no_tgz.tgz"

printf 'contenido\n' > "$T/f"
SHA_F=$(openssl dgst -sha256 "$T/f" | sed 's/.* //')
printf '# comentario\n%s\n' "$SHA_F" > "$T/sha_bien"
printf '# c\n%s\n%s\n' "$SHA_F" "$SHA_F" > "$T/sha_dos"
printf '%s\n' "${SHA_F%?}" > "$T/sha_corta"
printf '%s\n' "$(printf '%s' "$SHA_F" | tr 'a-f' 'A-F')" > "$T/sha_mayus"
printf '# solo comentarios\n' > "$T/sha_vacia"

sha_igual() { [ "$(etcd_sha256 "$1")" = "$2" ]; }
sha_lee() { [ "$(etcd_sha256_de_fichero "$1")" = "$2" ]; }
url_es() { [ "$(etcd_url "$1")" = "$2" ]; }
extrae_bien() { local d="$T/x_$1"; rm -rf "$d"; etcd_extraer "$T/$1.tgz" 3.6.16 "$d" \
  && [ "$(ls -A "$d" | tr '\n' ' ')" = "etcd etcdctl etcdutl " ] && etcd_instalado_cuadra 3.6.16 "$d"; }
extrae_y_cuadra() { local d="$T/y_$1"; rm -rf "$d"; etcd_extraer "$T/$1.tgz" 3.6.16 "$d" && etcd_instalado_cuadra 3.6.16 "$d"; }
version_repo() { etcd_version_valida "$(tr -d '[:space:]' < "$src/VERSION")"; }
sha_repo_es() { [ "$(etcd_sha256_de_fichero "$src/SHA256")" = "$1" ]; }

los_casos() {
  acepta "versión 3.6.16" etcd_version_valida 3.6.16
  rechaza "versión v3.6.16 (con v)" etcd_version_valida v3.6.16
  rechaza "versión 3.6 (sin parche)" etcd_version_valida 3.6
  rechaza "versión 3.6.16-rc.0" etcd_version_valida 3.6.16-rc.0
  rechaza "versión latest (por nombre)" etcd_version_valida latest
  rechaza "versión vacía" etcd_version_valida ""
  rechaza "dos versiones en dos líneas" etcd_version_valida $'3.6.16\n3.6.17'
  acepta "URL de la release oficial" url_es 3.6.16 https://github.com/etcd-io/etcd/releases/download/v3.6.16/etcd-v3.6.16-linux-amd64.tar.gz
  acepta "SHA256 de un fichero (64 hex)" sha_igual "$T/f" "$SHA_F"
  rechaza "SHA256 de otro contenido" sha_igual "$T/sha_bien" "$SHA_F"
  acepta "fichero SHA256 con comentario" sha_lee "$T/sha_bien" "$SHA_F"
  rechaza "fichero SHA256 con dos líneas" etcd_sha256_de_fichero "$T/sha_dos"
  rechaza "fichero SHA256 corto" etcd_sha256_de_fichero "$T/sha_corta"
  rechaza "fichero SHA256 en mayúscula" etcd_sha256_de_fichero "$T/sha_mayus"
  rechaza "fichero SHA256 sin valor" etcd_sha256_de_fichero "$T/sha_vacia"
  rechaza "fichero SHA256 que no existe" etcd_sha256_de_fichero "$T/no_existe"
  acepta "línea de etcd --version (medida DAY334)" etcd_binario_cuadra 3.6.16 "etcd Version: 3.6.16"
  acepta "línea de etcdctl version (medida DAY334)" etcd_binario_cuadra 3.6.16 "etcdctl version: 3.6.16"
  acepta "línea de etcdutl version (medida DAY334)" etcd_binario_cuadra 3.6.16 "etcdutl version: 3.6.16"
  rechaza "binario de otra versión (3.6.17)" etcd_binario_cuadra 3.6.16 "etcd Version: 3.6.17"
  rechaza "binario 3.6.160 no es 3.6.16" etcd_binario_cuadra 3.6.16 "etcd Version: 3.6.160"
  rechaza "binario que no responde" etcd_binario_cuadra 3.6.16 ""
  rechaza "etcd no está (command not found)" etcd_binario_cuadra 3.6.16 "bash: etcd: command not found"
  acepta "tarball bueno: solo los tres binarios, con su versión" extrae_bien bueno
  rechaza "tarball sin etcdutl" etcd_extraer "$T/sin_etcdutl.tgz" 3.6.16 "$T/x1"
  rechaza "tarball de otra versión (otro directorio)" etcd_extraer "$T/otra_version.tgz" 3.6.16 "$T/x2"
  rechaza "tarball cuyos binarios dicen otra versión" extrae_y_cuadra binario_miente
  rechaza "tarball con un enlace en lugar de etcd" etcd_extraer "$T/enlace.tgz" 3.6.16 "$T/x3"
  rechaza "fichero que no es un tar.gz" etcd_extraer "$T/no_tgz.tgz" 3.6.16 "$T/x4"
  rechaza "binarios instalados que no están" etcd_instalado_cuadra 3.6.16 "$T/no_existe"
  acepta "provisioning/etcd/VERSION bien formado" version_repo
  acepta "provisioning/etcd/SHA256 es el del SHA256SUMS oficial (medido DAY333 y DAY334)" sha_repo_es "$SHA_DAY333"
  rechaza "provisioning/etcd/SHA256 no es el de otro fichero" sha_repo_es "$SHA_F"
}

los_casos
echo "$((casos - fallos))/$casos casos"
total=$fallos

# Contra funciones que lo aceptan todo, cada rechazo tiene que dar ❌.
etcd_version_valida() { return 0; }
etcd_sha256_de_fichero() { echo x; }
etcd_sha256() { cat "$1" >/dev/null 2>&1; echo "$SHA_F"; }
etcd_binario_cuadra() { return 0; }
etcd_extraer() { mkdir -p "$3"; return 0; }
etcd_instalado_cuadra() { return 0; }
sha_repo_es() { return 0; }
esperados=$rechazos; casos=0; fallos=0; rechazos=0; rechazos_vistos=0
los_casos > /dev/null
if [ "$rechazos_vistos" = "$esperados" ]; then
  echo "✅ contra funciones que lo aceptan todo fallan los $esperados casos de rechazo"
else
  echo "❌ contra funciones que lo aceptan todo fallan $rechazos_vistos de los $esperados casos de rechazo"; total=$((total + 1))
fi
[ "$total" = 0 ] && echo "✅ test-etcd-instalar" || { echo "❌ test-etcd-instalar: $total fallos"; exit 1; }
