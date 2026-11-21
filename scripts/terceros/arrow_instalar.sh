#!/usr/bin/env bash
# scripts/terceros/arrow_instalar.sh — [TERCEROS-ARROW-D333] DEBT-LAB-TERCEROS-DESCARGA-SIN-VERIFICAR-001, lente Arrow:
# Apache Arrow / Parquet (libarrow-dev, libparquet-dev; zona oro, escritura Parquet) desde el repositorio apt oficial de
# Arrow, con sus claves comprobadas por huella y la versión fijada. Se ejecuta EN el defender, como root: aprovisionador
# all-dependencies del Vagrantfile. Lee de provisioning/arrow/:
#   VERSION  versión exacta de libarrow-dev y libparquet-dev, X.Y.Z-N (p. ej. 24.0.0-1). Sin defecto: mal o ausente,
#            para (error de fabricante: el lab lo ve antes que nadie). Cambiarla exige revalidación completa (regla del
#            Consejo DAY205: smoke test 12/12 en el defender contra la versión exacta).
#   CLAVE    huellas de las claves de KEYS de Apache Arrow (lib_apt_oficial.sh)
# Antes (hasta DAY332): wget -q de apache-arrow-apt-source-latest-bookworm.deb (JFrog, sin hash ni firma, "latest"),
# instalado con apt-get: ponía la lista del repositorio y el anillo de claves en que apt confiaba, sin comprobar nada.
# Ahora el anillo sale de https://downloads.apache.org/arrow/KEYS y solo se instala si sus 25 claves están en CLAVE.
# Si una VM tiene aún el paquete apache-arrow-apt-source, se purga (se van su .sources y su anillo); un .sources
# huérfano lo detecta repo_oficial y para sin tocar nada. Tras apt-get update se registra qué clave firmó el InRelease
# (medir, no fallar: el fallo ya lo da apt si la firma no es de CLAVE).
# Las funciones arrow_* no tocan el sistema (las prueba scripts/terceros/test_arrow_instalar.sh en el Mac).
set -u
LC_ALL=C; export LC_ALL
log() { echo "[TERCEROS-ARROW] $*"; }
fallo() { echo "[TERCEROS-ARROW] FALLA: $*"; exit 1; }
ARROW_PAQUETES="libarrow-dev libparquet-dev"

# arrow_version_valida VERSION -> rc 0 si es X.Y.Z-N (la cadena entera: un salto de línea dentro también es error)
arrow_version_valida() {
  [[ "$1" =~ ^[0-9]{1,3}[.][0-9]{1,3}[.][0-9]{1,3}-[0-9]{1,3}$ ]]
}

# arrow_firmante < salida de gpgv -> imprime la huella que firmó y rc 0, solo si gpgv dio "Good signature" y ningún BAD
arrow_firmante() {
  awk '
    /BAD signature/ { mal = 1 }
    /Good signature from/ { bien++ }
    / using [A-Za-z0-9]+ key / && $NF ~ /^[0-9A-F]+$/ && length($NF) == 40 { n++; f = $NF }
    END { if (mal || bien != 1 || n != 1) exit 1; print f }
  '
}

# arrow_comprobar VERSION < "paquete=versión" por línea -> rc 0 si libarrow-dev y libparquet-dev están en VERSION;
# en stdout, lo que no cuadra
arrow_comprobar() {
  awk -F= -v v="$1" -v quiero="$ARROW_PAQUETES" '
    BEGIN { n = split(quiero, q, " "); for (i = 1; i <= n; i++) falta[q[i]] = 1 }
    ($1 in falta) { if ($2 == v) delete falta[$1]; else { print $1 " está en " $2 ", se exige " v; mal = 1; delete falta[$1] } }
    END { for (p in falta) { print "falta " p; mal = 1 } exit mal }
  '
}

arrow_instalados() {
  dpkg-query -W -f='${Package}=${Version}=${Status}\n' $ARROW_PAQUETES 2>/dev/null | awk -F= '$3 ~ / installed$/ {print $1 "=" $2}'
}

main() {
  local src=${ARROW_SRC:-/vagrant/provisioning/arrow} lib v p actual lista n firma informe
  local anillo=/usr/share/keyrings/apache-arrow.gpg
  lib=$(dirname "${BASH_SOURCE[0]}")/../vigilancia/lib_apt_oficial.sh
  [ "$(id -u)" = 0 ] || fallo "hay que ejecutarlo como root"
  for f in VERSION CLAVE; do [ -r "$src/$f" ] || fallo "no leo $src/$f"; done
  v=$(tr -d '[:space:]' < "$src/VERSION")
  arrow_version_valida "$v" || fallo "$src/VERSION: '$v' mal formado (X.Y.Z-N: p. ej. 24.0.0-1). ERROR DE FABRICANTE: avisar a aRGus"
  log "versión $v (de $src/VERSION)"
  [ -r "$lib" ] || fallo "no leo $lib"
  # shellcheck source=../vigilancia/lib_apt_oficial.sh
  . "$lib"
  if dpkg-query -W -f='${Status}' apache-arrow-apt-source 2>/dev/null | grep -q ' installed$'; then
    log "purgando apache-arrow-apt-source (el .deb de JFrog de antes de [TERCEROS-ARROW-D333])"
    DEBIAN_FRONTEND=noninteractive apt-get purge -y apache-arrow-apt-source >/dev/null || fallo "apt-get purge apache-arrow-apt-source"
  fi
  repo_oficial apache-arrow https://downloads.apache.org/arrow/KEYS "$src/CLAVE" \
    https://packages.apache.org/artifactory/arrow/debian/ "bookworm main" || fallo "repositorio de Apache Arrow"
  apt-get update -qq || fallo "apt-get update"
  lista=$(ls /var/lib/apt/lists/*_artifactory_arrow_debian_dists_bookworm_InRelease 2>/dev/null)
  n=$(printf '%s\n' "$lista" | grep -c .)
  if [ "$n" = 1 ] && firma=$(gpgv --keyring "$anillo" "$lista" 2>&1 | arrow_firmante); then
    log "InRelease de bookworm firmado por $firma ($(gpg --show-keys --with-colons "$anillo" 2>/dev/null \
      | awk -F: -v f="$firma" '$1 == "fpr" && $10 == f {s = 1; next} s && $1 == "uid" {print $10; exit}'))"
  else
    log "AVISO: no se pudo medir quién firmó el InRelease de bookworm ($n ficheros: $(echo $lista))"
  fi
  for p in $ARROW_PAQUETES; do
    actual=$(arrow_instalados | awk -F= -v p="$p" '$1 == p {print $2}')
    if [ "$actual" = "$v" ]; then
      apt-mark hold "$p" >/dev/null || fallo "apt-mark hold $p"
      log "$p $v ya instalado"
    else
      log "instalando $p $v (instalado antes: ${actual:-ninguno})"
      instalar_fijado "$p" "$v" || fallo "$p $v"
    fi
  done
  informe=$(arrow_instalados | arrow_comprobar "$v") || fallo "lo instalado no cuadra con $v: $(echo $informe)"
  log "✅ Arrow/Parquet $v ($(echo $(arrow_instalados))), de provisioning/arrow/VERSION, fijados con apt-mark hold"
}

if [ "${BASH_SOURCE[0]}" = "$0" ]; then main "$@"; fi
