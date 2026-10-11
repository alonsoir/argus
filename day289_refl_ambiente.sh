#!/usr/bin/env bash
# DAY289 §4.1 — filas de AMBIENTE (todo lo que NO es 192.168.100.50→192.168.100.1)
# con event_kind=0 y rasgos (syn_ack_ratio > -9000): cuántas traen reflection_signature=1
# y cuánto benigno UDP hay. Solo lectura sobre los CSV listados en runs.tsv.
set -eu
export LC_ALL=C
RUNS=/vagrant/logs/lab/day288/runs.tsv
DIR=/vagrant/logs/lab/ddos_dataset
OUT=/vagrant/logs/lab/day289
CAB="$OUT/cabecera.txt"
RES="$OUT/ambiente_resumen.tsv"
FIL="$OUT/ambiente_filas.tsv"

[ -f "$RUNS" ] || { echo "PARAR: falta $RUNS"; exit 1; }
[ -f "$CAB" ]  || { echo "PARAR: falta $CAB"; exit 1; }

STAMPS=$(grep -owE '[0-9]{6}' "$RUNS" | sort -u)
N=$(printf '%s\n' "$STAMPS" | grep -c . || true)
echo "corridas en runs.tsv: $N (esperadas 19)"
[ "$N" -eq 19 ] || { echo "PARAR: no son 19"; printf '%s\n' "$STAMPS"; exit 1; }

printf 'fichero\tfilas\tambiente\tamb_kind0\tamb_con_rasgos\tamb_udp\tamb_refl1\n' > "$RES"
printf 'fichero\tsrc_ip\tsrc_port\tdst_ip\tdst_port\tproto\trefl\tmean_size\tflow_pkts\n' > "$FIL"

for S in $STAMPS; do
  F="$DIR/ddos_dataset_20261005-$S.csv"
  [ -f "$F" ] || { echo "PARAR: falta $F"; exit 1; }
  head -1 "$F" | cmp -s - "$CAB" || { echo "PARAR: cabecera distinta en $F"; exit 1; }
  awk -F, -v f="$S" -v fil="$FIL" '
    NR==1 {next}
    {tot++}
    $3=="192.168.100.50" && $4=="192.168.100.1" {next}
    {amb++}
    $8+0 != 0 {next}
    {amb0++}
    $9+0 <= -9000 {next}
    {ambf++
     if ($7+0==17) udp++
     if ($11+0==1) refl++
     printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n", f,$3,$5,$4,$6,$7,$11,$10,$13 >> fil}
    END {printf "%s\t%d\t%d\t%d\t%d\t%d\t%d\n", f,tot,amb,amb0,ambf,udp,refl}
  ' "$F" >> "$RES"
done

echo "== resumen por corrida =="
cat "$RES"
echo
echo "== totales =="
awk -F'\t' 'NR>1{t+=$2;a+=$3;k+=$4;r+=$5;u+=$6;f+=$7} END{printf "filas=%d ambiente=%d amb_kind0=%d amb_con_rasgos=%d amb_udp=%d amb_refl1=%d\n",t,a,k,r,u,f}' "$RES"
echo
echo "== ambiente con rasgos por (src_ip, sport, dst_ip, dport, proto, refl); puertos >=1024 = alto; top 25 =="
awk -F'\t' 'NR>1{sp=($3+0>=1024)?"alto":$3; dp=($5+0>=1024)?"alto":$5; print $2"\t"sp"\t"$4"\t"dp"\t"$6"\t"$7}' "$FIL" | sort | uniq -c | sort -rn | head -25
