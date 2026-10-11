#!/usr/bin/env bash
# DAY290 — paquetes (filas) por flujo, por etiqueta/familia/event_kind. SOLO LECTURA.
# Clave de flujo = fichero + 5-tupla. Mide cuánto reduciría el volumen emitir por flujo
# (1 emisión por flujo) o con calendario en potencias de 2 (paquete 1,2,4,8,...).
set -eu
IN=/vagrant/logs/lab/day289/consolidado.csv
OUTDIR=/vagrant/logs/lab/day290
mkdir -p "$OUTDIR"
TMP="$OUTDIR/paquetes_por_flujo.tmp"
OUT="$OUTDIR/paquetes_por_flujo.tsv"

LC_ALL=C awk -F',' '
NR==1 {
  for (i=1;i<=NF;i++) c[$i]=i
  nreq = split("src_ip dst_ip src_port dst_port proto event_kind etiqueta familia fichero", req, " ")
  for (k=1;k<=nreq;k++) if (!(req[k] in c)) { print "FALTA columna " req[k] > "/dev/stderr"; bad=1 }
  next
}
bad { next }
{
  g   = $c["etiqueta"] "\t" $c["familia"] "\t" $c["event_kind"]
  key = g SUBSEP $c["fichero"] SUBSEP $c["src_ip"] SUBSEP $c["dst_ip"] SUBSEP $c["src_port"] SUBSEP $c["dst_port"] SUBSEP $c["proto"]
  rows[g]++
  if (key in n) n[key]++
  else { n[key]=1; flows[g]++ }
}
END {
  if (bad) exit 2
  for (k in n) {
    p = index(k, SUBSEP); g = substr(k, 1, p-1); v = n[k]
    if (v == 1) one[g]++
    if (v > mx[g]) mx[g] = v
    e2[g] += int(log(v)/log(2) + 1e-9) + 1
  }
  for (g in rows) {
    r = rows[g]; f = flows[g]
    printf "%s\t%d\t%d\t%.2f\t%.1f\t%d\t%d\t%.1f\t%.1f\n", g, r, f, r/f, 100*one[g]/f, mx[g], e2[g], 100*(1-f/r), 100*(1-e2[g]/r)
  }
}' "$IN" > "$TMP"

printf "etiqueta\tfamilia\tevent_kind\tfilas\tflujos\tfilas_por_flujo\tpct_flujos_1fila\tmax_filas_flujo\temis_pot2\treduc_flujo_pct\treduc_pot2_pct\n" > "$OUT"
sort -t "$(printf '\t')" -k1,1 -k2,2 -k3,3 "$TMP" >> "$OUT"
rm -f "$TMP"
echo "OK -> $OUT"
