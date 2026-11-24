#!/usr/bin/env bash
# scripts/vigilancia/zeek_instalar.sh — [TERCEROS-ZEEK-D330] DEBT-LAB-VERSIONES-TERCEROS-001, lente Zeek: Zeek desde el
# repositorio de OBS (el de los binarios de Zeek), con su clave comprobada por huella y la SERIE fijada.
# Se ejecuta EN la VM zeek, como root: aprovisionador install-zeek del Vagrantfile. Lee de provisioning/zeek/:
#   VERSION  la serie de Zeek, M.m (p. ej. 9.0). Formato exacto: dígitos, punto, dígitos. Sin defecto: mal o ausente,
#            para (es un error de fabricante: el lab lo ve antes que nadie).
#   CLAVE    huella de la clave de firma de OBS (lib_apt_oficial.sh)
# Por qué la serie y no la versión exacta (medido DAY330): OBS solo guarda la última versión de cada paquete
# (apt-cache madison da una), así que fijar zeek=9.0.1-0 rompería el lab el día que publiquen la 9.0.2. Se instala el
# paquete de la serie, zeek-M.m (sus dependencias van con "=" a su misma versión), se comprueba que todo lo de Zeek
# instalado es de esa serie y de esa versión, que el binario dice esa versión, y se fija todo con apt-mark hold. Un
# cambio de serie solo entra con un commit en VERSION. Los paquetes de serie y los sin serie (zeek, zeek-core...) NO se
# declaran en conflicto pero comparten /opt/zeek (medido DAY330): si ya hay de Zeek fuera de la serie, para sin tocar nada.
# Las funciones zeek_* no tocan el sistema (las prueba scripts/vigilancia/test_zeek_instalar.sh en el Mac).
set -u
LC_ALL=C; export LC_ALL
log() { echo "[TERCEROS-ZEEK] $*"; }
fallo() { echo "[TERCEROS-ZEEK] FALLA: $*"; exit 1; }

# zeek_serie_valida SERIE -> rc 0 si es M.m
zeek_serie_valida() {
  printf '%s\n' "$1" | grep -Eqx '[0-9]{1,3}[.][0-9]{1,3}'
}

# zeek_en_serie SERIE PAQUETE -> rc 0 si el paquete es de la serie (zeek-S, zeek-S-*, zeekctl-S, zeekctl-S-*)
zeek_en_serie() {
  case "$2" in
    "zeek-$1"|"zeek-$1-"*|"zeekctl-$1"|"zeekctl-$1-"*) return 0 ;;
  esac
  return 1
}

# zeek_fuera_de_serie SERIE < paquetes (uno por línea) -> imprime los que no son de la serie
zeek_fuera_de_serie() {
  local p
  while IFS= read -r p; do
    [ -n "$p" ] || continue
    zeek_en_serie "$1" "$p" || printf '%s\n' "$p"
  done
  return 0
}

# zeek_comprobar SERIE VERSION_DEL_PAQUETE_DE_SERIE SALIDA_DE_zeek_--version < "paquete=versión" (uno por línea)
#   -> rc 0 si: la versión es de la serie; están zeek-S y zeek-S-core; todo es de la serie y de esa versión; y el binario
#      dice esa versión (sin la revisión de Debian). Si no, una línea por fallo y rc 1.
zeek_comprobar() {
  local s=$1 v=$2 bin=$3 linea p pv mal=0 meta=0 core=0
  case "$v" in
    "$s".*) ;;
    *) echo "zeek-$s en '$v', fuera de la serie $s"; mal=1 ;;
  esac
  while IFS= read -r linea; do
    [ -n "$linea" ] || continue
    p=${linea%%=*}; pv=${linea#*=}
    [ "$p" = "zeek-$s" ] && meta=1
    [ "$p" = "zeek-$s-core" ] && core=1
    if ! zeek_en_serie "$s" "$p"; then echo "$p ($pv) no es de la serie $s"; mal=1
    elif [ "$pv" != "$v" ]; then echo "$p en $pv, no en $v (la de zeek-$s)"; mal=1
    fi
  done
  [ "$meta" = 1 ] || { echo "falta zeek-$s"; mal=1; }
  [ "$core" = 1 ] || { echo "falta zeek-$s-core"; mal=1; }
  [ "$bin" = "/opt/zeek/bin/zeek version ${v%-*}" ] || { echo "el binario dice '$bin', se espera la versión ${v%-*}"; mal=1; }
  return "$mal"
}

zeek_instalados() {
  dpkg-query -W -f='${Package}=${Version}=${Status}\n' 'zeek*' 2>/dev/null | awk -F= '$3 ~ / installed$/ {print $1 "=" $2}'
}

main() {
  local src=${ZEEK_SRC:-/vagrant/provisioning/zeek} lib s fuera actuales v bin informe
  lib=$(dirname "${BASH_SOURCE[0]}")/lib_apt_oficial.sh
  [ "$(id -u)" = 0 ] || fallo "hay que ejecutarlo como root"
  for f in VERSION CLAVE; do [ -r "$src/$f" ] || fallo "no leo $src/$f"; done
  s=$(tr -d '[:space:]' < "$src/VERSION")
  zeek_serie_valida "$s" || fallo "$src/VERSION: '$s' mal formado (la serie, M.m: p. ej. 9.0). ERROR DE FABRICANTE: avisar a aRGus"
  log "serie $s (de $src/VERSION)"
  fuera=$(zeek_instalados | cut -d= -f1 | zeek_fuera_de_serie "$s")
  [ -z "$fuera" ] || fallo "ya hay paquetes de Zeek fuera de la serie $s: $(echo $fuera) (comparten /opt/zeek; no se tocan: vagrant destroy zeek y volver a subirla)"
  # shellcheck source=lib_apt_oficial.sh
  . "$lib"
  repo_oficial zeek https://download.opensuse.org/repositories/security:/zeek/Debian_12/Release.key "$src/CLAVE" \
    http://download.opensuse.org/repositories/security:/zeek/Debian_12/ "/" || fallo "repositorio de Zeek"
  actualizar_indices || fallo "apt-get update"
  actuales=$(zeek_instalados | cut -d= -f1)
  [ -z "$actuales" ] || apt-mark unhold $actuales >/dev/null
  DEBIAN_FRONTEND=noninteractive apt-get install -y "zeek-$s" || fallo "apt-get install zeek-$s"
  v=$(dpkg-query -W -f='${Version}' "zeek-$s" 2>/dev/null)
  bin=$(/opt/zeek/bin/zeek --version 2>&1)
  informe=$(zeek_instalados | zeek_comprobar "$s" "$v" "$bin") || fallo "lo instalado no cuadra con la serie $s: $(echo $informe)"
  apt-mark hold $(zeek_instalados | cut -d= -f1) >/dev/null || fallo "apt-mark hold"
  log "✅ zeek $v (serie $s de provisioning/zeek/VERSION), $(zeek_instalados | wc -l | tr -d ' ') paquetes fijados (apt-mark hold): $(echo $(zeek_instalados))"
}

if [ "${BASH_SOURCE[0]}" = "$0" ]; then main "$@"; fi
