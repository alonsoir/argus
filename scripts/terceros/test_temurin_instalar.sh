#!/usr/bin/env bash
# scripts/terceros/test_temurin_instalar.sh — [TERCEROS-TEMURIN-D335] tests de las funciones tm_* de temurin_instalar.sh
# y de provisioning/temurin/{VERSION,CLAVE} (Mac, sin VMs ni red). La clave contra sus huellas, en repo_oficial
# (lib_apt_oficial.sh). Cada caso de rechazo se vuelve a correr contra funciones que lo aceptan todo, y tiene que fallar
# ahí: así se ve que el test distingue.
set -u
LC_ALL=C; export LC_ALL
aqui=$(dirname "$0")
src=${TEMURIN_SRC:-$aqui/../../provisioning/temurin}
. "$aqui/temurin_instalar.sh"

HUELLA_DAY335=3B04D753C9050D9A5D343F39843C48A565F8F04B
casos=0; fallos=0; rechazos=0; rechazos_vistos=0
acepta() { local n=$1; shift; casos=$((casos + 1)); if "$@" >/dev/null 2>&1; then echo "✅ $n"; else echo "❌ $n"; fallos=$((fallos + 1)); fi; }
rechaza() { local n=$1; shift; casos=$((casos + 1)); rechazos=$((rechazos + 1)); if "$@" >/dev/null 2>&1; then echo "❌ $n"; fallos=$((fallos + 1)); rechazos_vistos=$((rechazos_vistos + 1)); else echo "✅ $n"; fi; }

# `java -version` del Temurin 21.0.7 de SDKMAN en el defender (medido DAY335), y variantes
JAVA_21_0_7=$'openjdk version "21.0.7" 2025-04-15 LTS\nOpenJDK Runtime Environment Temurin-21.0.7+6 (build 21.0.7+6-LTS)\nOpenJDK 64-Bit Server VM Temurin-21.0.7+6 (build 21.0.7+6-LTS, mixed mode, sharing)'
JAVA_21_0_8=$'openjdk version "21.0.8" 2025-07-15 LTS\nOpenJDK Runtime Environment Temurin-21.0.8+9 (build 21.0.8+9-LTS)\nOpenJDK 64-Bit Server VM Temurin-21.0.8+9 (build 21.0.8+9-LTS, mixed mode, sharing)'
JAVA_OPENJDK=$'openjdk version "21.0.7" 2025-04-15\nOpenJDK Runtime Environment (build 21.0.7+6-Debian-1)\nOpenJDK 64-Bit Server VM (build 21.0.7+6-Debian-1, mixed mode, sharing)'
JAVA_NADA=$'bash: /usr/lib/jvm/temurin-21-jdk-amd64/bin/java: No such file or directory'

esperado_es() { [ "$(tm_esperado "$1")" = "$2" ]; }
mayor_es() { [ "$(tm_mayor "$1")" = "$2" ]; }
version_repo() { tm_version_valida "$(tr -d '[:space:]' < "$src/VERSION")"; }
version_repo_es() { [ "$(tr -d '[:space:]' < "$src/VERSION")" = "$1" ]; }
clave_repo_es() { [ "$(grep -v '^#' "$src/CLAVE" | tr -d ' \t\r' | grep -v '^$')" = "$1" ]; }

los_casos() {
  acepta "versión 21.0.7.0.0+6-0" tm_version_valida 21.0.7.0.0+6-0
  acepta "versión 21.0.12.1.0+1-0" tm_version_valida 21.0.12.1.0+1-0
  rechaza "versión 21.0.7+6 (la de java, no la del paquete)" tm_version_valida 21.0.7+6
  rechaza "versión 21.0.7.0.0+6 (sin revisión del paquete)" tm_version_valida 21.0.7.0.0+6
  rechaza "versión latest (por nombre)" tm_version_valida latest
  rechaza "dos versiones en dos líneas" tm_version_valida $'21.0.7.0.0+6-0\n21.0.8.0.0+9-0'
  acepta "mayor de 21.0.7.0.0+6-0: 21" mayor_es 21.0.7.0.0+6-0 21
  acepta "esperado de 21.0.7.0.0+6-0: Temurin-21.0.7+6" esperado_es 21.0.7.0.0+6-0 Temurin-21.0.7+6
  acepta "esperado de 21.0.12.1.0+1-0: Temurin-21.0.12.1+1" esperado_es 21.0.12.1.0+1-0 Temurin-21.0.12.1+1
  acepta "esperado de 21.0.0.0.0+35-0: Temurin-21.0.0+35 (deja tres números)" esperado_es 21.0.0.0.0+35-0 Temurin-21.0.0+35
  acepta "java de la 21.0.7 (medido DAY335) cuadra con 21.0.7.0.0+6-0" tm_java_cuadra 21.0.7.0.0+6-0 "$JAVA_21_0_7"
  rechaza "java de la 21.0.8 con 21.0.7.0.0+6-0" tm_java_cuadra 21.0.7.0.0+6-0 "$JAVA_21_0_8"
  rechaza "un OpenJDK que no es Temurin, misma versión" tm_java_cuadra 21.0.7.0.0+6-0 "$JAVA_OPENJDK"
  rechaza "sin java" tm_java_cuadra 21.0.7.0.0+6-0 "$JAVA_NADA"
  rechaza "salida vacía" tm_java_cuadra 21.0.7.0.0+6-0 ""
  acepta "provisioning/temurin/VERSION bien formado" version_repo
  acepta "provisioning/temurin/VERSION es la 21.0.7 de antes (la de SDKMAN, medido DAY335)" version_repo_es 21.0.7.0.0+6-0
  acepta "provisioning/temurin/CLAVE es la huella de Adoptium (medido DAY335, dos canales)" clave_repo_es "$HUELLA_DAY335"
  rechaza "provisioning/temurin/CLAVE no es otra huella" clave_repo_es 5E386EADB55F01504CAE8BCF7198F4B714ABFC68
}

los_casos
echo "$((casos - fallos))/$casos casos"
total=$fallos

# Contra funciones que lo aceptan todo, cada rechazo tiene que dar ❌.
tm_version_valida() { return 0; }
tm_java_cuadra() { return 0; }
clave_repo_es() { return 0; }
esperados=$rechazos; casos=0; fallos=0; rechazos=0; rechazos_vistos=0
los_casos > /dev/null
if [ "$rechazos_vistos" = "$esperados" ]; then
  echo "✅ contra funciones que lo aceptan todo fallan los $esperados casos de rechazo"
else
  echo "❌ contra funciones que lo aceptan todo fallan $rechazos_vistos de los $esperados casos de rechazo"; total=$((total + 1))
fi
[ "$total" = 0 ] && echo "✅ test-temurin-instalar" || { echo "❌ test-temurin-instalar: $total fallos"; exit 1; }
