#!/usr/bin/env bash
# DAY291 — secuencia de (ratio, pps) por ventana alrededor del inicio del ataque.
# Imprime una línea cada vez que cambia el par (los eventos de una misma ventana lo repiten).
# Uso: day291_ventanas.sh CSV [segundos_tras_t0]
set -eu
F=${1:?csv}
S=${2:-25}
LC_ALL=C awk -F, -v S="$S" '
NR==1 || $8!="0" || $4!="192.168.100.1" { next }
!($3=="192.168.100.51" || ($3=="192.168.100.50" && $5=="123")) { next }
{ m++; ts[m]=$1; rr[m]=$15; pp[m]=$16 }
$3=="192.168.100.50" && t0=="" { t0=$1 }
END {
  for (i=1;i<=m;i++) {
    d=(ts[i]-t0)/1e9
    if (d < -3 || d > S) continue
    k=rr[i]" "pp[i]
    if (k!=last) { printf "%+7.2f s  ratio=%-8s pps=%s\n", d, rr[i], pp[i]; last=k }
  }
}' "$F"
