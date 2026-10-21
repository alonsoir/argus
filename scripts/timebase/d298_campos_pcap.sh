#!/usr/bin/env bash
# DAY298 1.a: cardinalidad de cada campo de la 5-tupla en un pcap UDP (de donde sale la variedad de tuplas).
# Uso: d298_campos_pcap.sh PCAP
set -eu
P=${1:?pcap}
sudo tcpdump -nn -q -r "$P" udp 2>/dev/null \
 | LC_ALL=C awk '{ s=$3; d=$5; sub(/:$/,"",d)
     split(s,a,"."); split(d,b,".")
     sip=a[1]"."a[2]"."a[3]"."a[4]; sp=a[5]; dip=b[1]"."b[2]"."b[3]"."b[4]; dp=b[5]
     SIP[sip]++; SP[sp]++; DIP[dip]++; DP[dp]++; n++ }
   END{ c=0; for(k in SIP)c++; printf "paquetes=%d ip_origen=%d", n, c
        c=0; for(k in SP)c++;  printf " puerto_origen=%d", c
        c=0; for(k in DIP)c++; printf " ip_destino=%d", c
        c=0; for(k in DP)c++;  printf " puerto_destino=%d\n", c
        for(k in SIP) if(SIP[k]>n/10) printf "  ip_origen dominante %s %d\n", k, SIP[k]
        for(k in DIP) if(DIP[k]>n/10) printf "  ip_destino dominante %s %d\n", k, DIP[k]
        for(k in SP)  if(SP[k]>n/10)  printf "  puerto_origen dominante %s %d\n", k, SP[k]
        for(k in DP)  if(DP[k]>n/10)  printf "  puerto_destino dominante %s %d\n", k, DP[k] }'
