#!/usr/bin/env python3
# d335_kuzu_parche.py — [TERCEROS-KUZU-D335] DEBT-LAB-TERCEROS-DESCARGA-SIN-VERIFICAR-001, lente Kuzu: crea
# provisioning/kuzu/{VERSION,SHA256}, scripts/terceros/kuzu_instalar.sh y su test; el Vagrantfile llama al instalador en
# lugar del bloque con curl y PENDIENTE_PINEAR; el Makefile gana test-kuzu-instalar y su paso en el EMECAS. Va encima de
# terceros/d335-atomic-fuera (55328a2).
# Uso, desde la raíz del repo: python3 scripts/etcd_ha/d335_kuzu_parche.py
# Comprueba el sha256 de partida, que los nuevos no existan, cada ancla las veces exactas, el sha256 de llegada, y no
# escribe nada si algo falla.
import hashlib, pathlib, sys

PARTIDA = {'Vagrantfile': 'ac0869bc3e617356ac8cb8229303cb123b7c2a725160b3cf4bd1d2cda9616f6b', 'Makefile': 'ff0be8aaef26953e4f01b77da8f8d2741d46a8ab360fa8655dce279ab4b24daf'}
LLEGADA = {'Vagrantfile': '1770af4dd8044d84b282b71e0d1a8f087568a8d3db9a837fa26e522a84768556', 'Makefile': 'fa9647779498a2daecab4f8e315e4619def21aba41d18d16ab9d6ce52689e278', 'provisioning/kuzu/VERSION': '4c912d677643bad1d13bf1f9e841532150697e820444b1244f15e3f5a4a09563', 'provisioning/kuzu/SHA256': '6e91657e6e06f30dba632dedaf1c328fe950b8e3e34e823c2376c7aff61594a2', 'scripts/terceros/kuzu_instalar.sh': 'eaf33106d3ef2680b17078f22de7d733f7cd4b45d3cb9f3e06dd37df7a8c7812', 'scripts/terceros/test_kuzu_instalar.sh': '6be423e186932915db45c7d4d4e3a62a6bac13d8da5e362177889f145a5d63cf'}
NUEVOS = {
    'provisioning/kuzu/VERSION': r'''0.11.3
''',
    'provisioning/kuzu/SHA256': r'''# provisioning/kuzu/SHA256 — [TERCEROS-KUZU-D335] SHA256 del tarball oficial de la biblioteca C/C++ de Kuzu para Linux
# x86_64 en la versión de provisioning/kuzu/VERSION, el que publica el proyecto (kuzudb) en sus releases de GitHub:
#   https://github.com/kuzudb/kuzu/releases/download/v0.11.3/libkuzu-linux-x86_64.tar.gz
# Medido DAY335 por dos canales: es el digest sha256 que GitHub muestra junto al fichero en la página de la release
# v0.11.3 (visto por Alonso en el navegador) e igual al que fijaba el Vagrantfile desde DAY180, y al del tarball bajado
# ese día (8,09 MB; trae kuzu.h, kuzu.hpp y libkuzu.so). El tag v0.11.3 es ligero y apunta a 27cba5b9 (git ls-remote y
# la página de la release). Kuzu no firma sus releases; el repositorio está archivado desde el 10-oct-2025 y la v0.11.3
# es la última (DEBT-KUZU-CONTINUITY-001). Si cambia VERSION, cambia esto (medido igual).
# Una sola línea sin comentar: 64 caracteres hexadecimales en minúscula.
e99f9671ebfacf4d6208aa4b94490016e4ac9be242deed1fea78afb31c058ebd
''',
    'scripts/terceros/kuzu_instalar.sh': r'''#!/usr/bin/env bash
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
''',
    'scripts/terceros/test_kuzu_instalar.sh': r'''#!/usr/bin/env bash
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
''',
}
CAMBIOS = {
    'Vagrantfile': [('      # ── Kuzu v0.11.3 embebido (backend IGraphSink — DAY 180) ──────────────\n            # ⚠️  Upstream ARCHIVADO (10-oct-2025): v0.11.3 = release final, sin parches\n            #     futuros. Mitigado por abstracción IGraphSink. Plan B: fork\n            #     Vela-Engineering/kuzu. Ver nota BACKLOG DAY 180.\n            # C++ client = libkuzu.so + kuzu.hpp (NO hay .deb upstream). Pin URL+SHA256.\n            # DB = fichero único .kuzu desde v0.11.0 (no directorio).\n            if [ ! -f /usr/local/lib/libkuzu.so ]; then\n              echo "🗃️  Installing Kuzu v0.11.3 (embedded graph backend)..."\n              KUZU_URL="https://github.com/kuzudb/kuzu/releases/download/v0.11.3/libkuzu-linux-x86_64.tar.gz"\n              KUZU_SHA256="e99f9671ebfacf4d6208aa4b94490016e4ac9be242deed1fea78afb31c058ebd"   # ← pega aquí el sha256sum tras la 1ª descarga\n\n              cd /tmp && rm -rf kuzu-install && mkdir kuzu-install && cd kuzu-install\n              curl -fsSL "$KUZU_URL" -o libkuzu.tar.gz\n\n              GOT=$(sha256sum libkuzu.tar.gz | awk \'{print $1}\')\n              if [ "$KUZU_SHA256" = "PENDIENTE_PINEAR" ]; then\n                echo "⚠️  SHA256 sin pinear. Descargado: $GOT"\n                echo "    → Pégalo en KUZU_SHA256 y re-provisiona para fijar el pin."\n              elif [ "$GOT" != "$KUZU_SHA256" ]; then\n                echo "❌ SHA256 mismatch Kuzu: esperado $KUZU_SHA256, obtenido $GOT"; exit 1\n              else\n                echo "✅ SHA256 Kuzu verificado"\n              fi\n\n              tar xzf libkuzu.tar.gz\n              KUZU_SO=$(find . -name \'libkuzu.so*\' | head -1)\n              KUZU_HPP=$(find . -name \'kuzu.hpp\' | head -1)\n              KUZU_H=$(find . -name \'kuzu.h\' | head -1)\n              if [ -z "$KUZU_SO" ] || [ -z "$KUZU_HPP" ]; then\n                echo "❌ Artefactos Kuzu no hallados en el tarball (so/hpp)"; exit 1\n              fi\n              cp "$KUZU_SO" /usr/local/lib/libkuzu.so\n              cp "$KUZU_HPP" /usr/local/include/\n              [ -n "$KUZU_H" ] && cp "$KUZU_H" /usr/local/include/\n              ldconfig\n              cd /tmp && rm -rf kuzu-install\n              echo "✅ Kuzu instalado: $(ls -la /usr/local/lib/libkuzu.so)"\n            else\n              echo "✅ Kuzu ya instalado"\n            fi\n', '      # ── Kuzu (backend IGraphSink — DAY 180) ──────────────────────────────\n      # [TERCEROS-KUZU-D335] DEBT-LAB-TERCEROS-DESCARGA-SIN-VERIFICAR-001, lente Kuzu: libkuzu.so, kuzu.hpp y kuzu.h\n      # del tarball oficial (releases de github.com/kuzudb/kuzu) en la versión de provisioning/kuzu/VERSION, comprobado\n      # con el SHA256 de provisioning/kuzu/SHA256, contrastado DAY335 con el digest que publica GitHub\n      # (scripts/terceros/kuzu_instalar.sh). Antes: URL y SHA256 aquí, la descarga con curl y una rama PENDIENTE_PINEAR\n      # que instalaba sin comprobar nada. Upstream archivado (10-oct-2025): la v0.11.3 es la última; mitigado por\n      # IGraphSink, plan B el fork Vela-Engineering/kuzu (DEBT-KUZU-CONTINUITY-001, BACKLOG DAY 180).\n      # Si falla, para aquí.\n      bash /vagrant/scripts/terceros/kuzu_instalar.sh || { echo "❌ Kuzu"; exit 1; }\n', 1)],
    'Makefile': [('\t@$(EMECAS_PASO) test-etcdcpp-instalar -- $(MAKE) test-etcdcpp-instalar\n', '\t@$(EMECAS_PASO) test-etcdcpp-instalar -- $(MAKE) test-etcdcpp-instalar\n\t@$(EMECAS_PASO) test-kuzu-instalar -- $(MAKE) test-kuzu-instalar\n', 1), ('.PHONY: test-etcdcpp-instalar\ntest-etcdcpp-instalar:\n\t@bash scripts/terceros/test_etcdcpp_instalar.sh\n', '.PHONY: test-etcdcpp-instalar\ntest-etcdcpp-instalar:\n\t@bash scripts/terceros/test_etcdcpp_instalar.sh\n\n# [TERCEROS-KUZU-D335] test-kuzu-instalar (Mac, sin VMs ni red): las funciones de scripts/terceros/kuzu_instalar.sh\n# (VERSION, SHA256, qué se saca del tarball y qué no, la marca con el SHA256 y el de los tres ficheros instalados) y\n# provisioning/kuzu/{VERSION,SHA256}, también contra funciones que lo aceptan todo.\n.PHONY: test-kuzu-instalar\ntest-kuzu-instalar:\n\t@bash scripts/terceros/test_kuzu_instalar.sh\n', 1)],
}

def sha(b): return hashlib.sha256(b).hexdigest()

def main():
    raiz = pathlib.Path('.')
    if not (raiz / 'scripts/terceros/lib_git_fijado.sh').is_file():
        sys.exit('FALLA: falta scripts/terceros/lib_git_fijado.sh (¿rama equivocada?). Nada escrito.')
    salida = {}
    for f in NUEVOS:
        if (raiz / f).exists():
            sys.exit(f'FALLA: {f} ya existe. Nada escrito.')
        salida[f] = NUEVOS[f].encode()
    for f, esperado in PARTIDA.items():
        b = (raiz / f).read_bytes()
        if sha(b) != esperado:
            sys.exit(f'FALLA: {f} sha256 de partida {sha(b)}, se espera {esperado}. Nada escrito.')
        t = b.decode()
        for viejo, nuevo, veces in CAMBIOS[f]:
            n = t.count(viejo)
            if n != veces:
                sys.exit(f'FALLA: {f}: el ancla aparece {n} veces, se esperan {veces}:\n{viejo[:120]}\nNada escrito.')
            t = t.replace(viejo, nuevo)
        salida[f] = t.encode()
    for f, b in salida.items():
        if sha(b) != LLEGADA[f]:
            sys.exit(f'FALLA: {f} sha256 de llegada {sha(b)}, se espera {LLEGADA[f]}. Nada escrito.')
    for f, b in salida.items():
        (raiz / f).parent.mkdir(parents=True, exist_ok=True)
        (raiz / f).write_bytes(b)
        print(f'OK {f} {sha(b)}')

if __name__ == '__main__':
    main()
