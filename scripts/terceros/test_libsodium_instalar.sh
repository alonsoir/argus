#!/usr/bin/env bash
# scripts/terceros/test_libsodium_instalar.sh — [TERCEROS-SODIUM-D331] prueba las funciones ls_* de
# scripts/terceros/libsodium_instalar.sh, que tienen que FALLAR cuando deben.
#   sin argumentos: las funciones puras (en el Mac o en cualquier sitio; no baja nada ni toca el sistema)
#   --vm:           además, la descarga y la verificación de verdad con minisign y los tarballs oficiales (en el
#                   defender; baja libsodium-<VERSION> de releases/ y libsodium-1.0.18 de releases/old/, con su firma, a
#                   un directorio temporal y lo borra)
# Sale con rc 0 solo si pasan todos; sin minisign o sin red en --vm, falla (no se salta nada).
set -u
LC_ALL=C; export LC_ALL
aqui=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=libsodium_instalar.sh
. "$aqui/libsodium_instalar.sh"
src=${SODIUM_SRC:-$aqui/../../provisioning/libsodium}
ok=0; mal=0
si()  { if "$@" >/dev/null 2>&1; then ok=$((ok+1)); else mal=$((mal+1)); echo "FALLO (debía pasar): $*"; fi; }
no()  { if "$@" >/dev/null 2>&1; then mal=$((mal+1)); echo "FALLO (debía fallar): $*"; else ok=$((ok+1)); fi; }
t=$(mktemp -d); trap 'rm -rf "$t"' EXIT

# 1. versión
si ls_version_valida 1.0.19; no ls_version_valida 1.0; no ls_version_valida 1.0.19a; no ls_version_valida ""
no ls_version_valida "1.0.19 1.0.20"

# 2. clave y SHA256 de los ficheros del repo, y ficheros mal formados
si ls_clave_de_fichero "$src/MINISIGN_PUBKEY"; si ls_sha256_de_fichero "$src/SHA256"
si ls_version_valida "$(tr -d '[:space:]' < "$src/VERSION")"
k=RWQf6LRCGA9i53mlYecO4IzT51TGPpvWucNSCh1CBM0QTaLn73Y7GFO3
printf '# c\n%s\n' "$k" > "$t/k1"; si ls_clave_de_fichero "$t/k1"
[ "$(ls_clave_de_fichero "$t/k1")" = "$k" ] && ok=$((ok+1)) || { mal=$((mal+1)); echo "FALLO: la clave leída no es la escrita"; }
printf '%s\n%s\n' "$k" "$k" > "$t/k2"; no ls_clave_de_fichero "$t/k2"
printf '%s\n' "${k%?}" > "$t/k3"; no ls_clave_de_fichero "$t/k3"
printf '%s\n' "XX${k#RW}" > "$t/k4"; no ls_clave_de_fichero "$t/k4"
printf '# solo comentario\n' > "$t/k5"; no ls_clave_de_fichero "$t/k5"; no ls_clave_de_fichero "$t/no_existe"
h=018d79fe0a045cca07331d37bd0cb57b2e838c51bc48fd837a1472e50068bbea
printf '%s\n' "$h" | tr a-f A-F > "$t/s1"; no ls_sha256_de_fichero "$t/s1"
printf '%s\n' "${h%?}" > "$t/s2"; no ls_sha256_de_fichero "$t/s2"

# 3. sha256 portátil
printf 'abc' > "$t/abc"
[ "$(ls_sha256 "$t/abc")" = ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad ] \
  && ok=$((ok+1)) || { mal=$((mal+1)); echo "FALLO: ls_sha256 de 'abc'"; }

# 3b. carpetas de descarga, en orden
[ "$(ls_bases | grep -c .)" = 2 ] && [ "$(ls_bases | sed -n 1p)" = https://download.libsodium.org/libsodium/releases ] \
  && [ "$(ls_bases | sed -n 2p)" = https://download.libsodium.org/libsodium/releases/old ] \
  && ok=$((ok+1)) || { mal=$((mal+1)); echo "FALLO: ls_bases"; }

# 4. comentario de confianza
n=libsodium-1.0.19.tar.gz
firma() { printf 'untrusted comment: x\nRUQf\ntrusted comment: timestamp:1694614745\t%s\thashed\nzz\n' "$1" > "$2"; }
firma "file:$n" "$t/m1"; si ls_comentario_ok "$t/m1" "$n"
firma "file:libsodium-1.0.18.tar.gz" "$t/m2"; no ls_comentario_ok "$t/m2" "$n"
firma "file:$n.bak" "$t/m3"; no ls_comentario_ok "$t/m3" "$n"
firma "file:libsodium-1a0a19.tar.gz" "$t/m4"; no ls_comentario_ok "$t/m4" "$n"
printf 'untrusted comment: file:%s\nRUQf\nzz\n' "$n" > "$t/m5"; no ls_comentario_ok "$t/m5" "$n"
{ cat "$t/m1"; cat "$t/m1"; } > "$t/m6"; no ls_comentario_ok "$t/m6" "$n"

# 5. con --vm: firma real
if [ "${1:-}" = --vm ]; then
  v=$(tr -d '[:space:]' < "$src/VERSION"); n="libsodium-$v.tar.gz"; base=https://download.libsodium.org/libsodium/releases
  k=$(ls_clave_de_fichero "$src/MINISIGN_PUBKEY"); h=$(ls_sha256_de_fichero "$src/SHA256")
  if ! command -v minisign >/dev/null 2>&1; then mal=$((mal+1)); echo "FALLO: --vm sin minisign"
  elif ! u19=$(ls_bajar "$n" "$t") || ! u18=$(ls_bajar libsodium-1.0.18.tar.gz "$t"); then
    mal=$((mal+1)); echo "FALLO: --vm no pudo bajar $n o libsodium-1.0.18.tar.gz con su firma"
  else
    [ "$u19" = "$base/$n" ] && ok=$((ok+1)) || { mal=$((mal+1)); echo "FALLO: $n debía venir de $base, vino de $u19"; }
    [ "$u18" = "$base/old/libsodium-1.0.18.tar.gz" ] && ok=$((ok+1)) \
      || { mal=$((mal+1)); echo "FALLO: la 1.0.18 debía venir de $base/old, vino de $u18"; }
    no ls_bajar libsodium-0.0.0.tar.gz "$t"
    si ls_verificar "$t/$n" "$t/$n.minisig" "$k" "$n" "$h"
    cp "$t/$n" "$t/alterado"; printf 'X' | dd of="$t/alterado" bs=1 seek=1000 conv=notrunc 2>/dev/null
    no ls_verificar "$t/alterado" "$t/$n.minisig" "$k" "$n" "$(ls_sha256 "$t/alterado")"
    no ls_verificar "$t/$n" "$t/$n.minisig" "RW$(printf '%054d' 0 | tr 0 A)" "$n" "$h"
    no ls_verificar "$t/$n" "$t/libsodium-1.0.18.tar.gz.minisig" "$k" "$n" "$h"
    no ls_verificar "$t/$n" "$t/$n.minisig" "$k" "$n" "$(printf '%064d' 0)"
    # la 1.0.18 firmada de verdad, presentada como la 1.0.19 y con su propio SHA256: solo la para el comentario
    si minisign -V -m "$t/libsodium-1.0.18.tar.gz" -x "$t/libsodium-1.0.18.tar.gz.minisig" -P "$k"
    no ls_verificar "$t/libsodium-1.0.18.tar.gz" "$t/libsodium-1.0.18.tar.gz.minisig" "$k" "$n" \
       "$(ls_sha256 "$t/libsodium-1.0.18.tar.gz")"
  fi
fi

echo "[TEST-TERCEROS-SODIUM] ${1:-puras}: $ok bien, $mal mal"
[ "$mal" = 0 ]
