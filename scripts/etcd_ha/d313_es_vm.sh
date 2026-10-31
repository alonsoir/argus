#!/bin/bash
# d313_es_vm.sh — DAY313, paso 4b.2 de DEBT-ETCD-HA-TLS-RAFT-001: arrancar y parar el etcd-server en la VM etcd para medir.
# Se ejecuta EN LA VM etcd (sudo). El binario es el que instaló d312_etcd_vm_deploy.sh en /opt/argus/etcd-server.
#   bash d313_es_vm.sh arrancar [JSON]   arranca en segundo plano con -c JSON (defecto: el de la VM, con mTLS) y log propio
#   bash d313_es_vm.sh parar             SIGTERM y mide cuántos segundos tarda en salir (SIGKILL a los 120 s)
# Log: /var/tmp/d313-etcd-server.log (cada arranque lo vacía); PID: /run/argus/d313-etcd-server.pid
set -euo pipefail
LC_ALL=C; export LC_ALL
MODO=${1:-}
JSON=${2:-/vagrant/etcd-server/config/etcd-server.etcd-vm.json}
BIN=/opt/argus/etcd-server/bin/etcd-server
LIB=/opt/argus/etcd-server/lib
LOG=/var/tmp/d313-etcd-server.log
PID=/run/argus/d313-etcd-server.pid
ts() { date -u +%FT%TZ; }
falla() { echo "[D313-VM] $(ts) FALLA: $*"; exit 1; }

case "$MODO" in
  arrancar)
    [ -x "$BIN" ] || falla "no existe $BIN (d312_etcd_vm_deploy.sh desde el Mac)"
    [ -f "$JSON" ] || falla "no existe $JSON"
    if sudo ss -ltnpH 'sport = :2379' | grep -q .; then
      sudo ss -ltnpH 'sport = :2379'
      falla "el 2379 ya está ocupado (arriba quién): pararlo antes"
    fi
    echo "[D313-VM] $(ts) $(hostname) binario sha256 $(sha256sum "$BIN" | cut -c1-16) JSON $JSON"
    sudo LD_LIBRARY_PATH="$LIB" "$BIN" -c "$JSON" --check-config > /var/tmp/d313-check.txt 2>&1 && rc=0 || rc=$?
    grep -E 'ETCD-CONFIG-CHECK|ETCD-TLS-FATAL' /var/tmp/d313-check.txt || true
    [ "$rc" = 0 ] || falla "--check-config rc=$rc: no se arranca"
    sudo truncate -s 0 "$LOG" 2>/dev/null || true
    sudo sh -c "LD_LIBRARY_PATH='$LIB' nohup '$BIN' -c '$JSON' > '$LOG' 2>&1 & echo \$! > '$PID'"
    for _ in $(seq 1 30); do
      sudo ss -ltnH 'sport = :2379' | grep -q . && break
      sleep 1
    done
    sudo ss -ltnH 'sport = :2379' | grep -q . || { sudo tail -n 20 "$LOG"; falla "nadie escucha en 2379 a los 30 s"; }
    echo "[D313-VM] $(ts) arrancado pid=$(sudo cat "$PID"); escucha: $(sudo ss -ltnH 'sport = :2379' | awk '{print $4}' | tr '\n' ' ')"
    sudo grep -E '^\[ETCD-TLS|^\[ETCD-CONFIG\]|CONFIG-DEFAULT|registrado en proceso' "$LOG" || true
    ;;
  parar)
    [ -f "$PID" ] || falla "no hay $PID (¿se arrancó con este script?)"
    P=$(sudo cat "$PID")
    sudo kill -0 "$P" 2>/dev/null || falla "el pid $P ya no existe"
    T0=$(date +%s.%N)
    sudo kill -TERM "$P"
    for _ in $(seq 1 1200); do
      sudo kill -0 "$P" 2>/dev/null || break
      sleep 0.1
    done
    T1=$(date +%s.%N)
    if sudo kill -0 "$P" 2>/dev/null; then
      sudo kill -KILL "$P"
      echo "[D313-VM] $(ts) NO salió en 120 s tras SIGTERM: SIGKILL"
    fi
    echo "[D313-VM] $(ts) parado pid=$P en $(awk -v a="$T0" -v b="$T1" 'BEGIN{printf "%.1f", b-a}') s tras SIGTERM"
    sudo rm -f "$PID"
    ;;
  *) falla "modo '$MODO' desconocido (arrancar [JSON] | parar)";;
esac
