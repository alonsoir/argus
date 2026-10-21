#!/usr/bin/env bash
# DAY298 1.a: 5-tuplas distintas y paquetes por tupla en un pcap UDP (sin arrancar nada).
# Uso: d298_tuplas_pcap.sh PCAP
set -eu
P=${1:?pcap}
sudo tcpdump -nn -q -r "$P" udp 2>/dev/null \
 | LC_ALL=C awk '{print $3, $5}' \
 | LC_ALL=C sort | LC_ALL=C uniq -c \
 | LC_ALL=C awk '{n++; p+=$1; if($1>m)m=$1; if($1==1)u++} END{printf "paquetes_udp=%d tuplas=%d fpk_medio=%.3f max_pk_tupla=%d tuplas_1pk=%d\n",p,n,p/n,m,u}'
