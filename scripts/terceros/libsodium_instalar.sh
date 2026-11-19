#!/usr/bin/env bash
# scripts/terceros/libsodium_instalar.sh — [TERCEROS-SODIUM-D331] DEBT-LAB-TERCEROS-DESCARGA-SIN-VERIFICAR-001:
# libsodium compilada desde el tarball oficial de https://download.libsodium.org/libsodium/releases/, comprobado con la
# firma minisign del mantenedor Y con el SHA256 fijado (decisión de Alonso DAY331: las dos). Se ejecuta EN el defender,
# como root. Lee de provisioning/libsodium/:
#   VERSION         versión exacta, X.Y.Z (p. ej. 1.0.19)
#   MINISIGN_PUBKEY clave Ed25519 de minisign del mantenedor (RW + 54 base64), una línea sin comentar
#   SHA256          SHA256 del tarball (64 hex en minúscula), una línea sin comentar
# Sin defecto: mal o ausente, para (error de fabricante: el lab lo ve antes que nadie).
# Por qué (medido DAY331): el Vagrantfile la bajaba con curl de GitHub sin comprobar nada y corría ANTES que
# tools/provision.sh, que sí comprobaba un SHA256 pero se saltaba la instalación al ver la 1.0.19 ya puesta.
# Bookworm trae la 1.0.18 (libsodium.so.23) y no se puede quitar: la piden libzmq5, libzmq3-dev y vim. crypto-transport
# necesita la 1.0.19 (HKDF, ADR-013). Para que un proceso no cargue las dos, /usr/local/lib/libsodium.so.23 apunta a la
# 1.0.19 (FIX DAY107, antes en tools/provision.sh); este script lo crea, como hacía provision.sh.
# Además de la firma, el comentario de confianza de la firma tiene que nombrar libsodium-<VERSION>.tar.gz: así un
# tarball firmado de otra versión, renombrado, no pasa.
# Dónde (medido DAY331): libsodium pasa las versiones antiguas a releases/old/ (la 1.0.18 ya solo está allí); se prueba
# releases/ y, si no tiene el tarball y su firma, releases/old/. Lo que se baje pasa igual por firma, nombre y SHA256.
# Idempotente: si la marca /usr/local/lib/argus-libsodium.verificado dice esta versión y este SHA256, pkg-config da la
# versión y está la cabecera de HKDF, no baja ni compila nada. Las funciones ls_* no tocan el sistema (las prueba
# scripts/terceros/test_libsodium_instalar.sh: en el Mac las puras; con --vm, en el defender, la firma real).
set -u
LC_ALL=C; export LC_ALL
log() { echo "[TERCEROS-SODIUM] $*"; }
fallo() { echo "[TERCEROS-SODIUM] FALLA: $*"; exit 1; }

ls_version_valida() { printf '%s\n' "$1" | grep -Eqx '[0-9]{1,3}[.][0-9]{1,3}[.][0-9]{1,3}'; }

# ls_linea_unica FICHERO REGEX -> la única línea sin comentar (sin blancos), si casa entera con REGEX; rc 1 si no
ls_linea_unica() {
  local s
  s=$(grep -v '^#' "$1" 2>/dev/null | tr -d ' \t\r' | grep -v '^$')
  [ "$(printf '%s\n' "$s" | grep -c .)" = 1 ] || return 1
  printf '%s\n' "$s" | grep -Eqx "$2" || return 1
  printf '%s\n' "$s"
}
ls_clave_de_fichero() { ls_linea_unica "$1" 'RW[A-Za-z0-9+/]{54}'; }
ls_sha256_de_fichero() { ls_linea_unica "$1" '[0-9a-f]{64}'; }

# ls_sha256 FICHERO -> SHA256 en hex (portátil: openssl de Debian y LibreSSL del Mac)
ls_sha256() { openssl dgst -sha256 "$1" | awk '{print $NF}'; }

# ls_comentario_ok MINISIG NOMBRE -> rc 0 si el comentario de confianza tiene exactamente el campo file:NOMBRE
ls_comentario_ok() {
  local c
  c=$(grep '^trusted comment: ' "$1" 2>/dev/null)
  [ "$(printf '%s\n' "$c" | grep -c .)" = 1 ] || return 1
  printf '%s\n' "$c" | tr '\t' '\n' | grep -qxF "file:$2"
}

# ls_bases -> las carpetas donde libsodium publica sus versiones, en el orden en que se prueban
ls_bases() {
  printf '%s\n' https://download.libsodium.org/libsodium/releases https://download.libsodium.org/libsodium/releases/old
}

# ls_bajar NOMBRE DIR -> baja NOMBRE y NOMBRE.minisig a DIR desde la primera carpeta de ls_bases que tenga los dos y
# escribe la URL usada; rc 1 si ninguna los tiene. No comprueba nada: eso es ls_verificar.
ls_bajar() {
  local b
  for b in $(ls_bases); do
    if wget -q --https-only -T 60 -t 3 -O "$2/$1" "$b/$1" \
       && wget -q --https-only -T 60 -t 3 -O "$2/$1.minisig" "$b/$1.minisig"; then
      printf '%s\n' "$b/$1"; return 0
    fi
  done
  rm -f "$2/$1" "$2/$1.minisig"; return 1
}

# ls_verificar TARBALL MINISIG CLAVE NOMBRE SHA256 -> rc 0 si la firma es válida con CLAVE, el comentario de confianza
# nombra NOMBRE y el SHA256 coincide; si no, rc 1 y el motivo por la salida
ls_verificar() {
  local got
  minisign -V -m "$1" -x "$2" -P "$3" >/dev/null 2>&1 || { echo "firma minisign inválida con la clave $3"; return 1; }
  ls_comentario_ok "$2" "$4" || { echo "el comentario de confianza de la firma no nombra $4"; return 1; }
  got=$(ls_sha256 "$1")
  [ "$got" = "$5" ] || { echo "SHA256 $got, se exige $5"; return 1; }
}

main() {
  local src=${SODIUM_SRC:-/vagrant/provisioning/libsodium} v k sha nombre url tmp r d so zmq
  local marca=/usr/local/lib/argus-libsodium.verificado hkdf=/usr/local/include/sodium/crypto_kdf_hkdf_sha256.h
  [ "$(id -u)" = 0 ] || fallo "hay que ejecutarlo como root"
  v=$(tr -d '[:space:]' < "$src/VERSION" 2>/dev/null)
  ls_version_valida "$v" || fallo "$src/VERSION: '$v' mal formado (X.Y.Z). ERROR DE FABRICANTE: avisar a aRGus"
  k=$(ls_clave_de_fichero "$src/MINISIGN_PUBKEY") || fallo "$src/MINISIGN_PUBKEY: hace falta una línea sin comentar, RW + 54 base64. ERROR DE FABRICANTE: avisar a aRGus"
  sha=$(ls_sha256_de_fichero "$src/SHA256") || fallo "$src/SHA256: hace falta una línea sin comentar de 64 hex en minúscula. ERROR DE FABRICANTE: avisar a aRGus"
  nombre="libsodium-$v.tar.gz"
  log "versión $v, clave minisign $k, SHA256 ${sha:0:16}... (de $src)"
  if [ "$(cat "$marca" 2>/dev/null)" = "$v $sha" ] && [ "$(pkg-config --modversion libsodium 2>/dev/null)" = "$v" ] \
     && grep -q crypto_kdf_hkdf_sha256_extract "$hkdf" 2>/dev/null; then
    log "ya instalada y comprobada (marca $marca)"
  else
    if ! command -v minisign >/dev/null 2>&1; then
      DEBIAN_FRONTEND=noninteractive apt-get install -y -q minisign >/dev/null 2>&1 \
        || fallo "no se pudo instalar minisign (paquete de Debian)"
    fi
    tmp=$(mktemp -d)
    url=$(ls_bajar "$nombre" "$tmp") \
      || { rm -rf "$tmp"; fallo "no se pudo bajar $nombre y su firma de ninguna de: $(ls_bases | tr '\n' ' ')"; }
    r=$(ls_verificar "$tmp/$nombre" "$tmp/$nombre.minisig" "$k" "$nombre" "$sha") || { rm -rf "$tmp"; fallo "$r: no se instala"; }
    log "tarball bajado de $url y comprobado: $(stat -c %s "$tmp/$nombre") bytes, firma minisign válida, comentario de confianza file:$nombre, SHA256 igual al de $src/SHA256"
    d=$(tar tzf "$tmp/$nombre" | head -1 | cut -d/ -f1)
    [ -n "$d" ] && tar xzf "$tmp/$nombre" -C "$tmp" || { rm -rf "$tmp"; fallo "no se pudo desempaquetar $nombre"; }
    ( cd "$tmp/$d" && ./configure --prefix=/usr/local --quiet && make -j"$(nproc)" --quiet && make install --quiet ) \
      > "$tmp/compilacion.log" 2>&1 || { tail -20 "$tmp/compilacion.log"; rm -rf "$tmp"; fallo "la compilación de $nombre falló"; }
    rm -rf "$tmp"
    log "compilada e instalada en /usr/local"
  fi
  # FIX DAY107: una sola libsodium por proceso (ver cabecera)
  so=$(readelf -d /usr/local/lib/libsodium.so 2>/dev/null | sed -n 's/.*SONAME.*\[\(.*\)\].*/\1/p')
  [ -n "$so" ] && [ -e "/usr/local/lib/$so" ] || fallo "no hay /usr/local/lib/libsodium.so con SONAME"
  [ "$so" = libsodium.so.23 ] || ln -sfn "/usr/local/lib/$so" /usr/local/lib/libsodium.so.23
  ldconfig
  [ "$(pkg-config --modversion libsodium 2>/dev/null)" = "$v" ] || fallo "pkg-config da '$(pkg-config --modversion libsodium 2>/dev/null)', se espera $v"
  grep -q crypto_kdf_hkdf_sha256_extract "$hkdf" 2>/dev/null || fallo "falta la cabecera de HKDF ($hkdf)"
  ldconfig -p | grep -qF "$so (" || fallo "ldconfig no ve $so"
  log "enlace /usr/local/lib/libsodium.so.23 -> $so (FIX DAY107)"
  printf '%s\n' "$v $sha" > "$marca"
  log "✅ libsodium $v (download.libsodium.org, firma minisign y SHA256 comprobados) en /usr/local; marca $marca"
}

if [ "${BASH_SOURCE[0]}" = "$0" ]; then main "$@"; fi
