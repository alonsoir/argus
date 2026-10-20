#!/usr/bin/env bash
# DAY303 [ARGUS-VEREDICTO-D303]: veredicto PASA/FALLA del E2E de rangos protegidos (d300_protegidos_e2e.sh).
# Criterios del DISENO (decision de Alonso DAY303: EMECAS estricto y determinista):
#  P1 configuracion: "[CONFIG] ddos_protegidos.intranet += 192.168.100.61/32 (JSON)" y 0 "[CONFIG-DEFAULT] ddos_protegidos"
#  P2 un solo FIN, y su origenes= es SOLO 192.168.100.50 (ni .61 protegido ni .51 inocente)
#  P3 ultima linea "protegidos:": alertas > 0, intranet = alertas, dmz = externos_criticos = por_defecto = 0
#  P4 identidad: DROP_resumenes = DROP_FIN + alertas, diferencia 0 (DAY300: 16113 = 10742 + 5371).
#     OJO: BACKLOG tiene abierta la discrepancia de 4 DROP de antes2 (primera ventana con < m DROP fuera
#     del episodio). Si aparece aqui, FALLA: sigue sin explicar.
#  P5 volumen: DROP_FIN en [98%, 100%] de los paquetes de .50 y alertas en [98%, 100%] de los de .61.
#     Lo unico que el diseno deja escapar es el primer segundo antes del INICIO (DAY300: 10742/10800, 5371/5400).
#     Los totales se leen del --limit del propio d300_protegidos_client.sh (no se copian aqui).
# Uso (Mac o defender): bash d303_veredicto_protegidos.sh DIRECTORIO_CORRIDA ; rc 0 = PASA
set -u
export LC_ALL=C
D=${1:?directorio de la corrida}
F=$D/firewall-agent.log
CLIENTE=$(dirname "$0")/d300_protegidos_client.sh
for f in "$F" "$CLIENTE"; do
  [ -s "$f" ] || { echo "[VEREDICTO] FALLA: falta o esta vacio $f"; exit 1; }
done
lim() { awk -v v="$1" 'index($0, "\"" v "\"") && /tcpreplay/ { for (i = 1; i <= NF; i++) if ($i ~ /^--limit=/) { split($i, a, "="); print a[2] } }' "$CLIENTE" | head -n 1; }
N50=$(lim '$A50'); N61=$(lim '$A61')
[ -n "$N50" ] && [ -n "$N61" ] || { echo "[VEREDICTO] FALLA: no leo --limit de A50/A61 en $CLIENTE"; exit 1; }
fallos=0
ok() { echo "[VEREDICTO] PASA  $*"; }
ko() { echo "[VEREDICTO] FALLA $*"; fallos=$((fallos + 1)); }
echo "[VEREDICTO] protegidos corrida=$D paquetes_ataque .50=$N50 .61=$N61 (de $CLIENTE)"

# P1
C1=$(grep -c -F '[CONFIG] ddos_protegidos.intranet += 192.168.100.61/32 (JSON)' "$F")
C2=$(grep -c -F '[CONFIG-DEFAULT] ddos_protegidos' "$F")
if [ "$C1" -ge 1 ] && [ "$C2" -eq 0 ]; then ok "P1 configuracion: intranet .61 del JSON ($C1), CONFIG-DEFAULT ddos_protegidos=$C2"
else ko "P1 configuracion: intranet .61 del JSON=$C1 (esperado >=1), CONFIG-DEFAULT ddos_protegidos=$C2 (esperado 0)"; fi

# P2
NFIN=$(grep -c '\[SOMBRA-DDOS\] FIN ' "$F")
ORIG=$(grep '\[SOMBRA-DDOS\] FIN ' "$F" | awk '{ for (i = 1; i <= NF; i++) if ($i ~ /^origenes=/) { sub(/^origenes=/, "", $i); print $i } }' | tail -n 1)
if [ "$NFIN" -eq 1 ] && echo "$ORIG" | grep -q -E '^192\.168\.100\.50:[0-9]+$'; then ok "P2 episodio: 1 FIN, origenes=$ORIG"
else ko "P2 episodio: FIN=$NFIN (esperado 1), origenes=$ORIG (esperado solo 192.168.100.50)"; fi

# P3
set -- $(grep '\[SOMBRA-DDOS\] protegidos:' "$F" | tail -n 1 | awk '{
    for (i = 1; i <= NF; i++) { split($i, a, "="); if (a[1] != "" && a[2] != "") v[a[1]] = a[2] + 0 }
    printf "%d %d %d %d %d\n", v["alertas"], v["intranet"], v["dmz"], v["externos_criticos"], v["por_defecto"] }')
AL=${1:-0}; IN=${2:-0}; DMZ=${3:-0}; EXT=${4:-0}; DEF=${5:-0}
if [ "$AL" -gt 0 ] && [ "$IN" -eq "$AL" ] && [ "$DMZ" -eq 0 ] && [ "$EXT" -eq 0 ] && [ "$DEF" -eq 0 ]; then
  ok "P3 alertas: alertas=$AL intranet=$IN dmz=$DMZ externos_criticos=$EXT por_defecto=$DEF"
else ko "P3 alertas: alertas=$AL intranet=$IN dmz=$DMZ externos_criticos=$EXT por_defecto=$DEF (esperado todas en intranet, resto 0)"; fi

# P4
set -- $(awk '
  /\[SOMBRA-DDOS\] resumen:/ { for (i = 1; i <= NF; i++) if ($i ~ /^DROP=/) { split($i, a, "="); res += a[2] } }
  /\[SOMBRA-DDOS\] FIN / { for (i = 1; i <= NF; i++) if ($i ~ /^eventos_drop=/) { split($i, b, "="); fin += b[2] } }
  END { printf "%d %d\n", res, fin }' "$F")
RES=$1; FIN=$2
DIF=$((RES - FIN - AL))
if [ "$DIF" -eq 0 ]; then ok "P4 identidad: DROP_resumenes $RES = DROP_FIN $FIN + alertas $AL"
else ko "P4 identidad: DROP_resumenes $RES != DROP_FIN $FIN + alertas $AL (diferencia $DIF)"; fi

# P5 (98% = n*98/100 redondeado hacia arriba)
MIN50=$(( (N50 * 98 + 99) / 100 )); MIN61=$(( (N61 * 98 + 99) / 100 ))
if [ "$FIN" -ge "$MIN50" ] && [ "$FIN" -le "$N50" ] && [ "$AL" -ge "$MIN61" ] && [ "$AL" -le "$N61" ]; then
  ok "P5 volumen: DROP_FIN $FIN en [$MIN50, $N50], alertas $AL en [$MIN61, $N61]"
else ko "P5 volumen: DROP_FIN $FIN (esperado [$MIN50, $N50]), alertas $AL (esperado [$MIN61, $N61])"; fi

if [ "$fallos" -eq 0 ]; then echo "[VEREDICTO] RESULTADO PASA (protegidos)"; exit 0; fi
echo "[VEREDICTO] RESULTADO FALLA (protegidos): $fallos criterio(s)"
exit 1
