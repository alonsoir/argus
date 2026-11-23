#!/usr/bin/env bash
# scripts/terceros/kuzu_instalar.sh — [TERCEROS-KUZU-D335] DEBT-LAB-TERCEROS-DESCARGA-SIN-VERIFICAR-001, lente Kuzu: la
# biblioteca C/C++ oficial de Kuzu (kuzudb, releases de GitHub) para Linux x86_64, comprobada con el SHA256 fijado. La
# usa el backend de grafo (IGraphSink) del pipeline y del host-engine. Se ejecuta EN el defender, como root:
# aprovisionador all-dependencies del Vagrantfile. Lee de provisioning/kuzu/:
#   VERSION  versión exacta, X.Y.Z, sin v (p. ej. 0.11.3)
#   SHA256   SHA256 del tarball (64 hex en minúscula), una línea sin comentar
# Sin defecto: mal o ausente, para (error de fabricante: el lab lo ve antes que nadie).
# Antes (hasta DAY334): URL y SHA256 escritos en el Vagrantfile, la descarga con curl y una rama PENDIENTE_PINEAR que
# instalaba sin comprobar nada. Ahora todo en provisioning/kuzu/ y la descarga con wget, como los demás de
# scripts/terceros/. Medido DAY335: el tarball trae kuzu.h, kuzu.hpp y libkuzu.so (SONAME libkuzu.so) en su raíz; se
# sacan los tres por nombre exacto (nada fuera del directorio temporal) a /usr/local/lib y /usr/local/include.
# Idempotente: si la marca /usr/local/lib/argus-kuzu.sha256 dice este SHA256 y el sha256 de los tres ficheros
# instalados, no baja nada; uno que falte o haya cambiado se reinstala. Las funciones kz_* no tocan el sistema (las
# prueba scripts/terceros/test_kuzu_instalar.sh en el Mac, sin red).
set -u
LC_ALL=C; export LC_ALL
log() { echo "[TERCEROS-KUZU] $*"; }
fallo() { echo "[TERCEROS-KUZU] FALLA: $*"; exit 1; }
KZ_LIBDIR=/usr/local/lib
KZ_INCDIR=/usr/local/include

# kz_version_valida VERSION -> rc 0 si es X.Y.Z (la cadena entera: un salto de línea dentro también es error)
kz_version_valida() {
  [[ "$1" =~ ^[0-9]{1,3}[.][0-9]{1,3}[.][0-9]{1,3}$ ]]
}

# kz_sha256_de_fichero FICHERO -> la única línea sin comentar, si son 64 hex en minúscula; rc 1 si no
kz_sha256_de_fichero() {
  local s
  s=$(grep -v '^#' "$1" 2>/dev/null | tr -d ' \t\r' | grep -v '^$')
  [ "$(printf '%s\n' "$s" | grep -c .)" = 1 ] || return 1
  printf '%s\n' "$s" | grep -Eqx '[0-9a-f]{64}' || return 1
  printf '%s\n' "$s"
}

# kz_sha256 FICHERO -> SHA256 en hex (portátil: openssl de Debian y LibreSSL del Mac); vacío si no existe
kz_sha256() { [ -f "$1" ] || return 0; openssl dgst -sha256 "$1" | sed 's/.* //'; }

# kz_url VERSION -> URL del tarball en las releases oficiales
kz_url() { printf 'https://github.com/kuzudb/kuzu/releases/download/v%s/libkuzu-linux-x86_64.tar.gz\n' "$1"; }

# kz_extraer TGZ DESTINO -> deja DESTINO/libkuzu.so, DESTINO/kuzu.hpp y DESTINO/kuzu.h; nada más del tarball y nunca
# fuera de DESTINO (se piden los tres miembros por nombre exacto). rc 1 si falta alguno, es un enlace o no es un tar.gz.
kz_extraer() {
  local f
  mkdir -p "$2/x" || return 1
  tar -xzf "$1" -C "$2/x" libkuzu.so kuzu.hpp kuzu.h 2>/dev/null || return 1
  for f in libkuzu.so kuzu.hpp kuzu.h; do
    [ -f "$2/x/$f" ] && [ ! -L "$2/x/$f" ] || return 1
    mv "$2/x/$f" "$2/$f" || return 1
  done
  rm -rf "$2/x"
}

# kz_marca SHA LIBDIR INCDIR -> la línea de la marca: "SHA <sha256 de libkuzu.so> <de kuzu.hpp> <de kuzu.h>"; rc 1 si
# falta alguno de los tres
kz_marca() {
  local so hpp h
  so=$(kz_sha256 "$2/libkuzu.so"); hpp=$(kz_sha256 "$3/kuzu.hpp"); h=$(kz_sha256 "$3/kuzu.h")
  [ -n "$so" ] && [ -n "$hpp" ] && [ -n "$h" ] || return 1
  printf '%s %s %s %s\n' "$1" "$so" "$hpp" "$h"
}

# kz_estado SHA MARCA LIBDIR INCDIR -> rc 0 si la marca dice SHA y el sha256 de los tres ficheros instalados; si no,
# rc 1 y el motivo
kz_estado() {
  local m
  m=$(kz_marca "$1" "$3" "$4") || { echo "falta libkuzu.so, kuzu.hpp o kuzu.h en $3 o $4"; return 1; }
  [ "$(cat "$2" 2>/dev/null)" = "$m" ] || { echo "la marca $2 no dice el SHA256 $1 y el de los tres ficheros instalados"; return 1; }
}

main() {
  local src=${KUZU_SRC:-/vagrant/provisioning/kuzu} v sha url tmp got r marca=/usr/local/lib/argus-kuzu.sha256
  [ "$(id -u)" = 0 ] || fallo "hay que ejecutarlo como root"
  v=$(tr -d '[:space:]' < "$src/VERSION" 2>/dev/null)
  kz_version_valida "$v" || fallo "$src/VERSION: '$v' mal formado (X.Y.Z, sin v: p. ej. 0.11.3). ERROR DE FABRICANTE: avisar a aRGus"
  sha=$(kz_sha256_de_fichero "$src/SHA256") || fallo "$src/SHA256: hace falta una línea sin comentar de 64 hexadecimales en minúscula. ERROR DE FABRICANTE: avisar a aRGus"
  log "versión $v y SHA256 ${sha:0:16}... (de $src)"
  if r=$(kz_estado "$sha" "$marca" "$KZ_LIBDIR" "$KZ_INCDIR"); then
    log "✅ Kuzu $v ya instalado (marca $marca)"; return 0
  fi
  log "hay que instalar: $r"
  command -v wget >/dev/null || { apt-get update -qq && apt-get install -y wget >/dev/null; } || fallo "no hay wget ni se pudo instalar"
  url=$(kz_url "$v")
  tmp=$(mktemp -d)
  wget -q --https-only -T 60 -t 3 -O "$tmp/kuzu.tgz" "$url" || { rm -rf "$tmp"; fallo "no se pudo bajar $url"; }
  got=$(kz_sha256 "$tmp/kuzu.tgz")
  [ "$got" = "$sha" ] || { rm -rf "$tmp"; fallo "SHA256 del tarball $got, se exige $sha ($src/SHA256): no se instala"; }
  log "tarball bajado y comprobado: $(stat -c %s "$tmp/kuzu.tgz") bytes, SHA256 igual al de $src/SHA256"
  kz_extraer "$tmp/kuzu.tgz" "$tmp/b" || { rm -rf "$tmp"; fallo "no se pudieron sacar libkuzu.so, kuzu.hpp y kuzu.h del tarball"; }
  mkdir -p "$KZ_LIBDIR" "$KZ_INCDIR"
  install -m 0755 -o root -g root "$tmp/b/libkuzu.so" "$KZ_LIBDIR/libkuzu.so" \
    && install -m 0644 -o root -g root "$tmp/b/kuzu.hpp" "$KZ_INCDIR/kuzu.hpp" \
    && install -m 0644 -o root -g root "$tmp/b/kuzu.h" "$KZ_INCDIR/kuzu.h" || { rm -rf "$tmp"; fallo "no se pudieron instalar los tres ficheros"; }
  rm -rf "$tmp"
  ldconfig
  kz_marca "$sha" "$KZ_LIBDIR" "$KZ_INCDIR" > "$marca" || fallo "tras instalar falta alguno de los tres ficheros"
  r=$(kz_estado "$sha" "$marca" "$KZ_LIBDIR" "$KZ_INCDIR") || fallo "tras instalar: $r"
  log "✅ Kuzu $v (kuzudb, SHA256 de $src/SHA256 comprobado) en $KZ_LIBDIR/libkuzu.so y $KZ_INCDIR/kuzu.{hpp,h}"
}

if [ "${BASH_SOURCE[0]}" = "$0" ]; then main "$@"; fi
