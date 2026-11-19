#!/usr/bin/env bash
# scripts/emecas/lab_parar.sh — [LAB-PARAR-D331] (anfitrión) parada ordenada del laboratorio para cerrar el día y
# empezar al siguiente sin sobresaltos (decisión de Alonso DAY331). Es lo que hace `make halt`:
#   1. si el defender está en marcha, `make pipeline-stop` (sniffer ordenado; después ml-detector y firewall); si no
#      para bien, se avisa y se sigue: el halt apaga igual;
#   2. `vagrant halt` de una en una, en el orden de los argumentos (el Makefile pasa client, sensores, defender y los
#      nodos de control al revés: etcd y Vault, los últimos); las que ya están en poweroff o sin crear, se saltan;
#   3. si un halt no termina bien (o vence el límite), `vagrant halt --force` de esa VM, con aviso;
#   4. comprobación: todas en poweroff o not_created; si no, rc 1 diciendo cuál y en qué estado.
# Cada llamada, con scripts/emecas/con_limite.pl y el límite argus_lab_llamada_vm_limite_s de all.yml, leído y
# validado por scripts/emecas/lab_comun.rb (entero [10, 600]; falta o mal -> 60, con aviso).
# Uso: bash scripts/emecas/lab_parar.sh <vm>...    (rc 0 todo parado; 1 alguna sin parar o sin límite; 2 sin VMs)
# Para el test (scripts/emecas/test_lab_parar.sh): LAB_PARAR_VAGRANT, LAB_PARAR_MAKE y LAB_PARAR_ALLYML.
set -u
LC_ALL=C; export LC_ALL
D=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
VAGRANT=${LAB_PARAR_VAGRANT:-vagrant}
MAKE_ORDEN=${LAB_PARAR_MAKE:-make}
Y=${LAB_PARAR_ALLYML:-$D/../../ansible/inventory/group_vars/all.yml}
LIM=""
log() { echo "[LAB-PARAR] $*"; }

# lp_estado VM -> estado según vagrant (running, poweroff, not_created, aborted, saved...) o «desconocido»
lp_estado() {
  local e
  e=$(perl "$D/con_limite.pl" "$LIM" "$VAGRANT" status "$1" --machine-readable 2>/dev/null \
      | awk -F, '$3 == "state" { print $4; exit }')
  printf '%s\n' "${e:-desconocido}"
}

lp_parada_ok() { case "$1" in poweroff|not_created) return 0 ;; *) return 1 ;; esac; }

main() {
  local vm e rc mal=0 t0=$SECONDS
  [ $# -gt 0 ] || { echo "uso: bash scripts/emecas/lab_parar.sh <vm>..."; return 2; }
  LIM=$(ruby "$D/lab_comun.rb" limite "$Y") || { log "❌ sin límite de llamada a la VM ($Y)"; return 1; }
  log "orden de parada: $*; límite por llamada ${LIM} s"
  if [ "$(lp_estado defender)" = running ]; then
    log "defender en marcha: pipeline-stop"
    perl "$D/con_limite.pl" "$LIM" "$MAKE_ORDEN" --no-print-directory pipeline-stop; rc=$?
    [ "$rc" = 0 ] || log "⚠️  AVISO pipeline-stop rc=$rc$([ "$rc" = 142 ] && echo " (venció el límite de ${LIM} s)"); se sigue: el halt apaga igual"
  else
    log "defender no está en marcha: no hay pipeline que parar"
  fi
  for vm in "$@"; do
    e=$(lp_estado "$vm")
    if lp_parada_ok "$e"; then log "$vm: ya en $e"; continue; fi
    log "$vm: $e -> vagrant halt"
    perl "$D/con_limite.pl" "$LIM" "$VAGRANT" halt "$vm"; rc=$?
    if [ "$rc" != 0 ]; then
      log "⚠️  AVISO vagrant halt $vm rc=$rc$([ "$rc" = 142 ] && echo " (venció el límite de ${LIM} s)"): vagrant halt --force $vm"
      perl "$D/con_limite.pl" "$LIM" "$VAGRANT" halt --force "$vm" || log "⚠️  AVISO vagrant halt --force $vm rc=$?"
    fi
  done
  for vm in "$@"; do
    e=$(lp_estado "$vm")
    lp_parada_ok "$e" || { log "❌ $vm queda en $e"; mal=$((mal + 1)); }
  done
  [ "$mal" = 0 ] || { log "❌ $mal de $# VMs sin parar"; return 1; }
  log "✅ laboratorio parado en orden: $# VMs en poweroff o sin crear, en $((SECONDS - t0)) s"
}

if [ "${BASH_SOURCE[0]}" = "$0" ]; then main "$@"; exit $?; fi
