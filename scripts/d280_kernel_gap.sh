#!/usr/bin/env bash
# DAY280 v3 — hueco de 879 pkts. Episodios de la víctima cortados por TIEMPO:
# nuevo episodio si entre dos filas consecutivas de la clave pasan > GAP_MS.
# Uso: scripts/d280_kernel_gap.sh [csv] [victim] [proto] [gap_ms] [min_pkts_episodio]
set -euo pipefail
export LC_ALL=C
CSV=${1:-/vagrant/logs/lab/ddos_windows.csv}
VICTIM=${2:-192.168.100.1}
PROTO=${3:-17}
GAP=${4:-5000}
MINP=${5:-1000}
EXPECTED=49999   # 50 000 enviados - 1 PVST+ no IPv4 (DAY274)
[ -r "$CSV" ] || { echo "no leo $CSV"; exit 1; }
awk -F, -v V="$VICTIM" -v P="$PROTO" -v GAP="$GAP" -v MINP="$MINP" -v EXP="$EXPECTED" '
function col(cands,   n,a,i,j){ n=split(cands,a,"|"); for(i=1;i<=n;i++) for(j=1;j<=NF;j++) if($j==a[i]) return j; return 0 }
NR==1{
  gsub(/\r/,"")
  cV=col("dst_ip"); cP=col("proto"); cD=col("d_pkts"); cS=col("win"); cW=col("window_ms"); cT=col("ts_ms")
  if(!cV||!cP||!cD||!cS||!cW||!cT){ print "ABORTO: cabecera inesperada: " $0; exit 2 }
  next }
{ gsub(/\r/,"") }
$cV!=V || $cP!=P {next}
{ n++; d[n]=$cD+0; s[n]=$cS+0; w[n]=$cW+0; t[n]=$cT+0 }
END{
  if(n==0){ print "ABORTO: 0 filas"; exit 3 }
  ne=1; ea[1]=1
  for(i=2;i<=n;i++) if(t[i]-t[i-1]>GAP){ eb[ne]=i-1; ne++; ea[ne]=i }
  eb[ne]=n
  printf "filas de la clave=%d  episodios=%d (gap>%d ms)  mostrando los de >= %d pkts\n", n, ne, GAP, MINP
  for(e=1;e<=ne;e++){
    a=ea[e]; b=eb[e]; sum=0; ws=0; lo=0; g=0; mx=0; mxgap=0
    for(k=a;k<=b;k++){ sum+=d[k]; ws+=w[k]; if(d[k]<50) lo++; if(d[k]>mx) mx=d[k]
      if(k>a){ if(s[k]-s[k-1]!=1) g++; if(t[k]-t[k-1]>mxgap) mxgap=t[k]-t[k-1] } }
    if(sum<MINP) continue
    span=(t[b]-t[a])/1000+w[a]/1000
    printf "EP %3d: filas %d..%d vent=%d suma=%d max=%d vent<50=%d saltos_win=%d max_dt=%dms sum_window_ms=%.1fs span_ts=%.1fs t_ini=%.0f t_fin=%.0f%s\n", e,a,b,b-a+1,sum,mx,lo,g,mxgap,ws/1000,span,t[a],t[b],(b==n?"  <== FIN":"")
    printf "        vs %d: falta=%d (%.2f %%)\n", EXP, EXP-sum, 100*(EXP-sum)/EXP
  }
}' "$CSV" | perl -MPOSIX -pe 's/t_(ini|fin)=(\d{13})/"t_$1=".strftime("%F %T",localtime($2\/1000))/ge'
