#!/usr/bin/env bash
# DAY289 — consolidación del dataset DDoS v2. Solo lectura sobre las fuentes.
# Corrida (.50→.1): kind=0, syn_ack_ratio>-9000, proto según familia (benign: TCP dport 9000).
# Ambiente (no .50→.1): kind=0 con rasgos, etiqueta benigno, familia "ambiente".
set -eu
export LC_ALL=C
RUNS=/vagrant/logs/lab/day288/runs.tsv
DIR=/vagrant/logs/lab/ddos_dataset
OUT=/vagrant/logs/lab/day289
CAB="$OUT/cabecera.txt"
CSV="$OUT/consolidado.csv"
EST="$OUT/consolidado_por_corrida.tsv"
MAN="$OUT/manifiesto.sha256"

[ -f "$RUNS" ] || { echo "PARAR: falta $RUNS"; exit 1; }
[ -f "$CAB" ]  || { echo "PARAR: falta $CAB"; exit 1; }

printf '%s,etiqueta,familia,tasa,fichero\n' "$(cat "$CAB")" > "$CSV.tmp"
printf 'fichero\tfamilia\ttasa\tfilas\tcorr_kind0\tcorr_kind1\tcorr_sin_rasgos\tcorr_otro_proto\tcorr_ok\tamb_ok\n' > "$EST.tmp"
: > "$MAN.tmp"
N=0
while IFS= read -r LINEA; do
  S=$(printf '%s\n' "$LINEA" | grep -owE '[0-9]{6}' | head -1 || true)
  [ -n "$S" ] || continue
  set -- $LINEA
  FAM=$1; TASA=$2
  case "$FAM" in
    ntp|dns|udpA|udpB) PROTO=17; DPORT=any ;;
    syn)               PROTO=6;  DPORT=any ;;
    benign)            PROTO=6;  DPORT=9000 ;;
    *) echo "PARAR: familia desconocida en runs.tsv: $LINEA"; exit 1 ;;
  esac
  F="$DIR/ddos_dataset_20261005-$S.csv"
  [ -f "$F" ] || { echo "PARAR: falta $F"; exit 1; }
  head -1 "$F" | cmp -s - "$CAB" || { echo "PARAR: cabecera distinta en $F"; exit 1; }
  ETQ=ataque; [ "$FAM" = benign ] && ETQ=benigno
  awk -F, -v OFS=, -v fam="$FAM" -v tasa="$TASA" -v s="$S" -v proto="$PROTO" \
      -v dport="$DPORT" -v etq="$ETQ" -v csv="$CSV.tmp" '
    NR==1 {next}
    {tot++}
    $3=="192.168.100.50" && $4=="192.168.100.1" {
      if ($8+0 != 0) {k1++; next}
      k0++
      if ($9+0 <= -9000) {sr++; next}
      if ($7+0 != proto || (dport != "any" && $6+0 != dport+0)) {op++; next}
      ok++
      print $0, etq, fam, tasa, s >> csv
      next
    }
    $8+0 != 0 {next}
    $9+0 <= -9000 {next}
    {amb++; print $0, "benigno", "ambiente", "-", s >> csv}
    END {printf "%s\t%s\t%s\t%d\t%d\t%d\t%d\t%d\t%d\t%d\n", s,fam,tasa,tot,k0,k1,sr,op,ok,amb}
  ' "$F" >> "$EST.tmp"
  sha256sum "$F" >> "$MAN.tmp"
  N=$((N+1))
done < "$RUNS"
[ "$N" -eq 19 ] || { echo "PARAR: $N corridas, esperadas 19"; exit 1; }

sha256sum "$RUNS" >> "$MAN.tmp"
for P in /vagrant/datasets/lab/*.pcap /vagrant/scripts/dataset_lab/MANIFEST.md \
         /vagrant/datasets/cicddos2019/_0125_50k_lab.pcap /vagrant/datasets/cicddos2019/_0220_50k_lab.pcap; do
  if [ -f "$P" ]; then sha256sum "$P" >> "$MAN.tmp"; else echo "FALTA  $P" >> "$MAN.tmp"; fi
done
mv "$CSV.tmp" "$CSV"; mv "$EST.tmp" "$EST"; mv "$MAN.tmp" "$MAN"

echo "== por corrida =="
cat "$EST"
echo
echo "== P1 supervivencia (corr_ok / corr_kind0) =="
awk -F'\t' 'NR>1{printf "%s\t%s\t%s\t%.1f%%\n",$1,$2,$3,($5>0?100*$9/$5:0)}' "$EST"
echo
echo "== P2/P4 por familia y tasa: filas y % old_ddos_class=1 =="
awk -F, 'NR>1{k=$20"\t"$21; n[k]++; c[k]+=($18+0==1)} END{for(k in n) printf "%s\t%d\t%.2f%%\n",k,n[k],100*c[k]/n[k]}' "$CSV" | sort
echo
echo "== totales por etiqueta =="
awk -F, 'NR>1{n[$19]++} END{for(k in n) print k, n[k]}' "$CSV" | sort
echo
echo "== manifiesto: entradas FALTA =="
grep -c '^FALTA' "$MAN" || true
grep '^FALTA' "$MAN" || true
