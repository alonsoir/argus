#!/usr/bin/env bash
# DAY297 D15 A1/A2: contabilidad. Cable (pcap de tcpdump en eth2) frente a resumenes, registros de la sombra y
# contadores de secuencia [TIMEBASE-SEQ-D297] del firewall; fraccion de DROP por origen sobre sus paquetes de ataque
# (udp src port 123). Solo lectura. Uso: a1_contabilidad.sh [pcap] [log_firewall]
set -u
P=${1:-/tmp/d297_a1.pcap}
L=${2:-/vagrant/logs/lab/firewall-agent.log}
ORIG="192.168.100.50 192.168.100.51 192.168.100.61"
echo "== cable: $P"
ATQ=""
for s in $ORIG; do
  n=$(tcpdump -n -r "$P" "src host $s" 2>/dev/null | wc -l)
  a=$(tcpdump -n -r "$P" "src host $s and udp and src port 123" 2>/dev/null | wc -l)
  echo "src $s paquetes=$n ataque_udp_sport123=$a"
  ATQ="$ATQ $s:$a"
done
echo "total=$(tcpdump -n -r "$P" 2>/dev/null | wc -l)"
echo "== firewall: configuracion activa"
grep -E '\[SOMBRA-DDOS\] pol' "$L" | tail -n 1
grep -E '\[CONFIG-DEFAULT\]' "$L" || echo "sin [CONFIG-DEFAULT]"
echo "== firewall: suma de resumenes [SOMBRA-DDOS] ($L)"
SUMA=$(grep -F '[SOMBRA-DDOS] resumen:' "$L" | LC_ALL=C awk '
  { for (i = 1; i <= NF; i++) { if (split($i, kv, "=") == 2) s[kv[1]] += kv[2] } n++ }
  END { printf "resumenes=%d eventos=%d flujo=%d DROP=%d ALLOW=%d otro_o_vacio=%d",
        n, s["eventos"], s["flujo"], s["DROP"], s["ALLOW"], s["otro_o_vacio"] }')
echo "$SUMA"
echo "== firewall: resumenes con flujo>0"
grep -F '[SOMBRA-DDOS] resumen:' "$L" | LC_ALL=C awk '
  { for (i = 1; i <= NF; i++) { if (split($i, kv, "=") == 2) v[kv[1]] = kv[2] }
    if (v["flujo"] + 0 > 0)
      printf "eventos=%s flujo=%s DROP=%s ALLOW=%s otro=%s ts_min=%s ts_max=%s\n",
             v["eventos"], v["flujo"], v["DROP"], v["ALLOW"], v["otro_o_vacio"], v["ts_evento_min"], v["ts_evento_max"] }'
echo "== registros de la sombra"
grep -E '\[SOMBRA-DDOS\] (INICIO|FIN|primer DROP)' "$L"
echo "== DROP por origen (suma de los FIN) frente a sus paquetes de ataque en el cable"
grep -E '\[SOMBRA-DDOS\] FIN ' "$L" | LC_ALL=C awk -v atq="$ATQ" '
  BEGIN { n = split(atq, xs, " "); for (i = 1; i <= n; i++) { split(xs[i], kv, ":"); cab[kv[1]] = kv[2] } }
  { for (i = 1; i <= NF; i++) if ($i ~ /^origenes=/) {
      sub(/^origenes=/, "", $i); m = split($i, os, ",")
      for (j = 1; j <= m; j++) { split(os[j], kv, ":"); d[kv[1]] += kv[2] } } }
  END { for (ip in cab) printf "origen %s drop=%d ataque_cable=%d fraccion=%.4f\n", ip, d[ip], cab[ip],
                                (cab[ip] > 0 ? d[ip] / cab[ip] : 0) }'
echo "== secuencia [TIMEBASE-SEQ-D297]: numero de lineas y ultima"
echo "lineas=$(grep -c -F '[TIMEBASE] secuencia:' "$L")"
SEQ=$(grep -F '[TIMEBASE] secuencia:' "$L" | tail -n 1)
echo "$SEQ"
echo "detalles [TIMEBASE-SEQ]=$(grep -c -F '[TIMEBASE-SEQ] ' "$L")"
grep -F '[TIMEBASE-SEQ] ' "$L" | head -n 10
grep -F '[TIMEBASE-ANOMALIA] seq_invariante' "$L" | tail -n 1
echo "== identidad: seq_recibidos (ultima linea) frente a suma de eventos de los resumenes"
REC=$(echo "$SEQ" | LC_ALL=C awk '{ for (i = 1; i <= NF; i++) { if (split($i, kv, "=") == 2 && kv[1] == "seq_recibidos") print kv[2] } }')
EVT=$(echo "$SUMA" | LC_ALL=C awk '{ for (i = 1; i <= NF; i++) { if (split($i, kv, "=") == 2 && kv[1] == "eventos") print kv[2] } }')
echo "seq_recibidos=$REC suma_eventos=$EVT diferencia=$(( ${REC:-0} - ${EVT:-0} ))"
