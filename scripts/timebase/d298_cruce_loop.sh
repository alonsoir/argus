#!/usr/bin/env bash
# DAY298 1.a: con tcpreplay --pps P --loop, el paquete i sale en i/P s. Para cada tupla con >1 paquete,
# hueco al cruzar la vuelta = (primera + N - ultima)/P s. Si es <= T (timeout de flujo) el flujo NO caduca
# entre vueltas y flow_packet_count crece. Tambien cuenta huecos internos > T (flujo partido ya en una vuelta).
# Uso: d298_cruce_loop.sh PCAP PPS TIMEOUT_S
set -eu
P=${1:?pcap}; PPS=${2:?pps}; T=${3:?timeout_s}
sudo tcpdump -nn -q -r "$P" udp 2>/dev/null \
 | LC_ALL=C awk -v pps="$PPS" -v T="$T" '
   { k=$3" "$5; i=NR; n++
     if(!(k in f)){f[k]=i; c[k]=0} else { g=(i-l[k])/pps; if(g>T) partidos++ }
     l[k]=i; c[k]++ }
   END{ for(k in c){ if(c[k]<2) continue; multi++; pm+=c[k]
          w=(f[k]+n-l[k])/pps; if(w<=T){ cruza++; pc+=c[k] } if(w<mn||mn=="")mn=w }
        printf "N=%d pps=%d T=%d tuplas_multi=%d paquetes_multi=%d no_caducan_en_cruce=%d paquetes_afectados=%d (%.2f%%) hueco_cruce_min_s=%.2f huecos_internos_gt_T=%d\n",
               n,pps,T,multi,pm,cruza,pc,100*pc/n,mn,partidos }'
