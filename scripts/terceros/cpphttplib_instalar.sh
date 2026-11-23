#!/usr/bin/env bash
# scripts/terceros/cpphttplib_instalar.sh — [TERCEROS-HTTPLIB-D335] DEBT-LAB-TERCEROS-DESCARGA-SIN-VERIFICAR-001, lente
# cpp-httplib: httplib.h (biblioteca de una sola cabecera) del repositorio oficial (github.com/yhirose/cpp-httplib), en
# el tag v<VERSION> y comprobado que el tag apunta al commit fijado. La usan common, etcd-client, etcd-server,
# firewall-acl-agent y ml-detector. Se ejecuta EN el defender, como root: aprovisionador all-dependencies del
# Vagrantfile. Lee de provisioning/cpp-httplib/:
#   VERSION  versión exacta, X.Y.Z (p. ej. 0.67.0)
#   COMMIT   commit al que apunta el tag v<VERSION> (40 hex en minúscula), una línea sin comentar
# Sin defecto: mal o ausente, para (error de fabricante: el lab lo ve antes que nadie).
# Antes (hasta DAY334): git clone de la rama principal, sin tag ni commit, y solo si no había httplib.h: entraba en el
# pipeline lo que hubiera ese día. Medido DAY335: la del lab dice "0.67.0", y el tag v0.67.0 es ligero.
# Idempotente: si la marca /usr/local/lib/argus-cpp-httplib.commit dice este commit y el sha256 de la httplib.h
# instalada, y la cabecera dice esta versión, no baja nada. Una httplib.h sin marca (la de antes) o cambiada después se
# sustituye. Las funciones ch_*, y las gf_* de lib_git_fijado.sh, no tocan el sistema (las prueban
# scripts/terceros/test_cpphttplib_instalar.sh y test_lib_git_fijado.sh en el Mac, sin red).
set -u
LC_ALL=C; export LC_ALL
log() { echo "[TERCEROS-HTTPLIB] $*"; }
fallo() { echo "[TERCEROS-HTTPLIB] FALLA: $*"; exit 1; }
CH_URL=https://github.com/yhirose/cpp-httplib.git
CH_DESTINO=/usr/local/include/httplib.h

# gf_version_valida, gf_commit_de_fichero y gf_clonar: [TERCEROS-GIT-FIJADO-D335] en lib_git_fijado.sh, a su lado
. "$(dirname "${BASH_SOURCE[0]}")/lib_git_fijado.sh" || fallo "no se pudo cargar lib_git_fijado.sh"

# ch_version_de_cabecera FICHERO -> la versión de su #define CPPHTTPLIB_VERSION "X.Y.Z"; vacío si no hay
ch_version_de_cabecera() {
  sed -n 's/^#define CPPHTTPLIB_VERSION "\([^"]*\)"$/\1/p' "$1" 2>/dev/null | head -1
}

# ch_sha256 FICHERO -> su sha256 (sha256sum en Debian, shasum en el Mac); vacío si no existe
ch_sha256() {
  [ -f "$1" ] || return 0
  if command -v sha256sum >/dev/null; then sha256sum "$1" | cut -d' ' -f1; else shasum -a 256 "$1" | cut -d' ' -f1; fi
}

# ch_estado VERSION COMMIT CABECERA MARCA -> rc 0 si la cabecera dice VERSION y la marca dice "COMMIT <sha256 de la
# cabecera>"; si no, rc 1 y el motivo
ch_estado() {
  local v s
  [ -f "$3" ] || { echo "no hay $3"; return 1; }
  v=$(ch_version_de_cabecera "$3")
  [ "$v" = "$1" ] || { echo "$3 dice la versión '${v}', se espera $1"; return 1; }
  s=$(ch_sha256 "$3")
  [ "$(cat "$4" 2>/dev/null)" = "$2 $s" ] || { echo "la marca $4 no dice el commit $2 y el sha256 $s de $3"; return 1; }
}

main() {
  local src=${CPPHTTPLIB_SRC:-/vagrant/provisioning/cpp-httplib} v c tmp r marca=/usr/local/lib/argus-cpp-httplib.commit
  [ "$(id -u)" = 0 ] || fallo "hay que ejecutarlo como root"
  v=$(tr -d '[:space:]' < "$src/VERSION" 2>/dev/null)
  gf_version_valida "$v" || fallo "$src/VERSION: '$v' mal formado (X.Y.Z: p. ej. 0.67.0). ERROR DE FABRICANTE: avisar a aRGus"
  c=$(gf_commit_de_fichero "$src/COMMIT") || fallo "$src/COMMIT: hace falta una línea sin comentar de 40 hexadecimales en minúscula. ERROR DE FABRICANTE: avisar a aRGus"
  log "versión $v y commit ${c:0:12}... (de $src)"
  if r=$(ch_estado "$v" "$c" "$CH_DESTINO" "$marca"); then
    log "✅ cpp-httplib $v ya instalada (marca $marca)"; return 0
  fi
  log "hay que instalar: $r"
  command -v git >/dev/null || apt-get install -y git >/dev/null || fallo "apt-get install git"
  tmp=$(mktemp -d)
  r=$(gf_clonar "$CH_URL" "v$v" "$tmp/cpp-httplib" "$c") || { rm -rf "$tmp"; fallo "$r"; }
  log "tag v$v clonado de $CH_URL y comprobado: commit $c"
  r=$(ch_version_de_cabecera "$tmp/cpp-httplib/httplib.h")
  [ "$r" = "$v" ] || { rm -rf "$tmp"; fallo "la httplib.h del tag v$v dice la versión '${r}'"; }
  mkdir -p "$(dirname "$CH_DESTINO")" "$(dirname "$marca")"
  install -m 0644 "$tmp/cpp-httplib/httplib.h" "$CH_DESTINO" || { rm -rf "$tmp"; fallo "no se pudo copiar a $CH_DESTINO"; }
  rm -rf "$tmp"
  printf '%s %s\n' "$c" "$(ch_sha256 "$CH_DESTINO")" > "$marca"
  r=$(ch_estado "$v" "$c" "$CH_DESTINO" "$marca") || fallo "tras instalar: $r"
  log "✅ cpp-httplib $v (commit $c del repositorio oficial) en $CH_DESTINO, sha256 $(ch_sha256 "$CH_DESTINO")"
}

if [ "${BASH_SOURCE[0]}" = "$0" ]; then main "$@"; fi
