#!/usr/bin/env bash
# DAY339 — DEBT-SNIFFER-IS-EXTERNAL-IP-BYTE-ORDER-001: medida con eventos reales del sniffer.
#
# El bronce correlation_v1 pinta dst_ip (col 9) con ip_host_to_buffer(event.dst_ip) = inet_ntop(htonl(v)).
# Es el MISMO SimpleEvent que process_raw_event pasa a fast_detector_.ingest() y a
# ransomware_processor_->process_packet() (ring_consumer.cpp:665, :774, :787 -> :800).
# Si el texto es a.b.c.d, entonces v = a<<24|b<<16|c<<8|d, que es lo que compara is_external_ip.
# Con el orden invertido, las IPs del lab aparecerían al revés (p. ej. 20.100.168.192).
#
# Uso (en el Mac, raíz del repo): bash scripts/etcd_ha/d339_medir_orden_dst_ip.sh logs/correlation
# Solo lee. Sale con 0 si hay filas de argus y ninguna con un privado "al revés"; 1 si no; 2 si no hay datos.
set -euo pipefail
export LC_ALL=C
DIR="${1:?falta el directorio del bronce}"
[ -d "$DIR" ] || { echo "no existe: $DIR"; exit 2; }

GZ=$(find "$DIR" -type f -name '*.gz' | wc -l | tr -d ' ')
echo "ficheros .gz (no leídos): $GZ"
echo "ficheros leídos: $(find "$DIR" -type f ! -name '*.gz' | wc -l | tr -d ' ')"

find "$DIR" -type f ! -name '*.gz' -print0 | xargs -0 cat | awk -F, '
function priv(a,b){ return a==10 || (a==172 && b>=16 && b<=31) || (a==192 && b==168) || a==127 || (a==169 && b==254) }
NF==19 && $2=="argus" {
  n=split($9,o,".")
  if (n!=4) { mal++; next }
  filas++
  pref[o[1] "." o[2] ".x.x"]++
  # is_external_ip sobre v=a<<24|b<<16|c<<8|d (lo que pinta el bronce)
  if (priv(o[1]+0,o[2]+0)) interna++; else externa++
  # el mismo texto leído al revés: si fuera el orden real, su primer octeto sería o[4]
  if (priv(o[4]+0,o[3]+0) && !priv(o[1]+0,o[2]+0)) alreves++
}
END {
  printf "filas argus: %d (dst_ip no IPv4: %d)\n", filas, mal
  printf "is_external_ip con el orden del bronce: internas %d, externas %d\n", interna, externa
  printf "privadas solo si se leen al reves: %d\n", alreves
  print "prefijos de dst_ip (filas, prefijo):"
  for (k in pref) printf "%d %s\n", pref[k], k
  if (filas==0) exit 2
  exit (alreves>0 ? 1 : 0)
}' | { IFS= read -r a; echo "$a"; IFS= read -r b; echo "$b"; IFS= read -r c; echo "$c"; IFS= read -r d; echo "$d"; sort -rn | head -15; }
exit "${PIPESTATUS[2]}"
