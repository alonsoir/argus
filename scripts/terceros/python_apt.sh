#!/usr/bin/env bash
# scripts/terceros/python_apt.sh — [PYTHON-APT-D336] DEBT-LAB-TERCEROS-DESCARGA-SIN-VERIFICAR-001, lente pip (A):
# los módulos Python de PA_MODULOS salen de los paquetes de Debian (python3-<módulo>, de la fecha fijada de
# argus_debian_snapshot), nunca de pip. Comprueba, en el defender, que cada import resuelve a /usr/lib/python3/
# dist-packages; si alguno no importa o viene de otro sitio (p. ej. /usr/local, de pip), sale con 1.
# Antes (hasta DAY335): `pip3 install jinja2` y `pip3 install cryptography`, sin versión ni hash. Medido DAY336: ninguno
# de los dos bajaba nada (pip daba por buenos python3-jinja2 3.1.2 y python3-cryptography 38.0.4, que trae Ansible).
# Lo llama el Vagrantfile tras el apt-get de Python y en vault-enterprise-bootstrap. Las funciones pa_* no tocan el
# sistema (las prueba scripts/terceros/test_python_apt.sh en el Mac).
set -u
LC_ALL=C; export LC_ALL
PA_MODULOS="jinja2 cryptography"
PA_DIR_APT=/usr/lib/python3/dist-packages/

# 0 si la ruta del __file__ de un módulo está bajo el dist-packages de Debian
pa_origen_apt() {
  case "$1" in
    *..*) return 1 ;;
    "$PA_DIR_APT"?*) return 0 ;;
    *) return 1 ;;
  esac
}

# 0 si el fichero (un Vagrantfile) no tiene ninguna línea, fuera de comentarios, que instale con pip un módulo de
# PA_MODULOS
pa_sin_pip() {
  local f=$1 m
  [ -f "$f" ] || return 1
  for m in $PA_MODULOS; do
    if grep -v '^[[:space:]]*#' "$f" | grep -E "pip3?[[:space:]]+install" | grep -q -E "(^|[[:space:]])${m}([[:space:]=<>]|$)"; then
      return 1
    fi
  done
  return 0
}

main() {
  local m f rc=0
  for m in $PA_MODULOS; do
    if ! f=$(python3 -c "import ${m}; print(${m}.__file__)" 2>/dev/null) || [ -z "$f" ]; then
      echo "[PYTHON-APT] ❌ ${m} no importa (falta python3-${m})"; rc=1; continue
    fi
    if pa_origen_apt "$f"; then
      echo "[PYTHON-APT] ✅ ${m} de apt: ${f}"
    else
      echo "[PYTHON-APT] ❌ ${m} no es el de apt (python3-${m}): ${f}"; rc=1
    fi
  done
  return "$rc"
}

if [ "${BASH_SOURCE[0]}" = "$0" ]; then main "$@"; exit $?; fi
