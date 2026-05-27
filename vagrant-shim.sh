#!/usr/bin/env bash
# /usr/local/bin/vagrant — CI shim (Jenkins inside VM)
# Generado DAY 167 — BACKLOG-CI-ENTERPRISE-001
#
# Problema: Jenkins corre DENTRO de la VM Vagrant. El Makefile usa
# "vagrant ssh -c CMD" para ejecutar comandos en la VM (diseñado para
# correr desde el host macOS). Este shim intercepta esas llamadas y
# las ejecuta directamente en el proceso local — ya estamos dentro.
#
# Instalación (una sola vez):
#   sudo cp vagrant-shim.sh /usr/local/bin/vagrant
#   sudo chmod +x /usr/local/bin/vagrant
#
# Comportamiento:
#   vagrant ssh [-c "CMD" | host -c "CMD"]  →  bash -c "CMD"
#   vagrant destroy [-f]                    →  no-op (VM ya viva)
#   vagrant up [host]                       →  no-op (VM ya viva)
#   vagrant status                          →  ok (shim)

set -euo pipefail

case "${1:-}" in

  ssh)
    shift
    cmd=""
    while [[ $# -gt 0 ]]; do
      case "$1" in
        -c)
          shift
          cmd="$1"
          shift
          ;;
        *)
          shift  # ignorar hostname: defender, client, etc.
          ;;
      esac
    done
    if [[ -z "$cmd" ]]; then
      echo "vagrant-shim: 'vagrant ssh' sin -c no soportado en CI" >&2
      exit 1
    fi
    exec bash -c "$cmd"
    ;;

  destroy)
    echo "vagrant-shim: 'vagrant destroy' ignorado — Jenkins corre dentro de la VM"
    exit 0
    ;;

  up)
    echo "vagrant-shim: 'vagrant up' ignorado — Jenkins corre dentro de la VM"
    exit 0
    ;;

  status)
    echo "vagrant-shim: running (CI shim activo)"
    exit 0
    ;;

  *)
    echo "vagrant-shim: comando '${1:-}' no soportado en CI" >&2
    exit 1
    ;;

esac