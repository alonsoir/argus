#!/usr/bin/env bash
# DAY288 — control de calidad de una corrida sobre ddos_windows.csv.
# Uso: day288_qa_corrida.sh MARCA PPS_ESPERADO PROTO   (PROTO 17 UDP, 6 TCP)
# Ventanas de ataque = victima .1/PROTO con pps >= R/2. ACEPTADA si, entre la primera y la ultima,
# ningun sondeo (cualquier clave) pasa de 1500 ms y el pps de ataque queda en [0,5R, 1,5R].
set -eu
export LC_ALL=C
W=/vagrant/logs/lab/ddos_windows.csv
M=${1:?marca}; R=${2:?pps}; P=${3:?proto}
tail -n +"$((M+1))" "$W" | awk -F',' -v R="$R" -v P="$P" '
  { ts[NR]=$2+0; wm[NR]=$3+0; win[NR]=$1 }
  ($4=="192.168.100.1" || $4=="3232261121" || $4=="23374016") && $5==P && $3>0 {
    pps=$6*1000/$3
    if (pps >= R/2) { na++; if (t0=="") t0=$2+0; t1=$2+0
      if (mn=="" || pps<mn) mn=pps; if (pps>mx) mx=pps }
  }
  END {
    for (i=1; i<=NR; i++) if (ts[i]>=t0 && ts[i]<=t1 && !s[win[i]]++ && wm[i]>wmx) wmx=wm[i]
    ok = (na>0 && wmx<=1500 && mn>=0.5*R && mx<=1.5*R)
    printf "ventanas_ataque=%d duracion_s=%.1f pps_min=%.1f pps_max=%.1f max_window_ms=%d -> %s\n",
           na, (t1-t0)/1000, mn, mx, wmx, ok ? "ACEPTADA" : "RECHAZADA"
  }'
