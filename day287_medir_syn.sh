#!/usr/bin/env bash
# DAY287 2.2 — SYN flood del lab por el pipeline
set -u
export LC_ALL=C
OUT=/vagrant/logs/lab/day287/25_syn.txt
DS=$(ls -1t /vagrant/logs/lab/ddos_dataset/ddos_dataset_*.csv | head -1)
{
echo "dataset=$DS"
echo "--- filas .50 -> .1:80 TCP por kind"
awk -F',' 'NR>1 && $3=="192.168.100.50" && $4=="192.168.100.1" && $6==80 && $7==6 { print "kind=" $8 }' "$DS" | sort | uniq -c
echo "--- rasgos medios (kind=0, TCP a :80)"
awk -F',' 'NR>1 && $3=="192.168.100.50" && $4=="192.168.100.1" && $6==80 && $7==6 && $8==0 {
  n++; sa+=$9; ms+=$10; r+=$11; fp+=$13; co+=$14
  if ($18==1) c1++; else if ($18==0) c0++; else cn++
} END { if (n) printf "n=%d syn_ack=%.3f mean_size=%.1f refl=%.3f flow_pkts=%.2f completion=%.3f class1=%d class0=%d no_eval=%d\n", n, sa/n, ms/n, r/n, fp/n, co/n, c1, c0, cn }' "$DS"
echo "--- 3 filas de ejemplo"
awk -F',' 'NR>1 && $3=="192.168.100.50" && $4=="192.168.100.1" && $6==80 && $7==6 && $8==0' "$DS" | head -3
} > "$OUT" 2>&1
wc -l "$OUT"
