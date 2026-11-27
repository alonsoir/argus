#!/usr/bin/env bash
# DAY339 — DEBT-SNIFFER-IS-EXTERNAL-IP-BYTE-ORDER-001, medida 2: el bronce por día.
# La v1 dio 141 (SIGPIPE de head con pipefail) y un criterio "al revés" demasiado ancho.
# Aquí, por día de flow_start_sec (col 6), filas argus con dst_ip (col 9):
#   N = 192.168.x.x (orden bueno)   R = x.x.168.192 (el lab al revés)
#   S = otras con pinta de invertidas: 251.0.x.x, 255.56.x.x, x.x.0.224, x.x.56.255 (y no 192.168)
# Y las 20 dst_ip completas más frecuentes de R y S.
# Uso (Mac, raíz del repo): bash scripts/etcd_ha/d339_medir_orden_dst_ip_v2.sh logs/correlation
# Solo lee. El día sale como número de días desde 1970-01-01 (UTC); Claude lo convierte a fecha.
set -eu
export LC_ALL=C
DIR="${1:?falta el directorio del bronce}"
[ -d "$DIR" ] || { echo "no existe: $DIR"; exit 2; }

find "$DIR" -type f ! -name '*.gz' -print0 \
| xargs -0 awk -F, '
NF==19 && $2=="argus" {
  if (split($9,o,".")!=4) next
  d=int(($6+0)/86400)
  if (o[1]==192 && o[2]==168) { c["N " d]++; next }
  if (o[4]==192 && o[3]==168) { c["R " d]++; ip["R " $9]++; next }
  if ((o[1]==251 && o[2]==0) || (o[1]==255 && o[2]==56) || (o[4]==224 && o[3]==0) || (o[4]==255 && o[3]==56)) {
    c["S " d]++; ip["S " $9]++
  }
}
END { for (k in c) print "C", k, c[k]; for (k in ip) print "I", k, ip[k] }' \
| awk '
$1=="C" { n[$2 " " $3]+=$4; dias[$3]=1; t[$2]+=$4; next }
$1=="I" { i[$2 " " $3]+=$4; next }
END {
  printf "totales: N %d  R %d  S %d\n", t["N"], t["R"], t["S"]
  print "== dia N R S"
  for (d in dias) printf "D %s %d %d %d\n", d, n["N " d], n["R " d], n["S " d]
  print "== ip (filas, grupo, dst_ip)"
  for (k in i) { split(k,p," "); printf "I %d %s %s\n", i[k], p[1], p[2] }
}' > "${TMPDIR:-/tmp}/d339_v2_bruto.txt"

B="${TMPDIR:-/tmp}/d339_v2_bruto.txt"
sed -n '1p' "$B"
echo "== dia N R S (dias epoch UTC)"
awk '$1=="D"' "$B" | sort -k2,2n | sed 's/^D //'
echo "== top 20 dst_ip de R y S (filas grupo ip)"
awk '$1=="I"' "$B" | sort -k2,2rn | sed -n '1,20p' | sed 's/^I //'
