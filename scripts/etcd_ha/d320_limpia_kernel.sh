#!/usr/bin/env bash
# [PROTEGIDOS-LIMPIEZA-D320] DAY320. Retira del kernel lo que deja el firewall-acl-agent tras un E2E: el salto de INPUT,
# la cadena del filtro, el salto de raw PREROUTING y las tres cadenas del antispoofing (ADR-060 D8, 8e.4b) y los sets.
# Corre EN EL DEFENDER (como root). Los nombres NO van aquí: los pasa quien lo llama, leídos de firewall.json.
#
# Por qué existe (medido DAY320): los traps de d302_mitigacion_e2e.sh y d320_vigia_e2e.sh borraban la cadena del filtro
# y los sets, pero no la cadena raw del antispoofing. Como ésta usa el set de protegidos, 'ipset destroy' fallaba en
# silencio y quedaban en el defender ARGUS_ANTISPOOF{,_IF,_MAC} (en modo descarta) y los cuatro sets (quedan sets=1).
# El orden importa: primero los saltos y las cadenas (raw y filter), después los sets, que ya nadie referencia.
#
# Uso:  sudo bash d320_limpia_kernel.sh [--contar] CADENA_FILTER CADENA_ANTISPOOF SET [SET...]
#       (CADENA_ANTISPOOF puede ser '-' si no hay antispoofing que retirar; --contar solo cuenta, no toca nada:
#        es la comprobación de lab-kernel-limpio al final de lab-e2e)
# Salida: una línea "quedan raw=N filter=N sets=N"; código 0 si todo es 0, 1 si queda algo, 2 si el uso es malo.
set -u
CONTAR=0; [ "${1:-}" = "--contar" ] && { CONTAR=1; shift; }
if [ "$#" -lt 3 ]; then echo "uso: $0 CADENA_FILTER CADENA_ANTISPOOF SET [SET...]" >&2; exit 2; fi
CH=$1; AS=$2; shift 2
for n in "$CH" "$AS" "$@"; do
  case "$n" in ''|*[!A-Za-z0-9_.-]*) echo "nombre no válido: '$n'" >&2; exit 2 ;; esac
done

if [ "$CONTAR" = 0 ] && [ "$AS" != "-" ]; then
  while iptables -w -t raw -D PREROUTING -j "$AS" 2>/dev/null; do :; done
  for c in "$AS" "${AS}_IF" "${AS}_MAC"; do iptables -w -t raw -F "$c" 2>/dev/null; done
  for c in "$AS" "${AS}_IF" "${AS}_MAC"; do iptables -w -t raw -X "$c" 2>/dev/null; done
fi
if [ "$CONTAR" = 0 ]; then
  while iptables -w -D INPUT -j "$CH" 2>/dev/null; do :; done
  iptables -w -F "$CH" 2>/dev/null
  iptables -w -X "$CH" 2>/dev/null
  for s in "$@"; do ipset destroy "$s" 2>/dev/null; done
fi

raw=0
[ "$AS" != "-" ] && raw=$(iptables -w -t raw -S | grep -c -w -e "$AS" -e "${AS}_IF" -e "${AS}_MAC")
filter=$(iptables -w -S | grep -c -w -e "$CH")
pat=(); for s in "$@"; do pat+=(-e "$s"); done
sets=$(ipset list -n | grep -c -x "${pat[@]}")
echo "    quedan raw=$raw filter=$filter sets=$sets"
[ "$raw" = 0 ] && [ "$filter" = 0 ] && [ "$sets" = 0 ]
