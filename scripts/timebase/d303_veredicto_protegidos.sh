#!/usr/bin/env bash
# DAY303 [ARGUS-VEREDICTO-D303]: veredicto PASA/FALLA del E2E de rangos protegidos (d300_protegidos_e2e.sh).
# [PROTEGIDOS-BOOTSTRAP-D322] ADR-060 8e.5 (sección 3): reescrito para el manifiesto firmado (los rangos ya no salen del
# JSON). Criterios del DISEÑO (decisión de Alonso DAY303: EMECAS estricto y determinista):
#  P1 manifiesto: la última línea "[PROTEGIDOS-MANIFIESTO] verificado version=N" es del hospital y la planta de la
#     plantilla del lab (tools/argus-infra/plantillas/hospital-lab.json) con firmante argus-infra; la última
#     "[SOMBRA-DDOS] rangos protegidos (manifiesto version N):" lleva la misma N y TODAS las entradas de la plantilla
#     (categoria=cidr; [PROTEGIDOS-SENSORES-D323]: antes solo .20 y .61, escritas aquí); ninguna "rangos protegidos (NINGUNO".
#     La infraestructura del resto de criterios sale de esa línea (lo que el firewall aplica), no de una lista fija.
#  P2 un solo FIN, y su origenes= es SOLO 192.168.100.50 (ni .61 protegido ni .51 inocente).
#  P3 última línea "protegidos:": alertas > 0, alertas = intranet + infraestructura, dmz = externos_criticos = 0; cada
#     línea ALERTA_PROTEGIDO es de .61 con categoria=intranet o de una IP de infraestructura del manifiesto con
#     categoria=infraestructura (medido DAY323: con los sensores .10 .11 .12 como infraestructura, su NTP a .1 dentro del
#     ataque da alertas, como debe; el veredicto viejo las contaba como "de otro origen").
#  P4 identidad: DROP_resumenes = DROP_FIN + alertas (intranet + infraestructura) + DROP_aislados + pendientes, diferencia 0.
#     [SOMBRA-AISLADO-D311] DROP_aislados = suma de drop= de las lineas "[SOMBRA-DDOS] aislados:" (victimas que no
#     llegaron a episodio; DAY311: 2 FP de ddos_v2 en .11->.12:1514, agente Wazuh) y pendientes =
#     drop_pendientes_fuera + drop_pendientes_episodio de la ULTIMA de esas lineas. Un log sin lineas aislados:
#     (binario anterior) da DROP_aislados = 0 y vale la identidad antigua (DAY300: 16113 = 10742 + 5371).
#  P5 volumen: DROP_FIN en [98%, 100%] de los paquetes de .50 e intranet en [98%, 100%] de los de .61.
#     Lo unico que el diseno deja escapar es el primer segundo antes del INICIO (DAY300: 10742/10800, 5371/5400).
#     Los totales se leen del --limit del propio d300_protegidos_client.sh (no se copian aqui).
#  P6 infraestructura >= 0; ninguna IP de infraestructura del manifiesto aparece en origenes= de un INICIO ni de un FIN
#     (aRGus no bloquea su infraestructura). Medido DAY322: infraestructura=2 (lo que el DAY317 bloqueaba de la VM etcd
#     ahora es alerta, nunca bloqueo); DAY323: 11, de .20 y de los sensores.
# Uso (Mac o defender): bash d303_veredicto_protegidos.sh DIRECTORIO_CORRIDA ; rc 0 = PASA
set -u
export LC_ALL=C
D=${1:?directorio de la corrida}
F=$D/firewall-agent.log
AQUI=$(dirname "$0")
CLIENTE=$AQUI/d300_protegidos_client.sh
PLANTILLA=$AQUI/../../tools/argus-infra/plantillas/hospital-lab.json
for f in "$F" "$CLIENTE" "$PLANTILLA"; do
  [ -s "$f" ] || { echo "[VEREDICTO] FALLA: falta o esta vacio $f"; exit 1; }
done
lim() { awk -v v="$1" 'index($0, "\"" v "\"") && /tcpreplay/ { for (i = 1; i <= NF; i++) if ($i ~ /^--limit=/) { split($i, a, "="); print a[2] } }' "$CLIENTE" | head -n 1; }
N50=$(lim '$A50'); N61=$(lim '$A61')
[ -n "$N50" ] && [ -n "$N61" ] || { echo "[VEREDICTO] FALLA: no leo --limit de A50/A61 en $CLIENTE"; exit 1; }
read -r HOSP PLANTA < <(python3 -c 'import json, sys
j = json.load(open(sys.argv[1], encoding="utf-8")); p = list(j["plantas"])
print(j["hospital_id"], p[0] if len(p) == 1 else "")' "$PLANTILLA") || HOSP=""
# las entradas de la plantilla, categoria=cidr (las que tiene que traer el manifiesto que aplica el firewall)
ENTRADAS=$(python3 -c 'import json, sys
j = json.load(open(sys.argv[1], encoding="utf-8"))
print(" ".join(e["categoria"] + "=" + e["cidr"] for e in j["comun"] + [x for p in j["plantas"].values() for x in p]))' "$PLANTILLA") || ENTRADAS=""
[ -n "$ENTRADAS" ] || { echo "[VEREDICTO] FALLA: no leo las entradas de $PLANTILLA"; exit 1; }
[ -n "${HOSP:-}" ] && [ -n "${PLANTA:-}" ] || { echo "[VEREDICTO] FALLA: no leo hospital_id y una sola planta de $PLANTILLA"; exit 1; }
fallos=0
ok() { echo "[VEREDICTO] PASA  $*"; }
ko() { echo "[VEREDICTO] FALLA $*"; fallos=$((fallos + 1)); }
echo "[VEREDICTO] protegidos corrida=$D paquetes_ataque .50=$N50 .61=$N61 (de $CLIENTE) hospital=$HOSP planta=$PLANTA"

# P1
VER=$(grep -F '[PROTEGIDOS-MANIFIESTO] verificado version=' "$F" | tail -n 1)
VN=$(echo "$VER" | sed -n 's/.* verificado version=\([0-9]*\) .*/\1/p')
RAN=$(grep -F '[SOMBRA-DDOS] rangos protegidos (' "$F" | tail -n 1)
RN=$(echo "$RAN" | sed -n 's/.*rangos protegidos (manifiesto version \([0-9]*\)).*/\1/p')
NING=$(grep -c -F '[SOMBRA-DDOS] rangos protegidos (NINGUNO' "$F")
p1=""
[ -n "$VN" ] || p1="$p1 sin línea verificado;"
case "$VER" in *" hospital=$HOSP planta=$PLANTA "*) ;; *) p1="$p1 verificado no es de hospital=$HOSP planta=$PLANTA;";; esac
case "$VER" in *" firmante=argus-infra"*) ;; *) p1="$p1 firmante no es argus-infra;";; esac
[ -n "$RN" ] && [ "$RN" = "$VN" ] || p1="$p1 rangos protegidos con versión '${RN:-?}' (verificado '${VN:-?}');"
for e in $ENTRADAS; do case "$RAN " in *" $e "*) ;; *) p1="$p1 sin $e;";; esac; done
# la infraestructura que aplica el firewall (siempre /32, límite de ADR-060 D2): IPs separadas por espacios
INFRA=$(echo "$RAN" | tr ' ' '\n' | sed -n 's|^infraestructura=\([0-9.]*\)/32$|\1|p' | tr '\n' ' ' | sed 's/ *$//')
[ "$NING" -eq 0 ] || p1="$p1 $NING líneas 'rangos protegidos (NINGUNO';"
if [ -z "$p1" ]; then ok "P1 manifiesto: version $VN de $HOSP/$PLANTA firmada por argus-infra, con las $(echo $ENTRADAS | wc -w | tr -d ' ') entradas de la plantilla (infraestructura: $INFRA)"
else ko "P1 manifiesto:$p1"; fi

# P2
NFIN=$(grep -c '\[SOMBRA-DDOS\] FIN ' "$F")
ORIG=$(grep '\[SOMBRA-DDOS\] FIN ' "$F" | awk '{ for (i = 1; i <= NF; i++) if ($i ~ /^origenes=/) { sub(/^origenes=/, "", $i); print $i } }' | tail -n 1)
if [ "$NFIN" -eq 1 ] && echo "$ORIG" | grep -q -E '^192\.168\.100\.50:[0-9]+$'; then ok "P2 episodio: 1 FIN, origenes=$ORIG"
else ko "P2 episodio: FIN=$NFIN (esperado 1), origenes=$ORIG (esperado solo 192.168.100.50)"; fi

# P3
set -- $(grep '\[SOMBRA-DDOS\] protegidos:' "$F" | tail -n 1 | awk '{
    for (i = 1; i <= NF; i++) { split($i, a, "="); if (a[1] != "" && a[2] != "") v[a[1]] = a[2] + 0 }
    printf "%d %d %d %d %d\n", v["alertas"], v["intranet"], v["infraestructura"], v["dmz"], v["externos_criticos"] }')
AL=${1:-0}; IN=${2:-0}; INF=${3:-0}; DMZ=${4:-0}; EXT=${5:-0}
set -- $(grep -F '[SOMBRA-DDOS] ALERTA_PROTEGIDO ' "$F" | awk -v infra="$INFRA" 'BEGIN { m = split(infra, x, " "); for (i = 1; i <= m; i++) inf[x[i]] = 1 } {
    o = ""; c = ""
    for (i = 1; i <= NF; i++) { if ($i ~ /^origen=/) o = substr($i, 8); if ($i ~ /^categoria=/) c = substr($i, 11) }
    n++
    if (o == "192.168.100.61" && c == "intranet") a61++
    else if ((o in inf) && c == "infraestructura") ainf++
    else otras++ }
  END { printf "%d %d %d %d\n", n, a61, ainf, otras }')
LAL=${1:-0}; L61=${2:-0}; LINF=${3:-0}; LOTRAS=${4:-0}
if [ "$AL" -gt 0 ] && [ "$AL" -eq $((IN + INF)) ] && [ "$DMZ" -eq 0 ] && [ "$EXT" -eq 0 ] && [ "$LOTRAS" -eq 0 ]; then
  ok "P3 alertas: alertas=$AL = intranet $IN + infraestructura $INF, dmz=$DMZ externos_criticos=$EXT; líneas ALERTA_PROTEGIDO $LAL (.61 intranet $L61, infraestructura $LINF)"
else ko "P3 alertas: alertas=$AL intranet=$IN infraestructura=$INF dmz=$DMZ externos_criticos=$EXT; líneas ALERTA_PROTEGIDO $LAL de otro origen o categoría: $LOTRAS (esperado alertas = intranet + infraestructura, resto 0)"; fi

# P4
set -- $(awk '
  /\[SOMBRA-DDOS\] resumen:/ { for (i = 1; i <= NF; i++) if ($i ~ /^DROP=/) { split($i, a, "="); res += a[2] } }
  /\[SOMBRA-DDOS\] FIN / { for (i = 1; i <= NF; i++) if ($i ~ /^eventos_drop=/) { split($i, b, "="); fin += b[2] } }
  /\[SOMBRA-DDOS\] aislados:/ { pf = 0; pe = 0
    for (i = 1; i <= NF; i++) { split($i, c, "=")
      if (c[1] == "drop") ais += c[2]; if (c[1] == "drop_pendientes_fuera") pf = c[2]
      if (c[1] == "drop_pendientes_episodio") pe = c[2] } }
  END { printf "%d %d %d %d\n", res, fin, ais, pf + pe }' "$F")
RES=$1; FIN=$2; AIS=$3; PEN=$4
DIF=$((RES - FIN - AL - AIS - PEN))
if [ "$DIF" -eq 0 ]; then ok "P4 identidad: DROP_resumenes $RES = DROP_FIN $FIN + alertas $AL + aislados $AIS + pendientes $PEN"
else ko "P4 identidad: DROP_resumenes $RES != DROP_FIN $FIN + alertas $AL + aislados $AIS + pendientes $PEN (diferencia $DIF)"; fi

# P5 (98% = n*98/100 redondeado hacia arriba)
MIN50=$(( (N50 * 98 + 99) / 100 )); MIN61=$(( (N61 * 98 + 99) / 100 ))
if [ "$FIN" -ge "$MIN50" ] && [ "$FIN" -le "$N50" ] && [ "$IN" -ge "$MIN61" ] && [ "$IN" -le "$N61" ]; then
  ok "P5 volumen: DROP_FIN $FIN en [$MIN50, $N50], intranet $IN en [$MIN61, $N61]"
else ko "P5 volumen: DROP_FIN $FIN (esperado [$MIN50, $N50]), intranet $IN (esperado [$MIN61, $N61])"; fi

# P6
NINF=$(grep -E '\[SOMBRA-DDOS\] (INICIO|FIN) ' "$F" | awk -v infra="$INFRA" '
  BEGIN { m = split(infra, x, " "); for (i = 1; i <= m; i++) inf[x[i]] = 1 }
  { for (i = 1; i <= NF; i++) if ($i ~ /^origenes=/) { sub(/^origenes=/, "", $i); k = split($i, o, ",")
      for (j = 1; j <= k; j++) { split(o[j], ip, ":"); if (ip[1] in inf) { n++; cuales = cuales " " ip[1] } } } }
  END { printf "%d%s\n", n, cuales }')
if [ "$INF" -ge 0 ] && [ "${NINF%% *}" -eq 0 ]; then ok "P6 infraestructura: $INF alertas de infraestructura ($INFRA), nunca bloqueo: 0 en origenes= de INICIO/FIN"
else ko "P6 infraestructura: aparece en origenes= de INICIO/FIN ${NINF%% *} veces (${NINF#* }) (esperado 0: aRGus no bloquea su infraestructura)"; fi

if [ "$fallos" -eq 0 ]; then echo "[VEREDICTO] RESULTADO PASA (protegidos)"; exit 0; fi
echo "[VEREDICTO] RESULTADO FALLA (protegidos): $fallos criterio(s)"
exit 1
