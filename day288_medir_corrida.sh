#!/usr/bin/env bash
# DAY288 — medida de una corrida del dataset. Uso: day288_medir_corrida.sh FICHERO TAG
# Filas .50 -> .1. Columnas: 5 sport 6 dport 7 proto 8 kind 9 syn_ack 10 mean_size 11 refl
# 12 entropy 13 flow_pkts 14 completion 15 victim_rate_ratio 16 victim_pps 18 old_class
set -eu
export LC_ALL=C
F=/vagrant/logs/lab/ddos_dataset/${1:?fichero}
TAG=${2:?tag}
OUT=/vagrant/logs/lab/day288/medida_${TAG}.txt
awk -F',' -v f="$(basename "$F")" -v tag="$TAG" '
  NR==FNR { if (FNR>1 && $3=="192.168.100.50" && $4=="192.168.100.1" && $8==0) {
              if (tmin=="" || $1+0<tmin) tmin=$1+0; if ($1+0>tmax) tmax=$1+0 }
            next }
  FNR==1 {next}
  $3=="192.168.100.50" && $4=="192.168.100.1" {
    if ($8==1) { k1++; next }
    k0++; cid[$2]=1
    if ($9<=-9000) { hueco++; next }
    ok++; sa+=$9; ms+=$10; rf+=$11; en+=$12; fp+=$13; fc+=$14
    if ($13>fpmax) fpmax=$13
    if ($15>-9000) { vr+=$15; vrn++ }
    if ($16>-9000) { vp+=$16; vpn++
      if ($1+0 >= tmin+(tmax-tmin)/2) { vp2+=$16; vp2n++ } }
    oc[$18]++
  }
  END {
    printf "tag=%s fichero=%s\n", tag, f
    printf "kind0=%d kind1=%d huecos_flujo=%d con_rasgos=%d flujos=%d duracion_s=%.1f\n", k0, k1, hueco+0, ok, length(cid), (tmax-tmin)/1e9
    if (ok>0) printf "medias: syn_ack=%.3f mean_size=%.1f refl=%.3f entropy=%.3f flow_pkts=%.2f (max %d) completion=%.3f\n", sa/ok, ms/ok, rf/ok, en/ok, fp/ok, fpmax, fc/ok
    if (vrn>0) printf "victima: rate_ratio=%.3f victim_pps=%.1f victim_pps_2a_mitad=%.1f\n", vr/vrn, vp/vpn, (vp2n>0 ? vp2/vp2n : -1)
    printf "old_class:"; for (x in oc) printf " %s=%d", x, oc[x]; print ""
  }' "$F" "$F" > "$OUT"
cat "$OUT"
