#!/usr/bin/env bash
# scripts/terceros/lib_git_fijado.sh — [TERCEROS-GIT-FIJADO-D335] DEBT-LAB-TERCEROS-DESCARGA-SIN-VERIFICAR-001: lo común
# a los instaladores que traen código fuente de terceros por git (libbpf, cpp-httplib y etcd-cpp-apiv3). Un tag ligero
# no lleva firma y se puede mover (lección DAY334): se fija el commit al que apunta y se
# comprueba después de clonar. Sacado de libbpf_instalar.sh DAY335, sin cambiar una línea de las funciones, para que
# esté en un único lugar.
# Se carga con `.` desde cada instalador; no toca el sistema (lo prueba scripts/terceros/test_lib_git_fijado.sh en el
# Mac, sin red: con un repositorio git hecho allí).
# [TERCEROS-GIT-REINTENTOS-D335] (decisión de Alonso DAY335) un fallo de red pasajero no debe costar un EMECAS: el clon
# se reintenta hasta GF_INTENTOS veces, como el `wget -t 3` de los demás instaladores de scripts/terceros/; agotados,
# para y lo dice. Que el tag apunte a otro commit no es un fallo pasajero: para al primero, sin reintentar.

GF_INTENTOS=3     # intentos de clonar, en total (1..10)
GF_ESPERA_S=10    # segundos entre un intento fallido y el siguiente (0..300)

# gf_version_valida VERSION -> rc 0 si es X.Y.Z (la cadena entera: un salto de línea dentro también es error)
gf_version_valida() {
  [[ "$1" =~ ^[0-9]{1,3}[.][0-9]{1,3}[.][0-9]{1,3}$ ]]
}

# gf_commit_de_fichero FICHERO -> la única línea sin comentar, si son 40 hex en minúscula; rc 1 si no
gf_commit_de_fichero() {
  local s
  s=$(grep -v '^#' "$1" 2>/dev/null | tr -d ' \t\r' | grep -v '^$')
  [ "$(printf '%s\n' "$s" | grep -c .)" = 1 ] || return 1
  printf '%s\n' "$s" | grep -Eqx '[0-9a-f]{40}' || return 1
  printf '%s\n' "$s"
}

# gf_clonar URL TAG DESTINO COMMIT -> clona TAG (solo ese, profundidad 1) en DESTINO y rc 0 si HEAD es COMMIT; si no,
# rc 1 y el motivo por la salida. Hasta GF_INTENTOS intentos de clonar, avisando de cada fallo por stderr; la
# comprobación del commit, una vez. No compila nada.
gf_clonar() {
  local h i=1
  until git -c advice.detachedHead=false clone -q --depth 1 --branch "$2" "$1" "$3" >/dev/null 2>&1; do
    rm -rf "$3"
    [ "$i" -lt "$GF_INTENTOS" ] || { echo "no se pudo clonar el tag $2 de $1 ($GF_INTENTOS intentos)"; return 1; }
    echo "[GIT-FIJADO] intento $i/$GF_INTENTOS de clonar el tag $2 de $1 fallido; otro en $GF_ESPERA_S s" >&2
    i=$((i + 1)); sleep "$GF_ESPERA_S"
  done
  h=$(git -C "$3" rev-parse HEAD 2>/dev/null)
  [ "$h" = "$4" ] || { echo "el tag $2 apunta a ${h:-nada}, se exige $4"; return 1; }
}
