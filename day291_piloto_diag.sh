#!/usr/bin/env bash
# DAY291 — diagnóstico del piloto: filas por origen x event_kind x (victim_pps<0), con destino.
# Uso: day291_piloto_diag.sh CSV
set -eu
F=${1:?csv}
LC_ALL=C awk -F, '
NR==1 { next }
$3=="192.168.100.50" || $3=="192.168.100.51" {
  cls=($3=="192.168.100.50" && $5=="123") ? "ATQ_50_sport123" : ($3=="192.168.100.51" ? "BASE_51" : "OTRO_50")
  sent=($16+0<0) ? "centinela" : "vivo"
  k=cls" dst="$4" proto="$7" kind="$8" "sent; n[k]++
}
END { for (k in n) printf "%-70s %d\n", k, n[k] }' "$F" | LC_ALL=C sort
