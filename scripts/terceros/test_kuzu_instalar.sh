#!/usr/bin/env bash
# scripts/terceros/test_kuzu_instalar.sh — [TERCEROS-KUZU-D335] tests de las funciones kz_* de kuzu_instalar.sh y de
# provisioning/kuzu/{VERSION,SHA256} (Mac, sin VMs ni red: tarballs de juguete hechos aquí). Cada caso de rechazo se
# vuelve a correr contra funciones que lo aceptan todo, y tiene que fallar ahí: así se ve que el test distingue.
set -u
LC_ALL=C; export LC_ALL
aqui=$(dirname "$0")
src=${KUZU_SRC:-$aqui/../../provisioning/kuzu}
. "$aqui/kuzu_instalar.sh"

SHA_DAY335=e99f9671ebfacf4d6208aa4b94490016e4ac9be242deed1fea78afb31c058ebd
OTRO_SHA=0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
casos=0; fallos=0; rechazos=0; rechazos_vistos=0
acepta() { local n=$1; shift; casos=$((casos + 1)); if "$@" >/dev/null 2>&1; then echo "✅ $n"; else echo "❌ $n"; fallos=$((fallos + 1)); fi; }
rechaza() { local n=$1; shift; casos=$((casos + 1)); rechazos=$((rechazos + 1)); if "$@" >/dev/null 2>&1; then echo "❌ $n"; fallos=$((fallos + 1)); rechazos_vistos=$((rechazos_vistos + 1)); else echo "✅ $n"; fi; }

# ficheros SHA256 de juguete
printf '# comentario\n%s\n' "$SHA_DAY335" > "$T/s_bien"
printf '%s\n%s\n' "$SHA_DAY335" "$OTRO_SHA" > "$T/s_dos"
printf '%s\n' "${SHA_DAY335%?}" > "$T/s_corto"
printf '%s\n' "$(printf '%s' "$SHA_DAY335" | tr 'a-f' 'A-F')" > "$T/s_mayus"

# tarballs de juguete: los tres ficheros en la raíz, como el de la v0.11.3 (medido DAY335); sin kuzu.h; con kuzu.h como
# enlace; con un miembro de más fuera del directorio (../fuera); y algo que no es un tar.gz
mkdir -p "$T/t/bien" "$T/t/falta" "$T/t/enlace" "$T/t/mas"
for d in bien falta enlace mas; do echo so > "$T/t/$d/libkuzu.so"; echo hpp > "$T/t/$d/kuzu.hpp"; done
echo h > "$T/t/bien/kuzu.h"; echo h > "$T/t/mas/kuzu.h"; ln -s /etc/hosts "$T/t/enlace/kuzu.h"; echo fuera > "$T/t/fuera"
tar -czf "$T/bien.tgz" -C "$T/t/bien" libkuzu.so kuzu.hpp kuzu.h
tar -czf "$T/falta.tgz" -C "$T/t/falta" libkuzu.so kuzu.hpp
tar -czf "$T/enlace.tgz" -C "$T/t/enlace" libkuzu.so kuzu.hpp kuzu.h
tar -czf "$T/mas.tgz" -C "$T/t/mas" libkuzu.so kuzu.hpp kuzu.h ../fuera 2>/dev/null
echo 'no soy un tar.gz' > "$T/nada.tgz"

# instalación de juguete: lib/ e include/ con los tres ficheros, su marca buena, y variantes
mkdir -p "$T/i/lib" "$T/i/inc"
cp "$T/t/bien/libkuzu.so" "$T/i/lib/"; cp "$T/t/bien/kuzu.hpp" "$T/t/bien/kuzu.h" "$T/i/inc/"
kz_marca "$SHA_DAY335" "$T/i/lib" "$T/i/inc" > "$T/m_bien"
kz_marca "$OTRO_SHA" "$T/i/lib" "$T/i/inc" > "$T/m_otro"
printf '%s\n' "$SHA_DAY335" > "$T/m_solo_sha"

sha_lee() { [ "$(kz_sha256_de_fichero "$1")" = "$2" ]; }
extrae() { rm -rf "$T/x_$1"; kz_extraer "$2" "$T/x_$1"; }
extrae_tres() { extrae "$1" "$2" && [ -f "$T/x_$1/libkuzu.so" ] && [ -f "$T/x_$1/kuzu.hpp" ] && [ -f "$T/x_$1/kuzu.h" ]; }
# ../fuera, sacado desde x_mas/x, caería en x_mas/fuera: no tiene que existir, y en x_mas solo deben quedar los tres
nada_fuera() { [ ! -e "$T/x_mas/fuera" ] && [ "$(ls -A "$T/x_mas" | wc -l | tr -d ' ')" = 3 ]; }
url_es() { [ "$(kz_url "$1")" = "$2" ]; }
tocado() { # copia de la instalación con un fichero cambiado; estado contra la marca buena
  rm -rf "$T/c"; cp -R "$T/i" "$T/c"; printf 'x' >> "$T/c/$1"; kz_estado "$SHA_DAY335" "$T/m_bien" "$T/c/lib" "$T/c/inc"; }
falta() { rm -rf "$T/c"; cp -R "$T/i" "$T/c"; rm -f "$T/c/$1"; kz_estado "$SHA_DAY335" "$T/m_bien" "$T/c/lib" "$T/c/inc"; }
version_repo() { kz_version_valida "$(tr -d '[:space:]' < "$src/VERSION")"; }
sha_repo_es() { [ "$(kz_sha256_de_fichero "$src/SHA256")" = "$1" ]; }

los_casos() {
  acepta "versión 0.11.3" kz_version_valida 0.11.3
  rechaza "versión v0.11.3 (con v)" kz_version_valida v0.11.3
  rechaza "versión latest (por nombre)" kz_version_valida latest
  rechaza "dos versiones en dos líneas" kz_version_valida $'0.11.3\n0.11.4'
  acepta "fichero SHA256 con comentario" sha_lee "$T/s_bien" "$SHA_DAY335"
  rechaza "fichero SHA256 con dos líneas" kz_sha256_de_fichero "$T/s_dos"
  rechaza "fichero SHA256 corto" kz_sha256_de_fichero "$T/s_corto"
  rechaza "fichero SHA256 en mayúscula" kz_sha256_de_fichero "$T/s_mayus"
  rechaza "fichero SHA256 que no existe" kz_sha256_de_fichero "$T/no_existe"
  acepta "URL de la v0.11.3 (la que fijaba el Vagrantfile)" url_es 0.11.3 https://github.com/kuzudb/kuzu/releases/download/v0.11.3/libkuzu-linux-x86_64.tar.gz
  acepta "tarball con los tres ficheros: los saca" extrae_tres bien "$T/bien.tgz"
  rechaza "tarball sin kuzu.h" extrae falta "$T/falta.tgz"
  rechaza "tarball con kuzu.h como enlace" extrae enlace "$T/enlace.tgz"
  acepta "tarball con un miembro de más (../fuera): saca los tres" extrae_tres mas "$T/mas.tgz"
  acepta "tarball con un miembro de más: nada fuera del destino" nada_fuera
  rechaza "lo que no es un tar.gz" extrae nada "$T/nada.tgz"
  acepta "estado: marca con el SHA256 y los tres ficheros instalados" kz_estado "$SHA_DAY335" "$T/m_bien" "$T/i/lib" "$T/i/inc"
  rechaza "estado: la marca dice otro SHA256 del tarball" kz_estado "$SHA_DAY335" "$T/m_otro" "$T/i/lib" "$T/i/inc"
  rechaza "estado: marca solo con el SHA256 (sin los ficheros)" kz_estado "$SHA_DAY335" "$T/m_solo_sha" "$T/i/lib" "$T/i/inc"
  rechaza "estado: sin marca (el Kuzu de antes)" kz_estado "$SHA_DAY335" "$T/no_existe" "$T/i/lib" "$T/i/inc"
  rechaza "estado: libkuzu.so cambiada después de instalar" tocado lib/libkuzu.so
  rechaza "estado: kuzu.hpp cambiada después de instalar" tocado inc/kuzu.hpp
  rechaza "estado: kuzu.h cambiada después de instalar" tocado inc/kuzu.h
  rechaza "estado: falta kuzu.h" falta inc/kuzu.h
  acepta "provisioning/kuzu/VERSION bien formado" version_repo
  acepta "provisioning/kuzu/SHA256 es el digest de GitHub de la v0.11.3 (medido DAY335)" sha_repo_es "$SHA_DAY335"
  rechaza "provisioning/kuzu/SHA256 no es otro" sha_repo_es "$OTRO_SHA"
}

los_casos
echo "$((casos - fallos))/$casos casos"
total=$fallos

# Contra funciones que lo aceptan todo, cada rechazo tiene que dar ❌.
kz_version_valida() { return 0; }
kz_sha256_de_fichero() { echo x; }
kz_extraer() { mkdir -p "$2"; return 0; }
kz_estado() { return 0; }
sha_repo_es() { return 0; }
esperados=$rechazos; casos=0; fallos=0; rechazos=0; rechazos_vistos=0
los_casos > /dev/null
if [ "$rechazos_vistos" = "$esperados" ]; then
  echo "✅ contra funciones que lo aceptan todo fallan los $esperados casos de rechazo"
else
  echo "❌ contra funciones que lo aceptan todo fallan $rechazos_vistos de los $esperados casos de rechazo"; total=$((total + 1))
fi
[ "$total" = 0 ] && echo "✅ test-kuzu-instalar" || { echo "❌ test-kuzu-instalar: $total fallos"; exit 1; }
