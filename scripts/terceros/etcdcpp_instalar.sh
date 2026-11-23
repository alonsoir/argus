#!/usr/bin/env bash
# scripts/terceros/etcdcpp_instalar.sh — [TERCEROS-ETCDCPP-D335] DEBT-LAB-TERCEROS-DESCARGA-SIN-VERIFICAR-001, lente
# etcd-cpp-apiv3: el cliente C++ de etcd (libetcd-cpp-api.so), compilado desde el repositorio oficial
# (github.com/etcd-cpp-apiv3/etcd-cpp-apiv3), en el tag v<VERSION> y comprobado que el tag apunta al commit fijado. Lo
# usan etcd-server y ml-detector. Se ejecuta EN el defender, como root: aprovisionador all-dependencies del Vagrantfile,
# después de instalar gRPC, protobuf y cpprest de apt. Lee de provisioning/etcd-cpp-apiv3/:
#   VERSION  versión exacta, X.Y.Z (p. ej. 0.15.3)
#   COMMIT   commit al que apunta el tag v<VERSION> (40 hex en minúscula), una línea sin comentar
# Sin defecto: mal o ausente, para (error de fabricante: el lab lo ve antes que nadie).
# Antes (hasta DAY334): git clone y git checkout v0.15.3 sin comprobar a qué commit apuntaba, solo si no había
# libetcd-cpp-api.so ni .a, y un fallo de make no paraba el aprovisionamiento.
# Medido DAY335 (CMakeLists.txt de la v0.15.3): con el build por defecto la única biblioteca real es libetcd-cpp-api.so
# (etcd-cpp-api-core es una interfaz de CMake), sin SOVERSION, en /usr/local/lib; la versión queda en
# lib/cmake/etcd-cpp-api/etcd-cpp-api-config-version.cmake (PACKAGE_VERSION).
# Idempotente: si la marca /usr/local/lib/argus-etcd-cpp-api.commit dice este commit y el sha256 de la
# libetcd-cpp-api.so instalada, y el fichero de versión de CMake dice esta versión, no baja ni compila nada. Una sin
# marca (la de antes) o cambiada después se recompila. Las funciones ec_*, y las gf_* de lib_git_fijado.sh, no tocan el
# sistema (las prueban scripts/terceros/test_etcdcpp_instalar.sh y test_lib_git_fijado.sh en el Mac, sin red).
set -u
LC_ALL=C; export LC_ALL
log() { echo "[TERCEROS-ETCDCPP] $*"; }
fallo() { echo "[TERCEROS-ETCDCPP] FALLA: $*"; exit 1; }
EC_URL=https://github.com/etcd-cpp-apiv3/etcd-cpp-apiv3.git
EC_PREFIJO=/usr/local
EC_SO=$EC_PREFIJO/lib/libetcd-cpp-api.so
EC_CFGVER=$EC_PREFIJO/lib/cmake/etcd-cpp-api/etcd-cpp-api-config-version.cmake

# gf_version_valida, gf_commit_de_fichero y gf_clonar: [TERCEROS-GIT-FIJADO-D335] en lib_git_fijado.sh, a su lado
. "$(dirname "${BASH_SOURCE[0]}")/lib_git_fijado.sh" || fallo "no se pudo cargar lib_git_fijado.sh"

# ec_version_de_cmake FICHERO -> la versión de su set(PACKAGE_VERSION "X.Y.Z"); vacío si no hay
ec_version_de_cmake() {
  sed -n 's/^set(PACKAGE_VERSION "\([^"]*\)")$/\1/p' "$1" 2>/dev/null | head -1
}

# ec_sha256 FICHERO -> el sha256 del fichero al que apunta (sigue enlaces); vacío si no existe
ec_sha256() {
  local f
  [ -e "$1" ] || return 0
  f=$(readlink -f "$1" 2>/dev/null || echo "$1")
  if command -v sha256sum >/dev/null; then sha256sum "$f" | cut -d' ' -f1; else shasum -a 256 "$f" | cut -d' ' -f1; fi
}

# ec_estado VERSION COMMIT SO CFGVER MARCA -> rc 0 si existe SO, CFGVER dice VERSION y la marca dice "COMMIT <sha256 de
# SO>"; si no, rc 1 y el motivo
ec_estado() {
  local v s
  [ -e "$3" ] || { echo "no hay $3"; return 1; }
  v=$(ec_version_de_cmake "$4")
  [ "$v" = "$1" ] || { echo "$4 dice la versión '${v}', se espera $1"; return 1; }
  s=$(ec_sha256 "$3")
  [ "$(cat "$5" 2>/dev/null)" = "$2 $s" ] || { echo "la marca $5 no dice el commit $2 y el sha256 $s de $3"; return 1; }
}

main() {
  local src=${ETCDCPP_SRC:-/vagrant/provisioning/etcd-cpp-apiv3} v c tmp r marca=/usr/local/lib/argus-etcd-cpp-api.commit
  [ "$(id -u)" = 0 ] || fallo "hay que ejecutarlo como root"
  v=$(tr -d '[:space:]' < "$src/VERSION" 2>/dev/null)
  gf_version_valida "$v" || fallo "$src/VERSION: '$v' mal formado (X.Y.Z: p. ej. 0.15.3). ERROR DE FABRICANTE: avisar a aRGus"
  c=$(gf_commit_de_fichero "$src/COMMIT") || fallo "$src/COMMIT: hace falta una línea sin comentar de 40 hexadecimales en minúscula. ERROR DE FABRICANTE: avisar a aRGus"
  log "versión $v y commit ${c:0:12}... (de $src)"
  if r=$(ec_estado "$v" "$c" "$EC_SO" "$EC_CFGVER" "$marca"); then
    log "✅ etcd-cpp-apiv3 $v ya instalada (marca $marca)"; return 0
  fi
  log "hay que instalar: $r"
  command -v git >/dev/null || apt-get install -y git >/dev/null || fallo "apt-get install git"
  tmp=$(mktemp -d)
  r=$(gf_clonar "$EC_URL" "v$v" "$tmp/etcd-cpp-apiv3" "$c") || { rm -rf "$tmp"; fallo "$r"; }
  log "tag v$v clonado de $EC_URL y comprobado: commit $c"
  cmake -S "$tmp/etcd-cpp-apiv3" -B "$tmp/build" -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=ON \
    -DCMAKE_INSTALL_PREFIX="$EC_PREFIJO" >/dev/null || { rm -rf "$tmp"; fallo "cmake de etcd-cpp-apiv3"; }
  make -C "$tmp/build" -j"$(nproc)" >/dev/null || { rm -rf "$tmp"; fallo "make de etcd-cpp-apiv3"; }
  make -C "$tmp/build" install >/dev/null || { rm -rf "$tmp"; fallo "make install de etcd-cpp-apiv3"; }
  rm -rf "$tmp"
  ldconfig
  printf '%s %s\n' "$c" "$(ec_sha256 "$EC_SO")" > "$marca"
  r=$(ec_estado "$v" "$c" "$EC_SO" "$EC_CFGVER" "$marca") || fallo "tras instalar: $r"
  log "✅ etcd-cpp-apiv3 $v (commit $c del repositorio oficial) en $EC_SO, sha256 $(ec_sha256 "$EC_SO")"
}

if [ "${BASH_SOURCE[0]}" = "$0" ]; then main "$@"; fi
