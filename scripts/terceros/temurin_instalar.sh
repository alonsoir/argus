#!/usr/bin/env bash
# scripts/terceros/temurin_instalar.sh — [TERCEROS-TEMURIN-D335] DEBT-LAB-TERCEROS-DESCARGA-SIN-VERIFICAR-001, lente
# Temurin: el JDK de Eclipse Temurin (Adoptium) desde su repositorio apt oficial, con la clave comprobada por huella y
# la versión fijada. Solo lo usa Jenkins (2.555+ pide Java 21): lo llama scripts/jenkins/jenkins_instalar.sh, en el
# defender, como root. Lee de provisioning/temurin/:
#   VERSION  versión exacta del paquete deb, A.B.C.D.E+N-M (p. ej. 21.0.7.0.0+6-0); el paquete es temurin-<A>-jdk
#   CLAVE    huella de la clave de firma del repositorio (lib_apt_oficial.sh)
# Sin defecto: mal o ausente, para (error de fabricante: el lab lo ve antes que nadie).
# Antes (hasta DAY334): `curl -s https://get.sdkman.io | bash` como root, sin firma ni hash, y `sdk install java
# 21.0.7-tem` en /root/.sdkman. Medido DAY335: el .deb de temurin-21-jdk deja el JDK en /usr/lib/jvm/temurin-21-jdk-amd64
# y su postinst registra java, javac, keytool... en update-alternatives (prioridad 2111); en el repo solo Jenkins usa
# Java. Depende de adoptium-ca-certificates, del mismo repositorio firmado.
# Si algo falla, retira el repositorio de Adoptium (para no romper los apt-get update siguientes) y sale con 1.
# Idempotente: con el paquete en su versión y su java diciendo esa versión, no toca nada. Al acabar borra /root/.sdkman
# (lo de antes; ya nadie lo usa). Las funciones tm_* no tocan el sistema (las prueba
# scripts/terceros/test_temurin_instalar.sh en el Mac).
set -u
LC_ALL=C; export LC_ALL
log() { echo "[TERCEROS-TEMURIN] $*"; }
fallo() { echo "[TERCEROS-TEMURIN] FALLA: $*"; exit 1; }
TM_URL_CLAVE=https://packages.adoptium.net/artifactory/api/gpg/key/public
TM_URL_REPO=https://packages.adoptium.net/artifactory/deb
TM_LISTA=/etc/apt/sources.list.d/adoptium.list
TM_ANILLO=/usr/share/keyrings/adoptium.gpg

# tm_version_valida VERSION -> rc 0 si es A.B.C.D.E+N-M (la cadena entera: un salto de línea dentro también es error)
tm_version_valida() {
  [[ "$1" =~ ^[0-9]{1,3}([.][0-9]{1,3}){4}[+][0-9]{1,3}-[0-9]{1,3}$ ]]
}

# tm_mayor VERSION -> la versión mayor de Java (21 de 21.0.7.0.0+6-0)
tm_mayor() { printf '%s\n' "${1%%.*}"; }

# tm_esperado VERSION -> lo que dice `java -version` en su línea "Runtime Environment Temurin-X+B": de 21.0.7.0.0+6-0
# sale 21.0.7+6 y de 21.0.12.1.0+1-0, 21.0.12.1+1 (se quitan los .0 del final, dejando al menos tres números)
tm_esperado() {
  local n=${1%%+*} b=${1#*+} p
  b=${b%%-*}
  p=${n//[^.]/}
  while [ "${#p}" -gt 2 ] && [[ "$n" == *.0 ]]; do n=${n%.0}; p=${n//[^.]/}; done
  printf 'Temurin-%s+%s\n' "$n" "$b"
}

# tm_java_cuadra VERSION SALIDA -> rc 0 si SALIDA (de `java -version`) tiene la línea "Runtime Environment
# Temurin-X+B (build ..." de esa versión (medido DAY335 con la 21.0.7 de SDKMAN:
# "OpenJDK Runtime Environment Temurin-21.0.7+6 (build 21.0.7+6-LTS)")
tm_java_cuadra() {
  printf '%s\n' "$2" | grep -qF "Runtime Environment $(tm_esperado "$1") (build "
}

tm_retirar() { rm -f "$TM_LISTA" "$TM_ANILLO"; }

main() {
  local src=${TEMURIN_SRC:-/vagrant/provisioning/temurin} v mayor paquete dir codigo actual
  [ "$(id -u)" = 0 ] || fallo "hay que ejecutarlo como root"
  v=$(tr -d '[:space:]' < "$src/VERSION" 2>/dev/null)
  tm_version_valida "$v" || fallo "$src/VERSION: '$v' mal formado (A.B.C.D.E+N-M: p. ej. 21.0.7.0.0+6-0). ERROR DE FABRICANTE: avisar a aRGus"
  mayor=$(tm_mayor "$v"); paquete=temurin-$mayor-jdk; dir=/usr/lib/jvm/temurin-$mayor-jdk-amd64
  log "paquete $paquete $v (de $src); se espera $(tm_esperado "$v") en $dir"
  actual=$(dpkg-query -W -f='${Version}' "$paquete" 2>/dev/null)
  if [ "$actual" = "$v" ] && tm_java_cuadra "$v" "$("$dir/bin/java" -version 2>&1)"; then
    log "✅ $paquete $v ya instalado"
  else
    codigo=$(. /etc/os-release && printf '%s' "$VERSION_CODENAME")
    [[ "$codigo" =~ ^[a-z]{3,20}$ ]] || fallo "VERSION_CODENAME '$codigo' de /etc/os-release mal formado"
    # shellcheck source=../vigilancia/lib_apt_oficial.sh
    . "$(dirname "${BASH_SOURCE[0]}")/../vigilancia/lib_apt_oficial.sh" || fallo "no se pudo cargar lib_apt_oficial.sh"
    repo_oficial adoptium "$TM_URL_CLAVE" "$src/CLAVE" "$TM_URL_REPO" "$codigo main" \
      || { tm_retirar; fallo "la clave de $TM_URL_CLAVE no se pudo comprobar con $src/CLAVE (repositorio retirado)"; }
    apt-get update -qq || { tm_retirar; fallo "apt-get update con el repositorio de Adoptium (repositorio retirado)"; }
    instalar_fijado "$paquete" "$v" || { tm_retirar; fallo "apt-get install $paquete=$v (repositorio retirado)"; }
    tm_java_cuadra "$v" "$("$dir/bin/java" -version 2>&1)" \
      || { tm_retirar; fallo "$dir/bin/java no dice $(tm_esperado "$v") (repositorio retirado)"; }
    log "✅ $paquete $v (Adoptium, repositorio firmado con la clave de $src/CLAVE) en $dir, en hold"
  fi
  if [ -d /root/.sdkman ]; then
    rm -rf /root/.sdkman && log "borrado /root/.sdkman (el Java de antes, de SDKMAN)"
  fi
}

if [ "${BASH_SOURCE[0]}" = "$0" ]; then main "$@"; fi
