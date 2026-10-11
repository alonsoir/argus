#!/usr/bin/env bash
# DAY291 — mide el piloto caliente sobre un CSV del escritor de dataset.
# Solo event_kind=0 (kind=1 = fast alert, vector en centinela por diseño).
# t0 = primera fila de ATAQUE (src .50, sport 123, dst .1); línea base = src .51.
# Uso: day291_piloto_medir.sh [CSV]   (sin argumento: el más reciente de logs/lab/ddos_dataset/)
set -eu
F=${1:-$(ls -t /vagrant/logs/lab/ddos_dataset/ddos_dataset_*.csv | head -1)}
echo "fichero=$F"
LC_ALL=C awk -F, '
NR==1 || $8!="0" || $4!="192.168.100.1" { next }
{ cls="" }
$3=="192.168.100.50" && $5=="123" { cls="ATQ" }
$3=="192.168.100.51"              { cls="BASE" }
cls=="" { next }
cls=="ATQ" && t0=="" { t0=$1 }
{ m++; ts[m]=$1; c_[m]=cls; rr[m]=$15; pps[m]=$16; n[cls]++; if ($16+0<0) neg[cls]++ }
END {
  for (s in n) printf "filas kind0 %s n=%d centinela=%d\n", s, n[s], neg[s]+0
  if (t0=="") { print "SIN filas de ataque"; exit }
  for (i=1;i<=m;i++) {
    d=ts[i]-t0; b=(d>=0)?int(d/1e10):-int((-d+1e10-1)/1e10)
    k=c_[i] SUBSEP b; c[k]++; sr[k]+=rr[i]; sp[k]+=pps[i]
    if (rr[i]>mx[k] || !(k in mx)) mx[k]=rr[i]
    if (!(b in seen)) { seen[b]=1; bl[++nb]=b }
  }
  for (i=1;i<=nb;i++) for (j=i+1;j<=nb;j++) if (bl[j]<bl[i]) { t=bl[i]; bl[i]=bl[j]; bl[j]=t }
  print "tramo(10s)  clase  n  ratio_medio  ratio_max  pps_medio"
  for (i=1;i<=nb;i++) for (q=0;q<2;q++) {
    s=(q==0)?"BASE":"ATQ"; k=s SUBSEP bl[i]
    if (k in c) printf "%4d  %-4s  %5d  %7.3f  %7.3f  %7.1f\n", bl[i], s, c[k], sr[k]/c[k], mx[k], sp[k]/c[k]
  }
}' "$F"
