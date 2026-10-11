#!/usr/bin/env bash
# DAY287 — verificacion del escritor de dataset DDoS v2 (P10-P12)
set -u
export LC_ALL=C
OUT=/vagrant/logs/lab/day287
MARKER=$OUT/run_marker
DS=$(ls -1t /vagrant/logs/lab/ddos_dataset/ddos_dataset_*.csv 2>/dev/null | head -1)
[ -n "$DS" ] || { echo "sin dataset" > "$OUT/09_dataset.txt"; exit 1; }
{
echo "dataset=$DS"
echo "sha256=$(sha256sum "$DS" | cut -d' ' -f1)"
echo "filas_datos=$(( $(wc -l < "$DS") - 1 ))"
echo "--- P10: NF por fila (esperado: todas 18)"
awk -F',' 'NR>1{print NF}' "$DS" | sort -n | uniq -c
echo "--- event_kind x old_ddos_class"
awk -F',' 'NR>1{print "kind="$8, "class="$18}' "$DS" | sort | uniq -c
echo "--- P11: con community_id vs filas de correlacion de la corrida"
awk -F',' 'NR>1 && $2!=""{n++} END{print "dataset_con_cid="n+0}' "$DS"
echo "ficheros_correlacion:"
find /vagrant/logs/correlation -type f -newer "$MARKER" | sort
echo "correlacion_filas=$(find /vagrant/logs/correlation -type f -newer "$MARKER" -exec cat {} + | wc -l)"
echo "--- P12: flood 192.168.100.50 -> 192.168.100.1 UDP, kind=0"
awk -F',' 'NR>1 && $3=="192.168.100.50" && $4=="192.168.100.1" && $7==17 && $8==0 {n++; s+=$10; e+=$12; if($18==1)c1++; if($18==0)c0++; if($18<0)cn++} END{if(n) printf "n=%d mean_size=%.1f entropy=%.3f class1=%d class0=%d no_eval=%d\n", n, s/n, e/n, c1, c0, cn; else print "n=0"}' "$DS"
echo "--- cabecera + 3 filas"
head -4 "$DS"
} > "$OUT/09_dataset.txt" 2>&1
wc -l "$OUT/09_dataset.txt"
