#!/usr/bin/env bash
# DAY306 — Inventario de la cabeza DDoS v1 (DEBT-DDOS-V1-RETIRE-001).
# SOLO LECTURA: no escribe nada en el repo. Usa git grep (solo ficheros trackeados).
# Mide quién NOMBRA cada símbolo (fichero y nº de apariciones, por clase) y, en los
# puntos clave, QUIÉN LO USA (líneas con contexto: proto, JSON, CMake/Makefile,
# zmq_handler, heads_config, recolector del sniffer).
# Ejecutar en el Mac, desde cualquier punto del repo.
set -u
export LC_ALL=C
cd "$(git rev-parse --show-toplevel)" || exit 1

TMP="/tmp/d306_cuenta.$$"
NODOC=(':(exclude)docs' ':(exclude)*.md' ':(exclude)*.txt')

echo "== HEAD $(git rev-parse --short HEAD)  rama $(git rev-parse --abbrev-ref HEAD)  $(date '+%Y-%m-%d %H:%M:%S')"

seccion() { echo; echo "=================== $1"; }

# cuenta PATRON ETIQUETA: ficheros que nombran el patrón, clasificados.
cuenta() {
  local pat="$1" etq="$2" salida
  seccion "$etq   /$pat/"
  salida=$(git grep -I -c -E "$pat" -- . 2>/dev/null)
  if [ -z "$salida" ]; then echo "  (0 ficheros)"; return; fi
  echo "$salida" | awk -F: '{
      f=$1; n=$NF
      if (f ~ /\.pb\.(h|cc)$/ || f ~ /_pb2\.py$/)                 cls="GEN"
      else if (f ~ /(\.backup|\.bak|\.v1\.0|\.day[0-9]+$)/)       cls="RESIDUO"
      else if (f ~ /\.(md|txt)$/ || f ~ /^docs\//)                cls="DOC"
      else if (f ~ /^ml-training\//)                              cls="TRAIN"
      else if (f ~ /(^|\/)tests?\//)                              cls="TEST"
      else                                                        cls="CODIGO"
      printf "  %-8s %5d  %s\n", cls, n, f }' | sort -k1,1 -k3,3 > "$TMP"
  cat "$TMP"
  awk '{tot+=$2; c[$1]+=$2; nf++}
       END{printf "  -- %d ficheros, %d apariciones;", nf, tot
           for (k in c) printf " %s=%d", k, c[k]; print ""}' "$TMP"
  rm -f "$TMP"
}

# lineas PATRON ETIQUETA [pathspec...]: líneas exactas, sin docs.
lineas() {
  local pat="$1" etq="$2"; shift 2
  seccion "LINEAS $etq   /$pat/"
  if [ "$#" -gt 0 ]; then
    git grep -I -n -E "$pat" -- "$@" "${NODOC[@]}" 2>/dev/null || echo "  (nada)"
  else
    git grep -I -n -E "$pat" -- . "${NODOC[@]}" 2>/dev/null || echo "  (nada)"
  fi
}

echo
echo "############ A. ml-detector — piezas de la cabeza v1"
cuenta 'DDoSDetector'                          'A1 clase DDoSDetector'
cuenta 'ddos_detector\.(hpp|cpp|h)'            'A2 ficheros ddos_detector'
cuenta 'ddos_trees_inline'                     'A3 bosque v1 embebido'
cuenta 'DDOS_NUM_FEATURES'                     'A4 cardinalidad v1'
cuenta 'extract_level2_ddos_features'          'A5 extractor v1 del ml-detector'
cuenta 'l2_gate|force_all_heads|FORCE_ALL_HEADS|force-all-heads' 'A6 compuerta level1->level2 y su flag'
cuenta 'test_detectors'                        'A7 test que compila v1'
cuenta 'ddos_prob'                             'A8 salida v1 en logs'
cuenta 'level2[._]ddos|level2\.ddos|Level 2 DDoS' 'A9 nombre level2.ddos'
cuenta 'ddos_predict'                          'A10 muñón generate_ddos_inline'

echo
echo "############ B. Rasgos v1 (los 7 a retirar)"
cuenta 'packet_symmetry'                       'B1'
cuenta 'source_ip_dispersion'                  'B2 (OJO: posible 2.º significado en ransomware)'
cuenta 'protocol_anomaly'                      'B3'
cuenta 'amplification'                         'B4'
cuenta 'geographical_concentration'            'B5'
cuenta 'traffic_escalation|escalation_rate'    'B6'
cuenta 'resource_saturation|saturation_score'  'B7'
cuenta 'extract_ddos_features'                 'B8 productor v1 en el sniffer'

echo
echo "############ C. Rasgos de ddos_v2 (DEBEN SOBREVIVIR: solo se cuentan)"
cuenta 'syn_ack_ratio'                         'C1 compartido v1/v2'
cuenta 'packet_size_entropy'                   'C2 compartido v1/v2'
cuenta 'flow_completion_rate'                  'C3 compartido v1/v2'
cuenta 'mean_packet_size|reflection_signature|flow_packet_count|victim_rate_ratio|victim_pps' 'C4 campos 11-15 v2'
cuenta 'ddos_embedded'                         'C5 submensaje que lee v2'

echo
echo "############ D. Quién USA (líneas exactas en los puntos clave)"
seccion "D1 proto: mensaje DDoSFeatures completo"
git grep -I -n -A60 'message DDoSFeatures' -- '*.proto' 2>/dev/null \
  | awk '{print} /^[^:]+-[0-9]+-\}/{exit}' || echo "  (nada)"
lineas 'DDoSFeatures' 'D2 proto: dónde se usa el submensaje' '*.proto'
seccion "D3 JSON: bloques \"ddos\" (clave exacta) con 40 líneas de contexto"
git grep -I -n -A40 -E '"ddos"[[:space:]]*:' -- '*.json' 2>/dev/null || echo "  (nada)"
lineas 'ddos_detector|ddos_trees_inline|test_detectors|l2_gate|FORCE_ALL_HEADS|force.all.heads' \
       'D4 build: CMake / Makefile' '*CMakeLists.txt' '*.cmake' 'Makefile' '*.mk'
lineas 'DDoSDetector|ddos_detector|extract_level2_ddos_features|l2_gate|force_all_heads|ddos_prob|level2' \
       'D5 ml-detector/src (zmq_handler, main, ...)' 'ml-detector/src' 'ml-detector/include'
lineas '[Dd][Dd][Oo][Ss]' 'D6 heads_config (cabezas y nombres)' '*heads_config*'
lineas 'packet_symmetry|source_ip_dispersion|protocol_anomaly|amplification|geographical_concentration|escalation|saturation' \
       'D7 sniffer: recolector de rasgos v1' 'sniffer'
lineas 'source_ip_dispersion' 'D8 source_ip_dispersion fuera del sniffer' 'ml-detector' 'firewall-acl-agent' 'correlation-engine' 'libs'

echo
echo "############ E. Ficheros candidatos por nombre (trackeados)"
git ls-files | grep -i -E 'ddos' | grep -v -E '^docs/' | sort

echo
echo "== FIN inventario DAY306"
