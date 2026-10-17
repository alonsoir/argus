#!/usr/bin/env bash
# DAY300 [PROTEGIDOS-D300]: configuracion efectiva, alertas, episodios e identidad
# DROP_resumenes = DROP_FIN + alertas_protegido en el log del firewall.
set -u
export LC_ALL=C
F=/vagrant/logs/lab/firewall-agent.log
[ -f "$F" ] || { echo "ABORTA: no existe $F"; exit 1; }
echo "== configuracion de los rangos protegidos"
grep -n -e "ddos_protegidos" -e "rangos protegidos" "$F" | head -n 12
echo "== detalle ALERTA_PROTEGIDO: lineas totales y primeras 3"
grep -c "ALERTA_PROTEGIDO origen=" "$F"
grep -m 3 "ALERTA_PROTEGIDO origen=" "$F"
echo "== ultima linea protegidos"
grep "\[SOMBRA-DDOS\] protegidos:" "$F" | tail -n 1
echo "== INICIO y FIN"
grep -e "\[SOMBRA-DDOS\] INICIO" -e "\[SOMBRA-DDOS\] FIN" "$F"
echo "== identidad"
awk '
  /\[SOMBRA-DDOS\] resumen:/ { for (i = 1; i <= NF; i++) if ($i ~ /^DROP=/) { split($i, a, "="); res += a[2] } }
  /\[SOMBRA-DDOS\] FIN / { for (i = 1; i <= NF; i++) if ($i ~ /^eventos_drop=/) { split($i, b, "="); fin += b[2] } }
  /\[SOMBRA-DDOS\] protegidos:/ { for (i = 1; i <= NF; i++) if ($i ~ /^alertas=/) { split($i, c, "="); al = c[2] } }
  END { printf "DROP_resumenes=%d DROP_FIN=%d alertas_protegido=%d diferencia=%d\n", res, fin, al, res - fin - al }
' "$F"
