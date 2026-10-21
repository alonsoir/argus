#!/usr/bin/env bash
# DAY298 Analisis de una corrida de arranque en frio (lab_frio.sh): trafico hacia .1 en el cable (por origen y
# pico de pps en segundos de 1 s) y lo que vio la etapa 1 en el dataset del ml-detector (filas hacia .1,
# pico de victim_pps, filas con victim_rate_ratio >= 3 = pases de la etapa 1). Uso: d298_frio_analisis.sh DIR
set -eu
D=${1:?directorio de la corrida}
N=$(basename "$D")
P="$D/$N.pcap"
C=$(ls -t "$D"/ddos_dataset_*.csv 2>/dev/null | head -n 1)
[ -f "$P" ] || { echo "ABORTA: no existe $P"; exit 1; }
[ -n "$C" ] || { echo "ABORTA: no hay dataset en $D"; exit 1; }
echo "== tiempos"; cat "$D/tiempos.txt"
echo "== cable hacia .1: paquetes por origen"
sudo tcpdump -nn -tt -r "$P" 2>/dev/null | LC_ALL=C awk '{s=$3; n=split(s,a,"."); ip=a[1]"."a[2]"."a[3]"."a[4]; c[ip]++} END{for(k in c) printf "  %-16s %d\n", k, c[k]}' | sort -k2 -n -r
echo "== cable hacia .1: los 5 segundos con mas paquetes (epoch, paquetes)"
sudo tcpdump -nn -tt -r "$P" 2>/dev/null | LC_ALL=C awk '{s=int($1); c[s]++} END{for(k in c) print k, c[k]}' | sort -k2 -n -r | head -n 5
echo "== dataset: $C"
LC_ALL=C awk -F, 'NR>1 && $4=="192.168.100.1" {n++; if($15+0>=3) p++; if($16+0>m) m=$16+0; if(n==1) t0=$1}
  END{printf "filas_hacia_.1=%d primera_ts_ns=%s max_victim_pps=%.3f filas_ratio_ge_3=%d\n", n, t0, m, p}' "$C"
echo "== dataset: filas con ratio >= 3 hacia .1 (las 10 primeras)"
LC_ALL=C awk -F, 'NR>1 && $4=="192.168.100.1" && $15+0>=3 {print "  ts_ns="$1" src="$3" proto="$7" ratio="$15" pps="$16}' "$C" | head -n 10
