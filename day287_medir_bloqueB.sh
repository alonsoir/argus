#!/usr/bin/env bash
# DAY287 2.1 — bloque B (UDP ~4 KB fragmentado) por el pipeline: P21, P22
set -u
export LC_ALL=C
OUT=/vagrant/logs/lab/day287/17_bloqueB.txt
DS=$(ls -1t /vagrant/logs/lab/ddos_dataset/ddos_dataset_*.csv | head -1)
{
echo "dataset=$DS"
echo "--- filas .50 -> .1 por kind y proto"
awk -F',' 'NR>1 && $3=="192.168.100.50" && $4=="192.168.100.1" { print "kind=" $8, "proto=" $7 }' "$DS" | sort | uniq -c
echo "--- P21: flujo, puertos 0 frente a puertos reales (kind=0)"
awk -F',' 'NR>1 && $3=="192.168.100.50" && $4=="192.168.100.1" && $8==0 { k = ($5==0 && $6==0) ? "puertos_0" : "con_puertos"; n[k]++ } END { for (k in n) print k, n[k] }' "$DS"
echo "--- rasgos medios en kind=0 con puertos (centinela -9999 excluido)"
awk -F',' 'NR>1 && $3=="192.168.100.50" && $4=="192.168.100.1" && $8==0 && $5!=0 {
  n++; ms+=$10; e+=$12; r+=$11; fp+=$13
  if ($16>-9000) { v++; vp+=$16; vr+=$15 }
  if ($18==1) c1++; else if ($18==0) c0++; else cn++
} END {
  if (n) printf "n=%d mean_size=%.1f entropy=%.3f refl=%.3f flow_pkts=%.1f class1=%d class0=%d no_eval=%d\n", n, ms/n, e/n, r/n, fp/n, c1, c0, cn
  if (v) printf "P22: con_ventana=%d victim_pps_medio=%.1f victim_rate_ratio_medio=%.2f\n", v, vp/v, vr/v
}' "$DS"
echo "--- 3 filas de ejemplo del flood"
awk -F',' 'NR>1 && $3=="192.168.100.50" && $4=="192.168.100.1" && $8==0' "$DS" | head -3
} > "$OUT" 2>&1
wc -l "$OUT"
