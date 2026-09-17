#!/usr/bin/env bash
# scripts/ddos_gate_start.sh — DAY 271. Driver de MEDICION DE COMPUERTA (level1->level2).
# NO es hermano de ctu_start.sh: aquel construye el grafo cross-sensor; este mide SOLO
# el enrutado de la compuerta del ml-detector con un flood DDoS real (CICDDoS2019).
# Sin Zeek, sin adapters, sin bronce/oro, sin Kuzu, sin HMAC. Front-half + 2 greps.
# Requiere: `make pipeline-start VERBOSE=1` antes (ml-detector sniffando, verbosidad de gate).
# Se ejecuta en el HOST. A. Roman + Claude.
set -uo pipefail

PCAP="/vagrant/datasets/cicddos2019/SAT-01-12-2018_0125"   # flood UDP unidireccional, src unico
ATK_IP="172.16.0.5"; VIC_IP="192.168.50.1"                  # ground-truth CIC (clock-independiente)
PPS="4000"                                                  # cap de arranque (regimen Neris, 0,8% drop). Sube midiendo.
DRAIN="30"                                                  # segundos de drenaje tras el replay

# <<< CONFIRMAR: ruta del log del ml-detector y guest donde corre >>>
MLGUEST="defender"
MLLOG="/vagrant/logs/lab/ml-detector.log"                   # <-- ajusta a la ruta real

die(){ echo "X $*" >&2; exit 1; }

# 0) Guards: pcap en sitio, log existe, ml-detector vivo y verbose
vagrant ssh client   -c "test -f $PCAP"  || die "pcap ausente en $PCAP"
vagrant ssh $MLGUEST -c "test -f $MLLOG" || die "log del ml-detector ausente en $MLLOG (¿pipeline-start?)"
vagrant ssh $MLGUEST -c "pgrep -af ml-detector | grep -q -- --verbose" \
  || die "ml-detector no corre con --verbose -> las lineas de gate no se emiten (make pipeline-start VERBOSE=1)"

# 1) Invalidar el log EN SITIO (pipeline vivo -> truncate, NUNCA mv/logs-lab-clean)   [INVARIANTE DAY270]
vagrant ssh $MLGUEST -c "truncate -s 0 $MLLOG"
echo "OK log del ml-detector truncado en sitio (inodo/fd O_APPEND preservado)"

# 2) DRIVER: replay del flood capado a $PPS. --stats para ver drops de tcpreplay.
echo "-- tcpreplay flood @${PPS}pps (403k paquetes; ~$((403000/PPS))s) --"
vagrant ssh client -c "sudo tcpreplay -i eth1 --pps=$PPS --stats=5 $PCAP" || die "tcpreplay fallo"
echo "-- drenaje ${DRAIN}s --"; sleep "$DRAIN"

# 3) MEDICION DE COMPUERTA (los contadores de DAY270 sobre el log recien truncado)
echo ""; echo "======== COMPUERTA level1->level2 (flood CIC _0125) ========"
N=$(vagrant ssh $MLGUEST -c "grep -c 'Feature Extraction:' $MLLOG" | tr -d '\r')
GATE=$(vagrant ssh $MLGUEST -c "grep -c 'Running Level 2 DDoS' $MLLOG" | tr -d '\r')
FLAG=$(vagrant ssh $MLGUEST -c "grep -c 'DDoS: class=1' $MLLOG" | tr -d '\r')
echo "N (bloques Feature Extraction) : $N"
echo "Pasaron la compuerta (L2 DDoS) : $GATE"
echo "Marcados DDoS (class=1)        : $FLAG"
echo "-- filtrado por victima $VIC_IP (si las lineas llevan 5-tupla) --"
vagrant ssh $MLGUEST -c "grep 'Running Level 2 DDoS' $MLLOG | grep -c '$VIC_IP'" 2>/dev/null || true
echo "============================================================"
echo "LECTURA: GATE alto -> la compuerta deja pasar floods, Fase 2 importa."
echo "         GATE ~0    -> la P0 es level1; ningun trabajo en la cabeza lo arregla."