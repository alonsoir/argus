#!/usr/bin/env bash
# DAY303 [ARGUS-VEREDICTO-D303]: veredicto PASA/FALLA del E2E del reinicio del sniffer (d300_reinicio_e2e.sh).
# Criterios del DISENO (decision de Alonso DAY303: EMECAS estricto y determinista), no de tiempos:
#  R1 identidad: marcados del ml-detector (suma de ataque= en [DDOS-V2]) = DROP de los resumenes del firewall
#     ([SOMBRA-DDOS] resumen: DROP=), diferencia 0. Transporte sin perdidas. DAY300: 19967=19967, 19864=19864.
#  R2 restauracion, segun el modo:
#     antes:    2 x "sin estado previo" (arranque + reinicio con CSV borrado) y 0 "restauradas"
#     ordenada: 1 x "sin estado previo", 1 x "restauradas ... (1 bajo presion)", y antes de ella un
#               "volcado de parada ... (1 bajo presion)"
#     kill9:    1 x "sin estado previo", 1 x "restauradas ... (1 bajo presion)", y NINGUN "volcado de parada"
#               antes de ella (restaura del volcado periodico; el volcado del pipeline-stop final va despues)
#  R3 marcado tras el reinicio:
#     antes:    0 marcados despues del corte (70 pps < abs_pps=200: en frio el ataque se aprende como base)
#     ordenada/kill9: marcados_despues >= 0,5 x marcados_antes. Frontera entre los dos regimenes posibles:
#               con estado ~1,2-1,3 (DAY300: 1,305 y 1,236), sin estado 0. La banda 1,15-1,40 se imprime
#               como dato y NO decide (depende de lo que tarde vagrant ssh en parar el sniffer).
# Corte: linea del ml-detector.log con el sniffer YA parado (linea_ml_parado; si falta, linea_ml_reinicio).
# Uso (Mac o defender): bash d303_veredicto_reinicio.sh antes|ordenada|kill9 DIRECTORIO_CORRIDA ; rc 0 = PASA
set -u
export LC_ALL=C
MODO=${1:?modo: antes|ordenada|kill9}
D=${2:?directorio de la corrida}
case "$MODO" in antes|ordenada|kill9) ;; *) echo "[VEREDICTO] modo invalido: $MODO"; exit 2;; esac
T=$D/tiempos.txt; M=$D/ml-detector.log; S=$D/sniffer.log; F=$D/firewall-agent.log
for f in "$T" "$M" "$S" "$F"; do
  [ -s "$f" ] || { echo "[VEREDICTO] FALLA: falta o esta vacio $f"; exit 1; }
done
fallos=0
ok() { echo "[VEREDICTO] PASA  $*"; }
ko() { echo "[VEREDICTO] FALLA $*"; fallos=$((fallos + 1)); }

L=$(awk '$1=="linea_ml_parado"{print $2}' "$T" | tail -n 1)
if [ -z "$L" ]; then
  L=$(awk '$1=="linea_ml_reinicio"{print $2}' "$T" | tail -n 1)
  echo "[VEREDICTO] AVISO: sin linea_ml_parado, corte en linea_ml_reinicio"
fi
[ -n "$L" ] || { echo "[VEREDICTO] FALLA: sin linea de corte en $T"; exit 1; }
echo "[VEREDICTO] modo=$MODO corrida=$D corte_ml=$L"

set -- $(awk -v L="$L" '/\[DDOS-V2\] bajo_presion=/ {
    t = 0
    for (i = 1; i <= NF; i++) if ($i ~ /^ataque=/) { split($i, b, "="); t = b[2] + 0 }
    if (NR <= L) a += t; else d += t
  } END { printf "%d %d\n", a, d }' "$M")
MA=$1; MD=$2
FWD=$(awk '/\[SOMBRA-DDOS\] resumen:/ { for (i = 1; i <= NF; i++) if ($i ~ /^DROP=/) { split($i, a, "="); s += a[2] } }
  END { printf "%d\n", s }' "$F")

# R1
if [ $((MA + MD)) -eq "$FWD" ]; then ok "R1 identidad: ml marcados $MA+$MD=$((MA + MD)) = firewall DROP_resumenes $FWD"
else ko "R1 identidad: ml marcados $((MA + MD)) != firewall DROP_resumenes $FWD (diferencia $((MA + MD - FWD)))"; fi

# R2
set -- $(awk '
  /\[DDOS-ESTADO\] sin estado previo/ { nsin++ }
  /\[DDOS-ESTADO\] restauradas / { res++; if ($0 ~ /\(1 bajo presion\)/) res1++; if (!lr) lr = NR }
  /\[DDOS-ESTADO\] volcado de parada/ { if (!lr) { vb++; if ($0 ~ /\(1 bajo presion\)/) vb1++ } }
  END { printf "%d %d %d %d %d\n", nsin, res, res1, vb, vb1 }' "$S")
# (nsin, no sin: en awk sin() es la funcion seno)
SIN=$1; RES=$2; RES1=$3; VB=$4; VB1=$5
R2="sin_estado_previo=$SIN restauradas=$RES (1_bajo_presion=$RES1) volcados_antes_de_restaurar=$VB (1_bajo_presion=$VB1)"
case "$MODO" in
  antes)    if [ "$SIN" -eq 2 ] && [ "$RES" -eq 0 ]; then ok "R2 restauracion: $R2"; else ko "R2 restauracion (esperado 2 sin estado previo y 0 restauradas): $R2"; fi ;;
  ordenada) if [ "$SIN" -eq 1 ] && [ "$RES" -eq 1 ] && [ "$RES1" -eq 1 ] && [ "$VB1" -ge 1 ]; then ok "R2 restauracion: $R2"
            else ko "R2 restauracion (esperado 1 sin estado, 1 restauradas con 1 bajo presion tras un volcado de parada con 1 bajo presion): $R2"; fi ;;
  kill9)    if [ "$SIN" -eq 1 ] && [ "$RES" -eq 1 ] && [ "$RES1" -eq 1 ] && [ "$VB" -eq 0 ]; then ok "R2 restauracion: $R2"
            else ko "R2 restauracion (esperado 1 sin estado, 1 restauradas con 1 bajo presion y 0 volcados de parada antes): $R2"; fi ;;
esac

# R3
RAZON=$(awk -v a="$MA" -v d="$MD" 'BEGIN { if (a > 0) printf "%.3f", d / a; else print "n/a" }')
case "$MODO" in
  antes) if [ "$MD" -eq 0 ]; then ok "R3 marcado: antes=$MA despues=$MD (en frio, 0 tras el reinicio)"
         else ko "R3 marcado: $MD marcados tras el reinicio con el CSV borrado (esperado 0); antes=$MA"; fi ;;
  *)     if [ "$MA" -gt 0 ] && [ $((2 * MD)) -ge "$MA" ]; then ok "R3 marcado: antes=$MA despues=$MD razon=$RAZON (frontera 0,5)"
         else ko "R3 marcado: antes=$MA despues=$MD razon=$RAZON (frontera 0,5: el estado no se restauro)"; fi ;;
esac
echo "[VEREDICTO] dato (no decide): razon despues/antes=$RAZON; banda DAY300 para ordenada/kill9 1,15-1,40"

if [ "$fallos" -eq 0 ]; then echo "[VEREDICTO] RESULTADO PASA (reinicio $MODO)"; exit 0; fi
echo "[VEREDICTO] RESULTADO FALLA (reinicio $MODO): $fallos criterio(s)"
exit 1
