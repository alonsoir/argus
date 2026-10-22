#!/usr/bin/env bash
# DAY303 [ARGUS-EMECAS-FRESCURA-D303]: lo que corre es lo que se acaba de compilar.
# Para cada componente del pipeline comprueba, dentro de la VM defender:
#   1. existe el binario en <comp>/build-<perfil>/
#   2. <comp>/build-active apunta a <comp>/build-<perfil> (lo crea set-build-profile)
#   3. con sello: el binario es MAS NUEVO que el sello (escrito al inicio de EMECAS en /vagrant,
#      mismo sistema de ficheros que los binarios, asi las dos fechas las pone el mismo reloj)
# Falla (exit 1) con cualquier binario ausente, enlace mal puesto o binario anterior al sello.
# Uso (defender): bash /vagrant/scripts/emecas/emecas_frescura.sh <perfil> [sello]
set -u
PERFIL="${1:?uso: emecas_frescura.sh <perfil> [sello]}"
SELLO="${2:-}"
if [[ -n "$SELLO" && ! -f "$SELLO" ]]; then
  echo "[FRESCURA] FALLA: no existe el sello $SELLO"
  exit 1
fi
n=0
fallos=0

comprobar() {
  local comp="$1" bin="$2" con_enlace="$3"
  local dir="/vagrant/${comp}/build-${PERFIL}"
  local act="/vagrant/${comp}/build-active"
  local f="${dir}/${bin}"
  n=$((n + 1))
  if [[ ! -x "$f" ]]; then
    echo "[FRESCURA] FALLA ${comp}: no existe ${f}"
    fallos=$((fallos + 1))
    return
  fi
  local fecha
  fecha=$(stat -c '%y' "$f" | cut -c1-19)
  if [[ "$con_enlace" == "si" && "$(readlink -f "$act")" != "$(readlink -f "$dir")" ]]; then
    echo "[FRESCURA] FALLA ${comp}: build-active -> $(readlink "$act" 2>/dev/null || echo 'no existe'), se esperaba ${dir}"
    fallos=$((fallos + 1))
    return
  fi
  if [[ -n "$SELLO" && ! "$f" -nt "$SELLO" ]]; then
    echo "[FRESCURA] FALLA ${comp}: ${bin} es de ${fecha}, anterior al sello ($(stat -c '%y' "$SELLO" | cut -c1-19))"
    fallos=$((fallos + 1))
    return
  fi
  echo "[FRESCURA] ok    ${comp}: ${bin} ${fecha}"
}

comprobar etcd-server        etcd-server                  si
comprobar rag-ingester       rag-ingester                 si
comprobar ml-detector        ml-detector                  si
comprobar sniffer            sniffer                      si
comprobar firewall-acl-agent firewall-acl-agent           si   # FIREWALL_BIN := ./firewall-acl-agent (medido DAY303)
comprobar tools              synthetic_sniffer_injector   no
comprobar tools              synthetic_ml_output_injector no

echo "[FRESCURA] resumen perfil=${PERFIL} sello=${SELLO:-ninguno} comprobados=${n} fallos=${fallos}"
if [[ "$fallos" -ne 0 ]]; then
  echo "[FRESCURA] FALLA"
  exit 1
fi
echo "[FRESCURA] PASA"
