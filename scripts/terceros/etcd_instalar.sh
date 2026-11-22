#!/usr/bin/env bash
# scripts/terceros/etcd_instalar.sh — [TERCEROS-ETCD-D334] DEBT-LAB-TERCEROS-DESCARGA-SIN-VERIFICAR-001, lente etcd: el
# binario oficial de etcd (etcd-io, releases de GitHub) para Linux amd64, comprobado con el SHA256 que publica el
# proyecto en el SHA256SUMS de la release. Se ejecuta EN cada nodo del plano de control (control-1/2/3), como root:
# aprovisionador etcd-install del Vagrantfile ([ETCD-CLUSTER-D324]). Lee de provisioning/etcd/:
#   VERSION  versión exacta, X.Y.Z, sin v (p. ej. 3.6.16)
#   SHA256   SHA256 del tarball (64 hex en minúscula), una línea sin comentar
# Sin defecto: mal o ausente, para (error de fabricante: el lab lo ve antes que nadie).
# Antes (hasta DAY333): versión y sha256 escritos en el heredoc ETCD_INSTALL del Vagrantfile y la descarga con curl.
# Ahora todo en provisioning/etcd/ y la descarga con wget, como los demás de scripts/terceros/ (ONNX Runtime,
# libsodium). etcd no publica firma de sus binarios (medido DAY333): manda el SHA256.
# Del tarball solo se sacan etcd, etcdctl y etcdutl (por nombre exacto: nada fuera del directorio temporal), a
# /usr/local/bin. La configuración, la unidad, el arranque del clúster y el RBAC no son de aquí: make etcd-cluster-deploy.
# Idempotente: si la marca /usr/local/lib/argus-etcd.sha256 dice este SHA256 y los tres binarios dicen esta versión, no
# baja nada. Las funciones etcd_* no tocan el sistema (las prueba scripts/terceros/test_etcd_instalar.sh en el Mac).
set -u
LC_ALL=C; export LC_ALL
log() { echo "[TERCEROS-ETCD] $*"; }
fallo() { echo "[TERCEROS-ETCD] FALLA: $*"; exit 1; }

# etcd_version_valida VERSION -> rc 0 si es X.Y.Z (la cadena entera: un salto de línea dentro también es error)
etcd_version_valida() {
  [[ "$1" =~ ^[0-9]{1,3}[.][0-9]{1,3}[.][0-9]{1,3}$ ]]
}

# etcd_sha256_de_fichero FICHERO -> la única línea sin comentar, si son 64 hex en minúscula; rc 1 si no
etcd_sha256_de_fichero() {
  local s
  s=$(grep -v '^#' "$1" 2>/dev/null | tr -d ' \t\r' | grep -v '^$')
  [ "$(printf '%s\n' "$s" | grep -c .)" = 1 ] || return 1
  printf '%s\n' "$s" | grep -Eqx '[0-9a-f]{64}' || return 1
  printf '%s\n' "$s"
}

# etcd_sha256 FICHERO -> SHA256 en hex (portátil: openssl de Debian y LibreSSL del Mac)
etcd_sha256() { openssl dgst -sha256 "$1" | sed 's/.* //'; }

# etcd_nombre VERSION -> nombre del tarball y del directorio de dentro, sin .tar.gz
etcd_nombre() { printf 'etcd-v%s-linux-amd64\n' "$1"; }

# etcd_url VERSION -> URL del tarball en las releases oficiales
etcd_url() { printf 'https://github.com/etcd-io/etcd/releases/download/v%s/%s.tar.gz\n' "$1" "$(etcd_nombre "$1")"; }

# etcd_binario_cuadra VERSION LINEA -> rc 0 si LINEA (la primera de `etcd --version`, `etcdctl version` o
# `etcdutl version`) es exactamente "<etcd|etcdctl|etcdutl> version: VERSION" (mayúsculas o minúsculas en Version)
etcd_binario_cuadra() {
  case "$2" in
    "etcd Version: $1"|"etcdctl version: $1"|"etcdutl version: $1") return 0 ;;
  esac
  return 1
}

# etcd_extraer TGZ VERSION DESTINO -> deja DESTINO/etcd, DESTINO/etcdctl y DESTINO/etcdutl; nada más del tarball y
# nunca fuera de DESTINO (se piden los tres miembros por nombre exacto). rc 1 si falta alguno o no es un tar.gz.
etcd_extraer() {
  local n b
  n=$(etcd_nombre "$2")
  mkdir -p "$3/x" || return 1
  tar -xzf "$1" -C "$3/x" "$n/etcd" "$n/etcdctl" "$n/etcdutl" 2>/dev/null || return 1
  for b in etcd etcdctl etcdutl; do
    [ -f "$3/x/$n/$b" ] && [ ! -L "$3/x/$n/$b" ] || return 1
    mv "$3/x/$n/$b" "$3/$b" || return 1
  done
  rm -rf "$3/x"
}

# etcd_instalado_cuadra VERSION DIR -> rc 0 si DIR/etcd, DIR/etcdctl y DIR/etcdutl dicen esa versión
etcd_instalado_cuadra() {
  [ -x "$2/etcd" ] && [ -x "$2/etcdctl" ] && [ -x "$2/etcdutl" ] || return 1
  etcd_binario_cuadra "$1" "$("$2/etcd" --version 2>&1 | head -1)" \
    && etcd_binario_cuadra "$1" "$("$2/etcdctl" version 2>&1 | head -1)" \
    && etcd_binario_cuadra "$1" "$("$2/etcdutl" version 2>&1 | head -1)"
}

main() {
  local src=${ETCD_SRC:-/vagrant/provisioning/etcd} v sha url tmp got b marca=/usr/local/lib/argus-etcd.sha256
  [ "$(id -u)" = 0 ] || fallo "hay que ejecutarlo como root"
  v=$(tr -d '[:space:]' < "$src/VERSION" 2>/dev/null)
  etcd_version_valida "$v" || fallo "$src/VERSION: '$v' mal formado (X.Y.Z, sin v: p. ej. 3.6.16). ERROR DE FABRICANTE: avisar a aRGus"
  sha=$(etcd_sha256_de_fichero "$src/SHA256") || fallo "$src/SHA256: hace falta una línea sin comentar de 64 hexadecimales en minúscula. ERROR DE FABRICANTE: avisar a aRGus"
  log "versión $v y SHA256 ${sha:0:16}... (de $src)"
  if [ "$(cat "$marca" 2>/dev/null)" = "$sha" ] && etcd_instalado_cuadra "$v" /usr/local/bin; then
    log "✅ etcd $v ya instalado (marca $marca)"; return 0
  fi
  command -v wget >/dev/null || { apt-get update -qq && apt-get install -y wget >/dev/null; } || fallo "no hay wget ni se pudo instalar"
  url=$(etcd_url "$v")
  tmp=$(mktemp -d)
  wget -q --https-only -T 60 -t 3 -O "$tmp/etcd.tgz" "$url" || { rm -rf "$tmp"; fallo "no se pudo bajar $url"; }
  got=$(etcd_sha256 "$tmp/etcd.tgz")
  [ "$got" = "$sha" ] || { rm -rf "$tmp"; fallo "SHA256 del tarball $got, se exige $sha ($src/SHA256): no se instala"; }
  log "tarball bajado y comprobado: $(stat -c %s "$tmp/etcd.tgz") bytes, SHA256 igual al de $src/SHA256"
  etcd_extraer "$tmp/etcd.tgz" "$v" "$tmp/b" || { rm -rf "$tmp"; fallo "no se pudieron sacar etcd, etcdctl y etcdutl del tarball"; }
  chmod 0755 "$tmp/b/etcd" "$tmp/b/etcdctl" "$tmp/b/etcdutl"
  etcd_instalado_cuadra "$v" "$tmp/b" || { rm -rf "$tmp"; fallo "los binarios del tarball no dicen la versión $v"; }
  for b in etcd etcdctl etcdutl; do install -m 0755 -o root -g root "$tmp/b/$b" "/usr/local/bin/$b"; done
  rm -rf "$tmp"
  printf '%s\n' "$sha" > "$marca"
  etcd_instalado_cuadra "$v" /usr/local/bin || fallo "tras instalar, /usr/local/bin no dice la versión $v"
  log "✅ $(/usr/local/bin/etcd --version | head -1) (etcd-io, SHA256 de $src/SHA256 comprobado) en /usr/local/bin"
}

if [ "${BASH_SOURCE[0]}" = "$0" ]; then main "$@"; fi
